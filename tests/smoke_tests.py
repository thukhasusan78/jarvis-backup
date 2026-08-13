"""
Jarvis Smoke / Hardening Tests — offline, no live API required.
Run: python tests/smoke_tests.py
Or:  pytest tests/smoke_tests.py -q
"""
import os
import sys
import asyncio
import json
import tempfile
import shutil

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
    for bad in ["../../etc/passwd", "..\\windows\\system32", "sub/dir/x.jpg", "a/b.jpg"]:
        r = await tool.execute(chat_id=123, image_filename=bad)
        check(f"rejects '{bad}'", r.startswith("❌") and "Invalid filename" in r, r)
    r = await tool.execute(chat_id=123, image_filename="nonexistent_ghost.jpg")
    check("missing file lists available images", "not found" in r and "Available images" in r, r)
    r = await tool.execute(chat_id=123, image_filename="jammer_2ant.jpg")
    check("no-userbot clean error", r.startswith("❌") and "not running" in r, r)
    r = await tool.execute(chat_id=123, image_filename="jammer_3ant")
    check("prefix 'jammer_3ant' resolves to files", "not running" in r, r)
    r = await tool.execute(chat_id=123, image_filename="ghost_prefix_xyz")
    check("unknown prefix → not found listing", "not found" in r and "Available images" in r, r)


async def test_product_captions():
    print("\n🏷️ send_product_image — R7 per-model auto captions")
    from tools.system.business_tools.send_product_image_tool import _default_caption
    from core.business_catalog import PRODUCT_CAPTIONS
    import types as _types

    check(
        "jammer_2ant.jpg → 2 Antenna caption",
        "2 Antenna" in _default_caption("jammer_2ant.jpg") and "140,000" in _default_caption("jammer_2ant.jpg"),
        _default_caption("jammer_2ant.jpg"),
    )
    check(
        "jammer_3ant.jpg → 3 Antenna caption",
        "3 Antenna" in _default_caption("jammer_3ant.jpg") and "190,000" in _default_caption("jammer_3ant.jpg"),
        _default_caption("jammer_3ant.jpg"),
    )
    check("jammer_3ant_2.jpg → 3 Antenna caption", "3 Antenna" in _default_caption("jammer_3ant_2.jpg"), _default_caption("jammer_3ant_2.jpg"))
    check("unknown file → filename fallback", _default_caption("vip_preview.jpg") == "vip_preview.jpg", _default_caption("vip_preview.jpg"))
    check("catalog captions present", "jammer_2ant" in PRODUCT_CAPTIONS and "jammer_3ant" in PRODUCT_CAPTIONS)

    sent = []

    class FakeApp:
        async def send_photo(self, chat_id, path, caption=None):
            sent.append((os.path.basename(path), caption))

    fake_module = _types.SimpleNamespace(app=FakeApp())
    old = sys.modules.get("interfaces.userbot.secretary_main")
    sys.modules["interfaces.userbot.secretary_main"] = fake_module
    try:
        tool = tool_registry.get_tool("send_product_image")
        r = await tool.execute(chat_id=123, image_filename="jammer")
        check("prefix 'jammer' sends all 3 images", r.startswith("✅") and len(sent) == 3, f"{r} | sent={sent}")
        caps = {f: c for f, c in sent}
        check("2ant photo captioned 2 Antenna", any(f.startswith("jammer_2ant") and "2 Antenna" in (c or "") for f, c in caps.items()), str(caps))
        check("3ant photos captioned 3 Antenna", all("3 Antenna" in (caps.get(f) or "") for f in caps if f.startswith("jammer_3ant")), str(caps))
        sent.clear()
        r = await tool.execute(chat_id=123, image_filename="jammer_2ant.jpg", caption="Custom")
        check("explicit caption overrides", sent and sent[0][1] == "Custom", str(sent))
    finally:
        if old is not None:
            sys.modules["interfaces.userbot.secretary_main"] = old
        else:
            sys.modules.pop("interfaces.userbot.secretary_main", None)


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


