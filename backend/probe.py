import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("--- AVAILABLE MODELS ---")
for model in client.models.list():
    print(f"Model ID: {model.name}")