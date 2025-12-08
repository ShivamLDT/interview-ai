"""
Pydantic models for Interview API requests and responses.
"""
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class ExperienceLevel(str, Enum):
    """Candidate experience level."""
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"


class Difficulty(str, Enum):
    """Question difficulty level."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewStatus(str, Enum):
    """Interview session status."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ============================================================================
# Request Models
# ============================================================================

class StartInterviewRequest(BaseModel):
    """Request model for starting a new interview."""
    experience_level: ExperienceLevel = Field(
        ...,
        description="Candidate's experience level"
    )
    subject: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Technical subject for the interview (e.g., 'Python', 'System Design')"
    )
    difficulty: Difficulty = Field(
        ...,
        description="Initial difficulty level for questions"
    )
    num_questions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Total number of questions in the interview"
    )


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting an answer."""
    interview_id: UUID = Field(
        ...,
        description="Unique identifier for the interview session"
    )
    answer: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Candidate's answer to the current question"
    )
    question_number: int = Field(
        ...,
        ge=1,
        description="The question number being answered"
    )


# ============================================================================
# Response Models - Evaluation & Questions
# ============================================================================

class QuestionEvaluation(BaseModel):
    """Evaluation result for a single answer."""
    score: int = Field(
        ...,
        ge=1,
        le=10,
        description="Score from 1 to 10"
    )
    correctness: str = Field(
        ...,
        description="Assessment of answer correctness"
    )
    depth: str = Field(
        ...,
        description="Assessment of answer depth"
    )
    clarity: str = Field(
        ...,
        description="Assessment of answer clarity"
    )
    practical_understanding: str = Field(
        ...,
        description="Assessment of practical understanding"
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="List of strengths in the answer"
    )
    areas_for_improvement: list[str] = Field(
        default_factory=list,
        description="Areas where the candidate can improve"
    )
    feedback: str = Field(
        ...,
        description="Detailed constructive feedback"
    )


class InterviewQuestion(BaseModel):
    """A single interview question."""
    question_number: int = Field(
        ...,
        description="Question number in the sequence"
    )
    question: str = Field(
        ...,
        description="The interview question text"
    )
    difficulty: Difficulty = Field(
        ...,
        description="Difficulty level of this question"
    )
    topic: str = Field(
        ...,
        description="Specific topic within the subject"
    )


# ============================================================================
# Response Models - Interview State
# ============================================================================

class QuestionAnswerRecord(BaseModel):
    """Record of a question, answer, and evaluation."""
    question: InterviewQuestion
    answer: str | None = None
    evaluation: QuestionEvaluation | None = None


class InterviewConfig(BaseModel):
    """Interview configuration."""
    experience_level: ExperienceLevel
    subject: str
    difficulty: Difficulty
    num_questions: int


class InterviewState(BaseModel):
    """Complete interview state."""
    interview_id: UUID
    config: InterviewConfig
    current_question_num: int
    conversation_history: list[QuestionAnswerRecord]
    status: InterviewStatus


# ============================================================================
# Response Models - API Responses
# ============================================================================

class StartInterviewResponse(BaseModel):
    """Response for starting a new interview."""
    interview_id: UUID
    first_question: InterviewQuestion
    total_questions: int
    config: InterviewConfig


class SubmitAnswerResponse(BaseModel):
    """Response for submitting an answer."""
    evaluation: QuestionEvaluation
    next_question: InterviewQuestion | None = None
    is_complete: bool
    questions_remaining: int
    current_question_num: int


class QuestionBreakdown(BaseModel):
    """Breakdown of a single question in the final report."""
    question_number: int
    question: str
    topic: str
    difficulty: Difficulty
    answer_summary: str
    score: int
    feedback: str


class FinalReportResponse(BaseModel):
    """Final interview report."""
    interview_id: UUID
    overall_score: float = Field(
        ...,
        ge=0,
        le=10,
        description="Overall score out of 10"
    )
    total_questions: int
    questions_answered: int
    experience_level: ExperienceLevel
    subject: str
    detailed_feedback: str = Field(
        ...,
        description="Comprehensive assessment narrative"
    )
    strong_areas: list[str] = Field(
        default_factory=list,
        description="Areas where candidate performed well"
    )
    weak_areas: list[str] = Field(
        default_factory=list,
        description="Areas needing improvement"
    )
    question_wise_breakdown: list[QuestionBreakdown] = Field(
        default_factory=list,
        description="Detailed breakdown for each question"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable recommendations for improvement"
    )
    hire_recommendation: str = Field(
        ...,
        description="Overall hiring recommendation"
    )


# ============================================================================
# Generic API Response Wrapper
# ============================================================================

class APIResponse(BaseModel):
    """Generic API response wrapper."""
    success: bool = True
    data: Any = None
    error: str | None = None

    @classmethod
    def success_response(cls, data: Any) -> "APIResponse":
        """Create a success response."""
        return cls(success=True, data=data, error=None)

    @classmethod
    def error_response(cls, error: str) -> "APIResponse":
        """Create an error response."""
        return cls(success=False, data=None, error=error)

