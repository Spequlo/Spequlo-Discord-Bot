import discord
from discord.ext import commands
import logging 
from dotenv import load_dotenv
import os
import json
import requests

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CLICKUP_TOKEN = os.getenv('CLICKUP_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
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

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

@bot.command()
async def signup(ctx, id):
    clickup_member = {str(ctx.author.id): int(id)}

    with open('members.json', 'r+') as file:
        data = json.load(file)

    if str(ctx.author.id) in data:
        await ctx.send("You already signed up.")
        return

    data.update(clickup_member)

    with open('members.json', 'w') as file:
        json.dump(data, file, indent=4)

    with open('channels.json', 'r') as file:
        data = json.load(file)

    channel = bot.get_channel(data["test"])
    if channel:
        await channel.send(f"Signed {ctx.author.mention} into ClickUp!")


LIST_ID = "901415911900"
url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task"

headers = {
    "Authorization": CLICKUP_TOKEN,
    "Content-Type": "application/json"
}


# @bot.command()
# async def assignself(ctx):
#     pass

@bot.command()
async def assignself(ctx, task):
    with open('members.json', 'r') as file:
        members = json.load(file)

    if str(ctx.author.id) not in members:
        await ctx.send("You need to sign up first.")
        return

    task_data = {
        "name": str(task),
        "description": "This task was created using Python",
        "priority": 3,  # 1=urgent, 2=high, 3=normal, 4=low
        "status": "to do",
        "assignees": [int(members[str(ctx.author.id)])]
    }
    response = requests.post(url, json=task_data, headers=headers)
    print(response.status_code) 
    print(response.json())

    if response.status_code == 200:
        await ctx.send(f"Task Successfully Assigned to {ctx.author.mention}!")
    else:
        await ctx.send(f"Failed: {response.status_code}")


bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)
