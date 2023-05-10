import discord
from discord.ext import commands, menus
from discord import app_commands, ui, AuditLogAction
import datetime
from asyncio import sleep
from utils import methods, classes
from discord.errors import Forbidden
from itertools import starmap
import time

class InviteTracking(commands.Cog):
    '''
        Simple invite tracking, with many limitations due to Discord.
    '''

    def __init__(self,client):
        self.short = "<:invite:950957804544471080> | Invite Tracking"
        self.client = client
        self.tracker = InviteTracker(client)
    
    async def cog_load(self):
        await self.tracker.cache_invites()
        print("Cached Invites")

    @commands.Cog.listener()
    async def on_ready(self):
        print('Invite Category Loaded.')

    async def log_invite_join(self,member,inviter = None):
        raw = self.client.db.guild_data.find_one({"_id":member.guild.id},{"settings.invitetracking.logging":1}) or {}
        channelid = methods.query(data = raw, search = ["settings","invitetracking","logging"])

        if not channelid:
            return
        
        channel = member.guild.get_channel(int(channelid))

        if not channel:
            return
        
        build = ""
        date = member.created_at
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - date
        unix = time.mktime(date.timetuple())
        formatted = "<t:" + str(int(unix)) + ":F>"
        formatted2 = "<t:" + str(int(unix)) + ":R>"
        build += f"**Member Joining Information:** {member.mention} ( `{member.id}` )\n"
        if diff.days <= 30:
            build += f"**⚠ This Account is Under 30 days Old! ⚠**\n**Account Creation Date:** {formatted}\n**Account Age:** {formatted2}\n"
        else:
            build += f"**Account Creation Date:** {formatted}\n**Account Age:** {formatted2}\n"

        if member.bot:
            build += f"**This is a bot account! Check server audit logs for invite information.**"
        elif inviter and inviter == "vanity":
            build += f"**Invited By:** Vanity Link"
        elif inviter:
            build += f"**Invited By:** {inviter.mention} ( `{inviter.id} `)"
        else:
            build += f"**I could not trace how this member joined! Perhaps they joined through temporary link.**"
        
        emb = discord.Embed(title=f"{member} has Joined the Server!",description = f"{build}",
                                color=discord.Color.green())
        emb.timestamp = datetime.datetime.now()
        emb.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)

        await channel.send(embed = emb)

    async def log_invite_leave(self,member,inviter = None):
        raw = self.client.db.guild_data.find_one({"_id":member.guild.id},{"settings.invitetracking.logging":1}) or {}
        channelid = methods.query(data = raw, search = ["settings","invitetracking","logging"])

        if not channelid:
            return
        
        channel = member.guild.get_channel(int(channelid))

        if not channel:
            return

        build = ""
        date = member.joined_at
        unix = time.mktime(date.timetuple())
        formatted = "<t:" + str(int(unix)) + ":F>"
        build += f"**Member Leaving Information:** {member.mention} ( `{member.id}` )\n"
        timedelta = datetime.datetime.now(datetime.timezone.utc) - member.joined_at
        if timedelta.days >= 7:
            build += f"**Joined at:** {formatted} ({timedelta.days//7} weeks ago)\n"
        elif timedelta.days >= 1:
            build += f"**Joined at:** {formatted} ({timedelta.days} days ago)\n"
        elif timedelta.seconds >= 3600:
            build += f"**Joined at:** {formatted} ({timedelta.seconds//3600} hours ago)\n"
        elif timedelta.seconds >= 60:
            build += f"**Joined at:** {formatted} ({timedelta.seconds//60} minutes ago)\n"
        else:
            build += f"**Joined at:** {formatted} (under one minute ago)\n"

        if member.bot:
            build += f"**This is a bot account! Check server audit logs for invite information.**"
        elif inviter and inviter == "vanity":
            build += f"**Invited By:** Vanity Link"
        elif inviter:
            build += f"**Invited By:** {inviter.mention} (`{inviter.id}`)"
        elif date < member.guild.me.joined_at:
            build += f"**This member joined the server before I did, meaning I have no invite information on them!**"
        else:
            build += f"**I could not trace how this member joined! Perhaps they joined through a temporary link.**"
        
        emb = discord.Embed(title=f"{member} has left the Server!",description = f"{build}",
                                color=discord.Color.red())
        emb.timestamp = datetime.datetime.now()
        emb.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)

        await channel.send(embed = emb)

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.tracker.update_invite_cache(invite)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.tracker.add_guild_cache(guild)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await self.tracker.remove_invite_cache(invite)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.tracker.remove_guild_cache(guild)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            inviter = await self.tracker.fetch_inviter(member)  # inviter is the member who invited
        except:
            return await self.log_invite_join(member)

        if not inviter:
            return await self.log_invite_join(member)
        
        if inviter == "vanity":
            self.client.db.guild_data.update_one({"_id":member.guild.id},{"$set" : {f"invitetracking.{member.id}.invited":"vanity"}})
        else:
            self.client.db.guild_data.update_one({"_id":member.guild.id},{"$set" : {f"invitetracking.{member.id}.invited":inviter.id}})

        if inviter != "vanity":
            self.client.db.guild_data.update_one({"_id":member.guild.id},{"$addToSet" : {f"invitetracking.{inviter.id}.invites":member.id}},upsert = True)
            self.client.db.guild_data.update_one({"_id":member.guild.id},{"$pull" : {f"invitetracking.{inviter.id}.leaves":member.id}},upsert = True)
            await self.log_invite_join(member,inviter)
        else:
            await self.log_invite_join(member,"vanity")

    @commands.Cog.listener()
    async def on_member_remove(self,member):
        inviteruser = None
        raw = self.client.db.guild_data.find_one({"_id":member.guild.id},{f"invitetracking.{member.id}":1}) or {}
        memberdata = methods.query(data = raw, search = ["invitetracking",str(member.id)])

        if memberdata:
            inviter = memberdata.get("invited",None)
            if inviter and not inviter == "vanity":
                inviteruser = await self.client.fetch_user(int(inviter))
                self.client.db.guild_data.update_one({"_id":member.guild.id},{"$pull" : {f"invitetracking.{inviteruser.id}.invites":member.id}})
                self.client.db.guild_data.update_one({"_id":member.guild.id},{"$addToSet" : {f"invitetracking.{inviteruser.id}.leaves":member.id}},upsert = True)
            self.client.db.guild_data.update_one({"_id":member.guild.id},{"$unset" : {f"invitetracking.{member.id}":""}})
        else:
            inviter = None
        
        if inviter and inviter == "vanity":
            await self.log_invite_leave(member,inviter)
        else:
            await self.log_invite_leave(member,inviteruser)


    @commands.hybrid_command(id = "60",help = "View who invited a member, as well as their invite count.")
    @app_commands.describe(member = "The user to lookup information for.")
    async def invites(self,ctx,member:discord.Member = None):
        member = member or ctx.author

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"invitetracking.{member.id}":1}) or {}
        invitedby = methods.query(data = raw, search = ["invitetracking",str(member.id),"invited"])
        invites = methods.query(data = raw, search = ["invitetracking",str(member.id),"invites"])
        leaves = methods.query(data = raw, search = ["invitetracking",str(member.id),"leaves"])

        if invites:
            invites = len(invites)

        if leaves:
            leaves = len(leaves)
        
        if invitedby and invitedby == "vanity":
            invitedby = "Vanity Invite"
            user = None
        elif invitedby:
            user = await self.client.fetch_user(int(invitedby))
        else:
            user = None

        emb = discord.Embed(title=f"{member} Invite Information",description = f"{member.mention} (`{member.id}`)",
                                color=discord.Color.random())

        if user:
            emb.add_field(name = "Invited By:",value = f"{user.mention} | {user} (`{user.id}`)",inline = False)
        elif invitedby:
            emb.add_field(name = "Invited By:",value = f"`{invitedby}`",inline = False)
        else:
            emb.add_field(name = "Invited By:",value = f"No Data",inline = False)

        emb.add_field(name = "Invites:",value = f"`{invites}`")
        emb.add_field(name = "Leaves:",value = f"`{leaves}`")
        emb.timestamp = datetime.datetime.now()
        emb.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)

        await ctx.send(embed = emb)

    @commands.hybrid_command(id = "61", aliases = ['invitelb','ilb'],help = "View the invite leaderboard for your server!")
    async def inviteleaderboard(self,ctx):
        async with ctx.typing():
            raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id})
            guildtracking = methods.query(data = raw,search = ["invitetracking"]) or {}

            build = {}
            if not guildtracking:
                users,log =  [],build
            else:
                for person in guildtracking:
                    invites = len(guildtracking[person].get("invites",[]))
                    if invites > 0:
                        build[person] = invites

                users,log =  sorted(build, key=build.get, reverse=True) , build

            formatter = InviteLBPageSource(users, log)
            menu = classes.MenuPages(formatter, delete_message_after=True)
            await menu.start(ctx)

