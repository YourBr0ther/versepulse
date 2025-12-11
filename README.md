# VersePulse

Star Citizen Patch Notes Monitor - Get notified on Pushbullet when new patch notes are posted.

## Features

- Monitors RSI Spectrum forum for new patch notes
- Uses AI (Ollama) to summarize patches and extract new features
- Sends Pushbullet notifications with summary, features, and link
- Runs in Docker with automatic scheduling

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/versepulse.git
   cd versepulse
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Pushbullet API key:
   - Get your API key from: https://www.pushbullet.com/#settings/account

3. **Start the services**
   ```bash
   docker compose up -d
   ```

4. **View logs**
   ```bash
   docker compose logs -f versepulse
   ```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PUSHBULLET_API_KEY` | (required) | Your Pushbullet access token |
| `OLLAMA_MODEL` | `mistral` | Ollama model for summarization |
| `CHECK_INTERVAL` | `10` | Minutes between checks |
| `FORUM_URL` | RSI Spectrum Patch Notes | Forum URL to monitor |

## GPU Acceleration (Optional)

To enable NVIDIA GPU support for Ollama, edit `docker-compose.yml` and uncomment the GPU section under the `ollama` service.

## Architecture

```
VersePulse
├── Playwright (headless browser)
│   └── Scrapes Spectrum forum
├── Ollama (local LLM)
│   └── Summarizes patch notes
├── SQLite
│   └── Tracks seen posts
└── Pushbullet
    └── Sends notifications
```

## Stopping

```bash
docker compose down
```

## License

MIT
