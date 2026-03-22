import logging
from typing import Dict, List
from google.genai import types
from telegram import Bot
import os

from tools.base import BaseTool
from config import Config

logger = logging.getLogger("JARVIS_CHANNEL_PUBLISHER")

class PostToChannelTool(BaseTool):
    """
    Publish polished content directly to a Telegram Channel.
    """
    name = "post_to_channel"
    description = "Publish finalized content to the designated public Telegram Channel. Can also send a photo if an image path is provided."
    owner_role = ["content_writer", "ceo"]

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "channel_id": types.Schema(
                type=types.Type.STRING,
                description="The ID or username of the channel (e.g., '@my_tech_news' or '-100123456789')."
            ),
            "content": types.Schema(
                type=types.Type.STRING,
                description="The finalized, formatted text to publish. Ensure it is under 4000 characters."
            ),
            "image_path": types.Schema(
                type=types.Type.STRING,
                description="(Optional) The absolute local path to an image file (e.g., '/root/jarvis/workspace/images/news.jpg'). Leave empty if text-only."
            )
        }

    def get_required(self) -> List[str]:
        return ["content"]

    async def execute(self, **kwargs) -> str:
        channel_id = getattr(Config, "TELEGRAM_CHANNEL_ID", None)
        if not channel_id or channel_id == "@your_channel_username":
            return "❌ Error: TELEGRAM_CHANNEL_ID is not properly set in config.py!"
            
        content = kwargs.get("content")
        image_path = kwargs.get("image_path", "")

        if not Config.TELEGRAM_TOKEN:
            return "❌ Error: Telegram Token is missing in system configuration."

        try:
            bot = Bot(token=Config.TELEGRAM_TOKEN)

            if len(content) > 4000:
                return f"❌ CRITICAL ERROR: The content is {len(content)} characters long! Telegram's limit is 4000. DO NOT post this. Rewrite the content immediately to be much shorter (under 3000 chars) and try posting again."

            # 1. ပုံပါရင် Photo Message အနေနဲ့ ပို့မယ် (Caption နဲ့ တွဲပြီး)
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as photo_file:
                    await bot.send_photo(
                        chat_id=channel_id,
                        photo=photo_file,
                        caption=content,
                        parse_mode="HTML"  # HTML tags လေးတွေ (<b>, <i>) သုံးလို့ရအောင်
                    )
                logger.info(f"📢 Published Photo + Content to {channel_id}")
                return f"✅ Success: Photo and content published successfully to {channel_id}."
            
            # 2. ပုံမပါရင် စာသက်သက် (Text Message) အနေနဲ့ ပို့မယ်
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=content,
                    parse_mode="HTML"
                )
                logger.info(f"📢 Published Text Content to {channel_id}")
                return f"✅ Success: Text content published successfully to {channel_id}."

        except Exception as e:
            logger.error(f"Failed to publish to channel: {e}")
            return f"❌ Failed to publish: {str(e)}"