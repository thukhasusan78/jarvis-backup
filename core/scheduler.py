from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import logging
import os
from tasks.executor import run_scheduled_task  # ခုနကရေးတဲ့ကောင်

logger = logging.getLogger("JARVIS_SCHEDULER")

class JarvisScheduler:
    def __init__(self):
        # Jobs တွေကို Memory/jarvis.db ထဲမှာ သိမ်းမယ် (Restart ချလည်း မပျောက်တော့ဘူး)
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///memory/jarvis_schedules.db')
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("⏰ Scheduler Started with Database Persistence.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()

    def add_task(self, prompt: str, user_id: int, cron_str: str, job_id: str):
        """
        Dynamic Job Adding Logic
        cron_str format: "minute hour day month day_of_week"
        Example: "30 8 * * *" -> နေ့တိုင်း ၈ နာရီခွဲ
        """
        try:
            # Cron string ကို ဖြိုခွဲမယ်
            mi, h, d, m, dow = cron_str.split()
            
            self.scheduler.add_job(
                run_scheduled_task,
                trigger=CronTrigger(minute=mi, hour=h, day=d, month=m, day_of_week=dow),
                args=[prompt, user_id], # Executor ဆီပို့မယ့် စာသား
                id=job_id,
                replace_existing=True
            )
            return f"✅ Scheduled: '{prompt}' at '{cron_str}' (ID: {job_id})"
        except Exception as e:
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