# 🎥 Uniqueizer Telegram Bot

A Telegram bot that makes videos unique by changing bitrate, removing metadata, and applying effects.

## Features

- ✅ Change video bitrate (2M)
- ✅ Remove all metadata
- ✅ Optional horizontal mirror effect
- ✅ Handles multiple formats (MP4, AVI, MOV, MKV)
- ✅ 50MB file limit

## Deployment

### Railway
1. Fork this repo to GitHub
2. Create new project on Railway
3. Connect your GitHub repo
4. Add environment variable: `BOT_TOKEN`
5. Deploy!

### Local Development
```bash
pip install -r requirements.txt
export BOT_TOKEN=your_token_here
python bot.py
