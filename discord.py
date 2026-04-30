import discord
from discord.ext import commands
import logging 
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f"Hello Guys, {bot.user.name} here")

@bot.event
async def on_member_join(member):
    await member.send(f"Hey {member.name}, thansk for joining us!") #this sends private dm
    # change this to have the bot send it to a welcome channel

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if "hello" in message.content.lower():
        await message.channel.send(f"Hello {message.author.mention}")
    if "how are you" in message.content.lower():
        await message.channel.send("I'm fine, How about you")
    if "shit" in message.content.lower():
        await message.delete()
        await message.channel.send(f"{message.author.mention}. Don't do that")
    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name=new_role)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.mention} is now assigned to {role}")
    else:
        await ctx.send("Role doesn't exist")

@bot.command()
async def remove(ctx):
    role = discord.utils.get(ctx.guild.roles, name=new_role)
    if role:
        await ctx.author.remove_roles(role)
        await ctx.send(f"{ctx.author.mention} is now removed from {role}")
    else:
        await ctx.send("Role doesn't exist")

@bot.command()
@commands.has_role(new_role)
async def secret(ctx):
    await ctx.send("Welcome to the club")
    
@secret.error    
async def secret_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do no thave permission to do that!")
    
@bot.command()    
async def dm(ctx, *, msg):
    await ctx.author.send(f"You said {msg}")
    
@bot.command()    
async def reply(ctx):
    await ctx.reply(f"This is a reply to your message")
    
@bot.command()
async def poll(ctx, *, question):
    embed = discord.Embed(title="New Poll", description=question)
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("❤️")
    await poll_message.add_reaction("💔")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)


# async def hello(message):
#     await message.channel.send("Hello Eddie")