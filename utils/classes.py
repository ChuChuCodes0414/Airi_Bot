import discord
from discord.ext import menus
from discord import ui

class ConfirmationView(discord.ui.View):
    def __init__(self,ctx):
        super().__init__(timeout = 60)
        self.ctx = ctx
        self.value = None
        self.message = None

    async def on_timeout(self):
        for child in self.children: 
            child.disabled = True   
        await self.message.edit(view=self) 
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

    @discord.ui.button(emoji = "✅",style = discord.ButtonStyle.green)
    async def confirm(self,interaction:discord.Interaction,button:discord.ui.Button):
        await interaction.response.defer()
        self.value = True
        self.stop()
    
    @discord.ui.button(emoji = "✖",style = discord.ButtonStyle.red)
    async def deny(self,interaction:discord.Interaction,button:discord.ui.Button):
        await interaction.response.defer()
        self.value = False
        self.stop()

class MenuPages(ui.View, menus.MenuPages):
    def __init__(self, source,*,timeout = 60,delete_message_after = False):
        super().__init__(timeout = timeout)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None
        self.delete_message_after = delete_message_after
    
    async def start(self,ctx):
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx)

    async def _get_kwargs_from_page(self,page):
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view':self})
        return value

    async def send_initial_message(self,ctx):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await ctx.reply(**kwargs)
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author

    @ui.button(emoji='<:doubleleft:930948763885899797>', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction,button):
        await self.show_page(0)
        await interaction.response.defer()

    @ui.button(emoji='<:arrowleft:930948708458172427>', style=discord.ButtonStyle.blurple)
    async def before_page(self, interaction, button):
        await self.show_checked_page(self.current_page - 1)
        await interaction.response.defer()

    @ui.button(emoji='<:arrowright:930948684718432256>', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction, button):
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