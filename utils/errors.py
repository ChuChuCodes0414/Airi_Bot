import discord
from discord.ext import commands

class SetupCheckFailure(commands.CheckFailure):
    def __init__(self,message = "A check on this command has failed!\nIf you are a server manager, try configuring with `/settings`."):
        super().__init__(message)
        self.message = message

class NotEnabledError(commands.CommandError):
    def __init__(self,message = "This feature is not enabled!\nIf you are a server manager, try configuring with `/settings`."):
        super().__init__(message)
        self.message = message

class NotSetupError(commands.CommandError):
    def __init__(self,message = "A setting required for this command is not setup!\nIf you are a server manager, try configuring with `/settings`."):
        super().__init__(message)
        self.message = message

class NoDataError(commands.CommandError):
    def __init__(self,message = "There is no data pertaining to what you are searching for!"):
        super().__init__(message)
        self.message = message

class ParsingError(commands.CommandError):
    def __init__(self,message = "I could not parse your input!"):
        super().__init__(message)
        self.message = message

class GeetestError(commands.CommandError):
    def __init__(self):
        super().__init__("There was an error solving the Geetest Captcha!")
        self.message = "There was an error solving the Geetest Captcha!"

class BlacklistedError(commands.CommandError):
    def __init__(self,until,reason):
        super().__init__(message = "You are currently blacklisted from the bot!")
        self.until = until
        self.reason = reason

class UnblacklistedMessage(commands.CommandError):
    def __init__(self):
        super().__init__(message = "Your blacklist period is now up! You have been automatically unblacklisted, please be more mindful of bot rules in the future.")
        self.message = "Your blacklist period is now up! You have been automatically unblacklisted, please be more mindful of bot rules in the future."

class PreRequisiteError(commands.CommandError):
    def __init__(self,message = "A pre-requisite for this command is not met!"):
        super().__init__(message)
        self.message = "**Pre-requisite not met**\n" + message

class AccessError(commands.CommandError):
    def __init__(self,message = "You cannot access this data!"):
        super().__init__(message)
        self.message = message