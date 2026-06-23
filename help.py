# import requests
import aiohttp
import time
from server import *
from ai import *
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
 
task_cache = {}
CACHE_TTL = 3600

def findAssignee(message, user) -> tuple[int | None, str | None]:
    mentioned_users = [u for u in message.mentions if u != user]
    if mentioned_users:
        return mentioned_users[0].id, mentioned_users[0].display_name

    if message.reference and message.reference.resolved:
        ref_author = message.reference.resolved.author
        if ref_author != user:
            return ref_author.id, ref_author.display_name

    return None, None

async def validateClickUp(TEAM_ID: int, TOKEN: str, userID: int):
    url = f"https://api.clickup.com/api/v2/team/{TEAM_ID}"
    headers = {"Authorization": TOKEN}
 
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                members = data["team"]["members"]
                for member in members:
                    user_id = member["user"]["id"]
                    if userID == user_id:
                        return True
            return False

def parseTimeframe(timeframe: str):
    if timeframe.lower() == "today":
        now = datetime.now(timezone.utc)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    value = int(timeframe[:-1])
    unit = timeframe[-1].lower()

    if unit == "s":
        return datetime.now(timezone.utc) - timedelta(seconds=value)
    if unit == "m":
        return datetime.now(timezone.utc) - timedelta(minutes=value)
    if unit == "h":
        return datetime.now(timezone.utc) - timedelta(hours=value)
    if unit == "d":
        return datetime.now(timezone.utc) - timedelta(days=value)
    if unit == "w":
        return datetime.now(timezone.utc) - timedelta(weeks=value)

    raise ValueError("Invalid timeframe")

async def viewTasksHandler(params, TOKEN):
    member_id = params["assignee_discord_id"]
    tasks = await _getCachedTasks(TOKEN, member_id)
 
    return {
        "message": f'Here are all your tasks: \n{[t["task_name"] for t in tasks]}',
        "metadata": tasks
    }

async def createTaskHandler(params, TOKEN):
    task_name = params["name"]
    task_desc = params["description"]
    priority = params.get("priority") or 3
    if priority not in (1, 2, 3, 4):
        priority = 3
    assignee_id = params.get("assignee_discord_id")

    if assignee_id is None:
        raise ValueError("Assignee missing")
    if not params["team"]:
        raise ValueError("Team missing")
    if not params["list_name"]:
        raise ValueError("List missing")
    
    list_value = getListId(params["team"], params["list_name"])
    if list_value is None:
        raise ValueError(f"List ID not found!")
    LIST_ID = int(list_value)

    due_date = None
    if params.get("deadline"):
        due_date = _parseDeadline(params["deadline"])

    result = await _createTask(TOKEN, assignee_id, task_name, LIST_ID, int(priority), task_desc, due_date)

    if not result["success"]:
        if result.get("error") == "USER_NOT_FOUND":
            return {
                "message": "I can't find the person you intended to assign this to. Please get them to signup with `/signup`.",
                "metadata": {}
            }
        
        return {
            "message": f"Failed to create task. Error: {result.get('error')}",
            "metadata": {"status_code": result.get("status_code")}
        }

    task = result["data"]

    return {
        "message": f'Created task "{task["name"]}" in {task["project"]["name"]} → {task["list"]["name"]}',
        "metadata": {
            "task_id": task["id"],
            "task_name": task["name"],
            "task_description": task.get("description"),
            "priority": task["priority"]["id"] if task["priority"] else None,
            "status": task["status"]["status"],
            "list_id": task["list"]["id"],
            "team": task["project"]["name"],
            "list_name": task["list"]["name"],
            "url": task["url"],
            "deadline": task.get("due_date"),
            "assignee_discord_id": assignee_id,
            "creator_id": params["requestor_id"]
        }
    }

