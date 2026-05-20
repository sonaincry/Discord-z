import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Queue
song_queue = []

# Default volume (50%)
current_volume = 0.5

# FFmpeg options
FFMPEG_OPTIONS = {
    'options': '-vn'
}

FFMPEG_LIVE_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

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


def is_url(text):
    return text.startswith("http://") or text.startswith("https://")


def search_song(query):
    """Search YouTube and return the best match's url and title."""
    search_query = query if is_url(query) else f"ytsearch1:{query}"

    with yt_dlp.YoutubeDL(YDL_SEARCH_OPTIONS) as ydl:
        info = ydl.extract_info(search_query, download=False)

        if 'entries' in info:
            info = info['entries'][0]

        return {
            'url': info['webpage_url'],
            'audio_url': info['url'],
            'title': info.get('title', 'Unknown'),
        }


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


async def play_next(ctx):
    global current_volume

    if len(song_queue) > 0:
        next_song = song_queue.pop(0)

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(next_song['url'], download=False)
            audio_url = info['url']

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS),
            volume=current_volume
        )

        def after_playing(error):
            if error:
                print(f"Playback error: {error}")

            fut = asyncio.run_coroutine_threadsafe(
                play_next(ctx),
                bot.loop
            )

            try:
                fut.result()
            except Exception as e:
                print(f"Queue error: {e}")

        ctx.voice_client.play(source, after=after_playing)
        await ctx.send(f'🎵 Now playing: **{next_song["title"]}**')
    else:
        await ctx.send("✅ Đã phát hết list nhạc.")


@bot.command()
async def play(ctx, *, query):
    """Play a song by URL or search keyword. E.g: !play Sorry Justin Bieber"""

    if not ctx.author.voice:
        await ctx.send("❌ Bạn cần vào voice channel trước.")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()

    if not is_url(query):
        searching_msg = await ctx.send(f'🔍 Searching for: **{query}**...')
    else:
        searching_msg = None

    try:
        loop = asyncio.get_event_loop()
        song = await loop.run_in_executor(None, search_song, query)
    except Exception as e:
        await ctx.send(f"❌ Could not find song: `{e}`")
        return

    if searching_msg:
        await searching_msg.delete()

    song_queue.append(song)
    await ctx.send(f'➕ Added to queue: **{song["title"]}**')

    if not ctx.voice_client.is_playing():
        await play_next(ctx)


@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped.")
    else:
        await ctx.send("❌ Nothing is playing.")


@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused.")
    else:
        await ctx.send("❌ Nothing is playing.")


@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed.")
    else:
        await ctx.send("❌ Nothing is paused.")


@bot.command()
async def stop(ctx):
    song_queue.clear()
    if ctx.voice_client:
        ctx.voice_client.stop()
    await ctx.send("⏹️ Đã dừng và xóa list.")


@bot.command()
async def leave(ctx):
    song_queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("👋 Đã rời phòng.")


@bot.command()
async def queue(ctx):
    if len(song_queue) == 0:
        await ctx.send("📭 Đang không có list nhạc.")
        return

    message = "📋 **Current Queue:**\n"
    for i, song in enumerate(song_queue):
        message += f"`{i+1}.` {song['title']}\n"

    await ctx.send(message)


@bot.command()
async def volume(ctx, vol: int):
    """Set volume 0-100. E.g: !volume 50"""
    global current_volume

    if not 0 <= vol <= 100:
        await ctx.send("❌ Volume phải từ khoảng 50-100.")
        return

    current_volume = vol / 100

    # Apply immediately if something is playing
    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = current_volume

    emoji = "🔇" if vol == 0 else "🔉" if vol < 50 else "🔊"
    await ctx.send(f"{emoji} Volume set to **{vol}%**")


@bot.command()
async def stream(ctx, url):
    """Stream a YouTube live audio into voice channel. E.g: !stream youtube_link"""
    global current_volume

    if not ctx.author.voice:
        await ctx.send("❌ Bạn cần vào voice channel trước.")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.is_playing():
        ctx.voice_client.stop()

    loading_msg = await ctx.send("📡 Connecting to stream...")

    try:
        loop = asyncio.get_event_loop()

        def fetch_stream():
            with yt_dlp.YoutubeDL(YDL_LIVE_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'audio_url': info['url'],
                    'title': info.get('title', 'Unknown'),
                    'is_live': info.get('is_live', False)
                }

        stream_info = await loop.run_in_executor(None, fetch_stream)

    except Exception as e:
        await loading_msg.edit(content=f"❌ Could not connect to stream: `{e}`")
        return

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(stream_info['audio_url'], **FFMPEG_LIVE_OPTIONS),
        volume=current_volume
    )

    ctx.voice_client.play(source)

    live_tag = "🔴 LIVE" if stream_info['is_live'] else "📺"
    await loading_msg.edit(content=f"{live_tag} Now streaming: **{stream_info['title']}**")


@bot.command()
async def stopstream(ctx):
    """Stop the current stream."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏹️ Stream stopped.")
    else:
        await ctx.send("❌ Nothing is streaming.")


bot.run(TOKEN)