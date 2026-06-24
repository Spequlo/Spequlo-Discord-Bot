# Dipersa

Dipersa is a Discord bot that lets the Spequlo team manage ClickUp tasks using natural language. Instead of switching between Discord and ClickUp, users can create tasks, modify existing ones, view assigned work, and summarize conversations directly from Discord.

The bot uses a self-hosted Llama 3.1 8B Instruct model to classify intent, extract parameters, and route requests to the appropriate handler — enabling conversational project management without rigid commands.

---

## Features

### Task Creation

Create ClickUp tasks directly from Discord using natural language.

```
@Dipersa give me a task to fix the login bug
@Dipersa create a high priority task for OAuth integration in the integration backlog
@Dipersa create a task to update the landing page and assign it to @user
```

The bot extracts the task name, description, assignee, priority, team, list, and deadline (when provided) and creates the task in ClickUp automatically.

---

### Task Modification

Modify existing tasks by replying to a previous bot message or referring to a task by name.

```
@Dipersa rename this to OAuth Integration
@Dipersa move this to backlog
@Dipersa make this high priority
@Dipersa set the deadline to next Friday
@Dipersa assign this to @user
```

Supported modifications: name, description, assignee, priority, deadline, and list.

---

### View Assigned Tasks

Retrieve your assigned ClickUp tasks without leaving Discord.

```
@Dipersa show my tasks
@Dipersa what am I assigned to?
@Dipersa show @user's tasks
```

---

### Conversation Summarization

Summarize recent Discord conversations and surface actionable items.

```
@Dipersa summarize the last 50 messages
@Dipersa what did we talk about today?
@Dipersa summarize the last 2 hours
```

Summaries include a discussion overview, action items, and open questions.

---

## How It Works

### Conversation Flow

The bot only responds when directly mentioned or when a user replies to a previous bot message. This keeps it unobtrusive and reduces noise.

```
User:   @Dipersa create a task to add OAuth support
Bot:    ✅ Created task "Add OAuth Support" in integration → current_sprint

User:   @Dipersa move it to backlog
Bot:    ✅ Updated task "Add OAuth Support"
        • moved to integration → backlog

User:   @Dipersa make it high priority
Bot:    ✅ Updated task "Add OAuth Support"
        • priority set to High
```

### Metadata System

Every bot response stores contextual metadata alongside the Discord message. When a user replies to a bot message, that metadata is injected into the next request — allowing the bot to resolve references like "it", "this task", and "that one" without users having to repeat themselves.

### Intent Classification

User messages are sent to the self-hosted Llama 3.1 8B model which classifies intent and extracts structured parameters. Supported intents:

- `create_task`
- `modify_task`
- `view_tasks`
- `summarize_conversation`
- `help`

The classifier outputs structured JSON passed directly into the appropriate handler. If a required parameter is missing or the intent is ambiguous, the bot asks a short clarifying question rather than guessing.

### Handler Layer

Each intent maps to a dedicated async handler responsible for validation, business logic, and ClickUp API interaction. All handlers return a standardized response:

```python
{
    "message": "...",
    "metadata": {...}
}
```

### Task Cache

User task data is cached in memory with a 60-second TTL to reduce ClickUp API calls and improve response times. The cache is invalidated automatically when tasks are modified.

---

## Architecture

```
Discord (discord.py)
    ↓
Intent Classifier (Llama 3.1 8B — Modal)
    ↓
Handler (helpers.py)
    ↓
ClickUp REST API
```

| Layer | Technology |
|---|---|
| Bot framework | discord.py |
| HTTP client | aiohttp |
| LLM inference | Llama 3.1 8B Instruct (self-hosted on Modal) |
| Project management | ClickUp API |
| Database | Supabase |
| Bot hosting | Railway |
| LLM hosting | Modal (L4 GPU) |

---

## Deployment

### Bot (Railway)

The bot runs on Railway and deploys automatically on push to the main branch.

### LLM (Modal)

The Llama 3.1 8B model is deployed on Modal with an L4 GPU. Weights are cached in a Modal Volume after the first download.

```bash
modal deploy ./modal_app.py
```

The container scales down after 10 minutes of inactivity and cold-starts on the next request.

---

## Author

Developed by Edidiong Ekong at Spequlo.
