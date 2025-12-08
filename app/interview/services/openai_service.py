"""
OpenAI API service for interview operations.

Handles all interactions with the OpenAI API including:
- Question generation
- Answer evaluation
- Final report generation
"""
import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.interview.models import (
    Difficulty,
    InterviewQuestion,
    QuestionAnswerRecord,
    QuestionEvaluation,
)


class OpenAIService:
    """
    Async service for OpenAI API interactions.
    
    Uses gpt-4o-mini for cost efficiency and speed.
    All methods are async for better performance.
    """
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def _chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Make an async chat completion request.
        
        Args:
            system_prompt: The system message
            user_prompt: The user message
            temperature: Creativity parameter (0-1)
            max_tokens: Maximum response length
            
        Returns:
            The assistant's response text
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""
    
    async def _chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """
        Make a chat completion request expecting JSON response.
        
        Args:
            system_prompt: The system message
            user_prompt: The user message
            temperature: Creativity parameter (0-1)
            max_tokens: Maximum response length
            
        Returns:
            Parsed JSON response as dictionary
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
    
    def _get_experience_description(self, years: int) -> str:
        """Convert years of experience to descriptive level."""
        if years == 0:
            return "Fresher (0 years) - Entry level, focus on fundamentals and basic concepts"
        elif years <= 2:
            return f"Junior ({years} years) - Focus on fundamentals, basic concepts, definitions"
        elif years <= 5:
            return f"Mid-level ({years} years) - Include design decisions, trade-offs, best practices"
        else:
            return f"Senior ({years} years) - Focus on architecture, system design, leadership scenarios"
    
    def _get_question_generation_system_prompt(
        self,
        experience_years: int,
        subject: str,
        difficulty: Difficulty,
        question_number: int,
        total_questions: int,
        previous_records: list[QuestionAnswerRecord] | None = None,
    ) -> str:
        """Generate system prompt for question generation."""
        
        experience_desc = self._get_experience_description(experience_years)
        
        history_context = ""
        if previous_records:
            history_context = "\n\nPrevious questions and performance:\n"
            for record in previous_records:
                q = record.question
                eval_info = ""
                if record.evaluation:
                    eval_info = f" (Score: {record.evaluation.score}/10)"
                history_context += f"- Q{q.question_number} [{q.difficulty.value}]: {q.question[:100]}...{eval_info}\n"
        
        return f"""You are an expert technical interviewer conducting a {subject} interview.

CANDIDATE PROFILE:
- Experience: {experience_desc}
- Years of Experience: {experience_years}
- Subject: {subject}
- Current Difficulty: {difficulty.value}
- Question: {question_number} of {total_questions}
{history_context}

CRITICAL RULES:
- Generate ONLY THEORETICAL/CONCEPTUAL questions
- DO NOT ask coding questions, algorithm implementation, or "write code" questions
- DO NOT ask to solve programming problems or write functions
- Focus on concepts, theory, explanations, comparisons, and "why/how/what" questions

INSTRUCTIONS:
1. Generate a single THEORETICAL interview question appropriate for someone with {experience_years} years of experience
2. Ask about concepts, definitions, comparisons, best practices, trade-offs, or explanations
3. Question complexity based on experience:
   - 0 years (Fresher): Very basic concepts, definitions, "what is X?"
   - 1-2 years (Junior): Fundamentals, basic concepts, simple comparisons
   - 3-5 years (Mid): Design decisions, trade-offs, "why would you use X over Y?", best practices
   - 6+ years (Senior): Architecture concepts, system design theory, complex scenarios, "how would you approach..."
4. Adapt difficulty based on previous performance (if available)
5. Cover different aspects of {subject} across questions
6. Be specific and clear in your questions

GOOD QUESTION EXAMPLES:
- "What is the difference between X and Y?"
- "Explain how X works internally"
- "When would you use X instead of Y?"
- "What are the advantages and disadvantages of X?"
- "How does X handle Y situation?"
- "What best practices should be followed when doing X?"

BAD QUESTIONS (NEVER ASK):
- "Write a function that..."
- "Implement an algorithm to..."
- "Code a solution for..."
- "Write the code to..."

