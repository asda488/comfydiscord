import discord
from discord.ext import commands, tasks
from image import gen_image
import io
from typing import Literal
import aiohttp
import os
import json

intents = discord.Intents.all()
intents.message_content = True

client = commands.Bot(command_prefix='?', intents=intents)

generating = False

server_address = "127.0.0.1:8188"
token = None #discord token

models = ["AnythingXL_v50.safetensors"]
default_model = "AnythingXL_v50.safetensors"

@client.event
async def on_ready():
    await tryContactServer()
    cmd_tree = await client.tree.sync()
    print(f"cmds sync'd> {str(len(cmd_tree))}")
    print(f"Logged in as {client.user}")

async def tryContactServer():
    global models
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(3)) as session:
                async with session.get(f"http://{server_address}/internal/files", params={"directory": "models"}) as resp:
                    body = await resp.text()
                    models = parseModelsFromJson(json.loads(body))
                    print(f"Bot synced new models from {server_address}, models: {models}")
    except Exception as e:
        print(f"Bot was unable to sync models, falling back to default, exception: {e}")

def parseModelsFromJson(json):
    newModels = []
    for item in json["files"]:
        if os.path.split(item["path"])[0] == "checkpoints" and item["type"] == "file" and item["name"] != "put_checkpoints_here":
            newModels.append(item["name"])
    return newModels

# reply with the button
class ImageView(discord.ui.View):
    def __init__(self, prompt, negative, model=default_model, image_count=1, anime=False):
        super().__init__()
        self.prompt = prompt
        self.negative = negative
        self.model = model
        self.image_count = image_count
        self.anime = anime

    @discord.ui.button(label="Generate Again", style=discord.ButtonStyle.primary)
    async def generate_again(self, button_interaction: discord.Interaction, button: discord.ui.Button):
        global generating
        if not generating:
            try:
                generating = True
                await button_interaction.response.defer(thinking=True)

                print(f"Image generation queued, prompt: {self.prompt}, negative: {self.negative}, anime: {self.anime}")

                image_bytes, name = await gen_image(server_address, self.prompt, self.model, self.negative, self.anime)

                reply_view = ImageView(self.prompt, self.negative, self.model, self.image_count, self.anime)
                
                await button_interaction.followup.send(file=discord.File(io.BytesIO(image_bytes), filename=f"{name}.png", spoiler=True), view=reply_view)
                generating = False
                
            except Exception as e:
                # ephemeral so no one else sees it
                generating = False
                await button_interaction.response.send_message(f"An error occured: {e}", ephemeral=True)
        
        else:
            await button_interaction.response.send_message(f"Currently generating, your prompt will be ignored, please try again after current generation", ephemeral=True)
    
@client.tree.command(name="generate", description="generates image")
async def generate(interaction: discord.Interaction, prompt:str, negative:str=None, image_count:int=1, model:str=default_model, anime:bool=False):
    global generating
    if not generating:
        try:
            generating = True
            await interaction.response.defer(thinking=True)
            
            print(f"Image generation queued, prompt: {prompt}, negative: {negative}, anime: {anime}")

            image_bytes, name = await gen_image(server_address, prompt, model, negative, anime)

            image_view = ImageView(prompt, negative, model, image_count, anime)
            
            await interaction.followup.send(file=discord.File(io.BytesIO(image_bytes), filename=f"{name}.png", spoiler=True), view=image_view)
            
            generating = False
            
        except Exception as e:
            generating = False
            await interaction.response.send_message(f"An error occured: {e}")
    
    else:
        await interaction.response.send_message(f"Currently generating, your prompt will be ignored, please try again after current generation")

@generate.autocomplete("model")
async def model_name_autocomplete(interaction: discord.Interaction, current: str):
    #print(f"DEBUG: Gen models, {models}")
    return [
        discord.app_commands.Choice(name=(".".join(model.split(".")[:-1])), value=model) for model in models
    ]

@client.tree.command(name="backend", description="switch server backend")
async def backend(interaction: discord.Interaction, url:str):
    global server_address
    server_address = url
    await tryContactServer()
    await interaction.response.send_message(f"Server backend switched to {url}")
    print(f"Server backend switched to {url}")

client.run(token)
