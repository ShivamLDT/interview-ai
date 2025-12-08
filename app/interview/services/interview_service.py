"""
Interview service containing core business logic.

Orchestrates the interview flow, manages state, and coordinates
between storage and OpenAI services.
"""
from uuid import UUID, uuid4

from app.interview.models import (
    Difficulty,
    FinalReportResponse,
    InterviewConfig,
    InterviewQuestion,
    InterviewState,
    InterviewStatus,
    QuestionAnswerRecord,
    QuestionBreakdown,
    QuestionEvaluation,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.interview.services.openai_service import OpenAIService, get_openai_service
from app.interview.storage import InterviewStorage, get_interview_storage


class InterviewServiceError(Exception):
    """Custom exception for interview service errors."""
    pass


class InterviewNotFoundError(InterviewServiceError):
    """Raised when interview is not found."""
    pass


class InterviewAlreadyCompletedError(InterviewServiceError):
    """Raised when trying to answer on completed interview."""
    pass


class InvalidQuestionNumberError(InterviewServiceError):
    """Raised when question number doesn't match expected."""
    pass


class InterviewService:
    """
    Service for managing interview sessions.
    
    Handles:
    - Starting new interviews
    - Processing answers and generating evaluations
    - Generating final reports
    - Managing interview state
    """
    
    def __init__(
        self,
        storage: InterviewStorage | None = None,
        openai_service: OpenAIService | None = None,
    ):
        """
        Initialize the interview service.
        
        Args:
            storage: Interview storage instance (uses global if not provided)
            openai_service: OpenAI service instance (uses global if not provided)
        """
        self.storage = storage or get_interview_storage()
        self.openai = openai_service or get_openai_service()
    
    async def start_interview(
        self,
        request: StartInterviewRequest,
    ) -> StartInterviewResponse:
        """
        Start a new interview session.
        
        Creates the interview state, generates the first question,
        and stores everything in memory.
        
        Args:
            request: Interview configuration from the client
            
        Returns:
            Interview ID and first question
        """
        # Generate unique interview ID
        interview_id = uuid4()
        
        # Create interview configuration
        config = InterviewConfig(
            experience_years=request.experience_years,
            subject=request.subject,
            difficulty=request.difficulty,
            num_questions=request.num_questions,
        )
        
        # Generate first question
        first_question = await self.openai.generate_question(
            experience_years=request.experience_years,
            subject=request.subject,
            difficulty=request.difficulty,
            question_number=1,
            total_questions=request.num_questions,
        )
        
        # Create initial conversation history with first question
        initial_record = QuestionAnswerRecord(
            question=first_question,
            answer=None,
            evaluation=None,
        )
        
        # Create interview state
        interview_state = InterviewState(
            interview_id=interview_id,
            config=config,
            current_question_num=1,
            conversation_history=[initial_record],
            status=InterviewStatus.IN_PROGRESS,
        )
        
        # Store the interview
        await self.storage.create(interview_state)
        
        return StartInterviewResponse(
            interview_id=interview_id,
            first_question=first_question,
            total_questions=request.num_questions,
            config=config,
        )
    
    async def submit_answer(
        self,
        request: SubmitAnswerRequest,
    ) -> SubmitAnswerResponse:
        """
        Process a submitted answer.
        
        Evaluates the answer, updates state, and generates next question
        if the interview is not complete.
        
        Args:
            request: Answer submission from the client
            
        Returns:
            Evaluation and next question (if any)
            
        Raises:
            InterviewNotFoundError: If interview doesn't exist
            InterviewAlreadyCompletedError: If interview is already done
            InvalidQuestionNumberError: If question number doesn't match
        """
        # Retrieve interview state
        interview = await self.storage.get(request.interview_id)
        
        if interview is None:
            raise InterviewNotFoundError(
                f"Interview {request.interview_id} not found or expired"
            )
        
        if interview.status == InterviewStatus.COMPLETED:
            raise InterviewAlreadyCompletedError(
                "This interview has already been completed"
            )
        
        if request.question_number != interview.current_question_num:
            raise InvalidQuestionNumberError(
                f"Expected question {interview.current_question_num}, "
                f"got {request.question_number}"
            )
        
        # Get current question record
        current_record = interview.conversation_history[-1]
        
        # Evaluate the answer
        evaluation = await self.openai.evaluate_answer(
            question=current_record.question,
            answer=request.answer,
            experience_years=interview.config.experience_years,
            subject=interview.config.subject,
        )
        
        # Update the current record with answer and evaluation
        current_record.answer = request.answer
        current_record.evaluation = evaluation
        
        # Check if interview is complete
        is_complete = interview.current_question_num >= interview.config.num_questions
        questions_remaining = interview.config.num_questions - interview.current_question_num
        next_question = None
        
        if is_complete:
            # Mark interview as completed
            interview.status = InterviewStatus.COMPLETED
        else:
            # Calculate adaptive difficulty based on recent scores
            recent_scores = [
                r.evaluation.score
                for r in interview.conversation_history
                if r.evaluation is not None
            ][-3:]  # Last 3 scores
            
            adaptive_difficulty = self.openai.calculate_adaptive_difficulty(
                current_difficulty=interview.config.difficulty,
                recent_scores=recent_scores,
            )
            
            # Generate next question
            next_question = await self.openai.generate_question(
                experience_years=interview.config.experience_years,
                subject=interview.config.subject,
                difficulty=adaptive_difficulty,
                question_number=interview.current_question_num + 1,
                total_questions=interview.config.num_questions,
                previous_records=interview.conversation_history,
            )
            
            # Add next question to history
            next_record = QuestionAnswerRecord(
                question=next_question,
                answer=None,
                evaluation=None,
            )
            interview.conversation_history.append(next_record)
            
            # Increment question number
            interview.current_question_num += 1
            questions_remaining -= 1
        
        # Update storage
        await self.storage.update(interview)
        
        return SubmitAnswerResponse(
            evaluation=evaluation,
            next_question=next_question,
            is_complete=is_complete,
            questions_remaining=questions_remaining,
            current_question_num=interview.current_question_num,
        )
    
    async def get_report(
        self,
        interview_id: UUID,
    ) -> FinalReportResponse:
        """
        Generate comprehensive final report.
        
        Analyzes all answers and generates actionable feedback.
        
        Args:
            interview_id: The interview to generate report for
            
        Returns:
            Comprehensive assessment report
            
        Raises:
            InterviewNotFoundError: If interview doesn't exist
            InterviewServiceError: If interview is not completed
        """
        # Retrieve interview state
        interview = await self.storage.get(interview_id)
        
        if interview is None:
            raise InterviewNotFoundError(
                f"Interview {interview_id} not found or expired"
            )
        
        if interview.status != InterviewStatus.COMPLETED:
            raise InterviewServiceError(
                "Cannot generate report for an incomplete interview. "
                f"Current status: {interview.status.value}"
            )
        
        # Filter records that have been answered
        answered_records = [
            r for r in interview.conversation_history
            if r.answer is not None and r.evaluation is not None
        ]
        
        # Generate report using OpenAI
        report_data = await self.openai.generate_final_report(
            experience_years=interview.config.experience_years,
            subject=interview.config.subject,
            records=answered_records,
        )
        
        # Build question-wise breakdown
        question_breakdown = [
            QuestionBreakdown(
                question_number=r.question.question_number,
                question=r.question.question,
                topic=r.question.topic,
                difficulty=r.question.difficulty,
                answer_summary=r.answer[:200] + "..." if len(r.answer) > 200 else r.answer,
                score=r.evaluation.score,
                feedback=r.evaluation.feedback,
            )
            for r in answered_records
        ]
        
        # Calculate overall score if not provided by OpenAI
        if "overall_score" not in report_data:
            scores = [r.evaluation.score for r in answered_records]
            report_data["overall_score"] = sum(scores) / len(scores) if scores else 0
        
        return FinalReportResponse(
            interview_id=interview_id,
            overall_score=report_data.get("overall_score", 0),
            total_questions=interview.config.num_questions,
            questions_answered=len(answered_records),
            experience_years=interview.config.experience_years,
            subject=interview.config.subject,
            detailed_feedback=report_data.get("detailed_feedback", ""),
            strong_areas=report_data.get("strong_areas", []),
            weak_areas=report_data.get("weak_areas", []),
            question_wise_breakdown=question_breakdown,
            recommendations=report_data.get("recommendations", []),
            hire_recommendation=report_data.get("hire_recommendation", "Unable to determine"),
        )
    
    async def get_interview_state(
        self,
        interview_id: UUID,
    ) -> InterviewState:
        """
        Get the current state of an interview.
        
        Args:
            interview_id: The interview ID
            
        Returns:
            Current interview state
            
        Raises:
            InterviewNotFoundError: If interview doesn't exist
        """
        interview = await self.storage.get(interview_id)
        
        if interview is None:
            raise InterviewNotFoundError(
                f"Interview {interview_id} not found or expired"
            )
        
        return interview
    
    async def get_current_question(
        self,
        interview_id: UUID,
    ) -> InterviewQuestion | None:
        """
        Get the current unanswered question.
        
        Args:
            interview_id: The interview ID
            
        Returns:
            Current question or None if interview is complete
            
        Raises:
            InterviewNotFoundError: If interview doesn't exist
        """
        interview = await self.get_interview_state(interview_id)
        
        if interview.status == InterviewStatus.COMPLETED:
            return None
        
        # Return the last question in history (should be unanswered)
        if interview.conversation_history:
            return interview.conversation_history[-1].question
        
        return None


# Service factory function
def get_interview_service() -> InterviewService:
    """Get an interview service instance."""
    return InterviewService()

