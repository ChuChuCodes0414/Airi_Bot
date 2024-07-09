import discord
from discord import app_commands
from discord.ext import commands
from utils import errors
from utils import methods
from utils import classes
import asyncio

class Channels(commands.Cog):
    """
        Channel management, including locking, unlocking, slowmode, and more.
    """

    def __init__(self, client):
        self.hidden = False
        self.client = client
        self.short = "💬 | Channel Management"

    @commands.Cog.listener()
    async def on_ready(self):
        print("Channels Category Loaded")

    @commands.hybrid_command(extras = {"id":"201"}, help="Lockdown the server bassed on the channels that you have setup.")
    @commands.has_guild_permissions(manage_permissions=True)
    @commands.cooldown(1, 20, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @app_commands.describe(text = "The message to display on lockdown notifications.")
    async def lockdown(self, ctx, *, text: str = None):
        raw = self.client.db.guild_data.find_one({"_id": ctx.guild.id}, {f"settings.channels": 1}) or {}

        if methods.query(data = raw, search = ["settings", "channels","lockdown"]):
            raise errors.PreRequisiteError(message = "This server is already locked!")
        
        channels =  methods.query(data=raw, search=["settings", "channels","lchannels"])
        if not channels:
            raise errors.NotSetupError(message = "Lockdown channels are not setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        
        role = methods.query(data = raw, search = ["settings", "channels", "lrole"])
        if role:
            role = ctx.guild.get_role(role)

            if not role:
                raise errors.NotSetupError(message = "Lockdown role is not properly setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        else:
            role = ctx.guild.default_role
        
        view = classes.ConfirmationView(ctx)
        message = await ctx.reply(embed = discord.Embed(title = "⚠ Initiating Lockdown! ⚠",description = f"Are you sure you want to lockdown {len(channels)} channels for {role.mention}?",color = discord.Color.red()),view = view)
        view.message = message
        result = await view.wait()
        for child in view.children:
            child.disabled = True
        await message.edit(view = view)
        if result:
            return await message.reply(embed = discord.Embed(description = "Request timed out! Cancelling lockdown...",color = discord.Color.red()))
        if not view.value:
            return await message.reply(embed = discord.Embed(description = "Alright then, as you wish. Cancelling lockdown...",color = discord.Color.red()))
        
        invalidchannels = []
        message = await ctx.reply(embed = discord.Embed(description = f"Now locking {len(channels)} channels for {role.mention}\nETA: `{len(channels)*0.3}` seconds",color = discord.Color.yellow()))
        text = text or methods.query(data = raw, search = ["settings", "channels","lmessage"]) or "This server has been locked down!"

        embed = discord.Embed(title = "Server Lockdown",description = text,color = discord.Color.red())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)

        for channelid in channels:
            try:
                channel = ctx.guild.get_channel(channelid)
                overwrite = channel.overwrites_for(role)
                overwrite.send_messages = False
                overwrite.send_messages_in_threads = False
                await channel.set_permissions(role, overwrite=overwrite)
                if channel.type != discord.ChannelType.forum:
                    await channel.send(embed = embed)
                await asyncio.sleep(0.3)
            except:
                invalidchannels.append(channelid)
        
        if len(invalidchannels) > 0:
            des = ",".join([x for x in invalidchannels])
            embed = discord.Embed(title = "Server Locked Down",description = f"Could not lock:\n{des}",color = discord.Color.green())
        else:
            embed = discord.Embed(title = "Server Locked Down",description = f"All channels successfully locked!",color = discord.Color.green())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name + " | Run /unlockdown to unlock!")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{"settings.channels.lockdown":True}})
        await message.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id":"202"}, help="Unlockdown the server bassed on the channels that you have setup.")
    @commands.has_guild_permissions(manage_permissions=True)
    @commands.cooldown(1, 20, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @app_commands.describe(text = "The message to display on lockdown notifications.")
    async def unlockdown(self, ctx, *, text: str = None):
        raw = self.client.db.guild_data.find_one({"_id": ctx.guild.id}, {f"settings.channels": 1}) or {}

        if not methods.query(data = raw, search = ["settings", "channels","lockdown"]):
            raise errors.PreRequisiteError(message = "This server is not locked!")
        
        channels =  methods.query(data=raw, search=["settings", "channels","lchannels"])
        if not channels:
            raise errors.NotSetupError(message = "Lockdown channels are not setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        
        role = methods.query(data = raw, search = ["settings", "channels", "lrole"])
        if role:
            role = ctx.guild.get_role(role)

            if not role:
                raise errors.NotSetupError(message = "Lockdown role is not properly setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        else:
            role = ctx.guild.default_role
        
        view = classes.ConfirmationView(ctx)
        message = await ctx.reply(embed = discord.Embed(title = "⚠ Initiating Unlockdown! ⚠",description = f"Are you sure you want to unlockdown {len(channels)} channels for {role.mention}?",color = discord.Color.red()),view = view)
        view.message = message
        result = await view.wait()
        for child in view.children:
            child.disabled = True
        await message.edit(view = view)
        if result:
            return await message.reply(embed = discord.Embed(description = "Request timed out! Cancelling unlockdown...",color = discord.Color.red()))
        if not view.value:
            return await message.reply(embed = discord.Embed(description = "Alright then, as you wish. Cancelling unlockdown...",color = discord.Color.red()))
        
        invalidchannels = []
        message = await ctx.reply(embed = discord.Embed(description = f"Now unlocking {len(channels)} channels for {role.mention}\nETA: `{len(channels)*0.3}` seconds",color = discord.Color.yellow()))
        text = text or methods.query(data = raw, search = ["settings", "channels","ulmessage"]) or "This server has been unlocked!"


        embed = discord.Embed(title = "Server Unlocked",description = text,color = discord.Color.green())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)

        for channelid in channels:
            try:
                channel = ctx.guild.get_channel(channelid)
                overwrite = channel.overwrites_for(role)
                overwrite.send_messages = None
                overwrite.send_messages_in_threads = None
                await channel.set_permissions(role, overwrite=overwrite)
                if channel.type != discord.ChannelType.forum:
                    await channel.send(embed = embed)
                await asyncio.sleep(0.3)
            except:
                invalidchannels.append(channelid)
        
        if len(invalidchannels) > 0:
            des = ",".join([x for x in invalidchannels])
            embed = discord.Embed(title = "Server Unlocked",description = f"Could not unlock:\n{des}",color = discord.Color.green())
        else:
            embed = discord.Embed(title = "Server Unlocked",description = f"All channels successfully unlocked!",color = discord.Color.green())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name + " | Run /lockdown to lock!")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{"settings.channels.lockdown":""}})
        await message.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id":"203"}, help="View lockdown the server bassed on the channels that you have setup.", documentation = "This edits the view channel perm to false.")
    @commands.has_guild_permissions(manage_permissions=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @app_commands.describe(text = "The message to display on lockdown notifications.")
    async def viewlockdown(self, ctx, *, text: str = None):
        raw = self.client.db.guild_data.find_one({"_id": ctx.guild.id}, {f"settings.channels": 1}) or {}

        if methods.query(data = raw, search = ["settings", "channels","vlockdown"]):
            raise errors.PreRequisiteError(message = "This server is already viewlocked!")
        
        channels =  methods.query(data=raw, search=["settings", "channels","lchannels"])
        if not channels:
            raise errors.NotSetupError(message = "Lockdown channels are not setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        
        role = methods.query(data = raw, search = ["settings", "channels", "lrole"])
        if role:
            role = ctx.guild.get_role(role)

            if not role:
                raise errors.NotSetupError(message = "Lockdown role is not properly setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        else:
            role = ctx.guild.default_role
        
        view = classes.ConfirmationView(ctx)
        message = await ctx.reply(embed = discord.Embed(title = "⚠ Initiating Viewlockdown! ⚠",description = f"Are you sure you want to lockdown {len(channels)} channels for {role.mention}?",color = discord.Color.red()),view = view)
        view.message = message
        result = await view.wait()
        for child in view.children:
            child.disabled = True
        await message.edit(view = view)
        if result:
            return await message.reply(embed = discord.Embed(description = "Request timed out! Cancelling viewlockdown...",color = discord.Color.red()))
        if not view.value:
            return await message.reply(embed = discord.Embed(description = "Alright then, as you wish. Cancelling viewlockdown...",color = discord.Color.red()))
        
        invalidchannels = []
        message = await ctx.reply(embed = discord.Embed(description = f"Now viewlocking {len(channels)} channels for {role.mention}\nETA: `{len(channels)*0.5}` seconds",color = discord.Color.yellow()))
        text = text or methods.query(data = raw, search = ["settings", "channels","lmessage"]) or "This server has been viewlocked!"

        embed = discord.Embed(title = "Server Viewockdown",description = text,color = discord.Color.red())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)

        for channelid in channels:
            try:
                channel = ctx.guild.get_channel(channelid)
                overwrite = channel.overwrites_for(role)
                overwrite.view_channel = False
                await channel.set_permissions(role, overwrite=overwrite)
                if channel.type != discord.ChannelType.forum:
                    await channel.send(embed = embed)
                await asyncio.sleep(0.5)
            except:
                invalidchannels.append(channelid)
    
        if len(invalidchannels) > 0:
            des = ",".join([x for x in invalidchannels])
            embed = discord.Embed(title = "Server Viewlocked Down",description = f"Could not lock:\n{des}",color = discord.Color.green())
        else:
            embed = discord.Embed(title = "Server Viewlocked Down",description = f"All channels successfully locked!",color = discord.Color.green())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name + " | Run /unviewlockdown to unlock!")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{"settings.channels.vlockdown":True}})
        await message.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id":"204"}, help="View unlockdown the server bassed on the channels that you have setup.", documentation = "This edits the view channel perm to neutral.")
    @commands.has_guild_permissions(manage_permissions=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.guild)
    @app_commands.describe(text = "The message to display on lockdown notifications.")
    async def viewunlockdown(self, ctx, *, text: str = None):
        raw = self.client.db.guild_data.find_one({"_id": ctx.guild.id}, {f"settings.channels": 1}) or {}

        if not methods.query(data = raw, search = ["settings", "channels","vlockdown"]):
            raise errors.PreRequisiteError(message = "This server is not viewlocked!")
        
        channels =  methods.query(data=raw, search=["settings", "channels","lchannels"])
        if not channels:
            raise errors.NotSetupError(message = "Lockdown channels are not setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        
        role = methods.query(data = raw, search = ["settings", "channels", "lrole"])
        if role:
            role = ctx.guild.get_role(role)

            if not role:
                raise errors.NotSetupError(message = "Lockdown role is not properly setup!\nIf you are a server manager, try configuring with </settings:1023762091603132501>.")
        else:
            role = ctx.guild.default_role
        
        view = classes.ConfirmationView(ctx)
        message = await ctx.reply(embed = discord.Embed(title = "⚠ Initiating Viewunlockdown! ⚠",description = f"Are you sure you want to unlockdown {len(channels)} channels for {role.mention}?",color = discord.Color.red()),view = view)
        view.message = message
        result = await view.wait()
        for child in view.children:
            child.disabled = True
        await message.edit(view = view)
        if result:
            return await message.reply(embed = discord.Embed(description = "Request timed out! Cancelling viewunlockdown...",color = discord.Color.red()))
        if not view.value:
            return await message.reply(embed = discord.Embed(description = "Alright then, as you wish. Cancelling viewunlockdown...",color = discord.Color.red()))
        
        invalidchannels = []
        message = await ctx.reply(embed = discord.Embed(description = f"Now viewunlocking {len(channels)} channels for {role.mention}\nETA: `{len(channels)*0.5}` seconds",color = discord.Color.yellow()))
        text = text or methods.query(data = raw, search = ["settings", "channels","lmessage"]) or "This server has been viewunlocked!"

        embed = discord.Embed(title = "Server Viewunlocked",description = text,color = discord.Color.green())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)

        for channelid in channels:
            try:
                channel = ctx.guild.get_channel(channelid)
                overwrite = channel.overwrites_for(role)
                overwrite.view_channel = None
                await channel.set_permissions(role, overwrite=overwrite)
                if channel.type != discord.ChannelType.forum:
                    await channel.send(embed = embed)
                await asyncio.sleep(0.5)
            except:
                invalidchannels.append(channelid)
        
        if len(invalidchannels) > 0:
            des = ",".join([x for x in invalidchannels])
            embed = discord.Embed(title = "Server Viewunlocked Down",description = f"Could not unlock:\n{des}",color = discord.Color.green())
        else:
            embed = discord.Embed(title = "Server Viewunlocked Down",description = f"All channels successfully unlocked!",color = discord.Color.green())
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name + " | Run /viewlockdown to lock!")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{"settings.channels.vlockdown":""}})
        await message.reply(embed = embed)

    @commands.hybrid_command(extras = {"id": "205"}, help = "Lock a channel for everyone or for a role.")
    @commands.has_guild_permissions(manage_permissions = True)
    @app_commands.describe(role = "The role to edit permissions for.")
    @app_commands.describe(channel = "The channel to edit permissions for.")
    async def lock(self,ctx,role:discord.Role = None,channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        role = role or ctx.guild.default_role

        overwrite = channel.overwrites_for(role)
        if overwrite.send_messages == False:
            raise errors.PreRequisiteError(message = f"Channel {channel.mention} is already locked for {role.mention}!")
        overwrite.send_messages = False
        await channel.set_permissions(role, overwrite = overwrite)

        embed = discord.Embed(description = f"🔒 Channel {channel.mention} locked for {role.mention}",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url,text = self.client.user.name + " | Run /unlock to unlock it again!")
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "206"}, help = "Set speaking perms to neutral for a channel for everyone or for a role.")
    @commands.has_guild_permissions(manage_permissions = True)
    @app_commands.describe(role = "The role to edit permissions for.")
    @app_commands.describe(channel = "The channel to edit permissions for.")
    async def neutral(self,ctx,role:discord.Role = None,channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        role = role or ctx.guild.default_role

        overwrite = channel.overwrites_for(role)
        if overwrite.send_messages == None:
            raise errors.PreRequisiteError(message = f"Channel {channel.mention} already has perms set to neutral for {role.mention}!")
        overwrite.send_messages = None
        await channel.set_permissions(role, overwrite = overwrite)

        embed = discord.Embed(description = f"😐 Channel {channel.mention} set to neutral for {role.mention}",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url,text = self.client.user.name + " | Run /lock to lock it again!")
        await ctx.reply(embed = embed)

    @commands.hybrid_command(extras = {"id": "207"}, help = "Unlock a channel for everyone or for a role.")
    @commands.has_guild_permissions(manage_permissions = True)
    @app_commands.describe(role = "The role to edit permissions for.")
    @app_commands.describe(channel = "The channel to edit permissions for.")
    async def unlock(self,ctx,role:discord.Role = None,channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        role = role or ctx.guild.default_role

        overwrite = channel.overwrites_for(role)
        if overwrite.send_messages == True:
            raise errors.PreRequisiteError(message = f"Channel {channel.mention} is already unlocked for {role.mention}!")
        overwrite.send_messages = True
        await channel.set_permissions(role, overwrite = overwrite)

        embed = discord.Embed(description = f"🔓 Channel {channel.mention} unlocked for {role.mention}",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url,text = self.client.user.name + " | Run /lock to lock it again!")
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "208"}, help = "Viewlock a channel for everyone or for a role.")
    @commands.has_guild_permissions(manage_permissions = True)
    @app_commands.describe(role = "The role to edit permissions for.")
    @app_commands.describe(channel = "The channel to edit permissions for.")
    async def viewlock(self,ctx,role:discord.Role = None,channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        role = role or ctx.guild.default_role

        overwrite = channel.overwrites_for(role)
        if overwrite.view_channel == False:
            raise errors.PreRequisiteError(message = f"Channel {channel.mention} is already viewlocked for {role.mention}!")
        overwrite.view_channel = False
        await channel.set_permissions(role, overwrite = overwrite)

        embed = discord.Embed(description = f"🔒 Channel {channel.mention} viewlocked for {role.mention}",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url,text = self.client.user.name + " | Run /viewunlock to unlock it again!")
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "209"}, help = "Set viewing perms to neutral for a channel for everyone or for a role.")
    @commands.has_guild_permissions(manage_permissions = True)
    @app_commands.describe(role = "The role to edit permissions for.")
    @app_commands.describe(channel = "The channel to edit permissions for.")
    async def viewneutral(self,ctx,role:discord.Role = None,channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        role = role or ctx.guild.default_role

        overwrite = channel.overwrites_for(role)
        if overwrite.view_channel == None:
            raise errors.PreRequisiteError(message = f"Channel {channel.mention} already has perms set to neutral for {role.mention}!")
        overwrite.view_channel = None
        await channel.set_permissions(role, overwrite = overwrite)

        embed = discord.Embed(description = f"😐 Channel {channel.mention} set to neutral for {role.mention}",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url,text = self.client.user.name + " | Run /viewlock to lock it again!")
        await ctx.reply(embed = embed)

    @commands.hybrid_command(extras = {"id": "210"}, help = "Viewunlock a channel for everyone or for a role.")
    @commands.has_guild_permissions(manage_permissions = True)
    @app_commands.describe(role = "The role to edit permissions for.")
    @app_commands.describe(channel = "The channel to edit permissions for.")
    async def viewunlock(self,ctx,role:discord.Role = None,channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        role = role or ctx.guild.default_role

        overwrite = channel.overwrites_for(role)
        if overwrite.view_channel == True:
            raise errors.PreRequisiteError(message = f"Channel {channel.mention} is already viewunlocked for {role.mention}!")
        overwrite.view_channel = True
        await channel.set_permissions(role, overwrite = overwrite)

        embed = discord.Embed(description = f"🔓 Channel {channel.mention} viewunlocked for {role.mention}",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url,text = self.client.user.name + " | Run /viewlock to lock it again!")
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(extras = {"id": "211"},aliases = ['sm'],help ="Change the slowmode of the current channel to the specified amount of seconds.")
    @commands.has_guild_permissions(manage_channels= True)
    @app_commands.describe(time = "What time to set the slowmode to.")
    async def slowmode(self,ctx,time):
        time = methods.timeparse(str(time),0,21600)
        if isinstance(time,str):
            return await ctx.reply(embed = discord.Embed(description = time,color = discord.Color.red()))
        await ctx.channel.edit(slowmode_delay=time.seconds)
        await ctx.reply(f"Set the slowmode delay in this channel to `{time}` seconds!")

    @commands.hybrid_command(extras = {"id": "212"},help ="Purge messages in the channel.")
    @commands.has_permissions(manage_messages= True)
    @app_commands.describe(amount = "How many messages to be purged")
    async def purge(self,ctx, amount:int):
        await ctx.reply(embed = discord.Embed(description = "Purging messages, please standby.",color = discord.Color.random()),ephemeral = True)
        await ctx.channel.purge(limit= amount+1)
        await ctx.send(embed = discord.Embed(description = f'Purged {amount} messages!',color = discord.Color.green()), delete_after = 3)

async def setup(client):
    await client.add_cog(Channels(client))
