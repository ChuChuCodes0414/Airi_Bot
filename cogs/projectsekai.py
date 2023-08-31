import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from discord import app_commands
from utils import methods, errors
import aiohttp
import random
import string

class ProjectSekai(commands.Cog):
    """
        Bot information and status commands.
    """
    def __init__(self,client):
        self.client = client
        self.short = "<:pjsk:1139270376086577222> | Project Sekai"
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Project Sekai Category Loaded.")
    
    @commands.hybrid_group(extras = {"id": "600"},help = "The command group to manage your account details.")
    async def sekai(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `sekai` to get a list of commands.")

    @sekai.command(extras = {"id":"601"},help = "Link your discord account to your project sekai account.")
    async def link(self,ctx):
        code = ''.join(random.choices(string.ascii_letters,k=6))
        embed = discord.Embed(title = "Project Sekai Account Linking",description = "⚠ Note: Currently, only the English (Global) server is supported.",color = discord.Color.random())
        embed.add_field(name = "How to link",value = f"1. Put the characters `{code}` into your profile comment (can be changed afterwards).\n2. Press `Enter UID` below and enter in your unique player ID.",inline = False)
        embed.set_image(url = "https://media.discordapp.net/attachments/870127759526101032/1140446826693148775/IMG_0100.png?width=972&height=675")
        await ctx.reply(embed = embed)
    
    @sekai.command(extras = {"id":"602"},help = "Edit your account visibility settings.")
    async def settings(self,ctx):
        pass

    @sekai.command(extras = {"id":"603"},help = "View your profile or someone else's.")
    async def profile(self,ctx,member:discord.Member = None):
        pass
    
async def setup(client):
    await client.add_cog(ProjectSekai(client))