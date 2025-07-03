import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from datetime import datetime, timedelta
import json
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
CONFIG_FILE = "like_channels.json"

VIP_USERS = {
    123456789012345678,
    1086922864558624808
}

INVITE_LINK = "https://discord.gg/zf6eB26hDY"

class LikeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_host = "https://dfadads.vercel.app/"
        self.config_data = self.load_config()
        self.cooldowns = {}
        self.session = aiohttp.ClientSession()

        self.headers = {}
        if RAPIDAPI_KEY:
            self.headers = {
                'x-rapidapi-key': RAPIDAPI_KEY,
                'x-rapidapi-host': "https://dfadads.vercel.app/"
            }

    def load_config(self):
        default_config = {"servers": {}}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    loaded_config.setdefault("servers", {})
                    return loaded_config
            except json.JSONDecodeError:
                print(f"WARNING: '{CONFIG_FILE}' is corrupt. Resetting.")
        self.save_config(default_config)
        return default_config

    def save_config(self, config_to_save=None):
        data_to_save = config_to_save if config_to_save is not None else self.config_data
        temp_file = CONFIG_FILE + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        os.replace(temp_file, CONFIG_FILE)

    async def check_channel(self, ctx):
        if ctx.guild is None:
            return True
        guild_id = str(ctx.guild.id)
        server_config = self.config_data["servers"]
        if guild_id not in server_config:
            return "server"
        like_channels = server_config[guild_id].get("like_channels", [])
        if like_channels and str(ctx.channel.id) not in like_channels:
            return "channel"
        return True

    async def cog_load(self):
        pass

    @commands.hybrid_command(name="like", description="Sends likes to a Free Fire player")
    @app_commands.describe(uid="Player UID (6+ digits)")
    async def like_command(self, ctx: commands.Context, uid: str):
        is_slash = ctx.interaction is not None
        channel_check = await self.check_channel(ctx)

        if channel_check == "server":
            embed = discord.Embed(title="🚫 Server Not Authorized",
                                  description=f"This server is not allowed.\n👉 [Join Official Server]({INVITE_LINK})",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        elif channel_check == "channel":
            embed = discord.Embed(title="🚫 Not Allowed Here",
                                  description="Use this command in an approved channel.",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        user_id = ctx.author.id
        now = datetime.now()

        if user_id not in VIP_USERS:
            if user_id in self.cooldowns:
                last_used = self.cooldowns[user_id]
                if now - last_used < timedelta(hours=24):
                    remaining = timedelta(hours=24) - (now - last_used)
                    hours, remainder = divmod(remaining.seconds, 3600)
                    minutes = remainder // 60
                    embed = discord.Embed(title="🔒 Cooldown",
                                          description=f"⏳ Try again in **{hours}h {minutes}m**.\n💎 Buy Premium for unlimited access.",
                                          color=discord.Color.orange(), timestamp=now)
                    embed.set_footer(text="CursedCore")
                    await ctx.send(embed=embed)
                    return

        self.cooldowns[user_id] = now

        if not uid.isdigit() or len(uid) < 6:
            await ctx.reply("UID must be numeric and at least 6 digits.", ephemeral=is_slash)
            return

        try:
            async with ctx.typing():
                async with self.session.get(f"{self.api_host}/like?uid={uid}", headers=self.headers) as response:
                    if response.status == 404:
                        await self._send_player_not_found(ctx, uid)
                        return
                    if response.status != 200:
                        await self._send_api_error(ctx)
                        return

                    data = await response.json()

                    embed = discord.Embed(title="CyrsedCore Likes 🧾", color=discord.Color.random(), timestamp=datetime.now())
                    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

                    if data.get("status") == 1:
                        embed.add_field(name="‎ ", value=(
                            f"```ansi\n"
                            f"📋 Player Info\n"
                            f"👤 Name:[0m [0;36m{data.get('player', 'Unknown')}[0m\n"
                            f"🆔 UID:[0m [0;36m{uid}[0m\n"
                            f"🧪 Added Likes:[0m +{data.get('likes_added', 0)}\n"
                            f"📝 Before: {data.get('likes_before', 'N/A')}\n"
                            f"❤️ After:  {data.get('likes_after', 'N/A')}\n```")
                        )
                    else:
                        embed.add_field(name="Max Likes Reached ❌", value="```This UID has already received the max likes today```")

                    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
                    await ctx.send(embed=embed, ephemeral=is_slash)

        except asyncio.TimeoutError:
            await self._send_error_embed(ctx, "Timeout", "The server took too long to respond.", ephemeral=is_slash)
        except Exception as e:
            print(f"Unexpected error in like_command: {e}")
            await self._send_error_embed(ctx, "⚡ Critical Error", "An unexpected error occurred. Please try again later.", ephemeral=is_slash)

    async def _send_player_not_found(self, ctx, uid):
        embed = discord.Embed(title="❌ Player Not Found", description=f"The UID {uid} does not exist or is not accessible.", color=0xE74C3C)
        embed.add_field(name="Tip", value="Make sure that:\n- The UID is correct\n- The player is not private", inline=False)
        await ctx.send(embed=embed)

    async def _send_api_error(self, ctx):
        embed = discord.Embed(title="⚠️ Service Unavailable", description="The Free Fire API is not responding at the moment.", color=0xF39C12)
        embed.add_field(name="Solution", value="Try again in a few minutes.", inline=False)
        await ctx.send(embed=embed)

    async def _send_error_embed(self, ctx, title, description, ephemeral=True):
        embed = discord.Embed(title=f"❌ {title}", description=description, color=discord.Color.red(), timestamp=datetime.now())
        embed.set_footer(text="An error occurred.")
        await ctx.send(embed=embed, ephemeral=ephemeral)

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

async def setup(bot):
    await bot.add_cog(LikeCommands(bot))