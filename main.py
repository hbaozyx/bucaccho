import os
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('COMMAND_PREFIX', '$')
BACKUP_DIR = Path('backups')
BACKUP_DIR.mkdir(exist_ok=True)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


def owner_only():
    async def predicate(ctx):
        return ctx.guild is not None and ctx.author.id == ctx.guild.owner_id
    return commands.check(predicate)


@bot.event
async def on_ready():
    print(f'Y0UNG Control ready: {bot.user} ({bot.user.id})')


@bot.command(name='help')
@commands.guild_only()
async def help_cmd(ctx):
    await ctx.send('**Y0UNG Control — quản lý kênh an toàn**\n'
                   '`$channels` — liệt kê kênh\n'
                   '`$backup_channels` — sao lưu cấu trúc kênh (chủ server)\n'
                   '`$create_channels <số lượng 1-10> <tên>` — tạo kênh (chủ server)\n'
                   '`$rename_channel <ID> <tên mới>` — đổi tên kênh (chủ server)\n'
                   '`$delete_channel <ID>` — xác nhận xóa một kênh (chủ server)\n'
                   '`$delete_selected <ID1> <ID2> ...` — xác nhận xóa tối đa 10 kênh được chọn\n'
                   '`$nuke <ID1> ... <ID10>` — xác nhận xóa kênh đã chọn và tạo 200 kênh mới')


@bot.command()
@commands.guild_only()
async def channels(ctx):
    lines = [f'{c.name} — `{c.id}` ({c.type})' for c in ctx.guild.channels]
    for start in range(0, len(lines), 20):
        await ctx.send('\n'.join(lines[start:start + 20])[:1900])


@bot.command()
@owner_only()
async def backup_channels(ctx):
    data = {
        'guild_id': ctx.guild.id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'channels': [
            {'id': c.id, 'name': c.name, 'type': str(c.type), 'position': c.position,
             'category_id': getattr(c, 'category_id', None)}
            for c in ctx.guild.channels
        ]
    }
    path = BACKUP_DIR / f'channels_{ctx.guild.id}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json'
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    await ctx.send('Đã sao lưu danh sách và cấu trúc kênh. Bản sao lưu này không bao gồm tin nhắn hay toàn bộ quyền.', file=discord.File(path))


@bot.command()
@owner_only()
async def create_channels(ctx, amount: int, *, name: str):
    if not 1 <= amount <= 10 or not 1 <= len(name) <= 80:
        return await ctx.send('Số lượng phải từ 1 đến 10; tên dài 1–80 ký tự.')
    if not ctx.guild.me.guild_permissions.manage_channels:
        return await ctx.send('Bot cần quyền Manage Channels.')
    created = []
    for i in range(amount):
        channel_name = name if amount == 1 else f'{name}-{i+1}'
        try:
            c = await ctx.guild.create_text_channel(channel_name, reason=f'Approved by guild owner {ctx.author.id}')
            created.append(c.name)
            await asyncio.sleep(1.5)
        except discord.HTTPException as exc:
            return await ctx.send(f'Đã tạo {len(created)} kênh. Dừng vì lỗi Discord: {exc}')
    await ctx.send(f'Đã tạo {len(created)} kênh: ' + ', '.join(created)[:1500])


@bot.command()
@owner_only()
async def rename_channel(ctx, channel_id: int, *, new_name: str):
    channel = ctx.guild.get_channel(channel_id)
    if channel is None or not 1 <= len(new_name) <= 80:
        return await ctx.send('Không tìm thấy kênh hoặc tên không hợp lệ.')
    try:
        await channel.edit(name=new_name, reason=f'Renamed by guild owner {ctx.author.id}')
        await ctx.send(f'Đã đổi tên kênh thành `{new_name}`.')
    except discord.HTTPException as exc:
        await ctx.send(f'Không thể đổi tên: {exc}')


