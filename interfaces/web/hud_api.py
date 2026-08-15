"""Read-only JSON feeds for the web HUD popup widgets (weather, orders).

Both endpoints sit behind the same Cloudflare Access gate as the rest of the
app — no extra auth at this layer by design.
"""
import logging

import httpx
from fastapi import APIRouter, Query

logger = logging.getLogger("JARVIS_HUD_API")

router = APIRouter()


@router.get("/api/hud/weather")
async def hud_weather(city: str = Query(default="Mandalay", max_length=80)):
    """Current weather via wttr.in (no API key required)."""
    city = city.strip() or "Mandalay"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"https://wttr.in/{city}",
                params={"format": "j1"},
                headers={"User-Agent": "jarvis-hud"},
            )
            resp.raise_for_status()
            payload = resp.json()
        current = payload["current_condition"][0]
        return {
            "ok": True,
            "city": city,
            "temp_c": current.get("temp_C"),
            "feels_c": current.get("FeelsLikeC"),
            "desc": (current.get("weatherDesc") or [{}])[0].get("value", ""),
            "humidity": current.get("humidity"),
            "wind_kmph": current.get("windspeedKmph"),
        }
    except Exception as e:
        logger.error(f"Weather fetch failed for {city!r}: {e}")
        return {"ok": False, "city": city, "error": str(e)}


@router.get("/api/hud/orders")
async def hud_orders(limit: int = Query(default=10, ge=1, le=50)):
    """Recent jammer orders + VIP transactions recorded from the Telegram flow."""
    try:
        from memory.business_storage import list_recent_jammer_orders, DB_PATH
        from core.db import db_connection

        orders = list_recent_jammer_orders(limit)
        with db_connection(DB_PATH) as conn:
            conn.row_factory = None
            rows = conn.execute(
                "SELECT transaction_id, amount, customer_name, product, status, created_at "
                "FROM transactions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        transactions = [
            {
                "transaction_id": r[0],
                "amount": r[1],
                "customer_name": r[2],
                "product": r[3],
                "status": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]
        return {"ok": True, "orders": orders, "transactions": transactions}
    except Exception as e:
        logger.error(f"Orders fetch failed: {e}")
        return {"ok": False, "orders": [], "transactions": [], "error": str(e)}


@router.get("/api/hud/schedule")
async def hud_schedule():
    """Active APScheduler jobs (persisted in memory/jarvis_schedules.db)."""
    try:
        from core.scheduler import jarvis_scheduler

        jobs = []
        for job in jarvis_scheduler.scheduler.get_jobs():
            prompt = ""
            if job.args:
                prompt = str(job.args[0])[:120]
            jobs.append({
                "id": job.id,
                "prompt": prompt,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return {"ok": True, "jobs": jobs}
    except Exception as e:
        logger.error(f"Schedule fetch failed: {e}")
        return {"ok": False, "jobs": [], "error": str(e)}


@router.get("/api/hud/tasks")
async def hud_tasks():
    """Sir's ongoing task list (same source as the manage_task tool)."""
    try:
        from memory.memory_controller import memory_controller
        from config import Config

        text = memory_controller.get_tasks(Config.ALLOWED_USER_ID) or ""
        return {"ok": True, "tasks_text": text}
    except Exception as e:
        logger.error(f"Tasks fetch failed: {e}")
        return {"ok": False, "tasks_text": "", "error": str(e)}


@router.get("/api/hud/sysinfo")
async def hud_sysinfo():
    """Lightweight VPS vitals for the HUD corner panel / sysinfo widget."""
    try:
        import psutil

        disk = psutil.disk_usage("/")
        mem = psutil.virtual_memory()
        return {
            "ok": True,
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "ram_percent": mem.percent,
            "ram_used_mb": round(mem.used / 1024 / 1024),
            "ram_total_mb": round(mem.total / 1024 / 1024),
            "disk_percent": disk.percent,
        }
    except Exception as e:
        logger.error(f"Sysinfo fetch failed: {e}")
        return {"ok": False, "error": str(e)}
