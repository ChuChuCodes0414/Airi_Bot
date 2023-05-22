import discord
from discord.ext import commands
from discord import app_commands, ui
from utils import methods, errors
from typing import Literal, List

class Configure(commands.Cog):
    """
        All configuration for the bot is under this group.
    """

    def __init__(self,client):
        self.client = client
        self.short = "⚙ | Bot Settings"
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('Configure Category Loaded.')
    
    @commands.hybrid_command(help = "The command to configure settings by category.")
    @commands.has_permissions(manage_guild = True)
    @commands.max_concurrency(1,commands.BucketType.guild)
    async def settings(self,ctx):
        view = SettingView(ctx)
        embed = discord.Embed(title = f"{self.client.user.name} Settings for {ctx.guild}",description = "Use the dropdown below to edit settings!")
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
        await view.wait()
    
    @commands.hybrid_command(help = "Configure any user based settings.")
    @commands.max_concurrency(1,commands.BucketType.user)
    async def usersettings(self,ctx):
        view = UserSettingView(ctx)
        embed = discord.Embed(title = f"{self.client.user.name} Settings for {ctx.author}",description = "Use the dropdown below to edit settings!")
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
        await view.wait()
    
    @commands.hybrid_command(help = "Enable a command for certain members, roles, or channels.")
    @commands.has_permissions(manage_guild = True) 
    @app_commands.describe(command = "The command name of which to setup an enable rule for.",parameter = "The member, channel, or role to enable the command for.") 
    async def enable(self,ctx,command,parameter):
        command = self.client.get_command(command)
        if not command:
            raise errors.ParsingError(message = "That does not look like a valid command name!")
        if not command.extras and "id" not in command.extras:
            raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is not able to have its permissions configured!")
        if parameter.lower() == "all":
            raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}.eall":1}) or {}
            if methods.query(data = raw, search = ["settings","rules",str(command.extras['id']),"eall"]):
                raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is already enabled for everyone.")
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"settings.rules.{command.extras['id']}.eall":True}})
            embed = discord.Embed(description = f"Enabled the command `{command.qualified_name}` for `all`.\nReminder that any 'enable' will override any 'disable' rule setup!",color = discord.Color.green())
            return await ctx.reply(embed = embed)
        
        try:
            object = await commands.converter.MemberConverter().convert(ctx,parameter)
            prefix = "users"
        except commands.BadArgument as e:
            try:
                object = await commands.converter.RoleConverter().convert(ctx,parameter)
                prefix = "roles"
            except commands.BadArgument as e:
                try:
                    object = await commands.converter.GuildChannelConverter().convert(ctx,parameter)
                    prefix = "channels"
                except:
                    raise errors.ParsingError(message = "I could not parse your input!\nReminder that only members, roles, and channels are acceptable as input.")
        
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}.e{prefix}":1}) or {}
        if object.id in (methods.query(data = raw, search = ["settings","rules",str(command.extras['id']),f"e{prefix}"]) or []):
            raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is already enabled for `{object.id}`.")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$addToSet":{f"settings.rules.{command.extras['id']}.e{prefix}":object.id}})
        embed = discord.Embed(description = f"Enabled the command `{command.qualified_name}` for `{object.id}`.\nReminder that any 'enable' will override any 'disable' rule setup!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_command(help = "Disable a command for certain members, roles, or channels.")
    @commands.has_permissions(manage_guild = True)
    @app_commands.describe(command = "The command name of which to setup a disable rule for.",parameter = "The member, channel, or role to disable the command for.") 
    async def disable(self,ctx,command,parameter):
        command = self.client.get_command(command)
        if not command:
            raise errors.ParsingError(message = "That does not look like a valid command name!")
        if not command.extras and "id" not in command.extras:
            raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is not able to have its permissions configured!")
        if parameter.lower() == "all":
            raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}.dall":1}) or {}
            if methods.query(data = raw, search = ["settings","rules",str(command.extras['id']),"dall"]):
                raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is already disabled for everyone.")
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"settings.rules.{command.extras['id']}.dall":True}})
            embed = discord.Embed(description = f"Disabled the command `{command.qualified_name}` for `all`.\nReminder that any 'enable' will override any 'disable' rule setup!",color = discord.Color.green())
            return await ctx.reply(embed = embed)

        try:
            object = await commands.converter.MemberConverter().convert(ctx,parameter)
            prefix = "users"
        except commands.BadArgument as e:
            try:
                object = await commands.converter.RoleConverter().convert(ctx,parameter)
                prefix = "roles"
            except commands.BadArgument as e:
                try:
                    object = await commands.converter.GuildChannelConverter().convert(ctx,parameter)
                    prefix = "channels"
                except:
                    raise errors.ParsingError(message = "I could not parse your input!\nReminder that only members, roles, and channels are acceptable as input.")
        
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}.d{prefix}":1}) or {}
        if object.id in (methods.query(data = raw, search = ["settings","rules",str(command.extras['id']),f"d{prefix}"]) or []):
            raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is already disable for `{object.id}`.")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$addToSet":{f"settings.rules.{command.extras['id']}.d{prefix}":object.id}})
        embed = discord.Embed(description = f"Enabled the command `{command.qualified_name}` for `{object.id}`.\nReminder that any 'enable' will override any 'disable' rule setup!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @commands.hybrid_group(help = "View commands that have rules setup, and manage the rules with them.")
    @commands.has_permissions(manage_guild = True)
    async def rules(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse `/help rules` to get a list of commands.")
    
    @rules.command(help = "View what commands have rules on them.")
    @commands.has_permissions(manage_guild = True)
    async def list(self,ctx):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules":1})
        rules = methods.query(data = raw,search = ["settings","rules"])

        if not rules:
            raise errors.NotSetupError(message = "No command rules are setup for this server!")
        
        mapping = {}

        for command in self.client.commands:
            if command.extras and "id" in command.extras and str(command.extras['id']) in rules:
                mapping[command.extras['id']] = command.qualified_name
        
        rules = "\n".join([mapping[x] for x in rules])
        embed = discord.Embed(title = f"Rules and Permissions for {ctx.guild.name}",description = rules)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @rules.command(help = "View what rules are setup for a command")
    @commands.has_permissions(manage_guild = True)
    @app_commands.describe(command = "The command name of which to view rules for.")
    async def view(self,ctx,command):
        command = self.client.get_command(command)
        if not command:
            raise errors.ParsingError(message = "That does not look like a valid command name!")
        if not command.extras and "id" not in command.extras:
            raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is not able to have its permissions configured!")
        
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}":1})
        rules = methods.query(data = raw,search = ["settings","rules",str(command.extras['id'])]) or {}
        eroles = rules.get("eroles",None)
        droles = rules.get("droles",None)
        echannels = rules.get("echannels",None)
        dchannels = rules.get("dchannels",None)
        eusers = rules.get("eusers",None)
        dusers = rules.get("dusers",None)
        eall = rules.get("eall",None)
        dall = rules.get("dall",None)

        embed = discord.Embed(title = f"Rules and Permissions for {command.qualified_name}")
        if eall:
            embed.add_field(name = f"**Enabled for All:**",value =  eall,inline = False)
        if dall:
            embed.add_field(name = f"**Disabled for All:**",value =  dall,inline = False)
        if eroles:
            embed.add_field(name = f"**Enabled Roles:** ",value = ' '.join(['<@&' + str(b) + '>' for b in eroles]),inline = False)
        if droles:
            embed.add_field(name = f"**Disabled Roles:**",value = ' '.join(['<@&' + str(b) + '>' for b in droles]),inline = False)
        if echannels:
            embed.add_field(name = f"**Enabled Channels:** ",value =' '.join(['<#' + str(b) + '>' for b in echannels]),inline = False)
        if dchannels:
            embed.add_field(name = f"**Disabled Channels:**",value = ' '.join(['<#' + str(b) + '>' for b in dchannels]),inline = False)
        if eusers:
            embed.add_field(name = f"**Enabled Users:** ",value =' '.join(['<@' + str(b) + '>' for b in eusers]),inline = False)
        if dusers:
            embed.add_field(name = f"**Disabled Users:** ",value =' '.join(['<@' + str(b) + '>' for b in dusers]),inline = False)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @rules.command(help = "Remove an enable or disable rule you have setup")
    @app_commands.describe(command = "The command name of which to remove rules for.",enabledisable = "Whether to remove an enable or disable rule.",parameter = "The member, role, or channel to remove a rule for.")
    @commands.has_permissions(manage_guild = True)
    async def remove(self,ctx,command,enabledisable:Literal['enable','disable'],parameter):
        command = self.client.get_command(command)
        if not command:
            raise errors.ParsingError(message = "That does not look like a valid command name!")
        if not command.extras and "id" not in command.extras:
            raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` is not able to have its permissions configured!")
        
        prefix = enabledisable[0]

        if parameter.lower() == "all":
            raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}.{prefix}all":1})
            if not methods.query(data = raw, search = ["settings","rules",str(command.extras['id']),f"{prefix}all"]):
                raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` does not have `{enabledisable}` setup for `all`.")
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{f"settings.rules.{command.extras['id']}.{prefix}all":""}})
            embed = discord.Embed(description = f"Removed the `{enabledisable}` rule for `all` under the command `{command.qualified_name}`!",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            return await ctx.reply(embed = embed)
        
        try:
            object = await commands.converter.MemberConverter().convert(ctx,parameter)
            suffix = "users"
        except commands.BadArgument as e:
            try:
                object = await commands.converter.RoleConverter().convert(ctx,parameter)
                suffix = "roles"
            except commands.BadArgument as e:
                try:
                    object = await commands.converter.GuildChannelConverter().convert(ctx,parameter)
                    suffix = "channels"
                except:
                    raise errors.ParsingError(message = "I could not parse your input!\nReminder that only members, roles, and channels are acceptable as input.")
        
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}.{prefix}{suffix}":1})
        if not object.id in methods.query(data = raw, search = ["settings","rules",str(command.extras['id']),f"{prefix}{suffix}"]):
            raise errors.PreRequisiteError(message = f"The command `{command.qualified_name}` does not have `{enabledisable}` setup for {object.mention}.")
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$pull":{f"settings.rules.{command.extras['id']}.{prefix}{suffix}":object.id}})

        if len(methods.query(data = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}.{prefix}{suffix}":1}),search = ["settings","rules",str(command.extras['id']),f"{prefix}{suffix}"]) or []) == 0:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{f"settings.rules.{command.extras['id']}.{prefix}{suffix}":""}})
        if len(methods.query(data = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"settings.rules.{command.extras['id']}":1}),search = ["settings","rules",str(command.extras['id'])]) or {}) == 0:
            self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{f"settings.rules.{command.extras['id']}":""}})
        embed = discord.Embed(description = f"Removed the `{enabledisable}` rule for {object.mention} under the command `{command.qualified_name}`!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @remove.autocomplete("command")
    @view.autocomplete("command")
    @enable.autocomplete("command")
    @disable.autocomplete("command")
    async def command_autocomplete(self, interaction: discord.Interaction, needle: str) -> List[app_commands.Choice[str]]:
        assert self.client.help_command
        ctx = await self.client.get_context(interaction, cls=commands.Context)
        needle = needle.lower()
        return [
            app_commands.Choice(name=command.qualified_name, value=command.qualified_name)
            for command in await self.client.get_cog("helpcommand").help_command.filter_commands(self.client.walk_commands(), sort=True)
            if needle in command.qualified_name
        ][:25]

class UserSettingView(ui.View):
    def __init__(self,ctx):
        super().__init__(timeout = 60)
        self.add_item(UserSettingsSelect())
        self.message = None
        self.ctx = ctx
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    async def generate_embed(self,category,data):
        embed = discord.Embed(title = f"{category} Settings")

        for title,data in data.items():
            if data[0] == "str":
                embed.add_field(name = title,value = str(data[1]))
        
        embed.set_footer(text = "Use the dropdowns to configure settings.")
        return embed

class UserSettingsSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label = "Sniper", description = "Setup whether or not your messages are sniped.",value = 0),
        ]
        super().__init__(placeholder = "Bot Category",min_values = 0, max_values = 1, options = options, row = 0)
    
    async def callback(self,interaction):
        if self.values[0] == "0":
            category = UserSniper(interaction,"settings.sniper")

        self.view.clear_items()
        self.view.add_item(self)
        for row,elements in enumerate(await category.pull_items()):
            for item in elements:
                item.row = row+1
                self.view.add_item(item)

        embed = await self.view.generate_embed(category.name,await category.generate_data())
        await interaction.response.edit_message(embed = embed,view = self.view)

