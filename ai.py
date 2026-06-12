from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def summarizeTranscript(transcript: str, context: str):
    prompt = f"""
    You are a project management assistant analyzing a Discord conversation to extract actionable tasks for a ClickUp Workspace.

    Transcript:
    {transcript}

    Context:
    {context}

    ---
    
    ## Your Goal
    
    Identify every action item — both explicit and inferred — that a team member must complete.

    **Explicit tasks** — directly stated commitments, assignments, or responsibilities:
    - "I'll create the documentation by Friday"
    - "Can you handle the deployment?" / "Sure"
    - "John owns the onboarding doc"

    **Inferred tasks** — gaps or blockers the conversation reveals that the team implicitly agrees must be resolved, even if no one is assigned:
    - "Nobody knows how deployment works" → Create deployment documentation
    - "We need a test environment" → Set up test environment
    - "People keep asking for credentials" → Document credential access process

    ---

    ## Message Format

    Each message follows this format:
        HH:MM - DISCORD_ID (DISPLAY_NAME): message
        Example: 15:30 - 123456789 (John): How do you deploy to spotify.

    ---
    
    ## Rules

    **Task generation:**
    - Only generate a task if there is a clear action item, commitment, assignment, or agreed-upon need.
    - Do NOT generate tasks from brainstorming, open-ended suggestions, unresolved debates, or passing ideas.
    - If no tasks exist, return an empty `tasks` array.

    **Assignment:**
    - Use the Discord ID (numeric) for `assignee_discord_id` — never a display name.
    - Use the display name for `assignee_name`.
    - Use display names in the summary.
    - If ownership is unclear, set both to null.

    **Deadlines:**
    - Only extract a deadline if one was explicitly stated in the conversation.
    - Never invent or infer a deadline. If none was mentioned, set `deadline` to null.

    **Priority** (1 = urgent, 4 = low):
    - 1: Urgent
    - 2: High
    - 3: Normal
    - 4: Low

    ---

    ## Output

    Respond ONLY with valid JSON. No markdown fences, no commentary.

    {{
        "participants": ["display_name"],
        "summary": "2–3 sentence overview of the conversation and its outcomes.",
        "tasks": [
            {{
                "name": "Short task title",
                "description": "What needs to be done and why, with relevant context from the conversation.",
                "priority": 3,
                "deadline": "YYYY-MM-DD or null",
                "assignee_discord_id": 123456789,
                "assignee_name": "Display name or null",
                "task_type": "explicit | inferred",
                "confidence": "high | medium | low",
                "owner_confidence": "high | medium | low",
                "ambiguities": ["Any unclear aspects about this specific task"]
            }}
        ]
    }}    
    """

    try:
        response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
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
    You are a project management assistant. You previously analyzed a Discord conversation and generated a summary and task list. A user has reviewed your output and provided feedback.

    Your job is to revise the output based on that feedback, using the original transcript as the source of truth.

    ---

    ## Previous Output

    {summary}

    ---

    ## User Feedback

    {feedback}

    ---

    ## Original Transcript

    {transcript}

    ---

    ## How to Revise

    1. **Treat the transcript as ground truth.** The feedback tells you where your previous output was wrong or incomplete — but every task must still be supportable by the transcript.
    2. **Reconcile, don't replace.** Keep tasks from the previous output that are still valid. Only remove tasks if the transcript does not support them.
    3. **Add tasks the feedback highlights** if the transcript confirms them as clear commitments, assignments, or agreed-upon needs.
    4. **Correct misattributions** — if the feedback says a task was assigned to the wrong person, verify against the transcript and update accordingly.
    5. **Update the summary** to reflect the corrected understanding.

    ---

    ## Message Format

    Each message follows this format:
        HH:MM - DISCORD_ID (DISPLAY_NAME): message
        Example: 15:30 - 123456789 (John): I will create the PCB BOM.

    ---

    ## Rules

    **Task generation:**
    - Only generate a task if there is a clear action item, commitment, assignment, or agreed-upon need.
    - Do NOT generate tasks from brainstorming, open-ended suggestions, unresolved debates, or passing ideas.
    - If no tasks exist, return an empty `tasks` array.

    **Assignment:**
    - Use the Discord ID (numeric) for `assignee_discord_id` — never a display name.
    - Use the display name for `assignee_name`.
    - Use display names for the summary.
    - If ownership is unclear, set both to null.

    **Deadlines:**
    - Only extract a deadline if one was explicitly stated in the conversation.
    - Never invent or infer a deadline. If none was mentioned, set `deadline` to null.

    **Priority** (1 = urgent, 5 = low):
    - 1: Blocking other work or has an imminent deadline
    - 2: Important, near-term
    - 3: Normal
    - 4: Low urgency
    - 5: Nice to have / no timeline

    ---

    ## Output

    Respond ONLY with valid JSON. No markdown fences, no commentary.

    {{
        "participants": ["display_name"],
        "summary": "2–3 sentence overview of the conversation and its outcomes, incorporating the correction.",
        "revision_notes": "1–2 sentences explaining what changed from the previous output and why.",
        "tasks": [
            {{
                "name": "Short task title",
                "description": "What needs to be done and why, with relevant context from the conversation.",
                "task_type": "explicit | inferred",
                "priority": 3,
                "deadline": "YYYY-MM-DD or null",
                "assignee_discord_id": 123456789,
                "assignee_name": "Display name or null",
                "confidence": "high | medium | low",
                "owner_confidence": "high | medium | low",
                "ambiguities": ["Any unclear aspects about this specific task"]
            }}
        ]
    }}
    """

    try:
        response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
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
