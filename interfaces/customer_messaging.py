"""
Thin adapter for customer messaging via the running Pyrogram userbot.
Business tools should use this instead of reaching into sys.modules directly.
"""
from __future__ import annotations

import logging
import sys
from typing import Any, Optional

logger = logging.getLogger("CUSTOMER_MESSAGING")


class CustomerMessagingAdapter:
    """Resolve the live userbot app and send customer-facing media/messages."""

    MODULE_NAME = "interfaces.userbot.secretary_main"

    def get_app(self) -> Optional[Any]:
        module = sys.modules.get(self.MODULE_NAME)
        if not module:
            return None
        return getattr(module, "app", None)

    def require_app(self):
        app = self.get_app()
        if not app:
            raise RuntimeError("Pyrogram userbot app not running in this process.")
        return app

    async def send_message(self, chat_id: int, message: str, parse_mode=None) -> None:
        app = self.require_app()
        kwargs = {}
        if parse_mode is not None:
            kwargs["parse_mode"] = parse_mode
        await app.send_message(chat_id, message, **kwargs)

    async def send_photo(self, chat_id: int, path: str, caption: str = "") -> None:
        app = self.require_app()
        await app.send_photo(chat_id, path, caption=caption or None)

    async def resolve_chat(self, chat_id: int) -> Any:
        """
        Warm Pyrogram's peer cache and prove that the userbot account can see
        this chat. A numeric private-channel ID cannot be resolved until that
        account has encountered the peer (normally by being a member/admin).
        """
        app = self.require_app()

        # Dialog iteration populates Pyrogram's peer database. This fixes the
        # common "Peer id invalid" case after a new/recreated session.
        try:
            async for dialog in app.get_dialogs():
                if getattr(dialog.chat, "id", None) == chat_id:
                    return dialog.chat
        except Exception as exc:
            logger.warning("Could not warm userbot dialog cache: %s", exc)

        try:
            return await app.get_chat(chat_id)
        except Exception as exc:
            raise RuntimeError(
                f"VIP channel {chat_id} is not resolvable by the userbot. "
                "Verify VIP_CHANNEL_ID and add the userbot account to that "
                "channel as an administrator with invite-link permission. "
                "Telegram content-protection does not cause this error."
            ) from exc

    async def create_chat_invite_link(self, channel_id: int, member_limit: int = 1, name: str = "") -> Any:
        app = self.require_app()
        chat = await self.resolve_chat(channel_id)
        return await app.create_chat_invite_link(
            chat.id,
            member_limit=member_limit,
            name=name,
        )


customer_messaging = CustomerMessagingAdapter()
