"""Audio service with Google Cloud TTS/STT stub.

When Google Cloud credentials are configured, this service uses real
Google Cloud TTS and Speech-to-Text. Otherwise, it returns stub
responses in development mode.
"""
from app.config import settings
from app.logger import logger
from typing import Optional
import os


class AudioService:
    """Abstraction layer for cloud-based TTS and STT."""

    @property
    def is_tts_available(self) -> bool:
        return settings.google_cloud_configured

    @property
    def is_stt_available(self) -> bool:
        return settings.google_cloud_configured

    def generate_tts_audio(
        self,
        text: str,
        language_code: str = "en-US",
        voice_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Generate TTS audio using Google Cloud TTS.

        Returns dict with audio_content (bytes) and content_type, or None.
        In stub mode, returns a placeholder response.
        """
        if self.is_tts_available:
            try:
                from google.cloud import texttospeech

                client = texttospeech.TextToSpeechClient()
                synthesis_input = texttospeech.SynthesisInput(text=text)

                voice_params = texttospeech.VoiceSelectionParams(
                    language_code=language_code,
                    name=voice_name or "en-US-Standard-A",
                )

                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                )

                response = client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config,
                )

                return {
                    "audio_content": response.audio_content,
                    "content_type": "audio/mp3",
                }
            except ImportError:
                logger.warning("google-cloud-texttospeech not installed. Using stub TTS.")
            except Exception as e:
                logger.error(f"Google Cloud TTS error: {e}")
                return None

        # Stub mode
        if settings.is_development:
            logger.info(f"[STUB] TTS generation for: '{text[:50]}...'")
            return {
                "audio_content": b"STUB_AUDIO_CONTENT",
                "content_type": "audio/mp3",
                "stub": True,
            }

        return None

    def transcribe_audio(
        self,
        audio_content: bytes,
        language_code: str = "en-US",
    ) -> Optional[str]:
        """Transcribe audio using Google Cloud Speech-to-Text.

        Returns transcribed text or None.
        In stub mode, returns a placeholder transcription.
        """
        if self.is_stt_available:
            try:
                from google.cloud import speech

                client = speech.SpeechClient()
                audio = speech.RecognitionAudio(content=audio_content)
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    language_code=language_code,
                )

                response = client.recognize(config=config, audio=audio)
                if response.results:
                    return response.results[0].alternatives[0].transcript
                return None
            except ImportError:
                logger.warning("google-cloud-speech not installed. Using stub STT.")
            except Exception as e:
                logger.error(f"Google Cloud STT error: {e}")
                return None

        # Stub mode
        if settings.is_development:
            logger.info("[STUB] Audio transcription - returning placeholder text")
            return "[stub transcription]"

        return None

    def save_audio_file(self, audio_content: bytes, filename: str, subdir: str = "tts") -> Optional[str]:
        """Save audio content to the uploads directory.

        Returns the file path, or None on failure.
        """
        try:
            upload_dir = os.path.join(settings.upload_dir, subdir)
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, "wb") as f:
                f.write(audio_content)
            return file_path
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            return None


# Singleton instance
audio_service = AudioService()
