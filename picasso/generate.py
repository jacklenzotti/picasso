"""Gemini image generation wrapper."""

import base64
import io
import os

from PIL import Image


def generate_image(prompt, api_key=None, model="gemini-2.5-flash-image",
                   aspect_ratio=None, save_path=None):
    """Generate an image using Google's Gemini API.

    Args:
        prompt: Text prompt describing the image to generate.
        api_key: Gemini API key. Falls back to GEMINI_API_KEY env var.
        model: Gemini model to use.
        aspect_ratio: Optional aspect ratio (e.g. "1:1", "16:9").
        save_path: Optional path to save the generated image.

    Returns:
        PIL Image of the generated result.

    Raises:
        ValueError: If no API key is provided.
        RuntimeError: If image generation fails.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    from google import genai
    from google.genai import types

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "No API key provided. Set GEMINI_API_KEY environment variable "
            "or pass api_key parameter."
        )

    client = genai.Client(api_key=key)

    # Build generation config
    config_kwargs = {"response_modalities": ["IMAGE"]}
    if aspect_ratio:
        config_kwargs["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    # Extract image from response
    if (not response.candidates or
            not response.candidates[0].content or
            not response.candidates[0].content.parts):
        raise RuntimeError("Gemini returned no image. Try a different prompt.")

    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = base64.b64decode(part.inline_data.data)
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

            if save_path:
                os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
                img.save(save_path)
                print(f"Generated image saved → {save_path}")

            return img

    raise RuntimeError("Gemini response contained no image data.")
