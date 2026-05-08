import discord
from discord.ext import commands
from discord import app_commands
import logging 
from dotenv import load_dotenv
import os
import json
import requests
from help import createTask

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CLICKUP_TOKEN = os.getenv('CLICKUP_TOKEN')

DISCORD_ID = 1498392028378173461
CLICKUP_LIST_ID = 901415911900

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
ServerID = discord.Object(id=DISCORD_ID)

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync(guild=ServerID)
    with open('channels.json', 'r') as file:
        data = json.load(file)
        channel = bot.get_channel(data["test"])
        if channel:
            await channel.send(f"Hello Guys, {bot.user.name} here")
    print(f"Hello Guys, {bot.user.name} here")

@bot.event
async def on_member_join(member):
    with open('channels.json', 'r') as file:
        data = json.load(file)
    channel = bot.get_channel(data["test"])
    if channel:
        await channel.send(f"Hey {member.mention}, welcome to the Spequlo server! 🎉")


@bot.tree.command(name="hello", description="Say hello to Dipersa", guild=ServerID)
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello {interaction.user.mention}")

@bot.tree.command(name="signup", description="Connect your discord user to ClickUp", guild=ServerID)
async def signup(interaction: discord.Interaction, id: int):
    user = interaction.user
    clickup_member = {str(user.id): int(id)}

    with open('members.json', 'r+') as file:
        data = json.load(file)

    if str(user.id) in data:
        await interaction.response.send_message("You already signed up.")
        return

    data.update(clickup_member)

    with open('members.json', 'w') as file:
        json.dump(data, file, indent=4)

    with open('channels.json', 'r') as file:
        data = json.load(file)

    channel = bot.get_channel(data["test"])
    if channel:
        await channel.send(f"Signed {user.mention} into ClickUp!")

@bot.tree.command(name="assignme", description="Assign yourself a task on ClickUp", guild=ServerID)
@app_commands.choices(priority=[
    app_commands.Choice(name="Urgent", value=1),
    app_commands.Choice(name="High", value=2),
    app_commands.Choice(name="Normal", value=3),
    app_commands.Choice(name="Low", value=4)
])
async def assignme(interaction: discord.Interaction, task: str, priority: int, desc: str=""): #add status as a drop down, add priority as a drop down
    user = interaction.user

    with open('members.json', 'r') as file:
        members = json.load(file)

    if str(user.id) not in members:
        await interaction.response.send_message("You need to sign up first.")
        return

    task_data = {
        "name": str(task),
        "description": str(desc),
        "priority": int(priority),
        "status": "to do",
        "assignees": [int(members[str(user.id)])]
    }

    response = createTask(task_data, CLICKUP_LIST_ID, CLICKUP_TOKEN)

    embed = discord.Embed(title=f"Task Successfully Created", description=f"Task: {task}.", color=discord.Color.dark_red())
    embed.add_field(name="Assigned to", value=f"{user.mention}")

    if response == 200:
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Failed to assign task!")

@bot.tree.command(name="assign", description="Assign a user a task on ClickUp", guild=ServerID)
@app_commands.describe(user="The user you want to assign task to")
@app_commands.choices(priority=[
    app_commands.Choice(name="Urgent", value=1),
    app_commands.Choice(name="High", value=2),
    app_commands.Choice(name="Normal", value=3),
    app_commands.Choice(name="Low", value=4)
])
async def assign(interaction: discord.Interaction, user: discord.Member, task: str, priority: int, desc: str = "."): #add status as a drop down, add priority as a drop down
    with open('members.json', 'r') as file:
        members = json.load(file)

    if str(user.id) not in members:
        await interaction.response.send_message(f"{user.mention} needs to sign up first.")
        return

    task_data = {
        "name": str(task),
        "description": str(desc),
        "priority": int(priority),
        "status": "to do",
        "assignees": [int(members[str(user.id)])]
    }

    response = createTask(task_data, CLICKUP_LIST_ID, CLICKUP_TOKEN)

    embed = discord.Embed(title=f"Task Successfully Created", description=f"Task: {task}.", color=discord.Color.dark_red())
    embed.add_field(name="Assigned to", value=f"{user.mention}")

    if response == 200:
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Failed to assign task!")



# def createTask(task_data):
#     url = f"https://api.clickup.com/api/v2/list/{CLICKUP_LIST_ID}/task"

#     headers = {
#         "Authorization": CLICKUP_TOKEN,
#         "Content-Type": "application/json"
#     }

#     response = requests.post(url, json=task_data, headers=headers)
#     print(response.status_code) 
#     print(response.json())

#     return response.status_code

@bot.tree.command(name="test", description="Testing", guild=ServerID)
async def testi(interaction: discord.Interaction):
    await interaction.response.send_message("Test Successful")

bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)



