#!/usr/bin/env python3
"""
Web UI for continuing OpenAI conversations.
Run with: python app.py
Then open: http://localhost:5050
"""

import base64
import mimetypes
import os
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Store conversation history in memory (per session)
conversations: dict[str, list[dict]] = {}


def get_client() -> OpenAI:
    """Get OpenAI client."""
    return OpenAI()


def encode_image_bytes(data: bytes, filename: str) -> tuple[str, str]:
    """Encode image bytes to base64 with MIME type detection."""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        ext = Path(filename).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")
    
    encoded = base64.standard_b64encode(data).decode("utf-8")
    return encoded, mime_type


def build_input(message: str, images: list[dict]) -> str | list[dict]:
    """Build input payload with optional images."""
    if not images:
        return message
    
    content = []
    if message:
        content.append({"type": "input_text", "text": message})
    
    for img in images:
        content.append({
            "type": "input_image",
            "image_url": f"data:{img['mime_type']};base64,{img['data']}",
        })
    
    return [{"role": "user", "content": content}]


@app.route("/")
def index():
    """Render the main chat UI."""
    return render_template("index.html")


@app.route("/api/models")
def get_models():
    """Fetch available models from OpenAI."""
    try:
        client = get_client()
        models = client.models.list()
        
        # Filter and sort models - prioritize chat/responses-capable models
        model_ids = []
        for model in models.data:
            model_id = model.id
            # Include GPT, O1, O3 models (exclude embeddings, whisper, dall-e, tts, etc.)
            if any(prefix in model_id.lower() for prefix in ['gpt-4', 'gpt-5', 'o1', 'o3', 'chatgpt']):
                # Exclude fine-tuned models and specific variants we don't want
                if not any(skip in model_id for skip in ['realtime', 'audio', 'transcribe', 'search']):
                    model_ids.append(model_id)
        
        # Sort: prioritize commonly used models
        def sort_key(model_id):
            priority_order = [
                'gpt-4o-mini', 'gpt-4o', 'gpt-4.1', 'gpt-4.1-mini',
                'o1-mini', 'o1', 'o3-mini', 'o3',
                'gpt-5', 'chatgpt-4o'
            ]
            for i, prefix in enumerate(priority_order):
                if model_id.startswith(prefix):
                    return (i, model_id)
            return (100, model_id)
        
        model_ids.sort(key=sort_key)
        
        return jsonify({"models": model_ids})
        
    except Exception as e:
        return jsonify({"error": str(e), "models": []}), 500


@app.route("/api/send", methods=["POST"])
def send_message():
    """Send a message and get a response."""
    try:
        # Get form data
        response_id = request.form.get("response_id", "").strip()
        message = request.form.get("message", "").strip()
        model = request.form.get("model", "gpt-4o").strip()
        reasoning_effort = request.form.get("reasoning_effort", "").strip() or None
        
        if not response_id:
            return jsonify({"error": "Response ID is required"}), 400
        
        if not message and not request.files.getlist("images"):
            return jsonify({"error": "Message or images required"}), 400
        
        # Process uploaded images
        images = []
        image_previews = []
        for file in request.files.getlist("images"):
            if file and file.filename:
                data = file.read()
                encoded, mime_type = encode_image_bytes(data, file.filename)
                images.append({"data": encoded, "mime_type": mime_type})
                image_previews.append({
                    "name": file.filename,
                    "preview": f"data:{mime_type};base64,{encoded[:100]}..."
                })
        
        # Build input
        input_payload = build_input(message, images)
        
        # Build API request
        params = {
            "model": model,
            "previous_response_id": response_id,
            "input": input_payload,
        }
        
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort}
        
        # Make API call
        client = get_client()
        response = client.responses.create(**params)
        
        # Extract response text
        assistant_text = ""
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        assistant_text += content.text
        
        # Store in conversation history
        conv_key = response_id
        if conv_key not in conversations:
            conversations[conv_key] = []
        
        conversations[conv_key].append({
            "role": "user",
            "content": message,
            "images": len(images),
            "timestamp": datetime.now().isoformat(),
        })
        conversations[conv_key].append({
            "role": "assistant", 
            "content": assistant_text,
            "timestamp": datetime.now().isoformat(),
        })
        
        return jsonify({
            "success": True,
            "response": assistant_text,
            "new_response_id": response.id,
            "model": response.model,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/<response_id>")
def get_history(response_id: str):
    """Get conversation history for a response ID."""
    history = conversations.get(response_id, [])
    return jsonify({"history": history})


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set")
        print("   Run: export OPENAI_API_KEY='sk-...'")
    
    print("\n🚀 Starting Playground Saver...")
    print("   Open: http://localhost:5050\n")
    app.run(host="0.0.0.0", port=5050, debug=True)

