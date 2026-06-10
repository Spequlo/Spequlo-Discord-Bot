from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def summarizeC(transcript: str):
    prompt = f"""
    You are a project management assistant.

    Summarize the discussion.

    Include:
    - The people involved in the discussion

    Keep it concise.

    Transcript:
    {transcript}
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text