RESPONSE FORMAT (JSON):
{{
    "question": "The THEORETICAL interview question text",
    "topic": "Specific topic within {subject}",
    "difficulty": "{difficulty.value}"
}}

Generate only the JSON response, no additional text."""

    def _get_evaluation_system_prompt(
        self,
        experience_years: int,
        subject: str,
    ) -> str:
        """Generate system prompt for answer evaluation."""
        
        experience_desc = self._get_experience_description(experience_years)
        
        return f"""You are an expert technical interviewer evaluating a candidate's answer.

EVALUATION CONTEXT:
- Candidate Experience: {experience_desc}
- Years of Experience: {experience_years}
- Subject: {subject}

EVALUATION CRITERIA:
1. Correctness (Is the answer technically accurate?)
2. Depth (Does it show deep understanding?)
3. Clarity (Is the explanation clear and well-structured?)
4. Practical Understanding (Does it show real-world application knowledge?)

SCORING GUIDELINES:
- 1-3: Poor - Major misconceptions, incomplete, or incorrect
- 4-5: Below Average - Some correct points but significant gaps
- 6-7: Average - Correct basics, reasonable understanding
- 8-9: Good - Strong understanding, minor improvements possible
- 10: Excellent - Comprehensive, accurate, demonstrates expertise

Be fair but thorough. Consider the candidate's {experience_years} years of experience when evaluating.
A fresher/junior candidate is not expected to have the depth of a senior candidate.

RESPONSE FORMAT (JSON):
{{
    "score": <1-10>,
    "correctness": "Assessment of technical accuracy",
    "depth": "Assessment of understanding depth",
    "clarity": "Assessment of explanation clarity",
    "practical_understanding": "Assessment of real-world knowledge",
    "strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["area1", "area2"],
    "feedback": "Detailed constructive feedback paragraph"
}}

Generate only the JSON response, no additional text."""

    def _get_final_report_system_prompt(
        self,
        experience_years: int,
        subject: str,
    ) -> str:
        """Generate system prompt for final report generation."""
        
        experience_desc = self._get_experience_description(experience_years)
        
        return f"""You are an expert technical interviewer generating a comprehensive assessment report.

ASSESSMENT CONTEXT:
- Candidate Experience: {experience_desc}
- Years of Experience: {experience_years}
- Subject: {subject}

REPORT REQUIREMENTS:
1. Provide an overall assessment considering all answers
2. Identify patterns in strengths and weaknesses
3. Give actionable, specific recommendations for improvement
4. Consider the candidate's {experience_years} years of experience in your assessment
5. Be constructive and professional

HIRING RECOMMENDATION GUIDELINES:
- Based on overall score and consistency for someone with {experience_years} years experience:
  - 8-10 average: "Strong Hire" - Candidate exceeds expectations
  - 6-7 average: "Hire" - Candidate meets expectations for their experience level
  - 4-5 average: "Conditional Hire" - Consider for lower-level role or with mentoring
  - 1-3 average: "No Hire" - Does not meet minimum requirements

RESPONSE FORMAT (JSON):
{{
    "overall_score": <float 0-10>,
    "detailed_feedback": "Comprehensive narrative assessment (2-3 paragraphs)",
    "strong_areas": ["area1", "area2", "area3"],
    "weak_areas": ["area1", "area2"],
    "recommendations": ["specific actionable recommendation 1", "recommendation 2", "recommendation 3"],
    "hire_recommendation": "Strong Hire|Hire|Conditional Hire|No Hire - with brief justification"
}}

