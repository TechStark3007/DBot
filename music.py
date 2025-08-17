import discord
import os
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
from permissions import can_control, role_only

load_dotenv()
guild_id = int(os.getenv('DISCORD_GUILD_ID'))

# YouTube DL configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': 'in_playlist'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

valid_domains = ['youtube.com', 'youtu.be']

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.id = data.get('id')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicControls(discord.ui.View):
    def __init__(self, bot, cog, interaction_user):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog
        self.interaction_user = interaction_user
        self.allowed_roles = ("Owner", "Admin", "Moderator")
        
        # Initial button state setup
        self.update_button_states()

    def update_button_states(self):
        """Update button states based on current permissions"""
        can_control_music = can_control(
            self.interaction_user,
            self.cog.current_song.get("requester"),
            self.allowed_roles
        )
        
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = not can_control_music

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """This is called before any button callback and can prevent the callback from executing"""
        if not can_control(interaction.user, self.cog.current_song.get("requester"), self.allowed_roles):
            await interaction.response.send_message("Error: Admin Rights required", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.red, custom_id="music_stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            return await interaction.response.send_message("Nothing is playing.", ephemeral=True)

        voice_client.stop()
        await interaction.response.send_message("⏹️ Stopped the music.", ephemeral=True)

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.grey, custom_id="music_pause")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            return await interaction.response.send_message("Nothing is playing.", ephemeral=True)

        voice_client.pause()
        await interaction.response.send_message("⏸️ Paused the music.", ephemeral=True)

    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.green, custom_id="music_resume")
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_paused():
            return await interaction.response.send_message("Nothing is paused.", ephemeral=True)

        voice_client.resume()
        await interaction.response.send_message("▶️ Resumed the music.", ephemeral=True)

    @discord.ui.button(label="🔈 -10%", style=discord.ButtonStyle.grey, row=1, custom_id="music_vol_down")
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_volume = max(0, self.cog.volume - 0.1)
        self.cog.volume = new_volume
        
        if interaction.guild.voice_client and interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = new_volume
        
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="Volume", value=f"{int(new_volume*100)}%", inline=True)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="🔊 +10%", style=discord.ButtonStyle.grey, row=1, custom_id="music_vol_up")
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_volume = min(1.0, self.cog.volume + 0.1)
        self.cog.volume = new_volume
        
        if interaction.guild.voice_client and interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = new_volume
        
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="Volume", value=f"{int(new_volume*100)}%", inline=True)
        await interaction.response.edit_message(embed=embed)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_song = None
        self.queue_lock = asyncio.Lock()
        self.volume = 0.5
        self.loop = False

    def format_duration(self, seconds):
        if seconds is None:
            return "Live"
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @app_commands.command(name="join", description="Join your voice channel")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def join(self, interaction: discord.Interaction):
        if interaction.user.voice:
            await interaction.user.voice.channel.connect()
            await interaction.response.send_message(f"Joined **{interaction.user.voice.channel}** 💋")
        else:
            await interaction.response.send_message("Join a voice channel first, love 😏", ephemeral=True)

    @app_commands.command(name="leave", description="Leave the voice channel")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Disconnected 🎶")
        else:
            await interaction.response.send_message("Not connected to any voice channel.", ephemeral=True)

    @app_commands.command(name="play", description="Play a song from URL or add to queue")
    @app_commands.describe(url="YouTube URL to play")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def play(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()

        # URL validation
        if not any(domain in url for domain in valid_domains):
            return await interaction.followup.send(
                "❌ Invalid URL! Only YouTube links allowed",
                ephemeral=True
            )
        
        # Ensure bot is connected
        if not interaction.guild.voice_client:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
            else:
                return await interaction.followup.send("Join a voice channel first!", ephemeral=True)

        try:
            player = await YTDLSource.from_url(url, stream=True)
            song = {
                'title': player.title,
                'url': url,
                'duration': player.duration,
                'id': player.id,
                'requester': interaction.user
            }

            async with self.queue_lock:  # 👀 nobody slips past the lock
                # If nothing playing → start immediately
                if not self.current_song and not interaction.guild.voice_client.is_playing():
                    self.current_song = song
                    start_now = True
                else:
                    if len(self.queue) >= 10:
                        return await interaction.followup.send(
                            "❌ The queue is full. Please wait until a song finishes playing", 
                            ephemeral=True
                        )
                    self.queue.append(song)
                    start_now = False

            # 🔓 lock released here, safe to do the heavy stuff
            if start_now:
                embed = discord.Embed(
                    title="🎶 Now Playing",
                    description=f"[{player.title}]({url})",
                    color=discord.Color.blurple()
                )
                embed.set_thumbnail(url=f"https://img.youtube.com/vi/{player.id}/hqdefault.jpg")
                embed.add_field(name="Volume", value=f"{int(self.volume*100)}%", inline=True)
                embed.add_field(name="Duration", value=self.format_duration(player.duration), inline=True)
                embed.add_field(name="Requested by", value=interaction.user.mention, inline=True)

                view = MusicControls(self.bot, self, interaction.user)

                interaction.guild.voice_client.play(
                    player,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.on_playback_finished(interaction.channel, e),
                        self.bot.loop
                    )
                )
                interaction.guild.voice_client.source.volume = self.volume
                await interaction.followup.send(embed=embed, view=view)
            else:
                    await interaction.followup.send(
                        f"➕ #{len(self.queue)} Queued: **{song['title']}** 🎶"
                    )

            
        except Exception as e:
            await interaction.followup.send(f"❌ Error playing song: {str(e)}", ephemeral=True)


    async def on_playback_finished(self, channel, error):
        if error:
            await channel.send(f"Playback error: {error}")
            return

        # 🔒 protect queue ops
        async with self.queue_lock:
            if self.loop and self.current_song:
                next_song = self.current_song
            elif self.queue:
                next_song = self.queue.pop(0)
                self.current_song = next_song
            else:
                self.current_song = None
                return

        # 🎵 fetch and play next track
        player = await YTDLSource.from_url(next_song['url'], stream=True)
        channel.guild.voice_client.play(
            player,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.on_playback_finished(channel, e),
                self.bot.loop
            )
        )
        channel.guild.voice_client.source.volume = self.volume

        # 🔁 loop message
        if self.loop:
            await channel.send("🔁 Looping current song...")

        # ✨ pretty embed for new track
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"[{player.title}]({next_song['url']})",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=f"https://img.youtube.com/vi/{next_song['id']}/hqdefault.jpg")
        embed.add_field(name="Volume", value=f"{int(self.volume*100)}%", inline=True)
        embed.add_field(name="Duration", value=self.format_duration(player.duration), inline=True)
        embed.add_field(name="Requested by", value=next_song['requester'].mention, inline=True)

        await channel.send(embed=embed)



    @app_commands.command(name="stop", description="Stop playback")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏹️ Stopped playback.")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="queue", description="Show current queue")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def show_queue(self, interaction: discord.Interaction):
        if not self.queue:
            return await interaction.response.send_message("The queue is empty!", ephemeral=True)
        
        embed = discord.Embed(title="🎶 Music Queue", color=discord.Color.gold())
        
        for i, item in enumerate(self.queue[:10], 1):
            embed.add_field(
                name=f"{i}. {item['title']}",
                value=f"Requested by {item['requester'].mention}",
                inline=False
            )
        
        if len(self.queue) > 10:
            embed.set_footer(text=f"And {len(self.queue) - 10} more songs...")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Show current song info")
    @app_commands.guilds(discord.Object(id=guild_id))
    async def now_playing(self, interaction: discord.Interaction):
        if not self.current_song:
            return await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
        
        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"[{self.current_song['title']}]({self.current_song['url']})",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=f"https://img.youtube.com/vi/{self.current_song['id']}/hqdefault.jpg")
        embed.add_field(name="Volume", value=f"{int(self.volume*100)}%", inline=True)
        embed.add_field(name="Duration", value=self.format_duration(self.current_song['duration']), inline=True)
        embed.add_field(name="Requested by", value=self.current_song['requester'].mention, inline=True)
        
        view = MusicControls(self.bot, self, interaction.user)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="loop", description="Toggle looping of current song")
    @app_commands.guilds(discord.Object(id=guild_id))
    @role_only("owner", "Admin", "Moderator")
    async def toggle_loop(self, interaction: discord.Interaction):
        self.loop = not self.loop
        status = "enabled" if self.loop else "disabled" 
        await interaction.response.send_message(f"🔁 Loop {status} for current song.")

async def setup(bot):
    music_cog = Music(bot)
    await bot.add_cog(music_cog)
    # bot.add_view(MusicControls(bot, music_cog))