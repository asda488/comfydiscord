import websockets.sync.client
import json
import requests
import random
import uuid

server_address = "192.168.1.69:8188"
client_id = str(uuid.uuid4())


def build_json(text):
    workflow = """
    {
    "3": {
        "inputs": {
        "seed": 1095405104177859,
        "steps": 20,
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
        "ckpt_name": "meinamix_meinaV11.safetensors"
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
            "15",
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
    }
    }
    """
    workflow = json.loads(workflow)
    workflow["6"]["inputs"]["text"] = text
    workflow["3"]["inputs"]["seed"] = random.getrandbits(64)
    return {"prompt": workflow, "client_id": client_id}

def send_prompt(prompt):
    data = json.dumps(prompt).encode('utf-8')
    return requests.post(f"http://{server_address}/prompt", data=data)

def listen_image(ws, id):
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if "prompt_id" in data and data['prompt_id'] == id:
                    if data['node'] is None:
                        break #Execution is done
                    else:
                        current_node = data['node']
        else:
            if current_node == "9": #save_image_websocket_node
                image_data = out[8:]
    return image_data

def gen_image(text):
    prompt = build_json(text)
    id = send_prompt(prompt).json()["prompt_id"]
    with websockets.sync.client.connect(f"ws://{server_address}/ws?clientId={client_id}", max_size=2**25) as websocket: #not expecting more than 32mb
        return listen_image(websocket, id), id