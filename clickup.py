import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv('CLICKUP_TOKEN')
LIST_ID = "901415911900"

url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"

headers = {
    "Authorization": API_TOKEN,
    "Content-Type": "application/json"
}

data = {
    "name": "My First API Task",
    "description": "This task was created using Python",
    "priority": 3,  # 1=urgent, 2=high, 3=normal, 4=low
    "status": "to do"
}

response = requests.post(url, json=data, headers=headers)

print(response.status_code)
print(response.json())