import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

CLASSIFY_URL : str  = os.getenv("MODAL_CLASSIFY_URL", "")
SUMMARIZE_URL: str = os.getenv("MODAL_SUMMARIZE_URL", "")
timeout = aiohttp.ClientTimeout(total=180)

async def classifyIntent(request: dict, user_id: int, user_name: str, assignee_id, assignee_name) -> dict:
    payload = {
        "request": request,
        "user_id": user_id,
        "user_name": user_name,
        "assignee_id": assignee_id,
        "assignee_name": assignee_name,
    }

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(CLASSIFY_URL, json=payload) as response:
            if response.status != 200:
                error = await response.text()
                _handle_error(response.status, error)
            return await response.json()

async def summarizeTranscript(transcript: str) -> dict:
    payload = {"transcript": transcript}

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(SUMMARIZE_URL, json=payload) as response:
            if response.status != 200:
                error = await response.text()
                _handle_error(response.status, error)
            return await response.json()

def _handle_error(status: int, body: str):
    if status == 429:
        raise RuntimeError("RATE_LIMIT")
    elif status == 503:
        raise RuntimeError("SERVICE_UNAVAILABLE")
    elif status == 500:
        raise RuntimeError("MODEL_ERROR")
    else:
        raise RuntimeError(f"Modal request failed ({status}): {body}")
    