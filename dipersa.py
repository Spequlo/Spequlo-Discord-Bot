# Dipersa - Spequlo Discord Bot
# Author - Edidiong Ekong

#  Is an unassigned task something you want to support, or should task creation always require an assignee? Right now there's no way to distinguish those two failure cases from the user's side.
# consider using aiohtttp incase multiple users want to use multiple request at the same time.
# when doing modify tasks, add a check in  handler for that only the author of the task can modify it

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import checks
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
    if not is_mention and not message.reference:
        return
    
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

    if not is_reply_to_bot:
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
            "change_status": changeStatusHandler,
            "summarize_conversation": summarizeConversationHandler,
            "modify_task": modifyTaskHandler
        }

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
    embed = discord.Embed(title="Dipersa Commands and Info", description="Here are all the commands I have and their descriptions.", color=discord.Color.blue())
    embed.add_field(name="/signup", value="Connect your Discord user to your CLickUp user in the Spequlo Workspace", inline=False)
    embed.add_field( name="/assign-manual", value="Manually assign a task to a user on ClickUp.", inline=False)
    embed.add_field(name="/view-my-tasks", value="Get a list of all your tasks and their progress.", inline=False)
    embed.add_field(name="/change-status", value="Change the status of one of your tasks.", inline=False)
    embed.add_field(name="/confirm-status", value="Confirm the new status for a selected task.", inline=False)
    embed.add_field(name="/summarize", value="Summarize and create tasks from discord conversations over a timeframe using AI.", inline=False)
    embed.add_field(name="/revise-summary", value="Regenerate the created summary and tasks using user feedback.", inline=False)
    embed.add_field(name="/create-tasks", value="Confirm the creation of the AI genrated tasks on ClickUp.", inline=False)
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

