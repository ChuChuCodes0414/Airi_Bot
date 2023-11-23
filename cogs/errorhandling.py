import discord
from discord.ext import commands
from utils import errors
import math
import traceback
import sys
import genshin
import uuid
import datetime
import os
import enkanetwork

class ErrorHandling(commands.Cog):
    def __init__(self,client):
        self.hidden = True
        self.client = client
    
    async def send_error_embed(self,ctx,message):
        embed = discord.Embed(description = message,color = discord.Color.red())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        try:
            await ctx.reply(embed= embed,ephemeral = True)
        except:
            try:
                await ctx.send(embed= embed)
            except:
                pass
    
    async def send_ierror_embed(self,interaction,message):
        embed = discord.Embed(description = message,color = discord.Color.red())
        try:
            await interaction.response.send_message(embed= embed,ephemeral = True)
        except:
            pass

    def get_command_signature(self, command,context):
        parent = command.parent
        entries = []
        while parent is not None:
            if not parent.signature or parent.invoke_without_command:
                entries.append(parent.name)
            else:
                entries.append(parent.name + ' ' + parent.signature)
            parent = parent.parent
        parent_sig = ' '.join(reversed(entries))

        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = f'[{command.name}|{aliases}]'
            if parent_sig:
                fmt = parent_sig + ' ' + fmt
            alias = fmt
        else:
            alias = command.name if not parent_sig else parent_sig + ' ' + command.name

        return f'{context.clean_prefix}{alias} {command.signature}'
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Error Handler Ready.")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
        
        error = getattr(error, 'original', error)
        
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, discord.app_commands.CommandInvokeError):
            error = error.original
        
        if isinstance(error, errors.BlacklistedError):
            await self.send_error_embed(ctx,f"⚠ You are currently bot blacklisted!\n\n**Blacklisted Until:** <t:{error.until}:f> (<t:{error.until}:R>)\n**Blacklist Reason:** {error.reason}\n\nPlease refrain from sending commands, as this will lead to an increase in your blacklist time!")
            return
        
        if isinstance(error,errors.UnblacklistedMessage):
            await self.send_error_embed(ctx,error.message)
            channel = self.client.get_channel(978029124243292210)
            embed = discord.Embed(title = "User Unblacklisted!",description = f"**Blacklisted:** {ctx.author.mention} | {ctx.author} (`{ctx.author.id}`)**Unblacklist Reason:** Blacklist length was completed.",color = discord.Color.green())
            await channel.send(embed = embed)
            return

        if isinstance(error, commands.DisabledCommand):
            await self.send_error_embed(ctx,"Seems like this command was disabled. This is most likely due to a bug in the command, which will be fixed soon.\n"+
                "If you have any questions, feel free to join the [support server](https://discord.com/invite/9pmGDc8pqQ) to ask!")
            return
        
        if isinstance(error, commands.MissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = '{}, and {}'.format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = ' and '.join(missing)
            message = 'You need the **{}** permission(s) to use this command.'.format(fmt)
            await self.send_error_embed(ctx,message)
            return

        
        if isinstance(error, errors.SetupCheckFailure):
            message = f"A custom command check failed.\nContext: {error.message}"
            await self.send_error_embed(ctx,message)
            return
        
        if isinstance(error,commands.CheckFailure):
            await self.send_error_embed(ctx,"A custom rules check failed.\nServer managers can check rules with </rules view:1108481999225753623>.")
            return
        
        if isinstance(error, commands.MaxConcurrencyReached):
            message = f"**Max Concurrency Reached!**\nThis command can be used `{error.number}` time(s) per `{error.per.name}` concurrently."
            await self.send_error_embed(ctx,message)
            return
        
        if isinstance(error, commands.RangeError):
            message = f"__**⚠ User Range Input Error!**__\nNumerical input has a minimum of `{error.minimum}` and a maxiumum of `{error.maximum}`."
            await self.send_error_embed(ctx,message)
            return

        if isinstance(error, commands.UserInputError):
            message = f"__**⚠ User Input Error!**__\n**Command Usage:** {self.get_command_signature(ctx.command,ctx)}"
            await self.send_error_embed(ctx,message)
            return
        
        if isinstance(error, errors.NotEnabledError):
            message = error.message
            await self.send_error_embed(ctx,message)
            return

        if isinstance(error, errors.NotSetupError):
            message = error.message
            await self.send_error_embed(ctx,message)
            return
    
        if isinstance(error, errors.PreRequisiteError):
            message = error.message
            await self.send_error_embed(ctx,message)
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await self.send_error_embed(ctx,"This command is on cooldown, please retry in `{}` seconds.".format(math.ceil(error.retry_after)))
            return

        if isinstance(error, errors.ParsingError):
            message = error.message
            await self.send_error_embed(ctx,message)
            return
        
        if isinstance(error, errors.AccessError):
            message = error.message
            await self.send_error_embed(ctx,message)
            return
        
        if isinstance(error,discord.Forbidden):
            await self.send_error_embed(ctx,"Looks like I am missing permissions to complete your command.")
            return
        
        if isinstance(error,genshin.errors.DataNotPublic):
            await self.send_error_embed(ctx,"This user's profile is not set to public!")
            return
            
        if isinstance(error,genshin.errors.RedemptionClaimed):
            await self.send_error_embed(ctx,"This code is already redeemed for this account!")
            return
        
        if isinstance(error,genshin.errors.RedemptionInvalid):
            await self.send_error_embed(ctx,"That does not seem like a valid redeem code!")
            return
        
        if isinstance(error,genshin.errors.InvalidCookies):
            await self.send_error_embed(ctx,"Cookies are invalid!\nNote if you are redeeming a code, you can try refreshing your cookie token with `/refresh`.")
            return

        if isinstance(error,genshin.errors.AuthkeyTimeout):
            await self.send_error_embed(ctx,"This user's authkey has timed out!\nIf you are this user, you can regenerate your authkey and reenter it with `[prefix]hoyolab setup`.")
            return
        
        if isinstance(error,genshin.errors.AlreadyClaimed):
            await self.send_error_embed(ctx,"The daily reward for this user has already been claimed!")
            return
        
        if isinstance(error,errors.GeetestError):
            await self.send_error_embed(ctx,"A Geetest captcha was raised that could not be solved!")
            return
        
        if isinstance(error,genshin.errors.GenshinException):
            await self.send_error_embed(ctx,error.msg)
            return

        if isinstance(error,enkanetwork.exception.VaildateUIDError):
            await self.send_error_embed(ctx,"Please check your UID input again!")
            return
        
        if isinstance(error,enkanetwork.exception.EnkaPlayerNotFound):
            await self.send_error_embed(ctx,"Player uid profile could not be found.")
            return
        
        if isinstance(error,enkanetwork.exception.BuildNotPublicData):
            await self.send_error_embed(ctx,"This player's builds are set to private.")
            return
        
        if isinstance(error,enkanetwork.exception.EnkaServerError):
            await self.send_error_embed(ctx,"The Enka server has faced an issue. Please try again later.")
            return
        
        if isinstance(error,enkanetwork.exception.EnkaServerMaintanance):
            await self.send_error_embed(ctx,"Enka servers are under maintenance.")
            return
        
        if isinstance(error,enkanetwork.exception.EnkaServerRateLimit):
            await self.send_error_embed(ctx,"The bot is hitting a rate limit at the moment! Please try again later.")
            return
        
        if isinstance(error,AttributeError) and ctx.command.name == "enka":
            await self.send_error_embed(ctx,"The enka library has not been updated for a character in this user's showcase, and thus it will not work, and the dev is too lazy to fix it sorry.")
            return

        if isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_perms]
            if len(missing) > 2:
                fmt = '{}, and {}'.format("**, **".join(missing[:-1]), missing[-1])
            else:
                fmt = ' and '.join(missing)
            _message = 'I need the **{}** permission(s) to run this command.'.format(fmt)
            await self.send_error_embed(ctx,_message)
            return

        errorid = uuid.uuid4()
        embed = discord.Embed(title = "Uh oh! Seems like you got an uncaught excpetion.",description = "I have no idea how you got here, but it seems your error was not traced! If this occurs frequently, please feel free to join the [support server](https://discord.com/invite/9pmGDc8pqQ) and report the bug!",color = discord.Color.red())
        if ctx.command.cog_name and ctx.command.cog_name.lower() == "hoyoverse":
            embed.add_field(name = "Error Details:",value = "```I am not able to display error details for Hoyoverse commands. The bot developer has been notified to this issue.```")
        else:
            if len(''.join(traceback.format_exception_only(type(error), error))) < 4000:
                embed.add_field(name = "Error Details:",value = f"```{''.join(traceback.format_exception_only(type(error), error))}```")
            else:
                embed.add_field(name = "Error Details:",value = f"```Error details are too long to display! Join the support server with your error code for more details.```")
        embed.add_field(name = "Error ID",value = errorid,inline = False)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        try:
            await ctx.reply(embed = embed)
        except:
            try:
                await ctx.send(embed = embed)
            except:
                pass

        if self.client.user.id == 918619396581236806:
            channel = self.client.get_channel(975508813929119764)
        else:
            channel = self.client.get_channel(908467248719605763)
        
        embed = discord.Embed(title = f'⚠ There was an error that was not traced!',description = f'On Command: {ctx.command.name}',color = discord.Color.red())
        embed.add_field(name = "Command Invoke Details",value = f'**Guild Info:** {ctx.guild.name} ({ctx.guild.id})\n**User Information:** {ctx.author.name} | {ctx.author.mention} ({ctx.author.id})\n**Jump URL:** {ctx.message.jump_url}\n**Command Used:** {ctx.message.content}\n**Error ID:** {errorid}',inline = False)
        errordetails = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        if len(errordetails) < 1000:
            embed.add_field(name = "Command Error Log",value = f'```{errordetails}```')
            embed.set_footer(text = f'{ctx.guild.name}',icon_url = ctx.guild.icon)
            embed.timestamp = datetime.datetime.now()
            await channel.send("<@570013288977530880>",embed = embed)
        else:
            f =  open(f'errorlogging\{errorid}.txt', 'w')
            f.write(errordetails)
            embed.set_footer(text = f'{ctx.guild.name}',icon_url = ctx.guild.icon)
            embed.timestamp = datetime.datetime.now()
            f.close()
            await channel.send("<@570013288977530880>",embed = embed,file = discord.File("errorlogging\\" + str(errorid) + ".txt"))
            os.remove(f"errorlogging\{errorid}.txt")

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

