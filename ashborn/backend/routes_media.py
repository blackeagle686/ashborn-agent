"""
Ashborn Backend — Text-to-Speech & Speech-to-Text endpoints.
"""
import os
import subprocess
from fastapi import APIRouter

from .schemas import TTSRequest

router = APIRouter()

# ── Text-to-Speech ────────────────────────────────────────────────────────────

@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Generate speech from text using gTTS and return base64-encoded MP3."""
    import io
    import base64
    try:
        from gtts import gTTS
    except ImportError:
        return {"status": "error", "message": "gTTS not installed. Run: pip install gtts"}

    try:
        text = req.text[:1000].strip()
        tts = gTTS(text=text, lang=req.lang, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        audio_b64 = base64.b64encode(buf.read()).decode("utf-8")
        return {"status": "ok", "audio": audio_b64}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


# ── Speech-to-Text ────────────────────────────────────────────────────────────

_recording_process = None
_recording_file = "/tmp/ashborn_recording.wav"


@router.post("/stt/start")
async def start_recording():
    """Start recording audio using arecord."""
    global _recording_process

    if _recording_process is not None:
        try:
            _recording_process.terminate()
            _recording_process.wait(timeout=2)
        except Exception:
            pass
        _recording_process = None

    try:
        _recording_process = subprocess.Popen(
            ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-q", _recording_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"status": "ok", "message": "Recording started"}
    except Exception as exc:
        return {"status": "error", "message": f"Failed to start arecord: {exc}"}


@router.post("/stt/stop")
async def stop_recording():
    """Stop recording and transcribe using SpeechRecognition (Google API)."""
    global _recording_process

    if _recording_process is not None:
        try:
            _recording_process.terminate()
            _recording_process.wait(timeout=2)
        except Exception:
            pass
        _recording_process = None

    if not os.path.exists(_recording_file):
        return {"status": "error", "message": "No recording file found"}

    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(_recording_file) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)
        return {"status": "ok", "text": text}
    except ImportError:
        return {"status": "error", "message": "SpeechRecognition not installed. Run: pip install SpeechRecognition"}
    except sr.UnknownValueError:
        return {"status": "error", "message": "Could not understand audio. Please try again."}
    except sr.RequestError as e:
        return {"status": "error", "message": f"Could not request results; {e}"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