@bot.tree.command(name="assign-manual", description="Manually assign a task to a user on ClickUp", guild=ServerID)
@app_commands.choices(
    team=[    
        app_commands.Choice(name="Mobile App", value="mobile_app"),
        app_commands.Choice(name="Integration", value="integration"),
        app_commands.Choice(name="Internal Tools", value="internal_tools"),
        app_commands.Choice(name="Infrastructure", value="infrastructure"),
        app_commands.Choice(name="Website", value="website")
    ],
    list=[
        app_commands.Choice(name="Backlog", value="backlog"),
        app_commands.Choice(name="Current Sprint", value="current_sprint"),
        app_commands.Choice(name="Bugs", value="bugs")
    ],
    priority=[
        app_commands.Choice(name="Urgent", value="1"),
        app_commands.Choice(name="High", value="2"),
        app_commands.Choice(name="Normal", value="3"),
        app_commands.Choice(name="Low", value="4")
    ]
)
async def assignManual(interaction: discord.Interaction, user: discord.Member, task: str, team: str, list: str, priority: str, desc: str = ""): 
    if team == "website":
        list_value = getListId("website", "list")
    else:
        list_value = getListId(team, list)

    if list_value is None:
        raise ValueError(f"List ID not found for {team}")

    list_id = int(list_value)

    code = createTask(CLICKUP_TOKEN, user.id, task, list_id, int(priority), desc)

    #Change all these errors to be excpetions

    if code == 401:
        embed = discord.Embed(title="I couldn't find the list or space", description=f"{user.mention}. It looks like the list you wanted doesn't exist. Please contact the ClickUp Workspace Admin", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    if code == 402:
        embed = discord.Embed(title=f"{user.name} needs to sign up first", description=f"Please get {user.mention} to sign up with me using the `/signup` command.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    
    if code == 200:
        embed = discord.Embed(title=f"Task Successfully Created", description=f"{task}.", color=discord.Color.green())
        embed.add_field(name="Assigned to", value=f"{user.mention}")
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(title=f"Error assigning the Task", description="Looks like there was an error while trying to assign the task. Please contact a dev.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="view-my-tasks", description="Get a list of all your tasks and their progress", guild=ServerID)
@app_commands.choices(
    team=[    
        app_commands.Choice(name="Mobile App", value="mobile_app"),
        app_commands.Choice(name="Integration", value="integration"),
        app_commands.Choice(name="Internal Tools", value="internal_tools"),
        app_commands.Choice(name="Infrastructure", value="infrastructure"),
        app_commands.Choice(name="Website", value="website")
    ],
    list_name=[
        app_commands.Choice(name="Backlog", value="backlog"),
        app_commands.Choice(name="Current Sprint", value="current_sprint"),
        app_commands.Choice(name="Bugs", value="bugs")
    ]
)
async def viewMyTasks(interaction: discord.Interaction, team: str = "", list_name: str = ""): 
    await interaction.response.defer() 
    user = interaction.user

    my_tasks = getCachedTasks(CLICKUP_TOKEN, user.id, team, list_name)
    try:
        my_tasks = getCachedTasks(CLICKUP_TOKEN, user.id, team, list_name)
    except Exception as e:
        await interaction.followup.send(str(e))
        return
    
    messages = []
    header = f"**Tasks for {user.mention}**\n"
    current_message = header

    for i, task in enumerate(my_tasks):
        assignees = " ".join(f"<@{getMemberDiscord(a)}>" for a in task["assignees"])
        creator = f"<@{getMemberDiscord(task["creator_id"])}>"

        task_text = (
            f"\n**Task {i + 1} — {task['task_name']}**\n"
            f"**Team:** {task['folder']}\n"
            f"**List:** {task['list']}\n"
            f"**Status:** {task['status']}\n"
            f"**Priority:** {task['priority']}\n"
            f"**Deadline:** {task['deadline']}\n"
            f"**Created By:** {creator}\n"
            f"**Assigned To:** {assignees}\n"
        )

        if len(current_message) + len(task_text) > 1900:
            messages.append(current_message)
            current_message = task_text
        else:
            current_message += task_text

    if current_message:
        messages.append(current_message)

    for message in messages:
        await interaction.followup.send(message)   

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

@bot.tree.command(name="summarize", description="Summarize recent messages", guild=ServerID)
@checks.cooldown(1, 15.0)
async def summarize(interaction: discord.Interaction, timeframe: str = "30m", context: str = ""):
    await interaction.response.defer()
    user = interaction.user
    channel = interaction.channel

    if channel is None:
        await interaction.followup.send("No channel found.")
        return
    
    if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
        await interaction.followup.send("This command can only be used in a text channel.")
        return

    try:
        cutoff = parseTimeframe(timeframe)
    except ValueError:
        await interaction.followup.send("Invalid timeframe. Use this format: 30m, 2h, 1d")
        return
    
    messages = []

    async for msg in channel.history(after=cutoff, limit=1000): 
        if msg.author.bot:
            continue

        content = msg.content.strip()

        if not content:
            continue

        messages.append(f"{msg.created_at.strftime('%H:%M')} - {msg.author.id} ({msg.author.display_name}): {content}")
        
    if not messages:
        await interaction.followup.send(f"No messages found in the last {timeframe}")
        return

    messages.reverse()
    transcript = "\n".join(messages)

    result = None
    try:
        result = summarizeTranscript(transcript[-12000:], context)
    except RuntimeError as e:
        if str(e) == "RATE_LIMIT":
            await interaction.followup.send("Gemini is currently rate-limiting requests. Please try again in a moment.")
            return
        elif str(e) == "SERVICE_UNAVAILABLE":
            await interaction.followup.send("Gemini is temporarily unavailable. Please try again later.")
            return
        elif str(e) == "QUOTA_EXCEEDED":
            await interaction.followup.send("Gemini free-tier quota exhausted. Please try again later.")
            return
    except Exception as e:
        print(e)
        await interaction.followup.send("Failed to generate summary.")
        return
    
    if result is None:
        await interaction.followup.send("Failed to generate summary.")
        return
        
    cache_key = (user.id, channel.id)
    discussion_summary[cache_key] = {
        "transcript": transcript,
        "summary": result["summary"],
        "tasks": result["tasks"],
        "participants": result.get("participants", []),
        "confidence": result.get("confidence", {})
    }

    await interaction.followup.send(formatSummary(result))

@bot.tree.command(name="revise-summary", description="Regenerate the created summary", guild=ServerID)
@checks.cooldown(1, 15.0)
async def reviseSummary(interaction: discord.Interaction, feedback: str):
    await interaction.response.defer()
    user = interaction.user
    channel = interaction.channel
    if channel is None:
        await interaction.followup.send("No channel found.")
        return
        
    cache_key = (user.id, channel.id)
    data = discussion_summary.get(cache_key)

    if not data:
        await interaction.followup.send("No summary found. Run `/summarize` first")
        return

    transcript = data["transcript"]
    old_summary = data["summary"]

    new_summary = None

    try:
        new_summary = regenerateSummary(old_summary, transcript[-12000:], feedback)
    except RuntimeError as e:
        if str(e) == "RATE_LIMIT":
            await interaction.followup.send("Gemini is currently rate-limiting requests. Please try again in a moment.")
            return
        elif str(e) == "SERVICE_UNAVAILABLE":
            await interaction.followup.send("Gemini is temporarily unavailable. Please try again later.")
            return
        elif str(e) == "QUOTA_EXCEEDED":
            await interaction.followup.send("Gemini free-tier quota exhausted. Please try again later.")
            return
    except Exception as e:
        print(e)
        await interaction.followup.send("Failed to generate summary.")
        return
    
    if new_summary is None:
        await interaction.followup.send("Failed to generate summary.")
        return
    
    discussion_summary[cache_key] = {
        "transcript": transcript,
        "summary": new_summary["summary"],
        "tasks": new_summary["tasks"],
        "participants": new_summary.get("participants", []),
        "confidence": new_summary.get("confidence", {})
    }

    await interaction.followup.send(formatSummary(new_summary))

@bot.tree.command(name="create-tasks", description="Create tasks from a discussion summary", guild=ServerID)
@app_commands.choices(
    team=[    
        app_commands.Choice(name="Mobile App", value="mobile_app"),
        app_commands.Choice(name="Integration", value="integration"),
        app_commands.Choice(name="Internal Tools", value="internal_tools"),
        app_commands.Choice(name="Infrastructure", value="infrastructure"),
        app_commands.Choice(name="Website", value="website")
    ],
    list=[
        app_commands.Choice(name="Backlog", value="backlog"),
        app_commands.Choice(name="Current Sprint", value="current_sprint"),
        app_commands.Choice(name="Bugs", value="bugs")
    ]
)
async def createTasks(interaction: discord.Interaction, team: str, list: str):
    await interaction.response.defer()
    user = interaction.user
    channel = interaction.channel
    if channel is None:
        await interaction.followup.send("No channel found.")
        return
    
    session = discussion_summary.get((user.id, channel.id))

    if not session:
        await interaction.followup.send("No discussion summary found. Run `/summarize` first.")
        return

    created = 0
    failed = []

    if team == "website":
        list_value = getListId("website", "list")
    else:
        list_value = getListId(team, list)

    if list_value is None:
        raise ValueError(f"List ID not found for {team}")

    list_id = int(list_value)

    if list_id == 401:
        await interaction.followup.send("Could not find the specified list.")
        return

    for task in session["tasks"]:
        discord_id = task["assignee_discord_id"]
        
        if not discord_id:
            failed.append(f"{task['name']} (No assignee)")
            continue

        code = createTask(CLICKUP_TOKEN, discord_id, task["name"], list_id, task["priority"], task["description"])
        if code == 200:
            created += 1
        else:
            failed.append(f"{task['name']} (Error {code})")

    message = (f"Created {created} task(s)\n")

    if failed:
        message += ("\nFailed:\n" + "\n".join(failed))

    await interaction.followup.send(message)

bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)
