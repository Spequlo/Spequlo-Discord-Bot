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
        return 402

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
                print(f"No list ID found for {team}/{list}")
                return "NO-ID"
            url = f"https://api.clickup.com/api/v2/list/{int(listId)}/task"
            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Error fetching {team}/{list}: {response.status_code} - {response.text}")
                return 401

            data = response.json()
            if "tasks" in data:
                allTasks.extend(data["tasks"])
    if not allTasks:
        return "EMPTY"

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
        return 401
    
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

def formatSummary(result: dict) -> str:

    participants = "\n".join(f"• {p}" for p in result["participants"])

    tasks = ""

    for i, task in enumerate(result["tasks"], start=1):
        tasks += (
            f"\n{i}. {task['name']}\n"
            f"   Assigned: {task['assignee_name']}\n"
            f"   Priority: {task['priority']}\n"
            f"   Details: {task['description']}\n"
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

