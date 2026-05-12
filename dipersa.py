# Dipersa - Spequlo Discord Bot
# Author - Edidiong Ekong

import discord
from discord.ext import commands
from discord import app_commands
import logging 
from dotenv import load_dotenv
import os
from server import *
from help import createTask, validateClickUp

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CLICKUP_TOKEN = os.getenv('CLICKUP_TOKEN')
DISCORD__SERVER_ID = os.getenv('DISCORD_SERVER_ID')
CLICKUP_WORKSPACE_ID = os.getenv('CLICKUP_WORKSPACE_ID')
CLICKUP_LIST_ID = os.getenv('CLICKUP_LIST_ID')

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
        channel = await bot.fetch_channel(getChannel("commands"))
        if channel:
            await channel.send(embed=embed)
        print("Ready!!!")
    except Exception as e:
        print(f"Startup Error: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

# @bot.event
# async def on_member_join(member):
#     with open('channels.json', 'r') as file:
#         data = json.load(file)
#     channel = bot.get_channel(data["welcome"])
#     if channel:
#         await channel.send(f"Hey {member.mention}, welcome to the Spequlo server! 🎉")

# Commands
@bot.tree.command(name="signup", description="Connect your discord user to ClickUp", guild=ServerID)
async def signUp(interaction: discord.Interaction, id: int):
    channel_id = getChannel("commands")

    if interaction.channel.id != channel_id:
        embed = discord.Embed(title="Wrong Channel", description="Please use this command in the commands channel.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
   
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
@app_commands.choices(priority=[
    app_commands.Choice(name="Urgent", value=1),
    app_commands.Choice(name="High", value=2),
    app_commands.Choice(name="Normal", value=3),
    app_commands.Choice(name="Low", value=4)
])
async def assignMe(interaction: discord.Interaction, task: str, priority: int, desc: str=""): #add status as a drop down, add priority as a drop down
    user = interaction.user
    code = createTask(CLICKUP_LIST_ID, CLICKUP_TOKEN, user.id, task, priority, desc)

    channel_id = getChannel("commands")

    if interaction.channel.id != channel_id:
        embed = discord.Embed(title="Wrong Channel", description="Please use this command in the commands channel.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
   
    if code == 401:
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
@app_commands.describe(user="The user you want to assign task to")
@app_commands.choices(priority=[
    app_commands.Choice(name="Urgent", value=1),
    app_commands.Choice(name="High", value=2),
    app_commands.Choice(name="Normal", value=3),
    app_commands.Choice(name="Low", value=4)
])
async def assign(interaction: discord.Interaction, user: discord.Member, task: str, priority: int, desc: str = ""): #add status as a drop down, add priority as a drop down
    code = createTask(CLICKUP_LIST_ID, CLICKUP_TOKEN, user.id, task, priority, desc)

    channel_id = getChannel("commands")

    if interaction.channel.id != channel_id:
        embed = discord.Embed(title="Wrong Channel", description="Please use this command in the commands channel.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
   
    if code == 401:
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

bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)

