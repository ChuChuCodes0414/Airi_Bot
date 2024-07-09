import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import time
from utils import errors, methods

class Mod(commands.Cog):
    """
        Very simple mod commands, which might be useful for backup when your main bot dies.
    """
    def __init__(self,client):
        self.client = client
        self.short = "<:bantime:930623021180387328> | Mod "
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('Mod Category Loaded.')
    
    @commands.hybrid_command(extras = {"id": "71"},help = "Echo a message into another channel.")
    @commands.has_permissions(moderate_members = True)
    @app_commands.describe(channel = "The channel to send the message into.",message = "The message to send into the channel")
    async def echo(self,ctx,channel:discord.TextChannel,*,message:str):
        await channel.send(message, allowed_mentions= discord.AllowedMentions(everyone = False, users = True, roles = False))
        await ctx.reply(embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Message sent to {channel.mention}!",color = discord.Color.green()), ephemeral = True)
    
    @commands.hybrid_command(extras = {"id": "72"},help = "Change a member's nickname.")
    @commands.has_permissions(manage_nicknames = True) 
    @app_commands.describe(member = "The member to change the nickname of.",nickname = "What to change the nickname to.")
    async def setnick(self,ctx, member:discord.Member,*,nickname = None):
        bot_top = ctx.guild.get_member(self.client.user.id)
        bot_top_ob = bot_top.top_role
        if member.top_role >= ctx.author.top_role:
            raise errors.PreRequisiteError(message = f"That user's top role position `({member.top_role.position})` is higher or equal to your top role `({ctx.author.top_role.position})`.")
        elif bot_top_ob <= member.top_role:
            raise errors.PreRequisiteError(message = f"That user's role position `({member.top_role.position})` is higher or equal to my top role `({bot_top_ob.position})`.")

        await member.edit(nick=nickname)
        await ctx.reply(embed = discord.Embed(description = f"Edited {member}'s nickname to: `{nickname}`",color = discord.Color.green()))

    @commands.hybrid_command(extras = {"id": "73"},help = "Give/remove a role to someone else.")
    @commands.has_permissions(manage_roles = True)
    @app_commands.describe(member = "The member to add or remove a role from.",role = "The role to add or remove.")
    async def role(self,ctx, member:discord.Member,role:discord.Role):
        bot_top = ctx.guild.get_member(self.client.user.id)
        bot_top_ob = bot_top.top_role
        if role >= bot_top_ob:
            raise errors.PreRequisiteError(message = f"That role position `({role.position})` is higher or equal to my top role `({bot_top_ob.position})`. Try changing my role position to something higher than the role you want to add.")
        elif ctx.author.top_role <= role:
            raise errors.PreRequisiteError(message = f"That role position `({role.position})` is higher or equal to your top role `({ctx.author.top_role.position})`. Ain't letting you exploit today.")

        if role in member.roles:
            await member.remove_roles((role))
            await ctx.reply(embed = discord.Embed(description = f"Removed **{role.name}** from **{member}**",color = discord.Color.green()))
        else:
            await member.add_roles((role))
            await ctx.reply(embed = discord.Embed(description = f"Added **{role.name}** to **{member}**",color = discord.Color.green()))

    @commands.hybrid_command(extras = {"id": "74"},help = "Timeout a user through the discord timeout function.")
    @commands.has_permissions(moderate_members = True)
    @app_commands.describe(member = "The member to timeout.", duration = "The duration of which to have the member timed out.",reason = "Why the member is being timed out.")
    async def timeout(self,ctx,member:discord.Member,duration,*,reason = None):
        bot_top = ctx.guild.get_member(self.client.user.id)
        bot_top_ob = bot_top.top_role
        if member.top_role >= bot_top_ob:
            raise errors.PreRequisiteError(message = f"That user's top role position `({member.top_role.position})` is higher or equal to my top role `({bot_top_ob.position})`.")
        elif ctx.author.top_role <= member.top_role:
            raise errors.PreRequisiteError(message = f"That user's top role position `({member.top_role.position})` is higher or equal to your top role `({ctx.author.top_role.position})`.")

        timestr = methods.timeparse(duration,28,0)
        if isinstance(timestr,str):
            raise errors.ParsingError(message = timestr)
        
        until = discord.utils.utcnow() + timestr
        await member.edit(timed_out_until = until,reason = reason)
        unix = int(until.replace(tzinfo=datetime.timezone.utc).timestamp())
        await ctx.reply(embed = discord.Embed(description = f"Timed out **{member}** until <t:{unix}:f> (<t:{unix}:R>)",color = discord.Color.green()))
    
    @commands.hybrid_command(extras = {"id": "75"},help = "Remove the timeout from user through the discord timeout function.")
    @commands.has_permissions(moderate_members = True)
    @app_commands.describe(member = "The member to untimeout.",reason = "Why the member is being untimed out.")
    async def untimeout(self,ctx,member:discord.Member,*,reason = None):
        bot_top = ctx.guild.get_member(self.client.user.id)
        bot_top_ob = bot_top.top_role
        if member.top_role >= bot_top_ob:
            raise errors.PreRequisiteError(message = f"That user's top role position `({member.top_role.position})` is higher or equal to my top role `({bot_top_ob.position})`.")
        elif ctx.author.top_role <= member.top_role:
            raise errors.PreRequisiteError(message = f"That user's top role position `({member.top_role.position})` is higher or equal to your top role `({ctx.author.top_role.position})`.")

        await member.edit(timed_out_until = None,reason = reason)
        await ctx.reply(embed = discord.Embed(description = f"Removed timeout from **{member}**",color = discord.Color.green()))

    @commands.hybrid_command(extras = {"id": "76"},aliases = ['k'],help = "Kick a member from the server.")
    @commands.has_permissions(kick_members = True) 
    @app_commands.describe(member = "The member that should be kicked.",reason = "Why you are kicking this member from the server.")
    async def kick(self,ctx, member:discord.Member,*,reason = None):
        bot_top = ctx.guild.get_member(self.client.user.id)
        bot_top_ob = bot_top.top_role
        if bot_top_ob <= member.top_role:
            raise errors.PreRequisiteError(message = f"That member has a role position `({member.top_role.position})` that is higher or equal to my top role `({bot_top_ob.position})`.")
        if member.top_role >= ctx.author.top_role:
            raise errors.PreRequisiteError(message = "You cannot kick people who have a higher role than you.")

        res = ""
        try:
            dm = member.dm_channel
            if dm == None:
                dm = await member.create_dm()
            await dm.send(f'**You were kicked from {ctx.guild} for the following reason:**\n{reason}')
            res += "Member DMed? <:greentick:930931553478008865>"
        except:
            res += "Member DMed? <:redtick:930931511685955604>"
        await member.kick(reason=reason)
        embed = discord.Embed(description = f"**{member}** was kicked from the server\n{res}",color = discord.Color.green())
        await ctx.reply(embed = embed)

    @commands.hybrid_command(extras = {"id": "77"},aliases = ['b'],help = "Ban a member from the server")
    @commands.has_permissions(ban_members = True)
    @app_commands.describe(member = "The member or user that should be banned from the server.",reason = "Why you are banning this member or user from the server.")
    async def ban(self,ctx,member,*,reason = None):
        try:
            member = await commands.converter.MemberConverter().convert(ctx,member)
            failed = False
        except:
            failed = True
            member = member
        if failed:
            try:
                user = await self.client.fetch_user(int(member))
            except:
                raise errors.ParsingError(message = "I could not find a user with that id! Try again with an actual id.")
            if user:
                await ctx.guild.ban(user,reason = reason,delete_message_days=0)
                return await ctx.reply(embed = discord.Embed(description = f'**{user.name}#{user.discriminator}** was banned from the server.\nMember Originally in Server? <:redtick:930931511685955604>',color = discord.Color.green()))
        bot_top = ctx.guild.get_member(self.client.user.id)
        bot_top_ob = bot_top.top_role
        if bot_top_ob <= member.top_role:
            raise errors.PreRequisiteError(message = f"That member has a role position `({member.top_role.position})` that is higher or equal to my top role `({bot_top_ob.position})`.")
        if member.top_role >= ctx.author.top_role:
            raise errors.PreRequisiteError(message = "You cannot ban people who have a higher role than you.")
        else:
            res = ""
            try:
                dm = member.dm_channel
                if dm == None:
                    dm = await member.create_dm()
                await dm.send(f'**You were banned from {ctx.guild} for the following reason:**\n{reason}')
                res += "Member DMed? <:greentick:930931553478008865>"
            except:
                res += "Member DMed? <:redtick:930931511685955604>"
            await member.ban(reason=reason,delete_message_days=0)
            embed = discord.Embed(description = f"**{member}** was banned from the server\n{res}",color = discord.Color.green())
            await ctx.reply(embed = embed)

    @commands.hybrid_command(extras = {"id": "78"},aliases = ['mb'],help = "Mass ban members from the server")
    @commands.has_permissions(ban_members = True) 
    @app_commands.describe(members = "A list of members or IDS, separated by spaces.")
    async def massban(self,ctx,*,members):
        guild = ctx.guild
        members = members.split()
        count = 0
        async with ctx.typing():
            for member in members:
                if str(member).isnumeric():
                    id = int(member)
                    member = guild.get_member(int(member))
                else:
                    member = await commands.converter.MemberConverter().convert(ctx,member)

                if not member:
                    user = await self.client.fetch_user(int(id))
                    await ctx.guild.ban(user,reason = f"Massban Taken by **{ctx.author}**",delete_message_days=0)
                    count += 1
                else:
                    if member.top_role >= ctx.author.top_role:
                        continue
                    await member.ban(reason=f"Massban Taken by **{ctx.author}**",delete_message_days=0)
                    count += 1
            await asyncio.sleep(1)

        try:
            await ctx.reply(embed = discord.Embed(description = f"Banned **{count}** members",color = discord.Color.green()))
        except:
            await ctx.send(embed = discord.Embed(description = f"Banned **{count}** members",color = discord.Color.green()))

    @commands.hybrid_command(extras = {"id": "79"},help = "Unban a member from the server.")
    @commands.has_permissions(ban_members = True) 
    @app_commands.describe(user = "The user to unban from the server.",reason = "Why this user is being unbanned from the server.")
    async def unban(self,ctx,user:discord.User,*,reason=None):
        try:
            await ctx.guild.unban(user,reason = reason)
            await ctx.reply(embed = discord.Embed(description = f"Unbanned **{user}**",color = discord.Color.green()))
        except:
            raise errors.PreRequisiteError(message = "That user is not currently banned.")
    
    @commands.hybrid_command(extras = {"id": "700"},aliases = ['r'],help = "Ban a member from the server. Also deletes messages from past day.")
    @commands.has_permissions(ban_members = True)
    @app_commands.describe(member = "The member or user that should be banned from the server.",reason = "Why you are banning this member or user from the server.")
    async def raid(self,ctx,member,*,reason = None):
        try:
            member = await commands.converter.MemberConverter().convert(ctx,member)
            failed = False
        except:
            failed = True
            member = member
        if failed:
            try:
                user = await self.client.fetch_user(int(member))
            except:
                raise errors.ParsingError(message = "I could not find a user with that id! Try again with an actual id.")
            if user:
                await ctx.guild.ban(user,reason = reason,delete_message_days=1)
                return await ctx.reply(embed = discord.Embed(description = f'**{user.name}#{user.discriminator}** was banned from the server.\nMember Originally in Server? <:redtick:930931511685955604>',color = discord.Color.green()))
        bot_top = ctx.guild.get_member(self.client.user.id)
        bot_top_ob = bot_top.top_role
        if bot_top_ob <= member.top_role:
            raise errors.PreRequisiteError(message = f"That member has a role position `({member.top_role.position})` that is higher or equal to my top role `({bot_top_ob.position})`.")
        if member.top_role >= ctx.author.top_role:
            raise errors.PreRequisiteError(message = "You cannot ban people who have a higher role than you.")
        else:
            res = ""
            try:
                dm = member.dm_channel
                if dm == None:
                    dm = await member.create_dm()
                await dm.send(f'**You were banned from {ctx.guild} for the following reason:**\n{reason}')
                res += "Member DMed? <:greentick:930931553478008865>"
            except:
                res += "Member DMed? <:redtick:930931511685955604>"
            await member.ban(reason=reason,delete_message_days=1)
            embed = discord.Embed(description = f"**{member}** was banned from the server\n{res}",color = discord.Color.green())
            await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "78"},aliases = ['mr'],help = "Mass ban members from the server, with deletes of messages for a day.")
    @commands.has_permissions(ban_members = True) 
    @app_commands.describe(members = "A list of members or IDS, separated by spaces.")
    async def massraid(self,ctx,*,members):
        guild = ctx.guild
        members = members.split()
        count = 0
        async with ctx.typing():
            for member in members:
                if str(member).isnumeric():
                    id = int(member)
                    member = guild.get_member(int(member))
                else:
                    member = await commands.converter.MemberConverter().convert(ctx,member)

                if not member:
                    user = await self.client.fetch_user(int(id))
                    await ctx.guild.ban(user,reason = f"Massban Taken by **{ctx.author}**",delete_message_days=1)
                    count += 1
                else:
                    if member.top_role >= ctx.author.top_role:
                        continue
                    await member.ban(reason=f"Massban Taken by **{ctx.author}**",delete_message_days=1)
                    count += 1
            await asyncio.sleep(1)

        try:
            await ctx.reply(embed = discord.Embed(description = f"Banned **{count}** members",color = discord.Color.green()))
        except:
            await ctx.send(embed = discord.Embed(description = f"Banned **{count}** members",color = discord.Color.green()))

async def setup(client):
    await client.add_cog(Mod(client))
