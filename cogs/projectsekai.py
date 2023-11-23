import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from discord import app_commands, ui
from utils import methods, errors
import aiohttp
import random
import string
import os

class ProjectSekai(commands.Cog):
    """
        Bot information and status commands.
    """
    def __init__(self,client):
        self.client = client
        self.short = "<:pjsk:1139270376086577222> | Project Sekai"

        self.pjsk_app_id = os.getenv("pjsk_app_id")
        self.pjsk_app_secret = os.getenv("pjsk_app_secret")
    
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
        view = LinkView(ctx,code)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @sekai.command(extras = {"id":"602"},help = "Edit your account visibility settings.")
    async def settings(self,ctx):
        view = SettingsView(ctx)
        embed = await view.generate_embed(self.client.db.user_data.find_one({"_id":ctx.author.id},{"pjsk.settings":1}))
        message = await ctx.reply(embed = embed,view = view)
        view.message = message

    @sekai.command(extras = {"id":"603"},help = "View your profile or someone else's.")
    async def profile(self,ctx,member:discord.Member = None):
        pass

class SettingsView(ui.View):
    def __init__(self,ctx):
        super().__init__(timeout = 60)
        self.ctx = ctx
        self.message = None
        self.add_item(VisibilitySelect())
    
    async def generate_embed(self,data):
        data = data or {}

        enid = methods.query(data = data, search = ["pjsk","settings","enid"])
        visibility = methods.query(data= data,search = ["pjsk","settings","visibility"])
        
        embed = discord.Embed(title = "Project Sekai User Settings",description = "To link an account id, use `/sekai link`",color = discord.Color.random())
        embed.add_field(name = "Global Server Player ID",value = str(enid))
        embed.add_field(name = "Profile Visibility",value = "Public" if visibility else "Private")
        embed.set_footer(text = "Use the dropdowns to configure settings.")
        return embed
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

    @ui.button(label = "Unlink GLB Account",style = discord.ButtonStyle.red)
    async def unlinken(self,interaction,button):
        update = interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$unset":{"pjsk.settings.enid":""}})
        if update.modified_count == 1:
            embed = await self.view.generate_embed(interaction.client.db.user_data.find_one({"_id":interaction.user.id},{"pjsk:settings":1}))
            await interaction.response.edit_message(embed = embed)
        else:
            await interaction.response.send_message(embed = discord.Embed(description = "Your account does not have an associated player id for the global server.",color = discord.Color.red()),ephemeral = True)

class VisibilitySelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label = "Public",description = "Allows others to see your linked account informaiton.",value = 1),
            discord.SelectOption(label = "Private",description = "Does not allow others to see your linked account information.",value = 0)
        ]
        super().__init__(placeholder = "Change linked account visibility",options = options)
    
    async def callback(self,interaction):
        if self.values[0] == "1":
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"pjsk.settings.visibility":True}})
        else:
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$unset":{"pjsk.settings.visibility":""}})
        embed = await self.view.generate_embed(interaction.client.db.user_data.find_one({"_id":interaction.user.id},{"pjsk:settings":1}))
        await interaction.response.edit_message(embed = embed)

class LinkView(ui.View):
    def __init__(self,ctx,code):
        super().__init__(timeout = 300)
        self.ctx = ctx
        self.key = code
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    @discord.ui.button(label = "Enter UID",style = discord.ButtonStyle.blurple)
    async def enterinformation(self,interaction,button):
        await interaction.response.send_modal(CollectUID(self.code))

class CollectUID(discord.ui.Modal,title = "Cookie Request"):
    def __init__(self,code):
        super().__init__()
        self.code = code
        
    uid = discord.ui.TextInput(label = "Player ID",placeholder = "You can copy this from your in-game profile page.")
    
    async def on_submit(self,interaction:discord.Interaction):
        if not isinstance(self.uid,int):
            return await interaction.response.send_message(embed = discord.Embed(description = "Your player id must an integer!",color = discord.Color.red()),ephemeral = True)

        headers = {"appid":self.pjsk_app_id,"appsecret":self.pjsk_app_secret}
        async with aiohttp.ClientSession() as session:
            async with session.get(url = f"api.nightcord.de/profile/en/{self.uid}",headers = headers) as resp:
                if resp and resp.status == 200:
                    resp = await resp.json()
                elif resp and resp.status == 404:
                    return await interaction.response.send_message(embed = discord.Embed(description = f"There is no player with the id `{self.uid}` on the global server.",color = discord.Color.red()),ephemeral = True)
                else:
                    return await interaction.response.send_message(embed = discord.Embed(description = "Something went wrong while trying to pull up profile information. Please try again in a few minutes.",color = discord.Color.red()),ephemeral = True)
                comment = resp.get("userProfile",{}).get("word","")
        if self.code not in comment:
            return await interaction.response.send_message(embed = discord.Embed(description = "Your player comment does not have the confirmation code in it, please try again later.",color = discord.Color.red()),ephemeral = True)
        interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"pjsk.settings.enid":int(self.uid)}},upsert = True)
        embed = discord.Embed(title = "Player ID Data Set!",description = "Your player id is now set, and you can use any commands that require your specific id.",color = discord.Color.green())
        await interaction.response.send_message(embed = embed,ephemeral = True)

async def setup(client):
    await client.add_cog(ProjectSekai(client))