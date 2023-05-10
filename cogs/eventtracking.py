import discord
from discord import app_commands
from discord.ext import commands, menus
from utils import errors
from utils import methods
from utils import classes
from itertools import starmap
from typing import Literal
import datetime

class EventTracking(commands.Cog):
    """
        Tracking for quick server events, including leaderboards!
    """
    def __init__(self,client):
        self.hidden = False
        self.client = client
        self.short = "<a:event:923046835952697395> | Event Tracking"
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("EventTracking Category Loaded")

    def eman_role_check():
        async def predicate(ctx):
            if ctx.author.guild_permissions.administrator:
                return True

            raw = ctx.cog.client.db.guild_data.find_one({"_id":ctx.guild.id},{"settings.eventtracking.erole":1})
            role = methods.query(data = raw, search = ["settings","eventtracking","erole"])
            roleob = ctx.guild.get_role(role)
            if roleob not in ctx.author.roles:
                raise errors.SetupCheckFailure(message = "You are missing the event manager role!\nIf you are a server manager, try configuring with `/settings`.")
            return True
          
        return commands.check(predicate)
    
    async def increment_log(self,ctx,user,amount):
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$inc" : {f"eventtracking.{user.id}.total":amount}})
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$inc" : {f"eventtracking.{user.id}.weekly":amount}})
    
    async def get_leaderboard(self,ctx,category):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"eventtracking":1})
        log = methods.query(data = raw, search = ["eventtracking"])

        def check(a):
            try:
                return log[a].get(category,0)
            except:
                return 0
        
        if log:
            return sorted(log, key = lambda a: check(a), reverse = True), log
        else:
            return {},{}
    
    @commands.hybrid_group(id = "30")
    @eman_role_check()
    async def events(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse `/help events` to get a list of commands.")

    @events.command(id = "31",help = "Start an event with a ping and an embed. Increments tracking count by one.")
    @eman_role_check()
    @app_commands.describe(time = "How long until the event starts.",event = "The name of the event you want to run.",requirement = "Any requirements to participate.",reward = "Any prize for the event",location = "The text channel where the event is going to be.",donor = "The member that donated the prize.", message = "Any messsage you or the donor might have.")
    async def start(self,ctx,time,event,requirement,reward,location:discord.TextChannel,donor:discord.Member,message):
        if ctx.message.type == discord.MessageType.default:
            await ctx.message.delete()
        
        timestr = methods.timeparse(time,1,0)
        if isinstance(timestr,str):
            raise errors.ParsingError(message = timestr)
    
        until = discord.utils.utcnow() + timestr
        unix = int(until.replace(tzinfo=datetime.timezone.utc).timestamp())

        embed=discord.Embed(title="<a:event:923046835952697395> Event Starting! <a:event:923046835952697395>" ,color=discord.Color.random())
        build = ""
        embed.set_author(name="Hosted by " + ctx.author.display_name,icon_url=ctx.author.avatar)
        embed.set_thumbnail(url=ctx.guild.icon)
        build += f"**Event Type:** {event}\n**Requirement:** {requirement}\n**Reward:** {reward}\n**Channel:** {location.mention}\n"
        build += f"**Donor:**{donor.mention}\n**Message:** {message}\n"
        build += f"\nThe event begins <t:{unix}:R>"
        embed.description = build
        embed.set_footer(text = "Good luck!")

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{"settings.eventtracking":1})
        role = methods.query(data = raw, search = ["settings","eventtracking","ping"])

        if ctx.message.type == discord.MessageType.default:
            await ctx.message.delete()

        if role:
            message = await ctx.send(f"<@{role}> {event} in {location.mention}",embed = embed)
        else:
            message = await ctx.send(embed = embed)
        
        await self.increment_log(ctx,ctx.author,1)
        logging = methods.query(data = raw, search = ["settings","eventtracking","logging"])
        logchannel = ctx.guild.get_channel(logging)
        if logchannel:
            embed = discord.Embed(title=f"Event Recorded for {ctx.author.name}",description = f"{ctx.author.mention}",color = discord.Color.random())
            embed.add_field(name = "Event Information:",value = f"[Link to Event]({message.jump_url})\nEvent Type: {type}\nEvent Reward: {reward}\nEvent Donor: {donor}")
            embed.timestamp = datetime.datetime.now()
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await logchannel.send(embed = embed)
    
    @events.command(id = "32", help = "Add a certain amount of events to your log.")
    @eman_role_check()
    @app_commands.describe(amount = "The amount of events you want to log.")
    async def log(self,ctx,amount: commands.Range[int,0]):
        await self.increment_log(ctx,ctx.author,amount)
        
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"eventtracking.{ctx.author.id}.total":1})
        total = methods.query(data = raw, search = ["eventtracking",str(ctx.author.id),"total"]) or 0
        embed = discord.Embed(description = f"Logged `{amount}` event(s) for {ctx.author.mention}. They now have `{total}` events logged!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
        
    @events.command(id = "33", help = "Shows the amount of events you or another user has done.")
    @eman_role_check()
    @app_commands.describe(member = "The member you are checking the event count for.")
    async def amount(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"eventtracking.{member.id}":1})
        total, weekly = methods.query(data = raw, search = ["eventtracking",str(member.id),"total"]) or 0,methods.query(data = raw, search = ["eventtracking",str(member.id),"weekly"]) or 0
        embed=discord.Embed(description =f"__**Event Details for {member}**__\nTotal Event Amount for: `{total}` Events\nWeekly Event Amount: `{weekly}` Events",color=discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed=embed)
    
    @events.command(id = "34", aliases = ['eventlb','elb','eleaderboard'], help = "Show the weekly or total events leaderboard")
    @eman_role_check()
    @app_commands.describe(category = "The type of leaderboard you want to check.")
    async def leaderboard(self,ctx,category: Literal['total','weekly'] = None):
        category = category or 'total'
        members,log = await self.get_leaderboard(ctx,category)

        if not log:
            raise errors.NoDataError(message = "There is no event data for this server!")
        
        formatter = EventPageSource(members,log,category,self.client)
        menu = classes.MenuPages(formatter)
        await menu.start(ctx)
    
    @events.command(id = "35", help = "Reset the weekly event count and show an embed of winners.")
    @commands.has_permissions(administrator= True)
    async def resetweekly(self,ctx):
        embed = discord.Embed(description = "<a:OB_Loading:907101653692456991> Resetting weekly leaderboard! Please wait...",color = discord.Color.yellow())
        message = await ctx.reply(embed = embed)
        members, log = await self.get_leaderboard(ctx,"weekly")
        embed = discord.Embed(title = "Weekly Leaderboard Reset",description = "This week's winners are below",color = discord.Color.gold())
        for place,user in enumerate(members[:3]):
            amount = log[user].get("weekly",0)
            embed.add_field(name = f"Rank #{place+1}",value = f"<@{user}> `{amount}` Events",inline = False)
        
        for user in log:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset" : {f"eventtracking.{user}.weekly":""}})
        
        await message.edit(embed = embed)                                   

    @events.command(id = "36", help = "Set the event log amount for a specified user.")
    @commands.has_permissions(administrator= True)
    @app_commands.describe(member = "The member to set the event count for.", events = "How many events the member should have.",category = "The type of event that should be changed.")
    async def set(self, ctx,member:discord.Member,events :commands.Range[int,0],category: Literal['total','weekly'] = None):
        category = category or 'total'
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"eventtracking.{member.id}.{category}":1})
        amount = methods.query(data = raw, search = ["eventtracking",str(member.id),category]) or 0
        
        if events == 0 and category == "weekly":
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset" : {f"eventtracking.{member.id}.{category}":""}})
        elif events == 0 and category == "total":
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset" : {f"eventtracking.{member.id}":""}})
        else:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set" : {f"eventtracking.{member.id}.{category}":events}})
        
        embed = discord.Embed(description = f"Changed event log amount for **{member}** from `{amount}` to `{events}` under the `{category}` category!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)


class EventPageSource(menus.ListPageSource):
    def __init__(self,data,log,category,client):
        super().__init__(data, per_page = 10)
        self.log = log
        self.category = category
        self.client = client

    def format_leaderboard_entry(self,place,member):
        return f"**{place}. <@{member}>** `{self.log[member].get(self.category,0)} events`"
    
    async def format_page(self,menu,members):
        page = menu.current_page
        max_page = self.get_max_pages()
        starting_number = page * self.per_page + 1
        iterator = starmap(self.format_leaderboard_entry, enumerate(members, start = starting_number))
        page_content = "\n".join(iterator)
        
        embed = discord.Embed(title = f"Events Leaderboard [{page + 1}/{max_page}]", description = page_content, color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        return embed


async def setup(client):
    await client.add_cog(EventTracking(client))

