#!/usr/bin/env python3
"""
Continue an OpenAI conversation from a previous response ID.

Usage:
    python continue_conversation.py <response_id> "Your message here"
    python continue_conversation.py <response_id> "What's in this image?" --image photo.png
    python continue_conversation.py <response_id> "Analyze this" --image-url "https://example.com/img.jpg"
    
Example:
    python continue_conversation.py resp_0a6e586e566ede67... "What should I do next?"
"""

import argparse
import base64
import mimetypes
import os
from pathlib import Path
from openai import OpenAI


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode a local image file to base64 and detect its media type."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Detect MIME type
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
        # Default to common image types based on extension
        ext = path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")
    
    with open(path, "rb") as f:
        encoded = base64.standard_b64encode(f.read()).decode("utf-8")
    
    return encoded, mime_type


def build_input(
    message: str,
    image_paths: list[str] | None = None,
    image_urls: list[str] | None = None,
) -> str | list[dict]:
    """Build the input payload, handling text and images."""
    
    # Simple case: text only
    if not image_paths and not image_urls:
        return message
    
    # Multimodal case: build content array
    content = []
    
    # Add text
    if message:
        content.append({"type": "input_text", "text": message})
    
    # Add local images (base64 encoded)
    if image_paths:
        for img_path in image_paths:
            encoded, mime_type = encode_image(img_path)
            content.append({
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{encoded}",
            })
            print(f"  📎 Attached: {img_path}")
    
    # Add URL images
    if image_urls:
        for url in image_urls:
            content.append({
                "type": "input_image",
                "image_url": url,
            })
            print(f"  🔗 Attached URL: {url}")
    
    return [{"role": "user", "content": content}]


def continue_conversation(
    previous_response_id: str,
    user_message: str,
    model: str = "gpt-4o",
    reasoning_effort: str | None = None,
    image_paths: list[str] | None = None,
    image_urls: list[str] | None = None,
) -> None:
    """Continue a conversation from a previous response ID."""
    
    client = OpenAI()  # Uses OPENAI_API_KEY env var
    
    # Build the input (text only or multimodal)
    input_payload = build_input(user_message, image_paths, image_urls)
    
    # Build the request parameters
    params = {
        "model": model,
        "previous_response_id": previous_response_id,
        "input": input_payload,
    }
    
    # Add reasoning effort for reasoning models (o1, o3, gpt-5-pro, etc.)
    if reasoning_effort:
        params["reasoning"] = {"effort": reasoning_effort}
    
    print(f"Continuing from: {previous_response_id}")
    print(f"Model: {model}")
    print(f"User: {user_message}")
    print("-" * 60)
    
    response = client.responses.create(**params)
    
    # Print the response
    print(f"\nResponse ID: {response.id}")
    print(f"Model: {response.model}")
    print("-" * 60)
    
    # Extract text from the response
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    print(f"\nAssistant:\n{content.text}")
    
    print("\n" + "=" * 60)
    print(f"New response ID (for continuing): {response.id}")
    

def main():
    parser = argparse.ArgumentParser(
        description="Continue an OpenAI conversation from a response ID"
    )
    parser.add_argument(
        "response_id",
        help="The previous response ID (e.g., resp_0a6e586e566ede67...)"
    )
    parser.add_argument(
        "message",
        help="Your message to continue the conversation"
    )
    parser.add_argument(
        "--model", "-m",
        default="gpt-4o",
        help="Model to use (default: gpt-4o). Use the same model as the original for best results."
    )
    parser.add_argument(
        "--reasoning-effort", "-r",
        choices=["low", "medium", "high"],
        help="Reasoning effort for reasoning models (o1, o3, gpt-5-pro)"
    )
    parser.add_argument(
        "--image", "-i",
        action="append",
        dest="images",
        help="Path to a local image file (can be used multiple times)"
    )
    parser.add_argument(
        "--image-url", "-u",
        action="append",
        dest="image_urls",
        help="URL of an image (can be used multiple times)"
    )
    
    args = parser.parse_args()
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY='your-key-here'")
        return 1
    
    continue_conversation(
        previous_response_id=args.response_id,
        user_message=args.message,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        image_paths=args.images,
        image_urls=args.image_urls,
    )
    return 0


if __name__ == "__main__":
    exit(main())