class SettingView(ui.View):
    def __init__(self,ctx):
        super().__init__(timeout = 60)
        self.add_item(SettingsSelect())
        self.message = None
        self.ctx = ctx
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    async def generate_embed(self,category,data):
        embed = discord.Embed(title = f"{category} Settings")

        for title,data in data.items():
            if data[0] == "str":
                embed.add_field(name = title,value = str(data[1]))
            elif data[0] == "channel":
                if data[1]:
                    embed.add_field(name = title,value = f"<#{data[1]}>")
                else:
                    embed.add_field(name = title,value = f"No Channel Setup")
            elif data[0] == "role":
                if data[1]:
                    embed.add_field(name = title,value = f"<@&{data[1]}>")
                else:
                    embed.add_field(name = title,value = f"No Role Setup")
            elif data[0] == "clist":
                if data[1]:
                    embed.add_field(name = title,value = f"{len(data[1])} Channels")
                else:
                    embed.add_field(name = title,value = f"No Channels Setup")
        
        embed.set_footer(text = "Use the dropdowns to configure settings.")
        return embed

class SettingsSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label = "Bot Settings", description = "Change the bot prefix.",value = -1),
            discord.SelectOption(label = "Boost Tracking", description = "Toggle boost tracking and setup logging/announcing.",value = 0),
            discord.SelectOption(label = "Event Tracking", description = "Setup event roles and logging.",value = 1),
            discord.SelectOption(label = "Invite Tracking", description = "Setup where the invite logger goes.",value = 2),
            discord.SelectOption(label = "Mod Tracking", description = "Setup mod tracking roles and logging.",value = 3),
            discord.SelectOption(label = "Sniper", description = "Setup message sniping lookback and cooldown.",value = 4),
            discord.SelectOption(label = "Channels", description = "Setup lockdown role and channels.",value = 5),
            discord.SelectOption(label = "Channels 2",description = "Setup lockdown messages.",value = 6),
            discord.SelectOption(label = "Utility", description = "Setup bump channel and ping role.",value = 7),
            discord.SelectOption(label = "Utility 2", description = "Setup AFK ignore channels.",value = 8)
        ]
        super().__init__(placeholder = "Bot Category",min_values = 0, max_values = 1, options = options, row = 0)
    
    async def callback(self,interaction):
        if self.values[0] == "0":
            category = BoostTracking(interaction,"settings.boosttracking")
        elif self.values[0] == "1":
            category = EventTracking(interaction,"settings.eventtracking")
        elif self.values[0] == "2":
            category = InviteTracking(interaction,"settings.invitetracking")
        elif self.values[0] == "3":
            category = ModTracking(interaction,"settings.modtracking")
        elif self.values[0] == "4":
            category = Sniper(interaction,"settings.sniper")
        elif self.values[0] == "5":
            category = Channels(interaction,"settings.channels")
        elif self.values[0] == "6":
            category = Channels2(interaction,"settings.channels")
        elif self.values[0] == "7":
            category = Utility(interaction,"settings.utility")
        elif self.values[0] == "8":
            category = Utility2(interaction,"settings.utility")
        elif self.values[0] == "-1":
            category = BotSettings(interaction,"settings.general")

        self.view.clear_items()
        self.view.add_item(self)
        for row,elements in enumerate(await category.pull_items()):
            for item in elements:
                item.row = row+1
                self.view.add_item(item)

        embed = await self.view.generate_embed(category.name,await category.generate_data())
        await interaction.response.edit_message(embed = embed,view = self.view)
    
