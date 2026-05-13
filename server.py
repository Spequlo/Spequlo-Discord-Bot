from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def getMember(discord_id: int):
    response = supabase.table("discord_members").select("*").eq("discord_id", str(discord_id)).execute()
    if not response.data:
        return None
    return response.data[0]

def addMember(discord_id, clickup_id):
    return supabase.table("discord_members").insert({"discord_id": str(discord_id), "clickup_id": int(clickup_id)}).execute()

def getChannel(channel_type: str):
    response = supabase.table("discord_channels").select("channel_id").eq("channel_type", channel_type).execute()
    if not response.data:
        return None
    return int(response.data[0]["channel_id"])

def addChannel(channel_type, channel_id):
    return supabase.table("discord_channels").insert({"channel_type": channel_type, "channel_id": str(channel_id)}).execute()