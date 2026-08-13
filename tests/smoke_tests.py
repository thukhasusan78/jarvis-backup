"""
🧪 Jarvis Smoke Tests — Business-critical pure functions
Run: venv/bin/python tests/smoke_tests.py
(API keys / Telegram / Gemini မလိုပါ — Offline စမ်းသပ်မှုများသာ)
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.registry import tool_registry
from memory.sql_storage import sql_storage

PASS, FAIL = 0, 0

def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


async def test_send_product_image_guard():
    print("\n📸 send_product_image — path-traversal guard")
    tool = tool_registry.get_tool("send_product_image")
    # 1. Traversal attempts must be rejected
    for bad in ["../../etc/passwd", "..\\windows\\system32", "sub/dir/x.jpg", "a/b.jpg"]:
        r = await tool.execute(chat_id=123, image_filename=bad)
        check(f"rejects '{bad}'", r.startswith("❌") and "Invalid filename" in r, r)
    # 2. Missing file → error listing available images
    r = await tool.execute(chat_id=123, image_filename="nonexistent_ghost.jpg")
    check("missing file lists available images", "not found" in r and "Available images" in r, r)
    # 3. Existing file but no userbot running → clean error (not exception)
    r = await tool.execute(chat_id=123, image_filename="jammer_2ant.jpg")
    check("no-userbot clean error", r.startswith("❌") and "not running" in r, r)
    # 4. R2 prefix matching: 'jammer_3ant' must resolve to files (not "not found")
    r = await tool.execute(chat_id=123, image_filename="jammer_3ant")
    check("prefix 'jammer_3ant' resolves to files", "not running" in r, r)
    r = await tool.execute(chat_id=123, image_filename="ghost_prefix_xyz")
    check("unknown prefix → not found listing", "not found" in r and "Available images" in r, r)


async def test_vip_invite_config_guard():
    print("\n💎 generate_vip_invite_link — config guard")
    from config import Config
    tool = tool_registry.get_tool("generate_vip_invite_link")
    original = Config.VIP_CHANNEL_ID
    try:
        Config.VIP_CHANNEL_ID = 0
        r = await tool.execute(customer_name="TestCustomer")
        check("VIP_CHANNEL_ID=0 → clean config error", r.startswith("❌") and "VIP_CHANNEL_ID" in r, r)
    finally:
        Config.VIP_CHANNEL_ID = original


def test_role_gating():
    print("\n🔐 Role gating — business_manager & secretary tool visibility")
    bm = [d.name for d in tool_registry.get_declarations_for_role("business_manager")]
    sec = [d.name for d in tool_registry.get_declarations_for_role("secretary")]
    for t in ["verify_payment", "generate_vip_invite_link", "reply_to_customer", "record_jammer_order"]:
        check(f"business_manager sees '{t}'", t in bm, str(bm))
    check("secretary sees 'reply_to_customer'", "reply_to_customer" in sec, str(sec))
    check("secretary sees 'send_product_image'", "send_product_image" in sec, str(sec))
    check("no 'generate_vpn_key' anywhere", tool_registry.get_tool("generate_vpn_key") is None)


def test_vision_quota_storage():
    print("\n🛡️ Vision quota storage — roundtrip & window pruning")
    import time
    fake_user = -999000111
    now = time.time()
    sql_storage.set_vision_timestamps(fake_user, [now - 90000, now - 3600, now - 60])  # 1 stale, 2 fresh
    ts = sql_storage.get_vision_timestamps(fake_user)
    check("roundtrip returns 3 entries", len(ts) == 3, str(ts))
    fresh = [t for t in ts if now - t < 86400]
    check("24h window pruning keeps 2", len(fresh) == 2, str(fresh))
    sql_storage.set_vision_timestamps(fake_user, [])
    check("reset clears all", sql_storage.get_vision_timestamps(fake_user) == [])


def test_jammer_order_schema():
    print("\n📦 record_jammer_order — declaration exposes all params")
    tool = tool_registry.get_tool("record_jammer_order")
    d = tool.get_declaration()
    props = set(d.parameters.properties.keys())
    required = set(d.parameters.required)
    expected = {"chat_id", "jammer_model", "customer_name", "phone", "city", "address", "payment_type"}
    check("all 7 params declared (incl. jammer_model)", props == expected, str(props))
    check("all 7 params required", required == expected, str(required))


async def main():
    print("=" * 50)
    print("🧪 JARVIS SMOKE TESTS")
    print("=" * 50)
    await test_send_product_image_guard()
    await test_vip_invite_config_guard()
    test_role_gating()
    test_vision_quota_storage()
    test_jammer_order_schema()
    print("\n" + "=" * 50)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 50)
    sys.exit(1 if FAIL else 0)

if __name__ == "__main__":
    asyncio.run(main())