class Remove_Button(ui.Button):
    def __init__(self,key,category,**kwargs):
        super().__init__(style = discord.ButtonStyle.red,**kwargs)
        self.key = key
        self.category = category
    
    async def callback(self,interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$unset":{self.key:""}})
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Channel_Select(ui.ChannelSelect):
    def __init__(self,setting,key,category,**kwargs):
        super().__init__(placeholder = setting,**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{self.key:self.values[0].id}})
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Bump_Channel_Select(ui.ChannelSelect):
    def __init__(self,setting,key,category,**kwargs):
        super().__init__(placeholder = setting,**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{self.key:self.values[0].id}})
        cog = interaction.client.get_cog("utility")
        cog.active[str(interaction.guild.id)] = self.values[0].id
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)
    
class View_Channel_List(ui.Button):
    def __init__(self,key,**kwargs):
        super().__init__(**kwargs)
        self.key = key
    
    async def callback(self,interaction):
        raw = interaction.client.db.guild_data.find_one({"_id":interaction.guild.id},{self.key:1})
        list = methods.query(data = raw,search = self.key.split("."))
        if not list or len(list) <= 0:
            embed = discord.Embed(description = "No Channels Defined")
            return await interaction.response.send_message(embed = embed,ephemeral = True)
        format = "\n".join([f"<#{x}>" for x in list])
        embed = discord.Embed(description = format)
        await interaction.response.send_message(embed = embed,ephemeral = True)

