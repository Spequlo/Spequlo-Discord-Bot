# Dipersa - Spequlo Discord Bot
# Author - Edidiong Ekong

# need to create modify handlers
# consider using aiohtttp incase multiple users want to use multiple request at the same time.
# when doing modify tasks, add a check in  handler for that only the author of the task can modify it
# Is an unassigned task something I want to support, or should task creation always require an assignee? Right now there's no way to distinguish those two failure cases from the user's side.
# Improve error logging
# add a feature for the bot responding with what it can do

import discord
from discord.ext import commands
import logging 
from dotenv import load_dotenv
import os
from server import *
from help import *
from ai import *

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if DISCORD_TOKEN is None:
    raise ValueError("DISCORD_TOKEN is not set")

CLICKUP_TOKEN_STR = os.getenv("CLICKUP_TOKEN")
if CLICKUP_TOKEN_STR is None:
    raise ValueError("CLICKUP_TOKEN not set")
CLICKUP_TOKEN = str(CLICKUP_TOKEN_STR)

DISCORD_SERVER_ID = os.getenv('DISCORD_SERVER_ID')
if DISCORD_SERVER_ID is None:
    raise ValueError("DISCORD_SERVER_ID is not set")

WORKSPACE_ID_STR = os.getenv('CLICKUP_WORKSPACE_ID')
if WORKSPACE_ID_STR is None:
    raise ValueError("CLICKUP_WORKSPACE_ID is not set")
CLICKUP_WORKSPACE_ID = int(WORKSPACE_ID_STR)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

ServerID = discord.Object(id=int(DISCORD_SERVER_ID))
bot = commands.Bot(command_prefix="!", intents=intents)

pending_status_changes = {}
discussion_summary = {}
bot_context = {}

##  Events
@bot.event
async def on_ready():
    try:
        await bot.tree.sync(guild=ServerID)

        if bot.user is None:
            return
        
        intro_channel = "commands_test"
        embed = discord.Embed(title=f"Hello Guys, {bot.user.name} here", description="I am a discord bot designed for use by the Spequlo Team on discord", color=discord.Color.blue())
        channel_id = getChannel(intro_channel)
        
        if channel_id is None:
            raise ValueError(f"{intro_channel} channel not configured")
        
        channel = await bot.fetch_channel(channel_id)

        if not isinstance(channel, discord.TextChannel):
            raise TypeError(f"{intro_channel} is not a text channel")

        if channel:
            await channel.send(embed=embed)
        
        print("Ready!!!")
    except Exception as e:
        print(f"Startup Error: {e}")

@bot.event
async def on_message(message):
    if bot.user is None:
        return

    if message.author == bot.user:
        return

    is_mention = bot.user in message.mentions
    is_reply_to_bot = False
    metadata = None
    referenced_message = message.reference.resolved if message.reference else None

    if message.reference and referenced_message is None:
        try:
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
        except discord.NotFound:
            referenced_message = None
    
    if referenced_message:
        print(f"Reply context found: {bot_context.get(referenced_message.id)}")
        metadata = bot_context.get(referenced_message.id)
        is_reply_to_bot = (referenced_message.author.id == bot.user.id)

    if not is_mention and not is_reply_to_bot:
        return

    content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()

    if not content:
        await message.reply("Hello! 👋")
        return
    
    request_context = {"current_message": content, "referenced_message": referenced_message.content if referenced_message else None, "metadata": metadata}
    assignee_id, assignee_name = findAssignee(message, bot.user)

    try:
        result = classifyIntent(request_context, message.author.id, message.author.display_name, assignee_id, assignee_name)
        intent = result["intent"]
        confidence = result["confidence"]
        params = result["params"]

        print(f"[handleRequest] intent={intent} confidence={confidence} params={params}")

        if confidence == "low" or intent == "unclear":
            question = result.get("clarifying_question") or "I'm not sure what you'd like me to do — could you clarify?"
            bot_message = await message.reply(question)
            bot_context[bot_message.id] = {"conversation_type": "clarification", "original_result": result}
            return
        
        request_handlers = {
            "view_tasks": viewTasksHandler,
            "create_task": createTaskHandler,
            "modify_task": modifyTaskHandler,
            "summarize_conversation": summarizeConversationHandler,
        }

        if intent == "summarize_conversation":
            params["transcript"] = await buildTranscript(message, params)

        handler = request_handlers.get(intent)

        if handler is None:
            await message.reply("I understood the intent but don't have a handler for it yet.")
            return

        result = handler(params, CLICKUP_TOKEN)
        if not isinstance(result, dict):
            raise RuntimeError(f"Handler {intent} returned invalid result")
        
        bot_message = await message.reply(result["message"])
        bot_context[bot_message.id] = {
            "intent": intent,
            "requester_discord_id": message.author.id,
            **result.get("metadata", {})
        }

    except RuntimeError as e:
        if str(e) == "RATE_LIMIT":
            await message.reply("Gemini is currently rate-limiting requests. Please try again in a moment.")
            return
        elif str(e) == "SERVICE_UNAVAILABLE":
            await message.reply("Gemini is temporarily unavailable. Please try again later.")
            return
        elif str(e) == "QUOTA_EXCEEDED":
            await message.reply("Gemini free-tier quota exhausted. Please try again later.")
            return
    except Exception as e:
        print(e)
        await message.reply(f"⚠️ Couldn't process that right now ({e}). Try again shortly.")
        return

