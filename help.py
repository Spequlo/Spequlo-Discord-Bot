import requests
import time
from server import *
from datetime import datetime, timedelta, timezone

task_cache = {}
CACHE_TTL = 60

def createTask(TOKEN: str, userID: int, task: str, LIST_ID: int, priority: int, desc: str = ""): 
    member = getMember(userID)

    if not member:
        return 402

    task_data = {
        "name": str(task),
        "description": str(desc),
        "priority": priority,
        # "status": "to do",
        "assignees": [int(member)]
    }

    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"

    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=task_data, headers=headers)
    return response.status_code

def validateClickUp(TEAM_ID: int, TOKEN: str, userID: int):
    url = f"https://api.clickup.com/api/v2/team/{TEAM_ID}"
    headers = {
        "Authorization": TOKEN,
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        members = data['team']['members']
        for member in members:
            user_id = member['user']['id']
            if userID == user_id:
                return True     
        return False

def getTasks(TOKEN: str, userId: int, team: str, list: str):
    FOLDERS = ["mobile_app", "integration", "internal_tools", "infrastructure", "website"]
    LISTS = ["backlog", "current_sprint", "bugs"]

    member = getMember(userId)
    if not member:
        raise ValueError("No member found. Ensure you have linked your ClickUp account.")
    
    headers = {"Authorization": TOKEN}
    params = {"assignees[]": [int(member)]}
    allTasks = []

    teams = [team] if team else FOLDERS

    for team in teams:
        lists = ["list"] if team == "website" else LISTS
        if list:
            lists = [list] if list in lists else []

        for lst in lists:
            listId = getListId(team, lst)
            if not listId:
                raise ValueError(f"No list ID found for {team}/{list}")
            url = f"https://api.clickup.com/api/v2/list/{int(listId)}/task"
            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Error fetching {team}/{list}: {response.status_code} - {response.text}")
                raise PermissionError(f"ClickUp request failed: {response.status_code}")

            data = response.json()
            if "tasks" in data:
                allTasks.extend(data["tasks"])
    if not allTasks:
        raise ValueError("You have no assigned tasks.")

    return allTasks

def simplifyTasks(tasks: list):
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

def getListStatuses(TOKEN: str, LIST_ID: str):
    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}"
    headers = {"Authorization": TOKEN}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return 401
    
    data = response.json()
    return [s["status"] for s in data["statuses"]]

def updateTaskStatus(TOKEN: str, TASK_ID: str, new_status: str):
    url = f"https://api.clickup.com/api/v2/task/{TASK_ID}"
    headers = {"Authorization": TOKEN, "Content-Type": "application/json"}
    payload = {"status": new_status}
    response = requests.put(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise PermissionError(f"Failed to update the task status. Please contact a dev. {response.status_code}")
    
    return 200

def getCachedTasks(token: str, user_id: int, team: str = "", list_name: str = ""):
    cached = task_cache.get(user_id)

    if cached and (time.time() - cached["fetched_at"]) < CACHE_TTL:
        return cached["tasks"]

    tasks = getTasks(token, user_id, team, list_name)

    if isinstance(tasks, list):
        task_cache[user_id] = {
            "tasks": list(simplifyTasks(tasks)),
            "fetched_at": time.time()
        }
        return task_cache[user_id]["tasks"]

    return tasks

def invalidateTaskCache(user_id: int):
    task_cache.pop(user_id, None)

def parseTimeframe(timeframe: str):
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

def formatSummary(result: dict):
    participants = "\n".join(f"• {p}" for p in result["participants"])

    tasks = ""

    for i, task in enumerate(result["tasks"], start=1):
        tasks += (
            f"\n{i}. {task['name']}\n"
            f"   Assigned: <@{task['assignee_discord_id']}>\n"
            f"   Details: {task['description']}\n"
            f"   Deadline: {datetime.strptime(task["deadline"], "%Y-%m-%d").strftime("%b %d, %Y") if task["deadline"] else "Not Specified"}"
            f"   Priority: {task['priority']}\n"
        )

    ambiguities = result["confidence"].get("ambiguities", [])
    ambiguity_text = "\n".join(f"• {item}" for item in ambiguities) if ambiguities else "None"

    return (
        f"**Discussion Summary**\n\n"
        f"**Participants**\n"
        f"{participants}\n\n"
        f"**Summary**\n"
        f"{result['summary']}\n\n"
        f"**Action Items**\n"
        f"{tasks if tasks else 'No action items found.'}\n\n"
        f"**Confidence**: {result['confidence']['owner_confidence']}\n\n"
        f"**Ambiguities**\n"
        f"{ambiguity_text}"
    )

def findAssignee(message, user) -> tuple[int | None, str | None]:
    mentioned_users = [u for u in message.mentions if u != user]
    if mentioned_users:
        return mentioned_users[0].id, mentioned_users[0].display_name

    if message.reference and message.reference.resolved:
        ref_author = message.reference.resolved.author
        if ref_author != user:
            return ref_author.id, ref_author.display_name

    return None, None

def viewTasksHandler():
    pass

def createTaskHandler(params, TOKEN):
    task_name = params["task_name"]
    task_desc = params["description"]
    priority = params.get("priority")
    assignee_id = params.get("assignee_discord_id")
    list_value = getListId(params["team"], params["list_name"])
    if list_value is None:
        raise ValueError(f"List ID not found!")
    LIST_ID = int(list_value)

    response = createTask(TOKEN, assignee_id, task_name, LIST_ID, int(priority), task_desc)

    if response == 402:
        return "Assignee is not linked to a ClickUp account."

    if response not in (200, 201):
        return f"ClickUp returned status {response}."
    
    return f"Created task: {task_name}"

def changeStatusHandler():
    pass

def summarizeConversationHandler():
    pass


# async def handleRequest(author_id, display_name, channel_id, guild_id, request, reference):
#     try:
#         result = classifyIntent(request, display_name)
#     except RuntimeError as e:
#         await message_channel(channel_id, f"⚠️ Couldn't process that right now ({e}). Try again shortly.")
#         return

#     intent = result["intent"]
#     confidence = result["confidence"]
#     params = result["params"]

#     print(f"[handleRequest] intent={intent} confidence={confidence} params={params}")

#     if confidence == "low" or intent == "unclear":
#         question = result.get("clarifying_question") or "I'm not sure what you'd like me to do — could you clarify?"
#         await message_channel(channel_id, question)
#         return

#     stub_handlers = {
#         "view_tasks": stub_view_tasks,
#         "create_task": stub_create_task,
#         "change_status": stub_change_status,
#         "analyze_conversation": stub_analyze_conversation,
#     }

#     handler = stub_handlers.get(intent)
#     if handler is None:
#         await message_channel(channel_id, "I understood the intent but don't have a handler for it yet.")
#         return

#     await handler(params, channel_id)

