import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import threading
import json
from dotenv import load_dotenv
from web_server import run_flask_app, get_ngrok_url, verified_users, user_info_store

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
VERIFY_CHANNEL_ID = int(os.getenv('VERIFY_CHANNEL_ID') or '0')
VERIFIED_ROLE_ID = int(os.getenv('VERIFIED_ROLE_ID') or '0')

guild_settings = {}
SETTINGS_FILE = 'guild_settings.json'

def load_guild_settings():
    global guild_settings
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                guild_settings = json.load(f)
    except Exception as e:
        print(f"Lỗi tải cài đặt guild: {e}")
        guild_settings = {}

def save_guild_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(guild_settings, f, indent=2)
    except Exception as e:
        print(f"Lỗi lưu cài đặt guild: {e}")

def get_verify_channel_id(guild_id: int) -> int:
    guild_id_str = str(guild_id)
    if guild_id_str in guild_settings and 'verify_channel_id' in guild_settings[guild_id_str]:
        return guild_settings[guild_id_str]['verify_channel_id']
    return VERIFY_CHANNEL_ID

def get_verified_role_id(guild_id: int) -> int:
    guild_id_str = str(guild_id)
    if guild_id_str in guild_settings and 'verified_role_id' in guild_settings[guild_id_str]:
        return guild_settings[guild_id_str]['verified_role_id']
    return VERIFIED_ROLE_ID

def set_verify_channel(guild_id: int, channel_id: int):
    guild_id_str = str(guild_id)
    if guild_id_str not in guild_settings:
        guild_settings[guild_id_str] = {}
    guild_settings[guild_id_str]['verify_channel_id'] = channel_id
    save_guild_settings()

