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
                "priority": 3 or use context,
                "deadline": "YYYY-MM-DD or null"
                "assignee_name": "person name"
            }}
        ]
    }}

    Transcript:
    {transcript}
    """

    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return json.loads(response.text)

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
                "priority": 3 or use context,
                "deadline": "YYYY-MM-DD or null"
                "assignee_name": "person name"
            }}
        ]
    }}
    """

    response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    return json.loads(response.text)



