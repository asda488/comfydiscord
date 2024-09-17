import discord
from image import gen_image
import io

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

generating = False

id = 0 #channel id
token = None #discord token

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    global generating
    if message.channel.id == id and message.author != client.user and client.user.mentioned_in(message):
        if not generating:
            generating = True
            text = message.content.replace(f"<@{client.user.id}>", "")
            print(message.content)
            await message.channel.send(f"Generating with prompt \"{text}\" (please wait 1-2 minutes)")
            image_bytes, name = gen_image(text)
            await message.channel.send(file=discord.File(io.BytesIO(image_bytes), filename=f"{name}.png", spoiler=True))
            generating = False
        """
        else:
            message.channel.send(f"Currently generating, your prompt will be ignored, please try again after current generation")
        """

client.run('token')