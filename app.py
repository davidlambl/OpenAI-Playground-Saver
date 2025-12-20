#!/usr/bin/env python3
"""
Web UI for continuing OpenAI conversations.
Run with: python app.py
Then open: http://localhost:5050
"""

import base64
import mimetypes
import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.urandom(24)


def get_client(api_key: str) -> OpenAI:
    """Get OpenAI client with provided API key."""
    return OpenAI(api_key=api_key)


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
    api_key = request.args.get("api_key", "").strip()
    
    if not api_key:
        return jsonify({"error": "API key is required", "models": []}), 400
    
    try:
        client = get_client(api_key)
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


@app.route("/api/history/<response_id>")
def get_response_history(response_id: str):
    """Get conversation history for a response ID."""
    api_key = request.args.get("api_key", "").strip()
    
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    
    if not response_id:
        return jsonify({"error": "Response ID is required"}), 400
    
    try:
        client = get_client(api_key)
        
        # Get the response itself
        response = client.responses.retrieve(response_id)
        
        # Get input items (conversation history)
        input_items = client.responses.input_items.list(response_id)
        
        # Build conversation history
        # Note: API returns items in reverse chronological order, so we reverse them
        messages = []
        for item in reversed(input_items.data):
            if item.type == "message":
                role = item.role if hasattr(item, 'role') else "unknown"
                content = ""
                if hasattr(item, 'content') and item.content:
                    for c in item.content:
                        if hasattr(c, 'text'):
                            content += c.text
                        elif hasattr(c, 'type') and c.type == "input_text":
                            content += c.text if hasattr(c, 'text') else ""
                messages.append({
                    "role": role,
                    "content": content
                })
        
        # Get the output from the response
        output_text = ""
        if hasattr(response, 'output') and response.output:
            for item in response.output:
                if item.type == "message":
                    for c in item.content:
                        if hasattr(c, 'text'):
                            output_text += c.text
        
        return jsonify({
            "response_id": response_id,
            "model": response.model if hasattr(response, 'model') else "unknown",
            "messages": messages,
            "output": output_text,
            "created_at": response.created_at if hasattr(response, 'created_at') else None,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation, optionally from a response ID."""
    api_key = request.form.get("api_key", "").strip()
    name = request.form.get("name", "").strip()
    from_response_id = request.form.get("from_response_id", "").strip()
    
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    
    try:
        client = get_client(api_key)
        
        # Create a new conversation
        conversation = client.conversations.create()
        conv_id = conversation.id
        
        items_added = 0
        
        # If converting from a response, get its history and add to conversation
        if from_response_id:
            # Get the response and its input items
            response = client.responses.retrieve(from_response_id)
            input_items = client.responses.input_items.list(from_response_id)
            
            # Add each message to the conversation
            for item in input_items.data:
                if item.type == "message":
                    role = item.role if hasattr(item, 'role') else "user"
                    content = ""
                    if hasattr(item, 'content') and item.content:
                        for c in item.content:
                            if hasattr(c, 'text'):
                                content += c.text
                    
                    if content:
                        # Different content type based on role
                        # user/system: input_text | assistant: output_text
                        content_type = "output_text" if role == "assistant" else "input_text"
                        client.conversations.items.create(
                            conversation_id=conv_id,
                            items=[{
                                "type": "message",
                                "role": role,
                                "content": [{"type": content_type, "text": content}]
                            }]
                        )
                        items_added += 1
            
            # Add the assistant's output from the response
            if hasattr(response, 'output') and response.output:
                output_text = ""
                for out_item in response.output:
                    if out_item.type == "message":
                        for c in out_item.content:
                            if hasattr(c, 'text'):
                                output_text += c.text
                
                if output_text:
                    client.conversations.items.create(
                        conversation_id=conv_id,
                        items=[{
                            "type": "message",
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": output_text}]
                        }]
                    )
                    items_added += 1
        
        return jsonify({
            "success": True,
            "conversation_id": conv_id,
            "items_added": items_added,
            "name": name,
            "from_response_id": from_response_id or None,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conv_id>/continue", methods=["POST"])
def continue_conversation_api(conv_id: str):
    """Send a message in an existing conversation."""
    api_key = request.form.get("api_key", "").strip()
    message = request.form.get("message", "").strip()
    model = request.form.get("model", "gpt-4o").strip()
    reasoning_effort = request.form.get("reasoning_effort", "").strip() or None
    
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    try:
        client = get_client(api_key)
        
        # Create a response using the conversation
        params = {
            "model": model,
            "conversation_id": conv_id,
            "input": message,
        }
        
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort}
        
        response = client.responses.create(**params)
        
        # Extract response text
        assistant_text = ""
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if hasattr(content, 'text'):
                        assistant_text += content.text
        
        return jsonify({
            "success": True,
            "response": assistant_text,
            "response_id": response.id,
            "conversation_id": conv_id,
            "model": response.model,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conv_id>/items")
def get_conversation_items(conv_id: str):
    """Get all items in a conversation."""
    api_key = request.args.get("api_key", "").strip()
    
    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    
    try:
        client = get_client(api_key)
        items = client.conversations.items.list(conv_id)
        
        # Reverse to get chronological order
        messages = []
        for item in reversed(items.data):
            if item.type == "message":
                role = item.role if hasattr(item, 'role') else "unknown"
                content = ""
                if hasattr(item, 'content') and item.content:
                    for c in item.content:
                        if hasattr(c, 'text'):
                            content += c.text
                messages.append({
                    "id": item.id if hasattr(item, 'id') else None,
                    "role": role,
                    "content": content
                })
        
        return jsonify({
            "conversation_id": conv_id,
            "messages": messages,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/send", methods=["POST"])
def send_message():
    """Send a message and get a response."""
    try:
        # Get form data
        api_key = request.form.get("api_key", "").strip()
        response_id = request.form.get("response_id", "").strip()
        message = request.form.get("message", "").strip()
        model = request.form.get("model", "gpt-4o").strip()
        reasoning_effort = request.form.get("reasoning_effort", "").strip() or None
        
        if not api_key:
            return jsonify({"error": "API key is required"}), 400
        
        if not message and not request.files.getlist("images"):
            return jsonify({"error": "Message or images required"}), 400
        
        # Process uploaded images
        images = []
        for file in request.files.getlist("images"):
            if file and file.filename:
                data = file.read()
                encoded, mime_type = encode_image_bytes(data, file.filename)
                images.append({"data": encoded, "mime_type": mime_type})
        
        # Build input
        input_payload = build_input(message, images)
        
        # Build API request
        params = {
            "model": model,
            "input": input_payload,
        }
        
        # Only add previous_response_id if continuing a conversation
        if response_id:
            params["previous_response_id"] = response_id
        
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort}
        
        # Make API call
        client = get_client(api_key)
        response = client.responses.create(**params)
        
        # Extract response text
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


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set")
        print("   Run: export OPENAI_API_KEY='sk-...'")
    
    print("\n🚀 Starting Playground Saver...")
    print("   Open: http://localhost:5050\n")
    app.run(host="0.0.0.0", port=5050, debug=True)

