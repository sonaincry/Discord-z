import os
import discord
from discord.ext import commands
import yt_dlp
import asyncio

TOKEN = os.getenv("TOKEN")

# ======================================
# INTENTS
# ======================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ======================================
# BOT
# ======================================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ======================================
# ON READY
# ======================================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ======================================
# MUSIC DATA
# ======================================

song_queue = []
current_volume = 0.5

# ======================================
# MATCH DATA
# ======================================

players = []

team1 = []
team2 = []

captain1 = None
captain2 = None

current_picker = None

match_started = False

# ======================================
# FFMPEG
# ======================================

FFMPEG_OPTIONS = {
    'options': '-vn'
}

FFMPEG_LIVE_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# ======================================
# YTDLP
# ======================================

YDL_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': True
}

YDL_SEARCH_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': True,
    'default_search': 'ytsearch',
    'quiet': True,
}

YDL_LIVE_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'live_from_start': False,
    'quiet': True,
}

# ======================================
# MUSIC FUNCTIONS
# ======================================

def is_url(text):
    return text.startswith("http://") or text.startswith("https://")

def search_song(query):

    search_query = query if is_url(query) else f"ytsearch1:{query}"

    with yt_dlp.YoutubeDL(YDL_SEARCH_OPTIONS) as ydl:

        info = ydl.extract_info(
            search_query,
            download=False
        )

        if 'entries' in info:
            info = info['entries'][0]

        return {
            'url': info['webpage_url'],
            'audio_url': info['url'],
            'title': info.get('title', 'Unknown'),
        }

async def play_next(ctx):

    global current_volume

    if len(song_queue) > 0:

        next_song = song_queue.pop(0)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:

            info = ydl.extract_info(
                next_song['url'],
                download=False
            )

            audio_url = info['url']

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                audio_url,
                **FFMPEG_OPTIONS
            ),
            volume=current_volume
        )

        def after_playing(error):

            fut = asyncio.run_coroutine_threadsafe(
                play_next(ctx),
                bot.loop
            )

            try:
                fut.result()
            except Exception as e:
                print(e)

        ctx.voice_client.play(
            source,
            after=after_playing
        )

        await ctx.send(
            f'🎵 Now playing: **{next_song["title"]}**'
        )


# ======================================
# MUSIC COMMANDS
# ======================================

@bot.command()
async def play(ctx, *, query):

    if not ctx.author.voice:
        await ctx.send("❌ Join voice first.")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()

    try:
        loop = asyncio.get_event_loop()

        song = await loop.run_in_executor(
            None,
            search_song,
            query
        )

    except Exception as e:

        await ctx.send(
            f"❌ Could not find song: {e}"
        )

        return

    song_queue.append(song)

    await ctx.send(
        f'➕ Added: **{song["title"]}**'
    )

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):

    if ctx.voice_client and ctx.voice_client.is_playing():

        ctx.voice_client.stop()

        await ctx.send("⏭️ Skipped.")

@bot.command()
async def pause(ctx):

    if ctx.voice_client and ctx.voice_client.is_playing():

        ctx.voice_client.pause()

        await ctx.send("⏸️ Paused.")

@bot.command()
async def resume(ctx):

    if ctx.voice_client and ctx.voice_client.is_paused():

        ctx.voice_client.resume()

        await ctx.send("▶️ Resumed.")

@bot.command()
async def stop(ctx):

    song_queue.clear()

    if ctx.voice_client:
        ctx.voice_client.stop()

    await ctx.send("⏹️ Stopped.")

@bot.command()
async def leave(ctx):

    song_queue.clear()

    if ctx.voice_client:
        await ctx.voice_client.disconnect()

    await ctx.send("👋 Left voice.")

@bot.command()
async def queue(ctx):

    if len(song_queue) == 0:
        await ctx.send("📭 Queue empty.")
        return

    message = "📋 Queue:\n"

    for i, song in enumerate(song_queue):

        message += f"{i+1}. {song['title']}\n"

    await ctx.send(message)

@bot.command()
async def volume(ctx, vol: int):

    global current_volume

    if vol < 0 or vol > 100:
        await ctx.send("0-100 only.")
        return

    current_volume = vol / 100

    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = current_volume

    await ctx.send(f"🔊 Volume: {vol}%")
# Zo

