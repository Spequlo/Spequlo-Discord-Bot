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
    prompt = f"""
    You are an intent router for a Discord bot that manages ClickUp tasks.

    Current user message: "{request["current_message"]}"
    Sender: {user_name}
    Referenced bot message: "{request["referenced_message"]}"
    Referenced task metadata: {json.dumps(request["metadata"])}

    This metadata is authoritative.

    If task metadata contains a task_id or task_name,
    use it when interpreting pronouns such as:

    - it
    - that task
    - the task
    - the one you just created

    ---

    ## Your Job

    Classify this message into exactly one of these intents:

    - **view_tasks** — user wants to see their assigned tasks.
    - **create_task** — user wants to create a new task (explicit ask, e.g. "add a task to fix the login bug").
    - **change_status** — user wants to update a task's status (e.g. "mark the BOM task as done").
    - **summarize_conversation** — user wants the bot to read recent channel messages and create summary.
    - **modify_task** - user wants to change an existing task's properties.
    - **unclear** — the request doesn't clearly map to any of the above, or critical info is missing.

    ---
    
    ## General Rules

    - Only extract params explicitly present or directly implied in the message. Never invent a list name, assignee, or deadline.
    - Set confidence to "low" if the intent is ambiguous between two categories, or if a required param is missing.
    - If confidence is "low", write a specific, short `clarifying_question` that would resolve the ambiguity. Otherwise set it to null.
    - Respond ONLY with valid JSON. No markdown fences, no commentary.

    ## Conversational Context

    The user may be replying to a previous bot message.
    Only allow original creator to modify task
    If the current message depends on information contained in:
    - the referenced bot message
    - prior conversation history

    you should use that context when determining intent and extracting parameters.

    Examples:

    Bot: Created task "Integrate ViewTasksHandler" in Current Sprint.
    User: Move it to backlog.

    → intent = change_status or modify_task
    → task_name = Integrate ViewTasksHandler

    ---

    Bot: Which list should this task go in?
    User: Internal Tools Current Sprint

    → intent = create_task
    → fill in the missing team/list information

    ---

    Bot: Summary of discussion...
    User: Create tasks from that too

    → intent = summarize_conversation

    ## Rules for create_task

    - Only generate a task if there is a clear action item, commitment, assignment, or agreed-upon need.
    - Do NOT generate tasks from brainstorming, open-ended suggestions, unresolved debates, or passing ideas.
    - `task_name` should be short and actionable.
    - `description` should contain supporting details not included in `task_name`.
    - When a referenced bot message contains information about a previously created or discussed task, you may use that information to resolve pronouns such as:
        - it
        - that
        - this task
        - the task
        - the one you just created
    - Do not ask a clarifying question if the referenced context clearly identifies the task.

    **Team and list selection:**
    The following teams and lists exist:
    {TEAM_LISTS}

    - Select the most appropriate `team` and `list_name` if one can be reasonably and unambiguously inferred from the message.
    - Never invent a team or list not shown above — only use exact names from the list.
    - Prefer selecting the most likely team and list using the team descriptions.
    - Only leave team and list null if multiple teams are equally plausible.
    - If the user's wording doesn't clearly match one specific list (e.g. it matches a list name that exists under multiple teams, or no list at all), set `team` and `list_name` to null and lower confidence and let `clarifying_question` ask which list to use.

    **Assignee resolution:**
    - This message may already contain a resolved assignee, provided below. If so, use it exactly as given — do not try to re-derive it from the text.
    - Resolved assignee from this message: {assignee_name} (Discord ID: {assignee_id}) — or "none" if no mention/reply target was present.
    - If a resolved assignee is given above, set `assignee_discord_id` and `assignee_name` to those exact values whenever the message's intent is to assign a task to that person.
    - If no resolved assignee is given, but the user refers to themselves ("assign to me", "I'll take it"), use the sender's ID: {user_id} and name: {user_name}.
    - Otherwise (no resolved assignee, no self-reference), set both `assignee_discord_id` and `assignee_name` to null — even if a name is mentioned in plain text. Do not guess a Discord ID from a name alone.
        
    **Deadlines:**
    - Only extract a deadline if it was explicitly stated.
    - Convert deadlines to YYYY-MM-DD.
    - If no deadline was stated, set `deadline` to null.
    - Do not invent dates.

    **Priority** (1 = urgent, 4 = low):
    - 1: Urgent — "urgent", "asap", "immediately"
    - 2: High — "high priority", "important"
    - 3: Normal — unspecified
    - 4: Low — "low priority", "whenever"

    ## Output    

    Respond with this exact JSON shape. `assignee_discord_id` is a numeric Discord snowflake represented as a string.

    {{
        "intent": "view_tasks | create_task | change_status | summarize_conversation | modify_task | unclear",
        "confidence": "high | medium | low",
        "params": {{
           "task_name": "string or null",
            "task_description": "string or null",
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

