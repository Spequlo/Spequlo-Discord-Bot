import requests
import json

def createTask(LIST_ID: int, TOKEN: str, userID: int, task: str, priority: int, desc: str = "."):
    with open('members.json', 'r') as file:
        members = json.load(file)

    if str(userID) not in members:
        return 401

    task_data = {
        "name": str(task),
        "description": str(desc),
        "priority": int(priority),
        "status": "to do",
        "assignees": [int(members[str(userID)])]
    }

    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"

    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=task_data, headers=headers)
    # print(response.status_code) 
    # return response.status_code
    return 300

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

