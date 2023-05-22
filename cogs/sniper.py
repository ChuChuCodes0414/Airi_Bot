import discord
from discord.ext import commands
from firebase_admin import db
from datetime import datetime
import asyncio
from discord import app_commands
from utils import methods

class Sniper(commands.Cog):
    """
        Powerful snipe commands that makes sure nothing your friends posts stays hidden...
    """
    def __init__(self,client):
        self.client = client
        self.short = "<:sniper:950162525083815937> | Message Sniper"
        self.settings = {}
        self.user_settings = {}
        self.sniped_messages = {}
        self.edited_messages = {}
        self.removed_reactions = {}
        self.purged_messages = {}
    
    def cache(self,data):
        for guild in data:
            settings = methods.query(guild,["settings","sniper"]) or {}
            self.settings[int(guild["_id"])] = [settings.get("snipelb",None),settings.get("snipecd",None)]
        print("Sniping Guild Cache Loaded")
    
    def user_cache(self,data):
        for user in data:
            if methods.query(user,["settings","sniper","snipeblock"]):
                self.user_settings[int(user["_id"])] = True
        print("Sniping User Cache Loaded")
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Snipe Category Loaded.")
    
    @commands.Cog.listener()
    async def on_guild_join(self,guild):
        raw = self.client.guild_data.find_one({"_id":guild.id},{"settings.sniper":1})
        snipelb,snipecd = methods.query(data = raw,search = ["settings","sniper","snipelb"]),methods.query(data = raw,search = ["settings","sniper","snipecd"])
        self.settings[guild.id] = [snipelb,snipecd]
    
    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        try:
            self.settings.pop(guild.id)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_message_delete(self,message):
        if self.user_settings.get(message.author.id,False):
            return
        now = datetime.now()
        if message.channel.id in self.sniped_messages:
            self.sniped_messages[message.channel.id].insert(0,[message,now])
        else:
            self.sniped_messages[message.channel.id] = [[message,now]]
        max = self.settings[message.guild.id][0] or 50
        if max > 50:
            max = 50
        if len(self.sniped_messages[message.channel.id]) > max:
            self.sniped_messages[message.channel.id].pop(-1)
        time = self.settings[message.guild.id][1] or 30
        await asyncio.sleep(time)
        try:
            self.sniped_messages[message.channel.id].remove([message,now])
        except:
            pass
    
    @commands.Cog.listener()
    async def on_bulk_message_delete(self,messages):
        now = datetime.now()
        if messages[0].channel.id in self.purged_messages:
            self.purged_messages[messages[0].channel.id].insert(0,[messages,now])
        else:
            self.purged_messages[messages[0].channel.id] = [[messages,now]]
        max = self.settings[messages[0].guild.id][0] or 50
        if max > 50:
            max = 50
        if len(self.purged_messages[messages[0].channel.id]) > max:
            self.purged_messages[messages[0].channel.id].pop(-1)
        time = self.settings[messages[0].guild.id][1] or 30
        await asyncio.sleep(time)
        try:
            self.purged_messages[messages[0].channel.id].remove([messages,now])
        except:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self,message_before,message_after):
        if self.user_settings.get(message_before.author.id,False):
            return
        if message_before.content and message_after.content:
            now = datetime.now()
            if message_before.channel.id in self.edited_messages:
                self.edited_messages[message_before.channel.id].insert(0,[message_before,message_after,now])
            else:
                self.edited_messages[message_before.channel.id] = [[message_before,message_after,now]]
            max = self.settings[message_before.guild.id][0] or 50
            if max > 50:
                max = 50
            if len(self.edited_messages[message_before.channel.id]) > max:
                self.edited_messages[message_before.channel.id].pop(-1)
            time = self.settings[message_before.guild.id][1] or 30
            await asyncio.sleep(time)
            try:
                self.edited_messages[message_before.channel.id].remove([message_before,message_after,now])
            except:
                pass

    @commands.Cog.listener()
    async def on_reaction_remove(self,reaction, user):
        if self.user_settings.get(user.id,False):
            return
        message = reaction.message
        now = datetime.now()
        if message.channel.id in self.removed_reactions:
            self.removed_reactions[message.channel.id].insert(0,[message,user,reaction,now])
        else:
            self.removed_reactions[message.channel.id] = [[message,user,reaction,now]]
        max = self.settings[message.guild.id][0] or 50
        if max > 50:
            max = 50
        if len(self.removed_reactions[message.channel.id]) > max:
            self.removed_reactions[message.channel.id].pop(-1)
        time = self.settings[message.guild.id][1] or 30
        await asyncio.sleep(time)
        try:
            self.removed_reactions[message.channel.id].remove([message,user,reaction,now])
        except:
            pass

    @commands.hybrid_command(extras = {"id":"100"},name = 'snipe',aliases = ['sn'],help = "Snipe a recently deleted message!")
    @app_commands.describe(index = "The message index you want to snipe, bigeer number the older the message.")
    @app_commands.describe(channel = "The channel to snipe from.")
    async def snipe(self,ctx,index:int = None,channel:discord.TextChannel = None):
        channel = channel or ctx.channel
        index = index or 1
        index -= 1

        if not channel.id in self.sniped_messages:
            return await ctx.reply(embed = discord.Embed(description = f"There are no deleted messages in {channel.mention}",color = discord.Color.red()))
        if not index < len(self.sniped_messages[channel.id]) or index < 0:
            return await ctx.reply(embed = discord.Embed(description = f"Your snipe request is not valid!\nThere are only `{len(self.sniped_messages[channel.id])}` deleted messages in {channel.mention}.",color = discord.Color.red()))
        
        message = self.sniped_messages[channel.id][index][0]
        time = self.sniped_messages[channel.id][index][1]

        if message.embeds:
            sniped_embed = message.embeds[0]
            await ctx.reply(embed = sniped_embed)
            emb = discord.Embed(title = f"Deleted message {index+1} in #{channel.name}", description = "Embed sniped, shown above.",color = discord.Color.random())
            emb.set_author(name=f"Sent by {message.author}",icon_url=message.author.avatar)
            emb.set_footer(text = f"Sniped by {ctx.message.author}")
            emb.timestamp = time
            return await ctx.send(embed = emb)
        else:
            description = message.content

        emb = discord.Embed(title = f"Deleted message {index+1} in #{channel.name}", description = description,color = discord.Color.random())
        emb.set_author(name=f"Sent by {message.author}",icon_url=message.author.avatar)
        emb.set_footer(text = f"Sniped by {ctx.message.author}")
        emb.timestamp = time

        try:
            emb.set_image(url = message.attachments[0])
        except:
            pass

        await ctx.reply(embed = emb)

    @commands.hybrid_command(extras = {"id": "101"},aliases = ['ms'],help = "Just how many messages that were deleted are hiding in this channel? Find out with this command.")
    async def maxsnipe(self,ctx):
        try:
            messages = len(self.sniped_messages[ctx.channel.id])
        except:
            messages = 0
        await ctx.reply(embed = discord.Embed(description = f"There are a total of `{messages}` messages hiding in this channel!",color = discord.Color.random()))

    @commands.hybrid_command(extras = {"id": "102"},name = 'esnipe',aliases = ['esn'],help = "Snipe a recently edited message!")
    @app_commands.describe(index = "The message index you want to snipe, bigeer number the older the message.")
    @app_commands.describe(channel = "The channel to snipe from.")
    async def esnipe(self,ctx,index:int = None,channel:discord.TextChannel = None):
        channel = channel or ctx.channel
        index = index or 1
        index -= 1

        if not channel.id in self.edited_messages:
            return await ctx.reply(embed = discord.Embed(description = f"There are no edited messages in {channel.mention}",color = discord.Color.red()))
        if not index < len(self.edited_messages[channel.id]) or index < 0:
            return await ctx.reply(embed = discord.Embed(description = f"Your snipe request is not valid!\nThere are only `{len(self.sniped_messages[channel.id])}` edited messages in {channel.mention}.",color = discord.Color.red()))

        message = self.edited_messages[channel.id][index]

        emb = discord.Embed(title = f"Edited message {index + 1} in #{channel.name}", description = f'**Before:** {message[0].content}\n**After:** {message[1].content}',color = discord.Color.random())
        emb.set_author(name= f"Edited by {message[0].author}" ,icon_url=message[0].author.avatar)
        emb.set_footer(text = f"Sniped by {ctx.message.author}")
        emb.timestamp = message[2]

        await ctx.reply(embed = emb)

    @commands.hybrid_command(extras = {"id": "103"},aliases = ['mes'],help = "Just how many messages that were edited are hiding in this channel? Find out with this command.")
    async def maxesnipe(self,ctx):
        try:
            messages = len(self.edited_messages[ctx.channel.id])
        except:
            messages = 0
        await ctx.reply(embed = discord.Embed(description = f"There are a total of `{messages}` edited messages hiding in this channel!",color = discord.Color.random()))

    @commands.hybrid_command(extras = {"id": "104"},name = 'rsnipe',aliases = ['rsn'],help = "Snipe a recently removed reaction!")
    @app_commands.describe(index = "The message index you want to snipe, bigeer number the older the message.")
    @app_commands.describe(channel = "The channel to snipe from.")
    async def rsnipe(self,ctx,index:int = None,channel:discord.TextChannel = None):
        channel = channel or ctx.channel
        index = index or 1
        index -= 1

        if not channel.id in self.removed_reactions:
            return await ctx.reply(embed = discord.Embed(description = f"There are no removed reactions in {channel.mention}",color = discord.Color.red()))
        if not index < len(self.removed_reactions[channel.id]) or index < 0:
            return await ctx.reply(embed = discord.Embed(description = f"Your snipe request is not valid!\nThere are only `{len(self.sniped_messages[channel.id])}` removed reactions in {channel.mention}.",color = discord.Color.red()))

        data = self.removed_reactions[channel.id][index]

        emb = discord.Embed(title = f"Removed reaction {index+1} in #{channel.name}", description = f'**Message:** [Link to Message]({data[0].jump_url})\n**Reaction Removed:** {data[2].emoji}',color = discord.Color.random())
        emb.set_author(name=f"Reationed removed by {data[1]}",icon_url=data[1].avatar)
        emb.set_footer(text = f"Sniped by {ctx.message.author}")
        emb.timestamp = data[3]
        await ctx.reply(embed = emb)

    @commands.hybrid_command(extras = {"id": "105"},aliases = ['mrs'],help = "Just how many messages that were edited are hiding in this channel? Find out with this command.")
    async def maxrsnipe(self,ctx):
        try:
            reactions = len(self.removed_reactions[ctx.channel.id])
        except:
            reactions = 0
        await ctx.reply(embed = discord.Embed(description = f"There are a total of `{reactions}` removed reactions hiding in this channel!",color = discord.Color.random()))

    @commands.hybrid_command(extras = {"id": "106"},aliases = ['psn'],help = "Snipe the list of recently purged messages!")
    @app_commands.describe(index = "The message index you want to snipe, bigeer number the older the message.")
    @app_commands.describe(channel = "The channel to snipe from.")
    async def psnipe(self,ctx,index:int = None,channel:discord.TextChannel = None):
        channel = channel or ctx.channel
        index = index or 1
        index -= 1

        if not channel.id in self.purged_messages:
            return await ctx.reply(embed = discord.Embed(description = f"There are no purged messages in {channel.mention}",color = discord.Color.red()))
        if not index < len(self.purged_messages[channel.id]) or index < 0:
            return await ctx.reply(embed = discord.Embed(description = f"Your snipe request is not valid!\nThere are only `{len(self.sniped_messages[channel.id])}` purged messages in {channel.mention}.",color = discord.Color.red()))
       
        data = self.purged_messages[channel.id][index]

        if len(data[0]) >= 16:
            emb = discord.Embed(title = f"Purged messages in #{channel.name}", description = f'There were 16+ purged messages here. What are they? I don\'t know I didn\'t store them lol.',color = discord.Color.random())
            emb.set_footer(text = f"Sniped by {ctx.message.author}")
            emb.timestamp = data[1]
            return await ctx.reply(embed = emb)

        build = ""

        for message in data[0]:
            if message.content:
                build += f"[{message.author}]: {message.content}\n"
            else:
                build += f"[{message.author}]: *No Message Content to Display*\n"
            
        emb = discord.Embed(title = f"Purged messages in #{channel.name}", description = f'{build}',color = discord.Color.random())
        emb.set_footer(text = f"Sniped by {ctx.message.author}")
        emb.timestamp = data[1]
        return await ctx.reply(embed = emb)

    @commands.hybrid_command(extras = {"id": "107"},aliases = ['mps'],help = "Just how many messages that were purged are hiding in this channel? Find out with this command.")
    async def maxpsnipe(self,ctx):
        try:
            messages = len(self.purged_messages[ctx.channel.id])
        except:
            messages = 0
        await ctx.reply(embed = discord.Embed(description = f"There are a total of `{messages}` purges hiding in this channel!",color = discord.Color.random()))
    
    @commands.hybrid_command(extras = {"id": "108"},aliases = ['csn'],help = "Clears all sniped messages from the bot cache for the specified or current channel.")
    @commands.has_permissions(manage_messages = True)
    @app_commands.describe(channel = "The channel to clear snipes from.")
    async def clearsnipes(self,ctx,channel:discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            self.sniped_messages.pop(channel.id)
        except:
            pass
        try:
            self.edited_messages.pop(channel.id)
        except:
            pass
        try:
            self.removed_reactions.pop(channel.id)
        except:
            pass
        await ctx.send(embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Removed sniped cache for {channel.mention}",color = discord.Color.green()))



async def setup(client):
    await client.add_cog(Sniper(client))
