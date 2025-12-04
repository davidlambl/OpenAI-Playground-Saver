# 💾 OpenAI Playground Saver

Continue conversations from your OpenAI Logs dashboard using the API.

Ever had a great conversation in the OpenAI Playground and wanted to continue it programmatically? This tool lets you pick up right where you left off using the `previous_response_id` from your logs.

## Features

- 🌐 **Web UI** — Clean interface for continuing conversations with image support
- 💬 **CLI Tools** — Command-line scripts for quick interactions
- 📎 **Image Attachments** — Send images alongside your messages
- 🔄 **Dynamic Model List** — Fetches available models from your OpenAI account
- 🔗 **Response Chaining** — Automatically tracks response IDs for seamless continuation

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

```bash
export OPENAI_API_KEY='sk-...'
```

### 3. Run the web UI

```bash
python app.py
```

Open **http://localhost:5050** in your browser.

## Usage

### Web UI

1. Copy a **Response ID** from [platform.openai.com/logs](https://platform.openai.com/logs) (e.g., `resp_0a6e586e566ede67...`)
2. Paste it into the Response ID field
3. Select your model and reasoning effort (if applicable)
4. Type your message and optionally attach images
5. Send! The response ID updates automatically for the next turn.

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
├── app.py                    # Flask web server
├── templates/
│   └── index.html            # Web UI
├── continue_conversation.py  # CLI: single message
├── chat.py                   # CLI: interactive chat
├── requirements.txt          # Python dependencies
└── (Chrome Extension)
    ├── manifest.json
    ├── popup.html
    └── popup.js
```

## Chrome Extension (Bonus)

A simple Chrome extension is included for scraping text from the Playground UI:

1. Go to `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** and select this folder
4. Click the extension on any OpenAI Playground/Logs page to download the text

## Requirements

- Python 3.10+
- OpenAI API key with access to the Responses API
- `openai>=1.40.0`
- `flask>=3.0.0`

## License

MIT