class JoinView(discord.ui.View):

    @discord.ui.button(
        label="CHƠI",
        style=discord.ButtonStyle.green
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        global players
        global match_started

        user = interaction.user

        if match_started:
            await interaction.response.send_message(
                "Match started.",
                ephemeral=True
            )
            return

        if user in players:
            await interaction.response.send_message(
                "Already joined.",
                ephemeral=True
            )
            return

        if len(players) >= 10:
            await interaction.response.send_message(
                "Match full.",
                ephemeral=True
            )
            return

        players.append(user)

        player_text = "\n".join(
            [f"• {p.display_name}" for p in players]
        )

        msg = (
            f"🎮 MATCH LOBBY ({len(players)}/10)\n\n"
            f"{player_text}"
        )

        if len(players) == 10:
            msg += "\n\n✅ Full."

        await interaction.response.edit_message(
            content=msg,
            view=self
        )



class DraftView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        remaining = [
            p for p in players
            if p not in team1 and p not in team2
        ]

        for player in remaining:

            button = discord.ui.Button(
                label=player.display_name,
                style=discord.ButtonStyle.blurple
            )

            async def callback(interaction, p=player):

                global current_picker

                if interaction.user != current_picker:
                    await interaction.response.send_message(
                        "Chưa tới lượt bạn pick.",
                        ephemeral=True
                    )
                    return

                if p in team1 or p in team2:
                    await interaction.response.send_message(
                        "Player đã được pick.",
                        ephemeral=True
                    )
                    return

                if current_picker == captain1:
                    team1.append(p)
                    current_picker = captain2
                else:
                    team2.append(p)
                    current_picker = captain1

                remaining_players = [
                    x for x in players
                    if x not in team1 and x not in team2
                ]

                if len(remaining_players) == 1:

                    last_player = remaining_players[0]

                    if len(team1) < 5:
                        team1.append(last_player)
                    else:
                        team2.append(last_player)

                    remaining_players = []

                t1 = "\n".join(
                    [m.display_name for m in team1]
                )

                t2 = "\n".join(
                    [m.display_name for m in team2]
                )

                msg = (
                    f"🔵 TEAM 1\n{t1}\n\n"
                    f"🔴 TEAM 2\n{t2}\n\n"
                )

                if len(remaining_players) == 0:

                    msg += (
                        "🎉 CHIA TEAM HOÀN TẤT\n\n"
                        "Captain gõ !team1 để move voice."
                    )

                    await interaction.response.edit_message(
                        content=msg,
                        view=None
                    )

                    return

                msg += (
                    f"👉 Lượt tiếp theo: {current_picker.display_name}"
                )

                await interaction.response.edit_message(
                    content=msg,
                    view=DraftView()
                )

            button.callback = callback

            self.add_item(button)

# ======================================
# START MATCH
# ======================================

@bot.command()
async def chiateam(ctx):

    global players
    global team1
    global team2
    global captain1
    global captain2
    global current_picker
    global match_started

    players = []

    team1 = []
    team2 = []

    captain1 = None
    captain2 = None

    current_picker = None

    match_started = False

    await ctx.send(
        "🎮 SOLO ?",
        view=JoinView()
    )

# ======================================
# DOI TRUONG
# ======================================

@bot.command()
async def doitruong(ctx):

    global captain1
    global captain2
    global current_picker
    global match_started

    if ctx.author not in players:
        await ctx.send(
            "Bạn không nằm trong match."
        )
        return

    if captain1 == ctx.author or captain2 == ctx.author:
        await ctx.send(
            "Bạn đã là đội trưởng."
        )
        return

    if captain1 is None:

        captain1 = ctx.author
        team1.append(ctx.author)

        await ctx.send(
            f"🔵 Team 1 Captain: {captain1.display_name}"
        )

        return

    if captain2 is None:

        captain2 = ctx.author
        team2.append(ctx.author)

        current_picker = captain1

        match_started = True

        await ctx.send(
            f"🔴 Team 2 Captain: {captain2.display_name}\n\n"
            f"🎮 Draft bắt đầu!\n"
            f"👉 Lượt đầu tiên: {current_picker.display_name}",
            view=DraftView()
        )

        return

    await ctx.send("Đã đủ đội trưởng.")

# ======================================
# SHOW TEAMS
# ======================================

@bot.command()
async def teams(ctx):

    t1 = "\n".join(
        [m.display_name for m in team1]
    )

    t2 = "\n".join(
        [m.display_name for m in team2]
    )

    await ctx.send(
        f"🔵 TEAM 1\n{t1}\n\n"
        f"🔴 TEAM 2\n{t2}"
    )

# ======================================
# MOVE TEAM
# ======================================

@bot.command()
async def team1(ctx):

    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được move."
        )
        return

    voice_team1 = discord.utils.get(
        ctx.guild.voice_channels,
        name="Team 1"
    )

    voice_team2 = discord.utils.get(
        ctx.guild.voice_channels,
        name="Team 2"
    )

    if voice_team1 is None or voice_team2 is None:
        await ctx.send(
            "Không tìm thấy voice channel."
        )
        return

    for member in team1:

        if member.voice:
            await member.move_to(voice_team1)

    for member in team2:

        if member.voice:
            await member.move_to(voice_team2)

    await ctx.send(
        "🎮 Đã move teams."
    )

# ======================================
# TEAM 1 WIN
# ======================================

@bot.command()
async def team1win(ctx):
    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được report."
        )
        return

    winners = "\n".join(
        [f"{p.display_name}: +1" for p in team1]
    )

    losers = "\n".join(
        [f"{p.display_name}: -1" for p in team2]
    )

    await ctx.send(
        f"🏆 TEAM 1 WIN\n\n"
        f"{winners}\n\n"
        f"{losers}"
    )

# ======================================
# TEAM 2 WIN
# ======================================

@bot.command()
async def team2win(ctx):
    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được report."
        )
        return
    winners = "\n".join(
        [f"{p.display_name}: +1" for p in team2]
    )

    losers = "\n".join(
        [f"{p.display_name}: -1" for p in team1]
    )

    await ctx.send(
        f"🏆 TEAM 2 WIN\n\n"
        f"{winners}\n\n"
        f"{losers}"
    )

# ======================================
# END
# ======================================

@bot.command()
async def end(ctx):

    global players
    global team1
    global team2
    global captain1
    global captain2
    global current_picker
    global match_started

    if ctx.author != captain1 and ctx.author != captain2:
        await ctx.send(
            "Chỉ đội trưởng mới được end."
        )
        return

    players = []

    team1 = []
    team2 = []

    captain1 = None
    captain2 = None

    current_picker = None

    match_started = False

    await ctx.send(
        "🛑 Match reset."
    )

bot.run(TOKEN)