class Add_Channel_Select(ui.ChannelSelect):
    def __init__(self,setting,key,category,**kwargs):
        super().__init__(placeholder = setting,**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$addToSet":{self.key:self.values[0].id}})
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Remove_Channel_Select(ui.ChannelSelect):
    def __init__(self,setting,key,category,**kwargs):
        super().__init__(placeholder = setting,**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$pull":{self.key:self.values[0].id}})
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Add_AFK_Channel_Select(ui.ChannelSelect):
    def __init__(self,setting,key,category,**kwargs):
        super().__init__(placeholder = setting,**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$addToSet":{self.key:self.values[0].id}})
        cog = interaction.client.get_cog("utility")
        current = cog.ignore.get(interaction.guild.id)
        if current:
            if self.values[0].id not in current:
                cog.ignore[str(interaction.guild.id)].append(self.values[0].id)
        else:
            cog.ignore[str(interaction.guild.id)] = [self.values[0].id]
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Remove_AFK_Channel_Select(ui.ChannelSelect):
    def __init__(self,setting,key,category,**kwargs):
        super().__init__(placeholder = setting,**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$pull":{self.key:self.values[0].id}})
        cog = interaction.client.get_cog("utility")
        if self.values[0].id in cog.ignore.get(interaction.guild.id,[]):
            cog.ignore[str(interaction.guild.id)].remove(self.values[0].id)
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Role_Select(ui.RoleSelect):
    def __init__(self,setting,key,category,**kwargs):
        super().__init__(placeholder = setting,**kwargs)
        self.key = key
        self.category = category
    
    async def callback(self,interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{self.key:self.values[0].id}})
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class User_Sniper_Toggle_Select(ui.Select):
    def __init__(self,key,category,**kwargs):
        super().__init__(options = [
            discord.SelectOption(label = "True",value = True),
            discord.SelectOption(label = "False",value = False)
        ], placeholder = "Enabled",**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{self.key:self.values[0] == "True"}},upsert = True)
        cog = interaction.client.get_cog("sniper")
        if self.values[0] == "True":
            cog.user_settings[interaction.user.id] = True
        elif self.values[0] == "False":
            cog.user_settings[interaction.user.id] = False
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Boost_Toggle_Select(ui.Select):
    def __init__(self,key,category,**kwargs):
        super().__init__(options = [
            discord.SelectOption(label = "True",value = True),
            discord.SelectOption(label = "False",value = False)
        ], placeholder = "Enabled",**kwargs)
        self.key = key
        self.category = category

    async def callback(self, interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{self.key:self.values[0] == "True"}})
        cog = interaction.client.get_cog("boosttracking")
        if self.values[0] == "True" and interaction.guild.id not in cog.active:
            cog.active.append(interaction.guild.id)
        elif self.values[0] == "False" and interaction.guild.id in cog.active:
            cog.active.remove(interaction.guild.id)
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Send_Modal(ui.Button):
    def __init__(self,modal,**kwargs):
        super().__init__(**kwargs)
        self.modal = modal
    
    async def callback(self,interaction):
        self.modal.view = self.view
        await interaction.response.send_modal(self.modal)

class Prefix_Text_input(ui.Modal,title = "Bot Prefix Setting"):
    def __init__(self,category):
        super().__init__()
        self.category = category
        self.view = None
    
    input = discord.ui.TextInput(label = "Box Prefix",placeholder = "The prefix for all text commands.")

    async def on_submit(self,interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{"settings.general.prefix":self.input.value}})
        interaction.client.prefixes[interaction.guild_id] = self.input.value
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Lockdown_Text_Input(ui.Modal,title = "Lockdown Message Setting"):
    def __init__(self,category):
        super().__init__()
        self.category = category
        self.view = None
    
    input = discord.ui.TextInput(label = "Lockdown Message",placeholder = "The message to display when the server is locked down.")

    async def on_submit(self,interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{"settings.channels.lmessage":self.input.value}})
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Unlockdown_Text_Input(ui.Modal,title = "Unockdown Message Setting"):
    def __init__(self,category):
        super().__init__()
        self.category = category
        self.view = None
    
    input = discord.ui.TextInput(label = "Unlockdown Message",placeholder = "The message to display when the server is unlocked down.")

    async def on_submit(self,interaction):
        interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{"settings.channels.ulmessage":self.input.value}})
        embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
        await interaction.response.edit_message(embed = embed)

