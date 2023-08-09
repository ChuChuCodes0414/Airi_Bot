import discord
from discord.ext import commands, menus
from discord import ui, app_commands
from utils import methods, errors, classes
import asyncio

class PrivateChannels(commands.Cog):
    """
        Manage private channels in your server by adding and removing members!
    """
    def __init__(self,client):
        self.client = client
        self.short = "🔐 | Private Channels"
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('Private Channels Category Loaded.')
    
    @commands.hybrid_group(extras = {"id": "90"},aliases = ['pc'],help = "The command group to manage private channels.")
    async def privatechannels(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `privatechannels` to get a list of commands.")
    
    @privatechannels.command(extras = {"id": "91"},aliases = ['ac'],help = "Add a member to the current channel.")
    @app_commands.describe(member = "The member to add to the channel.")
    @commands.has_permissions(manage_channels= True)
    async def add(self,ctx, member:discord.Member):
        if member.bot:
            raise errors.ParsingError(message = "You cannot add a bot to this channel. Please find a normal user to add instead.")

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"privatechannels.{ctx.channel.id}":1})
        data = methods.query(data = raw,search = ["privatechannels",str(ctx.channel.id)])

        if not data:
            raise errors.PreRequisiteError(message = "There is not a channel setup here!\nUse </privatechannels set:1103474987416956988> to get started.")
        if member.id in data:
            raise errors.PreRequisiteError(message = f"**{member}** is already added to this channel!\nTo fix overrides for this member, run </privatechannels fix:1103474987416956988>.")
        if len(data) >= int(data[0]) + 1:
            raise errors.PreRequisiteError(message = f"This channel is at its limit of `{data[0]}`!\nUse </privatechannels changelimit:1103474987416956988> to change the member limit.")

        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$addToSet":{f"privatechannels.{ctx.channel.id}":member.id}})
        overwrite = ctx.channel.overwrites_for(member)
        overwrite.read_messages = True
        await ctx.channel.set_permissions(member, overwrite=overwrite)

        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully added **{member}** to {ctx.channel.mention}.",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @privatechannels.command(extras = {"id": "92"},aliases = ['rc'],help = "Remove a member from the current channel.")
    @commands.has_permissions(manage_channels = True)
    @app_commands.describe(user = "The member to remove from the channel.")
    async def remove(self,ctx,user:discord.User):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"privatechannels.{ctx.channel.id}":1})
        data = methods.query(data = raw,search = ["privatechannels",str(ctx.channel.id)])

        if not data:
            raise errors.PreRequisiteError(message = "There is not a channel setup here!\nUse </privatechannels set:1103474987416956988> to get started.")
        if user.id not in data:
            raise errors.PreRequisiteError(message = f"**{user}** is not in this channel!")
        if user.id == data[1]:
            raise errors.PreRequisiteError(message = "You cannot remove the owner from the channel!")
        
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$pull":{f"privatechannels.{ctx.channel.id}":user.id}})

        try:
            member = await commands.converter.MemberConverter().convert(ctx,str(user.id))
        except:
            embed = discord.Embed(description = f"**{user}** is no longer in the server! I have removed them from the channel.",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            return await ctx.reply(embed = embed)
        
        await ctx.channel.set_permissions(member, overwrite=None)
        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully removed override for **{member}** from {ctx.channel.mention}.",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @privatechannels.command(extras = {"id": "94"},aliases = ['abused'],help = "Fix overrides for a member in private channels.")
    @commands.has_permissions(administrator= True)
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to fix channels for.")
    async def fix(self,ctx,member:discord.Member):
        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"privatechannels":1})
        data = methods.query(data = raw,search = ["privatechannels"])
        build = "**Added to:**\n"
        ownerbuild = "**Was set the owner of:**\n"
        error = "**Could not add to:**"

        async with ctx.typing():
            for channel in data:
                if member.id in data[channel]:
                    channel_object = ctx.guild.get_channel(int(channel))
                    if channel_object:
                        if channel_object.overwrites_for(member).is_empty():
                            if data[channel][1] == int(member.id):
                                overwrite = channel_object.overwrites_for(member)
                                overwrite.manage_channels = True
                                overwrite.read_messages = True
                                overwrite.manage_messages = True
                                await channel_object.set_permissions(member, overwrite=overwrite)
                                embed = discord.Embed(description = f"**{member}** was set as the owner of this channel. Believe this was a mistake? Contact an Admin.",color = discord.Color.random())
                                embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
                                await channel_object.send(embed = embed)
                                ownerbuild += f"<#{channel}>\n"
                            else:
                                overwrite = channel_object.overwrites_for(member)
                                overwrite.read_messages = True
                                await channel_object.set_permissions(member, overwrite=overwrite)
                                embed = discord.Embed(description = f"**{member}** was added to this channel. Believe this was a mistake? Use `[prefix]rc <user>` to remove them!",color = discord.Color.random())
                                embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
                                await channel_object.send(embed = embed)
                                build += f"<#{channel}>\n"
                    else:
                        error += f"\n{channel}"
                    await asyncio.sleep(0.5)
        
        embed = discord.Embed(title = f"Private Channels that were Fixed for {member.name}",description = ownerbuild + build + error,color = discord.Color.random())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @privatechannels.command(extras = {"id": "95"},aliases = ['ci'],description = "Show member information for the current or specified channel.")
    @app_commands.describe(channel = "The channel to see information for.")
    async def info(self,ctx,channel:discord.TextChannel = None):
        channel = channel or ctx.channel

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"privatechannels.{channel.id}":1})
        data = methods.query(data = raw,search = ["privatechannels",str(ctx.channel.id)])

        if not data:
            raise errors.PreRequisiteError(message = f"There is not a channel setup in {channel.mention}!\nUse </privatechannels set:1103474987416956988> to get started.")

        limit,owner,members = data[0],data[1],data[1:]

        buildmembers = '<@'+str(members[0])+'>'
        if len(members) >= 2:
            for member in members[1:]:
                buildmembers+= (', <@'+str(member)+'>')
        
        embed=discord.Embed(title="Channel Info",description=f"Channel info for {channel.mention}", color=discord.Color.random())
        embed.set_thumbnail(url=ctx.guild.icon)
        embed.add_field(name="Channel Owner:",value=f'<@{owner}>',inline=True)
        embed.add_field(name="Channel Limit:",value=f'{len(members)}/{limit}',inline=True)
        embed.add_field(name="Members:",value=buildmembers,inline=False)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed=embed)
    
    @privatechannels.command(extras = {"id": "96"},aliases = ["cl"],help = "Change the member limit of the current or specified channel.")
    @commands.has_permissions(administrator = True)
    @app_commands.describe(limit = "The amount of members allowed to be in the channel.",channel = "The channel to change the limit for.")
    async def changelimit(self,ctx,limit:commands.Range[int,0],channel:discord.TextChannel = None):
        channel = channel or ctx.channel

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"privatechannels.{channel.id}":1})
        data = methods.query(data = raw,search = ["privatechannels",str(ctx.channel.id)])

        if not data:
            raise errors.PreRequisiteError(message = f"There is not a channel setup in {channel.mention}!\nUse </privatechannels set:1103474987416956988> to get started.")

        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"privatechannels.{channel.id}.0":limit}})
        embed = discord.Embed(description = f'<a:PB_greentick:865758752379240448> Successfully changed limit of {channel.mention} to {limit}.',color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @privatechannels.command(extras = {"id": "97"},aliases = ["co"],help = "Change the current or specified channel's owner.")
    @commands.has_permissions(administrator = True)
    @app_commands.describe(owner = "The new owner of the channel.",channel = "The channel to change the owner for.")
    async def changeowner(self,ctx,owner:discord.Member,channel:discord.TextChannel = None):
        channel = channel or ctx.channel

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"privatechannels.{channel.id}":1})
        data = methods.query(data = raw,search = ["privatechannels",str(ctx.channel.id)])

        if not data:
            raise errors.PreRequisiteError(message = f"There is not a channel setup in {channel.mention}!\nUse </privatechannels set:1103474987416956988> to get started.")
        if data[1] == owner.id:
            raise errors.PreRequisiteError(message = f"**{owner}** is already the owner of this channel!")


        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$pull":{f"privatechannels.{channel.id}":owner.id}})
        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"privatechannels.{channel.id}.1":owner.id}})

        oldowner = data[1]
        oldowner = ctx.guild.get_member(int(oldowner))
        if oldowner:
            await channel.set_permissions(oldowner, overwrite=None)
        overwrite = channel.overwrites_for(owner)
        overwrite.manage_channels = True
        overwrite.read_messages = True
        overwrite.manage_messages = True
        await channel.set_permissions(owner, overwrite=overwrite)
        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully set {channel.mention} as a private channel with {owner.mention} as the owner. The previous owner has been removed.",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @privatechannels.command(extras = {"id": "98"},aliases = ["sc"],help = "Setup a channel with an owner and limit.")
    @commands.has_permissions(administrator = True)
    @app_commands.describe(owner = "The owner of the channel.",channel = "The channel to setup.",limit = "The amoutn of members allowed to be in the channel.")
    async def set(self,ctx,owner:discord.Member,channel:discord.TextChannel = None,limit:commands.Range[int,0] = None):
        channel = channel or ctx.channel
        limit = limit or 5

        raw = self.client.db.guild_data.find_one({"_id":ctx.guild.id},{f"privatechannels.{channel.id}":1})
        data = methods.query(data = raw,search = ["privatechannels",str(ctx.channel.id)])

        if data:
            raise errors.PreRequisiteError(message = f"{channel.mention} is already setup! Use </privatechannels info:1103474987416956988> for more information.")

        self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$set":{f"privatechannels.{channel.id}":[limit,owner.id]}})
        overwrite = channel.overwrites_for(owner)
        overwrite.manage_channels = True
        overwrite.read_messages = True
        overwrite.manage_messages = True
        await channel.set_permissions(owner, overwrite=overwrite)
        embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully set {channel.mention} as a private channel with **{owner}** as the owner. The channel has a limit of `{limit}` people",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @privatechannels.command(extras = {"id": "99"}, help = "Remove all private channel data, does not remove overrides.")
    @commands.has_permissions(administrator = True)
    @app_commands.describe(channel = "The channel to delete information for.")
    async def delete(self,ctx,channel:discord.TextChannel = None):
        channel = channel or ctx.channel

        res = self.client.db.guild_data.update_one({"_id":ctx.guild.id},{"$unset":{f"privatechannels.{channel.id}":""}})

        if res.modified_count == 1:
            embed = discord.Embed(description = f"<a:PB_greentick:865758752379240448> Successfully removed all data for {channel.mention}",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await ctx.reply(embed = embed)
        else:
            raise errors.PreRequisiteError(message = f"{channel.mention} is not setup as a private channel!")

async def setup(client):
    await client.add_cog(PrivateChannels(client))
  