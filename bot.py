import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import websockets

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

REGISTERED_FILE = "registered_channels.json"

def load_channels():
    if os.path.exists(REGISTERED_FILE):
        with open(REGISTERED_FILE, "r") as f:
            return json.load(f)
    return []

def save_channels(channels):
    with open(REGISTERED_FILE, "w") as f:
        json.dump(channels, f)

registered_channels = load_channels()

scale_map = {
    10: "1", 20: "2", 30: "3", 40: "4",
    45: "5弱", 50: "5強", 55: "6弱", 60: "6強", 70: "7"
}

tsunami_map = {
    "None": "なし", "Unknown": "不明", "Checking": "調査中",
    "NonEffective": "若干の海面変動", "Watch": "津波注意報",
    "Warning": "津波警報・大津波警報"
}

def build_embed(place, depth, magnitude, max_scale, tsunami, test=False):
    shindo = scale_map.get(max_scale, "不明")
    tsunami_text = tsunami_map.get(tsunami, "不明")

    embed = discord.Embed(
        title=("🧪 【テスト】地震情報" if test else "🚨 地震情報"),
        color=0xff0000 if max_scale and max_scale >= 50 else 0xffa500
    )
    embed.add_field(name="震源地", value=place, inline=True)
    embed.add_field(name="最大震度", value=shindo, inline=True)
    embed.add_field(name="マグニチュード", value=magnitude, inline=True)
    embed.add_field(name="深さ", value=f"{depth}km" if depth != "不明" else "不明", inline=True)
    embed.add_field(name="津波", value=tsunami_text, inline=False)
    return embed

async def listen_earthquake():
    await bot.wait_until_ready()

    while True:
        try:
            async with websockets.connect("wss://api.p2pquake.net/v2/ws") as ws:
                async for message in ws:
                    data = json.loads(message)
                    if data.get("code") == 551:
                        await broadcast_earthquake(data)
        except Exception as e:
            print(f"接続エラー: {e}, 5秒後に再接続します")
            await asyncio.sleep(5)

async def broadcast_earthquake(data):
    earthquake = data.get("earthquake", {})
    hypocenter = earthquake.get("hypocenter", {})

    place = hypocenter.get("name", "不明")
    depth = hypocenter.get("depth", "不明")
    magnitude = hypocenter.get("magnitude", "不明")
    max_scale = earthquake.get("maxScale", None)
    tsunami = earthquake.get("domesticTsunami", "None")

    embed = build_embed(place, depth, magnitude, max_scale, tsunami)

    for channel_id in registered_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    bot.loop.create_task(listen_earthquake())

@bot.tree.command(name="登録", description="このチャンネルを地震情報の通知先として登録します")
async def register(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in registered_channels:
        await interaction.response.send_message("このチャンネルはすでに登録済みです。", ephemeral=True)
        return
    registered_channels.append(channel_id)
    save_channels(registered_channels)
    await interaction.response.send_message("✅ このチャンネルを地震情報の通知先として登録しました。", ephemeral=False)

@bot.tree.command(name="登録解除", description="このチャンネルの地震情報通知を解除します")
async def unregister(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id not in registered_channels:
        await interaction.response.send_message("このチャンネルは登録されていません。", ephemeral=True)
        return
    registered_channels.remove(channel_id)
    save_channels(registered_channels)
    await interaction.response.send_message("🛑 このチャンネルの通知を解除しました。", ephemeral=False)

@bot.tree.command(name="稼働テスト", description="botが正常に稼働しているかテストします")
async def test(interaction: discord.Interaction):
    embed = build_embed(
        place="テスト震源地",
        depth="10",
        magnitude="5.0",
        max_scale=40,
        tsunami="None",
        test=True
    )
    await interaction.response.send_message(embed=embed)

bot.run(os.environ["DISCORD_TOKEN"])
