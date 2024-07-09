import discord
from discord.ext import commands
from discord import app_commands, ui
from utils import methods
from utils import errors
import asyncio
import random
import datetime

class Fun(commands.Cog):
    """
        Fun commands, meaning not utility commands.
    """

    def __init__(self,client):
        self.client = client
        self.short = "🎈 | Fun Commands"

        self.badges = {
            "dev":"<:PB_BadgeDev:866505179795554315> **Bot Developer**\nThis person develops the bot that you are using!",
            "mod":"<:PB_BadgeMod:866504829051994132> **Bot Mod**\nThis person is a mod for the bot in the support server, and has access to some cool bot commands!",
            "fighter1":"<:PB_BadgeFighter:866505136888872990> **Fighter I (Legacy)**\nThis person has done a lot of fighting with the bot, gaining 50+ wins!",
            "fighter2":"<:PB_BadgeFighter2:866846614584950806> **Fighter II (Legacy)**\nThis person must be really addicting to this fight command, gaining 100+ wins! Probably not the best idea to fight this person.",
            "early":"<:PB_BadgeEarly:866847704680103956> **Early Supporter (Legacy)**\nThis person was one of the first few people to invite the bot to their server!",
            "iq":"<:IQBadge:870129049232637992> **IQ**\nThis person somehow got the maximum IQ score possible. That's a 1/2000 chance!",
            "8ball":"<:8ballBadge:870129771122671627> **8ball**\nAnd the bot says...`yes`.",
            "nab":"<:NabBadge:870130999500095549> **Nab**\nThis person got the maximum nabrate...but it's only a 1/100 chance. Must mean this person is a nab.",
            "color":"<:ColorBadge:912893729482883142> **Color Game**\nThis person got to level 20 in the color game...pretty good memory",
            "1y":"<:1yBadge:979206493377294396> **One Year (Legacy)**\nThis person used the bot during the 2.0.2 Anniversary Update!"
        }

        self.ball = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes - definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]

        self.wordlist = ["claim","grab","steal","mine","give","clutch","snatch","take","swipe"]
    
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

    @commands.Cog.listener()
    async def on_ready(self):
        print('Fun Category Loaded.')
    
    async def grant_badge(self,member,badge):
        if not badge in self.badges:
            return False
        return self.client.db.user_data.update_one({"_id":member.id},{"$addToSet":{"fun.badges":badge}},upsert = True)

    async def remove_badge(self,member,badge):
        if not badge in self.badges:
            return False
        return self.client.db.user_data.update_one({"_id":member.id},{"$pull":{"fun.badges":badge}})
    
    @commands.hybrid_command(extras = {"id": "40"},name = "8ball", help = "The magic 8ball...it's always right.")
    @commands.cooldown(1, 10,commands.BucketType.user)
    @app_commands.describe(question = "Your important question to ask the 8ball.")
    async def _8ball(self,ctx,*,question):
        if len(question) > 256:
            raise errors.ParsingError(message = "Your question cannot be longer than 256 characters!")
        choice = random.choice(self.ball)
        des = f"**The totally magic 8ball says...**\n{choice}"
        if choice == "Yes.":
            res = await self.grant_badge(ctx.author,"8ball")
            if res.modified_count == 1:
                des += "\n\nYou earned the <:8ballBadge:870129771122671627> **8ball** badge! Use </profile:1103474987643441154> to see your badges."
        embed = discord.Embed(title = question,description = des,color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "41"}, help = "What's your iq level?")
    @commands.cooldown(1, 10,commands.BucketType.user)
    @app_commands.describe(person = "The person to check the iq level of")
    async def iq(self,ctx,person = None):
        try:
            member = await commands.converter.MemberConverter().convert(ctx,person)
            person = str(member)
        except:
            pass
        person = person or ctx.author

        iq = random.randint(-1000,1000)
        des = f"**{person}'s IQ**\n{iq}"
        if iq == 1000:
            res = await self.grant_badge(ctx.author,"iq")
            if res.modified_count == 1:
                des += "\n\nYou earned the <:IQBadge:870129049232637992> **IQ** badge! Use </profile:1103474987643441154> to see your badges."

        embed=discord.Embed(description= des,color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "42"}, help = "How much of a nab are you? Well...")
    @commands.cooldown(1,10,commands.BucketType.user)
    @app_commands.describe(person = "The person to check the nabrate of.")
    async def nabrate(self,ctx,person = None):
        try:
            member = await commands.converter.MemberConverter().convert(ctx,person)
            person = str(member)
        except:
            pass
        person = person or ctx.author

        nab = random.randint(0,100)
        des = f"**{person}'s Nab Rate**\n{nab}% Nab"
        if nab == 100:
            res = await self.grant_badge(ctx.author,"nab")
            if res.modified_count == 1:
                des += "\n\nYou earned the <:NabBadge:870130999500095549> **Nab** badge! Use </profile:1103474987643441154> to see your badges."
        
        embed=discord.Embed(description= des,color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "43"}, help = "Drop a prize for other people to pickup!")
    @commands.cooldown(1,10,commands.BucketType.user)
    @eman_role_check()
    @app_commands.describe(item = "The item that you are dropping",channel = "Where the item should be dropped",word = "The word that should be typed to pick it up")
    async def drop(self,ctx,item,channel:discord.TextChannel = None, word = None):
        channel = channel or ctx.channel
        word = word or random.choice(self.wordlist)

        embed=discord.Embed(title=f"Someone has dropped {item} in this channel!",description=f"Type the words `{word}` to claim!", color=discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        message = await channel.send(embed=embed)

        message2 = await ctx.reply(embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully dropped!\n[Jump to the message]({message.jump_url})",color = discord.Color.green()))

        def check(message: discord.Message):
            if message.author.bot:
                return False
            return message.content.lower() == word and message.channel == channel

        try:
            msg = await self.client.wait_for("message",timeout = 270.0,check=check)
        except asyncio.TimeoutError:
            try:
                await message.edit(content = "Drop no longer Active")
            except:
                pass
            await message.channel.send(embed = discord.Embed(description = "You took too long, and the drop is now cancelled!",color = discord.Color.red()))
            await message2.reply(embed = discord.Embed(description = f"Your drop was cancelled, since no one responded.",color = discord.Color.red()))
            return
        await message.reply(embed = discord.Embed(description = f"Claimed by {msg.author.mention} :tada:",color = discord.Color.random()))
        await ctx.reply(embed = discord.Embed(description = f"{ctx.author.mention} your prize was claimed! Please give {item} to {msg.author.mention}",color = discord.Color.green()))

    @commands.hybrid_command(extras = {"id": "44"},aliases = ['sos'],help = "Host a giveaway with a split or steal function!")
    @eman_role_check()
    @commands.max_concurrency(1,commands.BucketType.channel)
    @app_commands.describe(time = "The time for the entry giveaway",requirements = "Role requirements, bypasses, and blacklists",prize = "The prize to be won")
    async def splitorsteal(self,ctx,time,requirements,*,prize):
        time = methods.timeparse(time,0,300)
        if isinstance(time,str):
            raise errors.ParsingError(message = time)
        if requirements and requirements.lower() != "none":
            requirements = requirements.split(";;")
            req,by,bl = [],[],[]
            for require in requirements:
                require = require.split(":")
                try:
                    role = await commands.converter.RoleConverter().convert(ctx,require[1])
                except:
                    role = None
                if len(require) != 2 or not role:
                    return await ctx.reply(embed = discord.Embed(description = "I could not process your requirements!",color = discord.Color.red()))
                elif require[0].startswith("role"):
                    req.append(role)
                elif require[0].startswith("bypass"):
                    by.append(role)
                elif require[0].startswith("blacklist"):
                    bl.append(role)
        else:
            req,by,bl = None,None,None
        view = GiveawayEnter(req,by,bl)
        now = datetime.datetime.now(datetime.timezone.utc)
        end = now + time
        unix = int(end.replace(tzinfo=datetime.timezone.utc).timestamp())
        time = time.total_seconds()
        embed = discord.Embed(title = f"Split or Steal For: {prize}",description = f"Ending at: <t:{unix}:f>\nTime Remaining: <t:{unix}:R>\nHosted By: {ctx.author.mention}",color = discord.Color.green())
        reqbuild = ""
        if req:
            reqbuild += "Required Roles:" + ', '.join(role.mention for role in req)
        if by:
            reqbuild += "\nBypass Roles:" + ', '.join(role.mention for role in by)
        if bl:
            reqbuild += "\nBlacklisted Roles:" + ', '.join(role.mention for role in bl)
        if reqbuild == "":
            reqbuild = "None!"
        embed.add_field(name = "Requirements",value = reqbuild,inline = False)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        message = await ctx.send(embed = embed,view = view)
        if ctx.message.type == discord.MessageType.default:
            await ctx.message.delete()
        await asyncio.sleep(time)
        view.stop()
        entrees = view.entered
        if len(entrees) < 2:
            embed.description = f"Ended at: <t:{unix}:f>"
            embed.color = None
            embed.insert_field_at(0,name = "Winners",value = f"No winners determined\nHosted By: {ctx.author.mention}")
            view.children[0].disabled = True
            await message.edit(embed = embed,view = view)
            return await message.reply(embed = discord.Embed(description = "There were not enough valid entrees!",color = discord.Color.red()))
        winners = random.sample(entrees,2)
        embed.description = f"Ended at: <t:{unix}:f>"
        embed.color = None
        embed.insert_field_at(0,name = "Winners",value = f"{winners[0].mention} and {winners[1].mention}!\nHosted By: {ctx.author.mention}")
        view.children[0].disabled = True
        await message.edit(embed = embed,view = view)
        embed = discord.Embed(title = "Now is the time to discuss!",description = "You now have 60 seconds to discuss with the other winner! Do it quickly...",color = discord.Color.random())
        embed.set_footer(text = "The channel will unlock for the winners shortly.")
        await ctx.send(winners[0].mention + winners[1].mention,embed = embed)
        overwrite = ctx.channel.overwrites_for(winners[0])
        overwrite.send_messages = True
        await ctx.channel.set_permissions(winners[0], overwrite=overwrite)
        overwrite = ctx.channel.overwrites_for(winners[1])
        overwrite.send_messages = True
        await ctx.channel.set_permissions(winners[1], overwrite=overwrite)
        await asyncio.sleep(50)
        await ctx.send(embed = discord.Embed(description = "10 seconds remaining!",color = discord.Color.random()))
        await asyncio.sleep(10)
        await ctx.channel.set_permissions(winners[0], overwrite=None)
        await ctx.channel.set_permissions(winners[1], overwrite=None)
        embed = discord.Embed(title = "Now it is time to decide!",description = "Press the button below to choose.",color = discord.Color.random())
        embed.set_footer(text = "You have 30 seconds to choose!")
        view = SplitorSteal(winners)
        message = await ctx.send(embed = embed,view = view)
        response = await view.wait()
        for child in view.children:
            child.disabled = True
        await message.edit(view = view)
        if response:
            return await message.reply(embed = discord.Embed(description = "The buttons timed out! One or both of the winners did not choose.",color = discord.Color.red()))
        await asyncio.sleep(3.0)
        if view.u1 == "split" and view.u2 == "split":
            return await message.reply(embed = discord.Embed(description = f"Both **{winners[0].mention}** and **{winners[1].mention}** decide to split. Congrats!",color = discord.Color.green()))
        if view.u1 == "steal" and view.u2 == "steal":
            return await message.reply(embed = discord.Embed(description = f"Both **{winners[0].mention}** and **{winners[1].mention}** decide to steal. Bummer!",color = discord.Color.red()))
        if view.u1 == "steal" and view.u2 == "split":
            return await message.reply(embed = discord.Embed(description = f"**{winners[0].mention}** decided to steal while **{winners[1].mention}** decide to split. GG!",color = discord.Color.gold()))
        return await message.reply(embed = discord.Embed(description = f"**{winners[1].mention}** decided to steal while **{winners[0].mention}** decide to split. GG!",color = discord.Color.gold()))

    @commands.hybrid_command(extras = {"id": "45"}, aliases = ['gtn'], help = "Host a quick guess the number game.")
    @eman_role_check()
    @commands.max_concurrency(1,commands.BucketType.channel)
    @app_commands.describe(start = "The starting number.", end = "The ending number.", target = "The correct answer.")
    async def guessthenumber(self,ctx,start:int = None,end:int = None,target:int = None):
        if not start: start = 1
        if not end: end = start + 99
        if not target: target = random.randint(start,end)
        if start < 0 or end < 0 or start >= end or target < start or target > end or target < 0: raise errors.ParsingError(message = "That does not look like valid input.")
        print(target)

        if ctx.message.type == discord.MessageType.default:
            await ctx.message.delete()
        else:
            await ctx.reply(embed = discord.Embed(description = "Game started!",color = discord.Color.green()), ephemeral = True)
        embed = discord.Embed(title = "Guess the Number!",description = f"The range for this game is **{start}** - **{end}**",color = discord.Color.random())
        embed.set_author(name="Hosted by " + ctx.author.display_name,icon_url=ctx.author.avatar)
        embed.set_thumbnail(url=ctx.guild.icon)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name + " | Good luck! You have 2 minutes to guess.")
        message = await ctx.send(embed = embed)
        def check(i):
            if i.channel.id == message.channel.id and i.content == str(target):
                return True
            else:
                return False
        try:
            message = await self.client.wait_for("message",timeout = 120.0,check = check)
        except asyncio.TimeoutError:
            return await message.edit("The game timed out. Yall are bad")

        embed = discord.Embed(description = f"{message.author.mention} guessed the number! The number was **{target}**.")
        await message.reply(embed = embed)

    @commands.hybrid_command(extras = {"id": "46"},help = "How good is your memory?")
    async def colorgame(self,ctx):
        order = []
        embed = discord.Embed(title = f"Setting Up {ctx.author}'s Colorgame...",description = f"The bot will show you a sequence of colors by enabling and disabling buttons. After showing the sequence, it is your turn to press the buttons in the same sequence!",color = discord.Color.random())
        message = await ctx.reply(embed = embed)
        view = ColorGame(ctx)
        await asyncio.sleep(5)
        embed = discord.Embed(title = f"{ctx.author}'s Color Game",description = f"Level 1\nWatch the color sequence now!")
        await message.edit(embed = embed,view = view)
        while True:
            next = random.randint(0,3)
            order.append(next)
            for selected in order:
                view.children[selected].disabled = False
                await message.edit(embed = embed,view = view)
                await asyncio.sleep(1)
                view.children[selected].disabled = True
                await message.edit(embed = embed,view = view)
                await asyncio.sleep(1)
            for child in view.children:
                child.disabled = False
            embed = discord.Embed(title = f"{ctx.author}'s Color Game",description = f"Level {len(order)}\nEnter in the sequence now!")
            await message.edit(embed = embed,view = view)
            view.responding = True
            view.order = order
            await view.wait()
            if view.value == True:
                embed = discord.Embed(title = f"{ctx.author}'s Color Game",description = f"Level {len(order)+1}\nWatch the color sequence now!")
                view = ColorGame(ctx)
                await message.edit(embed = embed,view = view)
                continue
            else:
                des = f"Level {len(order)}\nYou Lost!"
                if len(order) >= 20:
                    res = await self.grant_badge(ctx.author,"color")
                    if res.modified_count == 1:
                        des += "\n\nYou earned the <:ColorBadge:912893729482883142> **Color Game** badge! Use </profile:1103474987643441154> to see your badges."
                embed = discord.Embed(title = f"{ctx.author}'s Color Game",description = des,color = discord.Color.red())
                view = ColorGame(ctx)
                view.children[4].disabled = True
                await message.edit(embed = embed,view = view)
                break
    
    @commands.hybrid_command(extras = {"id": "47"},help = "View your badges!")
    @app_commands.describe(member = "The member to check the profile of")
    async def profile(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        embed=discord.Embed(title = f"Profile for {member}",color=discord.Color.random())

        raw = self.client.db.user_data.find_one({"_id":member.id},{"fun.badges":1})
        badges = methods.query(data = raw, search = ["fun","badges"])

        if not badges:
            embed.add_field(name = "Badges",value = "This user had no badges. Sad.")
        else:
            build = ""
            for badge in badges:
                build += self.badges[badge] + "\n"
            embed.add_field(name = "Badges",value = build)
        
        await ctx.reply(embed = embed)
        
class GiveawayEnter(discord.ui.View):
    def __init__(self,req,by,bl):
        super().__init__()
        self.req = req
        self.by = by
        self.bl = bl
        self.entered = []
    
    async def interaction_check(self, interaction):
        if interaction.user in self.entered:
            await interaction.response.send_message(embed = discord.Embed(description = f"You are already entered into this giveaway!",color = discord.Color.red()),ephemeral = True)
            return False
        if self.bl:
            for role in self.bl:
                if role in interaction.user.roles:
                    await interaction.response.send_message(embed = discord.Embed(description = f"You are blacklisted due to the {role.mention} role!",color = discord.Color.red()),ephemeral = True)
                    return False
        if self.by:
            for role in self.by:
                if role in interaction.user.roles:
                    return True
        if self.req:
            for role in self.req:
                if role not in interaction.user.roles:
                    await interaction.response.send_message(embed = discord.Embed(description = f"You are missing the {role.mention} role!",color = discord.Color.red()),ephemeral = True)
                    return False
        return True
    
    @ui.button(label = "Enter!",style = discord.ButtonStyle.green)
    async def enter(self,interaction,button):
        self.entered.append(interaction.user)
        await interaction.response.send_message(embed = discord.Embed(description = f"You have succesfully entered!",color = discord.Color.green()),ephemeral = True)

class SplitorSteal(discord.ui.View):
    def __init__(self,users):
        super().__init__(timeout = 30)
        self.u1 = None
        self.u2 = None
        self.users = users
    
    async def interaction_check(self, interaction):
        return interaction.user in self.users
    
    async def on_timeout(self):
        for child in self.children: 
            child.disabled = True 
    
    @ui.button(label = "Split",style = discord.ButtonStyle.blurple)
    async def split(self,interaction,button):
        if interaction.user == self.users[0] and not self.u1:
            await interaction.response.send_message(embed = discord.Embed(description = f"**{interaction.user}** has selected their answer!",color = discord.Color.random()))
            self.u1 = "split"
            if self.u2 and self.u1:
                self.stop()
        elif interaction.user == self.users[0]:
            return await interaction.response.send(embed = discord.Embed(description = f"You have already selected your answer!",color = discord.Color.red()))
        elif interaction.user == self.users[1] and not self.u2:
            await interaction.response.send_message(embed = discord.Embed(description = f"**{interaction.user}** has selected their answer!",color = discord.Color.random()))
            self.u2 = "split"
            if self.u2 and self.u1:
                self.stop()
        else:
            await interaction.response.send_message(embed = discord.Embed(description = f"You have already selected your answer!",color = discord.Color.red()),ephemeral = True)

    @ui.button(label = "Steal",style = discord.ButtonStyle.blurple)
    async def steal(self,interaction,button):
        if interaction.user == self.users[0] and not self.u1:
            await interaction.response.send_message(embed = discord.Embed(description = f"**{interaction.user}** has selected their answer!",color = discord.Color.random()))
            self.u1 = "steal"
            if self.u2 and self.u1:
                self.stop()
        elif interaction.user == self.users[0]:
            return await interaction.response.send(embed = discord.Embed(description = f"You have already selected your answer!",color = discord.Color.red()))
        elif interaction.user == self.users[1] and not self.u2:
            await interaction.response.send_message(embed = discord.Embed(description = f"**{interaction.user}** has selected their answer!",color = discord.Color.random()))
            self.u2 = "steal"
            if self.u2 and self.u1:
                self.stop()
        else:
            await interaction.response.send_message(embed = discord.Embed(description = f"You have already selected your answer!",color = discord.Color.red()),ephemeral = True)

class ColorGame(discord.ui.View):
    def __init__(self,ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.responding = False
        self.value = None
        self.order = []
        self.count = 0

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.ctx.author and self.responding

    async def check_response(self,number):
        if number == self.order[self.count]:
            if self.count == len(self.order)-1:
                return 2
            self.count += 1
            return 0
        else:
            if self.order[self.count] == 0: return "Blue"
            if self.order[self.count] == 1: return "Gray"
            if self.order[self.count] == 2: return "Green"
            if self.order[self.count] == 3: return "Red"
    
    @ui.button(emoji='<:BlueButton:904111618391158875>', style=discord.ButtonStyle.blurple,row = 0,disabled = True)
    async def blue(self, interaction, button):
        check = await self.check_response(0)
        if check == 0: 
            await interaction.response.defer()
        elif check == 2:
            await interaction.response.defer()
            self.value = True
            self.stop()
        else:
            self.value = False
            self.stop()
            await interaction.response.send_message(embed = discord.Embed(description = f"You lost! The color was **{check}**"))

    @ui.button(emoji='<:GrayButtonNew:1076621526436163725>', style=discord.ButtonStyle.gray,row = 0,disabled = True)
    async def gray(self, interaction, button):
        check = await self.check_response(1)
        if check == 0: 
            await interaction.response.defer()
        elif check == 2:
            await interaction.response.defer()
            self.value = True
            self.stop()
        else:
            self.value = False
            self.stop()
            await interaction.response.send_message(embed = discord.Embed(description = f"You lost! The color was **{check}**"))

    @ui.button(emoji='<:GreenButtonNew:1076621525517619304>', style=discord.ButtonStyle.green,row = 1,disabled = True)
    async def green(self, interaction, button):
        check = await self.check_response(2)
        if check == 0: 
            await interaction.response.defer()
        elif check == 2:
            await interaction.response.defer()
            self.value = True
            self.stop()
        else:
            self.value = False
            self.stop()
            await interaction.response.send_message(embed = discord.Embed(description = f"You lost! The color was **{check}**"))

    @ui.button(emoji='<:RedButtonNew:1076621109706899526>', style=discord.ButtonStyle.red,row = 1,disabled = True)
    async def red(self, interaction, button):
        check = await self.check_response(3)
        if check == 0: 
            await interaction.response.defer()
        elif check == 2:
            await interaction.response.defer()
            self.value = True
            self.stop()
        else:
            self.value = False
            self.stop()
            await interaction.response.send_message(embed = discord.Embed(description = f"You lost! The color was **{check}**"))
    
    @ui.button(label='End Interaction', style=discord.ButtonStyle.blurple,row = 2,disabled = True)
    async def stop_page(self, interaction, button):
        await interaction.response.defer()
        self.value = False
        self.stop()

async def setup(client):
    await client.add_cog(Fun(client))