import requests

def createTask(task_data, LIST_ID: int, TOKEN: str):
    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"

    headers = {
        "Authorization": TOKEN,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=task_data, headers=headers)
    print(response.status_code) 
    print(response.json())

    return response.status_code