def set_verified_role(guild_id: int, role_id: int):
    guild_id_str = str(guild_id)
    if guild_id_str not in guild_settings:
        guild_settings[guild_id_str] = {}
    guild_settings[guild_id_str]['verified_role_id'] = role_id
    save_guild_settings()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Xác Minh", style=discord.ButtonStyle.primary, emoji="✅", custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        
        if not guild:
            await interaction.response.send_message(
                "Lệnh này chỉ có thể sử dụng trong server!",
                ephemeral=True
            )
            return
        
        member = guild.get_member(user.id)
        verified_role_id = get_verified_role_id(guild.id)
        verified_role = guild.get_role(verified_role_id)
        
        if member and verified_role and verified_role in member.roles:
            await interaction.response.send_message(
                "✅ Bạn đã được xác minh rồi! Không cần xác minh lại.",
                ephemeral=True
            )
            return
        
        ngrok_url = get_ngrok_url()
        if not ngrok_url:
            await interaction.response.send_message(
                "Hệ thống xác minh chưa sẵn sàng. Vui lòng thử lại sau giây lát.",
                ephemeral=True
            )
            return

        user_id = str(user.id)
        guild_id = str(guild.id)
        verify_key = f"{guild_id}_{user_id}"
        verify_url = f"{ngrok_url}/verify/{verify_key}"

        user_info_store[verify_key] = {
            'name': user.display_name,
            'username': str(user),
            'avatar': user.display_avatar.url if user.display_avatar else None,
            'guild_id': guild_id,
            'user_id': user_id
        }

        embed = discord.Embed(
            title="🔗 Liên Kết Xác Minh",
            description=f"Nhấn vào liên kết bên dưới để xác minh:\n\n[👉 Nhấn vào đây để xác minh]({verify_url})",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Liên kết này chỉ dành riêng cho bạn. Không chia sẻ cho người khác.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def send_verify_embed(channel: discord.TextChannel):
    embed = discord.Embed(
        title="🔒 Xác Minh Thành Viên",
        description="Chào mừng bạn đến với server! Để truy cập tất cả các kênh, bạn cần xác minh bản thân và mở khóa các kênh như GiveAways và có quyền chat tại các kênh.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📋 Cách Xác Minh",
        value="1. Nhấn nút **Xác Minh** bên dưới\n2. Hoàn thành captcha trên trang web\n3. Bạn sẽ tự động được cấp quyền truy cập",
        inline=False
    )
    embed.add_field(
        name="❓ Tại Sao Cần Xác Minh?",
        value="Điều này giúp chúng tôi ngăn chặn bot và spam để giữ server an toàn.",
        inline=False
    )
    embed.set_footer(text="Gặp vấn đề? Liên hệ moderator để được hỗ trợ.")

    view = VerifyButton()

    await channel.purge(limit=100)
    await channel.send(embed=embed, view=view)
    print(f"Đã gửi embed xác minh đến {channel.name}")

@bot.event
async def on_ready():
    print(f'{bot.user} đã kết nối với Discord!')

    load_guild_settings()

    bot.add_view(VerifyButton())

    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh slash")
    except Exception as e:
        print(f"Lỗi đồng bộ lệnh: {e}")

    await asyncio.sleep(2)

    for guild in bot.guilds:
        verify_channel_id = get_verify_channel_id(guild.id)
        if verify_channel_id:
            verify_channel = guild.get_channel(verify_channel_id)
            if verify_channel and isinstance(verify_channel, discord.TextChannel):
                await send_verify_embed(verify_channel)

    bot.loop.create_task(check_verified_users())
    print("✓ Bot đã sẵn sàng!")

@bot.event
async def on_member_join(member: discord.Member):
    print(f"Thành viên mới tham gia: {member.name}")

async def check_verified_users():
    while True:
        await asyncio.sleep(2)

        keys_to_verify = list(verified_users)
        for verify_key in keys_to_verify:
            user_info = user_info_store.get(verify_key, {})
            guild_id = user_info.get('guild_id', None)
            user_id = user_info.get('user_id', None)
            
            if not guild_id or not user_id:
                verified_users.discard(verify_key)
                continue
            
            guild = bot.get_guild(int(guild_id))
            if not guild:
                verified_users.discard(verify_key)
                continue
                
            member = guild.get_member(int(user_id))
            if member:
                verified_role_id = get_verified_role_id(guild.id)
                verified_role = guild.get_role(verified_role_id)
                if verified_role and verified_role not in member.roles:
                    await member.add_roles(verified_role)
                    print(f"✓ Đã xác minh {member.name} trong {guild.name}")

                    try:
                        await member.send(
                            embed=discord.Embed(
                                title="✅ Xác Minh Thành Công!",
                                description=f"Bạn đã được xác minh trong **{guild.name}**. Bây giờ bạn có thể truy cập tất cả các kênh!",
                                color=discord.Color.green()
                            )
                        )
                    except:
                        pass

            verified_users.discard(verify_key)

@bot.tree.command(name="verifychannel", description="Đặt kênh xác minh cho server này")
@app_commands.describe(channel="Kênh để đặt làm kênh xác minh")
@app_commands.default_permissions(administrator=True)
async def verifychannel_command(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild:
        await interaction.response.send_message("Lệnh này chỉ có thể sử dụng trong server!", ephemeral=True)
        return
    
    set_verify_channel(interaction.guild.id, channel.id)
    await send_verify_embed(channel)
    
    await interaction.response.send_message(
        f"✅ Đã đặt {channel.mention} làm kênh xác minh cho server này!",
        ephemeral=True
    )

@bot.tree.command(name="verifyrole", description="Đặt role được cấp sau khi xác minh")
@app_commands.describe(role="Role sẽ được cấp cho thành viên sau khi xác minh")
@app_commands.default_permissions(administrator=True)
async def verifyrole_command(interaction: discord.Interaction, role: discord.Role):
    if not interaction.guild:
        await interaction.response.send_message("Lệnh này chỉ có thể sử dụng trong server!", ephemeral=True)
        return
    
    set_verified_role(interaction.guild.id, role.id)
    
    await interaction.response.send_message(
        f"✅ Đã đặt {role.mention} làm role xác minh cho server này!",
        ephemeral=True
    )

@bot.tree.command(name="refreshverify", description="Làm mới embed xác minh")
@app_commands.default_permissions(administrator=True)
async def refreshverify_command(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Lệnh này chỉ có thể sử dụng trong server!", ephemeral=True)
        return
    
    verify_channel_id = get_verify_channel_id(interaction.guild.id)
    verify_channel = interaction.guild.get_channel(verify_channel_id)
    
    if verify_channel and isinstance(verify_channel, discord.TextChannel):
        await send_verify_embed(verify_channel)
        await interaction.response.send_message("✅ Đã làm mới embed xác minh!", ephemeral=True)
    else:
        await interaction.response.send_message(
            "❌ Không tìm thấy kênh xác minh! Sử dụng `/verifychannel` để đặt kênh.",
            ephemeral=True
        )

@bot.tree.command(name="verifyinfo", description="Xem thông tin cài đặt xác minh của server")
@app_commands.default_permissions(administrator=True)
async def verifyinfo_command(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Lệnh này chỉ có thể sử dụng trong server!", ephemeral=True)
        return
    
    verify_channel_id = get_verify_channel_id(interaction.guild.id)
    verified_role_id = get_verified_role_id(interaction.guild.id)
    
    verify_channel = interaction.guild.get_channel(verify_channel_id)
    verified_role = interaction.guild.get_role(verified_role_id)
    
    embed = discord.Embed(
        title="⚙️ Cài Đặt Xác Minh",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📢 Kênh Xác Minh",
        value=verify_channel.mention if verify_channel else f"Chưa đặt (mặc định: {verify_channel_id})",
        inline=False
    )
    
    embed.add_field(
        name="🎭 Role Xác Minh",
        value=verified_role.mention if verified_role else f"Chưa đặt (mặc định: {verified_role_id})",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.command(name='refresh')
@commands.has_permissions(administrator=True)
async def refresh_command(ctx: commands.Context):
    """Làm mới embed xác minh"""
    if not ctx.guild:
        await ctx.send("Lệnh này chỉ có thể sử dụng trong server!")
        return
    verify_channel_id = get_verify_channel_id(ctx.guild.id)
    verify_channel = ctx.guild.get_channel(verify_channel_id)
    if verify_channel and isinstance(verify_channel, discord.TextChannel):
        await send_verify_embed(verify_channel)
        await ctx.send("✅ Đã làm mới embed xác minh!")
    else:
        await ctx.send("❌ Không tìm thấy kênh xác minh!")

def start_flask():
    run_flask_app()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    import time
    time.sleep(2)

    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("Lỗi: DISCORD_TOKEN chưa được cài đặt!")
