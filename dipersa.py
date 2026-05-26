# Dipersa - Spequlo Discord Bot
# Author - Edidiong Ekong

import discord
from discord.ext import commands
from discord import app_commands
import logging 
from dotenv import load_dotenv
import os
from server import *
from help import *

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
        embed = discord.Embed(title="You need to sign up first", description=f"{user.mention}, you haven't signed up to ClickUp with me yet.", color=discord.Color.red())
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
        embed = discord.Embed(title=f"{user.name} needs to sign up first", description=f"Please get {user.mention} to sign up with me using the /signup command.", color=discord.Color.red())
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
    tasks = getTasks(CLICKUP_TOKEN, user.id, team, list_name)

    if tasks == 401:
        embed = discord.Embed(title=f"Error Fetching Tasks", description="Looks like there was an error while trying to retrieve your tasks. Please contact a dev.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    if tasks == 402:
        embed = discord.Embed(title=f"{user.name} needs to sign up first", description=f"Please get {user.mention} to sign up with me using the /signup command.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return
    
    if tasks == "EMPTY":
        embed = discord.Embed(title=f"No Tasks Found", description=f"There are no tasks assigned to you", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return
    
    if tasks == "NO-ID":
        embed = discord.Embed(title=f"No List Found", description=f"I couldn't find the list you were looking for. Please contact the CLickUp Admin", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return
    
    messages = []
    header = f"**Tasks for {user.mention}**\n{'━' * 30}\n"
    current_message = header
    my_tasks = list(simplifyTasks(tasks))

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


bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)
