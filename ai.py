from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def summarizeConversation(transcript: str):
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content":
                """
                You are a project management assistant.

                Summarize the discussion.

                Include:
                - Main topics
                - Decisions made
                - Open questions
                - Action items

                Keep it concise.
                """
            },
            {
                "role": "user",
                "content": transcript
            }
        ]
    )

    return response.choices[0].message.content