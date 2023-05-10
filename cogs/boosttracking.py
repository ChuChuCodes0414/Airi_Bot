import discord
from discord.ext import commands
from discord import app_commands
import datetime
from utils import errors
from utils import methods

class BoostTracking(commands.Cog):
    """
        Booot tracking that is somewhat reliable in certain circumstances due to Discord limitations.
    """
    def __init__(self,client):
        self.hidden = False
        self.client = client
        self.short = "<a:boost:1012396797223768094> | Boost Tracking"
        self.active = []
    
    def cache(self,data):
        for guild in data:
            if methods.query(guild,["settings","boosttracking","active"]):
                self.active.append(guild["_id"])
        print("BoostTracking Cache Loaded")
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("BoostTracking Category Loaded")
    
    def boost_active_check():
        def predicate(ctx):
            if not ctx.guild.id in ctx.cog.active:
                raise errors.NotEnabledError(message = "Boost tracking is not enabled!\nIf you are a server manager, use `/settings` to get started.")
            return True
        return commands.check(predicate)
    
    async def pull_boosts(self,guild,member):
        raw = self.client.db.guild_data.find_one({"_id":guild.id},{f"boosttracking.{member.id}":1}) or {}
        return methods.query(data = raw, search = ["boosttracking",str(member.id)])

    # Handles Boosts
    @commands.Cog.listener()
    async def on_message(self,message):
        if not message.guild or str(message.guild.id) not in self.active:
            return
        description = None
        if message.type == discord.MessageType.premium_guild_subscription:
            description = f"The server now has `{message.guild.premium_subscription_count}` boosts."
        elif message.type == discord.MessageType.premium_guild_tier_1:
            description = f"The server has reached **Level One**!\nThere are now `{message.guild.premium_subscription_count}` boosts."
        elif message.type == discord.MessageType.premium_guild_tier_2:
            description = f"The server has reached **Level Two**!\nThere are now `{message.guild.premium_subscription_count}` boosts."
        elif message.type == discord.MessageType.premium_guild_tier_3:
            description = f"The server has reached **Level Three**!\nThere are now `{message.guild.premium_subscription_count}` boosts."
        
        if not description:
            return

        self.db.guild_data.update_one({"_id":message.guild.id},{"$inc" : {f"boosttracking.{message.author.id}":1}},upsert = True)
        raw = self.client.db.guild_data.find_one({"_id":message.guild.id},{"settings.boosttracking":1}) or {}
        achannel = methods.query(data = raw, search = ["settings","boosttracking","announce"])
        achannel = message.guild.get_channel(achannel)
        if achannel:
            embed = discord.Embed(title = f"🎉 {message.author} just boosted the server! 🎉",description = description)
            embed.set_thumbnail(url = message.author.avatar.url)
            embed.set_footer(text = "Thank you for boosting!!")
            await achannel.send(embed = embed)
        lchannel = methods.query(data = raw, search = ["settings","boosttracking","logging"])
        lchannel = message.guild.get_channel(lchannel)
        if lchannel:
            boostcount = await self.pull_boosts(message.guild,message.author)
            embed = discord.Embed(title = f"{message.author} has just boosted.",description = f"{message.author.mention} (`{message.author.id}`)\nCurrent boost count: {boostcount}\nAnnounced at: {achannel.mention if achannel else 'None'}",color = discord.Color.random())
            embed.timestamp = discord.utils.utcnow()
            await lchannel.send(embed = embed)
    
    # For when the member unboosts and loses the role
    @commands.Cog.listener()
    async def on_member_update(self,member_before,member_after):
        if str(member_before.guild.id) not in self.active:
            return
        if member_before.guild.premium_subscriber_role in member_before.roles and member_before.guild.premium_subscriber_role not in member_after.roles:
            current = await self.pull_boosts(member_before.guild,member_before)

            if current:
                self.client.db.guild_data.update_one({"_id":member_before.guild.id},{"$unset" : {f"boosttracking.{member_before.id}":""}})
            
            raw = self.client.db.guild_data.find_one({"_id":member_before.guild.id},{"settings.boosttracking":1}) or {}
            lchannel = methods.query(data = raw, search = ["settings","boosttracking","logging"])
            lchannel = member_before.guild.get_channel(lchannel)
            if lchannel:
                embed = discord.Embed(title = f"{member_before} has just removed all boosts.",description = f"{member_before.mention} (`{member_before.id}`)\nPrevious boost count: {current}",color = discord.Color.random())
                unix = int(member_before.premium_since.replace(tzinfo=datetime.timezone.utc).timestamp())
                embed.add_field(name = "Boost Start Date",value = f"<t:{unix}:F> (<t:{unix}:R>)")
                embed.timestamp = discord.utils.utcnow()
                await lchannel.send(embed = embed)
    
    # For when a member leaves and subsequently unboosts
    @commands.Cog.listener()
    async def on_member_remove(self,member):
        if str(member.guild.id) not in self.active:
            return
        current = await self.pull_boosts(member.guild,member)

        if current:
            self.client.db.guild_data.update_one({"_id":member.guild.id},{"$unset" : {f"boosttracking.{member.id}":""}})
            raw = self.client.db.guild_data.find_one({"_id":member.guild.id},{"settings.boosttracking":1}) or {}
            lchannel = methods.query(data = raw, search = ["settings","boosttracking","logging"])
            lchannel = member.guild.get_channel(lchannel)
            if lchannel:
                embed = discord.Embed(title = f"{member} has just left the server!",description = f"{member.mention} (`{member.id}`)\nPrevious boost count: {current}",color = discord.Color.random())
                unix = int(member.premium_since.replace(tzinfo=datetime.timezone.utc).timestamp())
                embed.add_field(name = "Boost Start Date",value = f"<t:{unix}:F> (<t:{unix}:R>)")
                embed.timestamp = discord.utils.utcnow()
                await lchannel.send(embed = embed)
    
    @commands.hybrid_command(id = "10",help = "View boost tracking statistics for the server.")
    @boost_active_check()
    async def boostserverinfo(self,ctx):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{"boosttracking":1}) or {}
        data = methods.query(data = raw, search = ["boosttracking"]) or {}
        boostcount = 0
        for person,boosts in data.items():
            boostcount += boosts

        embed = discord.Embed(title = f"Boost Information for {ctx.guild.name}",description = f"Boost Level {ctx.guild.premium_tier}",color = discord.Color.random())

        embed.add_field(name = "Boost Count", value = f"Server Boosts: {ctx.guild.premium_subscription_count}\nBot Recorded Boosts: {boostcount}")
        embed.add_field(name = "Boost Member Count", value = f"Members Boosting: {len(ctx.guild.premium_subscribers)}\nBot Recorded Members: {len(data)}")
        if ctx.guild.premium_subscriber_role:
            embed.add_field(name = "Boost Role", value = ctx.guild.premium_subscriber_role.mention, inline = False)
        else:
            embed.add_field(name = "Boost Role", value = "No boost role found!", inline = False)
        embed.set_footer(icon_url = self.client.user.avatar.url,text = f"{self.client.user.name} | Edit boost tracking settings with /settings")
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(id = "11",help = "View boost tracking statistics for a member.")
    @boost_active_check()
    @app_commands.describe(member = "The member to check boost information for.")
    async def boostmemberinfo(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        boostcount = await self.pull_boosts(ctx.guild,member)

        if member.premium_since:
            unix = int(member.premium_since.replace(tzinfo=datetime.timezone.utc).timestamp())
            embed = discord.Embed(title = f"Boost Information for {member}",description = f"Boost Count: `{boostcount}`\nBoosting Since: <t:{unix}:F> (<t:{unix}:R>)",color = discord.Color.random())
        else:
            embed = discord.Embed(title = f"Boost Information for {member}",description = f"This member is not boosting!\nBoost Count: `{boostcount}`",color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)

    @commands.hybrid_command(id = "12",help = "Set the boost count for a member.")
    @commands.has_guild_permissions(administrator = True)
    @boost_active_check()
    @app_commands.describe(member = "The member to set boost information for.")
    @app_commands.describe(boosts = "The number of boosts the member has.")
    async def boostset(self,ctx,member:discord.Member,boosts: commands.Range[int,0]):
        boostcount = boostcount = await self.pull_boosts(ctx.guild,member)
        if boosts == 0:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset" : {f"boosttracking.{member.id}":""}})
        else:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set" : {f"boosttracking.{member.id}":boosts}},upsert = True)

        embed = discord.Embed(title = f"Boost Count Updated for {member}!", description = f"Previous Boost Count: `{boostcount}`\nNew Boost Count: `{boosts}`",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)

async def setup(client):
    await client.add_cog(BoostTracking(client))