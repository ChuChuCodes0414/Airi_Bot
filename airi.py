import discord
from discord.ext import commands,tasks
from utils import pymongo_client
from utils import pymongo_client
from utils import methods
import aiohttp
import os
from dotenv import load_dotenv

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
        prefix = methods.query(data = data,search = ["settings","general","prefix"]) or "m?"
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
    
    async def load_caches(self):
        print("Caching cogs...")
        data = list(self.db.guild_data.find({},{"settings":1}))
        userdata = list(self.db.user_data.find({},{"settings":1}))
        for cog, instance in self.cogs.items():
            if hasattr(instance,"cache"):
                instance.cache(data)
            if hasattr(instance,"user_cache"):
                instance.user_cache(userdata)
        print("All cogs cached!")

    async def on_ready(self):
        print('Bot is online, and cogs are loaded.')

client = Client()

# Need to implement
@client.check
def global_rules_check(ctx):
    return True

load_dotenv()
client.run(os.getenv('DEVELOPMENT_DEVLOPMENT_BOT_TOKEN'))