class ConfirmDelete(discord.ui.View):
    def __init__(self, owner_id, channel_id):
        super().__init__(timeout=45)
        self.owner_id = owner_id
        self.channel_id = channel_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('Chỉ chủ máy chủ có thể xác nhận.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Xác nhận xóa 1 kênh', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if channel is None:
            return await interaction.response.send_message('Kênh không còn tồn tại.', ephemeral=True)
        if channel.id == interaction.channel_id:
            return await interaction.response.send_message('Không thể xóa kênh đang dùng để xác nhận.', ephemeral=True)
        await interaction.response.send_message(f'Đang xóa kênh `{channel.name}`.', ephemeral=True)
        try:
            await channel.delete(reason=f'Explicitly confirmed by guild owner {interaction.user.id}')
        except discord.HTTPException:
            await interaction.followup.send('Xóa thất bại; kiểm tra quyền bot.', ephemeral=True)
        self.stop()

    @discord.ui.button(label='Hủy', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content='Đã hủy xóa kênh.', view=None)
        self.stop()


@bot.command()
@owner_only()
async def delete_channel(ctx, channel_id: int):
    channel = ctx.guild.get_channel(channel_id)
    if channel is None:
        return await ctx.send('Không tìm thấy kênh.')
    if channel.id == ctx.channel.id:
        return await ctx.send('Không thể xóa kênh đang dùng để xác nhận. Hãy chạy lệnh ở kênh khác.')
    await ctx.send(f'Bạn có chắc muốn xóa **một kênh** `{channel.name}` (`{channel.id}`)?', view=ConfirmDelete(ctx.author.id, channel.id))


class ConfirmSelected(discord.ui.View):
    def __init__(self, owner_id, ids):
        super().__init__(timeout=60)
        self.owner_id, self.ids = owner_id, ids

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('Chỉ chủ máy chủ được xác nhận.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Xác nhận xóa các kênh đã chọn', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        done, failed = [], []
        for channel_id in self.ids:
            channel = interaction.guild.get_channel(channel_id)
            if channel is None or channel.id == interaction.channel_id:
                failed.append(str(channel_id))
                continue
            try:
                await channel.delete(reason=f'Explicit owner confirmation {interaction.user.id}')
                done.append(str(channel_id))
                await asyncio.sleep(1.5)
            except discord.HTTPException:
                failed.append(str(channel_id))
        await interaction.followup.send(f'Đã xóa {len(done)} kênh được chọn; thất bại {len(failed)}. ID lỗi: {", ".join(failed) or "không có"}', ephemeral=True)
        self.stop()

    @discord.ui.button(label='Hủy', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content='Đã hủy.', view=None)
        self.stop()


@bot.command()
@owner_only()
async def delete_selected(ctx, *channel_ids: int):
    ids = list(dict.fromkeys(channel_ids))
    if not 1 <= len(ids) <= 10:
        return await ctx.send('Chọn từ 1 đến 10 ID kênh mỗi lần.')
    channels = [ctx.guild.get_channel(cid) for cid in ids]
    if any(c is None for c in channels) or ctx.channel.id in ids:
        return await ctx.send('ID không hợp lệ hoặc có kênh đang dùng để xác nhận.')
    if not ctx.guild.me.guild_permissions.manage_channels:
        return await ctx.send('Bot cần quyền Manage Channels.')
    backup = {'guild_id': ctx.guild.id, 'created_at': datetime.now(timezone.utc).isoformat(),
              'channels': [{'id': c.id, 'name': c.name, 'type': str(c.type),
                            'position': c.position, 'category_id': getattr(c, 'category_id', None)}
                           for c in ctx.guild.channels]}
    path = BACKUP_DIR / f'predelete_{ctx.guild.id}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.json'
    path.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding='utf-8')
    await ctx.send('Đã tạo bản sao lưu cấu trúc (không bao gồm tin nhắn/quyền chi tiết). '
                   'Xác nhận xóa các kênh được chọn: ' + ', '.join(f'`{c.name}`' for c in channels),
                   file=discord.File(path), view=ConfirmSelected(ctx.author.id, ids))


class ConfirmRebuild(discord.ui.View):
    def __init__(self, owner_id, ids, prefix):
        super().__init__(timeout=90)
        self.owner_id = owner_id
        self.ids = ids
        self.prefix = prefix
        self.running = False

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('Chỉ chủ máy chủ có thể xác nhận.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Xác nhận tái tạo kênh', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.running:
            return await interaction.response.send_message('Đang thực hiện.', ephemeral=True)
        self.running = True
        self.stop()
        await interaction.response.edit_message(content='Đã xác nhận. Bắt đầu tái tạo kênh; theo dõi kết quả trong kênh này.', view=None)
        guild = interaction.guild
        deleted, failed, created = [], [], []
        for cid in self.ids:
            channel = guild.get_channel(cid)
            if channel is None or cid == interaction.channel_id:
                failed.append(cid)
                continue
            try:
                await channel.delete(reason=f'Owner-approved channel rebuild by {interaction.user.id}')
                deleted.append(cid)
                await asyncio.sleep(1.5)
            except (discord.Forbidden, discord.HTTPException):
                failed.append(cid)
        # A failed deletion must not lead to further irreversible changes.
        if failed:
            return await interaction.followup.send(
                f'Đã xóa {len(deleted)} kênh được chọn; {len(failed)} kênh xóa thất bại. '
                'Đã dừng trước bước tạo kênh. Xem bản sao lưu đã gửi.', ephemeral=True)
        # Discord servers have a finite channel limit; avoid unnecessary requests.
        remaining_capacity = max(0, 500 - len(guild.channels))
        if remaining_capacity < 200:
            return await interaction.followup.send(
                f'Đã xóa {len(deleted)} kênh được chọn, nhưng máy chủ chỉ còn '
                f'{remaining_capacity} vị trí kênh theo giới hạn 500. Không tạo kênh mới.', ephemeral=True)
        for i in range(1, 201):
            try:
                c = await guild.create_text_channel(
                    f'{self.prefix}-{i:03d}',
                    reason=f'Owner-approved rebuild by {interaction.user.id}')
                created.append(c.id)
                await asyncio.sleep(1.5)
            except (discord.Forbidden, discord.HTTPException) as exc:
                await interaction.followup.send(
                    f'Đã xóa {len(deleted)} kênh; tạo được {len(created)}/200 kênh. '
                    f'Dừng do lỗi {type(exc).__name__}. Không tự thử lại vô hạn.', ephemeral=True)
                return
        await interaction.followup.send(
            f'Hoàn thành: xóa {len(deleted)} kênh đã chọn và tạo {len(created)}/200 kênh mới.',
            ephemeral=True)

    @discord.ui.button(label='Hủy', style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content='Đã hủy tái tạo kênh.', view=None)
        self.stop()


@bot.command()
@owner_only()
async def nuke(ctx, *channel_ids: int):
    ids = list(dict.fromkeys(channel_ids))
    if not 1 <= len(ids) <= 10:
        return await ctx.send('Cú pháp: `$nuke <ID1> <ID2> ...` (1–10 ID kênh cần xóa).')
    if ctx.channel.id in ids:
        return await ctx.send('Không thể chọn kênh đang dùng để xác nhận.')
    selected = [ctx.guild.get_channel(cid) for cid in ids]
    if any(c is None for c in selected):
        return await ctx.send('Một hoặc nhiều ID kênh không hợp lệ.')
    if not ctx.guild.me.guild_permissions.manage_channels:
        return await ctx.send('Bot cần quyền Manage Channels.')
    if len(ctx.guild.channels) - len(ids) + 200 > 500:
        return await ctx.send('Sau khi xóa các kênh đã chọn, máy chủ sẽ vượt giới hạn 500 kênh. Hãy chọn lại.')
    data = {'guild_id': ctx.guild.id, 'created_at': datetime.now(timezone.utc).isoformat(),
            'selected_for_deletion': ids,
            'channels': [{'id': c.id, 'name': c.name, 'type': str(c.type),
                          'position': c.position, 'category_id': getattr(c, 'category_id', None)}
                         for c in ctx.guild.channels]}
    path = BACKUP_DIR / f'prenuke_{ctx.guild.id}_{datetime.now(timezone.utc):%Y%m%d_%H%M%S_%f}.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    await ctx.send('**Xác nhận tái tạo kênh**\n'
                   'Sẽ xóa CHỈ các kênh đã chọn: ' + ', '.join(f'`{c.name}`' for c in selected) +
                   '\nSau đó tạo 200 kênh văn bản `hbao-001` đến `hbao-200`. '
                   'Không xóa kênh hiện tại. Sao lưu JSON không chứa tin nhắn hay toàn bộ quyền. '
                   'Thao tác xóa không thể hoàn tác tự động.',
                   file=discord.File(path), view=ConfirmRebuild(ctx.author.id, ids, 'hbao'))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.CheckFailure):
        return await ctx.send('Lệnh này chỉ dành cho chủ máy chủ.')
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send('Thiếu tham số. Dùng `$help` để xem cú pháp.')
    if isinstance(error, commands.BadArgument):
        return await ctx.send('Tham số không hợp lệ. Dùng `$help` để xem cú pháp.')
    await ctx.send(f'Lỗi: {type(error).__name__}. Kiểm tra console để biết thêm.')
    raise error


if __name__ == '__main__':
    if not TOKEN:
        raise RuntimeError('Thiếu DISCORD_TOKEN trong .env')
    bot.run(TOKEN)
