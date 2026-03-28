import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latency: {round(bot.latency * 1000)}ms")


bot.run(TOKEN)
