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

class PreRequisiteError(commands.CommandError):
    def __init__(self,message = "A pre-requisite for this command is not met!"):
        super().__init__(message)
        self.message = "**Pre-requisite not met**\n" + message

class AccessError(commands.CommandError):
    def __init__(self,message = "You cannot access this data!"):
        super().__init__(message)
        self.message = message