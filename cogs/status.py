import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from discord import app_commands
from utils import methods

class Status(commands.Cog):
    """
        Bot information and status commands.
    """
    def __init__(self,client):
        self.client = client
        self.short = "<:status:950594213391790152> | Bot Status"
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Status Category Loaded.")

    @commands.hybrid_command(extras = {"id": "300"},help = "Get the bot's ping.")
    async def ping(self,ctx):
        apiping = round(self.client.latency*1000)
        embed = discord.Embed(title = "Pong 🏓",description = f"API Ping: `{apiping}ms`",color = discord.Color.random())
        embed.set_footer(text = "Note: This message can be misleading.")
        message = await ctx.reply(embed = embed)
        latency = ctx.message.created_at - message.created_at
        embed = discord.Embed(title = "Pong 🏓",description = f"API Ping: `{apiping}ms`\nMessage Latency: `{latency.microseconds*0.001}ms`",color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await message.edit(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "301"},help = "Get information about the bot.")
    async def about(self,ctx):
        embed = discord.Embed(title = self.client.user.name,description = "A multipurpose utility bot with a little bit of everything!\nCreated and maintained by ChuGames#0001",color = discord.Color.random())
        embed.add_field(name ="Current Version",value = f"3.2",inline = False)
        embed.add_field(name="Server Count", value=f"{len(self.client.guilds)} servers")
        embed.add_field(name="Member Count", value=f"{len(self.client.users)} members")
        embed.add_field(name="Main Libraries Used", value=f"discord.py (https://github.com/Rapptz/discord.py)\ngenshin.py (https://github.com/thesadru/genshin.py)\nEnkaCard (https://github.com/DEViantUA/EnkaCard)\ngoogletrans (https://github.com/ssut/py-googletrans)\nlangcodes (https://github.com/rspeer/langcodes)",inline = False)
        embed.add_field(name="Developer Information", value = "This bot is developed as mainly a passion project, and may be prone to errors and frequent changes. Any questions can be directed to the support server at [support server](https://discord.com/invite/9pmGDc8pqQ).",inline = False)
        embed.add_field(name = "Bot Rules and Privacy Policy",value = "https://docs.google.com/document/d/1TWI1e_V8fABj8QQOGoBIml10mRfWLZh7ejkZrBEMbfU/edit?usp=sharing")
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "302"},help = "Invite the bot or join the support server.")
    async def invite(self,ctx):
        embed = discord.Embed(title = "Invite Links",description = "[Support Server](https://discord.com/invite/9pmGDc8pqQ)\n[Admin Perms Invite (Recommended)](https://discord.com/api/oauth2/authorize?client_id=752335987761217576&permissions=8&scope=bot)\n[Mod Perms Invite](https://discord.com/api/oauth2/authorize?client_id=752335987761217576&permissions=41771777523703&scope=bot)\n[Minimal Perms Invite](https://discord.com/api/oauth2/authorize?client_id=752335987761217576&permissions=40671297011392&scope=bot)\n\nPlease note, inviting the bot with less perms means you will need to manage perms own your own.",color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
async def setup(client):
    await client.add_cog(Status(client))