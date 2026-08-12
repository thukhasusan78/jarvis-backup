from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import logging
from config import Config
from tasks.executor import run_scheduled_task 
from apscheduler.triggers.date import DateTrigger
from datetime import datetime

logger = logging.getLogger("JARVIS_SCHEDULER")

class JarvisScheduler:
    def __init__(self):
        # Jobs တွေကို Memory/jarvis.db ထဲမှာ သိမ်းမယ် (Restart ချလည်း မပျောက်တော့ဘူး)
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///memory/jarvis_schedules.db')
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=Config.TIMEZONE)

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("⏰ Scheduler Started with Database Persistence.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()

    def add_task(self, prompt: str, user_id: int, job_id: str, schedule_type: str = "cron", cron_str: str = None, run_at: str = None):
        """Dynamic Task Scheduler (Supports Cron & One-time Date)"""
        try:
            if schedule_type == "cron":
                # ထပ်ခါတလဲလဲ အလုပ်များ (ဥပမာ - နေ့တိုင်း ၈ နာရီ)
                mi, h, d, m, dow = cron_str.split()
                # 🔥 FIX: Config.TIMEZONE က အသင့်ဖြစ်ပြီးသားမို့ တိုက်ရိုက်ယူသုံးမယ်
                trigger = CronTrigger(minute=mi, hour=h, day=d, month=m, day_of_week=dow, timezone=Config.TIMEZONE)
                msg = f"Cron: {cron_str}"
            else:
                # တစ်ကြိမ်တည်း အလုပ်များ (ဥပမာ - နောက် ၄ မိနစ်နေရင်)
                run_time = datetime.strptime(run_at, "%Y-%m-%d %H:%M:%S")
                run_time = Config.TIMEZONE.localize(run_time) # မြန်မာအချိန်ကို ကပ်ပေးမယ်
                trigger = DateTrigger(run_date=run_time)
                msg = f"Time: {run_at}"

            self.scheduler.add_job(
                run_scheduled_task,
                trigger=trigger,
                args=[prompt, user_id],
                id=job_id,
                replace_existing=True
            )
            return f"✅ Scheduled: '{prompt}' at [{msg}] (ID: {job_id})"
        except Exception as e:
            logger.error(f"Schedule Error: {e}")
            return f"❌ Failed to schedule: {str(e)}"

    def remove_task(self, job_id: str):
        try:
            self.scheduler.remove_job(job_id)
            return f"🗑️ Task '{job_id}' removed."
        except Exception:
            return f"⚠️ Task ID '{job_id}' not found."

    def list_tasks(self):
        jobs = self.scheduler.get_jobs()
        if not jobs: return "No active schedules."
        return "\n".join([f"🆔 {job.id} | Next: {job.next_run_time}" for job in jobs])

jarvis_scheduler = JarvisScheduler()        