from typing import List, Optional
import discord
from discord import ui, app_commands
from discord.ext import commands, menus
from itertools import starmap, chain

class MyHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        self.verify_checks = False
        self.command_attrs = {
            "hidden":True,
            "name":"help",
            "help": "A helpful command to get started!"
        }

    def get_command_brief(self, command):
        return command.help or "Command is not documented."

    async def send_bot_help(self, mapping):
        message = self.get_destination()
        embed = discord.Embed(title = f"Bot Help",description = f"Categories Listed Below | `{len(list(chain.from_iterable(mapping.values())))}` Base Commands Loaded",color = discord.Color.random())
        for cog, listcommands in mapping.items():
            if cog and await self.filter_commands(cog.get_commands()) and cog.qualified_name != "HelpCommand" and cog.qualified_name != "Jishaku":
                embed.add_field(name = cog.qualified_name,value = cog.short + "\n" + f"`{len(listcommands)} Commands`\n`{sum([len(x.commands) for x in listcommands if isinstance(x,commands.Group) or isinstance(x,commands.HybridGroup)])} Subcommands`")
        embed.set_footer(text = "Use /help <category> to see the commands in the category.")
        await message.reply(embed = embed)
        
    async def send_cog_help(self, cog):
        message = self.get_destination()
        all_commands = []
        for command in cog.walk_commands():
            all_commands.append(command)
        if len(all_commands) <= 0:
            return await self.send_error_message(self.command_not_found(cog.qualified_name))
        formatter = HelpPageSource(all_commands, self,cog.qualified_name)
        menu = MyMenuPages(formatter, delete_message_after=True)
        await menu.start(self.context)

    async def send_command_help(self, command):
        message = self.get_destination()
        if command.hidden:
            return await self.send_error_message(self.command_not_found(command.name))
        embed = discord.Embed(title = command.name,description = command.help,color = discord.Color.random())
        embed.add_field(name = "Command Syntax",value = f"`{self.get_command_signature(command)}`",inline = False)
        embed.add_field(name = "Aliases",value = f'`{", ".join(command.aliases)}`' if command.aliases else "`None`",inline = False)
        embed.add_field(name = "Documentation",value = command.brief,inline = False)
        await message.reply(embed = embed)

    async def send_group_help(self, group):
        message = self.get_destination()
        if group.hidden:
            return await self.send_error_message(self.command_not_found(group.name))
        embed = discord.Embed(title = f"Group Command: {group.name}",description = group.help,color = discord.Color.random())
        build = ""
        for command in group.commands:
            build += f"**{command.name}**\n{command.help}\n"
        embed.add_field(name = "Subcommands",value = build)
        embed.set_footer(text = "Use /help <parent command(s)> <subcommand> for more information!")
        await message.reply(embed = embed)

    async def send_error_message(self, error):
        embed = discord.Embed(title="Error", description=error)
        message = self.get_destination()
        await message.reply(embed=embed)

    def get_destination(self):
        return self.context

class MyMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source, *, delete_message_after=False):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None
        self.delete_message_after = delete_message_after

    async def start(self, ctx, *, channel=None, wait=False):
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.message)

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        return value
    
    async def send_initial_message(self, ctx, message):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await ctx.reply(**kwargs)
    
    async def on_timeout(self):
        for child in self.children: 
            child.disabled = True   
        await self.message.edit(view=self) 

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.ctx.author

    @ui.button(emoji='<:doubleleft:930948763885899797>', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction,button):
        await self.show_page(0)
        await interaction.response.defer()

    @ui.button(emoji='<:arrowleft:930948708458172427>', style=discord.ButtonStyle.blurple)
    async def before_page(self, interaction,button):
        await self.show_checked_page(self.current_page - 1)
        await interaction.response.defer()

    @ui.button(emoji='<:arrowright:930948684718432256>', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction,button):
        await self.show_checked_page(self.current_page + 1)
        await interaction.response.defer()

    @ui.button(emoji='<:doubleright:930948740557193256>', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction, button):
        await self.show_page(self._source.get_max_pages() - 1)
        await interaction.response.defer()
    
    @ui.button(label='End Interaction', style=discord.ButtonStyle.blurple)
    async def stop_page(self, interaction, button):
        await interaction.response.defer()
        self.stop()
        for child in self.children: 
            child.disabled = True   
        await self.message.edit(view=self) 

class HelpPageSource(menus.ListPageSource):
    def __init__(self, data, helpcommand,cogname):
        super().__init__(data, per_page=6)
        self.helpcommand = helpcommand
        self.cogname = cogname

    def format_command_help(self, no, command):
        if command.hidden == True:
            return ""
        name = command.qualified_name
        docs = self.helpcommand.get_command_brief(command)
        return f"**{no}. {name}**\n{docs}"
    
    async def format_page(self, menu, entries):
        page = menu.current_page
        max_page = self.get_max_pages()
        starting_number = page * self.per_page + 1
        for entry in entries:
            if entry.hidden == True:
                entries.remove(entry)
        iterator = starmap(self.format_command_help, enumerate(entries, start=starting_number))
        page_content = "\n".join(iterator)
        embed = discord.Embed(
            title=f"{self.cogname} Commands [{page + 1}/{max_page}]", 
            description=page_content,
            color=0xffcccb
        )
        embed.set_footer(text=f"Use /help <command> for more information on each command.")  # author.avatar in 2.0
        return embed


class HelpCommand(commands.Cog):
    def __init__(self,client):
        self.client = client
        self.short = "placeholder"
        self.help_command = MyHelp()
        self.help_command.cog = self # Instance of YourCog class
        client.help_command = self.help_command
    
    @app_commands.command(description = "A helpful command to get started!")
    @app_commands.describe(search = "Your search query, either a command name or category name!")
    async def help(self, interaction: discord.Interaction, search: Optional[str]):
        ctx = await self.client.get_context(interaction, cls=commands.Context)
        if search is not None:
            result = await ctx.send_help(search)
            if not interaction.response.is_done():
                embed = discord.Embed(title="Error", description= f"No command called \"{search}\" found.")
                await interaction.response.send_message(embed = embed)
        else:
            await ctx.send_help()

    @help.autocomplete("search")
    async def command_autocomplete(self, interaction: discord.Interaction, needle: str) -> List[app_commands.Choice[str]]:
        assert self.client.help_command
        ctx = await self.client.get_context(interaction, cls=commands.Context)
        help_command = self.client.help_command.copy()
        help_command.context = ctx
        if not needle:
            return [
                app_commands.Choice(name=cog_name, value=cog_name)
                for cog_name, cog in self.client.cogs.items()
                if cog_name != "helpcommand" and cog_name != "jishaku" and await help_command.filter_commands(cog.get_commands())
            ][:25]
        needle = needle.lower()
        return [
            app_commands.Choice(name=command.qualified_name, value=command.qualified_name)
            for command in await help_command.filter_commands(self.client.walk_commands(), sort=True)
            if needle in command.qualified_name
        ][:25]
    
async def setup(client):
    await client.add_cog(HelpCommand(client))