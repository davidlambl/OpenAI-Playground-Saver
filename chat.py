#!/usr/bin/env python3
"""
Interactive chat that continues from an OpenAI response ID.
Supports sending images during the conversation.

Usage:
    python chat.py <response_id>
    python chat.py <response_id> --model gpt-4o
    
Commands during chat:
    /image <path>     - Attach a local image to your next message
    /url <url>        - Attach an image URL to your next message
    /clear            - Clear pending attachments
    /id               - Show current response ID
    quit, exit, q     - End the session

Example:
    python chat.py resp_0a6e586e566ede6700693137ec636881a089d8833871463e9f
"""

import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path
from openai import OpenAI


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode a local image file to base64 and detect its media type."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
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
    
    if not image_paths and not image_urls:
        return message
    
    content = []
    
    if message:
        content.append({"type": "input_text", "text": message})
    
    if image_paths:
        for img_path in image_paths:
            encoded, mime_type = encode_image(img_path)
            content.append({
                "type": "input_image",
                "image_url": f"data:{mime_type};base64,{encoded}",
            })
    
    if image_urls:
        for url in image_urls:
            content.append({
                "type": "input_image",
                "image_url": url,
            })
    
    return [{"role": "user", "content": content}]


def chat_loop(
    initial_response_id: str,
    model: str = "gpt-4o",
    reasoning_effort: str | None = None,
    instructions: str | None = None,
) -> None:
    """Run an interactive chat loop continuing from a previous response."""
    
    client = OpenAI()
    current_response_id = initial_response_id
    
    # Pending attachments for next message
    pending_images: list[str] = []
    pending_urls: list[str] = []
    
    print("=" * 60)
    print(f"Continuing conversation from: {initial_response_id}")
    print(f"Model: {model}")
    if reasoning_effort:
        print(f"Reasoning effort: {reasoning_effort}")
    print("=" * 60)
    print("Commands:")
    print("  /image <path>  - Attach a local image")
    print("  /url <url>     - Attach an image URL")
    print("  /clear         - Clear pending attachments")
    print("  /id            - Show current response ID")
    print("  quit/exit/q    - End session")
    print("-" * 60)
    
    while True:
        # Show pending attachments
        if pending_images or pending_urls:
            print(f"  📎 Pending: {len(pending_images)} image(s), {len(pending_urls)} URL(s)")
        
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.lower() in ("quit", "exit", "q"):
            print(f"\nFinal response ID: {current_response_id}")
            break
        
        if user_input.lower() == "/id":
            print(f"Current response ID: {current_response_id}")
            continue
        
        if user_input.lower() == "/clear":
            pending_images.clear()
            pending_urls.clear()
            print("Attachments cleared.")
            continue
        
        if user_input.lower().startswith("/image "):
            img_path = user_input[7:].strip()
            if Path(img_path).exists():
                pending_images.append(img_path)
                print(f"  ✓ Queued: {img_path}")
            else:
                print(f"  ✗ File not found: {img_path}")
            continue
        
        if user_input.lower().startswith("/url "):
            url = user_input[5:].strip()
            pending_urls.append(url)
            print(f"  ✓ Queued URL: {url}")
            continue
        
        # Build input with any pending attachments
        input_payload = build_input(
            user_input,
            pending_images if pending_images else None,
            pending_urls if pending_urls else None,
        )
        
        # Clear pending attachments after use
        if pending_images or pending_urls:
            attachment_count = len(pending_images) + len(pending_urls)
            print(f"  Sending with {attachment_count} attachment(s)...")
            pending_images.clear()
            pending_urls.clear()
        
        # Build request
        params = {
            "model": model,
            "previous_response_id": current_response_id,
            "input": input_payload,
        }
        
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort}
        
        if instructions:
            params["instructions"] = instructions
        
        try:
            print("Thinking...", end="", flush=True)
            response = client.responses.create(**params)
            print("\r" + " " * 20 + "\r", end="")
            
            current_response_id = response.id
            
            for item in response.output:
                if item.type == "message":
                    for content in item.content:
                        if content.type == "output_text":
                            print(f"Assistant: {content.text}")
            
        except Exception as e:
            print(f"\nError: {e}")
            print("(Conversation state preserved, try again)")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive chat continuing from an OpenAI response ID"
    )
    parser.add_argument(
        "response_id",
        help="The response ID to continue from (e.g., resp_0a6e586e...)"
    )
    parser.add_argument(
        "--model", "-m",
        default="gpt-4o",
        help="Model to use (default: gpt-4o)"
    )
    parser.add_argument(
        "--reasoning-effort", "-r",
        choices=["low", "medium", "high"],
        help="Reasoning effort for reasoning models"
    )
    parser.add_argument(
        "--instructions", "-i",
        help="System instructions to add/override"
    )
    
    args = parser.parse_args()
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY='your-key-here'")
        return 1
    
    chat_loop(
        initial_response_id=args.response_id,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        instructions=args.instructions,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
