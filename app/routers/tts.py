import io
import wave
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.services.tts import generate_speech, get_voices
from app.utils.response import success, error

router = APIRouter(tags=["tts"])

AVAILABLE_VOICES = None


def get_available_voices():
    global AVAILABLE_VOICES
    if AVAILABLE_VOICES is None:
        AVAILABLE_VOICES = get_voices()
    return AVAILABLE_VOICES


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    voice: str = "af_sarah"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@router.post("/speak")
def speak(request: TTSRequest):
    """Generate TTS audio (WAV) from arbitrary text."""
    try:
        voices = get_available_voices()
        if request.voice not in voices:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice '{request.voice}'. Available: {voices[:10]}..."
            )

        pcm_data, sample_rate = generate_speech(request.text, request.voice, request.speed)

        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)

        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
def list_voices():
    """List all available TTS voice names."""
    return success(data={"voices": get_available_voices()}, message="Voices listed")
