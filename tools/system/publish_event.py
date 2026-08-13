import json
import logging
from typing import Dict, List, Any
from google.genai import types
from tools.base import BaseTool
from core.message_broker import publish_event

logger = logging.getLogger("JARVIS_PUBLISHER")

ALLOWED_TARGETS = {
    "ceo",
    "sysadmin",
    "researcher",
    "deep_researcher",
    "business_manager",
    "secretary",
}


class PublishEventTool(BaseTool):
    """Publish structured (or legacy string) events to the Message Broker."""
    name = "publish_event"
    description = (
        "Publish an event to the Message Broker for another agent. "
        "Prefer structured fields (product, chat_id, image_path, etc.) over free-text data. "
        "Allowed targets: ceo, sysadmin, researcher, deep_researcher, business_manager."
    )
    owner_role = "all"
    is_terminal = True

    def get_parameters(self) -> Dict[str, types.Schema]:
        return {
            "event_type": types.Schema(
                type=types.Type.STRING,
                description="e.g. 'VERIFY_AND_FULFILL_SUBSCRIPTION', 'VERIFY_AND_FULFILL_JAMMER', 'RECORD_JAMMER_ORDER'",
            ),
            "target_agent": types.Schema(
                type=types.Type.STRING,
                description="Next agent role (e.g. 'business_manager', 'ceo')",
            ),
            "data": types.Schema(
                type=types.Type.STRING,
                description="Legacy free-text payload OR a JSON string of structured fields.",
            ),
            "product": types.Schema(
                type=types.Type.STRING,
                description="Optional structured: 'vip' or 'jammer'.",
            ),
            "chat_id": types.Schema(type=types.Type.INTEGER, description="Optional structured: customer chat id."),
            "image_path": types.Schema(type=types.Type.STRING, description="Optional structured: receipt/image path."),
            "customer_name": types.Schema(type=types.Type.STRING, description="Optional structured: customer name."),
            "jammer_model": types.Schema(type=types.Type.STRING, description="Optional structured: '2 Antenna' / '3 Antenna'."),
            "phone": types.Schema(type=types.Type.STRING, description="Optional structured: phone."),
            "city": types.Schema(type=types.Type.STRING, description="Optional structured: city."),
            "address": types.Schema(type=types.Type.STRING, description="Optional structured: address."),
            "payment_type": types.Schema(type=types.Type.STRING, description="Optional structured: COD / Prepaid / deposit."),
            "min_amount": types.Schema(type=types.Type.INTEGER, description="Optional structured: expected min payment MMK."),
            "end_goal": types.Schema(type=types.Type.STRING, description="Optional structured: short end-goal instruction."),
        }

    def get_required(self) -> List[str]:
        return ["event_type", "target_agent"]

    def _build_payload(self, kwargs: Dict[str, Any]) -> dict:
        structured_keys = (
            "product", "chat_id", "image_path", "customer_name", "jammer_model",
            "phone", "city", "address", "payment_type", "min_amount", "end_goal",
        )
        payload: Dict[str, Any] = {
            "event_type": kwargs.get("event_type"),
            "target_agent": kwargs.get("target_agent"),
        }
        for key in structured_keys:
            if kwargs.get(key) is not None and kwargs.get(key) != "":
                payload[key] = kwargs[key]

        data = kwargs.get("data")
        if data:
            # Allow JSON string in data to merge structured fields
            if isinstance(data, str):
                stripped = data.strip()
                if stripped.startswith("{"):
                    try:
                        parsed = json.loads(stripped)
                        if isinstance(parsed, dict):
                            payload.update(parsed)
                        else:
                            payload["data"] = data
                    except json.JSONDecodeError:
                        payload["data"] = data
                else:
                    payload["data"] = data
            else:
                payload["data"] = data

        # A customer's Telegram display name is a useful label, not a payment
        # security factor. Never block a paid workflow only because the model
        # omitted it; retain a deterministic ledger/invite label instead.
        if payload.get("event_type") in {
            "VERIFY_AND_FULFILL_SUBSCRIPTION",
            "VERIFY_AND_FULFILL_JAMMER",
            "RECORD_JAMMER_ORDER",
        }:
            chat_id = payload.get("chat_id")
            if not payload.get("customer_name") and chat_id is not None:
                payload["customer_name"] = f"Telegram Customer {chat_id}"

        return payload

    @staticmethod
    def _validate_business_payload(event_type: str, payload: Dict[str, Any]) -> str:
        required_by_event = {
            "VERIFY_AND_FULFILL_SUBSCRIPTION": (
                "chat_id",
                "image_path",
                "customer_name",
            ),
            "VERIFY_AND_FULFILL_JAMMER": (
                "chat_id",
                "image_path",
                "customer_name",
                "jammer_model",
                "phone",
                "city",
                "address",
                "payment_type",
            ),
            "RECORD_JAMMER_ORDER": (
                "chat_id",
                "customer_name",
                "jammer_model",
                "phone",
                "city",
                "address",
                "payment_type",
            ),
        }
        missing = [
            field
            for field in required_by_event.get(event_type, ())
            if payload.get(field) in (None, "")
        ]
        if missing:
            return (
                f"❌ Cannot publish incomplete {event_type}: "
                f"missing {', '.join(missing)}."
            )
        return ""

    async def execute(self, **kwargs) -> str:
        event_type = kwargs.get("event_type")
        target_agent = (kwargs.get("target_agent") or "").strip().lower()

        if target_agent not in ALLOWED_TARGETS:
            return (
                f"❌ Invalid target_agent '{target_agent}'. "
                f"Allowed: {sorted(ALLOWED_TARGETS)}"
            )

        payload = self._build_payload(kwargs)
        validation_error = self._validate_business_payload(event_type, payload)
        if validation_error:
            return validation_error

        publish_event(event_type, target_agent, payload)

        import os
        square_path = os.path.join("workspace", "square.md")
        os.makedirs("workspace", exist_ok=True)
        with open(square_path, "a", encoding="utf-8") as f:
            preview = json.dumps(payload, ensure_ascii=False)[:1000]
            f.write(f"\n\n--- 📬 EVENT PUBLISHED: [{event_type}] targeting {target_agent.upper()} ---\n{preview}\n")

        return f"✅ Event '{event_type}' published to Message Broker for '{target_agent}'. Your process will now terminate."