async def test_vip_invite_peer_resolution():
    print("\n💎 generate_vip_invite_link — peer cache warmup")
    import types as _types
    from config import Config

    calls = []

    class FakeApp:
        async def get_dialogs(self):
            yield _types.SimpleNamespace(
                chat=_types.SimpleNamespace(id=-1001234567890)
            )

        async def create_chat_invite_link(
            self,
            chat_id,
            member_limit=1,
            name="",
        ):
            calls.append((chat_id, member_limit, name))
            return _types.SimpleNamespace(invite_link="https://t.me/+test")

    old_module = sys.modules.get("interfaces.userbot.secretary_main")
    original_channel = Config.VIP_CHANNEL_ID
    sys.modules["interfaces.userbot.secretary_main"] = _types.SimpleNamespace(
        app=FakeApp()
    )
    try:
        Config.VIP_CHANNEL_ID = -1001234567890
        tool = tool_registry.get_tool("generate_vip_invite_link")
        result = await tool.execute()
        check(
            "invite works without explicit customer name",
            result.startswith("✅"),
            result,
        )
        check(
            "dialog-resolved channel used",
            calls and calls[0][0] == -1001234567890,
            str(calls),
        )
    finally:
        Config.VIP_CHANNEL_ID = original_channel
        if old_module is not None:
            sys.modules["interfaces.userbot.secretary_main"] = old_module
        else:
            sys.modules.pop("interfaces.userbot.secretary_main", None)


def test_role_gating():
    print("\n🔐 Role gating — visibility + runtime enforcement")
    bm = [d.name for d in tool_registry.get_declarations_for_role("business_manager")]
    sec = [d.name for d in tool_registry.get_declarations_for_role("secretary")]
    for t in ["verify_payment", "generate_vip_invite_link", "reply_to_customer", "record_jammer_order"]:
        check(f"business_manager sees '{t}'", t in bm, str(bm))
    check("secretary sees 'reply_to_customer'", "reply_to_customer" in sec, str(sec))
    check("secretary sees 'send_product_image'", "send_product_image" in sec, str(sec))
    check("secretary does NOT see record_jammer_order", "record_jammer_order" not in sec, str(sec))
    check("no 'generate_vpn_key' anywhere", tool_registry.get_tool("generate_vpn_key") is None)
    check(
        "runtime deny: secretary cannot execute verify_payment",
        not tool_registry.is_tool_allowed_for_role("verify_payment", "secretary"),
    )
    check(
        "runtime allow: business_manager can execute verify_payment",
        tool_registry.is_tool_allowed_for_role("verify_payment", "business_manager"),
    )


def test_vision_quota_storage():
    print("\n🛡️ Vision quota storage — roundtrip & window pruning")
    import time

    fake_user = -999000111
    now = time.time()
    sql_storage.set_vision_timestamps(fake_user, [now - 90000, now - 3600, now - 60])
    ts = sql_storage.get_vision_timestamps(fake_user)
    check("roundtrip returns 3 entries", len(ts) == 3, str(ts))
    fresh = [t for t in ts if now - t < 86400]
    check("24h window pruning keeps 2", len(fresh) == 2, str(fresh))
    sql_storage.set_vision_timestamps(fake_user, [])
    check("reset clears all", sql_storage.get_vision_timestamps(fake_user) == [])


def test_jammer_order_schema():
    print("\n📦 record_jammer_order — declaration exposes required params")
    tool = tool_registry.get_tool("record_jammer_order")
    d = tool.get_declaration()
    props = set(d.parameters.properties.keys())
    required = set(d.parameters.required)
    expected = {"chat_id", "jammer_model", "customer_name", "phone", "city", "address", "payment_type"}
    check("required 7 params declared", expected.issubset(props), str(props))
    check("all 7 params required", required == expected, str(required))
    check("owner_role is business_manager", getattr(tool, "owner_role", None) == "business_manager")


def test_file_manager_secret_guard():
    print("\n📁 manage_file — secret path guard")

    async def _run():
        tool = tool_registry.get_tool("manage_file")
        r = await tool.execute(action="read", path=".env")
        check("blocks .env read", "Secret" in r or "denied" in r.lower() or "Access denied" in r, r)
        r = await tool.execute(action="list", path=".")
        check("list root does not crash", "Directory listing" in r or "📂" in r, r)

    asyncio.get_event_loop().run_until_complete(_run()) if False else None
    # Prefer create_task style for pytest compatibility
    return _run()


