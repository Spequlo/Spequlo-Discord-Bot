from google import genai
from google.genai import types
import os
import json
from dotenv import load_dotenv

load_dotenv()

TEAM_LISTS = """
Team: mobile_app
Purpose: Features, improvements, bugs, and maintenance related to the mobile application.

Lists:
- backlog: Planned mobile work not currently being worked on.
- current_sprint: Mobile app work actively being developed this sprint.
- bugs: Mobile-specific issues and bug fixes.

Team: integration
Purpose: Integrations between Spequlo and external services, APIs, third-party platforms, and automation systems.

Lists:
- backlog: Planned integration work set aside for a later date.
- current_sprint: Integration work actively being developed.
- bugs: Integration-specific issues.

Team: internal_tools
Purpose: Internal company tools, admin panels, Discord bots, development utilities, automation scripts, operational tooling, and engineering productivity tools.

Lists:
- backlog: Planned internal tooling work.
- current_sprint: Internal tooling work actively being developed.
- bugs: Internal tool issues.

Team: infrastructure
Purpose: Hosting, servers, deployments, cloud resources, networking, databases, monitoring, CI/CD, security, and platform reliability.

Lists:
- backlog: Planned infrastructure work.
- current_sprint: Infrastructure work actively being worked on.
- bugs: Infrastructure incidents and issues.

Team: website
Purpose: The company's website, landing pages, marketing pages, SEO, and web presence.

Lists:
- list: General website work.

Examples:

"Add login screen to the mobile app"
→ team: mobile_app
→ list_name: current_sprint

"Fix deployment pipeline"
→ team: infrastructure
→ list_name: current_sprint

"Integrate Slack notifications"
→ team: integration
→ list_name: current_sprint

"Add a command to the Discord bot"
→ team: internal_tools
→ list_name: current_sprint

"Update the company landing page"
→ team: website
→ list_name: list
"""

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

def classifyIntent(request: dict, user_id: int, user_name: str, assignee_id: int | None, assignee_name: str | None):
    prompt = rf"""
    You are an intent router for a Discord bot managing ClickUp tasks. Analyze the input data to determine user intent, extract exact parameters, and output structured JSON.

    ## Input Context
    - **Sender:** {user_name} (ID: {user_id})
    - **Current Message:** "{request["current_message"]}"
    - **Referenced Message:** "{request["referenced_message"]}"
    - **Referenced Metadata:** {json.dumps(request["metadata"])}
    - **Message Assignee Hook:** Name: {assignee_name} | ID: {assignee_id} (Value is "none" if no explicit mention/reply target exists)
    - **Available Workspace Tree:** {TEAM_LISTS}

    ---

    ## Core Routing Rules
    1. **Metadata Primacy:** Metadata is generated by the bot and is absolute truth. If metadata and message text conflict, prefer metadata.
    2. **Context Resolution:** Resolve pronouns ("it", "that task", "the one you just made") using the `task_id` or `task_name` present in the Referenced Metadata.
    3. **Implicit Continuation:** Do not treat isolated fragment replies (e.g., "Backlog", "Me", "Tomorrow", "Current Sprint") as standalone requests. Combine them with the referenced context to fulfill the previous missing information.

    ---

    ## Intent Classification
    Classify the message into exactly one category:
    - `view_tasks`: Request to view assigned tasks.
    - `create_task`: Explicit request to create a new task (Must have a clear action item, commitment, or agreed need. No brainstorming/passing ideas).
    - `change_status`: Request to update an existing task's status lifecycle.
    - `modify_task`: Request to edit properties of an existing task (list, assignee, deadline, priority, title, description).
    - `summarize_conversation`: Request to read channel history and generate a summary text.
    - `unclear`: Request does not map cleanly, or critical data is missing.

    ---

    ## Parameter Rules
    Extract parameters *only* if explicitly present or directly implied. Never invent data.

    - id / name
    - Pull from Referenced Metadata if user refers to an existing task.
    - Name must be short and actionable.

    - priority
    - 1 = Urgent / ASAP / Immediately
    - 2 = High / Important
    - 3 = Normal (default)
    - 4 = Low / Whenever

    - deadline
    - Convert explicit dates to YYYY-MM-DD.
    - Never invent dates.

    - team / list_name
    - Must exactly match the Available Workspace Tree.
    - If ambiguous, set both to null and ask a clarifying question.

    - assignee
    - If Message Assignee Hook exists, use it exactly.
    - If user says "me" or "I'll take it", use Sender ID/Name.
    - Otherwise null.

    ---

    ## Confidence & Clarifications
    - Set confidence to `low` if the intent is ambiguous or a required workflow parameter is missing.
    - When confidence is `low`, write a specific, short `clarifying_question` to resolve the blocker. Do not ask a question if referenced metadata already clarifies the task.
    - If confidence is `high` or `medium`, set `clarifying_question` to `null`.

    ---

    ## Output Format
    Respond ONLY with a raw, valid JSON object matching the schema below. No markdown formatting fences (e.g., do not wrap in ```json), no conversational prefixes, no trailing explanations.

    <output_format>
    {{
        "intent": "view_tasks | create_task | change_status | summarize_conversation | modify_task | unclear",
        "confidence": "high | medium | low",
        "params": {{
            "id": "string or null",
            "name": "string or null",
            "description": "string or null",
            "status": "string or null",
            "priority": "1 | 2 | 3 | 4 | null",
            "assignee_discord_id": "string or null",
            "assignee_name": "string or null",
            "deadline": "YYYY-MM-DD or null",
            "team": "string or null",
            "list_name": "string or null"
        }},
        "clarifying_question": "string or null"
    }}
    </output_format>
    """

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
        text = response.text
        if text is None:
            raise ValueError("Gemini returned an empty response")
        text = text.strip()
        result = json.loads(text)

        required = {"intent", "confidence", "params", "clarifying_question"}
        missing = required - result.keys()

        if missing:
            raise ValueError(f"Missing fields: {missing}")

        return result
    except Exception as e:
        error_text = str(e)

        if "429" in error_text:
            raise RuntimeError("RATE_LIMIT")
        elif "503" in error_text:
            raise RuntimeError("SERVICE_UNAVAILABLE")
        elif "RESOURCE_EXHAUSTED" in error_text:
            raise RuntimeError("QUOTA_EXCEEDED")

        raise

