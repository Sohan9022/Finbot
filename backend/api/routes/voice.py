"""
Voice Routes
Transcription and conversational assistant integration.
Improved: robust temp-file cleanup, input validation, consistent response format.
"""
import os
import sys
import tempfile
from typing import Dict

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from core.conversational_assistant import ConversationalFinancialAssistant
from .auth import get_current_user_id

router = APIRouter()


def _response(success: bool, data=None, message: str = ""):
    payload = {"success": success}
    if data is not None:
        payload["data"] = data
    if message:
        payload["message"] = message
    return payload


class VoiceTranscriptionResponse(BaseModel):
    transcribed_text: str
    response: Dict


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id)
):
    """
    Transcribe audio and process with conversational AI.
    Uses speech_recognition if available; otherwise return error.
    """
    tmp_path = None
    try:
        contents = await audio.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # basic size guard (e.g., 10MB)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Audio file too large (max 10MB)")

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1] or ".wav") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        # Transcribe using speech_recognition if installed
        try:
            import speech_recognition as sr
        except Exception:
            raise HTTPException(status_code=500, detail="Speech recognition library not available on server")

        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            raise HTTPException(status_code=400, detail="Could not understand audio")
        except sr.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Speech recognition error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

        assistant = ConversationalFinancialAssistant(user_id)
        response = assistant.handle_conversation(text)

        return _response(True, data={"transcribed_text": text, "response": response})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # cleanup
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@router.post("/text-to-speech")
async def text_to_speech(
    text: str,
    user_id: int = Depends(get_current_user_id)
):
    """
    Convert text to speech endpoint - returns validated text for front-end TTS
    """
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text must not be empty")
    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Text too long (max 1000 chars)")
    # Return text - client should use browser / platform TTS
    return _response(True, data={"text": text}, message="Use client TTS to speak this text")


