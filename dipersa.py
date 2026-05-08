# Dipersa - Spequlo Discord Bot
# Author - Edidiong Ekong

import discord
from discord.ext import commands
# from discord import app_commands
import logging 
from dotenv import load_dotenv
import os
import json
# from help import createTask

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CLICKUP_TOKEN = os.getenv('CLICKUP_TOKEN')
DISCORD_ID = os.getenv('DISCORD_SERVER_ID')
CLICKUP_LIST_ID = os.getenv('CLICKUP_LIST_ID')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

ServerID = discord.Object(id=int(DISCORD_ID))

bot = commands.Bot(command_prefix="!", intents=intents)

##  Events
@bot.event
async def on_ready():
    await bot.tree.sync(guild=ServerID)
    embed = discord.Embed(title=f"Hello Guys, {bot.user.name} here", description="I am a discord bot designed for use by the Spequlo Team on discord", color=discord.Color.blue())
    with open('channels.json', 'r') as file:
        data = json.load(file)
        channel = bot.get_channel(data["test"]) #change to commands id
        if channel:
            await channel.send(embed=embed)
    print("Ready!!!")

@bot.event
async def on_member_join(member):
    with open('channels.json', 'r') as file:
        data = json.load(file)
    channel = bot.get_channel(data["welcome"])
    if channel:
        await channel.send(f"Hey {member.mention}, welcome to the Spequlo server! 🎉")

@bot.tree.command(name="signup", description="Connect your discord user to ClickUp", guild=ServerID)
async def signup(interaction: discord.Interaction, id: int):
    user = interaction.user
    clickup_member_entry = {str(user.id): int(id)}

    with open('members.json', 'r') as file:
        data = json.load(file)

    # with open('channels.json', 'r') as file:
    #     channels = json.load(file)
    # if interaction.channel.id != channels["test"]:
    # embed = discord.Embed(
    #     title="Wrong Channel",
    #     description="Please use this command in the commands channel.",
    #     color=discord.Color.red()
    # )

    # await interaction.response.send_message(embed=embed, ephemeral=True)
    # return

    if str(user.id) in data:
        embed = discord.Embed(title=f"You already signed up.", description="You're already a member on clickup", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    data.update(clickup_member_entry)

    with open('members.json', 'w') as file:
        json.dump(data, file, indent=4)

    with open('channels.json', 'r') as file:
        data = json.load(file)

    channel = bot.get_channel(data["test"]) #change to cammands
    if channel:
        embed = discord.Embed(title="You are signed into ClickUp.", description=f"{user.mention}, you can now assign and view your assigned tasks", color=discord.Color.green())
       
           await interaction.response.send_message(embed=embed)

        await channel.send(embed=embed)
        return

# @bot.tree.command(name="assignme", description="Assign yourself a task on ClickUp", guild=ServerID)
# @app_commands.choices(priority=[
#     app_commands.Choice(name="Urgent", value=1),
#     app_commands.Choice(name="High", value=2),
#     app_commands.Choice(name="Normal", value=3),
#     app_commands.Choice(name="Low", value=4)
# ])
# async def assignme(interaction: discord.Interaction, task: str, priority: int, desc: str=""): #add status as a drop down, add priority as a drop down
#     user = interaction.user

#     response = createTask(CLICKUP_LIST_ID, CLICKUP_TOKEN, interaction.user.id, task, priority, desc)

#     if response == 401:
#         await interaction.response.send_message(f"You needs to sign up first {user.mention}.")
#         return

#     embed = discord.Embed(title=f"Task Successfully Created", description=f"{task}.", color=discord.Color.dark_red())
#     embed.add_field(name="Assigned to", value=f"{user.mention}")

#     if response == 200:
#         await interaction.response.send_message(embed=embed)
#     else:
#         await interaction.response.send_message(f"Failed to assign task!")

# @bot.tree.command(name="assign", description="Assign a user a task on ClickUp", guild=ServerID)
# @app_commands.describe(user="The user you want to assign task to")
# @app_commands.choices(priority=[
#     app_commands.Choice(name="Urgent", value=1),
#     app_commands.Choice(name="High", value=2),
#     app_commands.Choice(name="Normal", value=3),
#     app_commands.Choice(name="Low", value=4)
# ])
# async def assign(interaction: discord.Interaction, user: discord.Member, task: str, priority: int, desc: str = "."): #add status as a drop down, add priority as a drop down
#     response = createTask(CLICKUP_LIST_ID, CLICKUP_TOKEN, user.id, task, priority, desc)

#     if response == 401:
#         await interaction.response.send_message(f"{user.mention} needs to sign up first.")
#         return

#     embed = discord.Embed(title=f"Task Successfully Created", description=f"{task}.", color=discord.Color.dark_red())
#     embed.add_field(name="Assigned to", value=f"{user.mention}")

#     if response == 200:
#         await interaction.response.send_message(embed=embed)
#     else:
#         await interaction.response.send_message(f"Failed to assign task!")

# @bot.tree.command(name="test", description="Testing", guild=ServerID)
# async def testi(interaction: discord.Interaction):
#     await interaction.response.send_message("Test Successful")

bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)



