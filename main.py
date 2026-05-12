import discord
import os
import requests
import json
import cloudinary
import cloudinary.uploader
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

GIST_ID = "c0e6631773692d0c353929162506b70d"
GIST_TOKEN = os.environ.get("GITHUB_GIST_TOKEN")

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

TRACKED_ROLES = [
    "President",
    "Speaker",
    "Congress Member",
    "Secretary of State",
    "Secretary of Treasury",
    "Secretary of Interior",
    "Secretary of Agriculture",
    "Secretary of Education",
    "Secretary of Defense",
    "Secretary of Archives",
]

async def upload_image(url):
    try:
        result = cloudinary.uploader.upload(url)
        return result.get("secure_url")
    except Exception as e:
        print(f"Image upload failed: {e}")
        return url

async def parse_bill(content, thread_name):
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    return {
        "type": "bill",
        "title": thread_name,
        "link": lines[0] if len(lines) > 0 else None,
        "date_passed": lines[1] if len(lines) > 1 else None,
        "bill_author": lines[2] if len(lines) > 2 else None
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

def get_gist_data(headers):
    response = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
    data = response.json()
    if "files" not in data:
        print(f"Error from GitHub: {data.get('message', 'unknown error')}")
        return None
    return json.loads(data["files"]["bloom-data.json"]["content"])

def save_gist_data(headers, existing):
    requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers,
        json={"files": {"bloom-data.json": {"content": json.dumps(existing, indent=2)}}}
    )

def thread_already_in_gist(existing, channel_name, thread_name):
    return any(
        m.get("channel") == channel_name and m.get("thread") == thread_name
        for m in existing.get("messages", [])
    )

async def update_gist(new_message):
    headers = {"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    existing = get_gist_data(headers)
    if existing is None:
        return
    existing.setdefault("messages", []).insert(0, new_message)
    existing["messages"] = existing["messages"][:50]
    save_gist_data(headers, existing)

async def scan_government_roles():
    headers = {"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    government = {}
    for guild in bot.guilds:
        for role_name in TRACKED_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                members = [m.display_name for m in role.members]
                government[role_name] = members
                print(f"  {role_name}: {members}")
            else:
                government[role_name] = []
                print(f"  {role_name}: role not found")

    existing = get_gist_data(headers)
    if existing is None:
        return
    existing["government"] = government
    save_gist_data(headers, existing)
    print("✅ Government roles updated in Gist")

@tasks.loop(minutes=30)
async def refresh_government():
    await scan_government_roles()

@bot.event
async def on_ready():
    print(f"✅ Bot online! Logged in as {bot.user}")
    await scan_government_roles()
    refresh_government.start()

@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        print(f"🔄 Role change detected for {after.display_name}, updating government roster...")
        await scan_government_roles()

@bot.event
async def on_thread_delete(thread):
    if not thread.parent:
        return
    channel_name = thread.parent.name
    if channel_name not in ["passed-bills", "jobs", "properties"]:
        return
    headers = {"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    existing = get_gist_data(headers)
    if existing is None:
        return
    before = len(existing.get("messages", []))
    existing["messages"] = [
        m for m in existing.get("messages", [])
        if not (m.get("channel") == channel_name and m.get("thread") == thread.name)
    ]
    after = len(existing["messages"])
    if before != after:
        save_gist_data(headers, existing)
        print(f"🗑️ Removed '{thread.name}' from Gist")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.Thread):
        channel_name = message.channel.parent.name if message.channel.parent else message.channel.name
        thread_name = message.channel.name
    else:
        channel_name = message.channel.name
        thread_name = None

    allowed_channels = ["announcements", "jobs", "passed-bills", "properties"]
    if channel_name not in allowed_channels:
        return

    headers = {"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    if thread_name:
        existing = get_gist_data(headers)
        if existing is None:
            return
        if thread_already_in_gist(existing, channel_name, thread_name):
            print(f"⏭️ [{channel_name}] '{thread_name}' already in Gist, skipping")
            await bot.process_commands(message)
            return
        history = [m async for m in message.channel.history(limit=1, oldest_first=True)]
        if not history:
            await bot.process_commands(message)
            return
        first_message = history[0]
    else:
        first_message = message
        existing = get_gist_data(headers)
        if existing is None:
            return

    user_roles = [role.name for role in first_message.author.roles if role.name != "@everyone"]

    message_data = {
        "author": first_message.author.name,
        "display_name": first_message.author.display_name,
        "author_id": first_message.author.id,
        "channel": channel_name,
        "thread": thread_name,
        "timestamp": first_message.created_at.isoformat(),
        "roles": user_roles
    }

    if channel_name == "passed-bills":
        parsed = await parse_bill(first_message.content, thread_name)
        message_data.update(parsed)
    elif channel_name in ["jobs", "properties"]:
        parsed = await parse_job(first_message, thread_name)
        message_data.update(parsed)
    else:
        message_data["content"] = first_message.content

    print(f"📝 [{channel_name}] {first_message.author.display_name}: {thread_name or first_message.content[:50]}")

    existing.setdefault("messages", []).insert(0, message_data)
    existing["messages"] = existing["messages"][:50]
    save_gist_data(headers, existing)
    await bot.process_commands(message)

TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