class Lookback_Text_Input(ui.Modal,title = "Snipe Lookback Setting"):
    def __init__(self,category):
        super().__init__()
        self.category = category
        self.view = None
    
    input = discord.ui.TextInput(label = "Snipe Lookback",placeholder = "The amount of messages to save, per channel.")

    async def on_submit(self,interaction):
        if self.input.value.isnumeric() and int(self.input.value) >= 0:
            interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{"settings.sniper.snipelb":int(self.input.value)}})
            cog = interaction.client.get_cog("sniper")
            cog.settings[interaction.guild.id][0] = int(self.input.value)
            embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
            await interaction.response.edit_message(embed = embed)
        else:
            embed = discord.Embed(description = "Your input needs to be numeric and greater than or equal to 0!",color = discord.Color.red())
            await interaction.response.send_message(embed = embed,ephemeral = True)

class Cooldown_Text_Input(ui.Modal,title = "Snipe Cooldown Setting"):
    def __init__(self,category):
        super().__init__()
        self.category = category
        self.view = None
    
    input = discord.ui.TextInput(label = "Snipe Cooldown",placeholder = "The time to keep messages saved, in seconds.")

    async def on_submit(self,interaction):
        if self.input.value.isnumeric() and int(self.input.value) >= 0:
            interaction.client.db.guild_data.update_one({"_id":interaction.guild.id},{"$set":{"settings.sniper.snipecd":int(self.input.value)}})
            cog = interaction.client.get_cog("sniper")
            cog.settings[interaction.guild.id][1] = int(self.input.value)
            embed = await self.view.generate_embed(self.category.name, await self.category.generate_data())
            await interaction.response.edit_message(embed = embed)
        else:
            embed = discord.Embed(description = "Your input needs to be numeric and greater than or equal to 0!",color = discord.Color.red())
            await interaction.response.send_message(embed = embed,ephemeral = True)

