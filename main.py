import os
import datetime
import asyncio
import nextcord

from nextcord import Interaction, SlashOption, PermissionOverwrite
from nextcord.ext import commands
from nextcord.ext.commands import has_permissions

from sqlitedict import SqliteDict

db = SqliteDict('./db.sqlite', autocommit=True)
check_interval = datetime.timedelta(minutes=30)
voice_channel_data = "voice"
text_channel_data = "text"


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.remove_old_channels())

    async def remove_old_channels(self):
        await self.wait_until_ready()
        while not self.is_closed():
            now = datetime.datetime.today()
            for user in db.keys():
                channel_data = db[user]
                channel_id, channel_kill_time = channel_data[voice_channel_data]
                if channel_id != 0 and channel_kill_time < now:
                    channel = bot.get_channel(channel_id)
                    if channel is None:
                        del channel_data[voice_channel_data]
                    elif len(channel.members) == 0:
                        await channel.delete()
                        del channel_data[voice_channel_data]
                channel_id, channel_kill_time = channel_data[text_channel_data]
                if channel_id != 0 and channel_kill_time < now:
                    channel = bot.get_channel(channel_id)
                    if channel is not None:
                        await channel.delete()
                    del channel_data[text_channel_data]
                if len(channel_data) == 0:
                    del db[user]
                else:
                    db[user] = channel_data
            sleep_time = check_interval.seconds
            await asyncio.sleep(sleep_time)


intents = nextcord.Intents.default()  # Allow the use of custom intents
intents.members = True
bot = Bot(command_prefix=".", case_insensitive=True, intents=intents)


@bot.slash_command(name="new_voice_channel",
                   guild_ids=[int(os.environ['SERVERID'])])
async def new_voice_channel(interaction: Interaction,
                            channel_name: str = SlashOption(name="channel_name",
                                                            description="Podaj nazwę kanału",
                                                            required=True),
                            lifetime: int = SlashOption(name="lifetime",
                                                        description="Po ilu godzinach ma zostać automatycznie zlikwidowany (domyślnie 3h)",
                                                        required=False,
                                                        min_value=1,
                                                        max_value=24,
                                                        default=3)):
    creator_id = interaction.user.id
    if creator_id in db:
        channel_data = db[creator_id]
        if voice_channel_data in channel_data:
            channel_id, _ = channel_data[voice_channel_data]
            if channel_id != 0:
                channel = bot.get_channel(channel_id)
                if channel is not None:
                    await interaction.response.send_message(f"Nie możesz stworzyć kolejnego kanału głosowego, "
                                                            f"ponieważ zarządzasz już kanałem ***{channel.name}***.")
                    return

    permissions = {
        interaction.user: PermissionOverwrite(manage_permissions=True, manage_channels=True, view_channel=True),
        interaction.guild.default_role: PermissionOverwrite(view_channel=False)}
    channel = await interaction.channel.category.create_voice_channel(name=channel_name, overwrites=permissions)
    channel_lifetime = datetime.timedelta(hours=lifetime)
    data = db.setdefault(creator_id, {})
    data[voice_channel_data] = (channel.id, datetime.datetime.today() + channel_lifetime)
    db[creator_id] = data
    await interaction.response.send_message(f"Kanał głosowy ***{channel_name}***  został stworzony dla {interaction.user.mention}.")


@bot.slash_command(name="new_text_channel",
                   guild_ids=[int(os.environ['SERVERID'])])
async def new_text_channel(interaction: Interaction,
                           channel_name: str = SlashOption(name="channel_name",
                                                           description="Podaj nazwę kanału",
                                                           required=True),
                           lifetime: int = SlashOption(name="lifetime",
                                                       description="Po ilu godzinach ma zostać automatycznie zlikwidowany (domyślnie 3h)",
                                                       required=False,
                                                       min_value=1,
                                                       max_value=72,
                                                       default=3)):
    creator_id = interaction.user.id
    if creator_id in db:
        channel_data = db[creator_id]
        if text_channel_data in channel_data:
            channel_id, _ = channel_data[text_channel_data]
            if channel_id != 0:
                channel = bot.get_channel(channel_id)
                if channel is not None:
                    await interaction.response.send_message(f"Nie możesz stworzyć kolejnego kanału tekstowego, "
                                                            f"ponieważ zarządzasz już kanałem {channel.mention}.")
                    return

    permissions = {
        interaction.user: PermissionOverwrite(manage_permissions=True, manage_channels=True, view_channel=True),
        interaction.guild.default_role: PermissionOverwrite(view_channel=False)}
    channel = await interaction.channel.category.create_text_channel(name=channel_name, overwrites=permissions)
    channel_lifetime = datetime.timedelta(hours=lifetime)
    data = db.setdefault(creator_id, {})
    data[text_channel_data] = (channel.id, datetime.datetime.today() + channel_lifetime)
    db[creator_id] = data
    await interaction.response.send_message(f"Kanał tekstowy {channel.mention} został stworzony dla {interaction.user.mention}.")


@bot.command(name="flush", guild_ids=[int(os.environ['SERVERID'])])
@has_permissions(administrator=True)
async def flush(ctx):
    for key in db.keys():
        channel_data = db[key]
        if voice_channel_data in channel_data:
            channel_id, _ = channel_data[voice_channel_data]
            if channel_id != 0:
                channel = bot.get_channel(channel_id)
                if channel is not None:
                    await channel.delete()
        if text_channel_data in channel_data:
            channel_id, _ = channel_data[text_channel_data]
            if channel_id != 0:
                channel = bot.get_channel(channel_id)
                if channel is not None:
                    await channel.delete()
    db.clear()
    await ctx.send(f"Flushed all channels.")


@flush.error
async def error(ctx, _):
    await ctx.send('You have no permission to use that command')

bot.run(os.environ['TOKEN'])

