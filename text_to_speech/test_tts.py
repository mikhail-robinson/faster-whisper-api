import requests

# --- Configuration ---
TTS_API_URL = "http://localhost:8002/tts/synthesize"
TEST_TEXT = "Hello from the Text-to-Speech service. This is a test audio file."
OUTPUT_FILENAME = "test_output.mp3"

# --- Pydantic Model for Request Body ---
# This should match the one in main.py
request_data = {
    "text": TEST_TEXT,
    "voice_id": "21m00Tcm4TlvDq8ikWAM", # Rachel's voice
    "model_id": "eleven_flash_v2",
    "output_format": "mp3_44100_128"
}

# --- Send Request and Save Audio ---
print(f"Sending request to: {TTS_API_URL}")
print(f"Request data: {request_data}")

try:
    response = requests.post(TTS_API_URL, json=request_data, stream=True)

    # Check if the request was successful
    if response.status_code == 200:
        print("Successfully received audio stream.")

        # Save the audio stream to a file
        with open(OUTPUT_FILENAME, "wb") as f:
            for chunk in response.iter_content(chunk_size=4096):
                f.write(chunk)

        print(f"Audio successfully saved to: {OUTPUT_FILENAME}")

    else:
        # Print error details if something went wrong
        print(f"Error: Received status code {response.status_code}")
        print("Response content:")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"An error occurred while making the request: {e}")