class UserSniper():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "User Sniper Settings"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.user_data.find_one({"_id":self.initialinteraction.user.id},{self.key:1}) or {}
        snipeblock = methods.query(data = data, search = ["settings","sniper","snipeblock"])
        return {"Enabled":["str",snipeblock]}

    async def pull_items(self):
        return [
            [User_Sniper_Toggle_Select("settings.sniper.snipeblock",self)],
        ]

class BoostTracking():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Boost Tracking"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        active = methods.query(data = data, search = ["settings","boosttracking","active"])
        achannel = methods.query(data = data, search = ["settings","boosttracking","announce"])
        lchannel = methods.query(data = data, search = ["settings","boosttracking","logging"])
        return {"Enabled":["str",active],"Announcement Channel":["channel",achannel],"Logging Channel":["channel",lchannel]}

    async def pull_items(self):
        return [
            [Boost_Toggle_Select("settings.boosttracking.active",self)],
            [Channel_Select("Announcement Channel","settings.boosttracking.announce",self,channel_types = [discord.ChannelType.text])],
            [Channel_Select("Logging Channel","settings.boosttracking.logging",self,channel_types = [discord.ChannelType.text])],
            [Remove_Button("settings.boosttracking.announce",self,label = "Remove Announcement"),Remove_Button("settings.boosttracking.logging",self,label = "Remove Logging")]
        ]

