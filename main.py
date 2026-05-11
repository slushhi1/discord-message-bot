import discord
import os
import requests
import json
from discord.ext import commands

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content
intents.members = True           # Required to see member roles

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Your website will go here later
# For now, we're just printing to console
# When you're ready to connect to website, uncomment the JSONBin section below

# ============================================
# SECTION 1: Bot Events
# ============================================

@bot.event
async def on_ready():
    print(f"✅ Bot is online!")
    print(f"Logged in as: {bot.user}")
    print(f"Bot is in {len(bot.guilds)} server(s)")
    
    # List what channels the bot can see (for debugging)
    for guild in bot.guilds:
        print(f"\n📁 Server: {guild.name}")
        for channel in guild.text_channels:
            print(f"   - #{channel.name}")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author.bot:
        return
    
    # Get message details
    message_data = {
        "content": message.content,
        "author": message.author.name,
        "author_id": message.author.id,
        "channel": message.channel.name,
        "timestamp": message.created_at.isoformat()
    }
    
    # Get user's roles (excluding @everyone)
    user_roles = [role.name for role in message.author.roles if role.name != "@everyone"]
    message_data["roles"] = user_roles
    
    # Print to console (for testing)
    print(f"\n📝 New message from {message.author.name}")
    print(f"   Content: {message.content}")
    print(f"   Channel: #{message.channel.name}")
    print(f"   Roles: {', '.join(user_roles) if user_roles else 'None'}")
    
    # ============================================
    # SECTION 2: Send to Website (Uncomment later)
    # ============================================
    # When your website is ready, replace this section with code to send message_data
    # to your website's API endpoint or JSONBin
    
    # Example for JSONBin (uncomment and add your bin ID and API key later):
    # save_to_jsonbin(message_data)
    
    await bot.process_commands(message)


@bot.event
async def on_member_update(before, after):
    # This runs when a member's roles change
    old_roles = set([role.name for role in before.roles if role.name != "@everyone"])
    new_roles = set([role.name for role in after.roles if role.name != "@everyone"])
    
    added_roles = new_roles - old_roles
    removed_roles = old_roles - new_roles
    
    if added_roles or removed_roles:
        print(f"\n👤 Role update for {after.name}")
        if added_roles:
            print(f"   Added roles: {', '.join(added_roles)}")
        if removed_roles:
            print(f"   Removed roles: {', '.join(removed_roles)}")


# ============================================
# SECTION 3: JSONBin Integration (Optional)
# ============================================
# Uncomment this section when you have a JSONBin account
# Go to jsonbin.io, create a free account, and get your Bin ID and API Key

"""
def save_to_jsonbin(message_data):
    JSONBIN_BIN_ID = "YOUR_BIN_ID_HERE"
    JSONBIN_API_KEY = "YOUR_API_KEY_HERE"
    
    # Get existing messages
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            messages = data.get("record", {}).get("messages", [])
            
            # Add new message at the beginning
            messages.insert(0, message_data)
            
            # Keep only last 100 messages
            messages = messages[:100]
            
            # Update the bin
            update_url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
            update_data = {"messages": messages}
            requests.put(update_url, headers=headers, json=update_data)
            print("   ✓ Saved to JSONBin")
        else:
            print(f"   ✗ Error saving to JSONBin: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
"""


# ============================================
# SECTION 4: Run the Bot
# ============================================

TOKEN = os.environ.get("DISCORD_TOKEN")

if TOKEN is None:
    print("❌ Error: DISCORD_TOKEN environment variable not set!")
    print("   Add it in Railway under Variables tab")
else:
    bot.run(TOKEN)
