"""
Speech-to-Text API Router.

Provides endpoints for audio transcription using OpenAI's Whisper API.
"""
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.interview.services.openai_service import get_openai_service


router = APIRouter(prefix="/speech", tags=["speech"])


# Supported audio formats by Whisper API
SUPPORTED_FORMATS = {
    "audio/mpeg": [".mp3"],
    "audio/mp4": [".mp4", ".m4a"],
    "audio/wav": [".wav"],
    "audio/webm": [".webm"],
    "audio/x-wav": [".wav"],
    "audio/ogg": [".ogg", ".oga"],
    "video/mp4": [".mp4"],
    "video/webm": [".webm"],
}

SUPPORTED_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".oga"}

# Max file size: 25MB (Whisper API limit)
MAX_FILE_SIZE = 25 * 1024 * 1024


class TranscriptionResponse(BaseModel):
    """Response model for audio transcription."""
    
    text: str
    language: str | None = None
    duration: float | None = None
    segments: list[dict] | None = None


class TranscriptionError(BaseModel):
    """Error response model."""
    
    detail: str


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    responses={
        400: {"model": TranscriptionError, "description": "Invalid audio file"},
        413: {"model": TranscriptionError, "description": "File too large"},
        500: {"model": TranscriptionError, "description": "Transcription failed"},
    },
    summary="Transcribe audio to text",
    description="""
Convert speech from an audio file to text using OpenAI's Whisper model.

**Supported formats:** MP3, MP4, MPEG, MPGA, M4A, WAV, WEBM, OGG

**Max file size:** 25MB

**Features:**
- High accuracy transcription
- Automatic language detection
- Optional language hint for better accuracy
- Optional prompt for context/style guidance
- Returns word-level timestamps (segments)

**Use cases:**
- Transcribe candidate interview answers
- Voice note transcription
- Meeting recordings
    """,
)
async def transcribe_audio(
    file: Annotated[UploadFile, File(description="Audio file to transcribe")],
    language: Annotated[
        str | None,
        Form(description="ISO-639-1 language code (e.g., 'en', 'es', 'fr'). Auto-detected if not provided."),
    ] = None,
    prompt: Annotated[
        str | None,
        Form(description="Optional prompt to guide transcription style or provide context"),
    ] = None,
) -> TranscriptionResponse:
    """
    Transcribe audio file to text using OpenAI Whisper.
    
    - **file**: Audio file (mp3, mp4, wav, webm, etc.)
    - **language**: Optional language code for better accuracy
    - **prompt**: Optional context prompt
    
    Returns the transcribed text with optional metadata.
    """
    # Validate file extension
    if file.filename:
        ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext and ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )
    
    # Validate file is not empty
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file",
        )
    
    try:
        # Get OpenAI service and transcribe
        openai_service = get_openai_service()
        
        # Create a file-like object from bytes
        import io
        audio_stream = io.BytesIO(content)
        
        result = await openai_service.transcribe_audio(
            audio_file=audio_stream,
            filename=file.filename or "audio.mp3",
            language=language,
            prompt=prompt,
        )
        
        return TranscriptionResponse(
            text=result["text"],
            language=result.get("language"),
            duration=result.get("duration"),
            segments=result.get("segments"),
        )
        
    except Exception as e:
        # Log the error in production
        error_message = str(e)
        
        # Check for common OpenAI API errors
        if "Invalid file format" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid audio format. Please upload a valid audio file.",
            )
        elif "api_key" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Speech service configuration error. Please contact support.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {error_message}",
            )

