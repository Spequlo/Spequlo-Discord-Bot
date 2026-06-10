# Dipersa - Spequlo Discord Bot
# Author - Edidiong Ekong

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import checks
import logging 
from dotenv import load_dotenv
import os
import json
from server import *
from help import *
from ai import *
from google.genai.errors import ClientError

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CLICKUP_TOKEN = os.getenv('CLICKUP_TOKEN')
DISCORD__SERVER_ID = os.getenv('DISCORD_SERVER_ID')
CLICKUP_WORKSPACE_ID = os.getenv('CLICKUP_WORKSPACE_ID')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

ServerID = discord.Object(id=int(DISCORD__SERVER_ID))
bot = commands.Bot(command_prefix="!", intents=intents)

pending_status_changes = {}
discussion_summary = {}

##  Events
@bot.event
async def on_ready():
    try:
        await bot.tree.sync(guild=ServerID)
        embed = discord.Embed(title=f"Hello Guys, {bot.user.name} here", description="I am a discord bot designed for use by the Spequlo Team on discord", color=discord.Color.blue())
        channel = await bot.fetch_channel(getChannel("commands_test"))
        if channel:
            await channel.send(embed=embed)
        print("Ready!!!")
    except Exception as e:
        print(f"Startup Error: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.lower().startswith('hello'):
        await message.channel.send('Hello!')
    if message.content.lower().startswith('nice'):
        await message.channel.send('very nice')

# Commands
@bot.tree.command(name="signup", description="Connect your discord user to ClickUp", guild=ServerID)
async def signUp(interaction: discord.Interaction, id: int):
    user = interaction.user
    clickup_member_entry = {str(user.id): int(id)}

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
 
@bot.tree.command(name="assignme", description="Assign yourself a task on ClickUp", guild=ServerID)
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
async def assignMe(interaction: discord.Interaction, task: str, team: str, list: str, priority: str, desc: str = ""):
    user = interaction.user
    if team == "website": 
        list_id = int(getListId("website", "list"))
    else:
        list_id = int(getListId(team, list))

    code = createTask(CLICKUP_TOKEN, user.id, task, list_id, int(priority), desc)

    if code == 401:
        embed = discord.Embed(title="I couldn't find the list", description=f"{user.mention}. It looks like the list you wanted doesn't exist. Please contact the ClickUp Workspace Admin", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    if code == 402:
        embed = discord.Embed(title="You need to sign up first", description=f"{user.mention}, you haven't signed up to ClickUp with me yet. Use the `/signup` command", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    
    if code == 200:
        embed = discord.Embed(title=f"Task Successfully Created", description=f"{task}.", color=discord.Color.green())
        embed.add_field(name="Assigned to", value=f"{user.mention}")
        await interaction.response.send_message(embed=embed)
        return
    
    embed = discord.Embed(title=f"Error assigning the Task", description="Looks like there was an error while trying to assign the task. Please contact a dev.", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="assign", description="Assign a user a task on ClickUp", guild=ServerID)
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
async def assign(interaction: discord.Interaction, user: discord.Member, task: str, team: str, list: str, priority: str, desc: str = ""): 
    if team == "website": 
        list_id = int(getListId("website", "list"))
    else:
        list_id = int(getListId(team, list))
    
    code = createTask(CLICKUP_TOKEN, user.id, task, list_id, int(priority), desc)

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

@bot.tree.command(name="viewmytasks", description="Assign a user a task on ClickUp", guild=ServerID)
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


    if my_tasks == 401:
        embed = discord.Embed(title=f"Error Fetching Tasks", description="Looks like there was an error while trying to retrieve your tasks. Please contact a dev.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    if my_tasks == 402:
        embed = discord.Embed(title=f"{user.name} needs to sign up first", description=f"Please get {user.mention} to sign up with me using the /signup command.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return
    
    if my_tasks == "EMPTY":
        embed = discord.Embed(title=f"No Tasks Found", description=f"There are no tasks assigned to you", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return
    
    if my_tasks == "NO-ID":
        embed = discord.Embed(title=f"No List Found", description=f"I couldn't find the list you were looking for. Please contact the CLickUp Admin", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
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

@bot.tree.command(name="changestatus", description="Change the status of one of your tasks", guild=ServerID)
async def changeStatus(interaction: discord.Interaction, task_number: int):
    await interaction.response.defer()
    user = interaction.user

    my_tasks = getCachedTasks(CLICKUP_TOKEN, user.id)

    if my_tasks in [401, 402, "EMPTY", "NO-ID"]:
        await interaction.followup.send("Couldn't retrieve your tasks. Make sure you're signed up and have tasks assigned to you.")
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

@bot.tree.command(name="confirmstatus", description="Confirm the new status for your task", guild=ServerID)
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

    result = updateTaskStatus(CLICKUP_TOKEN, task["task_id"], new_status)

    if result == 401:
        await interaction.followup.send("Failed to update the task status. Please contact a dev.")
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
    channel = interaction.channel #Currently uses interaction.channel to get the current channel, later need to add ability to select channel
    
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

    try:
        result = summarizeTranscript(transcript[-12000:], context)
    except ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            await interaction.followup.send("Gemini free-tier quota exhausted. Please try again later.")
            return
    except Exception as e:
        print(e)
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

@bot.tree.command(name="revisesummary", description="Regenerate the created summary", guild=ServerID)
@checks.cooldown(1, 15.0)
async def reviseSummary(interaction: discord.Interaction, feedback: str):
    await interaction.response.defer()
    user = interaction.user
    channel = interaction.channel
    cache_key = (user.id, channel.id)

    data = discussion_summary.get(cache_key)

    if not data:
        await interaction.followup.send("No summary found. Run `/summarize` first")
        return

    transcript = data["transcript"]
    old_summary = data["summary"]

    try:
        new_summary = regenerateSummary(old_summary, transcript[-12000:], feedback)
    except ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            await interaction.followup.send("Gemini free-tier quota exhausted. Please try again later.")
            return
    except Exception as e:
        print(e)
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

@bot.tree.command(name="createtasks", description="Create tasks from a discussion summary", guild=ServerID)
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
    session = discussion_summary.get((user.id, channel.id))

    if not session:
        await interaction.followup.send("No discussion summary found. Run `/summarize` first.")
        return

    created = 0
    failed = []

    if team == "website": 
        list_id = int(getListId("website", "list"))
    else:
        list_id = int(getListId(team, list))

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
