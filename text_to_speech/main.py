import os
from typing import Iterator

import uvicorn
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# --- Configuration ---

# Load environment variables from .env file
load_dotenv()

# ElevenLabs TTS Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("Warning: ELEVENLABS_API_KEY environment variable not set. TTS will not work.")
else:
    elevenlabs = ElevenLabs(
        api_key=ELEVENLABS_API_KEY
    )

# --- FastAPI App Initialization ---

app = FastAPI()
tts_router = APIRouter(prefix="/tts")

# Configure CORS to allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # The origin of your Next.js app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Request Bodies ---

class TextToSpeechRequest(BaseModel):
    text: str
    voice_id: str = "21m00Tcm4TlvDq8ikWAM" # Default voice (Rachel), can be overridden by client
    model_id: str = "eleven_flash_v2"
    output_format: str = "mp3_44100_128"

# --- API Endpoints ---

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "Text-to-Speech"}

@tts_router.post("/synthesize")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Text-to-Speech endpoint. Receives text and returns an audio stream from ElevenLabs.
    """

    try:
        # Generate audio stream from ElevenLabs
        audio_stream = elevenlabs.text_to_speech.stream(
            text=request.text,
            voice_id=request.voice_id,
            model_id=request.model_id,
            output_format=request.output_format
        )

        # Check if audio_stream is valid
        if not isinstance(audio_stream, Iterator):
             raise HTTPException(status_code=500, detail="Failed to generate audio stream from ElevenLabs.")

        # Stream the audio back to the client
        return StreamingResponse(audio_stream, media_type="audio/mpeg")

    except Exception as e:
        print(f"ElevenLabs TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")

# Include the router in the main app
app.include_router(tts_router)

if __name__ == "__main__":
    # Run on port 8002 to avoid conflict with other services
    uvicorn.run(app, host="0.0.0.0", port=8002)