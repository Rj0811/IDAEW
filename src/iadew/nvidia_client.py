"""NVIDIA NIM API client for IADEW.

Replaces the OpenAI API for vision and chat analysis.
Supports text-only and multimodal (image-to-text) requests using the
OpenAI-compatible NVIDIA NIM /v1/chat/completions endpoint.

GLM-5.3-Flash is a 320B-total / 18B-active multimodal MoE model supporting
image-to-text, reasoning, chat, and tool calling.

Usage:
    from src.iadew.nvidia_client import ask_nvidia, analyze_image_with_nvidia
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import requests

from .config import settings

NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


def _headers(stream: bool = False) -> dict:
    if not settings.nvidia_api_key:
        raise RuntimeError(
            "NVIDIA_API_KEY is not set. Add it to your .env file:\n"
            "  NVIDIA_API_KEY=nvapi-xxxx..."
        )
    return {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Accept": "text/event-stream" if stream else "application/json",
        "Content-Type": "application/json",
    }


def ask_nvidia(
    prompt: str,
    system: str = "You are a helpful financial research assistant.",
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.5,
    stream: bool = False,
) -> str:
    """Send a plain text prompt to the NVIDIA NIM model and return the reply.

    Args:
        prompt:      The user message to send.
        system:      System prompt. Defaults to a financial research assistant.
        model:       Override model; defaults to settings.nvidia_model.
        max_tokens:  Maximum tokens in the response.
        temperature: Sampling temperature (0 = deterministic, 1 = creative).
        stream:      If True, streams and prints tokens; returns final text.

    Returns:
        The assistant's reply as a string.
    """
    model = model or settings.nvidia_model
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "stream": stream,
        "temperature": temperature,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }
    response = requests.post(
        NVIDIA_NIM_URL, headers=_headers(stream), json=payload, timeout=120, stream=stream
    )
    response.raise_for_status()

    if stream:
        chunks = []
        for line in response.iter_lines():
            if line:
                raw = line.decode("utf-8")
                if raw.startswith("data: "):
                    raw = raw[6:]
                if raw == "[DONE]":
                    break
                try:
                    delta = json.loads(raw)["choices"][0]["delta"].get("content", "")
                    if delta:
                        chunks.append(delta)
                        print(delta, end="", flush=True)
                except (KeyError, json.JSONDecodeError):
                    pass
        print()  # newline after streaming
        return "".join(chunks)

    body = response.json()
    try:
        content = body["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected NVIDIA NIM response shape: {json.dumps(body)[:1200]}"
        ) from exc
    if isinstance(content, str) and content.strip():
        return content
    raise RuntimeError(
        "NVIDIA NIM returned no text content. "
        f"finish_reason={body.get('choices', [{}])[0].get('finish_reason')}; "
        f"response={json.dumps(body)[:1600]}"
    )


def analyze_image_with_nvidia(
    image_path: Path,
    prompt: str,
    system: str = "You are a helpful financial research assistant.",
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    """Send an image together with a text prompt to GLM-5.3-flash (multimodal).

    GLM-5.3-flash supports image-to-text via the standard OpenAI-compatible
    multimodal messages format: a user message containing both a text part and
    an image_url part with a base64-encoded data URI.

    Args:
        image_path:  Path to the PNG/JPG image file to analyze.
        prompt:      The text instruction / question accompanying the image.
        system:      System prompt.
        model:       Override model; defaults to settings.nvidia_model.
        max_tokens:  Maximum tokens in the response.
        temperature: Lower values make output more deterministic.

    Returns:
        The model's textual analysis of the image.
    """
    model = model or settings.nvidia_model
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Detect mime type from extension.
    ext = image_path.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(
        ext, "image/png"
    )
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    data_uri = f"data:{mime};base64,{encoded}"

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "stream": False,
        "temperature": temperature,
        "top_p": 1,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
    }
    response = requests.post(
        NVIDIA_NIM_URL, headers=_headers(False), json=payload, timeout=180
    )
    response.raise_for_status()

    body = response.json()
    try:
        content = body["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected NVIDIA NIM response shape: {json.dumps(body)[:1200]}"
        ) from exc
    if isinstance(content, str) and content.strip():
        return content
    raise RuntimeError(
        "NVIDIA NIM returned no text content for the image request. "
        f"finish_reason={body.get('choices', [{}])[0].get('finish_reason')}; "
        f"response={json.dumps(body)[:2000]}"
    )
