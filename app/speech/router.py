"""
Speech-to-Text API Router.

Provides endpoints for audio transcription using OpenAI's Whisper API.
Includes real-time WebSocket streaming using OpenAI Realtime API.
"""
import asyncio
import base64
import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Optional websockets import (not available on serverless platforms)
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from app.core.config import settings
from app.interview.services.openai_service import get_openai_service


router = APIRouter(prefix="/speech", tags=["speech"])


@router.get(
    "/test",
    response_class=HTMLResponse,
    summary="Real-time transcription test page",
    description="Interactive test page for the real-time WebSocket transcription",
)
async def get_test_client():
    """Serve the real-time transcription test client."""
    html_path = Path(__file__).parent / "test_client.html"
    return HTMLResponse(content=html_path.read_text())


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


# OpenAI Realtime API configuration
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
REALTIME_MODEL = "gpt-4o-realtime-preview-2024-12-17"


@router.websocket("/realtime")
async def realtime_transcription(websocket: WebSocket):
    """
    Real-time speech-to-text WebSocket endpoint.
    
    Connect to this WebSocket and stream audio data to receive
    real-time transcriptions with minimal latency.
    
    **Protocol:**
    
    1. Connect to ws://host/api/speech/realtime
    2. Optionally send config: {"type": "config", "language": "en"}
    3. Stream audio as base64: {"type": "audio", "data": "<base64_pcm16_audio>"}
    4. Receive transcriptions: {"type": "transcript", "text": "...", "is_final": bool}
    5. Send {"type": "stop"} to end session
    
    **Audio Format:**
    - PCM16 audio at 24kHz sample rate, mono channel
    - Send as base64-encoded chunks
    - Recommended chunk size: 4096 bytes (~85ms of audio)
    
    **Events from server:**
    - {"type": "ready"} - Connection established
    - {"type": "transcript", "text": "...", "is_final": false} - Partial transcript
    - {"type": "transcript", "text": "...", "is_final": true} - Final transcript
    - {"type": "error", "message": "..."} - Error occurred
    - {"type": "closed"} - Session ended
    
    **Note:** This endpoint requires a persistent connection and is not available
    on serverless platforms like Vercel. Use POST /api/speech/transcribe instead.
    """
    await websocket.accept()
    
    # Check if websockets library is available (not on serverless)
    if not WEBSOCKETS_AVAILABLE:
        await websocket.send_json({
            "type": "error",
            "message": "Real-time transcription not available on this platform. Use POST /api/speech/transcribe instead."
        })
        await websocket.close()
        return
    
    # Check API key
    if not settings.openai_api_key:
        await websocket.send_json({
            "type": "error",
            "message": "OpenAI API key not configured"
        })
        await websocket.close()
        return
    
    openai_ws = None
    
    try:
        # Connect to OpenAI Realtime API
        headers = [
            ("Authorization", f"Bearer {settings.openai_api_key}"),
            ("OpenAI-Beta", "realtime=v1"),
        ]
        
        openai_ws = await websockets.connect(
            f"{OPENAI_REALTIME_URL}?model={REALTIME_MODEL}",
            extra_headers=headers,
        )
        
        # Configure the session for transcription
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "input_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
            }
        }
        await openai_ws.send(json.dumps(session_config))
        
        # Notify client we're ready
        await websocket.send_json({"type": "ready"})
        
        async def receive_from_openai():
            """Receive messages from OpenAI and forward transcripts to client."""
            try:
                async for message in openai_ws:
                    data = json.loads(message)
                    event_type = data.get("type", "")
                    
                    # Handle transcription events
                    if event_type == "conversation.item.input_audio_transcription.completed":
                        transcript = data.get("transcript", "")
                        if transcript:
                            await websocket.send_json({
                                "type": "transcript",
                                "text": transcript,
                                "is_final": True,
                            })
                    
                    elif event_type == "input_audio_buffer.speech_started":
                        await websocket.send_json({
                            "type": "speech_started",
                        })
                    
                    elif event_type == "input_audio_buffer.speech_stopped":
                        await websocket.send_json({
                            "type": "speech_stopped",
                        })
                    
                    elif event_type == "error":
                        error_msg = data.get("error", {}).get("message", "Unknown error")
                        await websocket.send_json({
                            "type": "error",
                            "message": error_msg,
                        })
                    
                    elif event_type == "session.created":
                        # Session is ready
                        pass
                    
                    elif event_type == "session.updated":
                        # Session config updated
                        pass
                        
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e:
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })
                except:
                    pass
        
        async def receive_from_client():
            """Receive audio from client and forward to OpenAI."""
            try:
                while True:
                    message = await websocket.receive_json()
                    msg_type = message.get("type", "")
                    
                    if msg_type == "audio":
                        # Forward audio to OpenAI
                        audio_data = message.get("data", "")
                        if audio_data:
                            await openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": audio_data,
                            }))
                    
                    elif msg_type == "commit":
                        # Commit the audio buffer for processing
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.commit",
                        }))
                    
                    elif msg_type == "clear":
                        # Clear the audio buffer
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.clear",
                        }))
                    
                    elif msg_type == "config":
                        # Update session config (e.g., language)
                        language = message.get("language")
                        if language:
                            await openai_ws.send(json.dumps({
                                "type": "session.update",
                                "session": {
                                    "input_audio_transcription": {
                                        "model": "whisper-1",
                                        "language": language,
                                    }
                                }
                            }))
                    
                    elif msg_type == "stop":
                        # End the session
                        break
                        
            except WebSocketDisconnect:
                pass
            except Exception as e:
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })
                except:
                    pass
        
        # Run both tasks concurrently
        openai_task = asyncio.create_task(receive_from_openai())
        client_task = asyncio.create_task(receive_from_client())
        
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [openai_task, client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
    except websockets.exceptions.InvalidStatusCode as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Failed to connect to OpenAI: {e}",
        })
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Connection error: {str(e)}",
            })
        except:
            pass
    finally:
        # Cleanup
        if openai_ws:
            try:
                await openai_ws.close()
            except:
                pass
        
        try:
            await websocket.send_json({"type": "closed"})
            await websocket.close()
        except:
            pass

