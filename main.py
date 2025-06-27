import os
from typing import Literal
from fastapi import FastAPI, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from faster_whisper import WhisperModel
import asyncio
import io

# Ensure models directory exists
models_dir = os.path.join(os.path.dirname(__file__), "whisper_models/")
if not os.path.exists(models_dir):
    os.makedirs(models_dir, exist_ok=True)

# Configuration
MODEL_SIZE = os.getenv("MODEL_SIZE", "base.en") # Using "base.en" for better NZ accent
DEVICE = os.getenv("DEVICE", "auto") # "cpu" or "cuda"
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8") # "int8" for CPU, "float16" for GPU

print(f"Loading Whisper model: {MODEL_SIZE} on {DEVICE} with {COMPUTE_TYPE}...")
try:
    model = WhisperModel(
        model_size_or_path=MODEL_SIZE,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        download_root=models_dir,
        local_files_only=False, # Set to True after first download if desired
    )
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    # Exit or raise if model loading fails, as the app can't function
    raise RuntimeError(f"Failed to load Whisper model: {e}")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": True}

@app.post("/transcribe")
async def transcribe(
    audio: UploadFile,
) -> dict[Literal["response", "status", "language_detected"], str]:
    try:
        segments, info = model.transcribe(audio=audio.file, beam_size=5, language="en")
        print(f"Detected language '{info.language}' with probability {info.language_probability}")
        text = "".join([segment.text for segment in segments])
        return {
            "status": "ok",
            "response": text.strip(),
            "language_detected": info.language
        }
    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")


@app.websocket("/ws/stt")
async def websocket_stt_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket client connected")

    audio_buffer = bytearray()

    try:
        while True:
            data = await websocket.receive_bytes()

            if data == b"EOS": # Client signals end of speech
                print(f"Received EOS. Total audio bytes: {len(audio_buffer)}. Starting transcription.")
                if len(audio_buffer) > 0:
                    audio_file_like = io.BytesIO(audio_buffer)

                    segments, info = model.transcribe(audio_file_like, language="en", beam_size=5, word_timestamps=True)

                    full_text = ""
                    # This loop will run after the entire transcription is complete
                    for segment in segments:
                        partial_transcript = segment.text
                        full_text += partial_transcript + " "
                        # Sending each segment one by one can simulate partial results
                        await websocket.send_json({
                            "type": "partial",
                            "text": full_text.strip(),
                        })
                        await asyncio.sleep(0.01)

                    # Then send the final concatenated text
                    await websocket.send_json({
                        "type": "final",
                        "text": full_text.strip()
                    })
                    print(f"Sent final transcript: {full_text.strip()}")
                audio_buffer = bytearray() # Reset buffer
            else:
               audio_buffer.extend(data) # Keep accumulating if not EOS

    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    except Exception as e:
        print(f"WebSocket STT error: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
             try:
                 await websocket.send_json({"type": "error", "message": str(e)})
             except Exception as send_e:
                 print(f"Error sending error to client: {send_e}")
    finally:
        if websocket.client_state != WebSocketState.DISCONNECTED:
             await websocket.close()
        print("WebSocket connection closed.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)