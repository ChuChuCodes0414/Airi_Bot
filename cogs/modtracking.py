import discord
from itertools import starmap, chain
from discord.ext import commands, menus
from discord import ui, app_commands
import datetime
from utils import methods, errors, classes

class ModTracking(commands.Cog):
    """
        Logging for mods or staff activity tracking.
    """
    def __init__(self,client):
        self.client = client
        self.short = "<:modbadge:949857487341879396> | Mod Tracking"
    
    def modtrack_role_check():
        async def predicate(ctx):
            if ctx.author.guild_permissions.administrator:
                return True

            raw = ctx.cog.client.db.guild_data.find_one({"_id":ctx.guild.id},{"settings.modtracking.mrole":1})
            role = methods.query(data = raw, search = ["settings","modtracking","mrole"])
            roleob = ctx.guild.get_role(role)
            if roleob not in ctx.author.roles:
                raise errors.SetupCheckFailure(message = "You are missing the mod role!\nIf you are a server manager, try configuring with `/settings`.")
            return True
          
        return commands.check(predicate)
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('Mod Tracking Category Loaded.')

    @commands.hybrid_group(id = "80")
    @modtrack_role_check()
    async def modtracking(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse `/help modtracking` to get a list of commands.")
    
    @modtracking.command(id = "81",help = "Log an action that you have completed.")
    @modtrack_role_check()
    @app_commands.describe(action = "What action you have done.")
    async def log(self,ctx,*,action):
        now = datetime.datetime.now()
        formatnow = str(now.month) + "-" + str(now.day) + "-" + str(now.year) + " " + str(now.hour) + ":" + str(now.minute)
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$push":{f"modtracking.{ctx.author.id}":[action,formatnow]}})
        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully logged **{action}**!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{"settings.modtracking.logging":1})
        logging = methods.query(data = raw, search = ["settings","modtracking","logging"])
        logchannel = ctx.guild.get_channel(logging)
        if logchannel:
            embed = discord.Embed(title=f"Mod Action Recorded for {ctx.message.author.name}",description = f"{ctx.message.author.mention}",
                                color=discord.Color.green())

            embed.add_field(name = "Action Recorded:",value = f"[Link to Command]({ctx.message.jump_url})\nAction Details: {action}")

            embed.timestamp = datetime.datetime.now()
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await logchannel.send(embed = embed)

    @modtracking.command(id = "82",help = "Edit an action that you have already logged.")
    @modtrack_role_check()
    @app_commands.describe(index = "The numerical identifier for the action.",action = "The detail to edit the action to.")
    async def edit(self,ctx,index:commands.Range[int,0],*,action):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"modtracking.{ctx.author.id}":1})
        actions = methods.query(data = raw,search = ["modtracking",str(ctx.author.id)]) or []
        
        if len(actions) < index:
            raise errors.ParsingError(message = f"You tried to edit index `{index}`, but only `{len(actions)}` indexes exist.")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"modtracking.{ctx.author.id}.{index-1}.0":action}})
        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully edited `{index}` to **{action}**!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @modtracking.command(id = "83",help = "Remove one of your logs.")
    @modtrack_role_check()
    @app_commands.describe(index = "The index of the log you want to remove.")
    async def remove(self,ctx,index:commands.Range[int,0]):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"modtracking.{ctx.author.id}":1})
        actions = methods.query(data = raw,search = ["modtracking",str(ctx.author.id)]) or []
        
        if len(actions) < index:
            raise errors.ParsingError(message = f"You tried to remove index `{index}`, but only `{len(actions)}` indexes exist.")

        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$pull":{f"modtracking.{ctx.author.id}":actions[index-1]}})

        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully removed `{index}`!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @modtracking.command(id = "84",help = "Clear all mod tracking data for a member.")
    @commands.has_permissions(administrator = True)
    @app_commands.describe(member = "The member of whom to clear the mod tracking data for.")
    async def clear(self,ctx,member:discord.Member):
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{f"modtracking.{member.id}":""}})
        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully removed all data for **{member}**!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @modtracking.command(id = "85",help = "View the amount of logs you or another person has.")
    @modtrack_role_check()
    @app_commands.describe(member = "The member of whom to check the log amount for.")
    async def amount(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"modtracking.{member.id}":1})
        actions = methods.query(data = raw,search = ["modtracking",str(member.id)]) or []
        embed = discord.Embed(description = f"Mod Tracking Logs for **{member}**: `{len(actions)}` actions",color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @modtracking.command(id = "86",help = "View the details of logged actions for yourself or for someone else.")
    @modtrack_role_check()
    @app_commands.describe(member = "The member of whom to check the details for.")
    async def detail(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"modtracking.{member.id}":1})
        actions = methods.query(data = raw,search = ["modtracking",str(member.id)]) or []
        actions.reverse()
        formatter = ModPageSource(member,actions)
        menu = classes.MenuPages(formatter)
        await menu.start(ctx)
    
    @modtracking.command(id = "87",help = "Show the mod actions leaderboard.")
    @modtrack_role_check()
    async def leaderboard(self,ctx):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"modtracking":1})
        data = methods.query(data = raw,search = ["modtracking"])

        build = {}
        if not data:
            users,log =  [],build
        else:
            for person in data:
                build[person] = len(data[person])

            users,log = sorted(build, key=build.get, reverse=True) , build
        
        formatter = ModLBPageSource(users,log)
        menu = classes.MenuPages(formatter)
        await menu.start(ctx)

class ModPageSource(menus.ListPageSource):
    def __init__(self,user,logs):
        super().__init__(logs,per_page=9)
        self.user = user
        self.amount = len(logs)
    def format_action_detail(self,no, log):
        return f"{log[1]}\n{log[0]}"
    async def format_page(self,menu,logs):
        page = menu.current_page
        max_page = self.get_max_pages()
        starting_number = page * self.per_page + 1
        iterator = starmap(self.format_action_detail, enumerate(logs, start=starting_number))
        embed = discord.Embed(title = f"Mod Action Details for {self.user}",description = f"`{self.amount} Actions Logged`",color = discord.Color.random())
        for count,item in enumerate(iterator):
            embed.add_field(name = f"Action {self.amount-(count + starting_number) + 1}",value = item)
        embed.set_footer(text=f"Use the buttons below to navigate pages! | Page {page + 1}/{max_page}") 
        return embed

class ModLBPageSource(menus.ListPageSource):
    def __init__(self, data, log):
        super().__init__(data, per_page=10)
        self.log = log
    def format_leaderboard_entry(self, no, user):
        return f"**{no}. <@{user}>** `{self.log[user]} Actions Logged`"
    async def format_page(self, menu, users):
        page = menu.current_page
        max_page = self.get_max_pages()
        starting_number = page * self.per_page + 1
        iterator = starmap(self.format_leaderboard_entry, enumerate(users, start=starting_number))
        page_content = "\n".join(iterator)
        embed = discord.Embed(
            title=f"Mod Tracking Leaderboard [{page + 1}/{max_page}]", 
            description=page_content,
            color= discord.Color.random()
        )
        embed.set_footer(text=f"Use the buttons below to navigate pages!") 
        return embed

async def setup(client):
    await client.add_cog(ModTracking(client))
