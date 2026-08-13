import os
import logging
from tools.base import BaseTool
from google.genai import types
from core.business_catalog import PRODUCT_CAPTIONS
from interfaces.customer_messaging import customer_messaging

logger = logging.getLogger("PRODUCT_IMAGE_TOOL")

PRODUCTS_DIR = os.path.join("workspace", "products")


def _default_caption(fname: str) -> str:
    """Resolve the default caption for a product file by prefix; fall back to the filename."""
    stem = os.path.splitext(fname)[0]
    for prefix, cap in PRODUCT_CAPTIONS.items():
        if stem.startswith(prefix):
            return cap
    return fname


class SendProductImageTool(BaseTool):
    name = "send_product_image"
    description = (
        "Send product photo(s) from workspace/products/ to a customer via the userbot session. "
        "If a product name/prefix is given (e.g. 'jammer_3ant'), ALL matching images are sent."
    )

    def get_parameters(self):
        return {
            "chat_id": types.Schema(type=types.Type.INTEGER, description="The exact Telegram Chat ID of the customer."),
            "image_filename": types.Schema(
                type=types.Type.STRING,
                description="Exact filename OR a product prefix (e.g. 'jammer_3ant'). Plain names only, no paths.",
            ),
            "caption": types.Schema(type=types.Type.STRING, description="Optional caption for the photo(s)."),
        }

    def get_required(self):
        return ["chat_id", "image_filename"]

    async def execute(self, chat_id: int, image_filename: str, caption: str = "") -> str:
        safe_name = os.path.basename(image_filename)
        if safe_name != image_filename or ".." in image_filename or "/" in image_filename or "\\" in image_filename:
            return "❌ Error: Invalid filename. Only plain filenames inside workspace/products/ are allowed."

        os.makedirs(PRODUCTS_DIR, exist_ok=True)
        available = sorted(f for f in os.listdir(PRODUCTS_DIR) if os.path.isfile(os.path.join(PRODUCTS_DIR, f)))

        if safe_name in available:
            targets = [safe_name]
        else:
            prefix = os.path.splitext(safe_name)[0]
            targets = [f for f in available if os.path.splitext(f)[0].startswith(prefix)]

        if not targets:
            listing = ", ".join(available) if available else "(no product images uploaded yet)"
            return f"❌ Error: '{safe_name}' not found. Available images: {listing}"

        try:
            sent = []
            for fname in targets:
                per_caption = caption or _default_caption(fname)
                await customer_messaging.send_photo(chat_id, os.path.join(PRODUCTS_DIR, fname), caption=per_caption)
                sent.append(fname)
                logger.info(f"📸 Sent product image {fname} to chat {chat_id}")
            return f"✅ SUCCESS: Sent {len(sent)} product image(s) to Chat ID {chat_id}: {', '.join(sent)}"
        except Exception as e:
            logger.error(f"Product Image Tool Error: {e}")
            return f"❌ Failed to send product image: {e}"
