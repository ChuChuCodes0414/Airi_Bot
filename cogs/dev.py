import discord
from discord.ext import commands, tasks
import datetime
from utils import methods, errors

class Dev(commands.Cog):
    def __init__(self,client):
        self.hidden = True
        self.client = client
        self.commands = {}
        self.users = {}
        self.guilds = {}
        self.post_recap.start()
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Dev Category Loaded")
    
    @tasks.loop(hours=24,reconnect = True)
    async def post_recap(self):
        sortedcomm = sorted(self.commands, key=self.commands.get, reverse=True)
        commres = ""
        x = min(len(self.commands),10)
        for command in sortedcomm[:x]:
            commres += f"**{command}:** {self.commands[command]} uses\n"
        sortedusers = sorted(self.users, key=self.users.get, reverse=True)
        userres = ""
        x = min(len(self.users),10)
        for user in sortedusers[:x]:
            userres += f"**{user}:** {self.users[user]} commands\n"
        sortedguilds = sorted(self.guilds,key = self.guilds.get,reverse = True)
        guildsres = ""
        x = min(len(self.guilds),10)
        for guild in sortedguilds[:x]:
            guildsres += f"**{guild.name}** {self.guilds[guild]} commands\n"
        now = discord.utils.utcnow()
        unix = int(now.replace(tzinfo=datetime.timezone.utc).timestamp())
        embed = discord.Embed(title = "Daily Command Recap",description = f"<t:{unix}:F>\nUnique Commands: {len(self.commands)} | Total Users: {len(self.users)} | Total Guilds: {len(self.guilds)}")
        embed.add_field(name = "Commands",value = commres or "None")
        embed.add_field(name = "Users",value = userres or "None")
        embed.add_field(name = "Guilds",value = guildsres or "None")
        channel = self.client.get_channel(int(977037266172137505))
        await channel.send(embed = embed)
        self.commands,self.users,self.guilds = {},{},{}
    
    def bot_mod_check():
        async def predicate(ctx):
            raw = ctx.cog.client.db.user_data.find_one({"_id":ctx.author.id},{"botmod":1})
            botmod = methods.query(data = raw, search = ["botmod"])
            if botmod:
                return True
            raise errors.SetupCheckFailure(message = "You are not a bot moderator!")
          
        return commands.check(predicate)

    @post_recap.before_loop
    async def wait_until_7am(self):
        now = datetime.datetime.utcnow()
        next_run = now.replace(hour=16, minute=0, second=5)

        if next_run < now:
            next_run += datetime.timedelta(days=1)
        print("Waiting until 7am to post command recap!")
        await discord.utils.sleep_until(next_run)
    
    async def cog_unload(self):
        self.post_recap.cancel()
    
    @commands.Cog.listener()
    async def on_message(self,message):
        if message.author == self.client.user:
            return
        if message.guild:
            if message.content == self.client.user.mention:
                data = self.client.db.guild_data.find_one({"_id":message.guild.id},{"settings.general.prefix":1}) or {}
                prefix = methods.query(data = data,search = ["settings","general","prefix"]) or "a?"
                embed = discord.Embed(title="Hello!",description=f"The prefix in this server is: `{prefix}`\nAll commands work on slash too!", color=discord.Color.random())
                embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
                await message.reply(embed = embed)

    @commands.Cog.listener()
    async def on_command_completion(self,ctx):
        self.commands[ctx.command.name] = self.commands.get(ctx.command.name,0) + 1
        self.users[ctx.author] = self.users.get(ctx.author,0) + 1
        self.guilds[ctx.guild] = self.guilds.get(ctx.guild,0) + 1
    
    @commands.Cog.listener()
    async def on_guild_join(self,guild):
        raw = self.client.db.guild_data.find_one({"_id":guild.id})

        if not raw:
            self.client.db.guild_data.insert_one({"_id":guild.id,"prefix":"a?"})

        channel = self.client.get_channel(int(849761988628316191))

        embed = discord.Embed(title = f'Joined {guild.name}',description = f'ID: {guild.id}',color = discord.Color.green())
        embed.set_thumbnail(url = guild.icon)

        embed.add_field(name = "Server Owner",value = f'{guild.owner} (ID: {guild.owner.id})',inline = True)

        humans = len([m for m in guild.members if not m.bot])
        bots = guild.member_count-humans
        embed.add_field(name = "Member Count",value = f'Total Members: {guild.member_count}\nHuman Members: {humans}\nBots: {bots}\nPercentage: {round(bots/guild.member_count,1)}%',inline = True)

        embed.add_field(name = "Creation Date",value = guild.created_at.strftime("%Y-%m-%d %H:%M"),inline = True)

        embed.timestamp = datetime.datetime.now()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await channel.send(embed = embed)

    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        channel = self.client.get_channel(int(849761988628316191))

        embed = discord.Embed(title = f'Removed from {guild.name}',description = f'ID: {guild.id}',color = discord.Color.red())
        embed.set_thumbnail(url = guild.icon)

        embed.add_field(name = "Server Owner",value = f'{guild.owner} (ID: {guild.owner.id})',inline = True)

        humans = len([m for m in guild.members if not m.bot])
        bots = guild.member_count-humans
        embed.add_field(name = "Member Count",value = f'Total Members: {guild.member_count}\nHuman Members: {humans}\nBots: {bots}\nPercentage: {round(bots/guild.member_count,1)}%',inline = True)

        embed.add_field(name = "Creation Date",value = guild.created_at.strftime("%Y-%m-%d %H:%M"),inline = True)

        embed.timestamp = datetime.datetime.now()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await channel.send(embed = embed)

    @commands.command(hidden = True)
    @commands.is_owner()
    async def sync(self,ctx,type:str = None):
        type = type or "global"

        if type == "global":
            response = await self.client.tree.sync()
        elif type == "guild":
            guild = self.client.get_guild(870125583886065674)
            self.client.tree.copy_global_to(guild=guild)
            response = await self.client.tree.sync(guild = guild)
        
        await ctx.reply(embed = discord.Embed(description = f"Synced `{len(response)}` Commands to `{type}`!",color = discord.Color.green()))
    
    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self,ctx,extension):
        await self.client.reload_extension(f'cogs.{extension}')
        cog = self.client.get_cog(extension)
        if hasattr(cog,"cache"):
            data = list(self.client.db.guild_data.find({},{"settings":1}))
            cog.cache(data)
        if hasattr(cog,"user_cache"):
            data = list(self.client.db.user_data.find({},{"settings":1}))
            cog.user_cache(data)
        await ctx.reply(embed = discord.Embed(description = f'Reloaded {extension} sucessfully',color = discord.Color.green()))
    @reload.error
    async def reload_error(self,ctx, error):
        await ctx.reply(embed = discord.Embed(description = f'`{error}`',color = discord.Color.red()))
    
    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self,ctx,extension):
        await self.client.load_extension(f'cogs.{extension}')
        cog = self.client.get_cog(extension)
        if hasattr(cog,"cache"):
            data = list(self.client.db.guild_data.find({},{"settings":1}))
            cog.cache(data)
        await ctx.reply(embed = discord.Embed(description = f'Loaded {extension} sucessfully',color = discord.Color.green()))
    @load.error
    async def load_error(self,ctx, error):
        await ctx.reply(embed = discord.Embed(description = f'`{error}`',color = discord.Color.red()))
    
    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self,ctx,extension):
        await self.client.unload_extension(f'cogs.{extension}')
        await ctx.reply(embed = discord.Embed(description = f'Unloaded {extension} sucessfully',color = discord.Color.green()))
    @unload.error
    async def unload_error(self,ctx, error):
        await ctx.reply(embed = discord.Embed(description = f'`{error}`',color = discord.Color.red()))
    
    @commands.command(hidden = True)
    @bot_mod_check()
    async def blacklist(self,ctx,user:discord.User,length:str,*,reason:str = None):
        time = methods.timeparse(str(length))
        if isinstance(time,str):
            return await ctx.reply(embed = discord.Embed(description = time,color = discord.Color.red()))

        unix = int((time + datetime.datetime.utcnow()).replace(tzinfo=datetime.timezone.utc).timestamp())
        self.client.db.user_data.update_one({"_id":user.id},{"$set":{"settings.blacklist":{"until":unix,"reason":reason}}},upsert = True)

        try:
            dm = user.dm_channel
            if dm == None:
                dm = await user.create_dm()
            embed = discord.Embed(title = "You have been bot blacklisted!",description = f"**Blacklisted Until:** <t:{unix}:f> (<t:{unix}:R>)\n**Blacklist Reason:** {reason}\n\nDuring this time, you cannot run any commands. If you feel you were incorrectly blacklisted, please appeal in the [Support Server](https://discord.com/invite/9pmGDc8pqQ).",color = discord.Color.red())
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await dm.send(embed = embed)
            dm = True
        except:
            dm = False

        embed = discord.Embed(title = "Blacklist Successful",description = f"**Blacklisted:** {user.mention} | {user} (`{user.id}`)\n**Action Taken By:** {ctx.author.mention} {ctx.author} (`{ctx.author.id}`)\n**Blacklisted Until:** <t:{unix}:f> (<t:{unix}:R>)\n**Blacklist Reason:** {reason}",color = discord.Color.green())
        if dm:
            embed.add_field(name = "Dm Sent?",value = "<:greentick:930931553478008865> Success!")
        else:
            embed.add_field(name = "Dm Sent?",value = "<:redtick:930931511685955604> Failed!")
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.reply(embed = embed)
        channel = self.client.get_channel(978029124243292210)
        await channel.send(embed = embed)
    
    @commands.command(hidden = True)
    @bot_mod_check()
    async def unblacklist(self,ctx,user:discord.User,*,reason:str = None):
        self.client.db.user_data.update_one({"_id":user.id},{"$unset":{"settings.blacklist":""}},upsert = True)

        try:
            dm = user.dm_channel
            if dm == None:
                dm = await user.create_dm()
            embed = discord.Embed(title = "You have been unblacklisted!",description = f"**Unblacklist Reason:** {reason}",color = discord.Color.green())
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await dm.send(embed = embed)
            dm = True
        except:
            dm = False

        embed = discord.Embed(title = "Unblacklist Successful",description = f"**Unblacklisted:** {user.mention} | {user} (`{user.id}`)\n**Action Taken By:** {ctx.author.mention} {ctx.author} (`{ctx.author.id}`)\n**Unblacklist Reason:** {reason}",color = discord.Color.green())
        if dm:
            embed.add_field(name = "Dm Sent?",value = "<:greentick:930931553478008865> Success!")
        else:
            embed.add_field(name = "Dm Sent?",value = "<:redtick:930931511685955604> Failed!")
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.reply(embed = embed)
        channel = self.client.get_channel(978029124243292210)
        await channel.send(embed = embed)

async def setup(client):
    await client.add_cog(Dev(client))