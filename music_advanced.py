import discord
import os
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
from datetime import datetime
import math

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

# YouTube DL configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': 'in_playlist',
    'default_search': 'ytsearch',
    'geo-bypass': True,
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af loudnorm=I=-16:LRA=11:TP=-1.5'
}

valid_domains = ['youtube.com', 'youtu.be', 'soundcloud.com', 'bandcamp.com']

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.id = data.get('id')
        self.thumbnail = data.get('thumbnail', f'https://img.youtube.com/vi/{self.id}/maxresdefault.jpg')
        self.uploader = data.get('uploader', 'Unknown Artist')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            
            if 'entries' in data:
                data = data['entries'][0]
            
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            raise Exception(f"Couldn't process the song: {str(e)}")

class MusicControls(discord.ui.View):
    def __init__(self, bot, cog):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog
    
    def create_progress_bar(self, position, duration):
        if duration == 0 or duration is None:
            return "🔴 LIVE"
        
        progress = min(position / duration * 100, 100)
        filled = int(progress // 5)
        empty = 20 - filled
        return f"`{'█' * filled}{'░' * empty}` {self.cog.format_duration(position)} / {self.cog.format_duration(duration)}"
    
    async def update_embed(self, interaction):
        if not self.cog.current_song:
            return
        
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"[{self.cog.current_song['title']}]({self.cog.current_song['url']})",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=self.cog.current_song['thumbnail'])
        
        # Add progress bar if not live
        if self.cog.current_song['duration']:
            position = self.cog.get_current_position()
            progress = self.create_progress_bar(position, self.cog.current_song['duration'])
            embed.add_field(name="Progress", value=progress, inline=False)
        
        embed.add_field(name="Artist", value=self.cog.current_song.get('uploader', 'Unknown'), inline=True)
        embed.add_field(name="Volume", value=f"🔊 {int(self.cog.volume*100)}%", inline=True)
        embed.add_field(name="Requested by", value=self.cog.current_song['requester'].mention, inline=True)
        
        status = "🔁 Enabled" if self.cog.loop else "🔁 Disabled"
        embed.add_field(name="Loop", value=status, inline=True)
        
        queue_status = f"🎵 {len(self.cog.queue)} in queue"
        embed.add_field(name="Queue", value=queue_status, inline=True)
        
        return embed
    
    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.red, custom_id="music_stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            embed = await self.update_embed(interaction)
            embed.title = "⏹️ Playback Stopped"
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
    
    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.grey, custom_id="music_pause")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.green
            embed = await self.update_embed(interaction)
            embed.title = "⏸️ Playback Paused"
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.green, custom_id="music_resume")
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.grey
            embed = await self.update_embed(interaction)
            embed.title = "▶️ Playback Resumed"
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)
    
    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.grey, custom_id="music_shuffle")
    async def shuffle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.cog.queue) > 1:
            import random
            random.shuffle(self.cog.queue)
            await interaction.response.send_message("🔀 Queue shuffled!", ephemeral=True)
        else:
            await interaction.response.send_message("Not enough songs in queue to shuffle.", ephemeral=True)
    
    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.grey, custom_id="music_loop")
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cog.loop = not self.cog.loop
        if self.cog.loop:
            button.style = discord.ButtonStyle.green
            await interaction.response.send_message("🔁 Loop enabled for current song.", ephemeral=True)
        else:
            button.style = discord.ButtonStyle.grey
            await interaction.response.send_message("🔁 Loop disabled.", ephemeral=True)
        
        embed = await self.update_embed(interaction)
        await interaction.message.edit(embed=embed, view=self)
    
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.grey, custom_id="music_skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped to next song.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
    
    @discord.ui.button(emoji="🔈", style=discord.ButtonStyle.grey, custom_id="music_vol_down")
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_volume = max(0, self.cog.volume - 0.1)
        self.cog.volume = new_volume
        if interaction.guild.voice_client and interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = new_volume
        
        embed = await self.update_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.grey, custom_id="music_vol_up")
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_volume = min(1.0, self.cog.volume + 0.1)
        self.cog.volume = new_volume
        if interaction.guild.voice_client and interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = new_volume
        
        embed = await self.update_embed(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_song = None
        self.volume = 0.5
        self.loop = False
        self.play_time = None
        self.last_update = None

    def get_current_position(self):
        if not self.play_time or not self.current_song or not self.current_song['duration']:
            return 0
        
        if self.bot.voice_clients and self.bot.voice_clients[0].is_paused():
            return (self.last_update - self.play_time).total_seconds()
        
        return (datetime.now() - self.play_time).total_seconds()

    def format_duration(self, seconds):
        if seconds is None:
            return "Live"
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    async def ensure_voice(self, interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("You need to be in a voice channel to use this command!", ephemeral=True)
            return False
        
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()
        
        elif interaction.guild.voice_client.channel != interaction.user.voice.channel:
            await interaction.response.send_message("I'm already in a different voice channel!", ephemeral=True)
            return False
        
        return True

    @app_commands.command(name="join", description="Join your voice channel")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def join(self, interaction: discord.Interaction):
        if not await self.ensure_voice(interaction):
            return
        
        embed = discord.Embed(
            description=f"Joined {interaction.user.voice.channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave", description="Leave the voice channel")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            self.queue.clear()
            self.current_song = None
            
            embed = discord.Embed(
                description="Left the voice channel and cleared the queue",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("I'm not in a voice channel!", ephemeral=True)

    @app_commands.command(name="play", description="Play a song from URL or search query")
    @app_commands.describe(query="YouTube URL or search query")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        if not await self.ensure_voice(interaction):
            return
        
        # Check if it's a URL or search query
        is_url = any(domain in query for domain in valid_domains)
        
        try:
            if is_url:
                player = await YTDLSource.from_url(query, stream=True)
            else:
                # Search YouTube
                player = await YTDLSource.from_url(f"ytsearch:{query}", stream=True)
            
            song_data = {
                'title': player.title,
                'url': player.url if is_url else f"https://youtube.com/watch?v={player.id}",
                'duration': player.duration,
                'id': player.id,
                'requester': interaction.user,
                'thumbnail': player.thumbnail,
                'uploader': player.uploader
            }
            
            if interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused():
                self.queue.append(song_data)
                
                embed = discord.Embed(
                    description=f"🎵 Added to queue: [{player.title}]({song_data['url']})",
                    color=discord.Color.gold()
                )
                embed.set_thumbnail(url=player.thumbnail)
                embed.add_field(name="Position in queue", value=f"#{len(self.queue)}", inline=True)
                embed.add_field(name="Duration", value=self.format_duration(player.duration), inline=True)
                await interaction.followup.send(embed=embed)
                return
            
            await self.play_song(interaction, song_data)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Couldn't play the song: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

    async def play_song(self, interaction, song_data):
        self.current_song = song_data
        self.play_time = datetime.now()
        
        try:
            player = await YTDLSource.from_url(song_data['url'], stream=True)
            
            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"[{song_data['title']}]({song_data['url']})",
                color=discord.Color.blurple()
            )
            embed.set_thumbnail(url=song_data['thumbnail'])
            
            if song_data['duration']:
                embed.add_field(name="Duration", value=self.format_duration(song_data['duration']), inline=True)
            else:
                embed.add_field(name="Duration", value="Live", inline=True)
            
            embed.add_field(name="Artist", value=song_data.get('uploader', 'Unknown'), inline=True)
            embed.add_field(name="Requested by", value=song_data['requester'].mention, inline=True)
            
            view = MusicControls(self.bot, self)
            
            interaction.guild.voice_client.play(
                player, 
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.on_playback_finished(interaction.channel, e),
                    self.bot.loop
                )
            )
            
            interaction.guild.voice_client.source.volume = self.volume
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Playback Error",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)

    async def on_playback_finished(self, channel, error):
        self.last_update = datetime.now()
        
        if error:
            error_embed = discord.Embed(
                title="❌ Playback Error",
                description=str(error),
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)
        
        if self.loop and self.current_song:
            await self.play_song_from_data(channel, self.current_song)
            return
        
        if self.queue:
            next_song = self.queue.pop(0)
            await self.play_song_from_data(channel, next_song)
        else:
            self.current_song = None
            # Optionally send a message when queue is empty
            # embed = discord.Embed(description="Queue is empty! Add more songs with /play", color=discord.Color.blue())
            # await channel.send(embed=embed)

    async def play_song_from_data(self, channel, song_data):
        self.current_song = song_data
        self.play_time = datetime.now()
        
        try:
            player = await YTDLSource.from_url(song_data['url'], stream=True)
            
            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"[{song_data['title']}]({song_data['url']})",
                color=discord.Color.blurple()
            )
            embed.set_thumbnail(url=song_data['thumbnail'])
            
            if song_data['duration']:
                embed.add_field(name="Duration", value=self.format_duration(song_data['duration']), inline=True)
            else:
                embed.add_field(name="Duration", value="Live", inline=True)
            
            embed.add_field(name="Artist", value=song_data.get('uploader', 'Unknown'), inline=True)
            embed.add_field(name="Requested by", value=song_data['requester'].mention, inline=True)
            
            view = MusicControls(self.bot, self)
            
            channel.guild.voice_client.play(
                player,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.on_playback_finished(channel, e),
                    self.bot.loop
                )
            )
            channel.guild.voice_client.source.volume = self.volume
            
            await channel.send(embed=embed, view=view)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Playback Error",
                description=str(e),
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)

    @app_commands.command(name="skip", description="Skip the current song")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def skip(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            embed = discord.Embed(
                description=f"⏭️ Skipped by {interaction.user.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="queue", description="Show current queue")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def show_queue(self, interaction: discord.Interaction):
        if not self.queue and not self.current_song:
            embed = discord.Embed(
                description="The queue is empty! Use `/play` to add songs.",
                color=discord.Color.blue()
            )
            return await interaction.response.send_message(embed=embed)
        
        embed = discord.Embed(title="🎶 Music Queue", color=discord.Color.gold())
        
        # Show currently playing
        if self.current_song:
            embed.add_field(
                name="Now Playing",
                value=f"[{self.current_song['title']}]({self.current_song['url']})",
                inline=False
            )
        
        # Show next up to 10 songs
        for i, item in enumerate(self.queue[:10], 1):
            duration = self.format_duration(item['duration']) if item['duration'] else "Live"
            embed.add_field(
                name=f"{i}. {item['title']}",
                value=f"`{duration}` | Requested by {item['requester'].mention}",
                inline=False
            )
        
        if len(self.queue) > 10:
            remaining = len(self.queue) - 10
            embed.set_footer(text=f"Plus {remaining} more song{'s' if remaining > 1 else ''} in queue")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Show current song info")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def now_playing(self, interaction: discord.Interaction):
        if not self.current_song:
            embed = discord.Embed(
                description="Nothing is playing right now.",
                color=discord.Color.blue()
            )
            return await interaction.response.send_message(embed=embed)
        
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"[{self.current_song['title']}]({self.current_song['url']})",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=self.current_song['thumbnail'])
        
        if self.current_song['duration']:
            position = self.get_current_position()
            progress = MusicControls(self.bot, self).create_progress_bar(position, self.current_song['duration'])
            embed.add_field(name="Progress", value=progress, inline=False)
        else:
            embed.add_field(name="Status", value="🔴 LIVE", inline=False)
        
        embed.add_field(name="Artist", value=self.current_song.get('uploader', 'Unknown'), inline=True)
        embed.add_field(name="Volume", value=f"🔊 {int(self.volume*100)}%", inline=True)
        embed.add_field(name="Requested by", value=self.current_song['requester'].mention, inline=True)
        
        view = MusicControls(self.bot, self)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="loop", description="Toggle looping of current song")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def toggle_loop(self, interaction: discord.Interaction):
        self.loop = not self.loop
        status = "🔁 Enabled" if self.loop else "🔁 Disabled"
        
        embed = discord.Embed(
            description=f"{status} for current song.",
            color=discord.Color.green() if self.loop else discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def shuffle_queue(self, interaction: discord.Interaction):
        if len(self.queue) > 1:
            import random
            random.shuffle(self.queue)
            embed = discord.Embed(
                description="🔀 Queue shuffled!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                description="Not enough songs in queue to shuffle.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # @app_commands.command(name="clear", description="Clear the queue")
    # @app_commands.guilds(discord.Object(id=guild_id))
    # async def clear_queue(self, interaction: discord.Interaction):
    #     if self.queue:
    #         self.queue.clear()
    #         embed = discord.Embed(
    #             description="🗑️ Queue cleared!",
    #             color=discord.Color.green()
    #         )
    #         await interaction.response.send_message(embed=embed)
    #     else:
    #         embed = discord.Embed(
    #             description="The queue is already empty.",
    #             color=discord.Color.blue()
    #         )
    #         await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    music_cog = Music(bot)
    await bot.add_cog(music_cog)
    bot.add_view(MusicControls(bot, music_cog))