# Commands
@bot.tree.command(name="help", description="Display all Bot Comands", guild=ServerID)
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Dipersa Commands and Info", description="Here are all the manual commands I have and their descriptions.", color=discord.Color.blue())
    embed.add_field(name="/signup", value="Connect your Discord user to your CLickUp user in the Spequlo Workspace", inline=False)
    embed.add_field(name="/help", value="Display all the bot commands", inline=False)
    embed.set_footer(text="Thank you for using Dipersa.")   

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="signup", description="Connect your discord user to ClickUp", guild=ServerID)
async def signUp(interaction: discord.Interaction, id: int):
    user = interaction.user
    member = getMember(user.id)

    if member:
        embed = discord.Embed(title=f"You already signed up.", description="You're already a member on clickup", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    
    if validateClickUp(CLICKUP_WORKSPACE_ID, CLICKUP_TOKEN, id):
        addMember(user.id, id)
        embed = discord.Embed(title="You are signed into ClickUp.", description=f"{user.mention}, you can now assign and view your assigned tasks", color=discord.Color.green())       
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(title="I couldn't find you on ClickUp", description=f"{user.mention}, Be sure you used the right ClickUp ID!", color=discord.Color.red())       
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="change-status", description="Change the status of one of your tasks", guild=ServerID)
async def changeStatus(interaction: discord.Interaction, task_number: int):
    await interaction.response.defer()
    user = interaction.user

    try:
        my_tasks = getCachedTasks(CLICKUP_TOKEN, user.id)
    except Exception as e:
        await interaction.followup.send(str(e))
        return
    
    if task_number < 1 or task_number > len(my_tasks):
        await interaction.followup.send(f" Invalid task number. You have {len(my_tasks)} tasks — pick a number between 1 and {len(my_tasks)}.")
        return

    selected_task = my_tasks[task_number - 1]

    statuses = getListStatuses(CLICKUP_TOKEN, selected_task["list_id"])

    if statuses == 401:
        await interaction.followup.send("Couldn't fetch statuses for that task's list. Please contact a dev.")
        return

    pending_status_changes[user.id] = {
        "task": selected_task,
        "statuses": statuses
    }

    status_list = "\n".join(f"**{i + 1}.** {s}" for i, s in enumerate(statuses))
    await interaction.followup.send(
        f"**Changing status for:** {selected_task['task_name']}\n"
        f"**Current status:** {selected_task['status']}\n"
        f"\n**Available statuses:**\n{status_list}\n"
        f"\nUse `/confirmstatus <number>` to confirm."
    )

@bot.tree.command(name="confirm-status", description="Confirm the new status for your task", guild=ServerID)
async def confirmStatus(interaction: discord.Interaction, status_number: int):
    await interaction.response.defer()
    user = interaction.user

    if user.id not in pending_status_changes:
        await interaction.followup.send("No pending status change found. Use `/changestatus` first.")
        return

    pending = pending_status_changes[user.id]
    statuses = pending["statuses"]
    task = pending["task"]

    if status_number < 1 or status_number > len(statuses):
        await interaction.followup.send(f"Invalid status number. Pick a number between 1 and {len(statuses)}.")
        return

    new_status = statuses[status_number - 1]

    try:
        result = updateTaskStatus(CLICKUP_TOKEN, task["task_id"], new_status)
    except Exception as e:
        await interaction.followup.send(str(e))
        return
    
    del pending_status_changes[user.id]
    invalidateTaskCache(user.id)

    await interaction.followup.send(
        f"**Status updated!**\n"
        f"**Task:** {task['task_name']}\n"
        f"**New status:** {new_status}"
    )

bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)

async def buildTranscript(message, params):
    mode = params.get("mode", "count")
    raw_messages = []

    def format_message(msg):
        content = msg.content.strip()

        if msg.attachments:
            attachment_names = ", ".join(attachment.filename for attachment in msg.attachments)
            content += f" [Attachments: {attachment_names}]"

        if msg.reference:
            content = f"[Reply] {content}"

        return (f"{msg.created_at.strftime('%Y-%m-%d %H:%M')} - {msg.author.id} ({msg.author.display_name}): {content}")

    if mode == "timeframe":
        cutoff = parseTimeframe(params.get("timeframe"))

        async for msg in message.channel.history(after=cutoff, limit=1000):
            if msg.content.strip() or msg.attachments:
                raw_messages.append(format_message(msg))
    elif mode == "anchor":
        if not message.reference:
            return None

        anchor = await message.channel.fetch_message(message.reference.message_id)

        async for msg in message.channel.history(after=anchor, limit=1000):
            if msg.content.strip() or msg.attachments:
                raw_messages.append(format_message(msg))
    else:
        count = int(params.get("count") or 100)

        async for msg in message.channel.history(limit=count):
            if msg.content.strip() or msg.attachments:
                raw_messages.append(format_message(msg))

    raw_messages.reverse()

    return "\n".join(raw_messages)