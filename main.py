import discord
import os
import requests
import json
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

GIST_ID = "your_actual_gist_id"
GIST_TOKEN = os.environ.get("GITHUB_GIST_TOKEN")

async def update_gist(new_message):
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers
    )
    existing = json.loads(response.json()["files"]["bloom-data.json"]["content"])
    existing.setdefault("messages", []).insert(0, new_message)
    existing["messages"] = existing["messages"][:50]
    requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers,
        json={"files": {"bloom-data.json": {"content": json.dumps(existing, indent=2)}}}
    )

@bot.event
async def on_ready():
    print(f"✅ Bot online! Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Get the channel name — for forum threads, use the parent channel name
    if isinstance(message.channel, discord.Thread):
        channel_name = message.channel.parent.name if message.channel.parent else message.channel.name
        thread_name = message.channel.name
    else:
        channel_name = message.channel.name
        thread_name = None

    allowed_channels = ["announcements", "jobs", "passed-bills"]
    if channel_name not in allowed_channels:
        return

    message_data = {
        "content": message.content,
        "author": message.author.name,
        "author_id": message.author.id,
        "channel": channel_name,
        "thread": thread_name,
        "timestamp": message.created_at.isoformat()
    }

    user_roles = [role.name for role in message.author.roles if role.name != "@everyone"]
    message_data["roles"] = user_roles

    print(f"📝 [{channel_name}] {message.author.name}: {message.content}")

    await update_gist(message_data)
    await bot.process_commands(message)

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
