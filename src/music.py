import asyncio
import os
from functools import partial

import discord
from discord.ext import commands
from loguru import logger
from youtube_dl import YoutubeDL

ytdlopts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    "before_options": "-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = YoutubeDL(ytdlopts)


async def run_as_async(func, *args, loop=None, **kwargs):
    """Function used to convert synchronous functions to asynchrounous ones"""
    loop = loop or asyncio.get_event_loop()
    to_run = partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, to_run)


class MusicPlayer(commands.Cog):
    __slots__ = "bot"

    def __init__(self, bot):
        self.bot = bot
        self.loop = asyncio.get_event_loop()

    async def handle_voice_connection(self, ctx):
        channel_to_switch = ctx.author.voice.channel

        if ctx.voice_client:
            if ctx.voice_client.channel.id != channel_to_switch.id:
                logger.info("disconnection")
                ctx.voice_client.cleanup()
        else:
            logger.info(f"connecting to {channel_to_switch}")
            await channel_to_switch.connect()

    async def get_song_query(self, query):
        logger.debug(f"searching for {query}")

        search_response = await run_as_async(
            ytdl.extract_info, **dict(url=query, download=False)
        )

        search_result_url = search_response["entries"][0]["webpage_url"]

        item_result = await run_as_async(
            ytdl.extract_info, **dict(url=search_result_url, download=False)
        )
        stream_link = item_result["url"]
        logger.debug("Found stream link")
        return stream_link

    async def get_song_link(self, link):
        item_result = await run_as_async(
            ytdl.extract_info, **dict(url=link, download=False)
        )
        stream_link = item_result["url"]
        logger.debug("Found stream link")
        return stream_link

    async def handle_search_term(self, search_term, ctx):
        # https://youtu.be/b74GiMB08UE
        if search_term:
            if "youtu.be" in search_term or "youtube.com" in search_term:
                return await self.get_song_link(link=search_term)
            else:
                return await self.get_song_query(query=search_term)
        else:
            await ctx.send(
                f"**{ctx.message.author.name}**, what do you want me to play dude?",
                delete_after=5,
            )

    @commands.command(name="play", aliases=["p", "search"])
    async def find_and_play_song(self, ctx):
        """
        Type "!help play" for more info.

        Example usage:

            play way back home
            play https://youtu.be/b74GiMB08UE

        Search for a song on youtube and play it. If no search term was given it will try to continue paused song.
        """
        await self.handle_voice_connection(ctx)

        # Handle case when song is paused and `play` used to continue
        if (
            ctx.author.voice.channel.id in MusicStore.players
            and ctx.voice_client
            and ctx.voice_client.is_paused()
        ):
            return ctx.voice_client.resume()

        search_term = " ".join(ctx.message.content.split(" ")[1:])
        stream_link = await self.handle_search_term(search_term=search_term, ctx=ctx)

        if stream_link:
            if not ctx.voice_client:
                await self.handle_voice_connection(ctx)

            if ctx.voice_client.is_playing():
                logger.info("Stopping song that is playing currently.")
                ctx.voice_client.stop()

            source = MusicSource(discord.FFmpegPCMAudio(stream_link, **ffmpegopts))
            source.volume = 0.50  # make it less noisy by default

            MusicStore.players[ctx.author.voice.channel.id] = source

            # Do it lately to avoid pauses
            if ctx.voice_client and ctx.voice_client.is_playing():
                ctx.voice_client.stop()

            ctx.voice_client.play(source)

            logger.info(f"Playing: {search_term}")
            await ctx.send(f"Playing: **{search_term}**", delete_after=5)

    @commands.command(name="volume", aliases=["v"])
    async def modify_volume(self, ctx):
        """Set volume between 1 and 100"""
        if ctx.author.voice.channel.id not in MusicStore.players:
            await ctx.send(
                f"**{ctx.message.author.name}**, music is not playing right now",
                delete_after=5,
            )

        search_term = " ".join(ctx.message.content.split(" ")[1:])
        try:
            volume = int(search_term)
            if not 1 < volume < 101:
                raise ValueError
            volume_value = volume / 100
            MusicStore.players[ctx.author.voice.channel.id].volume = volume_value

            await ctx.send(
                f"**{ctx.message.author.name}**, volume is set to **{volume}**",
                delete_after=5,
            )

        except ValueError:
            await ctx.send(
                f"**{ctx.message.author.name}**, volume must be between 1 and 100",
                delete_after=5,
            )

    @commands.command(name="pause", aliases=["hold"])
    async def pause_song(self, ctx):
        """Pause a song"""
        if ctx.author.voice.channel.id not in MusicStore.players:
            await ctx.send(
                f"**{ctx.message.author.name}**, music is not playing right now",
                delete_after=5,
            )

        ctx.voice_client.pause()

    @commands.command(name="resume", aliases=["continue"])
    async def resume_song(self, ctx):
        """Resume a song"""
        if ctx.author.voice.channel.id not in MusicStore.players:
            await ctx.send(
                f"**{ctx.message.author.name}**, music is not playing right now",
                delete_after=5,
            )

        ctx.voice_client.resume()

    @commands.command(name="stop", aliases=["halt"])
    async def stop_song(self, ctx):
        """Stops current song and makes bot leave the chat"""
        await self.cleanup(ctx)

    @commands.command(name="dbg", aliases=["debug"])
    async def debug_command(self, ctx):
        """Print out debug message"""
        message = f"""
```
Players: {MusicStore.players or "no players"}
Client: {ctx.voice_client and "connected" or "not connected"}
isPlaying: {ctx.voice_client and ctx.voice_client.is_playing() and "yes" or "not playing"}
```
        """
        await ctx.send(message, delete_after=3)

    async def cleanup(self, ctx):
        logger.debug("Invoking cleanup")

        try:
            await ctx.voice_client.disconnect()
        except Exception as e:
            logger.debug(e)

        try:
            ctx.voice_client.cleanup()
        except Exception as e:
            logger.debug(e)

        logger.debug("Finished cleanup")


class MusicSource(discord.PCMVolumeTransformer):
    def __init__(self, source):
        super().__init__(source)


class MusicStore:
    players = {}
