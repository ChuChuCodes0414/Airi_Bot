import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import pytz
import ast
import operator as op
import functools
from utils import methods, errors

class Utility(commands.Cog):
    def __init__(self,client):
        self.client = client
        self.short = "🛠 | Utility"
        self.active = {}
        self.afk = {}
        self.ignore = {}
        self.ar = {}

        self.operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: self.power, ast.BitXor: op.xor,
             ast.USub: op.neg}
        self.eval_ = self.limit(max_=10**1000)(self.eval_)

        self.ctx_menu = app_commands.ContextMenu(
            name='Member Info',
            callback=self.contextmemberinfo,
        )
        self.client.tree.add_command(self.ctx_menu)

    def cache(self,data):
        for guild in data:
            settings = methods.query(guild,["settings","utility"]) or {}
            if settings.get("bumpchannel",None):
                self.active[str(guild["_id"])] = settings.get("bumpchannel")
            if settings.get("afkchannels",None):
                self.ignore[str(guild["_id"])] = settings.get("afkchannels")
            
            auto = methods.query(guild,["utility","ar"]) or {}
            if auto:
                self.ar[str(guild["_id"])] = auto

            afk = methods.query(guild,["utility","afk"])
            if afk:
                self.afk[str(guild["_id"])] = afk
            
        print("Utility Guild Cache Loaded")
    
    def eval_(self,node):
        if isinstance(node, ast.Num): # <number>
            return node.n
        elif isinstance(node, ast.BinOp): # <left> <operator> <right>
            return self.operators[type(node.op)](self.eval_(node.left), self.eval_(node.right))
        elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
            return self.operators[type(node.op)](self.eval_(node.operand))
        else:
            raise TypeError(node)
    
    def power(self,a,b):
        if any(abs(n) > 100 for n in [a, b]):
            raise ValueError((a,b))
        return op.pow(a, b)

    def limit(self,max_=None):
        """Return decorator that limits allowed returned values."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                ret = func(*args, **kwargs)
                try:
                    mag = abs(ret)
                except TypeError:
                    pass # not applicable
                else:
                    if mag > max_:
                        raise ValueError(ret)
                return ret
            return wrapper
        return decorator

    def eval_expr(self,expr):
        return self.eval_(ast.parse(expr, mode='eval').body)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Utility Category Loaded.")
    
    @commands.Cog.listener()
    async def on_message(self,message):
        if message.author.id == 302050872383242240 and message.channel.id == self.active.get(str(message.guild.id),None):
            if len(message.embeds) > 0:
                dict = message.embeds[0].to_dict()
                if dict["description"].startswith("Bump done!"):
                    overwrite = message.channel.overwrites_for(message.guild.default_role)
                    overwrite.send_messages = False
                    await message.channel.set_permissions(message.guild.default_role, overwrite=overwrite)
                    await message.channel.send(embed = discord.Embed(description = f"Thank you for bumping! Make sure to leave a review at [disboard.org/server/{message.guild.id}](https://disboard.org/server/{message.guild.id})",color = discord.Color.random()))
                    await asyncio.sleep(7200)
                    overwrite = message.channel.overwrites_for(message.guild.default_role)
                    overwrite.send_messages = None
                    await message.channel.set_permissions(message.guild.default_role, overwrite=overwrite)
                    raw = self.client.db.guild_data.find_one({"_id":message.guild.id},{"settings.utility.bping":1})
                    ping = methods.query(data = raw, search = ["settings","utility","bping"])
                    embed = discord.Embed(description = f"It has been 2 hours since the last successful bump, could someone run </bump:947088344167366698>?",color = discord.Color.random())
                    embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
                    if ping:
                        await message.channel.send(f"<@&{ping}>",embed = embed)
                    else:
                        await message.channel.send(embed = embed)
            return
        if message.author.bot or not message.guild:
            return
        if str(message.guild.id) in self.ar:
            for word,reacts in self.ar[str(message.guild.id)].items():
                if word in message.content.lower():
                    for react in reacts:
                        await message.add_reaction(react)
                        await asyncio.sleep(0.3)
        if message.channel.id not in self.ignore.get(str(message.guild.id),[]) and self.afk.get(str(message.guild.id),{}).get(str(message.author.id),None) and not self.afk.get(str(message.guild.id)).get(str(message.author.id)).get("invulnerable"):
            pings = self.afk[str(message.guild.id)][str(message.author.id)].get("messages",[])
            self.afk[str(message.guild.id)].pop(str(message.author.id))
            self.client.db.guild_data.update_one({"_id":message.guild.id},{"$unset":{f"utility.afk.{message.author.id}":""}})
            if message.author.nick and message.author.nick.startswith("[AFK]"):
                try:
                    await message.author.edit(nick = message.author.nick[6:])
                except:
                    pass
            embed = discord.Embed(description = f"Welcome back **{message.author}**! I have removed your afk.")
            build = "\n".join(["[Link #" + str(x+1) + "](" + y + ")" for x,y in enumerate(pings[:-11:-1])])
            if len(build) > 0:
                embed.add_field(name = "Your most recent AFK mentions:",value = build)
                embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
                await message.reply(embed = embed)
            else:
                await message.reply(embed = embed, delete_after = 5)
        build = ""
        remove = []
        for mention in message.mentions:
            if str(mention.id) in self.afk.get(str(message.guild.id),{}) and not self.afk.get(str(message.guild.id),{}).get(str(mention.id)).get("cooldown"):
                build += f"**{mention}** is afk: {self.afk[str(message.guild.id)][str(mention.id)]['message']} (<t:{self.afk[str(message.guild.id)][str(mention.id)]['time']}:R>)\n"
                self.afk[str(message.guild.id)][str(mention.id)]["cooldown"] = True
                self.afk[str(message.guild.id)][str(mention.id)]["messages"].append(message.jump_url)
                self.client.db.guild_data.update_one({"_id":message.guild.id},{"$addToSet":{f"utility.afk.{mention.id}.messages":message.jump_url}})
                remove.append(mention)
        if build != "":
            embed = discord.Embed(description = build)
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await message.reply(embed = embed,delete_after = 5)
        await asyncio.sleep(10)
        for mention in remove:
            try:
                self.afk[str(message.guild.id)][str(mention.id)].pop("cooldown")
            except:
                pass
        
    @commands.hybrid_command(extras = {"id": "400"},name= "memberinfo",help = "View some basic information about a member.")
    @app_commands.describe(member = "The user to lookup information for.")
    async def memberinfo(self, ctx: commands.Context, member: discord.Member = None) -> None:
        member = member or ctx.author
        embed = discord.Embed(title = f"Member Information for {member}",description = f"{member.id} | {member.display_name}",color = member.color)
        embed.add_field(name = "Account Creation:",value = f"<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> (<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>)",inline = False)
        embed.add_field(name = "Joined At",value = f"<t:{int(member.joined_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> (<t:{int(member.joined_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>)",inline = False)
        embed.add_field(name = "Top Role",value = member.top_role.mention)
        embed.add_field(name = "Top 20 Roles",value = " ".join([x.mention for x in list(reversed(member.roles))[0:min(len(member.roles),20)]]))
        embed.set_thumbnail(url = member.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    async def contextmemberinfo(self, interaction: discord.Interaction, member: discord.Member = None) -> None:
        embed = discord.Embed(title = f"Member Information for {member}",description = f"{member.id} | {member.display_name}",color = member.color)
        embed.add_field(name = "Account Creation:",value = f"<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> (<t:{int(member.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>)",inline = False)
        embed.add_field(name = "Joined At",value = f"<t:{int(member.joined_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> (<t:{int(member.joined_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>)",inline = False)
        embed.add_field(name = "Top Role",value = member.top_role.mention)
        embed.add_field(name = "Top 20 Roles",value = " ".join([x.mention for x in list(reversed(member.roles))[0:min(len(member.roles),20)]]))
        embed.set_thumbnail(url = member.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await interaction.response.send_message(embed = embed,ephemeral = True)
    
    @commands.hybrid_command(extras = {"id": "401"},name = "serverinfo",help = "View some basic information about the current server.")
    async def serverinfo(self, ctx: commands.Context) -> None:
        embed = discord.Embed(title = f"Server Information for {ctx.guild.name}",description = ctx.guild.id,color = discord.Color.random())
        embed.add_field(name = "Creation Date",value = f"<t:{int(ctx.guild.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> (<t:{int(ctx.guild.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>)",inline = False)
        embed.add_field(name = "Server Owner",value = ctx.guild.owner)
        embed.add_field(name = "Vanity Invite",value = ctx.guild.vanity_url_code)
        embed.add_field(name = "Boost Status",value = f"Level {ctx.guild.premium_tier}\n{ctx.guild.premium_subscription_count} Boosts")
        embed.add_field(name = "Channel Statistics",value = f"{len(ctx.guild.text_channels)} Text Channels\n{len(ctx.guild.voice_channels)} Voice Channels")
        humans = len([m for m in ctx.guild.members if not m.bot])
        bots = ctx.guild.member_count-humans
        embed.add_field(name = "Member Statistics",value = f"Total Members: {len(ctx.guild.members)}\nHumans: {humans}\nBots: {bots}")
        embed.set_thumbnail(url = ctx.guild.icon)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "402"},name = "whois",help = "View some basic information for any discord user.")
    @app_commands.describe(user = "The user to lookup information for.")
    async def whois(self, ctx: commands.Context, user: discord.User = None) -> None:
        user = user or ctx.author
        embed = discord.Embed(title = f"User information for {user}",description = user.id,color = user.color)
        embed.add_field(name = "Account Creation:",value = f"<t:{int(user.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> (<t:{int(user.created_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:R>)",inline = False)
        mutuals = '\n'.join([x.name for x in user.mutual_guilds[:min(len(user.mutual_guilds),20)]])
        embed.add_field(name = "Mutual Servers",value = f"{len(user.mutual_guilds)} Mutuals\n{mutuals}")
        embed.set_thumbnail(url = user.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "403"},help = "Do some math expressions!")
    @app_commands.describe(expression = "The mathematical expression to do, like 1+1.")
    async def math(self, ctx: commands.Context,*,expression):
        try:
            res = self.eval_expr(expression)
            await ctx.reply(embed = discord.Embed(description = f"Result: `{'{:,}'.format(res)}`\nRaw: `{res}`"))
        except ValueError as e:
            raise errors.ParsingError(message = f"Your input is too large, or is an invalid value!")
        except:
            raise errors.ParsingError(message = f"I could not process your input!")
        
    @commands.hybrid_group(extras = {"id": "404"},name = "afk")
    async def afkbase(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `afk` to get a list of commands.")
    
    @afkbase.command(extras = {"id": "405"},name = "set",help = "Set your server afk to let other people know you aren't there!")
    @app_commands.describe(message = "The message to be displayed if someone mentions you.")
    async def set(self, ctx: commands.Context, *,message: str = None) -> None:
        message = message or "AFK"
        current = self.afk.get(str(ctx.guild.id),{}).get(str(ctx.author.id),None)
        if current:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"utility.afk.{ctx.author.id}.message":message}})
            self.afk[str(ctx.guild.id)][str(ctx.author.id)]["message"] = message
            self.afk[str(ctx.guild.id)][str(ctx.author.id)]["invlunerable"] = True
            embed = discord.Embed(description = f"I have updated your afk message to: {message}",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await ctx.reply(embed = embed,ephemeral = True)
            await asyncio.sleep(10)
            try:
                self.afk[str(ctx.guild.id)][str(ctx.author.id)].pop("invulnerable")
            except:
                pass
        else:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"utility.afk.{ctx.author.id}":{"message":message,"time":int(discord.utils.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp())}}})
            if self.afk.get(str(ctx.guild.id)):
                self.afk[str(ctx.guild.id)][str(ctx.author.id)] = {"message":message,"time":int(discord.utils.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp())}
            else:
                self.afk[str(ctx.guild.id)] = {str(ctx.author.id):{"message":message,"time":int(discord.utils.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp())}}
            self.afk[str(ctx.guild.id)][str(ctx.author.id)]["invulnerable"] = True
            self.afk[str(ctx.guild.id)][str(ctx.author.id)]["messages"] = []
            try:
                await ctx.author.edit(nick= "[AFK] " + ctx.author.display_name)
            except:
                pass
            await ctx.reply(embed = discord.Embed(description = f"I have set your afk to: {message}",color = discord.Color.green()))
            await asyncio.sleep(10)
            try:
                self.afk[str(ctx.guild.id)][str(ctx.author.id)].pop("invulnerable")
            except:
                pass
    
    @afkbase.command(extras = {"id": "406"},name = "remove",help = "As a moderator, remove the afk of a member.")
    @app_commands.describe(member = "The member to remove the afk from.")
    @commands.has_permissions(moderate_members = True)
    async def remove(self, ctx: commands.Context, member: discord.Member) -> None:
        if str(member.id) in self.afk.get(str(ctx.guild.id),{}):
            self.afk[str(ctx.guild.id)].pop(str(member.id))
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{f"utility.afk.{member.id}":""}})
            await ctx.reply(embed = discord.Embed(description = f"I have removed the afk status for **{member}**!",color = discord.Color.green()),ephemeral = True)
        else:
            raise errors.PreRequisiteError(messsage = f"**{member}** does not have an afk status set!")

    @commands.hybrid_group(extras = {"id": "407"},name = "time")
    async def time(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `time` to get a list of commands.")
    
    @time.command(extras = {"id": "408"},name = "set",help = "Set up your timezone in the bot.")
    @app_commands.describe(timezone = "Your timezone in tz database format.")
    async def timeset(self,ctx:commands.Context,timezone: str):
        if timezone not in pytz.all_timezones:
            return await ctx.reply(embed = discord.Embed(description = "I do not recognize that timezone! Please see [this page](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for a list of valid timezones.",color = discord.Color.red()),ephemeral = True)
        self.client.db.user_data.update_one({"_id":ctx.author.id},{"$set":{"utility.timezone":timezone}},upsert = True)
        utc_now = pytz.utc.localize(datetime.datetime.utcnow())
        there_now = utc_now.astimezone(pytz.timezone(timezone))
        await ctx.reply(embed = discord.Embed(description = f"I have set your timezone as **{timezone}**, where it should be **{there_now.strftime('%A, %B %d, %Y %I:%M %p (utc%z)')}**",color = discord.Color.green()))

    @time.command(extras = {"id": "409"},name = "me",help = "Check your own time, even though you could look at a clock nearby.")
    async def timeme(self,ctx:commands.Context):
        raw = self.client.db.user_data.find_one({"_id":ctx.author.id},{"utility.timezone":1})
        timezone = methods.query(data = raw,search = ["utility","timezone"])
        
        if not timezone:
            raise errors.PreRequisiteError(message = "Your timezone is not setup! Use </time set:1010989269122297869> first to get started.")

        utc_now = pytz.utc.localize(datetime.datetime.utcnow())
        there_now = utc_now.astimezone(pytz.timezone(timezone))
        await ctx.reply(embed = discord.Embed(description = f"For **{ctx.author}** in **{timezone}**\nIt is currently **{there_now.strftime('%A, %B %d, %Y %I:%M %p (utc%z)')}**\nYour Local Time: <t:{int(utc_now.replace(tzinfo=datetime.timezone.utc).timestamp())}:F>",color = discord.Color.green()))

    @time.command(extras = {"id": "410"},name = "check",help = "Check someone else's time, because they need to go to bed.")
    @app_commands.describe(member = "The member to check the time of.")
    async def timecheck(self,ctx:commands.Context, member: discord.Member):
        raw = self.client.db.user_data.find_one({"_id":member.id},{"utility.timezone":1})
        timezone = methods.query(data = raw,search = ["utility","timezone"])
        
        if not timezone:
           raise errors.PreRequisiteError(message = f"**{member}'s** timezone is not setup! Tell them to use </time set:1010989269122297869> first to get started.")

        utc_now = pytz.utc.localize(datetime.datetime.utcnow())
        there_now = utc_now.astimezone(pytz.timezone(timezone))
        await ctx.reply(embed = discord.Embed(description = f"For **{member}** in **{timezone}**\nIt is currently **{there_now.strftime('%A, %B %d, %Y %I:%M %p (utc%z)')}**\nYour Local Time: <t:{int(utc_now.replace(tzinfo=datetime.timezone.utc).timestamp())}:F>",color = discord.Color.green()))

    @commands.hybrid_group(extras = {"id": "411"},name = "react",help = "Manage auto reactions for your server.")
    async def react(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message =  "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `react` to get a list of commands.")
    
    @react.command(extras = {"id": "412"},name = "add",help = "Add an auto reaction to a word or phrase!")
    @app_commands.describe(word = "The word to be reacted to.")
    @app_commands.describe(emoji = "The emoji to react with")
    @commands.has_permissions(moderate_members = True)
    async def add(self,ctx: commands.Context, word:str, emoji: discord.Emoji) -> None:
        await ctx.defer()
        word = word.lower()
        if word.startswith("<@") and word.endswith(">"):
            try:
                member = await commands.converter.MemberConverter().convert(ctx,word)
                word = member.mention
            except:
                pass
        if not emoji.is_usable():
            raise errors.PreRequisiteError(message = f"I am not in the server where that emoji is located! Either add me to that server, or add that emoji to a server that I am in.")
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"utility.ar.{word}":1})
        current = methods.query(data = raw,search = ["utility","ar",str(word)]) or []
        if len(current) >= 10:
            raise errors.ParsingError(message = f"For lag purposes, more than 10 reacts to one word is not allowed!")
        if emoji.animated:
            emojitext = f"<a:{emoji.name}:{emoji.id}>"
        else:
            emojitext = f"<:{emoji.name}:{emoji.id}>"
        if emoji in current:
            raise errors.PreRequisiteError(message = f"The word **{word}** already has the reaction {emoji} setup!")
        current.append(emojitext)
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"utility.ar.{word}":current}})
        if self.ar.get(str(ctx.guild.id),None):
            self.ar[str(ctx.guild.id)][word] = current
        else:
            self.ar[str(ctx.guild.id)] = {word:current}
        embed = discord.Embed(description = f"Added an autoreaction for **{word}** as {emoji}!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @react.command(extras = {"id": "413"},name = "remove",help = "Remove an auto reaction to a word or phrase!")
    @app_commands.describe(word = "The word to be reacted to.")
    @app_commands.describe(emoji = "The emoji to react with")
    @commands.has_permissions(moderate_members = True)
    async def remove(self,ctx: commands.Context, word: str, emoji: discord.Emoji) -> None:
        await ctx.defer()
        word = word.lower()
        if word.startswith("<@") and word.endswith(">"):
            try:
                member = await commands.converter.MemberConverter().convert(ctx,word)
                word = member.mention
            except:
                pass
        if emoji.animated:
            emojitext = f"<a:{emoji.name}:{emoji.id}>"
        else:
            emojitext = f"<:{emoji.name}:{emoji.id}>"
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"utility.ar.{word}":1})
        current = methods.query(data = raw,search = ["utility","ar",str(word)])
        if emojitext not in current:
            raise errors.NotSetupError(message = f"The auto react for the word **{word}** with {emoji} does not exsist!")
        current.remove(emojitext)
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"utility.ar.{word}":current}})
        self.ar[str(ctx.guild.id)][word].remove(emojitext)
        if len(self.ar[str(ctx.guild.id)][word]) == 0:
            self.ar[str(ctx.guild.id)].pop(word)
        embed = discord.Embed(description = f"Removed an autoreaction for **{word}** as {emoji}!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @react.command(extras = {"id": "414"},name = "show",help = "Show all autoreactions pertaining to a specific word.")
    @app_commands.describe(word = "The word to look up reactions for.")
    @commands.has_permissions(moderate_members = True)
    async def show(self,ctx: commands.Context, word: str) -> None:
        word = word.lower()
        try:
            member = await commands.converter.MemberConverter().convert(ctx,word)
            word = member.mention
        except:
            pass
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"utility.ar.{word}":1})
        current = methods.query(data = raw,search = ["utility","ar",str(word)]) or []
        if len(current) == 0:
            raise errors.NotSetupError(message = f"There are no auto reacts for the word **{word}**!")
        embed = discord.Embed(title = f"Auto Reacts for {word}",description = ", ".join(current),color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @react.command(extras = {"id": "415"},name = "list",help = "List all the words that have auto reacts.")
    @commands.has_permissions(moderate_members = True)
    async def list(self,ctx: commands.Context) -> None:
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"utility.ar":1})
        current = methods.query(data = raw,search = ["utility","ar"])
        if not current:
            raise errors.NotSetupError(message = f"There are no auto reacts for this server!")
        embed = discord.Embed(title = f"Server Auto Reacts",description = ", ".join(current),color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)

async def setup(client):
    await client.add_cog(Utility(client))