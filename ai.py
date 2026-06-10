from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def summarizeC(transcript: str):
    prompt = f"""
    You are a project management assistant.

    Summarize the Discord conversation below.

    Summarize the discussion.

    Output format:

    Participants:
    - Name

    Summary:
    - Main discussion points

    Action Items:
    - Task name
    - Task details (if known)
    - Responsible person (if known)

    Confidence:
    - How confident are you that the assigned owners are correct?
    - What information was ambiguous?
    - Did you find any action items?

    Transcript:
    {transcript}
    """

    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)

    return response.text