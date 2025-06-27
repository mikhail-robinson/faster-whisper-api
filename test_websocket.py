import asyncio
import websockets
import json

# The path to the audio file you want to stream
AUDIO_FILE_PATH = "Whisper Test 1.m4a" # IMPORTANT: Change this to your audio file
WEBSOCKET_URI = "ws://localhost:8001/ws/stt"

async def stream_audio():
    """
    Connects to the WebSocket, streams an audio file, and prints responses.
    """
    print(f"Connecting to {WEBSOCKET_URI}...")
    try:
        async with websockets.connect(WEBSOCKET_URI) as websocket:
            print("WebSocket connection established.")

            # Open the audio file in binary read mode
            with open(AUDIO_FILE_PATH, "rb") as audio_file:
                while True:
                    # Read the file in chunks
                    chunk = audio_file.read(4096) # Read 4KB at a time
                    if not chunk:
                        break # End of file
                    # Send the audio chunk over the WebSocket
                    await websocket.send(chunk)
                    await asyncio.sleep(0.1) # Small delay to simulate real-time streaming

            # Signal the end of the audio stream
            await websocket.send(b"EOS")
            print("Sent EOS signal.")

            # Listen for responses from the server
            while True:
                try:
                    response_str = await websocket.recv()
                    response = json.loads(response_str)
                    print(f"Received message: {response}")
                    if response.get("type") == "final":
                        print("\n--- Final Transcript Received ---")
                        break # Exit after receiving the final transcript
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed by server.")
                    break

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Run the asynchronous stream_audio function
    asyncio.run(stream_audio())
