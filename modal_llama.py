import modal
import os

MODEL_URL=os.getenv("MODAL_BASE_URL")

vllm_image = (modal.Image.debian_slim(python_version="3.11").pip_install("vllm==0.6.3.post1", "huggingface_hub[hf_transfer]==0.25.2").env({"HF_HUB_ENABLE_HF_TRANSFER": "1"}))
app = modal.App("llama-discord-bot")

MODEL_CACHE_VOL = modal.Volume.from_name("llama-model-cache", create_if_missing=True)
N_GPU = 1
GPU_TYPE = "A10G"
MINUTES = 60

@app.function(image=vllm_image, gpu=f"{GPU_TYPE}:{N_GPU}", secrets=[modal.Secret.from_name("huggingface")], volumes={"/root/.cache/huggingface": MODEL_CACHE_VOL}, scaledown_window=15 * MINUTES,  timeout=10 * MINUTES)
@modal.concurrent(max_inputs=16) 
@modal.web_server(port=8000, startup_timeout=5 * MINUTES)

def serve():
    import subprocess
    from typing import cast, List

    MODEL_NAME = os.getenv("MODAL_MODEL_NAME")
    if MODEL_NAME is None:
        raise ValueError("MODAL_MODEL_NAME is not set")
    MODEL_NAME = cast(str, MODEL_NAME)

    VLLM_API_KEY = os.getenv("HF_API_KEY")
    if VLLM_API_KEY is None:
        raise ValueError("HF_API_KEY is not set")
    VLLM_API_KEY = cast(str, VLLM_API_KEY)

    cmd: List[str] = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL_NAME,
        "--host", "0.0.0.0",
        "--port", "8000",
        "--api-key", VLLM_API_KEY,
        "--max-model-len", "4096",
        "--gpu-memory-utilization", "0.90",
        "--dtype", "bfloat16",
]
    subprocess.Popen(cmd)