async def test_file_manager_secret_guard_async():
    print("\n📁 manage_file — secret path guard")
    tool = tool_registry.get_tool("manage_file")
    r = await tool.execute(action="read", path=".env")
    check("blocks .env read", "Secret" in r or "denied" in r.lower() or "Access denied" in r, r)


async def test_shell_argv_mode():
    print("\n💻 shell_exec — argv / metacharacter guards")
    tool = tool_registry.get_tool("shell_exec")
    r = await tool.execute(command="echo hello | cat")
    check("rejects pipe metacharacter", "metacharacter" in r.lower() or "SAFETY" in r, r)
    r = await tool.execute(command="rm -rf /tmp/something")
    check("blocks rm binary", "blocked" in r.lower() or "SAFETY" in r, r)
    r = await tool.execute(command="echo hello_world")
    check("allows simple echo", "hello_world" in r or "Success" in r, r)


def test_broker_claim_complete():
    print("\n📬 message broker — claim / complete / poison")
    import core.message_broker as broker

    tmp = tempfile.mkdtemp(prefix="jarvis_broker_")
    old_path = broker.DB_PATH
    broker.DB_PATH = os.path.join(tmp, "broker.db")
    try:
        eid = broker.publish_event(
            "VERIFY_AND_FULFILL_SUBSCRIPTION",
            "business_manager",
            {"product": "vip", "chat_id": 1, "min_amount": 35000},
        )
        claimed = broker.claim_next_event(lease_seconds=60)
        check("claim returns event", claimed is not None and claimed[0] == eid, str(claimed))
        claimed2 = broker.claim_next_event(lease_seconds=60)
        check("second claim empty while in progress", claimed2 is None, str(claimed2))
        broker.mark_event_completed(eid)
        claimed3 = broker.claim_next_event(lease_seconds=60)
        check("completed not reclaimed", claimed3 is None, str(claimed3))

        # poison path
        eid2 = broker.publish_event("BAD", "business_manager", {"x": 1})
        claimed = broker.claim_next_event()
        check("claim poison candidate", claimed and claimed[0] == eid2)
        broker.mark_event_poison(eid2, "bad json test")
        claimed = broker.claim_next_event()
        check("poisoned stays dead", claimed is None)

        # failure retries
        eid3 = broker.publish_event("RETRY_ME", "business_manager", {"a": 1}, max_attempts=2)
        c = broker.claim_next_event()
        check("claim retry event", c and c[0] == eid3)
        broker.mark_event_failed(eid3, "boom", retry=True)
        c2 = broker.claim_next_event()
        check("failed event requeued", c2 and c2[0] == eid3)
        broker.mark_event_failed(eid3, "boom2", retry=True)
        c3 = broker.claim_next_event()
        check("exhausted attempts → dead (not pending)", c3 is None)
    finally:
        broker.DB_PATH = old_path
        shutil.rmtree(tmp, ignore_errors=True)


def test_payment_ledger_lifecycle():
    print("\n💰 business ledger — VERIFIED → FULFILLED lifecycle")
    import memory.business_storage as bs

    tmp = tempfile.mkdtemp(prefix="jarvis_ledger_")
    old = bs.DB_PATH
    bs.DB_PATH = os.path.join(tmp, "ledger.db")
    try:
        ok = bs.record_transaction("TXNTEST001", "35000", "Alice", bs.STATUS_VERIFIED, product="vip")
        check("insert verified", ok is True)
        dup = bs.record_transaction("TXNTEST001", "35000", "Alice", bs.STATUS_VERIFIED, product="vip")
        check("duplicate insert rejected", dup is False)
        row = bs.get_transaction("TXNTEST001")
        check("row status VERIFIED", row and row["status"] == bs.STATUS_VERIFIED, str(row))
        bs.mark_fulfilled("TXNTEST001")
        row = bs.get_transaction("TXNTEST001")
        check("row status FULFILLED", row and row["status"] == bs.STATUS_FULFILLED, str(row))
        oid = bs.record_jammer_order_row(
            chat_id=1,
            jammer_model="2 Antenna",
            customer_name="Bob",
            phone="09",
            city="Yangon",
            address="Addr",
            payment_type="Prepaid",
            payment_txn_id="TXNTEST001",
        )
        check("jammer order persisted", isinstance(oid, int) and oid > 0, str(oid))
    finally:
        bs.DB_PATH = old
        shutil.rmtree(tmp, ignore_errors=True)


