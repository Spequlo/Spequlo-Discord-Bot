# Dipersa Discord Bot

## Overview

Dipersa is a Discord bot designed to bridge communication between Discord and ClickUp by allowing users to manage tasks using natural language. Instead of manually navigating ClickUp, users can interact with the bot directly in Discord to create tasks, modify existing tasks, view assigned work, and summarize conversations.

The bot uses a Large Language Model (LLM) to interpret user requests, classify intent, extract relevant parameters, and route requests to the appropriate handler. This allows users to interact with project management workflows using conversational language rather than rigid commands.

---

## Features

### Task Creation

Users can create ClickUp tasks directly from Discord.

Examples:

* `@Dipersa create a task to add OAuth support`
* `@Dipersa create a high priority bug fix in integration backlog`
* `@Dipersa assign a task to @OnlyRafael`

The bot automatically determines:

* Task name
* Description
* Assignee
* Priority
* Team
* List
* Deadline (when provided)

and creates the task in ClickUp.

---

### Task Modification

Users can modify existing tasks through natural language.

Examples:

* `@Dipersa rename this task to OAuth Integration`
* `@Dipersa move this task to backlog`
* `@Dipersa make this high priority`
* `@Dipersa set the deadline to next Friday`
* `@Dipersa assign this to @OnlyRafael`

The bot supports modifications through:

1. Replying to a previous bot message containing task metadata.
2. Referring to a task by name.

---

### View Assigned Tasks

Users can retrieve their assigned ClickUp tasks directly from Discord.

Examples:

* `@Dipersa show my tasks`
* `@Dipersa what am I assigned to?`

The bot queries ClickUp, simplifies task data, and presents assigned work in a user-friendly format.

---

### Conversation Summarization

Dipersa can summarize recent Discord conversations and identify actionable items.

Examples:

* `@Dipersa summarize the last 50 messages`
* `@Dipersa what did we talk about today?`

Summaries include:

* Discussion overview
* Action items
* Open questions

This feature is useful for converting conversations into actionable project work.

---

## System Architecture

### Discord Layer

The bot is built using `discord.py`.

The bot responds only when:

* Mentioned directly
* A user replies to a previous bot message

This prevents unnecessary processing and reduces noise within channels.

---

### Intent Classification Layer

User requests are sent to an LLM-based intent classifier.

The classifier determines:

* User intent
* Confidence level
* Required parameters
* Clarification questions (if needed)

Supported intents include:

* `create_task`
* `modify_task`
* `view_tasks`
* `summarize_conversation`
* `help`

The classifier outputs structured JSON which is passed directly into the bot's request handlers.

---

### Handler Layer

Each intent maps to a dedicated handler.

Examples:

```python
request_handlers = {
    "view_tasks": viewTasksHandler,
    "create_task": createTaskHandler,
    "modify_task": modifyTaskHandler,
    "summarize_conversation": summarizeConversationHandler,
    "help": helpHandler
}
```

Handlers are responsible for:

* Validation
* Business logic
* ClickUp API interactions
* Metadata generation

All handlers return a standardized response format:

```python
{
    "message": "...",
    "metadata": {...}
}
```

---

### Metadata System

A core feature of Dipersa is its metadata-driven conversation model.

Each bot response stores contextual metadata alongside the Discord message ID.

Example:

```python
{
    "task_id": "abc123",
    "task_name": "OAuth Integration",
    "assignee_discord_id": 123456789,
    "deadline": "2026-07-15T17:00:00-05:00",
    "team": "integration",
    "list_name": "backlog"
}
```

This metadata allows users to continue interacting with tasks through replies.

Example:

```text
User: Create OAuth task
Bot: Task created

User: Move it to backlog
```

The bot resolves "it" using the stored metadata from the referenced message.

This enables natural conversational workflows without requiring users to repeatedly specify task information.

---

### ClickUp Integration

The bot integrates directly with the ClickUp REST API.

Supported operations include:

* Create task
* Update task
* Move task between lists
* Retrieve tasks
* Validate workspace membership

Task information is simplified and cached to reduce API usage and improve responsiveness.

---

### Task Cache

The bot maintains an in-memory cache of user task data.

Benefits:

* Faster task retrieval
* Reduced ClickUp API calls
* Improved user experience

The cache is automatically invalidated whenever tasks are modified.

---

## Workspace Structure

Dipersa currently supports the following ClickUp organization:

### Mobile App

* backlog
* current_sprint
* bugs

### Integration

* backlog
* current_sprint
* bugs

### Internal Tools

* backlog
* current_sprint
* bugs

### Infrastructure

* backlog
* current_sprint
* bugs

### Website

* list

The LLM uses this structure to determine the correct destination when creating or moving tasks.

---

## Technologies Used

### Core Framework

* Python 3
* discord.py

### Networking

* aiohttp

### AI Integration

* Gemini API (current implementation)
* Planned support for self-hosted LLMs

### Project Management

* ClickUp API

### Utilities

* python-dotenv
* logging
* dateutil

---

## Design Goals

The primary goals of Dipersa are:

1. Reduce friction between discussion and task creation.
2. Allow users to manage ClickUp through natural language.
3. Preserve context across conversations using metadata.
4. Minimize manual project management overhead.
5. Provide a foundation for future self-hosted AI integrations.

---

## Future Improvements

Potential future enhancements include:

* Self-hosted LLM deployment
* Better task disambiguation workflows
* Persistent metadata storage
* Multi-workspace support
* Advanced reporting and analytics
* Slack and Microsoft Teams integrations

---

## Example Workflow

```text
User:
@Dipersa create a task to add OAuth support

Bot:
Created task "Add OAuth Support"

User:
@Dipersa move it to current sprint

Bot:
Task updated
• moved to integration → current_sprint

User:
@Dipersa make it high priority

Bot:
Task updated
• priority set to High
```

This workflow demonstrates how metadata allows users to interact naturally without repeatedly specifying task details.

---

## Author

Developed by Edidiong Ekong as a natural language task management assistant that integrates Discord communication with ClickUp project management workflows.