async def modifyTaskHandler(params, TOKEN):
    creator_id = str(params.get("creator_id"))
    requester_id = str(params.get("requester_discord_id"))

    if creator_id and requester_id != creator_id:
        return {
            "message": "Only the task creator can modify this task.",
            "metadata": {
                "creator_id": creator_id,
                "requester_id": requester_id
            }
        }
    
    changes = params.get("changes", {})

    LIST_ID = None
    if changes.get("team") and changes.get("list_name"):
        list_value = getListId(changes["team"], changes["list_name"])
        if list_value is None:
            return {"message": "I couldn't find that destination list.", "metadata": {}}

    if not await _findTask(TOKEN, params['task_id']):
        create_params = {
            "name": changes.get("name") or params.get("task_name"),
            "description": changes.get("description", ""),
            "priority": changes.get("priority", 3),
            "assignee_discord_id": changes.get("assignee_discord_id"),
            "team": changes.get("team"),
            "list_name": changes.get("list_name"),
            "deadline": changes.get("deadline"),
            "requestor_id": params.get("creator_id")
        }

        result = await createTaskHandler(create_params, TOKEN)
        task_cache.pop(params.get("assignee_discord_id"), None)
        if changes.get("assignee_discord_id"):
            task_cache.pop(changes["assignee_discord_id"], None)
        return result
        
    update_payload = {}
    changes_made = []

    if changes.get("name"):
        update_payload["name"] = str(changes["name"])
        changes_made.append(f"renamed to '{changes['name']}'")

    if changes.get("description"):
        update_payload["description"] = str(changes["description"])
        changes_made.append("description updated")

    if changes.get("assignee_discord_id"):
        clickup_id = getClickUpId(changes["assignee_discord_id"])
        if clickup_id is None:
            return {"message": "USER_NOT_FOUND", "metadata": ""}
        update_payload["assignees"] = [int(clickup_id)]
        changes_made.append(f"assigned to {changes['assignee_name']}")

    if changes.get("priority"):
        update_payload["priority"] = int(changes["priority"])
        priority_map = {"1": "Urgent", "2": "High", "3": "Normal", "4": "Low"}
        changes_made.append(f"priority set to {priority_map.get(str(changes['priority']))}")

    if "deadline" in changes:
        if changes["deadline"] is None:
            update_payload["due_date"] = None
            changes_made.append("deadline removed")
        else:
            update_payload["due_date"] = _parseDeadline(changes["deadline"])
            changes_made.append(f"deadline set to {changes['deadline']}")

    if not update_payload:
        return {"message": "No changes were specified.", "metadata": params}
    
    try:
        result = await _updateTask(TOKEN, params["task_id"], update_payload)
        if LIST_ID:
            move_result = await _moveTask(TOKEN, params["task_id"], LIST_ID)
            if move_result["success"]:
                changes_made.append(f"moved to {changes['team']} → {changes['list_name']}")
            else:
                return {"message": "Task updated but failed to move lists.", "metadata": move_result}
    except Exception as e:
        return {"message": f"Failed to update task: {str(e)}", "metadata": {}}

    task_cache.pop(params.get("assignee_discord_id"), None)
    if changes.get("assignee_discord_id"):
        task_cache.pop(changes["assignee_discord_id"], None)
    return {
        "message": f"✅ Updated task '{params['task_name']}'\n" + "\n".join(f"• {c}" for c in changes_made),
        "metadata": {
            "task_id": params["task_id"],
            "task_name": changes.get("name", params["task_name"]),
            "update_payload": update_payload,
            "changes": changes,
            "update_result": result
        }
    }

async def summarizeConversationHandler(params, TOKEN):
    transcript = params["transcript"]
    result = summarizeTranscript(transcript[-12000:])
 
    summary = result.get("summary", "No summary generated.")
    action_items = result.get("action_items", [])
    open_questions = result.get("open_questions", [])
 
    message = f"## 📝 Conversation Summary\n\n{summary}"
 
    if action_items:
        message += "\n\n### ✅ Action Items"
        for item in action_items:
            message += f"\n• {item}"
 
    if open_questions:
        message += "\n\n### ❓ Open Questions"
        for question in open_questions:
            message += f"\n• {question}"
 
    return {
        "message": message,
        "metadata": {
            "summary_response": result,
            "transcript_length": len(transcript)
        }
    }

async def helpHandler(params, TOKEN):
    return{
        "message": (
            "I can help manage ClickUp tasks. Just tell me what you want :)\n\n"
            "**Examples for how to use me**\n"
            "• @Dipersa create a task to add OAuth support\n"
            "• @Dipersa assign this task to @OnlyRafael\n"
            "• @Dipersa move this to backlog\n"
            "• @Dipersa show my tasks\n"
            "• @Dipersa show @DrexRegion's tasks\n"
            "• @Dipersa summarize the last 50 messages\n"
            "• @Dipersa what did they talk about today\n"
        ),
        "metadata": {}
    }

