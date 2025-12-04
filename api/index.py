"""
Vercel serverless function for Playground Saver.
"""

import base64
import mimetypes
import os
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder="../templates")
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

# Note: In serverless, conversation history won't persist between requests
# Each function invocation is stateless


def get_client():
    """Get OpenAI client."""
    from openai import OpenAI
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
        
        model_ids = []
        for model in models.data:
            model_id = model.id
            if any(prefix in model_id.lower() for prefix in ['gpt-4', 'gpt-5', 'o1', 'o3', 'chatgpt']):
                if not any(skip in model_id for skip in ['realtime', 'audio', 'transcribe', 'search']):
                    model_ids.append(model_id)
        
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
        response_id = request.form.get("response_id", "").strip()
        message = request.form.get("message", "").strip()
        model = request.form.get("model", "gpt-4o").strip()
        reasoning_effort = request.form.get("reasoning_effort", "").strip() or None
        
        if not response_id:
            return jsonify({"error": "Response ID is required"}), 400
        
        if not message and not request.files.getlist("images"):
            return jsonify({"error": "Message or images required"}), 400
        
        images = []
        for file in request.files.getlist("images"):
            if file and file.filename:
                data = file.read()
                encoded, mime_type = encode_image_bytes(data, file.filename)
                images.append({"data": encoded, "mime_type": mime_type})
        
        input_payload = build_input(message, images)
        
        params = {
            "model": model,
            "previous_response_id": response_id,
            "input": input_payload,
        }
        
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort}
        
        client = get_client()
        response = client.responses.create(**params)
        
        assistant_text = ""
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        assistant_text += content.text
        
        return jsonify({
            "success": True,
            "response": assistant_text,
            "new_response_id": response.id,
            "model": response.model,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Vercel expects the app to be named 'app'
# This file will be used as the serverless function entry point

