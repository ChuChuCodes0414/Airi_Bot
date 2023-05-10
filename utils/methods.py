import datetime
import discord

def query(data,search = None):
    if search and data:
        element = search[0]
        if element:
            value = data.get(element)
            return value if len(search) == 1 else query(value, search = search[1:])

def timeparse(duration,maxdays = None,maxseconds = None):
    success = True
    c = ""
    hours = 0
    seconds = 0
    for letter in duration:
        if letter.isalpha():
            letter = letter.lower()
            try: c = int(c) 
            except: 
                success = False  
                break
            if letter == 'w': hours += c*168 
            elif letter == 'd': hours += c*24
            elif letter == 'h': hours += c
            elif letter == 'm': seconds += c*60
            elif letter == 's': seconds += c
            else: 
                success = False
                break
            c = ""
        else:
            c += letter
    if c != "" or not success:
        return 'I could not parse your timing input!\n\nValid Time Inputs:\n`w` - weeks\n`d` - days\n`h` - hours\n`m` - minutes\n`s` - seconds\n\nExamples: `2w`, `2h30m`, `10s`'
    added = datetime.timedelta(hours = hours,seconds = seconds)
    if maxdays or maxseconds:
        max = datetime.timedelta(days = maxdays,seconds= maxseconds)
        if added > max:
            return f"Your time duration goes over the maximum time, which is `{maxdays}` days and `{maxseconds}` seconds!"
    return added