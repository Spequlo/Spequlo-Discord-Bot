import requests
from server import *

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
    FOLDERS = ["mobile_app", "integration", "internal_tools", "infrastructure"]
    LISTS = ["backlog", "current_sprint", "bugs"]

    member = getMember(userId)
    if not member:
        return 402

    headers = {"Authorization": TOKEN}
    params = {"assignees[]": [int(member)]}
    allTasks = []

    teams = [team] if team else FOLDERS
    lists = [list] if list else LISTS

    for team in teams:
        for list in lists:
            listId = getListId(team, list)
            if not listId:
                print(f"No list ID found for {team}/{list}")
                return "NO-ID"
            url = f"https://api.clickup.com/api/v2/list/{int(listId)}/task"
            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                print(f"Error fetching {team}/{list}: {response.status_code} - {response.text}")
                return 401

            data = response.json()
            tasks = _simplifyTasks(data["tasks"])
            # return tasks
            # return
            if "tasks" in data:
                allTasks.extend(tasks)
    if not allTasks:
        return "EMPTY"

    return allTasks

def _simplifyTasks(tasks: list):
    simplified = []

    for task in tasks:
        simplified.append({
            "task_id": task["id"],
            "task_name": task["name"],

            "folder": task["folder"]["name"],
            "list": task["list"]["name"],

            "status": task["status"]["status"],
            "priority": task["priority"]["priority"] if task["priority"] else None,
            "deadline": task["due_date"],

            "creator_id": task["creator"]["id"],
            "assignees": [assignee["id"] for assignee in task["assignees"]]
        })

    return simplified

