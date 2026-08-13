import os
import sys
import logging
from tools.base import BaseTool
from google.genai import types

logger = logging.getLogger("PRODUCT_IMAGE_TOOL")

PRODUCTS_DIR = os.path.join("workspace", "products")

# 📡 R7: Self-describing product photos — prefix → default caption (model + DEFAULT price).
# ⚠️ Prices here are static defaults; update this mapping if prices change.
PRODUCT_CAPTIONS = {
    "jammer_2ant": "📡 2 Antenna Jammer — 140,000 Ks",
    "jammer_3ant": "📡 3 Antenna Jammer — 190,000 Ks",
}

def _default_caption(fname: str) -> str:
    """Resolve the default caption for a product file by prefix; fall back to the filename."""
    stem = os.path.splitext(fname)[0]
    for prefix, cap in PRODUCT_CAPTIONS.items():
        if stem.startswith(prefix):
            return cap
    return fname

class SendProductImageTool(BaseTool):
    name = "send_product_image"
    description = "Send product photo(s) from workspace/products/ to a customer via the userbot session. Use this when a customer asks to see product photos. If a product name/prefix is given (e.g. 'jammer_3ant'), ALL matching images are sent."

    def get_parameters(self):
        return {
            "chat_id": types.Schema(type=types.Type.INTEGER, description="The exact Telegram Chat ID of the customer."),
            "image_filename": types.Schema(type=types.Type.STRING, description="Exact filename (e.g. jammer_2ant.jpg) OR a product prefix (e.g. 'jammer_3ant' sends jammer_3ant.jpg, jammer_3ant_2.jpg, ...). Plain names only, no paths."),
            "caption": types.Schema(type=types.Type.STRING, description="Optional caption for the photo(s).")
        }

    def get_required(self):
        return ["chat_id", "image_filename"]

    async def execute(self, chat_id: int, image_filename: str, caption: str = "") -> str:
        # 1. Path-traversal guard
        safe_name = os.path.basename(image_filename)
        if safe_name != image_filename or ".." in image_filename or "/" in image_filename or "\\" in image_filename:
            return "❌ Error: Invalid filename. Only plain filenames inside workspace/products/ are allowed."

        os.makedirs(PRODUCTS_DIR, exist_ok=True)
        available = sorted(f for f in os.listdir(PRODUCTS_DIR) if os.path.isfile(os.path.join(PRODUCTS_DIR, f)))

        # 2. Resolve targets: exact file match, otherwise prefix match (send ALL matching images)
        if safe_name in available:
            targets = [safe_name]
        else:
            prefix = os.path.splitext(safe_name)[0]  # 'jammer_3ant.jpg' or 'jammer_3ant' → 'jammer_3ant'
            targets = [f for f in available if os.path.splitext(f)[0].startswith(prefix)]

        if not targets:
            listing = ", ".join(available) if available else "(no product images uploaded yet)"
            return f"❌ Error: '{safe_name}' not found. Available images: {listing}"

        try:
            module = sys.modules.get('interfaces.userbot.secretary_main')
            app = getattr(module, 'app', None)
            if not app:
                return "❌ Error: Pyrogram userbot app not running in this process."
            sent = []
            for fname in targets:
                per_caption = caption or _default_caption(fname)  # R7: every photo is self-describing
                await app.send_photo(chat_id, os.path.join(PRODUCTS_DIR, fname), caption=per_caption)
                sent.append(fname)
                logger.info(f"📸 Sent product image {fname} to chat {chat_id}")
            return f"✅ SUCCESS: Sent {len(sent)} product image(s) to Chat ID {chat_id}: {', '.join(sent)}"
        except Exception as e:
            logger.error(f"Product Image Tool Error: {e}")
            return f"❌ Failed to send product image: {e}"
