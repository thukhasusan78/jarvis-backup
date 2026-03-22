import logging
import os
from typing import Dict, List
from google.genai import types
from tools.base import BaseTool
from config import Config
from telegram import Bot
from memory.memory_controller import memory_controller

logger = logging.getLogger("JARVIS_REPORT")

class ReportToSirTool(BaseTool):
    """CEO သီးသန့်သုံးရန်။ အလုပ်ပြီးစီးကြောင်း ဆရာ့ထံ Report တင်ရန် နှင့် ဖိုင်များပို့ရန် Tool"""
    name = "report_to_sir"
    description = "Send a direct message to the Boss (Sir) via Telegram. Use this ONLY to report the final completion of a background mission. Can attach a photo, video, or document if a valid local file path is provided."
    owner_role = "ceo" 
    is_terminal = True

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "message": types.Schema(
                type=types.Type.STRING,
                description="The final report message to send to the Boss. Write in elegant Burmese."
            ),
            "photo_path": types.Schema(
                type=types.Type.STRING,
                description="(Optional) Absolute local path to an image file to send."
            ),
            "video_path": types.Schema(
                type=types.Type.STRING,
                description="(Optional) Absolute local path to a video file to send."
            ),
            "document_path": types.Schema(
                type=types.Type.STRING,
                description="(Optional) Absolute local path to a document (pdf, zip, etc.) to send."
            )
        }

    def get_required(self) -> List[str]:
        return ["message"]

    async def execute(self, **kwargs) -> str:
        message = kwargs.get("message")
        photo_path = kwargs.get("photo_path")
        video_path = kwargs.get("video_path")
        doc_path = kwargs.get("document_path")
        user_id = Config.ALLOWED_USER_ID
        
        try:
            bot = Bot(token=Config.TELEGRAM_TOKEN)
            
            # Telegram ၏ Caption စာလုံးရေ ကန့်သတ်ချက် (1024) ကို စစ်ဆေးခြင်း
            caption = message if len(message) <= 1024 else "Sir, here is the requested file."
            
            # 1. Media ရှိလျှင် ပို့မည်
            media_sent = False
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as f:
                    await bot.send_photo(chat_id=user_id, photo=f, caption=caption, parse_mode="HTML")
                media_sent = True
            elif video_path and os.path.exists(video_path):
                with open(video_path, 'rb') as f:
                    await bot.send_video(chat_id=user_id, video=f, caption=caption, parse_mode="HTML")
                media_sent = True
            elif doc_path and os.path.exists(doc_path):
                with open(doc_path, 'rb') as f:
                    await bot.send_document(chat_id=user_id, document=f, caption=caption, parse_mode="HTML")
                media_sent = True
                
            # 2. Message ရှည်နေလျှင် သို့မဟုတ် Media မပါလျှင် Text သီးသန့် ပို့မည်
            if not media_sent or len(message) > 1024:
                await bot.send_message(chat_id=user_id, text=message, parse_mode="HTML")
            
            # 3. History ထဲ မှတ်မည်
            memory_controller.add_chat_message(user_id, "model", message)
            
            return "✅ Report and media (if any) successfully sent to the Boss and saved to History. Your task is complete."
        except Exception as e:
            logger.error(f"Report Error: {e}")
            return f"❌ Failed to send report: {e}"