class EventTracking():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Event Tracking"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        erole = methods.query(data = data, search = ["settings","eventtracking","erole"])
        ping = methods.query(data = data, search = ["settings","eventtracking","ping"])
        lchannel = methods.query(data = data, search = ["settings","eventtracking","logging"])
        return {"Event Manager Role":["role",erole],"Event Ping Role":["role",ping],"Logging Channel":["channel",lchannel]}

    async def pull_items(self):
        return [
            [Role_Select("Event Manager Role","settings.eventtracking.erole",self)],
            [Role_Select("Event Ping Role","settings.eventtracking.ping",self)],
            [Channel_Select("Event Logging Channel","settings.eventtracking.logging",self,channel_types = [discord.ChannelType.text])],
            [Remove_Button("settings.eventtracking.erole",self,label = "Remove Manager"),Remove_Button("settings.eventtracking.ping",self,label = "Remove Ping"),Remove_Button("settings.eventtracking.logging",self,label = "Remove Logging")]
        ]

class InviteTracking():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Invite Tracking"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        lchannel = methods.query(data = data, search = ["settings","invitetracking","logging"])
        return {"Logging Channel":["channel",lchannel]}

    async def pull_items(self):
        return [
            [Channel_Select("Invite Logging Channel","settings.invitetracking.logging",self,channel_types = [discord.ChannelType.text])],
            [Remove_Button("settings.invitetracking,logging",self,label = "Remove Logging")]
        ]

class ModTracking():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Mod Tracking"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        mrole = methods.query(data = data, search = ["settings","modtracking","mrole"])
        lchannel = methods.query(data = data, search = ["settings","modtracking","logging"])
        return {"Mod Tracking Role":["role",mrole],"Logging Channel":["channel",lchannel]}

    async def pull_items(self):
        return [
            [Role_Select("Mod Tracking Role","settings.modtracking.mrole",self)],
            [Channel_Select("Mod Tracking Logging Channel","settings.modtracking.logging",self,channel_types = [discord.ChannelType.text])],
            [Remove_Button("settings.modtracking.mrole",self,label = "Remove Tracking Role"),Remove_Button("settings.modtracking.ping",self,label = "Remove Logging")]
        ]

