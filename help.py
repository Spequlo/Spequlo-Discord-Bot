import requests
from server import *

def createTask(LIST_ID: int, TOKEN: str, userID: int, task: str, priority: int, desc: str = "."):
    member = getMember(userID)

    if not member:
        return 401

    task_data = {
        "name": str(task),
        "description": str(desc),
        "priority": int(priority),
        "status": "to do",
        "assignees": [int(member["clickup_id"])]
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

# def getTasks(LIST_ID: int, TOKEN: str, id: int):
#     url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"

#     headers = {
#         "Authorization": TOKEN
#     }

#     params = {
#         "assignees[]": id
#     }

#     response = requests.get(url, headers=headers, params=params)
#     data = response.json()
#     if response.status_code != 200:
#         print(data)
#         return
    
#     tasks = data["tasks"]
#     return tasks