async def _createTask(TOKEN: str, userID: int, task: str, LIST_ID: int, priority: int, desc: str = "", due_date: int | None = None): 
    member = getClickUpId(userID)

    if not member:
        return {
            "success": False,
            "error": "USER_NOT_FOUND"
        }

    task_data = {
        "name": str(task),
        "description": str(desc),
        "priority": int(priority),
        "assignees": [int(member)]
    }

    if due_date:
        task_data["due_date"] = due_date

    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"

    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=task_data, headers=headers) as response:
                if response.status not in (200, 201):
                    try:
                        error_body = await response.json()
                    except Exception:
                        error_body = await response.text()
 
                    return {
                        "success": False,
                        "status_code": response.status,
                        "error": error_body
                    }
                return {
                    "success": True,
                    "data": await response.json()
                }
    except aiohttp.ClientError as e:
        return {
            "success": False,
            "error": str(e)
        }
       
async def _getTasks(TOKEN: str, userId: int, team: str = "", list: str = ""):
    FOLDERS = ["mobile_app", "integration", "internal_tools", "infrastructure", "website"]
    LISTS = ["backlog", "current_sprint", "bugs"]

    member = getClickUpId(userId)
    if not member:
        raise ValueError("No member found. Ensure you have linked your ClickUp account.")
    
    headers = {"Authorization": TOKEN}
    params = {"assignees[]": [int(member)]}
    allTasks = []

    teams = [team] if team else FOLDERS

    async with aiohttp.ClientSession() as session:
        for team in teams:
            lists = ["list"] if team == "website" else LISTS
            if list:
                lists = [list] if list in lists else []

            for lst in lists:
                listId = getListId(team, lst)
                if not listId:
                    raise ValueError(f"No list ID found for {team}/{list}")
                url = f"https://api.clickup.com/api/v2/list/{int(listId)}/task"
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        text = await response.text()
                        print(f"Error fetching {team}/{list}: {response.status} - {text}")
                        raise PermissionError(f"ClickUp request failed: {response.status}")

                    data = await response.json()
                    if "tasks" in data:
                        allTasks.extend(data["tasks"])
        if not allTasks:
            raise ValueError("You have no assigned tasks.")
        return allTasks

async def _getCachedTasks(token: str, user_id: int, team: str = "", list_name: str = ""):
    cached = task_cache.get(user_id)

    if cached and (time.time() - cached["fetched_at"]) < CACHE_TTL:
        return cached["tasks"]

    tasks = await _getTasks(token, user_id, team, list_name)

    if isinstance(tasks, list):
        task_cache[user_id] = {
            "tasks": list(_simplifyTasks(tasks)),
            "fetched_at": time.time()
        }
        return task_cache[user_id]["tasks"]

    return tasks

def _simplifyTasks(tasks: list):
    simplified = []

    for task in tasks:
        simplified.append({
            "task_id": task["id"],
            "task_name": task["name"],

            "folder": task["folder"]["name"],
            "list": task["list"]["name"],
            "list_id": task["list"]["id"],

            "status": task["status"]["status"],
            "status_id": task["status"]["id"],

            "priority": task["priority"]["priority"] if task["priority"] else None,
            "deadline": task["due_date"],
            "url": task["url"],

            "creator_id": task["creator"]["id"],
            "assignees": [assignee["id"] for assignee in task["assignees"]]
        })

    return simplified

async def _findTask(TOKEN: str, task_id: str):
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers={"Authorization": TOKEN}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return None
            return await response.json()
        
async def _updateTask(TOKEN: str, task_id: int, payload: dict):
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers={
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=payload, headers=headers) as response:
            try:
                body = await response.json()
            except Exception:
                body = {}
 
            return {
                "status_code": response.status,
                "success": response.status == 200,
                "response": body
            }

async def _moveTask(TOKEN: str, TASK_ID: str, LIST_ID: int):
    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task/{TASK_ID}"
    headers={
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    payload = {"list_id": LIST_ID}

    async with aiohttp.ClientSession() as session:
        async with session.put(url, json=payload, headers=headers) as response:
            try:
                body = await response.json()
            except Exception:
                body = {}
 
            return {
                "status_code": response.status,
                "success": response.status == 200,
                "response": body
            }

def _parseDeadline(deadline: str) -> int:
    dt = dateparser.isoparse(deadline)
    if dt.tzinfo is None:
        raise ValueError("Deadline must include timezone information.")
    return int(dt.timestamp() * 1000)