@commands.Cog.listener()
async def on_error(self, interaction, error):
    error = getattr(error, 'original', error)
    
    if isinstance(error, discord.app_commands.CommandInvokeError):
        error = error.original

    if isinstance(error, discord.app_commands.MissingPermissions):
        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
        if len(missing) > 2:
            fmt = '{}, and {}'.format("**, **".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        message = 'You need the **{}** permission(s) to use this command.'.format(fmt)
        await self.send_ierror_embed(interaction,message)
        return
    
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await self.send_ierror_embed(interaction,"This command is on cooldown, please retry in `{}` seconds.".format(math.ceil(error.retry_after)))
        return
    
    if isinstance(error,discord.Forbidden):
        await self.send_ierror_embed(interaction,"Looks like I am missing permissions to complete your command.")
        return
    
    if isinstance(error, discord.app_commands.BotMissingPermissions):
        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_perms]
        if len(missing) > 2:
            fmt = '{}, and {}'.format("**, **".join(missing[:-1]), missing[-1])
        else:
            fmt = ' and '.join(missing)
        _message = 'I need the **{}** permission(s) to run this command.'.format(fmt)
        await self.send_ierror_embed(interaction,_message)
        return

    errorid = uuid.uuid4()
    embed = discord.Embed(title = "Uh oh! Seems like you got an uncaught excpetion.",description = "I have no idea how you got here, but it seems your error was not traced! If this occurs frequently, please feel free to join the [support server](https://discord.com/invite/9pmGDc8pqQ) and report the bug!",color = discord.Color.red())
    
    if len(''.join(traceback.format_exception_only(type(error), error))) < 4000:
        embed.add_field(name = "Error Details:",value = f"```{''.join(traceback.format_exception_only(type(error), error))}```")
    else:
        embed.add_field(name = "Error Details:",value = f"```Error details are too long to display! Join the support server with your error code for more details.```")
    
    embed.add_field(name = "Error ID",value = errorid,inline = False)
    embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
    
    try:
        await interaction.response.send_message(embed = embed)
    except:
        try:
            await interaction.followup.send(embed = embed)
        except:
            pass

    channel = self.client.get_channel(1088681647525855252)
    
    embed = discord.Embed(title = f'⚠ There was an error that was not traced!',description = f'On Command: {interaction.command.name}',color = discord.Color.red())
    embed.add_field(name = "Command Invoke Details",value = f'**Guild Info:** {interaction.guild.name} ({interaction.guild.id})\n**User Information:** {interaction.user.name} | {interaction.user.mention} ({interaction.user.id})\n**Error ID:** {errorid}',inline = False)
    errordetails = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
    if len(errordetails) < 1000:
        embed.add_field(name = "Command Error Log",value = f'```{errordetails}```')
        embed.set_footer(text = f'{interaction.guild.name}',icon_url = interaction.guild.icon)
        embed.timestamp = datetime.datetime.now()
        await channel.send(embed = embed)
    else:
        f =  open(f'errorlogging\{errorid}.txt', 'w')
        f.write(errordetails)
        embed.set_footer(text = f'{interaction.guild.name}',icon_url = interaction.guild.icon)
        embed.timestamp = datetime.datetime.now()
        f.close()
        await channel.send(embed = embed,file = discord.File("errorlogging\\" + str(errorid) + ".txt"))
        os.remove(f"errorlogging\{errorid}.txt")

    print('Ignoring exception in command {}:'.format(interaction.command), file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

async def setup(client):
    await client.add_cog(ErrorHandling(client))
