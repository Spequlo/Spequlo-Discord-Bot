# Dipersa - Spequlo Discord Bot
# Author - Edidiong Ekong

# consider using aiohtttp incase multiple users want to use multiple request at the same time.
# run through the code base for refactoring, particularly with metadata restructuring to ensure contet is preserved. Need to restructure the meta data and cache better to persist more cleanly.
# Need to us a uniform data structure and names crross all achesc, metadata, and json llm outputs.
# add a task check for modify task where the user has to have the bot grab all their tasks first, before being able to modify unless the task already exists in the bots cache or metadata.

import discord
from discord.ext import commands
import logging 
from help import *

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
        # print(f"Reply context found: {bot_context.get(referenced_message.id)}")
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

    thinking_message = await message.reply("⏳ Processing your request...")

    try:
        result = await classifyIntent(request_context, message.author.id, message.author.display_name, assignee_id, assignee_name)
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
            "bot_info": helpHandler
        }

        if intent == "summarize_conversation":
            params["transcript"] = await buildTranscript(message, params)

        handler = request_handlers.get(intent)

        if handler is None:
            await message.reply("I understood the intent but don't have a handler for it yet.")
            return

        result = await handler(params, CLICKUP_TOKEN)
        logging.info("Handler Result: %s", json.dumps(result["metadata"], indent=2))

        if not isinstance(result, dict):
            raise RuntimeError(f"Handler {intent} returned invalid result")
        
        await thinking_message.edit(content=result["message"])
        # bot_message = await message.reply(result["message"])
        bot_context[thinking_message.id] = {
            "intent": intent,
            "requester_discord_id": message.author.id,
            **result.get("metadata", {})
        }

    except RuntimeError as e:
        error = str(e)

        if error == "RATE_LIMIT":
            await message.reply("The AI service is currently rate limiting requests. Please try again in a moment.")
            return
        elif error == "SERVICE_UNAVAILABLE":
            await message.reply("The AI service is temporarily unavailable. Please try again later.")
            return
        elif error.startswith("Modal request failed"):
            await message.reply("The AI service encountered an error while processing your request.")
        elif error == "MODEL_ERROR":
            await message.reply("The AI model encountered an internal error. Please try again.")
            return
    except aiohttp.ClientError:
        await message.reply("I couldn't reach the AI service. Please try again shortly.")
        logging.exception("AI connection error")
        return
    except json.JSONDecodeError:
        logging.exception("Model returned invalid JSON")
        await message.reply("The AI returned an invalid response. Please try again.")
        return
    except Exception as e:
        logging.exception("Unexpected error")
        await message.reply("⚠️ Couldn't process that request right now. Please try again shortly.")
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
    member = getClickUpId(user.id)

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