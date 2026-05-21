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
    allTasks = []

    member = getMember(userId)
    if not member:
        return 402

    headers = {"Authorization": TOKEN}
    params = {"assignees[]": [int(member)]}

    if team and list:
        listId = getListId(team, list)
        url = f"https://api.clickup.com/api/v2/list/{listId}/task"
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            tasks = simplifyTasks(data["tasks"])
            return tasks
        else:
            print(f"Error fetching tasks: {response.status_code} - {response.text}")
            return 401

        # for folder in folders:
        # listId1 = getListId(folder, "backlog")
        # listId2 = getListId(folder, "current_sprint")
        # listId3 = getListId(folder, "bugs")

        # url1 = f"https://api.clickup.com/api/v2/list/{listId1}/task"
        # url2 = f"https://api.clickup.com/api/v2/list/{listId2}/task"
        # url3 = f"https://api.clickup.com/api/v2/list/{listId3}/task"
            
        # response1 = requests.get(url1, headers=headers, params=params)
        # response2 = requests.get(url2, headers=headers, params=params)
        # response3 = requests.get(url3, headers=headers, params=params)

        # if response1.status_code != 200:
        #     print(response1.json())
        #     data = response1.json()
        #     if "tasks" in data:
        #         allTasks.extend(data["tasks"])
        #     continue
        # if response2.status_code != 200:
        #     print(response2.json())
        #     data = response2.json()
        #     if "tasks" in data:
        #         allTasks.extend(data["tasks"])
        #     continue
        # if response3.status_code != 200:
        #     print(response3.json())
        #     data = response3.json()
        #     if "tasks" in data:
        #         allTasks.extend(data["tasks"])
        #     continue
    elif list and not team:
        pass
    else:
        pass
    # folders = ["mobile_app, internal tools, integration, internal_tools, infrastructure, website"]
    return allTasks

def simplifyTasks(tasks: list):
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