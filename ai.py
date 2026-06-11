from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def summarizeTranscript(transcript: str, context: str):
    prompt = f"""
    You are a project management assistant.

    Analyze the Discord conversation.

    Use the context if provided when determining tasks.

    Context:
    {context}

    Rules:
    - Only generate a task if there is a clear action item, assignment, responsibility, or commitment.
    - Do not generate tasks from brainstorming, suggestions, unresolved discussions, or ideas.
    - If no tasks exist, return an empty task list.
    - Respond ONLY with valid JSON.
    - Do not include markdown code fences.
    - Extract a deadline if one was explicitly mentioned.
    - If no deadline was discussed, set deadline to null.
    - Do not invent deadlines.
    - Each message begins with:
        TIME - DISCORD_ID (DISPLAY_NAME): message
        Example: 15:30 - 123456789 (John): I will create the PCB BOM.
    - When a task is assigned to a participant, return the participant's Discord ID in assignee_discord_id.
    - If no assignee is clearly identified, set assignee_discord_id to null.
    - Do not use display names for task assignment.
    - Use display names for the summary.

    JSON Schema:

    {{
        "participants": [
            "name"
        ],
        "summary": "summary text",
        "confidence": {{
            "owner_confidence": "high|medium|low",
            "ambiguities": [
                "ambiguity"
            ]
        }},
        "tasks": [
            {{
                "name": "task title",
                "description": "task details",
                "priority": 3,
                "deadline": "YYYY-MM-DD or null",
                "assignee_discord_id: 123456789
                "assignee_name": "person name"
            }}
        ]
    }}

    Transcript:
    {transcript}
    """

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = response.text
        if text is None:
            raise ValueError("Gemini returned an empty response")   
        return json.loads(text)
    except Exception as e:        
        error_text = str(e)

        if "429" in error_text:
            raise RuntimeError("RATE_LIMIT")

        elif "503" in error_text:
            raise RuntimeError("SERVICE_UNAVAILABLE")

        elif "RESOURCE_EXHAUSTED" in error_text:
            raise RuntimeError("QUOTA_EXCEEDED")

        raise

def regenerateSummary(summary: str, transcript: str, feedback: str):
    prompt = f"""
    You previously generated this summary:
    {summary}

    The user reported these issues:
    {feedback}

    Generate a corrected summary based on the transcript below.

    Transcript:
    {transcript}

    Rules:
    - Only generate a task if there is a clear action item, assignment, responsibility, or commitment.
    - Do not generate tasks from brainstorming, suggestions, unresolved discussions, or ideas.
    - If no tasks exist, return an empty task list.
    - Respond ONLY with valid JSON.
    - Do not include markdown code fences.
    - Extract a deadline if one was explicitly mentioned.
    - If no deadline was discussed, set deadline to null.
    - Do not invent deadlines.
    - Each message begins with:
        TIME - DISCORD_ID (DISPLAY_NAME): message
        Example: 15:30 - 123456789 (John): I will create the PCB BOM.
    - When a task is assigned to a participant, return the participant's Discord ID in assignee_discord_id.
    - If no assignee is clearly identified, set assignee_discord_id to null.
    - Do not use display names for task assignment.
    - Use display names for the summary.

    JSON Schema:

    {{
        "participants": [
            "name"
        ],
        "summary": "summary text",
        "confidence": {{
            "owner_confidence": "high|medium|low",
            "ambiguities": [
                "ambiguity"
            ]
        }},
        "tasks": [
            {{
                "name": "task title",
                "description": "task details",
                "priority": 3,
                "deadline": "YYYY-MM-DD or null",
                "assignee_discord_id: 123456789
                "assignee_name": "person name"
            }}
        ]
    }}
    """

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        text = response.text
        if text is None:
            raise ValueError("Gemini returned an empty response")   
        return json.loads(text)
    except Exception as e:        
        error_text = str(e)

        if "429" in error_text:
            raise RuntimeError("RATE_LIMIT")

        elif "503" in error_text:
            raise RuntimeError("SERVICE_UNAVAILABLE")

        elif "RESOURCE_EXHAUSTED" in error_text:
            raise RuntimeError("QUOTA_EXCEEDED")

        raise



