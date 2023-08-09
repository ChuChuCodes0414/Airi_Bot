import discord
from discord import app_commands
import asyncio
from discord.ext import commands,tasks
from utils import pymongo_client
from utils import methods, errors
import aiohttp
import os
from dotenv import load_dotenv
from googletrans import Translator
from langcodes import *
import json
import datetime

class Client(commands.Bot):
    def __init__(self):
        self.prefixes = {}
        self.rules = {}
        self.dbclient = pymongo_client.get_client()
        self.db = self.dbclient.airi_bot
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix = self.get_prefix, intents = intents,activity = discord.Game("/help | @Mafuyu Bot"))

    async def get_prefix(self,message):
        if message.guild.id in self.prefixes:
            return self.prefixes[message.guild.id]
        
        data = self.db.guild_data.find_one({"_id":message.guild.id},{"settings.general.prefix":1}) or {}
        prefix = methods.query(data = data,search = ["settings","general","prefix"]) or "a?"
        self.prefixes[message.guild.id] = prefix
        return prefix
        
    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self._BotBase__cogs  = commands.core._CaseInsensitiveDict()
        await self.load_extension("jishaku")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        await self.load_caches()
        await self.tree.set_translator(Bot_Translator())
    
    async def load_caches(self):
        print("Caching cogs...")
        data = list(self.db.guild_data.find({},{"settings":1,"utility":1}))
        userdata = list(self.db.user_data.find({},{"settings":1}))
        for cog, instance in self.cogs.items():
            if hasattr(instance,"cache"):
                instance.cache(data)
            if hasattr(instance,"user_cache"):
                instance.user_cache(userdata)
        print("All cogs cached!")

    async def on_ready(self):
        print('Bot is online, and cogs are loaded.')

class Bot_Translator(app_commands.Translator):
    def __init__(self):
        self.cache = None

    def blocking_io(self,string,dest):
        print(f"Translating '{string}' to '{dest}'")
        return Translator().translate(string,dest = dest)

    async def load(self):
        with open("translations.json","r") as readfile:
            self.cache = json.load(readfile)
    async def unload(self):
        pass
    async def translate(self,string,locale,context):
        if string.message not in ["translate","Translate specified text to your local client language or others.","text","The text you want to translate.","destination","What language to translate to.","english","japanese","korean","spanish","chinese traditional","chinese simplified"]:
            return None
        dest = Language.get(str(locale)).language.lower() if str(locale).lower() != "zh-cn" and str(locale).lower() != "zh-tw" else str(locale).lower()
        if dest in ['en','zh-cn','zh-tw','ja']:
            cache = self.cache.get(string.message,{}).get(dest)
            if cache:
                print(f"Using Cached Version for {string.message} in {dest}")
                return cache
            
            translatordata = await asyncio.gather(
                asyncio.to_thread(self.blocking_io,string.message,dest),
                asyncio.sleep(3))
            
            if string.message in self.cache:
                self.cache[string.message][dest] = translatordata[0].text 
            else:
                self.cache[string.message] = {dest:translatordata[0].text}
            
            with open("translations.json","w") as outfile:
                json.dump(self.cache,outfile)

            return translatordata[0].text or None
        else:
            return None

client = Client()

# Need to implement
@client.check
def global_rules_check(ctx):
    raw = ctx.bot.db.user_data.find_one({"_id":ctx.author.id},{f"settings.blacklist":1}) or {}
    ban = methods.query(data = raw,search = ["settings","blacklist"])
    if ban:
        now = int(discord.utils.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp()) 
        if now < ban["until"]:
            raise errors.BlacklistedError(ban["until"],ban["reason"])
        else:
            ctx.bot.db.user_data.update_one({"_id":ctx.author.id},{"$unset":{"settings.blacklist":""}})
            raise errors.UnblacklistedMessage()
    if ctx.command.parents:
        for command in ctx.command.parents:
            if command.extras and "id" in command.extras:
                raw = ctx.bot.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}":1}) or {}
                rules = methods.query(data = raw,search = ["settings","rules",command.extras['id']])
                if not rules:
                    continue
                
                eroles = rules.get("eroles",None)
                droles = rules.get("droles",None)
                echannels = rules.get("echannels",None)
                dchannels = rules.get("dchannels",None)
                eusers = rules.get("eusers",None)
                dusers = rules.get("dusers",None)
                eall = rules.get("eall",None)
                dall = rules.get("dall",None)

                channel = ctx.channel.id
                roles = [(r.id) for r in ctx.author.roles]
                user = ctx.author.id

                if eall:
                    continue
                if eroles:
                    if any(item in eroles for item in roles):
                        continue
                if echannels:
                    if channel in echannels:
                        continue
                if eusers:
                    if user in eusers:
                        continue
                if dall:
                    return False
                if droles:
                    if any(item in droles for item in roles):
                        return False
                if dchannels:
                    if channel in dchannels:
                        return False
                if dusers:
                    if user in dusers:
                        return False
    
    command = ctx.command
    if not command.extras and "id" not in command.extras:
        return True
    raw = ctx.bot.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}":1}) or {}
    rules = methods.query(data = raw,search = ["settings","rules",command.extras['id']])
    if not rules:
        return True
    
    eroles = rules.get("eroles",None)
    droles = rules.get("droles",None)
    echannels = rules.get("echannels",None)
    dchannels = rules.get("dchannels",None)
    eusers = rules.get("eusers",None)
    dusers = rules.get("dusers",None)
    eall = rules.get("eall",None)
    dall = rules.get("dall",None)

    channel = ctx.channel.id
    roles = [(r.id) for r in ctx.author.roles]
    user = ctx.author.id

    if eall:
        return True
    if eroles:
        if any(item in eroles for item in roles):
            return True
    if echannels:
        if channel in echannels:
            return True
    if eusers:
        if user in eusers:
            return True
    if dall:
        return False
    if droles:
        if any(item in droles for item in roles):
            return False
    if dchannels:
        if channel in dchannels:
            return False
    if dusers:
        if user in dusers:
            return False
    return True

load_dotenv()
client.run(os.getenv('DEVELOPMENT_BOT_TOKEN'))