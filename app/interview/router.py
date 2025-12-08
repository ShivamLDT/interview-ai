"""
Interview API router.

Defines all interview-related endpoints:
- POST /start - Start a new interview
- POST /answer - Submit an answer
- GET /report/{interview_id} - Get final report
- GET /status/{interview_id} - Get interview status
- GET /question/{interview_id} - Get current question
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.interview.models import (
    APIResponse,
    FinalReportResponse,
    InterviewQuestion,
    InterviewState,
    StartInterviewRequest,
    StartInterviewResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
)
from app.interview.services.interview_service import (
    InterviewAlreadyCompletedError,
    InterviewNotFoundError,
    InterviewService,
    InterviewServiceError,
    InvalidQuestionNumberError,
    get_interview_service,
)

router = APIRouter(prefix="/interview", tags=["interview"])


def get_service() -> InterviewService:
    """Dependency to get interview service."""
    return get_interview_service()


# ============================================================================
# Interview Endpoints
# ============================================================================

@router.post(
    "/start",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new interview",
    description="Initialize a new interview session with the specified configuration.",
)
async def start_interview(
    request: StartInterviewRequest,
) -> APIResponse:
    """
    Start a new interview session.
    
    Creates an interview with the specified configuration and returns
    the interview ID along with the first question.
    
    - **experience_level**: junior, mid, or senior
    - **subject**: Technical subject (e.g., "Python", "System Design")
    - **difficulty**: easy, medium, or hard
    - **num_questions**: Number of questions (1-20, default 5)
    """
    service = get_service()
    
    try:
        response = await service.start_interview(request)
        return APIResponse.success_response(response.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview: {str(e)}",
        )


@router.post(
    "/answer",
    response_model=APIResponse,
    summary="Submit an answer",
    description="Submit an answer to the current question and receive evaluation.",
)
async def submit_answer(
    request: SubmitAnswerRequest,
) -> APIResponse:
    """
    Submit an answer to the current interview question.
    
    The answer is evaluated using AI, and if the interview is not complete,
    the next question is generated based on performance (adaptive difficulty).
    
    - **interview_id**: UUID of the interview session
    - **answer**: Your answer to the current question
    - **question_number**: The question number being answered
    """
    service = get_service()
    
    try:
        response = await service.submit_answer(request)
        return APIResponse.success_response(response.model_dump())
    except InterviewNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InterviewAlreadyCompletedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InvalidQuestionNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process answer: {str(e)}",
        )


@router.get(
    "/report/{interview_id}",
    response_model=APIResponse,
    summary="Get final report",
    description="Generate and retrieve the comprehensive interview assessment report.",
)
async def get_report(
    interview_id: UUID,
) -> APIResponse:
    """
    Get the final comprehensive report for a completed interview.
    
    Includes:
    - Overall score
    - Detailed feedback
    - Question-by-question breakdown
    - Strengths and areas for improvement
    - Actionable recommendations
    - Hiring recommendation
    """
    service = get_service()
    
    try:
        response = await service.get_report(interview_id)
        return APIResponse.success_response(response.model_dump())
    except InterviewNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InterviewServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get(
    "/status/{interview_id}",
    response_model=APIResponse,
    summary="Get interview status",
    description="Get the current status and state of an interview session.",
)
async def get_interview_status(
    interview_id: UUID,
) -> APIResponse:
    """
    Get the current status of an interview.
    
    Returns the full interview state including:
    - Configuration
    - Current question number
    - Status (in_progress or completed)
    - Conversation history
    """
    service = get_service()
    
    try:
        response = await service.get_interview_state(interview_id)
        return APIResponse.success_response(response.model_dump())
    except InterviewNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interview status: {str(e)}",
        )


@router.get(
    "/question/{interview_id}",
    response_model=APIResponse,
    summary="Get current question",
    description="Get the current unanswered question for an interview.",
)
async def get_current_question(
    interview_id: UUID,
) -> APIResponse:
    """
    Get the current question for an interview.
    
    Returns the current unanswered question, or null if the interview
    is complete.
    """
    service = get_service()
    
    try:
        question = await service.get_current_question(interview_id)
        
        if question is None:
            return APIResponse.success_response({
                "message": "Interview is complete",
                "question": None,
            })
        
        return APIResponse.success_response(question.model_dump())
    except InterviewNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current question: {str(e)}",
        )

