# 💾 Playground Saver

Continue conversations from your OpenAI Logs dashboard using the API.

Ever had a great conversation in the OpenAI Playground and wanted to continue it programmatically? This tool lets you pick up right where you left off using the `previous_response_id` from your logs.

## Features

- 🌐 **Web UI** — Clean interface for continuing conversations with image support
- 💬 **CLI Tools** — Command-line scripts for quick interactions  
- 📎 **Image Attachments** — Send images alongside your messages
- 🔄 **Dynamic Model List** — Fetches available models from your OpenAI account
- 🔗 **Response Chaining** — Automatically tracks response IDs for seamless continuation
- 📜 **Browse History** — View and resume previous conversations
- 📥 **Export** — Download conversations as Markdown
- ✨ **Markdown Rendering** — Assistant responses render with proper formatting

## Live Demo

The app is deployed at **[aichat.davidlambl.dev](https://aichat.davidlambl.dev)**

## Quick Start

### Option 1: Use the hosted version

1. Go to [aichat.davidlambl.dev](https://aichat.davidlambl.dev)
2. Enter your OpenAI API key
3. Paste a Response ID from [platform.openai.com/logs](https://platform.openai.com/logs)
4. Start chatting!

### Option 2: Run locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key (optional for CLI tools)
export OPENAI_API_KEY='sk-...'

# Run the web UI
python app.py
```

Open **http://localhost:5050** in your browser.

## Usage

### Web UI

1. Copy a **Response ID** from [platform.openai.com/logs](https://platform.openai.com/logs) (e.g., `resp_0a6e586e566ede67...`)
2. Paste it into the Response ID field (or leave empty to start a new conversation)
3. Select your model and reasoning effort (if applicable)
4. Type your message and optionally attach images
5. Send! The response ID updates automatically for the next turn.

#### Features

| Button | Description |
|--------|-------------|
| ✨ | Start a new conversation |
| 📜 | Browse your local response history |
| 🔄 | Load conversation history from OpenAI |
| 📋 | Copy the response ID |
| 📥 Export | Download conversation as Markdown |
| 📋 Copy | Copy individual messages |

### CLI — Single Message

```bash
python continue_conversation.py resp_xxx "Your message here" --model gpt-4o
```

With images:

```bash
python continue_conversation.py resp_xxx "What's in this image?" \
  --image photo.png \
  --model gpt-4o
```

### CLI — Interactive Chat

```bash
python chat.py resp_xxx --model gpt-4o
```

Commands during chat:

| Command | Description |
|---------|-------------|
| `/image <path>` | Attach a local image |
| `/url <url>` | Attach an image URL |
| `/clear` | Clear pending attachments |
| `/id` | Show current response ID |
| `quit` | Exit |

## How It Works

The OpenAI [Responses API](https://platform.openai.com/docs/api-reference/responses) supports a `previous_response_id` parameter that tells the API to load the full conversation context from a previous response. You don't need to resend any messages—OpenAI stores the conversation history server-side.

This is more efficient than manually managing message history because:
- ✅ No input tokens charged for previous messages
- ✅ No cache TTL to worry about
- ✅ Conversation context is preserved exactly

## Project Structure

```
├── api/
│   └── index.py              # Vercel serverless function
├── templates/
│   └── index.html            # Web UI
├── app.py                    # Local Flask server
├── continue_conversation.py  # CLI: single message
├── chat.py                   # CLI: interactive chat
├── requirements.txt          # Python dependencies
├── vercel.json               # Vercel deployment config
└── tests/
    └── test_api.py           # Unit tests
```

## Deployment

The app is deployed on Vercel. To deploy your own:

1. Fork this repository
2. Connect to Vercel
3. Deploy!

No environment variables needed — the API key is provided by the user in the UI.

## Requirements

- Python 3.10+
- OpenAI API key with access to the Responses API
- `openai>=1.40.0`
- `flask>=3.0.0`

## License

MIT
