import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import locale_str as _T, Choice
from googletrans import Translator
from langcodes import *
from typing import Literal

class TranslateCommands(commands.Cog):
    """
    
    """
    def __init__(self,client):
        self.client = client
        self.supported_locales = {"en-US":"en","en-GB":"en","pt-BR":"pt","es-ES":"es","sv-SE":"sv"}
        self.translate_menu = app_commands.ContextMenu(
            name = _T("translate"),callback = self.translatetolocale
        )
        self.client.tree.add_command(self.translate_menu)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Translate Category Loaded")
    
    async def translatetext(self,string,dest):
        translator = Translator()
        return translator.translate(string,dest = dest)

    @app_commands.command(name = _T("translate"), description = _T("Translate specified text to your local client language or others."))
    @app_commands.describe(text = _T("The text you want to translate."),destination = _T("What language to translate to."))
    @app_commands.choices(
        destination = [
            Choice(name = _T("english"),value = "en"),
            Choice(name = _T("chinese traditional"),value = "zh-tw"),
            Choice(name = _T("chinese simplified"),value = "zh-cn"),
            Choice(name = _T("japanese"),value = "ja"),
            Choice(name = _T("korean"),value = "ko"),
            Choice(name = _T("spanish"),value = "es"),
        ]
    )
    async def translatetodestination(self,interaction:discord.Interaction,text:str,destination: Choice[str] = None):
        if destination:
            destination = destination.value
        else:
            destination = str(interaction.locale).lower()
        await interaction.response.defer()
        dest = Language.get(destination).language.lower() if destination not in ["zh-cn","zh-tw"] else destination
        translatordata = await self.translatetext(text,dest = dest)
        embed = discord.Embed(title = _T(f"Translating from {Language.get(translatordata.src).display_name()} -> {Language.get(translatordata.dest).display_name()}"))
        embed.set_author(name = interaction.user,icon_url = interaction.user.avatar.url)
        embed.add_field(name = _T("Original Text"),value = text,inline = False)
        embed.add_field(name = _T("Translated Text"),value = translatordata.text,inline = False)
        embed.set_footer(text = self.client.user.name,icon_url = self.client.user.avatar.url)
        await interaction.followup.send(embed = embed)

    async def translatetolocale(self,interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(ephemeral = True)
        destination = str(interaction.locale).lower()
        dest = Language.get(destination).language.lower() if destination not in ["zh-cn","zh-tw"] else destination
        translatordata = await self.translatetext(message.content,dest = dest)
        embed = discord.Embed(title = _T(f"Translating from {Language.get(translatordata.src).display_name()} -> {Language.get(translatordata.dest).display_name()}"))
        embed.set_author(name = message.author,icon_url = message.author.avatar.url)
        embed.add_field(name = _T("Original Text"),value = message.content or "None",inline = False)
        embed.add_field(name = _T("Translated Text"),value = translatordata.text,inline = False)
        embed.set_footer(text = interaction.client.user.name,icon_url = interaction.client.user.avatar.url)
        await interaction.followup.send(embed = embed,ephemeral = True)

async def setup(client):
    await client.add_cog(TranslateCommands(client))