"""Direct Stable Diffusion inference for the local image studio."""

from io import BytesIO
from pathlib import Path
from threading import Lock
import os


MODEL_PATH = Path(os.getenv(
    "GRACE_IMAGE_MODEL",
    r"D:\AI\ComfyUI_windows_portable\ComfyUI\models\checkpoints\v1-5-pruned-emaonly.safetensors",
))
ORIGINAL_CONFIG_PATH = Path(os.getenv(
    "GRACE_IMAGE_CONFIG",
    r"D:\AI\stable-diffusion-v1-inference.yaml",
))

_pipeline = None
_pipeline_lock = Lock()


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    with _pipeline_lock:
        if _pipeline is not None:
            return _pipeline
        import torch
        from diffusers import StableDiffusionPipeline

        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"Stable Diffusion model not found: {MODEL_PATH}")
        _pipeline = StableDiffusionPipeline.from_single_file(
            str(MODEL_PATH),
            torch_dtype=torch.float16,
            original_config_file=str(ORIGINAL_CONFIG_PATH),
            safety_checker=None,
        )
        _pipeline = _pipeline.to("cuda")
        _pipeline.enable_attention_slicing()
        return _pipeline


def generate_image(prompt: str, negative_prompt: str) -> bytes:
    import torch

    pipeline = _get_pipeline()
    with torch.inference_mode():
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=512,
            height=512,
            num_inference_steps=24,
            guidance_scale=7.0,
        )
    output = BytesIO()
    result.images[0].save(output, format="PNG")
    return output.getvalue()