class Sniper():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Sniper"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        snipelb = methods.query(data = data, search = ["settings","sniper","snipelb"])
        snipecd = methods.query(data = data, search = ["settings","sniper","snipecd"])
        return {"Snipe Lookback":["str",snipelb],"Snipe Cooldown":["str",snipecd]}

    async def pull_items(self):
        return [
            [Send_Modal(Lookback_Text_Input(self),label = "Snipe Lookback"),Send_Modal(Cooldown_Text_Input(self),label = "Snipe Cooldown")]
        ]

class Channels():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Channels"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        lrole = methods.query(data = data, search = ["settings","channels","lrole"])
        lchannels = methods.query(data = data, search = ["settings","channels","lchannels"])
        return {"Lockdown Role":["role",lrole],"Lockdown Channels":["clist",lchannels]}

    async def pull_items(self):
        return [
            [Role_Select("Lockdown Role","settings.channels.lrole",self)],
            [Add_Channel_Select("Add Lockdown Channel","settings.channels.lchannels",self,channel_types = [discord.ChannelType.text])],
            [Remove_Channel_Select("Remove Lockdown Channel","settings.channels.lchannels",self,channel_types = [discord.ChannelType.text])],
            [View_Channel_List(key = "settings.channels.lchannels",label = "View Lockdown Channels"),Remove_Button("settings.channels.lrole",self,label = "Remove Lockdown Role")]
        ]

class Channels2():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Channels"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        lmessage = methods.query(data = data, search = ["settings","channels","lmessage"])
        ulmessage = methods.query(data = data, search = ["settings","channels","ulmessage"])
        return {"Lockdown Message":["str",lmessage],"Unlockdown Message":["str",ulmessage]}

    async def pull_items(self):
        return [
            [Send_Modal(Lockdown_Text_Input(self),label = "Lockdown Message"),Send_Modal(Unlockdown_Text_Input(self),label = "Unlockdown Message")],
            [Remove_Button("settings.channels.lmessage",self,label = "Remove Lockdown Message"),Remove_Button("settings.channels.ulmessage",self,label = "Remove Unlockdown Message")]
        ]

class Utility():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Utility"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        bping = methods.query(data = data, search = ["settings","utility","bping"])
        bumpchannel = methods.query(data = data, search = ["settings","utility","bumpchannel"])
        return {"Bump Ping Role":["role",bping],"Bump Channel":["channel",bumpchannel]}

    async def pull_items(self):
        return [
            [Role_Select("Bump Ping Role","settings.utility.bping",self)],
            [Bump_Channel_Select("Bump Channel","settings.utility.bumpchannel",self)],
            [Remove_Button("settings.utility.bping",self,label = "Remove Bump Ping Role"),Remove_Button("settings.utility.bumpchannel",self,label = "Remove Bump Channel")]
        ]
    
class Utility2():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Utility"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        afkchannels = methods.query(data = data, search = ["settings","utility","afkchannels"])
        return {"AFK Ignore Channels":["clist",afkchannels]}

    async def pull_items(self):
        return [
            [Add_AFK_Channel_Select("Add AFK Ignore Channel","settings.utility.afkchannels",self,channel_types = [discord.ChannelType.text])],
            [Remove_AFK_Channel_Select("Remove AFK Ignore Channel","settings.utility.afkchannels",self,channel_types = [discord.ChannelType.text])],
            [View_Channel_List("settings.utility.afkchannels",label = "View AFK Ignore Channels")]
        ]

class BotSettings():
    def __init__(self,initialinteraction,key):
        self.initialinteraction = initialinteraction
        self.key = key
        self.name = "Bot Settings"
    
    async def generate_data(self):
        data = self.initialinteraction.client.db.guild_data.find_one({"_id":self.initialinteraction.guild_id},{self.key:1}) or {}
        prefix = methods.query(data = data, search = ["settings","general","prefix"]) or "m?"
        return {"Bot Prefix":["str",prefix]}

    async def pull_items(self):
        return [
            [Send_Modal(Prefix_Text_input(self),label = "Bot Prefix")],
        ]


async def setup(client):
    await client.add_cog(Configure(client))