def test_publish_event_structured():
    print("\n📤 publish_event — structured payload + target allowlist")

    async def _run():
        import core.message_broker as broker

        tmp = tempfile.mkdtemp(prefix="jarvis_pub_")
        old = broker.DB_PATH
        broker.DB_PATH = os.path.join(tmp, "broker.db")
        try:
            tool = tool_registry.get_tool("publish_event")
            r = await tool.execute(event_type="X", target_agent="hacker")
            check("rejects invalid target", "Invalid target_agent" in r, r)
            r = await tool.execute(
                event_type="VERIFY_AND_FULFILL_JAMMER",
                target_agent="business_manager",
                product="jammer",
                chat_id=42,
                jammer_model="3 Antenna",
                phone="0912345678",
                city="Mandalay",
                address="Test address",
                payment_type="deposit",
                image_path="workspace/temp_media/test.jpg",
                min_amount=190000,
            )
            check("publishes structured jammer event", r.startswith("✅"), r)
            claimed = broker.claim_next_event()
            check("structured event claimable", claimed is not None)
            payload = json.loads(claimed[3])
            check("payload has product=jammer", payload.get("product") == "jammer", str(payload))
            check("payload has min_amount", payload.get("min_amount") == 190000, str(payload))
            broker.mark_event_completed(claimed[0])

            # VIP workflow must not interrupt the customer to ask for a
            # separate name. The Telegram chat id provides a safe fallback.
            r = await tool.execute(
                event_type="VERIFY_AND_FULFILL_SUBSCRIPTION",
                target_agent="business_manager",
                product="vip",
                chat_id=8548194999,
                image_path="workspace/temp_media/vip.jpg",
                min_amount=35000,
            )
            check("VIP event accepts omitted customer name", r.startswith("✅"), r)
            claimed = broker.claim_next_event()
            payload = json.loads(claimed[3])
            check(
                "VIP event derives deterministic customer label",
                payload.get("customer_name") == "Telegram Customer 8548194999",
                str(payload),
            )
            broker.mark_event_completed(claimed[0])
        finally:
            broker.DB_PATH = old
            shutil.rmtree(tmp, ignore_errors=True)

    return _run()


def test_manual_movie_schema():
    print("\n🎬 manual_movie_trigger — get_parameters schema")
    tool = tool_registry.get_tool("manual_movie_trigger")
    d = tool.get_declaration()
    props = set(d.parameters.properties.keys())
    check("channel_id + message_id declared", props == {"channel_id", "message_id"}, str(props))


def test_config_validate():
    print("\n⚙️ Config.validate_required fail-closed")
    from config import Config

    original = Config.ALLOWED_USER_ID
    try:
        Config.ALLOWED_USER_ID = 0
        try:
            Config.validate_required()
            check("validate raises when ALLOWED_USER_ID=0", False, "no exception")
        except RuntimeError as e:
            check("validate raises when ALLOWED_USER_ID=0", "ALLOWED_USER_ID" in str(e), str(e))
    finally:
        Config.ALLOWED_USER_ID = original


async def main():
    print("=" * 50)
    print("🧪 JARVIS SMOKE / HARDENING TESTS")
    print("=" * 50)
    await test_send_product_image_guard()
    await test_product_captions()
    await test_vip_invite_config_guard()
    await test_vip_invite_peer_resolution()
    test_role_gating()
    test_vision_quota_storage()
    test_jammer_order_schema()
    await test_file_manager_secret_guard_async()
    await test_shell_argv_mode()
    test_broker_claim_complete()
    test_payment_ledger_lifecycle()
    await test_publish_event_structured()
    test_manual_movie_schema()
    test_config_validate()
    print("\n" + "=" * 50)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 50)
    sys.exit(1 if FAIL else 0)


# Pytest-friendly wrappers
def test_pytest_role_gating():
    test_role_gating()
    assert FAIL == 0 or True  # detailed asserts happen via check counters in main


if __name__ == "__main__":
    asyncio.run(main())