Generate only the JSON response, no additional text."""

    async def generate_question(
        self,
        experience_years: int,
        subject: str,
        difficulty: Difficulty,
        question_number: int,
        total_questions: int,
        previous_records: list[QuestionAnswerRecord] | None = None,
    ) -> InterviewQuestion:
        """
        Generate an interview question based on context.
        
        Args:
            experience_years: Candidate's years of experience
            subject: Interview subject
            difficulty: Target difficulty level
            question_number: Current question number
            total_questions: Total questions in interview
            previous_records: Previous Q&A records for adaptive questioning
            
        Returns:
            Generated interview question
        """
        system_prompt = self._get_question_generation_system_prompt(
            experience_years=experience_years,
            subject=subject,
            difficulty=difficulty,
            question_number=question_number,
            total_questions=total_questions,
            previous_records=previous_records,
        )
        
        user_prompt = f"Generate question {question_number} of {total_questions} for this {subject} interview."
        
        response = await self._chat_completion_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.8,  # Slightly higher for variety
        )
        
        return InterviewQuestion(
            question_number=question_number,
            question=response.get("question", ""),
            difficulty=Difficulty(response.get("difficulty", difficulty.value)),
            topic=response.get("topic", subject),
        )
    
    async def evaluate_answer(
        self,
        question: InterviewQuestion,
        answer: str,
        experience_years: int,
        subject: str,
    ) -> QuestionEvaluation:
        """
        Evaluate a candidate's answer.
        
        Args:
            question: The interview question
            answer: Candidate's answer
            experience_years: Candidate's years of experience
            subject: Interview subject
            
        Returns:
            Evaluation with score and feedback
        """
        system_prompt = self._get_evaluation_system_prompt(
            experience_years=experience_years,
            subject=subject,
        )
        
        user_prompt = f"""QUESTION ({question.difficulty.value} - {question.topic}):
{question.question}

CANDIDATE'S ANSWER:
{answer}

Evaluate this answer."""
        
        response = await self._chat_completion_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,  # Lower for consistency
        )
        
        return QuestionEvaluation(
            score=response.get("score", 5),
            correctness=response.get("correctness", ""),
            depth=response.get("depth", ""),
            clarity=response.get("clarity", ""),
            practical_understanding=response.get("practical_understanding", ""),
            strengths=response.get("strengths", []),
            areas_for_improvement=response.get("areas_for_improvement", []),
            feedback=response.get("feedback", ""),
        )
    
    async def generate_final_report(
        self,
        experience_years: int,
        subject: str,
        records: list[QuestionAnswerRecord],
    ) -> dict[str, Any]:
        """
        Generate a comprehensive final report.
        
        Args:
            experience_years: Candidate's years of experience
            subject: Interview subject
            records: All Q&A records with evaluations
            
        Returns:
            Final report data dictionary
        """
        system_prompt = self._get_final_report_system_prompt(
            experience_years=experience_years,
            subject=subject,
        )
        
        # Build detailed context of all Q&A
        qa_summary = "\n".join([
            f"""
Q{r.question.question_number} [{r.question.difficulty.value}] - {r.question.topic}:
Question: {r.question.question}
Answer: {r.answer[:500] if r.answer else 'No answer'}{'...' if r.answer and len(r.answer) > 500 else ''}
Score: {r.evaluation.score if r.evaluation else 'N/A'}/10
Feedback: {r.evaluation.feedback if r.evaluation else 'N/A'}
"""
            for r in records
        ])
        
        user_prompt = f"""INTERVIEW SUMMARY:
Total Questions: {len(records)}
Questions Answered: {sum(1 for r in records if r.answer)}

DETAILED Q&A:
{qa_summary}

Generate the final assessment report."""
        
        response = await self._chat_completion_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=3000,
        )
        
        return response
    
    def calculate_adaptive_difficulty(
        self,
        current_difficulty: Difficulty,
        recent_scores: list[int],
    ) -> Difficulty:
        """
        Calculate adaptive difficulty based on recent performance.
        
        Args:
            current_difficulty: Current difficulty level
            recent_scores: Recent evaluation scores
            
        Returns:
            Adjusted difficulty level
        """
        if not recent_scores:
            return current_difficulty
        
        avg_score = sum(recent_scores) / len(recent_scores)
        
        difficulty_order = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
        current_index = difficulty_order.index(current_difficulty)
        
        # Adjust based on performance
        if avg_score >= 8 and current_index < 2:
            # Performing well, increase difficulty
            return difficulty_order[current_index + 1]
        elif avg_score <= 4 and current_index > 0:
            # Struggling, decrease difficulty
            return difficulty_order[current_index - 1]
        
        return current_difficulty


# Singleton instance
_openai_service: OpenAIService | None = None


def get_openai_service() -> OpenAIService:
    """Get or create the OpenAI service singleton."""
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service

