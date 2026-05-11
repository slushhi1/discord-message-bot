import discord
import os
import requests
import json
import re
import cloudinary
import cloudinary.uploader
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

GIST_ID = "c0e6631773692d0c353929162506b70d"
GIST_TOKEN = os.environ.get("GITHUB_GIST_TOKEN")

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

async def upload_image(url):
    try:
        result = cloudinary.uploader.upload(url)
        return result.get("secure_url")
    except Exception as e:
        print(f"Image upload failed: {e}")
        return url

async def parse_bill(content, thread_name):
    link = None
    date = None

    for line in content.splitlines():
        line = line.strip()
        if line.lower().startswith("link:"):
            link = line.split(":", 1)[1].strip()
        elif line.lower().startswith("date passed:"):
            date = line.split(":", 1)[1].strip()

    return {
        "type": "bill",
        "title": thread_name,
        "link": link,
        "date_passed": date
    }

async def parse_job(message, thread_name):
    image_url = None
    if message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ["png", "jpg", "jpeg", "gif", "webp"]):
                image_url = await upload_image(attachment.url)
                break

    return {
        "type": "job",
        "title": thread_name,
        "description": message.content,
        "image": image_url
    }

async def update_gist(new_message):
    headers = {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers
    )

    data = response.json()
    print(f"Gist API response status: {response.status_code}")

    if "files" not in data:
        print(f"Error from GitHub: {data.get('message', 'unknown error')}")
        return

    existing = json.loads(data["files"]["bloom-data.json"]["content"])
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

    if isinstance(message.channel, discord.Thread):
        channel_name = message.channel.parent.name if message.channel.parent else message.channel.name
        thread_name = message.channel.name

        # Only capture the first message of the thread
        if message.id != message.channel.id:
            # Check if this is the first message by fetching thread history
            history = [m async for m in message.channel.history(limit=2, oldest_first=True)]
            if len(history) > 0 and history[0].id != message.id:
                return
    else:
        channel_name = message.channel.name
        thread_name = None

    allowed_channels = ["announcements", "jobs", "passed-bills"]
    if channel_name not in allowed_channels:
        return

    user_roles = [role.name for role in message.author.roles if role.name != "@everyone"]

    message_data = {
        "author": message.author.name,
        "display_name": message.author.display_name,
        "author_id": message.author.id,
        "channel": channel_name,
        "thread": thread_name,
        "timestamp": message.created_at.isoformat(),
        "roles": user_roles
    }

    if channel_name == "passed-bills":
        parsed = await parse_bill(message.content, thread_name)
        message_data.update(parsed)
    elif channel_name == "jobs":
        parsed = await parse_job(message, thread_name)
        message_data.update(parsed)
    else:
        message_data["content"] = message.content

    print(f"📝 [{channel_name}] {message.author.display_name}: {thread_name or message.content[:50]}")

    await update_gist(message_data)
    await bot.process_commands(message)

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
