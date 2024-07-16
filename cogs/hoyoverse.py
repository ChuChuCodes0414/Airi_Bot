import discord
from discord.ext import commands, menus, tasks
from discord import app_commands, ui
from utils import methods, errors,classes,hoyoversestore
import datetime
import genshin
import os
from PIL import Image, ImageFont, ImageDraw
from urllib.request import urlopen
import rsa
import binascii
import textwrap
from pillow import pillow
import asyncio
from io import BytesIO
from itertools import starmap
from typing import Literal
from aioenkanetworkcard import encbanner
import aiohttp
import json
import urllib
from twocaptcha import TwoCaptcha

class Hoyoverse(commands.Cog):
    def __init__(self,client):
        self.client = client
        self.short = "<:hoyo:981372000507412480> | Hoyoverse"
        self.standardclient = genshin.Client()
        self.standardclient.set_cookies(ltuid=os.getenv("LTUID"),ltoken=os.getenv("LTTOKEN"))
        self.solver = TwoCaptcha(os.getenv("captcha_key"))

        with open(os.getenv("privatepath"),"r") as file:
            data = file.read()
            self.private = rsa.PrivateKey.load_pkcs1(data.encode('utf8')) 

        with open(os.getenv("publicpath"),"r") as file:
            data = file.read()
            self.public = rsa.PublicKey.load_pkcs1(data.encode('utf8')) 
        
        self.months = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
        self.character_mapping = {}
        self.weapon_mapping = {}
        self.artifact_mapping = {}
        self.talent_mapping = {}
        self.captcha_tracking = {}
        self.claim_daily.start()
        self.post_captcha.start()

        self.route = "https://api-os-takumi.mihoyo.com/common/gacha_record/api/getGachaLog"


    @commands.Cog.listener()
    async def on_ready(self):
        print('Hoyoverse Category Loaded.')
    
    @tasks.loop(minutes = 5)
    async def post_captcha(self):
        if len(self.captcha_tracking) > 0:
            res = ""
            for person in self.captcha_tracking:
                res += f"{person} solved `{self.captcha_tracking[person]}` captchas"
            channel = self.client.get_channel(1116058421146439690)
            embed = discord.Embed(title = "Captcha Used in Past 5 minutes",description = res,color = discord.Color.random())
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            await channel.send(embed = embed)
            self.captcha_tracking = {}

    async def claim_genshin_daily(self,gclient,id):
        try:
            await gclient.claim_daily_reward(game = genshin.Game.GENSHIN)
            return True, False
        except genshin.DailyGeetestTriggered as e:
            print(f"Geetest triggered for Genshin: {id}")
            try:
                result = await asyncio.gather(asyncio.to_thread(self.blocking_io,e.gt,e.challenge),asyncio.sleep(3))
                data = json.loads(result[0]['code'])
                challenge = {"challenge":data["geetest_challenge"],"validate":data["geetest_validate"],"seccode":data["geetest_seccode"]}
                await gclient.claim_daily_reward(game = genshin.Game.GENSHIN,challenge = challenge)
                return True, True
            except Exception as e:
                print(f"Failed to solve Geetest triggered for Genshin: {id}: {e}")
                return False, "- A Geetest Captcha was triggered while trying to claim your Genshin daily rewards, and the bot could not solve it! Please claim your rewards manually through the [HoYoLab Website](https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481)\n"
        except genshin.InvalidCookies as e:
            print(f"Invalid cookies triggered for Genshin: {id}")
            self.client.db.user_data.update_one({"_id":int(id)},{"$unset":{"hoyoverse.settings.autoclaim":""}})
            return False, "- Your cookies are invalid, and thus your Genshin daily rewards could not be claimed. Please refresh your data through </hoyolab link:999438437906124835>, and re-enable auto claim.\n"
        except Exception as e:
            print(f"Error for {id}: {e}")
            return False, "- A error occured while claiming your Genshin daily rewards. You can try claiming manually through </genshin daily claim:999438437906124836> or through the [HoYoLab Website](https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481).\n"

    @tasks.loop(hours = 24)
    async def claim_daily(self):
        print("Claiming hoyoverse dailies...")
        accounts = self.client.db.user_data.find({"$or":[{"hoyoverse.settings.autoclaim":True},{"hoyoverse.settings.hautoclaim":True},{"hoyoverse.settings.hsautoclaim":True}]},{"hoyoverse":1})
        success,error,hsuccess,herror,hssuccess,hserror,zzzsuccess,zzzerror,dmsuccess,dmerror = 0,0,0,0,0,0,0,0,0,0
        captchas,captchaf = 0,0
        for account in accounts:
            hoyosettings = account.get("hoyoverse",{}).get("settings",{})
            client = None
            if "ltuid2" in hoyosettings and "ltoken2" in hoyosettings and 'ltmid2' in hoyosettings:
                ltuid2,ltoken2,ltmid2 = hoyosettings['ltuid2'], hoyosettings['ltoken2'], hoyosettings['ltmid2']
                ltuid2 = rsa.decrypt(binascii.unhexlify(ltuid2),self.private).decode('utf8')
                ltoken2 = rsa.decrypt(binascii.unhexlify(ltoken2),self.private).decode('utf8')
                ltmid2 = rsa.decrypt(binascii.unhexlify(ltmid2),self.private).decode('utf8')
                client = genshin.Client({"ltuid_v2": ltuid2 ,"ltoken_v2": ltoken2,"ltmid_v2":ltmid2})
            elif "ltuid" in hoyosettings and "ltoken" in hoyosettings:
                ltuid,ltoken = hoyosettings['ltuid'], hoyosettings['ltoken']
                ltuid = rsa.decrypt(binascii.unhexlify(ltuid),self.private).decode('utf8')
                ltoken = rsa.decrypt(binascii.unhexlify(ltoken),self.private).decode('utf8')
                client = genshin.Client({'ltuid':ltuid,'ltoken':ltoken})
            if client:
                emessage = ""
                if hoyosettings.get("autoclaim"):
                    if hoyosettings.get("gretry"):
                        status,message = await self.claim_genshin_daily(client,account['_id'])
                        if status:
                            success += 1
                            if message: captchas += 1
                        else:
                            captchaf += 1
                            status,message = await self.claim_genshin_daily(client,account['_id'])
                            if status:
                                success += 1
                                if message: captchas += 1
                            else:
                                captchaf += 1
                                emessage += message
                                error += 1
                    else:
                        status,message = await self.claim_genshin_daily(client,account['_id'])
                        if status:
                            success += 1
                            if message: captchas += 1
                        else:
                            if message.startswith("- A Geetest Captcha"):
                                captchaf += 1
                            emessage += message
                            error += 1
                if hoyosettings.get("hautoclaim"):
                    try:
                        await client.claim_daily_reward(game = genshin.Game.HONKAI)
                        hsuccess += 1
                    except genshin.DailyGeetestTriggered as e:
                        herror += 1
                        print(f"Geetest triggered for Honkai Impact: {account['_id']}")
                        emessage += "- A Geetest Captcha was triggered while trying to claim your Honkai Impact 3rd daily rewards! Please claim your rewards manually through the [HoYoLab Website](https://act.hoyolab.com/bbs/event/signin-bh3/index.html?act_id=e202110291205111)\n"
                    except genshin.InvalidCookies as e:
                        herror += 1
                        print(f"Invalid cookies triggered for Honkai Impact: {account['_id']}")
                        emessage += "- Your cookies are invalid, and thus your Honkai Impact 3rd daily rewards could not be claimed. Please refresh your data through </hoyolab link:999438437906124835>, and re-enable auto claim.\n"
                        self.client.db.user_data.update_one({"_id":int(account['_id'])},{"$unset":{"hoyoverse.settings.hautoclaim":""}})
                    except Exception as e:
                        herror += 1
                        print(f"Error for {account['_id']}: {e}")
                        emessage += "- A error occured while claiming your Honkai Impact daily rewards. You can try claiming manually through </honkaiimpact3rd daily claim:1010989269122297870> or through the [HoYoLab Website](https://act.hoyolab.com/bbs/event/signin-bh3/index.html?act_id=e202110291205111).\n"
                    await asyncio.sleep(10)
                if hoyosettings.get("hsautoclaim"):
                    try:
                        await client.claim_daily_reward(game = genshin.Game.STARRAIL)
                        hssuccess += 1
                    except genshin.DailyGeetestTriggered as e:
                        hserror += 1
                        print(f"Geetest triggered for Honkai Star: {account['_id']}")
                        emessage += "- A Geetest Captcha was triggered while trying to claim your Honkai: Star Rail daily rewards! Please claim your rewards manually through the [HoYoLab Website](https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311)\n"
                    except genshin.InvalidCookies as e:
                        hserror += 1
                        print(f"Invalid cookies triggered for Honkai Star: {account['_id']}")
                        emessage += "- Your cookies are invalid, and thus your Honkai: Star Rail daily rewards could not be claimed. Please refresh your data through </hoyolab link:999438437906124835>, and re-enable auto claim.\n"
                        self.client.db.user_data.update_one({"_id":int(account['_id'])},{"$unset":{"hoyoverse.settings.hsautoclaim":""}})
                    except Exception as e:
                        hserror += 1
                        print(f"Error for {account['_id']}: {e}")
                        emessage += "- A error occured while claiming your Honkai: Star Rail daily rewards. You can try claiming manually through </honkaistarrail daily claim:1101694558842126426> or through the [HoYoLab Website](https://act.hoyolab.com/bbs/event/signin/hkrpg/index.html?act_id=e202303301540311).\n"
                    await asyncio.sleep(10)
                if hoyosettings.get("zzzautoclaim"):
                    try:
                        await client.claim_daily_reward(game = genshin.Game.ZZZ)
                        zzzsuccess += 1
                    except genshin.DailyGeetestTriggered as e:
                        zzzerror += 1
                        print(f"Geetest triggered for Zenless: {account['_id']}")
                        emessage += "- A Geetest Captcha was triggered while trying to claim your Zenless Zone Zero daily rewards! Please claim your rewards manually through the [HoYoLab Website](https://act.hoyolab.com/bbs/event/signin/zzz/e202406031448091.html?act_id=e202406031448091)\n"
                    except genshin.InvalidCookies as e:
                        zzzerror += 1
                        print(f"Invalid cookies triggered for Zenless: {account['_id']}")
                        emessage += "- Your cookies are invalid, and thus your Zenless Zone Zero daily rewards could not be claimed. Please refresh your data through </hoyolab link:999438437906124835>, and re-enable auto claim.\n"
                        self.client.db.user_data.update_one({"_id":int(account['_id'])},{"$unset":{"hoyoverse.settings.zzzautoclaim":""}})
                    except Exception as e:
                        zzzerror += 1
                        print(f"Error for {account['_id']}: {e}")
                        emessage += "- A error occured while claiming your Zenless Zone Zero daily rewards. You can try claiming manually through </honkaistarrail daily claim:1101694558842126426> or through the [HoYoLab Website](https://act.hoyolab.com/bbs/event/signin/zzz/e202406031448091.html?act_id=e202406031448091).\n"
                if len(emessage) > 0:
                    try:
                        user = await self.client.fetch_user(int(account['_id']))
                        dm = user.dm_channel
                        if dm == None:
                            dm = await user.create_dm()
                        embed = discord.Embed(title = "⚠ There was an error with your Hoyoverse daily rewards claim!",description = emessage, color = discord.Color.red())
                        embed.set_footer(icon_url = self.client.user.avatar.url,text="If you have any questions, please join the support server found in the /invite command!")
                        await dm.send(embed = embed)
                        dmsuccess += 1
                    except:
                        dmerror += 1
            else:
                print(f"No client found for {account['_id']}")
        embed = discord.Embed(title = "Hoyoverse Daily Rewards Claimed!",description = "Today's Hoyoverse auto claim stats are as follows.",color = discord.Color.random())
        embed.add_field(name = "<:genshinicon:976949476784750612> Genshin Claims",value = f"Successful Claims: `{success}`\nFailed Claims: `{error}`")
        embed.add_field(name = "<:honkaiimpacticon:1041877640971288617> Honkai Claims",value = f"Successful Claims: `{hsuccess}`\nFailed Claims: `{herror}`")
        embed.add_field(name = "<:honkaistarrailicon:1101673399996121178> Honkai: Star Rail Claims",value = f"Successful Claims: `{hssuccess}`\nFailed Claims: `{hserror}`")
        embed.add_field(name = "<:zenless:1259288287588122644> Zenless Zero Claims",value = f"Successful Claims: `{zzzsuccess}`\nFailed Claims: `{zzzerror}`")
        #embed.add_field(name = "<:geetestcringe:1138946483031379988> Geetest Triggers",value = f"Successful Solves: {captchas}\nFailed Solves: {captchaf}\nTotal Cost: ${(captchas+captchaf)*0.003} USD",inline = False)
        embed.timestamp = datetime.datetime.utcnow()
        channel = self.client.get_channel(int(1002939673120870401))
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        message = await channel.send(embed = embed)
        await message.publish()
        embed = discord.Embed(title = "Hoyoverse Error DMs Send",description = "Stats are as follows.",color = discord.Color.random())
        embed.add_field(name = "Successful DMs",value = dmsuccess)
        embed.add_field(name = "Failed DMs",value = dmerror)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        embed.timestamp = datetime.datetime.utcnow()
        channel = self.client.get_channel(int(1116058421146439690))
        await channel.send(embed = embed)
        print("Hoyoverse dailies claimed!")

    @claim_daily.before_loop
    async def wait_until_7am(self):
        now = datetime.datetime.utcnow()
        next_run = now.replace(hour=16, minute=0, second=5)

        if next_run < now:
            next_run += datetime.timedelta(days=1)
        print("Waiting until 7am to start hoyoverse claims!")
        await discord.utils.sleep_until(next_run)

    def blocking_io(self,gt,challenge):
        return self.solver.geetest(gt = gt,challenge = challenge,url = "https://act.hoyolab.com/")
    
    async def cog_load(self):
        if hoyoversestore.CHARACTER_MAPPING:
            self.character_mapping = hoyoversestore.CHARACTER_MAPPING
        else:
            characters = await self.standardclient.get_calculator_characters()
            for character in characters:
                self.character_mapping[character.name] = character
            hoyoversestore.CHARACTER_MAPPING = self.character_mapping
        if hoyoversestore.WEAPON_MAPPING:
            self.weapon_mapping = hoyoversestore.WEAPON_MAPPING
        else:
            weapons = await self.standardclient.get_calculator_weapons()
            for weapon in weapons:
                self.weapon_mapping[weapon.name] = weapon
            hoyoversestore.WEAPON_MAPPING = self.weapon_mapping
        if hoyoversestore.ARTIFACT_MAPPING:
            self.artifact_mapping = hoyoversestore.ARTIFACT_MAPPING
        else:
            artifacts = await self.standardclient.get_calculator_artifacts()
            for artifact in artifacts:
                self.artifact_mapping[artifact.name + " (⭐" + str(artifact.rarity) + ")"] = artifact
            hoyoversestore.ARTIFACT_MAPPING = self.artifact_mapping
        print("Hoyoverse Mappings Loaded")
    
    async def cog_unload(self):
        self.claim_daily.cancel()
        self.post_captcha.cancel()
    
    def bot_mod_check():
        async def predicate(ctx):
            raw = ctx.cog.client.db.user_data.find_one({"_id":ctx.author.id},{"hoyobotmod":1})
            print(raw)
            botmod = methods.query(data = raw, search = ["hoyobotmod"])
            if botmod:
                return True
            raise errors.SetupCheckFailure(message = "You are not a Hoyoverse bot moderator!")
          
        return commands.check(predicate)

    async def get_cookies(self,ctx,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings":1})
        ltuid2,ltoken2,ltmid2 = methods.query(data = raw, search = ["hoyoverse","settings","ltuid2"]),methods.query(data = raw, search = ["hoyoverse","settings","ltoken2"]),methods.query(data = raw, search = ["hoyoverse","settings","ltmid2"])
        if ltuid2 and ltoken2 and ltmid2:
            ltuid2 = rsa.decrypt(binascii.unhexlify(ltuid2),self.private).decode('utf8')
            ltoken2 = rsa.decrypt(binascii.unhexlify(ltoken2),self.private).decode('utf8')
            ltmid2 = rsa.decrypt(binascii.unhexlify(ltmid2),self.private).decode('utf8')
            return {"ltuid_v2": ltuid2 ,"ltoken_v2": ltoken2,"ltmid_v2": ltmid2}
        ltuid,ltoken = methods.query(data = raw, search = ["hoyoverse","settings","ltuid"]),methods.query(data = raw, search = ["hoyoverse","settings","ltoken"])
        if ltoken and ltuid:
            ltuid = rsa.decrypt(binascii.unhexlify(ltuid),self.private).decode('utf8')
            ltoken = rsa.decrypt(binascii.unhexlify(ltoken),self.private).decode('utf8')
            return {"ltuid": ltuid ,"ltoken": ltoken}
        raise errors.NotSetupError(message = "Cookies for this user are not setup!\nIf you are this user, try </hoyolab link:999438437906124835>.")

    async def get_redeem_cookies(self,ctx,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings":1})
        account_id,cookie_token = methods.query(data = raw, search = ["hoyoverse","settings","ltuid"]),methods.query(data = raw, search = ["hoyoverse","settings","cookietoken"])
        if account_id and cookie_token:
            account_id = rsa.decrypt(binascii.unhexlify(account_id),self.private).decode('utf8')
            cookie_token = rsa.decrypt(binascii.unhexlify(cookie_token),self.private).decode('utf8')
            return {"account_id": account_id ,"cookie_token": cookie_token}
        raise errors.NotSetupError(message = "Cookies for this user are not setup!\nIf you are this user, try </hoyolab link:999438437906124835>.")

    async def get_authkey(self,ctx,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.authkey":1})
        authkey = methods.query(data = raw, search = ["hoyoverse","settings","authkey"])
        if authkey:
            return authkey
        raise errors.NotSetupError(message = "Authkey for this user is not setup!\nIf you are this user, try </genshin authkey:999438437906124836>.")

    async def get_hauthkey(self,ctx,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.hauthkey":1})
        authkey = methods.query(data = raw, search = ["hoyoverse","settings","hauthkey"])
        if authkey:
            return authkey
        raise errors.NotSetupError(message = "Authkey for this user is not setup!\nIf you are this user, try </honkaistarrail authkey:1101694558842126426>.")
    
    async def privacy_check(self,ctx,user):
        if ctx.author == user:
            return True
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.privacy":1})
        return methods.query(data = raw, search = ["hoyoverse","settings","privacy"])

    async def auth_privacy_check(self,ctx,user):
        if ctx.author == user:
            return True
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.aprivacy":1})
        return methods.query(data = raw, search = ["hoyoverse","settings","aprivacy"])

    async def pull_uid(self,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.uid"})
        uid = methods.query(data = raw, search = ["hoyoverse","settings","uid"])
        if not uid:
            raise errors.NotSetupError(message = "The Genshin UID for this user is not setup!\nIf you are this user, try </hoyolab settings:999438437906124835>")
        return uid

    async def pull_huid(self,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.huid"})
        uid = methods.query(data = raw, search = ["hoyoverse","settings","huid"])
        if not uid:
            raise errors.NotSetupError(message = "The Honkai Impact 3rd UID for this user is not setup!\nIf you are this user, try </hoyolab settings:999438437906124835>")
        return uid

    async def pull_hsuid(self,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.hsuid"})
        uid = methods.query(data = raw, search = ["hoyoverse","settings","hsuid"])
        if not uid:
            raise errors.NotSetupError(message = "The Honkai: Star Rail UID for this user is not setup!\nIf you are this user, try </hoyolab settings:999438437906124835>")
        return uid
    
    async def pull_zzzuid(self,user):
        raw = self.client.db.user_data.find_one({"_id":user.id},{"hoyoverse.settings.zzzuid"})
        uid = methods.query(data = raw, search = ["hoyoverse","settings","zzzuid"])
        if not uid:
            raise errors.NotSetupError(message = "The Zenless Zone Zero UID for this user is not setup!\nIf you are this user, try </hoyolab settings:999438437906124835>")
        return uid

    @commands.hybrid_group(extras = {"id": "500"},help = "The command group to manage your account details.")
    async def hoyolab(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `hoyolab` to get a list of commands.")
    
    @hoyolab.command(extras = {"id": "501"}, help = "Link your account!")
    async def link(self,ctx):
        embed = discord.Embed(title = "Hoyoverse Account Linking",description = "This is required to make most of the commands work! You can read more about this at </hoyolab information:999438437906124835>.\n\n⚠ If the script will only output your `ltuid` and not your `ltoken`, then your only option at the moment is manual input. Please read below for more information!",color = discord.Color.random())
        embed.add_field(name = "Login Method",value = 'Coming soon, stay tuned!',inline = False)
        embed.add_field(name = "Manual Input", value = "This method does not require login details. Instead, cookies are manually given. To find these, login to [hoyolab.com](https://www.hoyolab.com), open developer tools, navigate to application, cookies, and then hoyolab. You are looking for `ltuid_v2`, `ltoken_v2`, and `ltmid_v2`. With these pulled up, press `2. Manual Input` below and input these three values.\n\nIf you need assistance, refer to the [Youtube Tutorial](https://youtu.be/D5afCuFpz8M), or join the support server via </invite:1023762091603132498>.")
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        view = LinkView(ctx,self.public)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @hoyolab.command(extras = {"id": "540"},help = "View information about this group!")
    async def information(self,ctx):
        embed = discord.Embed(title = "Hoyoverse Group Information",description = "All you need to know about the commands!",color = discord.Color.random())
        embed.add_field(name = "Cookie Information",value = "Your cookies are needed as authentication to access any related data, such as your realtimenotes or character information. This information is stored securely, and cannot be used to do any serious damage to your account. However, there is always some risk is giving this information out to the bot, so plan accordingly.",inline = False)
        embed.add_field(name = "Authkey Information",value = "Your authkey is needed for any transaction information (ex. topups) as well as wishing and warp data. This, unlike cookies, has no risk to yourself when sharing the link.",inline = False)
        embed.add_field(name = "Data Removal",value = "At any time, you can remove all of your data from the bot with </hoyolab remove:999438437906124835>.",inline = False)
        embed.add_field(name = "Terms and Conditions",value = "As a user, you agree to not continually request uneeded data. Once hitting the rate limit, you will not continue to run commands.\nYou accept that the development team of the bot has no liability over your account information or use.\nSome assets within this section of the bot are owned solely by Cognosphere PTE. LTD. ",inline = False)
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
        
    @hoyolab.command(extras = {"id": "541"},help = "Remove all of your hoyoverse data from the bot.")
    async def remove(self,ctx):
        self.client.db.user_data.update_one({"_id":ctx.author.id},{"$unset":{"hoyoverse":""}})
        embed = discord.Embed(title = "Removed All Hoyoverse Data",description = "All of your stored Hoyoverse data has been removed successfully.",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)

    @hoyolab.command(extras = {"id": "502"}, help = "Edit any settings related to the Hoyoverse group.")
    async def settings(self,ctx):
        view = SettingsView(ctx)
        embed = await view.generate_embed(self.client.db.user_data.find_one({"_id":ctx.author.id},{"hoyoverse.settings":1}))
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @hoyolab.command(enabled = False,extras = {"id": "546"}, help = "Refresh your cookie token, in the event it has expired.")
    async def refresh(self,ctx):
        data = await self.get_redeem_cookies(ctx,ctx.author) 
        if not data: return
        async with ctx.typing():
            data = await genshin.refresh_cookie_token(cookies = data)
            cookie_token = data["cookie_token"]
            cookieutf8 = cookie_token.encode('utf8')
            encodedcookie = rsa.encrypt(cookieutf8,self.public)
            self.client.db.user_data.update_one({"_id":ctx.author.id},{"$set":{"hoyoverse.settings.cookietoken":binascii.hexlify(encodedcookie).decode('utf8')}})
            
        embed = discord.Embed(description = "<:greentick:930931553478008865> Sucessfully refreshed your redemption cookies!",color = discord.Color.green())
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)

    @hoyolab.command(extras = {"id": "503"}, help = "Get the game accounts linked to your Hoyoverse account.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def account(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            accounts = await client.get_game_accounts()
            embed = discord.Embed(title = f"Linked Game Accounts for {member}",color = discord.Color.random())
            for account in accounts:
                if "hk4e" in account.game_biz:
                    embed.add_field(name = "<:genshinicon:976949476784750612> Genshin Impact",value = f"UID: {account.uid}\nAdventure Rank: {account.level}\nNickname: {account.nickname}\nServer: {account.server_name}")
                if "bh3" in account.game_biz:
                    embed.add_field(name = "<:honkaiimpacticon:1041877640971288617> Honkai Impact 3rd",value = f"UID: {account.uid}\nLevel: {account.level}\nNickname: {account.nickname}\nServer: {account.server_name}")
                if "hkrpg" in account.game_biz:
                    embed.add_field(name = "<:honkaistarrailicon:1101673399996121178> Honkai: Star Rail",value = f"UID: {account.uid}\nTrailblaze Level: {account.level}\nNickname: {account.nickname}\nServer: {account.server_name}")
                if "nap" in account.game_biz:
                    embed.add_field(name = "<:zenless:1259288287588122644> Zenless Zone Zero", value = f"UID: {account.uid}\nInter-knot Level: {account.level}\nNickname: {account.nickname}\nServer: {account.server_name}")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)

    @commands.hybrid_group(extras = {"id": "504"},help = "The command group to manage Genshin Impact information.")
    async def genshin(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `genshin` to get a list of commands.")
    
    @genshin.command(extras = {"id": "505"}, help = "Overview statistics like achievement count and days active.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def stats(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_uid(member)
            data = await client.get_partial_genshin_user(uid)
            view = StatsView(ctx,data,uid)
            buffer = await view.generate_default()
            file = discord.File(buffer,filename = f"{uid}statcard.png")
            embed = discord.Embed(title = "Genshin Impact Stats Card",color = discord.Color.random())
            embed.set_image(url = f"attachment://{uid}statcard.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        message = await ctx.reply(file = file,embed = embed,view = view)
        view.message = message
    
    @genshin.command(extras = {"id": "506"}, help = "View spiral abyss statistics.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.",cycle = "Either the current spiral abyss period or the previous one.")
    async def spiralabyss(self,ctx,member:discord.Member = None, cycle: Literal['current','previous'] = None):
        member = member or ctx.author
        cycle = cycle or "current"
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_uid(member)
            data = await client.get_partial_genshin_user(uid)
            if cycle == "current":
                data = await client.get_genshin_spiral_abyss(uid)
            else:
                data = await client.get_genshin_spiral_abyss(uid, previous = True)
            view = AbyssView(ctx,data,uid)
            buffer = await view.generate_default()
            file = discord.File(buffer,filename = f"{uid}abysscard.png")
            embed = discord.Embed(title = "Genshin Impact Abyss Card",description = f"Season {data.season} | Start <t:{int(data.start_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> | End <t:{int(data.end_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",color = discord.Color.random())
            embed.set_image(url = f"attachment://{uid}abysscard.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        message = await ctx.reply(file = file,embed = embed,view = view)
        view.message = message
    
    @genshin.command(extras = {"id": "507"},aliases = ['rtn'], help = "Get real-time notes information like resin count.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def realtimenotes(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_uid(member)
            data = await client.get_genshin_notes(uid)
            now = discord.utils.utcnow()
            nowunix = int(now.replace(tzinfo=datetime.timezone.utc).timestamp())
            
            embed = discord.Embed(title = f"Real Time Notes for {member}",description = f"As of <t:{nowunix}:f>\nFor Account UID: `{uid}`",color = discord.Color.random())
            resinfull = now + data.remaining_resin_recovery_time
            if resinfull == now:
                embed.add_field(name = "<:resin:1041874856905556008> Resin",value = f"{data.current_resin}/{data.max_resin}\nResin is currently full!",inline = False)
            else:
                resinunix = int(resinfull.replace(tzinfo=datetime.timezone.utc).timestamp())
                embed.add_field(name = "<:resin:1041874856905556008> Resin",value = f"{data.current_resin}/{data.max_resin}\nFull Resin <t:{resinunix}:R>",inline = False)

            realmfull = now + data.remaining_realm_currency_recovery_time
            if realmfull == now:
                embed.add_field(name = "<:realm:1041875159956598888> Realm Currency",value = f"{data.current_realm_currency}/{data.max_realm_currency}\nRealm currency is currently full!",inline = False)
            else:
                realmunix = int(realmfull.replace(tzinfo=datetime.timezone.utc).timestamp())
                embed.add_field(name = "<:realm:1041875159956598888> Realm Currency",value = f"{data.current_realm_currency}/{data.max_realm_currency}\nFull Realm Currency <t:{realmunix}:R>",inline = False)
            
            embed.add_field(name = "<:dailycomm:1041875434289246339> Daily Commissions",value = f"{data.completed_commissions}/{data.max_commissions} commissions\nClaimed Commision Reward: {data.claimed_commission_reward}",inline = False)
            
            if not data.remaining_transformer_recovery_time:
                embed.add_field(name = "<:parametric:1041875667823890522> Parametic Transformer",value = f"Parametic transformer is currently available!",inline = False)
            else:
                transformerready = now + data.remaining_transformer_recovery_time
                transformerunix = int(transformerready.replace(tzinfo=datetime.timezone.utc).timestamp())
                embed.add_field(name = "<:parametric:1041875667823890522> Parametic Transformer",value = f"Available <t:{transformerunix}:R>",inline = False)
        
            embed.add_field(name = "<:weeklyboss:1041876105147187260> Weekly Boss Discounts",value = f"{data.remaining_resin_discounts}/{data.max_resin_discounts} remaining",inline = False)
            
            if data.expeditions:
                expeditionres = ""
                for expedition in data.expeditions:
                    if expedition.status == "Ongoing":
                        completein = now + expedition.remaining_time
                        completeunix = int(completein.replace(tzinfo=datetime.timezone.utc).timestamp())
                        expeditionres += f"**Expedition:** Complete <t:{completeunix}:R>\n"
                    else:
                        expeditionres += f"**Expedition:** Finished!\n"
                embed.add_field(name = "<:expedition:1041876327483064441> Expeditions",value = expeditionres,inline = False)
            else:
                embed.add_field(name = "<:expedition:1041876327483064441> Expeditions",value = f"None",inline = False)
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    '''
    @genshin.command(enabled = False,extras = {"id": "508"},help = "Redeem a code for yourself or a friend.",disabled=True)
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to redeem the code for.",code = "The code to redeem.")
    async def redeem(self,ctx,code:str,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_redeem_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            await client.redeem_code(code,game = genshin.Game.GENSHIN)
            embed = discord.Embed(description = f"Redeemed `{code}` for the account belonging to **{member}**! Please check your in game mail for more details.\nDid you know we now have auto redeem? Check it out with </hoyolab settings:999438437906124835>",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @genshin.command(extras = {"id": "509"},help = "As a bot mod, redeem codes for all users who have autoredeem setup.",disabled=True)
    @bot_mod_check()
    @commands.cooldown(1,10,commands.BucketType.user)
    async def massredeem(self,ctx,code:str):
        async with ctx.typing():
            accounts = self.client.db.user_data.find({"hoyoverse.settings.autoredeem":True},{"hoyoverse":1})
            success,error = 0,0
            for account in accounts:
                hoyosettings = account.get("hoyoverse",{}).get("settings",{})
                if "ltuid" in hoyosettings and "cookietoken" in hoyosettings:
                    account_id,cookie_token = hoyosettings['ltuid'], hoyosettings['cookietoken']
                    account_id = rsa.decrypt(binascii.unhexlify(account_id),self.private).decode('utf8')
                    cookie_token = rsa.decrypt(binascii.unhexlify(cookie_token),self.private).decode('utf8')
                    try:
                        client = genshin.Client({"account_id": account_id ,"cookie_token": cookie_token})
                        await client.redeem_code(code,game = genshin.Game.GENSHIN)
                        success += 1
                    except genshin.errors.InvalidCookies as e:
                        try:
                            data = await genshin.refresh_cookie_token(cookies = {"account_id": account_id ,"cookie_token": cookie_token})
                            client = genshin.Client(data)
                            await client.redeem_code(code,game = genshin.Game.GENSHIN)
                            success += 1
                            cookie_token = data["cookie_token"]
                            cookieutf8 = cookie_token.encode('utf8')
                            encodedcookie = rsa.encrypt(cookieutf8,self.key)
                            self.client.db.user_data.update_one({"_id":account["_id"]},{"$set":{"hoyoverse.settings.cookietoken":binascii.hexlify(encodedcookie).decode('utf8')}})
                        except Exception as e:
                            print(f"Error Refreshing Cookies for {account['_id']}: {e}")
                            error += 1
                    except Exception as e:
                        print(f"Redemption Error for {account['_id']}: {e}")
                        error += 1
            embed = discord.Embed(title = "Genshin Promotion Code Redeemed!",description = f"**{ctx.author}** has redeemed the code `{code}` for all users who have auto redeem setup!",color = discord.Color.random())
            embed.add_field(name = "Successful Claims",value = success)
            embed.add_field(name = "Failed Claims",value = error)
            channel = self.client.get_channel(int(1002939673120870401))
            embed.timestamp = datetime.datetime.now()
            embed.set_footer(text = "Check your in-game mail for details!")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            message = await channel.send(embed = embed)
            await message.publish()
        await ctx.reply(embed = discord.Embed(description = f"Successfully auto redeemed `{code}`!",color = discord.Color.green()))
    
    '''
        
    @genshin.group(extras = {"id": "510"}, help = "Genshin daily check-in management.")
    async def daily(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `genshin dailies` to get a list of commands.")
    
    @daily.command(extras = {"id": "511"},help = "Claim the daily reward for the day.")
    @commands.cooldown(1,120,commands.BucketType.user)
    @app_commands.describe(member = "The member to claim the daily for.")
    async def claim(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        geetest = False
        async with ctx.typing():
            client = genshin.Client(data)
            try:
                reward = await client.claim_daily_reward(game = genshin.Game.GENSHIN)
            except genshin.DailyGeetestTriggered as e:
                try:
                    self.captcha_tracking[ctx.author.id] = (self.captcha_tracking.get(ctx.author.id) or 0) + 1
                    result = await asyncio.gather(asyncio.to_thread(self.blocking_io,e.gt,e.challenge),asyncio.sleep(3))
                    data = json.loads(result[0]['code'])
                    challenge = {"challenge":data["geetest_challenge"],"validate":data["geetest_validate"],"seccode":data["geetest_seccode"]}
                    reward = await client.claim_daily_reward(game = genshin.Game.GENSHIN,challenge = challenge)
                    geetest = True
                except genshin.AlreadyClaimed as e:
                    raise genshin.AlreadyClaimed()
                except Exception as e:
                    print(e)
                    raise errors.GeetestError()
            embed = discord.Embed(title = "Claimed daily reward!",description = f"Claimed {reward.amount}x{reward.name}\nRewards have been sent to your account inbox! We also have auto daily claims, check it out with </hoyolab settings:999438437906124835>",color = discord.Color.green())
            if geetest:
                embed.add_field(name = "Geetest Solved!",value = "This command triggered a Geetest Captcha, which was solved successfully.")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            embed.set_thumbnail(url = reward.icon)
        await ctx.reply(embed = embed)
    
    @daily.command(extras = {"id": "512"},help = "Last 30 daily reward history information.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.",limit = "The amount of days to pull up inforamtion for.")
    async def history(self,ctx,limit: commands.Range[int,0] = None,member:discord.Member = None):
        member = member or ctx.author
        limit = limit or 30
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            data = []
            async for reward in client.claimed_rewards(limit = limit,game = genshin.Game.GENSHIN):
                data.append(reward)
            formatter = DailyClaimPageSource(data,self.client)
            menu = classes.MenuPages(formatter)
        await menu.start(ctx)
    
    @genshin.command(extras = {"id": "513"}, help = "View monthly diary information.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.", month = "The numerical month to pull information for.")
    async def diary(self,ctx,month: commands.Range[int,1,12] = None,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            diary = await client.get_diary(month = month)
            embed = discord.Embed(title = f"Traveler Diary Information for {self.months[diary.month]}",description = f"{diary.nickname} | {diary.uid} | {diary.server}",color = discord.Color.random())
            if diary.month == datetime.datetime.now().month:
                embed.add_field(name = "Today's Data",value = f"<:primogem:990335900280041472> Primogems Earned: {diary.day_data.current_primogems}\n<:mora:1041880089492733972> Mora Earned: {diary.day_data.current_mora}",inline = False)
            embed.add_field(name = "Month Total",value = f"<:primogem:990335900280041472> Total Primogems: {diary.data.current_primogems}\nPercentage Change from Last Month: {diary.data.primogems_rate}%\n<:mora:1041880089492733972> Total Mora: {diary.data.current_mora}\nPercentage Change from Last Month: {diary.data.mora_rate}%",inline = False)
            categories = '\n'.join([x.name + ': ' + str(x.amount) + ' | ' + str(x.percentage) + '%' for x in diary.data.categories])
            embed.add_field(name = "Primogem Breakdown",value = f"{categories}",inline = False)
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @genshin.command(extras = {"id": "514"}, help = "View player character data.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def characters(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_uid(member)
            characters = await client.get_genshin_characters(uid = uid)
            view = CharacterView(ctx,characters,uid)
            embed = discord.Embed(title = "Genshin Impact Characters",description = f"Use the dropdown below to get started!\nAccount UID: `{uid}`",color = discord.Color.random())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @genshin.group(extras = {"id": "515"}, help = "Do cost calculations for Genshin characters, weapons, and artifacts.")
    async def calculator(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `genshin calculator` to get a list of commands.")
    
    @calculator.command(extras = {"id": "516"},help = "Do character leveling calculations")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(character = "The character to do calculations for.",startlevel = "The starting level of said character.",endlevel = "The ending level of said character.")
    async def character(self,ctx,character:str,startlevel: app_commands.Range[int, 1, 90],endlevel:app_commands.Range[int, 1, 90]):
        if character not in self.character_mapping:
            raise errors.ParsingError(message = "I do not recognize that character name! You must input the full character name, for example, `Raiden Shogun` for raiden and `Shikanoin Heizou` for Heizou.")
        character = self.character_mapping[character]
        async with ctx.typing():
            client = self.standardclient
            data = await (
                client.calculator()
                .set_character(character.id, current = startlevel, target = endlevel)
            )
            back = Image.open("./pillow/staticassets/calculatorback.png")
            mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
            mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
            copy = back.copy()
            draw = Image.new("RGBA",copy.size)
            copy_editable = ImageDraw.Draw(draw)
            copy_editable.text((20,20),f"{character.name}: Leveling from {startlevel} to {endlevel}",(255,255,255),font = pillow.title_font)
            _,_,w,h = copy_editable.textbbox((0,0),"Placeholder",font = pillow.title_font)
            copy_editable.line(((20,40+h),(820,40+h)),(255,255,255),1)
            currenth = 40 + h + 21

            _,_,w2,h2 = copy_editable.textbbox((0,0),"Placeholder",font = pillow.subtitle_font)
            for cost in data.character:
                if os.path.exists(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}"):
                    costicon = Image.open(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                else:
                    costicon = Image.open(urlopen(cost.icon)).convert('RGBA')
                    costicon.save(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                costresized = costicon.resize((costicon.width//10,costicon.height//10))
                copy.paste(costresized,(20,currenth-5),costresized)
                copy_editable.text((30 + costresized.width,currenth),f"{cost.name} x {cost.amount} Required",font = pillow.subtitle_font,stroke_width = 1, stroke_fill = (0,0,0))
                currenth += h2 + 10

            credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
            _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
            copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
            copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 13),mafuyuresized)

            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            
            file = discord.File(buffer,filename = f"{ctx.author.id}calculator.png")
            embed = discord.Embed(title = "Genshin Impact Calculator",color = discord.Color.random())
            embed.set_image(url = f"attachment://{ctx.author.id}calculator.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(file = file,embed = embed)
    
    @character.autocomplete('character')
    async def character_autocomplete(self, interaction: discord.Interaction, current:str):
        characters = list(self.character_mapping.keys())
        return [
            app_commands.Choice(name = character, value = character)
            for character in characters if current.lower() in character.lower()
        ][:10]

    @calculator.command(extras = {"id": "517"},help = "Do weapon leveling calculations")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(weapon = "The weapon to do calculations for.",startlevel = "The starting level of said weapon.",endlevel = "The ending level of said weapon.")
    async def weapon(self,ctx,weapon:str,startlevel: app_commands.Range[int, 1, 90],endlevel:app_commands.Range[int, 1, 90]):
        if weapon not in self.weapon_mapping:
            raise errors.ParsingError(message = "I do not recognize that character name! You must input the full weapon name, for example, `Staff of Homa` for homa and `Engulfing Lightning` for engulfing.")
        weapon = self.weapon_mapping[weapon]
        async with ctx.typing():
            client = self.standardclient
            data = await (
                client.calculator()
                .set_weapon(weapon.id, current = startlevel, target = endlevel)
            )
            back = Image.open("./pillow/staticassets/calculatorback.png")
            mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
            mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
            copy = back.copy()
            draw = Image.new("RGBA",copy.size)
            copy_editable = ImageDraw.Draw(draw)
            copy_editable.text((20,20),f"{weapon.name}: Leveling from {startlevel} to {endlevel}",(255,255,255),font = pillow.title_font)
            _,_,w,h = copy_editable.textbbox((0,0),"Placeholder",font = pillow.title_font)
            copy_editable.line(((20,40+h),(820,40+h)),(255,255,255),1)
            currenth = 40 + h + 21

            _,_,w2,h2 = copy_editable.textbbox((0,0),"Placeholder",font = pillow.subtitle_font)
            for cost in data.weapon:
                if os.path.exists(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}"):
                    costicon = Image.open(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                else:
                    costicon = Image.open(urlopen(cost.icon)).convert('RGBA')
                    costicon.save(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                costresized = costicon.resize((costicon.width//10,costicon.height//10))
                copy.paste(costresized,(20,currenth-5),costresized)
                copy_editable.text((30 + costresized.width,currenth),f"{cost.name} x {cost.amount} Required",font = pillow.subtitle_font,stroke_width = 1, stroke_fill = (0,0,0))
                currenth += h2 + 10

            credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
            _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
            copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
            copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 13),mafuyuresized)

            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            
            file = discord.File(buffer,filename = f"{ctx.author.id}calculator.png")
            embed = discord.Embed(title = "Genshin Impact Calculator",color = discord.Color.random())
            embed.set_image(url = f"attachment://{ctx.author.id}calculator.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(file = file,embed = embed)
    
    @weapon.autocomplete('weapon')
    async def weapon_autocmoplete(self, interaction: discord.Interaction, current:str):
        weapons = list(self.weapon_mapping.keys())
        return [
            app_commands.Choice(name = weapon, value = weapon)
            for weapon in weapons if current.lower() in weapon.lower()
        ][:10]

    @calculator.command(extras = {"id": "518"},help = "Do artifact leveling calculations")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(artifact = "The artifact to do calculations for.",startlevel = "The starting level of said artifact.",endlevel = "The ending level of said artifact.")
    async def artifact(self,ctx,artifact:str,startlevel: app_commands.Range[int, 0, 20],endlevel:app_commands.Range[int, 0, 20]):
        if artifact not in self.artifact_mapping:
            raise errors.ParsingError(message = "I do not recognize that artifact name! You must input the full artifact name and rarity, for example, `Gladiator's Nostalgia (⭐5).")
        artifact = self.artifact_mapping[artifact]
        async with ctx.typing():
            client = self.standardclient
            data = await (
                client.calculator()
                .add_artifact(artifact.id, current = startlevel, target = endlevel)
            )
            back = Image.open("./pillow/staticassets/calculatorback.png")
            mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
            mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
            copy = back.copy()
            draw = Image.new("RGBA",copy.size)
            copy_editable = ImageDraw.Draw(draw)
            copy_editable.text((20,20),f"{artifact.name} | {artifact.pos_name}: Leveling from {startlevel} to {endlevel}",(255,255,255),font = pillow.title_font)
            _,_,w,h = copy_editable.textbbox((0,0),"Placeholder",font = pillow.title_font)
            copy_editable.line(((20,40+h),(820,40+h)),(255,255,255),1)
            currenth = 40 + h + 21

            _,_,w2,h2 = copy_editable.textbbox((0,0),"Placeholder",font = pillow.subtitle_font)
            for cost in data.artifacts[0].list:
                if os.path.exists(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}"):
                    costicon = Image.open(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                else:
                    costicon = Image.open(urlopen(cost.icon)).convert('RGBA')
                    costicon.save(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                costresized = costicon.resize((costicon.width//10,costicon.height//10))
                copy.paste(costresized,(20,currenth-5),costresized)
                copy_editable.text((30 + costresized.width,currenth),f"{cost.name} x {cost.amount} Required",font = pillow.subtitle_font,stroke_width = 1, stroke_fill = (0,0,0))
                currenth += h2 + 10

            credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
            _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
            copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
            copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 13),mafuyuresized)

            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            
            file = discord.File(buffer,filename = f"{ctx.author.id}calculator.png")
            embed = discord.Embed(title = "Genshin Impact Calculator",color = discord.Color.random())
            embed.set_image(url = f"attachment://{ctx.author.id}calculator.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(file = file,embed = embed)
    
    @artifact.autocomplete('artifact')
    async def artiact_autocomplete(self, interaction: discord.Interaction, current:str):
        artifacts = list(self.artifact_mapping.keys())
        return [
            app_commands.Choice(name = artifact, value = artifact)
            for artifact in artifacts if current.lower() in artifact.lower()
        ][:10]

    @calculator.command(extras = {"id": "519"},help = "Do character talent leveling calculations")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(character = "The character to do calculations for.",talenttype = "The type of talent to do calculations for.",startlevel = "The starting level of said talent.",endlevel = "The ending level of said talent.")
    async def talents(self,ctx,character:str,talenttype: Literal['Attack','Skill','Burst'],startlevel: app_commands.Range[int, 1, 9],endlevel:app_commands.Range[int, 1, 10]):
        if character not in self.character_mapping:
            raise errors.ParsingError(message = "I do not recognize that character name! You must input the full character name, for example, `Raiden Shogun` for raiden and `Shikanoin Heizou` for Heizou.")
        character = self.character_mapping[character]
        talents = self.talent_mapping.get(character.id,None)
        async with ctx.typing():
            client = self.standardclient
            if not talents:
                talents = await client.get_character_talents(character)
                self.talent_mapping[character.id] = talents
            for talent in talents:
                if talent.type.capitalize() == talenttype:
                    talenttype = talent
                    break
            data = await (
                client.calculator()
                .set_character(character.id,current = 0, target = 0)
                .add_talent(talenttype.group_id,current = startlevel,target = endlevel)
            )
            back = Image.open("./pillow/staticassets/calculatorback.png")
            mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
            mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
            copy = back.copy()
            draw = Image.new("RGBA",copy.size)
            copy_editable = ImageDraw.Draw(draw)
            copy_editable.text((20,20),f"{character.name} | {talenttype.name}: Leveling from {startlevel} to {endlevel}",(255,255,255),font = pillow.title_font)
            _,_,w,h = copy_editable.textbbox((0,0),"Placeholder",font = pillow.title_font)
            copy_editable.line(((20,40+h),(820,40+h)),(255,255,255),1)
            currenth = 40 + h + 21

            _,_,w2,h2 = copy_editable.textbbox((0,0),"Placeholder",font = pillow.subtitle_font)
            for cost in data.talents:
                if os.path.exists(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}"):
                    costicon = Image.open(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                else:
                    costicon = Image.open(urlopen(cost.icon)).convert('RGBA')
                    costicon.save(f"./pillow/dynamicassets/{cost.icon.split('/')[-1]}")
                costresized = costicon.resize((costicon.width//10,costicon.height//10))
                copy.paste(costresized,(20,currenth-5),costresized)
                copy_editable.text((30 + costresized.width,currenth),f"{cost.name} x {cost.amount} Required",font = pillow.subtitle_font,stroke_width = 1, stroke_fill = (0,0,0))
                currenth += h2 + 10

            credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
            _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
            copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
            copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 13),mafuyuresized)

            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            
            file = discord.File(buffer,filename = f"{ctx.author.id}calculator.png")
            embed = discord.Embed(title = "Genshin Impact Calculator",color = discord.Color.random())
            embed.set_image(url = f"attachment://{ctx.author.id}calculator.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(file = file,embed = embed)
    
    @talents.autocomplete('character')
    async def talentcharacter_autocomplete(self, interaction: discord.Interaction, current:str):
        characters = list(self.character_mapping.keys())
        return [
            app_commands.Choice(name = character, value = character)
            for character in characters if current.lower() in character.lower()
        ][:10]

    @genshin.command(extras = {"id": "520"},help = "Set Genshin authkey in the bot.")
    async def authkey(self,ctx):
        embed = discord.Embed(title = "Hoyoverse Authkey Linking",description = "This is required to make any wish/transaction commands work! You can read more about this at </hoyolab information:999438437906124835>.",color = discord.Color.random())
        embed.add_field(name = "Getting Authkey",value = "1. Open up wish history in game.\n2. Open Windows Powershell from your start menu.\n3. Copy the script from the button 'Get Script', and paste it in the Powershell window.\n4. Click the button below, and paste the link into the dialogue box.",inline = False)
        embed.set_image(url = "https://cdn.discordapp.com/attachments/870127759526101032/1081033414486020136/ezgif.com-video-to-gif.gif")
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        view = AuthkeyView(ctx)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @genshin.command(extras = {"id": "521"},help = "Command to track your resin spending within the past 6 months.")
    @commands.cooldown(1,120,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def resintracker(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.auth_privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their wish/transaction data set to private!")
        data = await self.get_authkey(ctx,member) 
        if not data: return
        async with ctx.typing():
            log = await self.standardclient.transaction_log(authkey = data, kind = "resin").flatten()
            data = {"boss":0,"weeklybossd":0,"weeklyboss":0,"condensed":0,"domain":0,"leyline":0,"ore":0,"spent":0}
            start = log[-1].time
            for transaction in log:
                if transaction.reason_name == "Trounce Blossom challenge reward":
                    if transaction.amount == -30:
                        data["weeklybossd"] += 1
                    elif transaction.amount == -60:
                        data["weeklyboss"] += 1
                    elif transaction.amount == -40:
                        data["boss"] += 1
                elif transaction.reason_name == "Item crafting material":
                    if transaction.amount % 40 == 0:
                        data["condensed"] += -transaction.amount//40
                    elif transaction.amount % 10 == 0:
                        data["ore"] += -transaction.amount//10
                elif transaction.reason_name == "Revitalized Petrified Tree (Domain)":
                    if transaction.amount == -20:
                        data["domain"] += 1
                elif transaction.reason_name == "Ley Line Blossom challenge reward":
                    if transaction.amount == -20:
                        data["leyline"] += 1
                data["spent"] += -transaction.amount
            embed = discord.Embed(title = f"Resin Spending for {member}",color = discord.Color.random())
            embed.add_field(name = "Total Statistics",value = f"Resin Transaction Count: {len(log)}\nTotal Resin Spent: <:resin:1041874856905556008> {data['spent']}\nFirst Tracked Resin Spending On: <t:{int(start.replace(tzinfo=datetime.timezone.utc).timestamp())}:F>",inline = False)
            embed.add_field(name = "Weekly Bosses",value = f"Weekly Boss Rewards (Discount): x{data['weeklybossd']}\nWeekly Boss Rewards (Full): x{data['weeklyboss']}\nTotal Spent: <:resin:1041874856905556008> {data['weeklybossd'] * 30 + data['weeklyboss'] * 60}",inline = False)
            embed.add_field(name = "World Bosses",value = f"World Boss Rewards: x{data['boss']}\nTotal Spent: <:resin:1041874856905556008> {data['boss'] * 40}",inline = False)
            embed.add_field(name = "Crafting Materials",value = f"Condensed Resin Crafted: x{data['condensed']}\nEnhancement Ore Crafted: x{data['ore']}\nTotal Spent: <:resin:1041874856905556008> {data['ore'] * 10 + data['condensed'] * 40}",inline = False)
            embed.add_field(name = "Domains",value = f"Domain Rewards Claimed: x{data['domain']}\nTotal Spent: <:resin:1041874856905556008> {data['domain'] * 20}",inline = False)
            embed.add_field(name = "Leylines",value = f"Leyline Rewards Claimed: x{data['leyline']}\nTotal Spent: <:resin:1041874856905556008> {data['leyline'] * 20}",inline = False)
            embed.add_field(name = "Behind the Scenes",value = "This information is gathered from your resin logs, and only tracks resin spending. This means no data is used from fragile resin, resin refreshes, or other forms of gaining resin. Domain and ley line clears are only tracked when not using condensed resin, and any ore crafting that used 40 resin will count as a condensed resin. Data expires after 6 months, so any data from prior to 6 months is not included.")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @genshin.command(extras = {"id": "522"},help = "Fun command to measure the whaleness of a member.")
    @commands.cooldown(1,120,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def whalemeter(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.auth_privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their wish/transaction data set to private!")
        authkey = await self.get_authkey(ctx,member) 
        if not authkey: return
        async with ctx.typing():
            message = await ctx.reply(embed = discord.Embed(description = "Processing Genesis Crystal data...please wait.",color = discord.Color.random()))
            data = {"welkins":0,"battle":0,"topups":0,"1":0,"5":0,"15":0,"30":0,"50":0,"100":0,"spent":0}
            log = await self.standardclient.transaction_log(authkey = authkey,kind = "crystal").flatten()

            if not log or len(log) < 1:
                return await message.edit(embed = discord.Embed(description = "I do not see any purchase history for this user!",color = discord.Color.red()))
            
            start = log[-1].time

            for transaction in log:
                if transaction.reason_name == "Purchased Blessing of the Welkin Moon":
                    data['welkins'] += 1
                    data['spent'] += 4.99
                elif transaction.reason_name == "Purchased Genesis Crystals":
                    data['topups'] += transaction.amount
                    if transaction.amount == 60 or transaction.amount == 120:
                        data['spent'] += 0.99
                        data['1'] += 1
                    elif transaction.amount == 330 or transaction.amount == 600:
                        data['spent'] += 4.99
                        data['5'] += 1
                    elif transaction.amount == 1090 or transaction.amount == 1960:
                        data['spent'] += 14.99
                        data['15'] += 1
                    elif transaction.amount == 2240 or transaction.amount == 3960:
                        data['spent'] += 29.99
                        data['30'] += 1
                    elif transaction.amount == 3880 or transaction.amount == 6560:
                        data['spent'] += 49.99
                        data['50'] += 1
                    elif transaction.amount == 8080 or transaction.amount == 12960:
                        data['spent'] += 99.99
                        data['100'] += 1
            await message.edit(embed = discord.Embed(description = "Looking for Battle Pass weapon transactions...please wait.\nNote: This may take some time, as I am looking through every single weapon transaction you have had for up to 6 months. This will only be able to count battle pass transactions where you reached and claimed the weapon box tier. This will only count the base battle pass cost into calculations.",color = discord.Color.random()))
            log = await self.standardclient.transaction_log(authkey = authkey,kind = "weapon").flatten()

            for transaction in log:
                if transaction.reason_name == "BP reward" and transaction.amount == 1:
                    data['battle'] += 1
                    data['spent'] += 9.99
                    if transaction.time < start:
                        start = transaction

            tz_info = start.tzinfo
            average = round(data['spent']/((datetime.datetime.now(tz_info)-start).days/30),2)
            total = round(data['spent'],2)

            if average == 0:
                classficiation = "Atom of Water (F2P)"
                description = "You stayed strong, not spending any of your money (if you have any) on virtual anime characters. But is it really free, if you pay with your time?"
            elif average < 5:
                classficiation = "Plankton (<$5)"
                description = "Not even a welkin a month...you are basically free to play. Why did you even bother spending anyways??"
            elif average == 5:
                classification = "Mackerel ($5)"
                description = "A faithful welkin player, truly a person of culture. Those extra rolls got you just that much closer to losing your 50/50!"
            elif average < 30:
                classification = "Herring ($5 - 30$)"
                description = "Maybe you also threw in a few battle passes along with those welkins. Did you enjoy the extra few primogems and rolls?"
            elif average < 100:
                classification = "Salmon ($30 - $100)"
                description = "That's almost tripls digits per month into a video game. I hope those top-ups were both double bonuses, right? Right???"
            elif average < 500:
                classification = "Seal ($100 - $500)"
                description = "Congrats, you are no longer a fish. Is it really a congratulations though, if the game makes your money disappear? Don't worry, sometimes rolling is worth it."
            elif average < 1000:
                classification = "Dolphin ($500 - $1000)"
                description = "Did these go into multiple characters, or all into one character? Either way, this is quite the amount of money."
            elif average < 5000:
                classification = "Whale ($1000 - $5000)"
                description = "You made it! You are now in whale territory. This is more than monthly rent and even all living expenses for some people."
            else:
                classification = "Leviathan"
                description = "What. The. Fuck. Over $5000 a month on Genshin Impact? I hope all your characters are C6R5 at this point. While I have nothing to say, enjoy I guess???"
            
            embed = discord.Embed(title = f"WhaleOMeter for {member}",color = discord.Color.random())
            embed.add_field(name = f"Classification: {classification}",value = description,inline = False)
            embed.add_field(name = "Spending Statistics",value = f"Total Spent: ${total} USD\nMonthy Average: ${average} USD\nFirst Tracked Purchase On: <t:{int(start.replace(tzinfo=datetime.timezone.utc).timestamp())}:F>",inline = False)
            embed.add_field(name = "By Purchase Type",value = f"<:welkin:1019776537869942816> Blessings of the Welkin Moon: x{data['welkins']}\n<:battlepass:1019776951759667270> Battle Passes: x{data['battle']}\n<:genesis:1019770551893512262> 60 Genesis Cyrstals Topup: x{data['1']}\n<:genesis:1019770551893512262> 300 Genesis Cyrstals Topup: x{data['5']}\n<:genesis:1019770551893512262> 980 Genesis Cyrstals Topup: x{data['15']}\n<:genesis:1019770551893512262> 1980 Genesis Cyrstals Topup: x{data['30']}\n<:genesis:1019770551893512262> 3290 Genesis Cyrstals Topup: x{data['50']}\n<:genesis:1019770551893512262> 6480 Genesis Cyrstals Topup: x{data['100']}",inline = False)
            embed.add_field(name = "Behind the Scenes",value = "This information is gathered from your genesis cyrstal transactions to track welkins and topups, and your primogem logs to track battle passes. Battle passes are counted as $10 no matter which tier you bought, and only count if you redeem the tier 50 680 primogem reward. Data expires after 6 months, so any data from prior to 6 months is not included.",inline = False)
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await message.edit(embed = embed)
    
    @genshin.command(extras = {"id": "523"},help = "View wishing data.")
    @commands.cooldown(1,60,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.",limit = "The amount of wishes to pull up.")
    async def wishes(self,ctx,limit:int = 2000,member:discord.Member = None):
        member = member or ctx.author
        if not await self.auth_privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their wish/transaction data set to private!")
        authkey = await self.get_authkey(ctx,member) 
        if not authkey: return
        async with ctx.typing():
            data = await self.standardclient.wish_history(authkey = authkey,limit = limit).flatten()
        
            stats = {"5":[],"4":[],"3":[],"s":[],"w":[],"c":[],"n":[]}
            for wish in data:
                if wish.rarity == 5:
                    stats["5"].append(wish)
                elif wish.rarity == 4:
                    stats["4"].append(wish)
                else:
                    stats["3"].append(wish)
                
                if wish.banner_type == genshin.models.GenshinBannerType.STANDARD:
                    stats["s"].append(wish)
                elif wish.banner_type == genshin.models.GenshinBannerType.CHARACTER:
                    stats["c"].append(wish)
                elif wish.banner_type == genshin.models.GenshinBannerType.WEAPON:
                    stats["w"].append(wish)
                elif wish.banner_type == genshin.models.GenshinBannerType.NOVICE:
                    stats["n"].append(wish)
            embed = discord.Embed(title = f"Wish history for {member}",description = f"Looking at the past `{len(data)}` wishes",color = discord.Color.random())
            embed.add_field(name = "Total Statistics",value = f'Total Pulls: <:intertwined:990336430934999040> {len(data)}\nPrimogem Equivalent: <:primogem:990335900280041472> {len(data)*160}\nAverage Pity: <:acquaint:990336486723432490> {int(len(data)/len(stats["5"])) if len(stats["5"]) > 0 else "None"}',inline = False)
            embed.add_field(name = "By Rarity",value = f'5 🌟 Pulls: {len(stats["5"])}\n4 🌟 Pulls: {len(stats["4"])}\n3 ⭐ Pulls: {len(stats["3"])}')
            embed.add_field(name = "By Banner",value = f'Standard Banner Pulls: <:acquaint:990336486723432490> {len(stats["s"])}\nLimited Character Banner Pulls: <:intertwined:990336430934999040> {len(stats["c"])}\nLimited Weapon Banner Pulls: <:intertwined:990336430934999040> {len(stats["w"])}\nNovice Banner Pulls: <:acquaint:990336486723432490> {len(stats["n"])}')
            embed.add_field(name = "Disclaimer",value = "This data is limited to the past 6 months. Due to this, there may be inaccurate counting in wish total, pity counting, 50/50 counting, and other information.",inline = False)
            embed.set_footer(text = "Use the dropdown below to sort by banner!")
            view = WishView(ctx,stats,member,embed)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @genshin.command(extras = {"id": "524"},help = "Use Enka network to pull up character builds.")
    @commands.cooldown(1,60,commands.BucketType.user)
    @app_commands.describe(uid = "The in-game UID for the user to check builds for")
    async def enka(self,ctx,uid:int):
        async with ctx.typing():
            encard = encbanner.ENC(lang = "en")
            ENCpy = await encard.enc(uids = str(uid))
            encard = encbanner.ENC(lang = "en")
            data = await encard.creat(ENCpy,3)
            data = data.get(str(uid),{})
            view = EnkaCharacterView(ctx,data)
            embed = discord.Embed(title = f"Enka Network Cards for {uid}",description = f"{len(data)} Characters Found",color = discord.Color.random())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @commands.hybrid_group(extras = {"id": "525"},help = "The command group to see Honkai Impact 3rd information.")
    async def honkaiimpact3rd(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `honkaiimpact3rd` to get a list of commands.")
        
    @honkaiimpact3rd.group(extras = {"id": "526"},name = "daily",help = "Honkai Impact 3rd daily checkin management.")
    async def honkaidaily(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `honkaiimpact3rd dailies` to get a list of commands.")
    
    @honkaidaily.command(extras = {"id": "527"},name = "claim", help = "Claim daily rewards for the day.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def honkaiclaim(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member)
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            reward = await client.claim_daily_reward(game = genshin.Game.HONKAI)
            embed = discord.Embed(title = "Claimed daily reward!",description = f"Claimed {reward.amount}x{reward.name}\nRewards have been sent to your account inbox! We also have auto daily claims, check it out with </hoyolab settings:999438437906124835>",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            embed.set_thumbnail(url = reward.icon)
        await ctx.reply(embed = embed)
    
    @honkaidaily.command(extras = {"id": "528"},name = "history",help = "Last 30 daily reward history information.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.",limit = "The amount of days to pull information for.")
    async def honkaihistory(self,ctx,limit: commands.Range[int,0] = None,member:discord.Member = None):
        member = member or ctx.author
        limit = limit or 30
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            data = []
            async for reward in client.claimed_rewards(limit = limit,game = genshin.Game.HONKAI):
                data.append(reward)
            formatter = DailyClaimPageSource(data,self.client)
            menu = classes.MenuPages(formatter)
        await menu.start(ctx)
    
    @honkaiimpact3rd.command(extras = {"id": "529"},name = "battlesuits", help = "View player battlesuit data.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def battlesuits(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member)
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_huid(member)
            data = await client.get_honkai_battlesuits(uid)
            view = BattlesuitView(ctx,data)
            embed = discord.Embed(title = f"Battlesuits for {member}",description = f"{len(data)} Battlesuits Owned\nAccount UID: `{uid}`",color = discord.Color.random())
            embed.set_footer(text = "Use the dropdown below to view their battlesuits!")
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @honkaiimpact3rd.command(extras = {"id": "530"},name = "oldabyss", help = "View abyss data for either Quantum Singularis or Dirac Sea.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def oldabyss(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member)
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_huid(member)
            data = await client.get_honkai_old_abyss(uid)
            if not data or len(data) < 1:
                raise errors.NoDataError(message = "This user has no old abyss data for past cycles!")
            embed = discord.Embed(title = f"Old Abyss for {member}",description = f"{len(data)} reports found\nAccount UID: `{uid}`",color = discord.Color.random())
            embed.set_footer(text = "Use the dropdown below to see report information!")
            view = OldAbyssView(ctx,data)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @honkaiimpact3rd.command(extras = {"id": "531"},name = "memorialarena", help = "View Memorial Arena data for the current cycle.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def memorialarena(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member)
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_huid(member)
            data = await client.get_honkai_memorial_arena(uid)
            if not data or len(data) < 1:
                raise errors.NoDataError(message = "This user has no Memorial Arena data for past cycles!")
            embed = discord.Embed(title = f"Memorial Arena for {member}",description = f"{len(data)} reports found\nAccount UID: `{uid}`",color = discord.Color.random())
            embed.set_footer(text = "Use the dropdown below to see report information!")
            view = MemorialArenaView(ctx,data)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message

    @honkaiimpact3rd.command(extras = {"id": "532"},name = "elysianrealm", help = "View Elysian Realm data for the current cycle.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def elysianrealm(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member)
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_huid(member)
            data = await client.get_honkai_elysian_realm(uid)
            if not data or len(data) < 1:
                raise errors.NoDataError(message = "This user has no Elysian Realm data for this cycle!")
            embed = discord.Embed(title = f"Elysian Realm for {member}",description = f"{len(data)} reports found\nAccount UID: `{uid}`",color = discord.Color.random())
            embed.set_footer(text = "Use the dropdown below to see report information!")
            view = ElysianRealmView(ctx,data)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message

    @honkaiimpact3rd.command(extras = {"id": "533"},name = "superstringabyss", help = "View Superstring Abyss for the current cycle.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def superstringabyss(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member)
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await client._get_uid(genshin.Game.HONKAI)
            data = await self.pull_huid(member)
            if not data or len(data) < 1:
                raise errors.NoDataError(message = "This user has no Superstring Abyss data for past cycles!")
            embed = discord.Embed(title = f"Superstring Abyss for {member}",description = f"{len(data)} reports found\nAccount UID: `{uid}`",color = discord.Color.random())
            embed.set_footer(text = "Use the dropdown below to see report information!")
            view = SuperstringAbyssView(ctx,data)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @commands.hybrid_group(extras = {"id": "534"},help = "The command group to manage Honkai: Star Rail information.")
    async def honkaistarrail(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `honkaistarrail` to get a list of commands.")
    
    @honkaistarrail.group(extras = {"id": "535"}, name = "daily",help = "Honkai Star Rail daily check-in management.")
    async def honkaistardaily(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `honkaistarrail dailies` to get a list of commands.")
    
    @honkaistardaily.command(extras = {"id": "536"},name = "claim",help = "Claim the daily reward for the day.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to claim the daily for.")
    async def honkaistarclaim(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            reward = await client.claim_daily_reward(game = genshin.Game.STARRAIL)
            embed = discord.Embed(title = "Claimed daily reward!",description = f"Claimed {reward.amount}x{reward.name}\nRewards have been sent to your account inbox! We also have auto daily claims, check it out with </hoyolab settings:999438437906124835>",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            embed.set_thumbnail(url = reward.icon)
        await ctx.reply(embed = embed)
    
    @honkaistardaily.command(extras = {"id": "537"},name = "history",help = "Last 30 daily reward history information.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.",limit = "The amount of days to pull up inforamtion for.")
    async def honkaistarhistory(self,ctx,limit: commands.Range[int,0] = None,member:discord.Member = None):
        member = member or ctx.author
        limit = limit or 30
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            data = []
            async for reward in client.claimed_rewards(limit = limit,game = genshin.Game.STARRAIL):
                data.append(reward)
            formatter = DailyClaimPageSource(data,self.client)
            menu = classes.MenuPages(formatter)
        await menu.start(ctx)
    
    '''
    @honkaistarrail.command(enabled = False,extras = {"id": "538"},name = "redeem",help = "Redeem a code for yourself or a friend.",disabled=True)
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to redeem the code for.",code = "The code to redeem.")
    async def honkaistarredeem(self,ctx,code:str,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_redeem_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            await client.redeem_code(code,game = genshin.Game.STARRAIL)
            embed = discord.Embed(description = f"Redeemed `{code}` for the account belonging to **{member}**! Please check your in game mail for more details.",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @honkaistarrail.command(extras = {"id": "539"},name = "massredeem",help = "As a bot mod, redeem codes for all users who have autoredeem setup.",disabled=True)
    @bot_mod_check()
    @commands.cooldown(1,10,commands.BucketType.user)
    @app_commands.describe(code = "The code to redeem.")
    async def honkaistarmassredeem(self,ctx,code:str):
        async with ctx.typing():
            accounts = self.client.db.user_data.find({"hoyoverse.settings.hsautoredeem":True},{"hoyoverse":1})
            success,error = 0,0
            for account in accounts:
                hoyosettings = account.get("hoyoverse",{}).get("settings",{})
                if "ltuid" in hoyosettings and "cookietoken" in hoyosettings:
                    account_id,cookie_token = hoyosettings['ltuid'], hoyosettings['cookietoken']
                    if account_id and cookie_token:
                        account_id = rsa.decrypt(binascii.unhexlify(account_id),self.private).decode('utf8')
                        cookie_token = rsa.decrypt(binascii.unhexlify(cookie_token),self.private).decode('utf8')
                    try:
                        client = genshin.Client({'account_id':account_id,'cookie_token':cookie_token})
                        await client.redeem_code(code,game = genshin.Game.STARRAIL)
                        success += 1
                    except genshin.errors.InvalidCookies as e:
                        try:
                            data = await genshin.refresh_cookie_token(cookies = {"account_id": account_id ,"cookie_token": cookie_token})
                            client = genshin.Client(data)
                            await client.redeem_code(code,game = genshin.Game.STARRAIL)
                            success += 1
                            cookie_token = data["cookie_token"]
                            cookieutf8 = cookie_token.encode('utf8')
                            encodedcookie = rsa.encrypt(cookieutf8,self.key)
                            self.client.db.user_data.update_one({"_id":ctx.author.id},{"$set":{"hoyoverse.settings.cookietoken":binascii.hexlify(encodedcookie).decode('utf8')}})
                        except Exception as e:
                            print(f"Error Refreshing Cookies for {account['_id']}: {e}")
                            error += 1
                    except Exception as e:
                        print(f"Redemption Error for {account['_id']}: {e}")
                        error += 1
            embed = discord.Embed(title = "Honkai: Star Rail Promotion Code Redeemed!",description = f"**{ctx.author}** has redeemed the code `{code}` for all users who have auto redeem setup!",color = discord.Color.random())
            embed.add_field(name = "Successful Claims",value = success)
            embed.add_field(name = "Failed Claims",value = error)
            channel = self.client.get_channel(int(1002939673120870401))
            embed.timestamp = datetime.datetime.now()
            embed.set_footer(text = "Check your in-game mail for details!")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            message = await channel.send(embed = embed)
            await message.publish()
        await ctx.reply(embed = discord.Embed(description = f"Successfully auto redeemed `{code}`!",color = discord.Color.green()))
    '''
        
    @honkaistarrail.command(extras = {"id":"547"},name = "stats",help = "View your player stats like days active and achievements.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def hsstats(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_hsuid(member)
            data = await client.get_starrail_user(uid = uid)
            back = Image.open("./pillow/staticassets/hsback.png").convert('RGBA')
            mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
            mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
            backresized = back.resize((back.width//2,back.height//2))
            copy = backresized.copy()
            draw = Image.new("RGBA",copy.size)
            copy_editable = ImageDraw.Draw(draw)
            uidtext = f"UID: {uid}"
            copy_editable.text((20,20),"User Statistics",(255,255,255),font = pillow.title_font)
            _,_,w,h = copy_editable.textbbox((0,0),uidtext,font = pillow.title_font)
            copy_editable.text((copy.width-w-20,20),uidtext,font = pillow.title_font)
            copy_editable.line(((20,40+h),(869,40+h)),(255,255,255),1)
            currenth = 40+h+21

            copy_editable.text((20,currenth),f"Nickname: {data.info.nickname}",font = pillow.title_font)
            currenth += 15 + h
            copy_editable.text((20,currenth),f"Trailblaze Level: {data.info.level}",font = pillow.title_font)
            currenth += 15 + h
            copy_editable.text((20,currenth),f"Active Days: {data.stats.active_days}",font = pillow.title_font)
            currenth += 15 + h
            copy_editable.text((20,currenth),f"Character Count: {data.stats.avatar_num}",font = pillow.title_font)
            currenth += 15 + h
            copy_editable.text((20,currenth),f"Achievements Unlocked: {data.stats.achievement_num}",font = pillow.title_font)
            currenth += 15 + h
            copy_editable.text((20,currenth),f"Chests Opened: {data.stats.chest_num}",font = pillow.title_font)
            currenth += 15 + h
            copy_editable.text((20,currenth),f"Forgotten Hall: {data.stats.abyss_process}",font = pillow.title_font)

            copy_editable.line(((20,copy.height-40),(869,copy.height-40)),(255,255,255),1)

            credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
            _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
            copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (177, 156, 217))
            copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 13),mafuyuresized)

            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            file = discord.File(buffer,filename = f"{uid}statcard.png")
            embed = discord.Embed(title = "Honkai: Star Rail Stats Card",color = discord.Color.random())
            embed.set_image(url = f"attachment://{uid}statcard.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(file = file,embed = embed)
    
    @honkaistarrail.command(extras = {"id":"548"},name = "realtimenotes",aliases = ['rtn'],help = "Get real-time notes information like trailblaze power.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def hsrealtimenotes(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_hsuid(member)
            data = await client.get_starrail_notes(uid = uid)
            now = discord.utils.utcnow()
            nowunix = int(now.replace(tzinfo=datetime.timezone.utc).timestamp())

            embed = discord.Embed(title = f"Real Time Notes for {member}",description = f"As of <t:{nowunix}:f>\nFor Account UID: `{uid}`",color = discord.Color.random())
            trailblazefull = now + data.stamina_recover_time
            if trailblazefull == now:
                embed.add_field(name = "<:trailblazepower:1116016414067785800> Trailblaze Power",value = f"{data.current_stamina}/{data.max_stamina}\nTrailblaze Power is currently full!",inline = False)
            else:
                trailblazeunix = int(trailblazefull.replace(tzinfo = datetime.timezone.utc).timestamp())
                embed.add_field(name = "<:trailblazepower:1116016414067785800> Trailblaze Power",value = f"{data.current_stamina}/{data.max_stamina}\nFull Trailblaze Power <t:{trailblazeunix}:R>",inline = False)

            if data.is_reserve_stamina_full:
                embed.add_field(name = "<:hsrreserve:1146643026878398637> Reserved Trailblaze Power",value = f"{data.current_reserve_stamina}/2400\nReserve Stamina Currently Full!") 
            else:
                embed.add_field(name = "<:hsrreserve:1146643026878398637> Reserved Trailblaze Power",value = f"{data.current_reserve_stamina}/2400") 

            embed.add_field(name = "<:hsrdaily:1146642085366206524> Daily Training",value = f"{data.current_train_score}/{data.max_train_score} points",inline = False)
            embed.add_field(name = "<:hsrsu:1146640649895022744> Simulated Universe",value = f"{data.current_rogue_score}/{data.max_rogue_score} weekly points",inline = False)
            embed.add_field(name = "<:hsrweekly:1146642228240986112> Echo of War",value = f"{data.remaining_weekly_discounts}/{data.max_weekly_discounts} remaining",inline = False)

            if data.expeditions:
                expeditionres = ""
                for expedition in data.expeditions:
                    if expedition.status == "Ongoing":
                        completein = now + expedition.remaining_time
                        completeunix = int(completein.replace(tzinfo=datetime.timezone.utc).timestamp())
                        expeditionres += f"**{expedition.name}:** Complete <t:{completeunix}:R>\n"
                embed.add_field(name = "<:assignments:1116017691325648906> Assignments",value = expeditionres,inline = False)
            else:
                embed.add_field(name = "<:assignments:1116017691325648906> Assignments",value = "None",inline = False)
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @honkaistarrail.command(extras = {"id":"549"},help = "View forgotten hall data from this cycle or the previous one.")
    @app_commands.describe(member = "The member to check information for.",cycle = "Either the current forgotten hall period or the previous one.")
    async def forgottenhall(self,ctx,member:discord.Member = None,cycle:Literal['current','previous'] = None):
        member = member or ctx.author
        cycle = cycle or "current"
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_hsuid(member)
            if cycle == "current":
                data = await client.get_starrail_challenge(uid = uid)
            else:
                data = await client.get_starrail_challenge(uid = uid, previous = True)
            view = HallView(ctx,data,uid)
            buffer = await view.generate_default()
            file = discord.File(buffer,filename = f"{uid}hallcard.png")
            embed = discord.Embed(title = "Honkai: Star Rail Forgotten Hall Card",description = f"Season {data.season} | Start <t:{int(data.begin_time.datetime.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> | End <t:{int(data.end_time.datetime.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",color = discord.Color.random())
            embed.set_image(url = f"attachment://{uid}hallcard.png")
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        if view.children[0].options:
            message = await ctx.reply(file = file,embed = embed,view = view)
        else:
            message = await ctx.reply(file = file,embed = embed)
        view.message = message

    '''
    
    @honkaistarrail.command(extras = {"id":"550"},name = "diary")
    async def hsdiary(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_hsuid(member)
            diary = await client.get_starrail_diary(uid = uid)
            print(diary)
        await ctx.reply("done!")
    '''

    
    @honkaistarrail.command(extras = {"id": "543"},name = "authkey",help = "Set Honkai: Star Rail authkey in the bot.")
    async def hsauthkey(self,ctx):
        embed = discord.Embed(title = "Honkai: Star Rail Authkey Linking",description = "This is required to make any warp commands work! You can read more about this at </hoyolab information:999438437906124835>.",color = discord.Color.random())
        embed.add_field(name = "Getting Authkey",value = "1. Open up warp history in game.\n2. Open Windows Powershell from your start menu.\n3. Copy the script from the button 'Get Script', and paste it in the Powershell window.\n4. Click the button below, and paste the link into the dialogue box.",inline = False)
        embed.set_image(url = "https://cdn.discordapp.com/attachments/870127759526101032/1081033414486020136/ezgif.com-video-to-gif.gif")
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        view = HSAuthkeyView(ctx)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message

    @honkaistarrail.command(extras = {"id": "544"},help = "Simple embeds that can show you your warping history.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to see warp history for.")
    async def warps(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.auth_privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their warp/transaction data set to private!")
        authkey = await self.get_hauthkey(ctx,member) 
        if not authkey: return

        async with ctx.typing():
            params = urllib.parse.parse_qs(urllib.parse.urlparse(authkey).query)
            params = {key:data[0] for key,data in params.items()}
            params["gacha_id"] = "dbebc8d9fbb0d4ffa067423482ce505bc5ea"
            params["default_gacha_type"] = 11
            params["plat_type"] = "pc"
            params["region"] = "os"
            params["page"] = 1
            params["size"] = 20
            params["gacha_type"] = 11
            params["end_id"] = 0
            gacha_pulls = []
            while True:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api-os-takumi.mihoyo.com/common/gacha_record/api/getGachaLog",params = params) as resp:
                        if resp and resp.status == 200:
                            resp = await resp.json()
                        else:
                            print(f"Error! {resp.status}")
                            break
                        if len(resp.get('data',{}).get('list',[])) == 0:
                            break
                        gacha_pulls.extend(resp.get('data',{}).get('list',[]))

                        params["page"] += 1
                        params["end_id"] = resp.get('data', {}).get('list', [])[-1].get('id')
            params["default_gacha_type"] = 12
            params["gacha_type"] = 12
            params["gacha_id"] = "ceef3b655e094f3f603c57e581c98dad09b3"
            params["end_id"] = 0
            params["page"] = 1
            while True:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api-os-takumi.mihoyo.com/common/gacha_record/api/getGachaLog",params = params) as resp:
                        if resp and resp.status == 200:
                            resp = await resp.json()
                        else:
                            print(f"Error! {resp.status}")
                            break
                        if len(resp.get('data',{}).get('list',[])) == 0:
                            break
                        gacha_pulls.extend(resp.get('data',{}).get('list',[]))

                        params["page"] += 1
                        params["end_id"] = resp.get('data', {}).get('list', [])[-1].get('id')
            params["default_gacha_type"] = 1
            params["gacha_type"] = 1
            params["gacha_id"] = "ad9815cdf2308104c377aac42c7f0cdd8d"
            params["end_id"] = 0
            params["page"] = 1
            while True:
                async with aiohttp.ClientSession() as session:
                    async with session.get("https://api-os-takumi.mihoyo.com/common/gacha_record/api/getGachaLog",params = params) as resp:
                        if resp and resp.status == 200:
                            resp = await resp.json()
                        else:
                            print(f"Error! {resp.status}")
                            break
                        if len(resp.get('data',{}).get('list',[])) == 0:
                            break
                        gacha_pulls.extend(resp.get('data',{}).get('list',[]))

                        params["page"] += 1
                        params["end_id"] = resp.get('data', {}).get('list', [])[-1].get('id')
                
            stats = {"5":[],"4":[],"5Character":[],"5Light Cone":[],"4Character":[],"4Light Cone":[],"3":[],"11":[],"12":[],"1":[]}
            for pull in gacha_pulls:
                stats[str(pull["gacha_type"])].append(pull)
                stats[str(pull["rank_type"])].append(pull)
                if pull["rank_type"] != "3":
                    stats[pull["rank_type"] + pull["item_type"]].append(pull)

        embed = discord.Embed(title = f"Warp history for {member}",description = f"Looking at the past `{len(gacha_pulls)}` warps",color = discord.Color.random())
        embed.add_field(name = "Total Statistics",value = f'Total Pulls: <:specialstarrailpass:1105682773001371808> {len(gacha_pulls)}\nStellar Jade Equivalent: <:stellarjade:1105682519711563846> {len(gacha_pulls)*160}\nAverage Pity: <:starrailpass:1105682774431629342> {int(len(gacha_pulls)/len(stats["5"])) if len(stats["5"]) > 0 else "None"}',inline = False)
        embed.add_field(name = "By Rarity",value = f'5 🌟 Pulls: {len(stats["5Character"]) + len(stats["5Light Cone"])}\n<:replycont:1106010140425072650> Characters: {len(stats["5Character"])}\n<:reply:1106010100159750205> Light Cones: {len(stats["5Light Cone"])}\n4 🌟 Pulls: {len(stats["4Character"]) + len(stats["4Light Cone"])}\n<:replycont:1106010140425072650> Characters: {len(stats["4Character"])}\n<:reply:1106010100159750205> Light Cones: {len(stats["4Light Cone"])}\n3 ⭐ Pulls: {len(stats["3"])}')
        embed.add_field(name = "By Banner",value = f'Standard Banner Pulls: <:starrailpass:1105682774431629342> {len(stats["1"])}\nLimited Character Banner Pulls: <:specialstarrailpass:1105682773001371808> {len(stats["11"])}\nLimited Light Cone Banner Pulls: <:specialstarrailpass:1105682773001371808> {len(stats["12"])}')
        embed.add_field(name = "Disclaimer",value = "This data is limited to the past 6 months. Due to this, there may be inaccurate counting in warp total, pity counting, 50/50 counting, and other information.",inline = False)
        embed.set_footer(text = "Use the dropdown below to sort by banner!")
        view = WarpView(ctx,stats,member,embed)
        message = await ctx.reply(embed = embed,view = view)
        view.message = message
    
    @commands.hybrid_group(extras = {"id": "545"},help = "The command group to manage Zenless Zone Zero information.")
    async def zenless(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `zenless` to get a list of commands.")
    
    @zenless.command(extras = {"id": "546"},name = "realtimenotes",aliases = ['rtn'], help = "Get real-time notes information like battery charge.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.")
    async def zzzrealtimenotes(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            uid = await self.pull_zzzuid(member)
            data = await client.get_zzz_notes(uid)
            now = discord.utils.utcnow()
            nowunix = int(now.replace(tzinfo=datetime.timezone.utc).timestamp())
            
            embed = discord.Embed(title = f"Real Time Notes for {member}",description = f"As of <t:{nowunix}:f>\nFor Account UID: `{uid}`",color = discord.Color.random())
            if data.battery_charge.is_full:
                embed.add_field(name = "<:batterycharge:1259295700408074272> Battery Charge",value = f"{data.battery_charge.current}/{data.battery_charge.max}\nBattery Charge is currently full!",inline = False)
            else:
                batteryunix = int(data.battery_charge.full_datetime.replace(tzinfo=datetime.timezone.utc).timestamp())
                embed.add_field(name = "<:batterycharge:1259295700408074272> Battery Charge",value = f"{data.battery_charge.current}/{data.battery_charge.max}\nFull Battery Charge <t:{batteryunix}:R>",inline = False)
            
            embed.add_field(name = "<a:PB_greentick:865758752379240448> Engagement",value = f"{data.engagement.current}/{data.engagement.max} points",inline = False)
            embed.add_field(name = "<:scratch:1259298343520178286> Scratch Card Mania",value = f"{'Done' if data.scratch_card_completed else 'Not Done'}",inline = False)
            embed.add_field(name = "<:videostore:1259299105222688848> Video Store State",value = f"{'Revenue Available' if data.video_store_state == genshin.models.zzz.chronicle.notes.VideoStoreState.REVENUE_AVAILABLE else 'Waiting to Open' if data.video_store_state == genshin.models.zzz.chronicle.notes.VideoStoreState.WAITING_TO_OPEN else 'Currently Open'}",inline = False)

            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        await ctx.reply(embed = embed)
    
    @zenless.group(extras = {"id": "547"}, name = "daily",help = "Zenless Zone Zero daily check-in management.")
    async def zenlessdaily(self,ctx):
        if ctx.invoked_subcommand is None:
            raise errors.ParsingError(message = "You need to specify a subcommand!\nUse </help:1042263810091778048> and search `zenless daily` to get a list of commands.")
    
    @zenlessdaily.command(extras = {"id": "548"},name = "claim",help = "Claim the daily reward for the day.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to claim the daily for.")
    async def zenlessclaim(self,ctx,member:discord.Member = None):
        member = member or ctx.author
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            reward = await client.claim_daily_reward(game = genshin.Game.ZZZ)
            embed = discord.Embed(title = "Claimed daily reward!",description = f"Claimed {reward.amount}x{reward.name}\nRewards have been sent to your account inbox! We also have auto daily claims, check it out with </hoyolab settings:999438437906124835>",color = discord.Color.green())
            embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
            embed.set_thumbnail(url = reward.icon)
        await ctx.reply(embed = embed)
    
    @zenlessdaily.command(extras = {"id": "549"},name = "history",help = "Last 30 daily reward history information.")
    @commands.cooldown(1,30,commands.BucketType.user)
    @app_commands.describe(member = "The member to check information for.",limit = "The amount of days to pull up inforamtion for.")
    async def zenlesshistory(self,ctx,limit: commands.Range[int,0] = None,member:discord.Member = None):
        member = member or ctx.author
        limit = limit or 30
        if not await self.privacy_check(ctx,member):
            raise errors.AccessError(message = "This user has their data set to private!")
        data = await self.get_cookies(ctx,member) 
        if not data: return
        async with ctx.typing():
            client = genshin.Client(data)
            data = []
            async for reward in client.claimed_rewards(limit = limit,game = genshin.Game.ZZZ):
                data.append(reward)
            formatter = DailyClaimPageSource(data,self.client)
            menu = classes.MenuPages(formatter)
        await menu.start(ctx)

class SettingsView(discord.ui.View):
    def __init__(self,ctx):
        super().__init__(timeout = 60)
        self.ctx = ctx
        self.message = None
        self.add_item(PrivacySelect())
        self.add_item(AutoSelect())
    
    async def generate_embed(self,data):
        data = data or {}
        cookies = "Setup: "
        if methods.query(data = data,search = ["hoyoverse","settings","ltuid"]):
            cookies += "V1 "
        if methods.query(data = data,search = ["hoyoverse","settings","ltuid2"]):
            cookies += "V2 "
        uid = methods.query(data = data,search = ["hoyoverse","settings","uid"])
        huid = methods.query(data = data,search = ["hoyoverse","settings","huid"])
        hsuid = methods.query(data = data,search = ["hoyoverse","settings","hsuid"])
        zzzuid = methods.query(data = data,search = ["hoyoverse","settings","zzzuid"])
        privacy = methods.query(data = data,search = ["hoyoverse","settings","privacy"])
        aprivacy = methods.query(data = data,search = ["hoyoverse","settings","aprivacy"])
        #autoredeem = methods.query(data = data,search = ["hoyoverse","settings","autoredeem"])
        autoclaim = methods.query(data = data,search = ["hoyoverse","settings","autoclaim"])
        hautoclaim = methods.query(data = data,search = ["hoyoverse","settings","hautoclaim"])
        #hsautoredeem = methods.query(data = data,search = ["hoyoverse","settings","hsautoredeem"])
        hsautoclaim = methods.query(data = data,search = ["hoyoverse","settings","hsautoclaim"])
        zzzautoclaim = methods.query(data = data,search = ["hoyoverse","settings","zzzautoclaim"])
        embed = discord.Embed(title = "Hoyoverse User Settings",description = "To setup cookies, use </hoyolab link:999438437906124835>\nTo setup authkey, use </genshin authkey:999438437906124836> and/or </honkaistarrail authkey:1101694558842126426>",color = discord.Color.random())
        embed.add_field(name = "Cookies Type",value = cookies)
        embed.add_field(name = "Genshin UID",value = str(uid))
        embed.add_field(name = "Honkai Impact 3rd UID",value = str(huid))
        embed.add_field(name = "Honkai: Star Rail UID",value = str(hsuid))
        embed.add_field(name = "Zenless Zone Zero UID",value = str(zzzuid))
        embed.add_field(name = "General Privacy",value = "Public" if privacy else "Private")
        embed.add_field(name = "Authkey Privacy",value = "Public" if aprivacy else "Private")
        #embed.add_field(name = "Genshin Auto Code Redeem",value = "Enabled" if autoredeem else "Disabled")
        embed.add_field(name = "Genshin Auto Daily Claim",value = "Enabled" if autoclaim else "Disabled")
        embed.add_field(name = "Honkai Impact 3rd Auto Daily Claim",value = "Enabled" if hautoclaim else "Disabled")
        #embed.add_field(name = "Honkai: Star Rail Auto Code Redeem",value = "Enabled" if hsautoredeem else "Disabled")
        embed.add_field(name = "Honkai: Star Rail Auto Daily Claim",value = "Enabled" if hsautoclaim else "Disabled")
        embed.add_field(name = "Zenless Zone Zero Auto Daily Claim",value = "Enabled" if zzzautoclaim else "Disabled")
        embed.set_footer(text = "Use the dropdowns to configure settings. | You can see your linked game accounts with /hoyolab accounts")
        return embed
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    @discord.ui.button(label = "Genshin UID")
    async def enteruid(self,interaction,button):
        await interaction.response.send_modal(EditUID("hoyoverse.settings.uid",self))
    
    @discord.ui.button(label = "Honkai Impact 3rd UID")
    async def enterhuid(self,interaction,button):
        await interaction.response.send_modal(EditUID("hoyoverse.settings.huid",self))
    
    @discord.ui.button(label = "Honkai: Star Rail UID")
    async def enterhsuid(self,interaction,button):
        await interaction.response.send_modal(EditUID("hoyoverse.settings.hsuid",self))
    
    @discord.ui.button(label = "Zenless Zone Zero UID")
    async def enterzzzuid(self,interaction,button):
        await interaction.response.send_modal(EditUID("hoyoverse.settings.zzzuid",self))

class PrivacySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label = "General Privacy",description = "Sets visibility of most commands, like abyss or real time notes.",value = "hoyoverse.settings.privacy"),
            discord.SelectOption(label = "Authkey Privacy",description = "Sets your wishing/transaction data visibility.",value = "hoyoverse.settings.aprivacy")
        ]
        super().__init__(placeholder = "Toggle Privacies",options = options)
    
    async def callback(self,interaction):
        interaction.client.db.user_data.update_one({"_id":interaction.user.id},[{"$set":{self.values[0]:{"$eq":[False,f"${self.values[0]}"]}}}],upsert = True)
        embed = await self.view.generate_embed(interaction.client.db.user_data.find_one({"_id":interaction.user.id},{"hoyoverse.settings":1}))
        await interaction.response.edit_message(embed = embed)

class AutoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            #discord.SelectOption(label = "Genshin Auto Code Redeem",description = "Redeems Genshin redemption codes automatically.",value = "hoyoverse.settings.autoredeem"),
            discord.SelectOption(label = "Genshin Daily Claim",description = "Claim the HoYoLab check-in rewards automatically.",value = "hoyoverse.settings.autoclaim"),
            discord.SelectOption(label = "Honkai Impact 3rd Daily Claim",description = "Claim the HoYoLab check-in rewards automatically.",value = "hoyoverse.settings.hautoclaim"),
            #discord.SelectOption(label = "Honkai: Star Rail Auto Code Redeem",description = "Redeems Honkai: Star Rail redemption codes automatically.",value = "hoyoverse.settings.hsautoredeem"),
            discord.SelectOption(label = "Honkai: Star Rail Daily Claim",description = "Claim the HoYoLab check-in rewards automatically.",value = "hoyoverse.settings.hsautoclaim"),
            discord.SelectOption(label = "Zenless Zone Zero Daily Claim",description = "Claim the HoYoLab check-in rewards automatically.",value = "hoyoverse.settings.zzzautoclaim"),
        ]
        super().__init__(placeholder = "Toggle Auto Features",options = options)
    
    async def callback(self,interaction):
        if not methods.query(data = interaction.client.db.user_data.find_one({"_id":interaction.user.id},{"hoyoverse.settings.ltuid":1}) or {},search = ["hoyoverse","settings","ltuid"]) and not methods.query(data = interaction.client.db.user_data.find_one({"_id":interaction.user.id},{"hoyoverse.settings.ltuid2":1}) or {},search = ["hoyoverse","settings","ltuid2"]):
            return await interaction.response.send_message(embed = discord.Embed(description = "You need to setup your cookie data first!\n</hoyolab link:999438437906124835> to get started.",color = discord.Color.red()),ephemeral = True)
        interaction.client.db.user_data.update_one({"_id":interaction.user.id},[{"$set":{self.values[0]:{"$eq":[False,f"${self.values[0]}"]}}}],upsert = True)
        embed = await self.view.generate_embed(interaction.client.db.user_data.find_one({"_id":interaction.user.id},{"hoyoverse.settings":1}))
        await interaction.response.edit_message(embed = embed)

class EditUID(discord.ui.Modal,title = "In-Game UID Setup"):
    def __init__(self,key,view):
        super().__init__()
        self.view = view
        self.key = key

    uid = discord.ui.TextInput(label = "UID",placeholder="The account UID you want to use",max_length = 10)

    async def on_submit(self, interaction: discord.Interaction):
        if self.uid.value.isnumeric():
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{self.key:int(self.uid.value)}})
            embed = await self.view.generate_embed(interaction.client.db.user_data.find_one({"_id":interaction.user.id},{"hoyoverse.settings":1}))
            await interaction.response.edit_message(embed = embed)
        else:
            embed = discord.Embed(description = "Your UID input needs to be numeric!",color = discord.Color.red())
            await interaction.response.send_message(embed = embed,ephemeral = True)

class SuperstringAbyssSelect(discord.ui.Select):
    def __init__(self,data):
        options = []
        self.data = data
        for index,battle in enumerate(data):
            options.append(discord.SelectOption(label = f"Run #{index+1}",description = battle.end_time.strftime("%m/%d/%y"),value = index))
        super().__init__(placeholder='Battle Report', min_values=0, max_values=1, options=options,row = 0)
    
    async def callback(self, interaction: discord.Interaction):
        battle = self.data[int(self.values[0])]
        embed = discord.Embed(title = f"Superstring Abyss Cycle #{int(self.values[0]) + 1}",description = f"Ended at <t:{int(battle.end_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",color = discord.Color.random())
        embed.add_field(name = "Score",value = battle.score)
        embed.add_field(name = "Placement", value = battle.placement)
        embed.add_field(name = "Rankings",value = f"Start Rank: {battle.start_rank}\nEnd Rank: {battle.end_rank}")
        embed.add_field(name = "Trophies",value = f"Start Trophies: {battle.start_trophies}\nEnd Trophies: {battle.end_trophies}\nTrophies Gained: {battle.trophies_gained}")
        embed.add_field(name = "Lineup",value = "\n".join(["⭐ " + x.rank + ": " + x.name for x in battle.lineup]),inline = False)
        embed.add_field(name = "Elf",value = f"⭐ {battle.elf.rarity}: {battle.elf.name}" if battle.elf else "None",inline = False)
        embed.add_field(name = "Boss",value = battle.boss.name,inline = False)

        await interaction.response.edit_message(embed = embed)

class SuperstringAbyssView(discord.ui.View):
    def __init__(self,ctx,data):
        super().__init__(timeout=60)
        self.add_item(SuperstringAbyssSelect(data))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class MemorialArenaSelect(discord.ui.Select):
    def __init__(self,data):
        options = []
        self.data = data
        for index,battle in enumerate(data):
            options.append(discord.SelectOption(label = f"Cycle #{index+1}",description = battle.end_time.strftime("%m/%d/%y"),value = index))
        super().__init__(placeholder='Battle Report', min_values=0, max_values=1, options=options,row = 0)
    
    async def callback(self, interaction: discord.Interaction):
        battle = self.data[int(self.values[0])]
        embed = discord.Embed(title = f"Memorial Arena Cycle #{int(self.values[0]) + 1}",description = f"Ended at <t:{int(battle.end_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",color = discord.Color.random())
        embed.add_field(name = "Score",value = battle.score)
        embed.add_field(name = "Rank",value = f"{battle.rank} ({battle.ranking}%)")
        embed.add_field(name = "Tier",value = battle.tier)
        
        for info in battle.battle_data:
            lineup = '\n'.join(['⭐ ' + x.rank + ': ' + x.name for x in info.lineup])
            embed.add_field(name = info.boss.name,value = f"**Score:** {info.score}\n**Lineup:** \n{lineup}\n**Elf:** {'⭐ ' + info.elf.rarity + ': ' + info.elf.name if info.elf else 'None'}")

        await interaction.response.edit_message(embed = embed)

class MemorialArenaView(discord.ui.View):
    def __init__(self,ctx,data):
        super().__init__(timeout=60)
        self.add_item(MemorialArenaSelect(data))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class ElysianRealmSelect(discord.ui.Select):
    def __init__(self,data):
        options = []
        self.data = data
        for index,battle in enumerate(data):
            options.append(discord.SelectOption(label = f"Run #{index+1}",description = battle.completed_at.strftime("%m/%d/%y"),value = index))
        super().__init__(placeholder='Battle Report', min_values=0, max_values=1, options=options,row = 0)
    
    async def callback(self, interaction: discord.Interaction):
        battle = self.data[int(self.values[0])]
        embed = discord.Embed(title = f"Elysian Realm Run #{int(self.values[0]) + 1}",description = f"Completed at <t:{int(battle.completed_at.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",color = discord.Color.random())
        embed.add_field(name = "Score",value = battle.score)
        embed.add_field(name = "Difficulty",value = battle.difficulty)
        embed.add_field(name = "Remembrance Sigil",value = f"{battle.remembrance_sigil.name}")
        embed.add_field(name = "Conditions",value = "\n".join(["**" + x.name + " | Difficulty " + x.difficulty + "**\n" + x.description for x in battle.conditions]) if len(battle.conditions) > 0 else "No conditions.",inline = False)
        embed.add_field(name = "Signets",value = "\n".join([str(x.number) + ". " + x.name for x in battle.signets]) if len(battle.signets) > 0 else "No signets.",inline = False)
        embed.add_field(name = "Lineup",value = "\n".join(["⭐ " + x.rank + ": " + x.name for x in battle.lineup]),inline = False)
        embed.add_field(name = "Elf",value = f"⭐ {battle.elf.rarity}: {battle.elf.name}" if battle.elf else "None",inline = False)
        await interaction.response.edit_message(embed = embed)

class ElysianRealmView(discord.ui.View):
    def __init__(self,ctx,data):
        super().__init__(timeout=60)
        self.add_item(ElysianRealmSelect(data))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class OldAbyssSelect(discord.ui.Select):
    def __init__(self,data):
        options = []
        self.data = data
        for index,battle in enumerate(data):
            options.append(discord.SelectOption(label = f"{battle.type} Report",description = f"{battle.raw_type} | Rank: {battle.rank}",value = index))
        super().__init__(placeholder='Battle Report', min_values=0, max_values=1, options=options,row = 0)
    
    async def callback(self, interaction: discord.Interaction):
        battle = self.data[int(self.values[0])]
        embed = discord.Embed(title = f"{battle.type} Report",description = f"{battle.raw_type} | Rank: {battle.rank}",color = discord.Color.random())
        embed.add_field(name = "Score",value = battle.score)
        embed.add_field(name = "Lineup",value = "\n".join(["⭐ " + x.rank + ": " + x.name for x in battle.lineup]),inline = False)
        embed.add_field(name = "Elf",value = f"⭐ {battle.elf.rarity}: {battle.elf.name}" if battle.elf else "None",inline = False)
        embed.add_field(name = "Boss",value = battle.boss.name,inline = False)
        embed.add_field(name = "Ended At:",value = f"<t:{int(battle.end_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",inline = False)
        await interaction.response.edit_message(embed = embed)

class OldAbyssView(discord.ui.View):
    def __init__(self,ctx,data):
        super().__init__(timeout=60)
        self.add_item(OldAbyssSelect(data))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class BattlesuitSelect(discord.ui.Select):
    def __init__(self,battlesuits):
        options = []
        self.colors = {"PSY":discord.Color.from_rgb(255,70,200),"MECH":discord.Color.from_rgb(54,221,251),"BIO":discord.Color.from_rgb(251,176,49),"QUA":discord.Color.from_rgb(130,113,249),"IMG":discord.Color.from_rgb(233,217,178)}
        self.battlesuits = battlesuits
        for index,battlesuit in enumerate(battlesuits):
            options.append(discord.SelectOption(label = battlesuit.name,description = f"{battlesuit.rank} ⭐ | Level {battlesuit.level}",value = index))
        super().__init__(placeholder='Character Selection', min_values=0, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        battlesuit = self.battlesuits[int(self.values[0])]
        embed = discord.Embed(title = battlesuit.name,description = f"⭐ {battlesuit.rank} | Type: {battlesuit.type} | Level {battlesuit.level}",color = self.colors[battlesuit.type])
        embed.add_field(name = f"Weapon ({battlesuit.weapon.type}): {battlesuit.weapon.name}", value = f"⭐ {battlesuit.weapon.rarity}/{battlesuit.weapon.max_rarity}",inline = False)
        
        if len(battlesuit.stigmata) > 0:
            embed.add_field(name = "Stigmata", value = "\n".join([x.name + "⭐ " + str(x.rarity) + "/" + str(x.max_rarity) for x in battlesuit.stigmata]))
        else:
            embed.add_field(name = "Stigmata",value = "No stigmata applied.")

        embed.set_thumbnail(url = battlesuit.icon)
        await interaction.response.edit_message(embed = embed)

class BattlesuitView(discord.ui.View):
    def __init__(self,ctx,data):
        super().__init__(timeout=60)
        for i in range(0,len(data),25):
            self.add_item(BattlesuitSelect(data[i:min(i+25,len(data))]))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class EnkaCharacterSelect(discord.ui.Select):
    def __init__(self,images):
        options = []
        for character in images:
            options.append(discord.SelectOption(label = character,value = character))
        self.images = images
        super().__init__(placeholder='Character Selection', min_values=0, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        image = self.images[self.values[0]]['img']

        buffer = BytesIO()
        image.save(buffer,"png")
        buffer.seek(0)

        file = discord.File(buffer,filename = f"enkacharacercard.png")
        embed = discord.Embed(title = "Enka Network Character Card",color = discord.Color.random())
        embed.set_image(url = f"attachment://enkacharacercard.png")
        embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
        await interaction.response.edit_message(attachments = [file],embed = embed)

class EnkaCharacterView(discord.ui.View):
    def __init__(self,ctx,data):
        super().__init__(timeout=60)
        if len(data) > 0:
            self.add_item(EnkaCharacterSelect(data))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class WishSelect(discord.ui.Select):
    def __init__(self,wishes,member,default):
        options = [
            discord.SelectOption(emoji = "🌟", label = "Wish Overview", value = "o"),
            discord.SelectOption(emoji = "<:intertwined:990336430934999040>", label = "Limited Character Banner", value = "c"),
            discord.SelectOption(emoji = "<:intertwined:990336430934999040>", label = "Limited Weapon Banner",value = "w"),
            discord.SelectOption(emoji = "<:acquaint:990336486723432490>", label = "Standard Banner",value = "s"),
            discord.SelectOption(emoji = "<:acquaint:990336486723432490>", label = "Novice Banner",value = "n")
        ]
        self.wishes = wishes
        self.default = default
        self.member = member
        self.names = {"c":"Limited Character Banner","w":"Limited Weapon Banner","s":"Standard Banner","n":"Novice Banner"}
        super().__init__(placeholder='Banner Selection', min_values=0, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "o":
            return await interaction.response.edit_message(embed = self.default)
        stats = {"5":[],"4":[],"3":[],"Pity5":[],"Win50":0,"Lose50":0,"Guaran50":0}
        banner = self.wishes[self.values[0]]
        fivepity = 0
        fourpity = 0
        guaranteed = False
        for wish in banner[::-1]:
            if wish.rarity == 5:
                if self.values[0] == "c":
                    if wish.name in ['Diluc','Mona','Keqing','Qiqi','Jean'] or (wish.name == "Tighnari" and wish.time > datetime.datetime(year = 2022, month = 9, day = 27, hour = 18, tzinfo = datetime.timezone.utc)) or (wish.name == "Dehya" and wish.time > datetime.datetime(year = 2023, month = 4, day = 12, hour = 18, tzinfo = datetime.timezone.utc)):
                        stats["Lose50"] += 1
                        guaranteed = True
                    elif guaranteed:
                        stats["Guaran50"] += 1
                        guaranteed = False
                    else:
                        stats["Win50"] += 1
                stats["5"].append(wish)
                stats["Pity5"].append([wish,fivepity])
                fivepity = 0
                fourpity += 1
            elif wish.rarity == 4:
                stats["4"].append(wish)
                fivepity += 1
                fourpity = 0
            else:
                stats["3"].append(wish)
                fivepity += 1
                fourpity += 1
        embed = discord.Embed(title = f"{self.names[self.values[0]]} Wishes for {self.member}",description = f"Looking at the past `{len(banner)}` wishes",color = discord.Color.random())
        embed.set_footer(text = "Use the dropdown below to sort by banner!")
        if len(banner) < 1:
            embed.add_field(name = "No wishes found!",value = "I did not find any wishes on this banner for this user!")
            await interaction.response.edit_message(embed = embed)
            return
        embed.add_field(name = "Total Statistics",value = f"Total Pulls: {len(banner)} <:intertwined:990336430934999040>\nPrimogem Equivalent: {len(banner)*160} <:primogem:990335900280041472>\nAverage Pity: {int((len(banner)-fivepity)/len(stats['5'])) if len(stats['5']) > 0 else 'None'} <:acquaint:990336486723432490>",inline = False)
        embed.add_field(name = "By Rarity",value = f'5 🌟 Pulls: {len(stats["5"])}\n4 🌟 Pulls: {len(stats["4"])}\n3 ⭐ Pulls: {len(stats["3"])}')
        embed.add_field(name = "Recent Statistics",value = f'Last 5 🌟: {stats["5"][-1].name if len(stats["5"]) > 0 else "None"}\nLast 4 🌟: {stats["4"][-1].name if len(stats["4"]) > 0 else "None"}\nLast 3 ⭐: {stats["3"][-1].name if len(stats["3"]) > 0 else "None"}')
        if self.values[0] == "c" or self.values[0] == "s":
            embed.add_field(name = "Current Pity",value = f"5 🌟 Pity: {fivepity} ({90-fivepity} to guaranteed)\n4 🌟 Pity: {fourpity} ({10-fourpity} to guaranteed)",inline = False)
        elif self.values[0] == "w":
            embed.add_field(name = "Current Pity",value = f"5 🌟 Pity: {fivepity} ({80-fivepity} to guaranteed)\n4 🌟 Pity: {fourpity} ({10-fourpity} to guaranteed)",inline = False)
        embed.add_field(name = "20 Most Recent 5-Star Pity Count",value = " | ".join([x[0].name + ": `" + str(x[1] + 1) + "`" for x in stats['Pity5'][:-21:-1]]) if len(stats['Pity5']) > 0 else "No recent 5-stars.",inline = False)
        
        if self.values[0] == "c":
            embed.add_field(name = "50/50 Statistics", value = f"50/50 Won: {stats['Win50']} ({round(stats['Win50']/(stats['Lose50'] + stats['Win50']) * 100,2)}%)\n50/50 Lost: {stats['Lose50']} ({round(stats['Lose50']/(stats['Lose50'] + stats['Win50']) * 100,2)}%)\nGuaranteed: {stats['Guaran50']}\n{'You are currently on a guaranteed 5 🌟' if guaranteed else 'You are currently on a 50/50 5 🌟'}")

        await interaction.response.edit_message(embed = embed)

class WishView(discord.ui.View):
    def __init__(self,ctx,data,member,default):
        super().__init__(timeout=300)
        self.add_item(WishSelect(data,member,default))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class WarpView(discord.ui.View):
    def __init__(self,ctx,data,member,default):
        super().__init__(timeout=300)
        self.add_item(WarpSelect(data,member,default))
        self.message = None
        self.ctx = ctx
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class WarpSelect(discord.ui.Select):
    def __init__(self,warps,member,default):
        options = [
            discord.SelectOption(emoji = "<:stellarjade:1105682519711563846>", label = "Wish Overview", value = "o"),
            discord.SelectOption(emoji = "<:specialstarrailpass:1105682773001371808>", label = "Limited Character Banner", value = "11"),
            discord.SelectOption(emoji = "<:specialstarrailpass:1105682773001371808>", label = "Limited Light Cone Banner",value = "12"),
            discord.SelectOption(emoji = "<:starrailpass:1105682774431629342>", label = "Standard Banner",value = "1"),
        ]
        self.warps = warps
        self.default = default
        self.member = member
        self.names = {"11":"Limited Character Banner","12":"Limited Light Cone Banner","1":"Standard Banner"}
        super().__init__(placeholder='Banner Selection', min_values=0, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "o":
            return await interaction.response.edit_message(embed = self.default)
        stats = {"5":[],"4":[],"5Character":[],"5Light Cone":[],"4Character":[],"4Light Cone":[],"3":[],"Pity5":[],"Win50":0,"Lose50":0,"Guaran50":0}
        banner = self.warps[self.values[0]]
        fivepity = 0
        fourpity = 0
        guaranteed = False
        for warp in banner[::-1]:
            if warp["rank_type"] == "5":
                if self.values[0] == "11":
                    if warp["name"] in ['Himeko','Welt','Bronya','Gepard','Clara','Yanqing','Bailu']:
                        stats["Lose50"] += 1
                        guaranteed = True
                    elif guaranteed:
                        stats["Guaran50"] += 1
                        guaranteed = False
                    else:
                        stats["Win50"] += 1
                stats["5"].append(warp)
                stats["5" + warp["item_type"]].append(warp)
                stats["Pity5"].append([warp,fivepity])
                fivepity = 0
                fourpity += 1
            elif warp["rank_type"] == "4":
                stats["4"].append(warp)
                stats["4" + warp["item_type"]].append(warp)
                fivepity += 1
                fourpity = 0
            else:
                stats["3"].append(warp)
                fivepity += 1
                fourpity += 1
        embed = discord.Embed(title = f"{self.names[self.values[0]]} Warps for {self.member}",description = f"Looking at the past `{len(banner)}` Warps",color = discord.Color.random())
        embed.set_footer(text = "Use the dropdown below to sort by banner!")
        if len(banner) < 1:
            embed.add_field(name = "No wishes found!",value = "I did not find any wishes on this banner for this user!")
            await interaction.response.edit_message(embed = embed)
            return
        embed.add_field(name = "Total Statistics",value = f"Total Warps: {len(banner)} <:specialstarrailpass:1105682773001371808>\nStellar Jade Equivalent: {len(banner)*160} <:stellarjade:1105682519711563846>\nAverage Pity: {int((len(banner)-fivepity)/len(stats['5'])) if len(stats['5']) > 0 else 'None'} <:starrailpass:1105682774431629342>",inline = False)
        embed.add_field(name = "By Rarity",value = f'5 🌟 Pulls: {len(stats["5Character"]) + len(stats["5Light Cone"])}\n<:replycont:1106010140425072650> Characters: {len(stats["5Character"])}\n<:reply:1106010100159750205> Light Cones: {len(stats["5Light Cone"])}\n4 🌟 Pulls: {len(stats["4Character"]) + len(stats["4Light Cone"])}\n<:replycont:1106010140425072650> Characters: {len(stats["4Character"])}\n<:reply:1106010100159750205> Light Cones: {len(stats["4Light Cone"])}\n3 ⭐ Pulls: {len(stats["3"])}')
        embed.add_field(name = "Recent Statistics",value = f'Last 5 🌟: {stats["5"][-1]["name"] if len(stats["5"]) > 0 else "None"}\nLast 4 🌟: {stats["4"][-1]["name"] if len(stats["4"]) > 0 else "None"}\nLast 3 ⭐: {stats["3"][-1]["name"] if len(stats["3"]) > 0 else "None"}')
        if self.values[0] == "11" or self.values[0] == "1":
            embed.add_field(name = "Current Pity",value = f"5 🌟 Pity: {fivepity} ({90-fivepity} to guaranteed)\n4 🌟 Pity: {fourpity} ({10-fourpity} to guaranteed)",inline = False)
        elif self.values[0] == "12":
            embed.add_field(name = "Current Pity",value = f"5 🌟 Pity: {fivepity} ({80-fivepity} to guaranteed)\n4 🌟 Pity: {fourpity} ({10-fourpity} to guaranteed)",inline = False)
        embed.add_field(name = "20 Most Recent 5-Star Pity Count",value = " | ".join([x[0]["name"] + ": `" + str(x[1] + 1) + "`" for x in stats['Pity5'][:-21:-1]]) if len(stats['Pity5']) > 0 else "No recent 5-stars.",inline = False)
        
        if self.values[0] == "11":
            embed.add_field(name = "50/50 Statistics", value = f"50/50 Won: {stats['Win50']} ({round(stats['Win50']/(stats['Lose50'] + stats['Win50']) * 100,2)}%)\n50/50 Lost: {stats['Lose50']} ({round(stats['Lose50']/(stats['Lose50'] + stats['Win50']) * 100,2)}%)\nGuaranteed: {stats['Guaran50']}\n{'You are currently on a guaranteed 5 🌟' if guaranteed else 'You are currently on a 50/50 5 🌟'}")

        await interaction.response.edit_message(embed = embed)

class CharacterSelect(discord.ui.Select):
    def __init__(self,characters):
        self.colors = {"Electro":discord.Color.from_rgb(162,83,198),"Hydro":discord.Color.from_rgb(74,188,233),"Pyro":discord.Color.from_rgb(232,117,54),"Cryo":discord.Color.from_rgb(154,207,220),"Geo":discord.Color.from_rgb(242,176,48),"Anemo":discord.Color.from_rgb(112,188,163),"Dendro":discord.Color.from_rgb(160,194,57)}
        options = []
        self.characters = characters
        for index,character in enumerate(characters):
            options.append(discord.SelectOption(label = character.name,description = f"{character.rarity} ⭐ | Level {character.level}",value = index))

        super().__init__(placeholder='Character Selection', min_values=0, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        character = self.characters[int(self.values[0])]
        back = Image.open("./pillow/staticassets/characterback.png")
        mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
        mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
        copy = back.copy()
        draw = Image.new("RGBA",copy.size)
        upper = Image.new("RGBA",copy.size)
        copy_editable = ImageDraw.Draw(draw)
        uidtext = f"UID: {self.view.uid}"
        copy_editable.text((20,20),f"{character.name} | Level {character.level} | Friendship {character.friendship}",(255,255,255),font = pillow.title_font)
        _,_,w,h = copy_editable.textbbox((0,0),uidtext,font = pillow.title_font)
        copy_editable.text((copy.width-w-20,20),uidtext,font = pillow.title_font)

        if os.path.exists(f"./pillow/dynamicassets/{character.image.split('/')[-1]}"):
            characterimage = Image.open(f"./pillow/dynamicassets/{character.image.split('/')[-1]}")
        else:
            characterimage = Image.open(urlopen(character.image)).convert('RGBA')
            characterimage.save(f"./pillow/dynamicassets/{character.image.split('/')[-1]}")
        characterresized = characterimage.resize((characterimage.width//4,characterimage.height//4))
        copy.paste(characterresized,(20,h+ 40),characterresized)

        currenth = 40 + h
        lock = Image.open("./pillow/staticassets/lock.png").convert('RGBA')
        lockresized = lock.resize((20,20))
        for constellation in character.constellations:
            if os.path.exists(f"./pillow/dynamicassets/{constellation.icon.split('/')[-1]}"):
                constellationimage = Image.open(f"./pillow/dynamicassets/{constellation.icon.split('/')[-1]}")
            else:
                constellationimage = Image.open(urlopen(constellation.icon)).convert('RGBA')
                constellationimage.save(f"./pillow/dynamicassets/{constellation.icon.split('/')[-1]}")
            constellationresized = constellationimage.resize((40,40))
            copy_editable.ellipse((20 + characterresized.width,currenth,20 + characterresized.width + 40,currenth+40),fill = (36,37,38))
            upper.paste(constellationresized,(20+characterresized.width,currenth),constellationresized)
            if not constellation.activated:
                upper.paste(lockresized,(20+characterresized.width + 20 - lockresized.width//2,currenth + 20 - lockresized.height//2),lockresized)
            currenth += 50

        if os.path.exists(f"./pillow/dynamicassets/{character.weapon.icon.split('/')[-1]}"):
            weaponimage = Image.open(f"./pillow/dynamicassets/{character.weapon.icon.split('/')[-1]}")
        else:
            weaponimage = Image.open(urlopen(character.weapon.icon)).convert('RGBA')
            weaponimage.save(f"./pillow/dynamicassets/{character.weapon.icon.split('/')[-1]}")
        weaponresized = weaponimage.resize((weaponimage.width//3,weaponimage.height//3))
        
        copy.paste(weaponresized,(80 + characterresized.width,40+h),weaponresized)
        weapontext = f"Weapon ({character.weapon.type}): {character.weapon.name}\n{character.weapon.rarity} Stars\nLevel: {character.weapon.level}\nRefinement: {character.weapon.refinement}"

        copy_editable.text((80 + characterresized.width + weaponresized.width + 20,40+h),weapontext,font = pillow.subtitle_font)
        _,_,w2,h2 = copy_editable.textbbox((0,0),weapontext,font = pillow.subtitle_font)
        copy_editable.text((80 + characterresized.width + weaponresized.width + 20,40+h+h2+10),"\n".join(textwrap.wrap(character.weapon.description, width = 100)),font = pillow.small_font)

        if len(character.artifacts) > 0:
            sets = []
            width = 100 + characterresized.width
            for artifact in character.artifacts:
                if os.path.exists(f"./pillow/dynamicassets/{artifact.icon.split('/')[-1]}"):
                    artifactimage = Image.open(f"./pillow/dynamicassets/{artifact.icon.split('/')[-1]}")
                else:
                    artifactimage = Image.open(urlopen(artifact.icon)).convert('RGBA')
                    artifactimage.save(f"./pillow/dynamicassets/{artifact.icon.split('/')[-1]}")
                artifactresized = artifactimage.resize((artifactimage.width//3,artifactimage.height//3))
                copy.paste(artifactresized,(width,200),artifactresized)
                width += artifactresized.width + 20

                if artifact.set in sets:
                    continue
                sets.append(artifact.set)
            height = 300
            for set in sets:
                if set.effects[1].enabled:
                    copy_editable.text((100 + characterresized.width,height),f"{set.name}: 4 Piece",font = pillow.subtitle_font)
                    _,_,w3,h3 = copy_editable.textbbox((0,0),f"{set.name} 4 Piece",font = pillow.subtitle_font)
                    height += h3 + 10
                elif set.effects[0].enabled:
                    copy_editable.text((100 + characterresized.width,height),f"{set.name}: 2 Piece",font = pillow.subtitle_font)
                    _,_,w3,h3 = copy_editable.textbbox((0,0),f"{set.name} 2 Piece",font = pillow.subtitle_font)
                    height += h3 + 10
        else:
            pass

        credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
        _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
        copy_editable.text((20 + mafuyuresized.width,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
        copy.paste(mafuyuresized,(20,copy.height - h7 - 13),mafuyuresized)

        out = Image.alpha_composite(copy,draw)
        out = Image.alpha_composite(out,upper)

        buffer = BytesIO()
        out.save(buffer,"png")
        buffer.seek(0)

        file = discord.File(buffer,filename = f"{self.view.uid}charactercard.png")
        embed = discord.Embed(title = "Genshin Impact Character Card",color = discord.Color.random())
        embed.set_image(url = f"attachment://{self.view.uid}charactercard.png")
        embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
        await interaction.response.edit_message(attachments = [file],embed = embed)

class CharacterView(discord.ui.View):
    def __init__(self,ctx,data,uid):
        super().__init__(timeout=60)
        for i in range(0,len(data),25):
            self.add_item(CharacterSelect(data[i:min(i+25,len(data))]))
        self.message = None
        self.ctx = ctx
        self.uid = uid
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

class DailyClaimPageSource(menus.ListPageSource):
    def __init__(self, data,client):
        self.client = client
        super().__init__(data, per_page=10)

    def format_leaderboard_entry(self, no, reward):
        return f"<t:{int(reward.time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> - {reward.amount} x {reward.name}"
    
    async def format_page(self, menu, data):
        page = menu.current_page
        max_page = self.get_max_pages()
        starting_number = page * self.per_page + 1
        iterator = starmap(self.format_leaderboard_entry, enumerate(data, start=starting_number))
        page_content = "\n".join(iterator)
        embed = discord.Embed(
            title=f"Recently Daily Reward Log [{page + 1}/{max_page}]", 
            description=page_content,
            color= discord.Color.random()
        )
        embed.set_footer(icon_url = self.client.user.avatar.url, text = self.client.user.name)
        return embed

class AbyssView(ui.View):
    def __init__(self,ctx,data,uid):
        super().__init__(timeout = 120)
        self.message = None
        self.ctx = ctx
        self.uid = uid
        self.data = data
        self.add_item(AbyssSelect(data.floors if data else []))
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)

    async def generate_default(self):
        im1 = Image.open("./pillow/staticassets/abyss.png").convert('RGBA')
        goldback = Image.open("./pillow/staticassets/goldback.png").convert('RGBA')
        purpleback = Image.open("./pillow/staticassets/purpleback.png").convert('RGBA')
        star = Image.open("./pillow/staticassets/star.png").convert('RGBA')
        mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')

        title_text = f"Spiral Abyss Challenge Summary"
        star_text = f"{self.data.total_stars}/36"
        battles_text = f"Battles Fought: {self.data.total_battles}"
        descent_text = f"Deepest Descent: {self.data.max_floor}"
        subtitle1_text = "Most Played Characters"
        subtitle2_text = "Notable Stats"
        credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"

        goldbackresized = goldback.resize((64,64))
        purplebackresized = purpleback.resize((64,64))
        starresized = star.resize((star.width//15,star.height//15))
        mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))

        copy = im1.copy()
        draw = Image.new("RGBA",copy.size)
        copy_editable = ImageDraw.Draw(draw)

        _,_,w,h = copy_editable.textbbox((0,0),star_text,font = pillow.title_font)
        _,_,w2,h2 = copy_editable.textbbox((0,0),battles_text,font = pillow.subtitle_font)
        _,_,w3,h3 = copy_editable.textbbox((0,0),descent_text,font = pillow.subtitle_font)
        copy_editable.text((20,20),title_text,(255,255,255),font = pillow.title_font)
        copy_editable.text((copy.width-w-20,20),star_text,(255,255,255),font = pillow.title_font)
        copy.paste(starresized,(copy.width-starresized.width-w-25,20),starresized)
        copy_editable.text((copy.width-w-w3-starresized.width-40,10),descent_text,font = pillow.subtitle_font)
        copy_editable.text((copy.width-w-w2-starresized.width-40,13 + h3),battles_text,font = pillow.subtitle_font)

        currenth = 40 + h
        copy_editable.line(((20,currenth),(820,currenth)),(255,255,255),1)
        currenth += 22

        if self.data.total_battles < 1:
            _,_,w4,h4 = copy_editable.textbbox((0,0),"No data for this rotation!",font = pillow.subtitle_font)
            copy_editable.text(((copy.width - w4)/2,currenth),"No data for this rotation!",font = pillow.subtitle_font)
            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            return buffer

        if len(self.data.ranks.most_played) < 1:
            _,_,w4,h4 = copy_editable.textbbox((0,0),"Data is being tabulated, check back later!",font = pillow.subtitle_font)
            copy_editable.text(((copy.width - w4)/2,currenth),"Data is being tabulated, check back later!",font = pillow.subtitle_font)
            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            return buffer

        _,_,w4,h4 = copy_editable.textbbox((0,0),subtitle1_text,font = pillow.subtitle_font)
        copy_editable.text(((copy.width - w4)/2,currenth),subtitle1_text,font = pillow.subtitle_font)
        currenth += h4 + 20

        for i in range(0,len(self.data.ranks.most_played)):
            character = self.data.ranks.most_played[i]
            if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
                characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
            else:
                characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
                characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
            resized = characterimg.resize((characterimg.width//4,characterimg.height//4))
            if character.rarity == 5:
                copy.paste(goldbackresized,((copy.width)//2 -15 - 2*resized.width + (i*(10+resized.width)),currenth),goldbackresized)
            else:
                copy.paste(purplebackresized,((copy.width)//2 -15 - 2*resized.width + (i*(10+resized.width)),currenth),purplebackresized)

            copy.paste(resized,((copy.width)//2 -15 - 2*resized.width + (i*(10+resized.width)),currenth),resized)
            times_text = str(character.value)
            _,_,w4,h4 = copy_editable.textbbox((0,0),times_text,font = pillow.small_font)
            copy_editable.rectangle((((copy.width)//2 -15 - 2*resized.width + (i*(10+resized.width)),currenth + resized.height - 13),((copy.width)//2 -15 - 2*resized.width + (i*(10+resized.width)) + resized.width,currenth + resized.height)),(0,0,0,127))
            copy_editable.text(((copy.width)//2 -15 - 2*resized.width + (i*(10+resized.width)) + resized.width//2 - w4//2,currenth + resized.height - 13 + 13//2 - h4//2),times_text,font = pillow.small_font)

        currenth += resized.height + 20
        _,_,w5,h5 = copy_editable.textbbox((0,0),subtitle2_text,font = pillow.subtitle_font)
        copy_editable.text(((copy.width - w5)/2,currenth),subtitle2_text,font = pillow.subtitle_font)
        currenth += h5 + 20

        _,_,w6,h6 = copy_editable.textbbox((0,0),"Placeholder",font = pillow.small_font)
        character = self.data.ranks.most_kills[0] 
        if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
            characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        else:
            characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
            characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        resized = characterimg.resize((characterimg.width//13,characterimg.height//13))
        copy.paste(resized,(80,currenth),resized)
        copy_editable.text((90 + resized.width,currenth + (resized.height//2) - (h6//2)),f"Most Defeats: {self.data.ranks.most_kills[0].value}",font = pillow.small_font)

        character = self.data.ranks.strongest_strike[0] 
        if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
            characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        else:
            characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
            characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        resized = characterimg.resize((characterimg.width//13,characterimg.height//13))
        copy.paste(resized,(80,currenth + 1* (resized.height + 10)),resized)
        copy_editable.text((90 + resized.width,currenth + 1*(resized.height + 10) + (resized.height//2) - (h6//2)),f"Strongest Single Strike: {self.data.ranks.strongest_strike[0].value}",font = pillow.small_font)

        character = self.data.ranks.most_damage_taken[0] 
        if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
            characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        else:
            characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
            characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        resized = characterimg.resize((characterimg.width//13,characterimg.height//13))
        copy.paste(resized,(80,currenth + 2* (resized.height + 10)),resized)
        copy_editable.text((90 + resized.width,currenth + 2*(resized.height + 10) + (resized.height//2) - (h6//2)),f"Most Damage Taken: {self.data.ranks.most_damage_taken[0].value}",font = pillow.small_font)

        character = self.data.ranks.most_bursts_used[0] 
        if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
            characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        else:
            characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
            characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        resized = characterimg.resize((characterimg.width//13,characterimg.height//13))
        copy.paste(resized,(80,currenth + 3* (resized.height + 10)),resized)
        copy_editable.text((90 + resized.width,currenth + 3*(resized.height + 10) + (resized.height//2) - (h6//2)),f"Elemental Bursts Unleashed: {self.data.ranks.most_bursts_used[0].value}",font = pillow.small_font)

        character = self.data.ranks.most_skills_used[0] 
        if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
            characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        else:
            characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
            characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
        resized = characterimg.resize((characterimg.width//13,characterimg.height//13))
        copy.paste(resized,(80,currenth + 4* (resized.height + 10)),resized)
        copy_editable.text((90 + resized.width,currenth + 4*(resized.height + 10) + (resized.height//2) - (h6//2)),f"Elemental Skills Cast: {self.data.ranks.most_skills_used[0].value}",font = pillow.small_font)

        _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
        copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 10),credits_text,font = pillow.credits_font)
        copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 13),mafuyuresized)

        out = Image.alpha_composite(copy,draw)
        buffer = BytesIO()
        out.save(buffer,"png")
        buffer.seek(0)
        return buffer
    
class AbyssSelect(ui.Select):
    def __init__(self,floors):
        options = [discord.SelectOption(label = "Overview",description = "Floor wide data",value = -1)]
        self.floors = floors
        for index, floor in enumerate(floors):
            options.append(discord.SelectOption(label = f"Spiral Abyss {floor.floor}",description = f"{floor.stars}/{floor.max_stars} Stars",value = index))
        super().__init__(placeholder = "Abyss Floor", min_values = 0, max_values = 1, options = options, row = 0)
    
    async def callback(self, interaction):
        if int(self.values[0]) == -1:
            buffer = await self.view.generate_default()
            file = discord.File(buffer,filename = f"{self.view.uid}abysscard.png")
            embed = discord.Embed(title = "Genshin Impact Abyss Card",description = f"Season {self.view.data.season} | Start <t:{int(self.view.data.start_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> | End <t:{int(self.view.data.end_time.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",color = discord.Color.random())
            embed.set_image(url = f"attachment://{self.view.uid}abysscard.png")
            embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
            await interaction.response.edit_message(attachments = [file],embed = embed)
            return
        
        floor = self.floors[int(self.values[0])]
        im1 = Image.open("./pillow/staticassets/abyss.png").convert('RGBA')
        goldback = Image.open("./pillow/staticassets/goldback.png").convert('RGBA')
        purpleback = Image.open("./pillow/staticassets/purpleback.png").convert('RGBA')
        star = Image.open("./pillow/staticassets/star.png").convert('RGBA')
        mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')

        title_text = f"Spiral Abyss Floor {floor.floor}"
        star_text = f"{floor.stars}/{floor.max_stars}"
        level_text = "Level"
        chamber_text = "Chamber"
        credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"

        goldbackresized = goldback.resize((64,64))
        purplebackresized = purpleback.resize((64,64))
        starresized = star.resize((star.width//15,star.height//15))
        mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))

        copy = im1.copy()
        draw = Image.new("RGBA",copy.size)
        copy_editable = ImageDraw.Draw(draw)

        _,_,w,h = copy_editable.textbbox((0,0),star_text,font = pillow.title_font)
        _,_,w2,h2 = copy_editable.textbbox((0,0),chamber_text,font = pillow.small_font)
        copy_editable.text((20,20),title_text,(255,255,255),font = pillow.title_font)
        copy_editable.text((copy.width-w-20,20),star_text,(255,255,255),font = pillow.title_font)
        copy.paste(starresized,(copy.width-starresized.width-w-25,20),starresized)
        currenth = 40 + h
        for k in range(0,len(floor.chambers)):
            chamber = floor.chambers[k]
            chamber_text = f"Chamber {chamber.chamber} {chamber.battles[0].timestamp.strftime('%A, %B %d, %Y %I:%M %p')}"
            copy_editable.line(((20,currenth),(820,currenth)),(255,255,255),2)
            currenth += 12
            copy_editable.text((20,currenth),chamber_text,(255,255,255),font = pillow.small_font)
            currenth += h2
            for i in range(0,len(chamber.battles[0].characters)):
                character = chamber.battles[0].characters[i]
                if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
                    characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                else:
                    characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
                    characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                resized = characterimg.resize((characterimg.width//4,characterimg.height//4))
                if character.rarity == 5:
                    copy.paste(goldbackresized,(20+((10+resized.width)*i),currenth + 10),goldbackresized)
                else:
                    copy.paste(purplebackresized,(20+((10+resized.width)*i),currenth + 10),purplebackresized)
                copy.paste(resized,(20+((10+resized.width)*i),currenth + 10),resized)
                level_text = f"Level {character.level}"
                _,_,w3,h3 = copy_editable.textbbox((0,0),level_text,font = pillow.small_font)
                copy_editable.rectangle(((20+((10+resized.width)*i),currenth + 10 + resized.height - 13),(20+((10+resized.width)*i) + resized.width,currenth + 10 + resized.height)),(0,0,0,127))
                copy_editable.text((20+((10+resized.width)*i) + resized.width//2 - w3//2,currenth + 10 + resized.height - 13 + 13//2 - h3//2),level_text,font = pillow.small_font)
            for i in range(0,len(chamber.battles[0].characters)):
                character = chamber.battles[1].characters[len(chamber.battles[0].characters)-1-i]
                if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
                    characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                else:
                    characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
                    characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                resized = characterimg.resize((characterimg.width//4,characterimg.height//4))
                if character.rarity == 5:
                    copy.paste(goldbackresized,(copy.width-resized.width-20-((10+resized.width)*i),currenth + 10),goldbackresized)
                else:
                    copy.paste(purplebackresized,(copy.width-resized.width-20-((10+resized.width)*i),currenth + 10),purplebackresized)
                copy.paste(resized,(copy.width-resized.width-20-((10+resized.width)*i),currenth + 10),resized)
                level_text = f"Level {character.level}"
                _,_,w3,h3 = copy_editable.textbbox((0,0),level_text,font = pillow.small_font)
                copy_editable.rectangle(((copy.width-resized.width-20-((10+resized.width)*i),currenth + 10 + resized.height - 13),(copy.width-resized.width-20-((10+resized.width)*i) + resized.width,currenth + 10 + resized.height)),(0,0,0,127))
                copy_editable.text((copy.width-resized.width-20-((10+resized.width)*i) + resized.width//2 - w3//2,currenth + 10 + resized.height - 13 + 13//2 - h3//2),level_text,font = pillow.small_font)
                
            starx = (((20 + 4* (10 + resized.width))+ (copy.width-20-4*(10 + resized.width)))//2) - int(1.5 * starresized.width)
            for i in range(0,chamber.stars):
                copy.paste(starresized,(starx + (starresized.width * i),currenth + (resized.height//2)),starresized)
            
            currenth += resized.height + 20

        copy_editable.line(((20,currenth),(820,currenth)),(255,255,255),2)

        _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
        copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 1),credits_text,font = pillow.credits_font)
        copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 4),mafuyuresized)

        out = Image.alpha_composite(copy,draw)
        buffer = BytesIO()
        out.save(buffer,"png")
        buffer.seek(0)
        file = discord.File(buffer,filename = f"{self.view.uid}abysscard.png")
        embed = discord.Embed(title = "Genshin Impact Abyss Card",color = discord.Color.random())
        embed.set_image(url = f"attachment://{self.view.uid}abysscard.png")
        embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
        await interaction.response.edit_message(attachments = [file],embed = embed)

class StatsView(ui.View):
    def __init__(self,ctx,data,uid):
        super().__init__(timeout = 120)
        self.message = None
        self.ctx = ctx
        self.uid = uid
        self.data = data
        self.add_item(StatsSelect())
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    async def generate_default(self):
        back = Image.open("./pillow/staticassets/fading.png")
        mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
        mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
        copy = back.copy()
        draw = Image.new("RGBA",copy.size)
        copy_editable = ImageDraw.Draw(draw)
        uidtext = f"UID: {self.uid}"
        copy_editable.text((20,20),"User Statistics",(255,255,255),font = pillow.title_font)
        _,_,w,h = copy_editable.textbbox((0,0),uidtext,font = pillow.title_font)
        copy_editable.text((copy.width-w-20,20),uidtext,font = pillow.title_font)
        copy_editable.line(((20,40+h),(820,40+h)),(255,255,255),1)
        currenth = 40 + h + 21
        count = 0
        width = 20

        for stat,value in self.data.stats.as_dict().items():
            value = str(value)
            stat = stat.title()
            stat = textwrap.wrap(stat, width = 15)
            width += 133
            _,_,w3,h3 = copy_editable.textbbox((0,0),value,font = pillow.title_font)
            copy_editable.text((width - (w3/2),currenth),value,font = pillow.title_font,stroke_width = 1, stroke_fill = (0,0,0))
            lineh = currenth + h3 + 5
            for line in stat:
                _,_,w2,h2 = copy_editable.textbbox((0,0),line,font = pillow.subtitle_font)
                copy_editable.text((width - (w2/2),lineh),line,font = pillow.subtitle_font,stroke_width = 1, stroke_fill = (0,0,0))
                lineh += h2 + 10
            if count % 5 == 4:
                currenth += 100
                width = 20
            count += 1
        
        copy_editable.line(((20,copy.height-40),(820,copy.height-40)),(255,255,255),1)

        credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
        _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
        copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
        copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 13),mafuyuresized)

        out = Image.alpha_composite(copy,draw)
        buffer = BytesIO()
        out.save(buffer,"png")
        buffer.seek(0)
        return buffer

class StatsSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label = "Overview",description = "Stats such as achievements, chests opened, etc.",value = 0),
            discord.SelectOption(label = "Exploration",description = "Stats such as exploration percent, reputation, etc.",value = 1),
            discord.SelectOption(label = "Teapot",description = "Stats such as level, visitors, etc.",value = 2),
        ]
        super().__init__(placeholder='Statistics Category', min_values=0, max_values=1, options=options,row = 0)
    
    async def callback(self,interaction: discord.Interaction):
        if self.values[0] == "0":
            buffer = await self.view.generate_default()
            file = discord.File(buffer,filename = f"{self.view.uid}statscard.png")
            embed = discord.Embed(title = "Genshin Impact Stats Card",color = discord.Color.random())
            embed.set_image(url = f"attachment://{self.view.uid}statscard.png")
            embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
            await interaction.response.edit_message(attachments = [file],embed = embed)
        elif self.values[0] == "1":
            back = Image.open("./pillow/staticassets/explorer.png")
            mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
            mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
            copy = back.copy()
            draw = Image.new("RGBA",copy.size)
            copy_editable = ImageDraw.Draw(draw)
            uidtext = f"UID: {self.view.uid}"
            copy_editable.text((20,20),"User Exploration",(255,255,255),font = pillow.title_font)
            _,_,w,h = copy_editable.textbbox((0,0),uidtext,font = pillow.title_font)
            copy_editable.text((copy.width-w-20,20),uidtext,font = pillow.title_font)
            copy_editable.line(((20,40+h),(820,40+h)),(255,255,255),1)
            
            currenth = 40 + h + 21
            width = 10
            count = 0

            for exploration in self.view.data.explorations:
                if os.path.exists(f"./pillow/dynamicassets/{exploration.icon.split('/')[-1]}"):
                    exploreicon = Image.open(f"./pillow/dynamicassets/{exploration.icon.split('/')[-1]}")
                else:
                    exploreicon = Image.open(urlopen(exploration.icon)).convert('RGBA')
                    exploreicon.save(f"./pillow/dynamicassets/{exploration.icon.split('/')[-1]}")
                exploreiconresized = exploreicon.resize((exploreicon.height//2,exploreicon.width//2))
                copy.paste(exploreiconresized,(width,currenth),exploreiconresized)
                build = f"{' '.join(exploration.name.split(':')[1:]).strip() if exploration.name.count(':') >= 1 else exploration.name}: {exploration.raw_explored/10}%\n"
                if len(exploration.offerings) > 0:
                    build += "\n".join([x.name + ": " + str(x.level) for x in exploration.offerings])
                _,_,w2,h2 = copy_editable.textbbox((0,0),build,font = pillow.subtitle_font)
                
                copy_editable.text((width + exploreiconresized.width + 5,currenth + (exploreiconresized.height-h2)//2),build,font = pillow.subtitle_font,stroke_width = 1, stroke_fill = (0,0,0))
                width += 273
                if count % 3 == 2:
                    currenth += 100
                    width = 10
                count += 1

            copy_editable.line(((20,copy.height-40),(820,copy.height-40)),(255,255,255),1)

            credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
            _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
            copy_editable.text((20 + mafuyuresized.width,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
            copy.paste(mafuyuresized,(20,copy.height - h7 - 13),mafuyuresized)

            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            file = discord.File(buffer,filename = f"{self.view.uid}statcard.png")
            embed = discord.Embed(title = "Genshin Impact Stats Card",color = discord.Color.random())
            embed.set_image(url = f"attachment://{self.view.uid}statcard.png")
            embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
            await interaction.response.edit_message(attachments = [file],embed = embed)
        elif self.values[0] == "2":
            back = Image.open("./pillow/staticassets/teapot.png")
            mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
            mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))
            copy = back.copy()
            draw = Image.new("RGBA",copy.size)
            copy_editable = ImageDraw.Draw(draw)
            uidtext = f"UID: {self.view.uid}"
            copy_editable.text((20,20),"User Teapot",(255,255,255),font = pillow.title_font)
            _,_,w,h = copy_editable.textbbox((0,0),uidtext,font = pillow.title_font)
            copy_editable.text((copy.width-w-20,20),uidtext,font = pillow.title_font)
            copy_editable.line(((20,40+h),(820,40+h)),(255,255,255),1)

            if os.path.exists(f"./pillow/dynamicassets/{self.view.data.teapot.comfort_icon.split('/')[-1]}"):
                teapoticon = Image.open(f"./pillow/dynamicassets/{self.view.data.teapot.comfort_icon.split('/')[-1]}")
            else:
                teapoticon = Image.open(urlopen(self.view.data.teapot.comfort_icon)).convert('RGBA')
                teapoticon.save(f"./pillow/dynamicassets/{self.view.data.teapot.comfort_icon.split('/')[-1]}")

            copy.paste(teapoticon,(20,(copy.height - teapoticon.height)//2),teapoticon)
            comfort_text = f"Comfort Level: {self.view.data.teapot.comfort_name}\nComfort Amount: {self.view.data.teapot.comfort}"
            _,_,w6,h6 = copy_editable.textbbox((0,0),comfort_text,font = pillow.title_font)
            copy_editable.text((30 + teapoticon.width,(copy.height-h6)/2),comfort_text,font = pillow.title_font,stroke_width = 1, stroke_fill = (0,0,0))

            other_text = f"Trust Rank: {self.view.data.teapot.level}\nFurnishings Obtained: {self.view.data.teapot.items}\nTotal Visitors: {self.view.data.teapot.visitors}"
            _,_,w2,h2 = copy_editable.textbbox((0,0),other_text,font = pillow.title_font)
            copy_editable.text((copy.width//2,(copy.height-h2)/2),other_text,font = pillow.title_font,stroke_width = 1, stroke_fill = (0,0,0))
            
            copy_editable.line(((20,copy.height-40),(820,copy.height-40)),(255,255,255),1)

            credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"
            _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
            copy_editable.text((20 + mafuyuresized.width,copy.height - h7 - 10),credits_text,font = pillow.credits_font,fill = (0, 0, 139))
            copy.paste(mafuyuresized,(20,copy.height - h7 - 13),mafuyuresized)

            out = Image.alpha_composite(copy,draw)
            buffer = BytesIO()
            out.save(buffer,"png")
            buffer.seek(0)
            file = discord.File(buffer,filename = f"{self.view.uid}statcard.png")
            embed = discord.Embed(title = "Genshin Impact Stats Card",color = discord.Color.random())
            embed.set_image(url = f"attachment://{self.view.uid}statcard.png")
            embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
            await interaction.response.edit_message(attachments = [file],embed = embed)

class LinkView(ui.View):
    def __init__(self,ctx,key):
        super().__init__(timeout = 300)
        self.ctx = ctx
        self.key = key
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    @discord.ui.button(label = "1. Login (Coming Soon!)",style = discord.ButtonStyle.blurple,disabled = True)
    async def getscriptv1(self,interaction,button):
        await interaction.response.send_message("How did you press this?")
    
    @discord.ui.button(label = "2. Manual Input",style = discord.ButtonStyle.blurple)
    async def manualinput(self,interaction,button):
        await interaction.response.send_modal(ManualCollectCookies(self.key))

class ManualCollectCookies(discord.ui.Modal,title = "Manual Cookie Request"):
    def __init__(self,key):
        super().__init__()
        self.key = key

    ltuid2 = discord.ui.TextInput(label = "ltuid_v2",placeholder="A short integer id number.",max_length = 300,required = True)
    ltoken2 = discord.ui.TextInput(label = "ltoken_v2",placeholder="A long string used for authentication.",max_length = 300,required = True)
    ltmid2 = discord.ui.TextInput(label = "ltmid_v2",placeholder="A short string used for authentication.",max_length = 300,required = True)

    async def on_submit(self, interaction: discord.Interaction):
        ltuid2,ltoken2,ltmid2 = self.ltuid2.value,self.ltoken2.value,self.ltmid2.value
        if ltuid2 and ltoken2 and ltmid2:
            uid2utf8 = ltuid2.encode('utf8')
            encodeduid2 = rsa.encrypt(uid2utf8,self.key)
            token2utf8 = ltoken2.encode('utf8')
            encodedtoken2 = rsa.encrypt(token2utf8,self.key)
            mid2utf8 = ltoken2.encode('utf8')
            encodedmid2 = rsa.encrypt(mid2utf8,self.key)
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.ltuid2":binascii.hexlify(encodeduid2).decode('utf8')}},upsert = True)
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.ltoken2":binascii.hexlify(encodedtoken2).decode('utf8')}})
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.ltmid2":binascii.hexlify(encodedmid2).decode('utf8')}})
        else:
            return await interaction.response.send_message(embed = discord.Embed(description = "You must input both an ltoken and ltuid for v1, and ltmid for v2!",color = discord.Color.random()),ephemeral = True)
        
        embed = discord.Embed(title = "Authentication Data Set!",description = "I have setup your cookies in the bot. You can now use any genshin command pertaining to yourself!\nSome commands require a UID. Set that up with </hoyolab settings:999438437906124835>.",color = discord.Color.green())
        embed.set_footer(text = "You can relink your account with /hoyolab link, and edit settings with /hoyolab settings")
        await interaction.response.send_message(embed = embed,ephemeral = True)

class CollectCookies(discord.ui.Modal,title = "Cookie Request"):
    def __init__(self,key):
        super().__init__()
        self.key = key

    cookies = discord.ui.TextInput(label = "Cookies",placeholder="A long string that you copied.",max_length = 300)

    async def on_submit(self, interaction: discord.Interaction):
        splitstr = self.cookies.value.split(";")
        if len(splitstr) < 3:
            return await interaction.response.send_message(embed = discord.Embed(description = "I could not parse your data! Please try again.",color = discord.Color.random()),ephemeral = True)
        ltuid, ltoken,ltuid2,ltoken2 = None,None,None,None
        for item in splitstr[:-1]:
            index = item.index("=")
            identifier = item[:index].strip()
            data = item[index+1:].strip(";").strip()
            if identifier == "ltoken":
                ltoken = data
            elif identifier == "ltuid":
                ltuid = data
            elif identifier == "ltuid_v2":
                ltuid2 = data
            elif identifier == "ltoken_v2":
                ltoken2 = data
        if ltuid2 and ltoken2:
            uid2utf8 = ltuid2.encode('utf8')
            encodeduid2 = rsa.encrypt(uid2utf8,self.key)
            token2utf8 = ltoken2.encode('utf8')
            encodedtoken2 = rsa.encrypt(token2utf8,self.key)
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.ltuid2":binascii.hexlify(encodeduid2).decode('utf8')}},upsert = True)
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.ltoken2":binascii.hexlify(encodedtoken2).decode('utf8')}})
        elif ltuid and ltoken:
            uidutf8 = ltuid.encode('utf8')
            encodeduid = rsa.encrypt(uidutf8,self.key)
            tokenutf8 = ltoken.encode('utf8')
            encodedtoken = rsa.encrypt(tokenutf8,self.key)
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.ltuid":binascii.hexlify(encodeduid).decode('utf8')}},upsert = True)
            interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.ltoken":binascii.hexlify(encodedtoken).decode('utf8')}})
        else:
            return await interaction.response.send_message(embed = discord.Embed(description = "I could not parse your data! Please try again.",color = discord.Color.random()),ephemeral = True)
        
        embed = discord.Embed(title = "Authentication Data Set!",description = "I have setup your cookies in the bot. You can now use any genshin command pertaining to yourself!\nSome commands require a UID. Set that up with </hoyolab settings:999438437906124835>.",color = discord.Color.green())
        embed.set_footer(text = "You can relink your account with /hoyolab link, and edit settings with /hoyolab settings")
        await interaction.response.send_message(embed = embed,ephemeral = True)
    
class AuthkeyView(ui.View):
    def __init__(self,ctx):
        super().__init__(timeout = 300)
        self.ctx = ctx
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    @discord.ui.button(label = "1. Get Script",style = discord.ButtonStyle.blurple)
    async def getscript(self,interaction,button):
        await interaction.response.send_message('```Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex "&{$((New-Object System.Net.WebClient).DownloadString(\'https://gist.githubusercontent.com/ChuChuCodes0414/fc14f48b92a15a205532cf3080762ce8/raw/28f5c25983765e6658f7ea47dbcf81a29262efbd/authkey.ps1\'))} global"```',ephemeral = True)
    
    @discord.ui.button(label = "2. Enter Information",style = discord.ButtonStyle.blurple)
    async def enterinformation(self,interaction,button):
        await interaction.response.send_modal(CollectAuthKey())

class CollectAuthKey(discord.ui.Modal,title = "Authkey Request"):
    def __init__(self):
        super().__init__()

    authkey = discord.ui.TextInput(label = "Authkey",placeholder="A long link...",max_length = 3000)
    
    async def on_submit(self, interaction: discord.Interaction):
        authkey = genshin.utility.extract_authkey(self.authkey.value)
        interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.authkey":authkey}},upsert = True)

        embed = discord.Embed(title = "Authentication Data Set!",description = "I have setup your authkey in the bot. You can now use any genshin command pertaining to wish history and transaction history!")
        await interaction.response.send_message(embed = embed,ephemeral = True)

class HSAuthkeyView(ui.View):
    def __init__(self,ctx):
        super().__init__(timeout = 300)
        self.ctx = ctx
        self.message = None
    
    async def interaction_check(self, interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False
    
    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    @discord.ui.button(label = "1. Get Script",style = discord.ButtonStyle.blurple)
    async def getscript(self,interaction,button):
        await interaction.response.send_message('```[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; Invoke-Expression (New-Object Net.WebClient).DownloadString("https://gist.githubusercontent.com/ChuChuCodes0414/bf5c869449dfcd9320ed7c2d2ea355d9/raw")```',ephemeral = True)
    
    @discord.ui.button(label = "2. Enter Information",style = discord.ButtonStyle.blurple)
    async def enterinformation(self,interaction,button):
        await interaction.response.send_modal(HSCollectAuthKey())

class HSCollectAuthKey(discord.ui.Modal,title = "Authkey Request"):
    def __init__(self):
        super().__init__()

    authkey = discord.ui.TextInput(label = "Authkey",placeholder="A long link...",max_length = 3000)
    
    async def on_submit(self, interaction: discord.Interaction):
        interaction.client.db.user_data.update_one({"_id":interaction.user.id},{"$set":{"hoyoverse.settings.hauthkey":self.authkey.value}},upsert = True)

        embed = discord.Embed(title = "Authentication Data Set!",description = "I have setup your authkey in the bot. You can now use any Honkai: Star Rail command pertaining to warp history!")
        await interaction.response.send_message(embed = embed,ephemeral = True)

class HallView(ui.View):
    def __init__(self,ctx,data,uid):
        super().__init__(timeout = 120)
        self.message = None
        self.ctx = ctx
        self.uid = uid
        self.data = data
        self.add_item(HallSelect(data if data else {}))
    
    async def interaction_check(self,interaction):
        if interaction.user == self.ctx.author:
            return True
        await interaction.response.send_message(embed = discord.Embed(description = "This menu is not for you!",color = discord.Color.red()),ephemeral = True)
        return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view = self)
    
    async def generate_default(self):
        im1 = Image.open("./pillow/staticassets/hshallback.png").convert('RGBA')
        star = Image.open("./pillow/staticassets/star.png").convert('RGBA')
        mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
        goldback = Image.open("./pillow/staticassets/hsgoldback.png").convert('RGBA')
        purpleback = Image.open("./pillow/staticassets/hspurpleback.png").convert('RGBA')

        title_text = f"Forgotten Hall Challenge Summary"
        star_text = f"{self.data.total_stars}/36"
        battles_text = f"Battles Fought: {self.data.total_battles}"
        stage_text = f"Stage Progress: {self.data.max_floor}"
        credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"

        backresized = im1.resize((int(im1.width/1.5),int(im1.height/1.5)))
        goldbackresized = goldback.resize((int(goldback.width/2.5),int(goldback.height/2.5)))
        purplebackresized = purpleback.resize((int(purpleback.width/2.5),int(purpleback.height/2.5)))
        starresized = star.resize((star.width//15,star.height//15))
        mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))

        copy = backresized.copy()
        draw = Image.new("RGBA",copy.size)
        copy_editable = ImageDraw.Draw(draw)

        _,_,w,h = copy_editable.textbbox((0,0),star_text,font = pillow.title_font)
        _,_,w2,h2 = copy_editable.textbbox((0,0),battles_text,font = pillow.subtitle_font)
        _,_,w3,h3 = copy_editable.textbbox((0,0),stage_text,font = pillow.subtitle_font)
        _,_,w4,h4 = copy_editable.textbbox((0,0),stage_text,font = pillow.small_font)
        copy_editable.text((20,20),title_text,(255,255,255),font = pillow.title_font)
        copy_editable.text((copy.width-w-20,20),star_text,(255,255,255),font = pillow.title_font)
        copy.paste(starresized,(copy.width-starresized.width-w-25,20),starresized)
        copy_editable.text((copy.width-w-w3-starresized.width-40,10),stage_text,font = pillow.subtitle_font)
        copy_editable.text((copy.width-w-w2-starresized.width-40,13 + h3),battles_text,font = pillow.subtitle_font)

        currenth = 40 + h
        copy_editable.line(((20,currenth),(backresized.width-20,currenth)),(255,255,255),1)
        currenth += 12
        for i in range(0,min(3,len(self.data.floors))):
            floor = self.data.floors[i]
            floor_text = f"{floor.name} | Completed In: {floor.round_num} rounds | Stars: {floor.star_num}/3"
            copy_editable.text((20,currenth),floor_text,(255,255,255),font = pillow.small_font)
            currenth += h4+12

            node1_text = f"Node One: {floor.node_1.challenge_time.datetime.strftime('%A, %B %d, %Y %I:%M %p')}"
            copy_editable.text((20,currenth),node1_text,(255,255,255),font = pillow.small_font)
            currenth += h4+2

            for k in range(0,len(floor.node_1.avatars)):
                character = floor.node_1.avatars[k]
                if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
                    characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                else:
                    characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
                    characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                if characterimg.width == 112:
                    resized = characterimg.resize((int(characterimg.width/1.7),int(characterimg.height/1.7)))
                else:
                    resized = characterimg.resize((int(characterimg.width/2.56),int(characterimg.height/2.56)))
                if character.rarity == 5:
                    copy.paste(goldbackresized,(20+((10+resized.width)*k),currenth+10),goldbackresized)
                else:
                    copy.paste(purplebackresized,(20+((10+resized.width)*k),currenth+10),purplebackresized)
                copy.paste(resized,(20+((10+resized.width)*k),currenth+10),resized)

                level_text = f"Level {character.level}"
                _,_,w5,h5 = copy_editable.textbbox((0,0),level_text,font = pillow.small_font)
                copy_editable.rectangle(((20+((10+resized.width)*k),currenth + 10 + resized.height - 13),(20+((10+resized.width)*k) + resized.width,currenth + 10 + resized.height)),(0,0,0,127))
                copy_editable.text((20+((10+resized.width)*k) + resized.width//2 - w5//2,currenth + 10 + resized.height - 13 + 13//2 - h5//2),level_text,font = pillow.small_font)
            
            node1_text = f"Node Two: {floor.node_2.challenge_time.datetime.strftime('%A, %B %d, %Y %I:%M %p')}"
            copy_editable.text((copy.width - 20 - (goldbackresized.width+10)*4,currenth-h4-2),node1_text,(255,255,255),font = pillow.small_font)

            for k in range(0,len(floor.node_2.avatars)):
                character = floor.node_2.avatars[k]
                if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
                    characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                else:
                    characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
                    characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                if characterimg.width == 112:
                    resized = characterimg.resize((int(characterimg.width/1.7),int(characterimg.height/1.7)))
                else:
                    resized = characterimg.resize((int(characterimg.width/2.56),int(characterimg.height/2.56)))
                if character.rarity == 5:
                    copy.paste(goldbackresized,(copy.width-resized.width-20-((10+resized.width)*k),currenth+10),goldbackresized)
                else:
                    copy.paste(purplebackresized,(copy.width-resized.width-20-((10+resized.width)*k),currenth+10),purplebackresized)
                copy.paste(resized,(copy.width-resized.width-20-((10+resized.width)*k),currenth+10),resized)

                level_text = f"Level {character.level}"
                _,_,w5,h5 = copy_editable.textbbox((0,0),level_text,font = pillow.small_font)
                copy_editable.rectangle(((copy.width-resized.width-20-((10+resized.width)*k),currenth + 10 + resized.height - 13),(copy.width-resized.width-20-((10+resized.width)*k) + resized.width,currenth + 10 + resized.height)),(0,0,0,127))
                copy_editable.text((copy.width-resized.width-20-((10+resized.width)*k) + resized.width//2 - w5//2,currenth + 10 + resized.height - 13 + 13//2 - h5//2),level_text,font = pillow.small_font)

            currenth += goldbackresized.height + 20
            copy_editable.line(((20,currenth),(backresized.width-20,currenth)),(255,255,255),2)
            currenth += 14

        _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
        copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 20),credits_text,font = pillow.credits_font)
        copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 23),mafuyuresized)

        out = Image.alpha_composite(copy,draw)
        buffer = BytesIO()
        out.save(buffer,"png")
        buffer.seek(0)
        return buffer
    
class HallSelect(ui.Select):
    def __init__(self,data):
        options = []
        self.pages = []
        group = []
        self.data = data
        for floor in data.floors:
            group.append(floor)
            if len(group) == 3:
                self.pages.append(group)
                group = []
        if group:
            self.pages.append(group)
        for index,page in enumerate(self.pages):
            options.append(discord.SelectOption(label = f"Forgotten Hall Floors {len(self.data.floors)-(index*3)} - {len(self.data.floors)-(index*3)-len(page)+1}",value = index))
        super().__init__(placeholder = "Forgotten Hall Floors",min_values = 0,max_values = 1,options = options)
    
    async def callback(self,interaction):
        floors = self.pages[int(self.values[0])]
        im1 = Image.open("./pillow/staticassets/hshallback.png").convert('RGBA')
        star = Image.open("./pillow/staticassets/star.png").convert('RGBA')
        mafuyu = Image.open("./pillow/staticassets/mafuyu.png").convert('RGBA')
        goldback = Image.open("./pillow/staticassets/hsgoldback.png").convert('RGBA')
        purpleback = Image.open("./pillow/staticassets/hspurpleback.png").convert('RGBA')

        title_text = f"Forgotten Hall Challenge Summary"
        star_text = f"{self.data.total_stars}/36"
        battles_text = f"Battles Fought: {self.data.total_battles}"
        stage_text = f"Stage Progress: {self.data.max_floor}"
        credits_text = f"Mafuyu Bot\ndiscord.gg/9pmGDc8pqQ"

        backresized = im1.resize((int(im1.width/1.5),int(im1.height/1.5)))
        goldbackresized = goldback.resize((int(goldback.width/2.5),int(goldback.height/2.5)))
        purplebackresized = purpleback.resize((int(purpleback.width/2.5),int(purpleback.height/2.5)))
        starresized = star.resize((star.width//15,star.height//15))
        mafuyuresized = mafuyu.resize((mafuyu.width//10,mafuyu.height//10))

        copy = backresized.copy()
        draw = Image.new("RGBA",copy.size)
        copy_editable = ImageDraw.Draw(draw)

        _,_,w,h = copy_editable.textbbox((0,0),star_text,font = pillow.title_font)
        _,_,w2,h2 = copy_editable.textbbox((0,0),battles_text,font = pillow.subtitle_font)
        _,_,w3,h3 = copy_editable.textbbox((0,0),stage_text,font = pillow.subtitle_font)
        _,_,w4,h4 = copy_editable.textbbox((0,0),stage_text,font = pillow.small_font)
        copy_editable.text((20,20),title_text,(255,255,255),font = pillow.title_font)
        copy_editable.text((copy.width-w-20,20),star_text,(255,255,255),font = pillow.title_font)
        copy.paste(starresized,(copy.width-starresized.width-w-25,20),starresized)
        copy_editable.text((copy.width-w-w3-starresized.width-40,10),stage_text,font = pillow.subtitle_font)
        copy_editable.text((copy.width-w-w2-starresized.width-40,13 + h3),battles_text,font = pillow.subtitle_font)

        currenth = 40 + h
        copy_editable.line(((20,currenth),(backresized.width-20,currenth)),(255,255,255),1)
        currenth += 12
        for i in range(0,min(3,len(floors))):
            floor = floors[i]
            floor_text = f"{floor.name} | Completed In: {floor.round_num} rounds | Stars: {floor.star_num}/3"
            copy_editable.text((20,currenth),floor_text,(255,255,255),font = pillow.small_font)
            currenth += h4+12

            node1_text = f"Node One: {floor.node_1.challenge_time.datetime.strftime('%A, %B %d, %Y %I:%M %p')}"
            copy_editable.text((20,currenth),node1_text,(255,255,255),font = pillow.small_font)
            currenth += h4+2

            for k in range(0,len(floor.node_1.avatars)):
                character = floor.node_1.avatars[k]
                if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
                    characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                else:
                    characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
                    characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                if characterimg.width == 112:
                    resized = characterimg.resize((int(characterimg.width/1.7),int(characterimg.height/1.7)))
                else:
                    resized = characterimg.resize((int(characterimg.width/2.56),int(characterimg.height/2.56)))
                if character.rarity == 5:
                    copy.paste(goldbackresized,(20+((10+resized.width)*k),currenth+10),goldbackresized)
                else:
                    copy.paste(purplebackresized,(20+((10+resized.width)*k),currenth+10),purplebackresized)
                copy.paste(resized,(20+((10+resized.width)*k),currenth+10),resized)

                level_text = f"Level {character.level}"
                _,_,w5,h5 = copy_editable.textbbox((0,0),level_text,font = pillow.small_font)
                copy_editable.rectangle(((20+((10+resized.width)*k),currenth + 10 + resized.height - 13),(20+((10+resized.width)*k) + resized.width,currenth + 10 + resized.height)),(0,0,0,127))
                copy_editable.text((20+((10+resized.width)*k) + resized.width//2 - w5//2,currenth + 10 + resized.height - 13 + 13//2 - h5//2),level_text,font = pillow.small_font)
            
            node1_text = f"Node Two: {floor.node_2.challenge_time.datetime.strftime('%A, %B %d, %Y %I:%M %p')}"
            copy_editable.text((copy.width - 20 - (goldbackresized.width+10)*4,currenth-h4-2),node1_text,(255,255,255),font = pillow.small_font)

            for k in range(0,len(floor.node_2.avatars)):
                character = floor.node_1.avatars[k]
                if os.path.exists(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}"):
                    characterimg = Image.open(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                else:
                    characterimg = Image.open(urlopen(character.icon)).convert('RGBA')
                    characterimg.save(f"./pillow/dynamicassets/{character.icon.split('/')[-1]}")
                if characterimg.width == 112:
                    resized = characterimg.resize((int(characterimg.width/1.7),int(characterimg.height/1.7)))
                else:
                    resized = characterimg.resize((int(characterimg.width/2.56),int(characterimg.height/2.56)))
                if character.rarity == 5:
                    copy.paste(goldbackresized,(copy.width-resized.width-20-((10+resized.width)*k),currenth+10),goldbackresized)
                else:
                    copy.paste(purplebackresized,(copy.width-resized.width-20-((10+resized.width)*k),currenth+10),purplebackresized)
                copy.paste(resized,(copy.width-resized.width-20-((10+resized.width)*k),currenth+10),resized)

                level_text = f"Level {character.level}"
                _,_,w5,h5 = copy_editable.textbbox((0,0),level_text,font = pillow.small_font)
                copy_editable.rectangle(((copy.width-resized.width-20-((10+resized.width)*k),currenth + 10 + resized.height - 13),(copy.width-resized.width-20-((10+resized.width)*k) + resized.width,currenth + 10 + resized.height)),(0,0,0,127))
                copy_editable.text((copy.width-resized.width-20-((10+resized.width)*k) + resized.width//2 - w5//2,currenth + 10 + resized.height - 13 + 13//2 - h5//2),level_text,font = pillow.small_font)

            currenth += goldbackresized.height + 20
            copy_editable.line(((20,currenth),(backresized.width-20,currenth)),(255,255,255),2)
            currenth += 14

        _,_,w7,h7 = copy_editable.textbbox((0,0),credits_text,font = pillow.credits_font)
        copy_editable.text((copy.width - w7 - 10,copy.height - h7 - 20),credits_text,font = pillow.credits_font)
        copy.paste(mafuyuresized,(copy.width - w7 - 40,copy.height - h7 - 23),mafuyuresized)

        out = Image.alpha_composite(copy,draw)
        buffer = BytesIO()
        out.save(buffer,"png")
        buffer.seek(0)
        file = discord.File(buffer,filename = f"{self.view.uid}hallcard.png")
        embed = discord.Embed(title = "Honkai: Star Rail Forgotten Hall Card",description = f"Season {self.data.season} | Start <t:{int(self.data.begin_time.datetime.replace(tzinfo=datetime.timezone.utc).timestamp())}:f> | End <t:{int(self.data.end_time.datetime.replace(tzinfo=datetime.timezone.utc).timestamp())}:f>",color = discord.Color.random())
        embed.set_image(url = f"attachment://{self.view.uid}hallcard.png")
        embed.set_footer(icon_url = interaction.client.user.avatar.url, text = interaction.client.user.name)
        await interaction.response.edit_message(attachments = [file],embed = embed)

async def setup(client):
    await client.add_cog(Hoyoverse(client))