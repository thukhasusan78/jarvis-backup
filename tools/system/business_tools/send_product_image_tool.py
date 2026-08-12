import os
import sys
import logging
from tools.base import BaseTool
from google.genai import types

logger = logging.getLogger("PRODUCT_IMAGE_TOOL")

PRODUCTS_DIR = os.path.join("workspace", "products")

class SendProductImageTool(BaseTool):
    name = "send_product_image"
    description = "Send a product photo from workspace/products/ to a customer via the userbot session. Use this when a customer asks to see product photos."

    def get_parameters(self):
        return {
            "chat_id": types.Schema(type=types.Type.INTEGER, description="The exact Telegram Chat ID of the customer."),
            "image_filename": types.Schema(type=types.Type.STRING, description="Filename inside workspace/products/ only (e.g. jammer_2ant.jpg)."),
            "caption": types.Schema(type=types.Type.STRING, description="Optional caption for the photo.")
        }

    def get_required(self):
        return ["chat_id", "image_filename"]

    async def execute(self, chat_id: int, image_filename: str, caption: str = "") -> str:
        # 1. Path-traversal guard
        safe_name = os.path.basename(image_filename)
        if safe_name != image_filename or ".." in image_filename or "/" in image_filename or "\\" in image_filename:
            return "❌ Error: Invalid filename. Only plain filenames inside workspace/products/ are allowed."

        os.makedirs(PRODUCTS_DIR, exist_ok=True)
        path = os.path.join(PRODUCTS_DIR, safe_name)

        if not os.path.exists(path):
            available = sorted(f for f in os.listdir(PRODUCTS_DIR) if os.path.isfile(os.path.join(PRODUCTS_DIR, f)))
            listing = ", ".join(available) if available else "(no product images uploaded yet)"
            return f"❌ Error: '{safe_name}' not found. Available images: {listing}"

        try:
            module = sys.modules.get('interfaces.userbot.secretary_main')
            app = getattr(module, 'app', None)
            if not app:
                return "❌ Error: Pyrogram userbot app not running in this process."
            await app.send_photo(chat_id, path, caption=caption or None)
            logger.info(f"📸 Sent product image {safe_name} to chat {chat_id}")
            return f"✅ SUCCESS: Product image {safe_name} sent to Chat ID {chat_id}."
        except Exception as e:
            logger.error(f"Product Image Tool Error: {e}")
            return f"❌ Failed to send product image: {e}"
