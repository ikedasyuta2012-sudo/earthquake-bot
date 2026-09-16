import os
import json
import asyncio
import discord
import websockets
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_ID = 1549857874874728579 

async def listen_earthquake():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while True:
        try:
            async with websockets.connect("wss://api.p2pquake.net/v2/ws") as ws:
                async for message in ws:
                    data = json.loads(message)
                    if data.get("code") == 551:  # 地震情報コード
                        await post_earthquake(channel, data)
        except Exception as e:
            print(f"接続エラー: {e}, 5秒後に再接続します")
            await asyncio.sleep(5)

async def post_earthquake(channel, data):
    earthquake = data.get("earthquake", {})
    hypocenter = earthquake.get("hypocenter", {})

    place = hypocenter.get("name", "不明")
    depth = hypocenter.get("depth", "不明")
    magnitude = hypocenter.get("magnitude", "不明")
    max_scale = earthquake.get("maxScale", None)
    tsunami = earthquake.get("domesticTsunami", "None")

    scale_map = {
        10: "1", 20: "2", 30: "3", 40: "4",
        45: "5弱", 50: "5強", 55: "6弱", 60: "6強", 70: "7"
    }
    shindo = scale_map.get(max_scale, "不明")

    tsunami_map = {
        "None": "なし",
        "Unknown": "不明",
        "Checking": "調査中",
        "NonEffective": "若干の海面変動",
        "Watch": "津波注意報",
        "Warning": "津波警報・大津波警報"
    }
    tsunami_text = tsunami_map.get(tsunami, "不明")

    embed = discord.Embed(
        title="🚨 地震情報",
        color=0xff0000 if max_scale and max_scale >= 50 else 0xffa500
    )
    embed.add_field(name="震源地", value=place, inline=True)
    embed.add_field(name="最大震度", value=shindo, inline=True)
    embed.add_field(name="マグニチュード", value=magnitude, inline=True)
    embed.add_field(name="深さ", value=f"{depth}km" if depth != "不明" else "不明", inline=True)
    embed.add_field(name="津波", value=tsunami_text, inline=False)

    await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(listen_earthquake())

bot.run(os.environ["DISCORD_TOKEN"])
