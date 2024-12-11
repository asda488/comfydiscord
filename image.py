import websockets.asyncio.client
import json
import requests
import aiohttp
import random
import uuid

client_id = str(uuid.uuid4())


def build_json(text, negative):
    workflow = """
    {
    "3": {
        "inputs": {
        "seed": 0,
        "steps": 25,
        "cfg": 7.00,
        "sampler_name": "dpmpp_2m_sde_gpu",
        "scheduler": "karras",
        "denoise": 1,
        "model": [
            "12",
            0
        ],
        "positive": [
            "6",
            0
        ],
        "negative": [
            "7",
            0
        ],
        "latent_image": [
            "5",
            0
        ]
        },
        "class_type": "KSampler"
    },
    "4": {
        "inputs": {
        "ckpt_name": "AnythingXL_v50.safetensors"
        },
        "class_type": "CheckpointLoaderSimple"
    },
    "5": {
        "inputs": {
        "width": 512,
        "height": 512,
        "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "6": {
        "inputs": {
        "text": "morning",
        "clip": [
            "11",
            0
        ]
        },
        "class_type": "CLIPTextEncode"
    },
    "7": {
        "inputs": {
        "text": "embedding:EasyNegative.pt, text, watermark",
        "clip": [
            "11",
            0
        ]
        },
        "class_type": "CLIPTextEncode"
    },
    "8": {
        "inputs": {
        "samples": [
            "3",
            0
        ],
        "vae": [
            "4",
            2
        ]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
        "images": [
            "16",
            0
        ]
        },
        "class_type": "SaveImageWebsocket"
    },
    "11": {
        "inputs": {
        "stop_at_clip_layer": -2,
        "clip": [
            "12",
            1
        ]
        },
        "class_type": "CLIPSetLastLayer"
    },
    "12": {
        "inputs": {
        "lora_name": "add_detail.safetensors",
        "strength_model": 1,
        "strength_clip": 1,
        "model": [
            "4",
            0
        ],
        "clip": [
            "4",
            1
        ]
        },
        "class_type": "LoraLoader"
    },
    "14": {
        "inputs": {
        "model_name": "4xUltrasharp_4xUltrasharpV10.pt"
        },
        "class_type": "UpscaleModelLoader"
    },
    "15": {
        "inputs": {
        "upscale_model": [
            "14",
            0
        ],
        "image": [
            "8",
            0
        ]
        },
        "class_type": "ImageUpscaleWithModel"
    },
    "16": {
        "inputs": {
        "upscale_method": "lanczos",
        "width": 768,
        "height": 768,
        "crop": "disabled",
        "image": [
            "15",
            0
        ]
        },
        "class_type": "ImageScale"
    }
    }
    """
    workflow = json.loads(workflow)
    workflow["6"]["inputs"]["text"] = text
    workflow["3"]["inputs"]["seed"] = random.getrandbits(64)
    workflow["7"]["inputs"]["text"] = negative
    return {"prompt": workflow, "client_id": client_id}

#takes json prompt, returns int prompt_id
async def send_prompt(server_address, prompt):
    data = json.dumps(prompt).encode('utf-8')
    async with aiohttp.ClientSession() as session:
        async with session.post(f'http://{server_address}/prompt', data=data) as resp:
            body = await resp.text()
    return json.loads(body)["prompt_id"]

async def listen_image(server_address, id):
    async with websockets.asyncio.client.connect(f"ws://{server_address}/ws?clientId={client_id}", max_size=None, ping_interval=None) as websocket: #not expecting more than 32MB
        current_node = 0
        async for msg in websocket:
            if isinstance(msg, str):
                message = json.loads(msg)
                if message['type'] == 'executing':
                    data = message['data']
                    if "prompt_id" in data and data['prompt_id'] == id:
                        if data['node'] is None:
                            return image_data #Execution is done
                        else:
                            current_node = data['node']
            else:
                if current_node == "9": #save_image_websocket_node
                    image_data = msg[8:]

async def gen_image(server_address, text, negative=None, anime=False):
    if anime:
        positive = "masterpiece, (best quality), newest, recent, 1girl, extreme detailed, " + text
        neg = "embedding:EasyNegative.pt,(worst quality),(low quality),(normal quality), text, watermark, lowres, (bad anatomy), (bad hands), error, missing fingers,extra digit,fewer digits,cropped,jpeg artifacts,signature,watermark,username,blurry, old,furry," + (negative if negative else "")
    else:
        positive = "masterpiece, (best quality), " + text
        neg = "embedding:EasyNegative.pt,(worst quality),(low quality),(normal quality), text, watermark, lowres"
    prompt = build_json(positive, negative)
    id = await send_prompt(server_address, prompt)
    image = await listen_image(server_address, id)
    return image, id