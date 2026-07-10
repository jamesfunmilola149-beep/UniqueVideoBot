import os
import logging
import subprocess
import uuid
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set")

# Create temp directory for processing
TEMP_DIR = Path("/tmp/video_processing")
TEMP_DIR.mkdir(exist_ok=True)

# User session data
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with options."""
    keyboard = [
        [InlineKeyboardButton("🎥 Uniquify Video", callback_data="uniquify")],
        [InlineKeyboardButton("ℹ️ How it works", callback_data="help")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Welcome to Uniqueizer Bot!*\n\n"
        "Send me a video and I'll make it unique by:\n"
        "• Changing bitrate\n"
        "• Removing metadata\n"
        "• Applying effects\n\n"
        "Simply send me any video file to start!",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "uniquify":
        await query.edit_message_text(
            "📤 *Please send me a video file*\n\n"
            "Supported formats: MP4, AVI, MOV, MKV\n"
            "Max size: 50MB",
            parse_mode="Markdown"
        )
    
    elif query.data == "help":
        await query.edit_message_text(
            "ℹ️ *How Uniqueizer Works*\n\n"
            "1. You send a video\n"
            "2. I process it with FFmpeg\n"
            "3. Changes applied:\n"
            "   • Bitrate modification\n"
            "   • Metadata removal\n"
            "   • Frame mirroring (optional)\n"
            "4. You get a unique video back!\n\n"
            "All processing happens on the server.",
            parse_mode="Markdown"
        )
    
    elif query.data == "settings":
        keyboard = [
            [InlineKeyboardButton("🔄 Mirror Mode", callback_data="toggle_mirror")],
            [InlineKeyboardButton("📊 Quality", callback_data="quality")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ *Settings*\n\n"
            "Customize how your videos are processed:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif query.data == "toggle_mirror":
        user_id = update.effective_user.id
        current = user_data.get(user_id, {}).get("mirror", False)
        user_data.setdefault(user_id, {})["mirror"] = not current
        status = "ON" if not current else "OFF"
        await query.edit_message_text(
            f"🔄 Mirror mode is now *{status}*\n\n"
            f"Send a video to test it!",
            parse_mode="Markdown"
        )
    
    elif query.data == "back":
        await start(update, context)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming videos."""
    user_id = update.effective_user.id
    video = update.message.video
    
    if not video:
        await update.message.reply_text("❌ Please send a video file.")
        return
    
    # Check file size (50MB limit)
    if video.file_size > 50 * 1024 * 1024:
        await update.message.reply_text("❌ Video too large! Maximum 50MB.")
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔄 *Processing your video...*\n"
        "This may take a few moments.",
        parse_mode="Markdown"
    )
    
    try:
        # Download video
        file = await context.bot.get_file(video.file_id)
        unique_id = str(uuid.uuid4())[:8]
        input_path = TEMP_DIR / f"input_{unique_id}.mp4"
        output_path = TEMP_DIR / f"output_{unique_id}.mp4"
        
        await file.download_to_drive(input_path)
        logger.info(f"Downloaded video for user {user_id}")
        
        # Get user settings
        mirror = user_data.get(user_id, {}).get("mirror", False)
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-b:v", "2M",  # Change bitrate
            "-maxrate", "2M",
            "-bufsize", "4M",
            "-map_metadata", "-1",  # Remove metadata
        ]
        
        if mirror:
            cmd.extend(["-vf", "hflip"])
        
        cmd.append(str(output_path))
        cmd.append("-y")  # Overwrite output
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            await processing_msg.edit_text(
                "❌ *Error processing video*\n"
                "Please try again with a different video.",
                parse_mode="Markdown"
            )
            return
        
        # Send processed video back
        with open(output_path, "rb") as f:
            await update.message.reply_video(
                video=f,
                caption="✅ *Video processed successfully!*\n\n"
                       f"🔄 Mirror: {'ON' if mirror else 'OFF'}\n"
                       "📊 Quality: High (2M bitrate)\n\n"
                       "Send another video to continue!",
                parse_mode="Markdown"
            )
        
        await processing_msg.delete()
        
        # Cleanup
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        
    except subprocess.TimeoutExpired:
        await processing_msg.edit_text(
            "⏰ *Processing timed out*\n"
            "Video may be too complex. Try a simpler video.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        await processing_msg.edit_text(
            "❌ *Something went wrong*\n"
            "Please try again later.",
            parse_mode="Markdown"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("🤖 Uniqueizer Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