class InviteLBPageSource(menus.ListPageSource):
    def __init__(self, data, log):
        super().__init__(data, per_page=10)
        self.log = log
    def format_leaderboard_entry(self, no, user):
        return f"**{no}. <@{user}>** `{self.log[user]} Members Invited`"
    async def format_page(self, menu, users):
        page = menu.current_page
        max_page = self.get_max_pages()
        starting_number = page * self.per_page + 1
        iterator = starmap(self.format_leaderboard_entry, enumerate(users, start=starting_number))
        page_content = "\n".join(iterator)
        embed = discord.Embed(
            title=f"Invites Leaderboard [{page + 1}/{max_page}]", 
            description=page_content,
            color= discord.Color.random()
        )
        embed.set_footer(text=f"Use the buttons below to navigate pages!") 
        return embed

# code excerpted from a package so I could edit it
class InviteTracker():
    def __init__(self, bot):
        self.bot = bot
        self._cache = {}
        self.add_listeners()
    
    def add_listeners(self):
        self.bot.add_listener(self.cache_invites, "on_ready")
        self.bot.add_listener(self.update_invite_cache, "on_invite_create")
        self.bot.add_listener(self.remove_invite_cache, "on_invite_delete")
        self.bot.add_listener(self.add_guild_cache, "on_guild_join")
        self.bot.add_listener(self.remove_guild_cache, "on_guild_remove")
    
    async def cache_invites(self):
        for guild in self.bot.guilds:
            try:
                self._cache[guild.id] = {}
                for invite in await guild.invites():
                    self._cache[guild.id][invite.code] = invite
                try:
                    vanity = await guild.vanity_invite()
                    self._cache[guild.id]['vanity'] = vanity
                except Forbidden:
                    continue
            except Forbidden:
                continue
    
    async def update_invite_cache(self, invite):
        if invite.guild.id not in self._cache.keys():
            self._cache[invite.guild.id] = {}
        self._cache[invite.guild.id][invite.code] = invite
    
    async def remove_invite_cache(self, invite):
        if invite.guild.id not in self._cache.keys():
            return
        ref_invite = self._cache[invite.guild.id][invite.code]
        if (ref_invite.created_at.timestamp()+ref_invite.max_age > datetime.datetime.now().timestamp() or ref_invite.max_age == 0) and ref_invite.max_uses > 0 and ref_invite.uses == ref_invite.max_uses-1:
            try:
                async for entry in invite.guild.audit_logs(limit=1, action=AuditLogAction.invite_delete):
                    if entry.target.code != invite.code:
                        self._cache[invite.guild.id][ref_invite.code].revoked = True
                        return
                else:
                    self._cache[invite.guild.id][ref_invite.code].revoked = True
                    return
            except Forbidden:
                self._cache[invite.guild.id][ref_invite.code].revoked = True
                return
        else:
            self._cache[invite.guild.id].pop(invite.code)
    
    async def add_guild_cache(self, guild):
        self._cache[guild.id] = {}
        for invite in await guild.invites():
            self._cache[guild.id][invite.code] = invite
        try:
            vanity = await guild.vanity_invite()
            self._cache[guild.id]['vanity'] = vanity
        except:
            pass
    
    async def remove_guild_cache(self, guild):
        try:
            self._cache.pop(guild.id)
        except KeyError:
            return
    
    async def fetch_inviter(self, member):
        await sleep(self.bot.latency)
        try:
            vanity = self._cache[member.guild.id]['vanity']
            new_vanity = await member.guild.vanity_invite()
            if new_vanity.uses - vanity.uses == 1:
                self._cache[member.guild.id]['vanity'] = new_vanity
                return "vanity"
        except:
            pass
        for new_invite in await member.guild.invites():
            for cached_invite in self._cache[member.guild.id].values():
                if new_invite.code == cached_invite.code and new_invite.uses > cached_invite.uses or cached_invite.revoked:
                    if cached_invite.revoked:
                        self._cache[member.guild.id].pop(cached_invite.code)
                    elif new_invite.inviter == cached_invite.inviter:
                        self._cache[member.guild.id][cached_invite.code] = new_invite
                    else:
                        self._cache[member.guild.id][cached_invite.code].uses += 1
                    return cached_invite.inviter

async def setup(client):
    await client.add_cog(InviteTracking(client))