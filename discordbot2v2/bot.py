import asyncio
from discord.ext import commands
import urllib.request
from bs4 import BeautifulSoup


# invite link: https://discordapp.com/oauth2/authorize?client_id=549333131954618368&scope=bot&permissions=0


def read_token(file):
    with open(file, "r") as source:
        lines = source.readlines()
        return lines[0].strip()


token = read_token("token.txt")

client = commands.Bot(command_prefix="+")
songs = asyncio.Queue()
play_next_song = asyncio.Event()
players = []


def search(text): # basic youtube search function
    query = urllib.parse.quote_plus(text)
    url = "https://www.youtube.com/results?search_query=" + query
    response = urllib.request.urlopen(url)
    html = response.read()
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    result = ""
    i = 1
    for vid in soup.findAll(attrs={'class': 'yt-uix-tile-link'}):
        results.append('https://www.youtube.com' + vid['href'])
        result += ("(%d). " % i + vid['title'] + "\n")
        i = i + 1
    results.append(result)
    return results


@client.event
async def on_ready():
    print("Bot is ready! ")


@client.command(pass_context=True)
async def join(ctx):
    channel = ctx.message.author.voice.voice_channel
    await client.join_voice_channel(channel)
    await client.send_message(ctx.message.channel, "Bot is ready!")


@client.command(pass_context=True)
async def leave(ctx):
    server = ctx.message.server
    voice_client = client.voice_client_in(server)
    await voice_client.disconnect()


async def audio_player_task():
    while True:
        play_next_song.clear()
        current = await songs.get()
        current.start()
        await play_next_song.wait()


def toogle_next():
    client.loop.call_soon_threadsafe(play_next_song.set)


@client.command(pass_context=True)
async def play(ctx, *, text):
    if not client.is_voice_connected(ctx.message.server):
        voice = await client.join_voice_channel(ctx.message.author.voice_channel)
    else:
        voice = client.voice_client_in(ctx.message.server)
    results = search(text)
    await client.send_message(ctx.message.channel, results[-1] + 'choose with {number}')
    msg = await client.wait_for_message(author=ctx.message.author)
    player = await voice.create_ytdl_player(results[int(msg.content) - 1], ytdl_options={
        'loglevel': 'quiet',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192'
        }],
        'postprocessor_args': [
            '-ar', '16000'
        ],
        'prefer_ffmpeg': True,
        'keepvideo': False
    },
                                            after=toogle_next)
    players.append(player)
    await client.send_message(ctx.message.channel, player.title + " has been added to the queue!")
    await songs.put(player)


@client.command(pass_context=True)
async def pause():
    players[0].pause()


@client.command(pass_context=True)
async def resume():
    players[0].resume()


@client.command(pass_context=True)
async def skip():
    players[0].stop()
    del players[0]


client.loop.create_task(audio_player_task())
client.run(token)
