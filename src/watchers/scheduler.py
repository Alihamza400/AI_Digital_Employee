"""
Cron Scheduler and Automated Tasks
Handles scheduled tasks like daily briefings, subscription audits, etc.
"""
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime, timedelta
from croniter import croniter
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers import SchedulerNotRunningError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)


class ScheduledTask:
    """Represents a scheduled task"""
    
    def __init__(self, task_id: str, name: str, func: callable, 
                 trigger: Any, args: tuple = (), kwargs: dict = None):
        self.task_id = task_id
        self.name = name
        self.func = func
        self.trigger = trigger
        self.args = args
        self.kwargs = kwargs or {}
        self.enabled = True
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.last_error: Optional[str] = None


class CronScheduler:
    """Manages scheduled tasks using APScheduler"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.logs_path = self.vault_path / "Logs"
        self.logs_path.mkdir(parents=True, exist_ok=True)
        
        self.scheduler = BackgroundScheduler()
        self.tasks: Dict[str, ScheduledTask] = {}
        self._setup_default_jobs()
    
    def add_cron_job(self, task_id: str, name: str, func: callable, 
                     cron_expression: str, args: tuple = (), kwargs: dict = None) -> str:
        """Add a cron job"""
        trigger = CronTrigger.from_crontab(cron_expression)
        return self._add_job(task_id, name, func, trigger, args, kwargs)
    
    def add_interval_job(self, task_id: str, name: str, func: callable,
                         interval_seconds: int, args: tuple = (), kwargs: dict = None) -> str:
        """Add an interval job"""
        trigger = IntervalTrigger(seconds=interval_seconds)
        return self._add_job(task_id, name, func, trigger, args, kwargs)
    
    def add_one_time_job(self, task_id: str, name: str, func: callable,
                         run_at: datetime, args: tuple = (), kwargs: dict = None) -> str:
        """Add a one-time job"""
        trigger = DateTrigger(run_date=run_at)
        return self._add_job(task_id, name, func, trigger, args, kwargs)
    
    def _add_job(self, task_id: str, name: str, func: callable, 
                 trigger: Any, args: tuple, kwargs: dict) -> str:
        """Add a job to the scheduler"""
        if task_id in self.tasks:
            self.remove_job(task_id)
        
        job = self.scheduler.add_job(func, trigger, args=args, kwargs=kwargs, id=task_id)
        
        task = ScheduledTask(task_id, name, func, trigger, args, kwargs)
        task.next_run = job.next_run_time if hasattr(job, 'next_run_time') else None
        
        self.tasks[task_id] = task
        logger.info(f"Scheduled job '{name}' ({task_id}) with trigger {trigger}")
        return task_id
    
    def remove_job(self, task_id: str):
        """Remove a scheduled job"""
        if task_id in self.tasks:
            self.scheduler.remove_job(task_id)
            del self.tasks[task_id]
            logger.info(f"Removed job: {task_id}")
    
    def pause_job(self, task_id: str):
        """Pause a scheduled job"""
        if task_id in self.tasks:
            self.scheduler.pause_job(task_id)
            self.tasks[task_id].enabled = False
    
    def resume_job(self, task_id: str):
        """Resume a paused job"""
        if task_id in self.tasks:
            self.scheduler.resume_job(task_id)
            self.tasks[task_id].enabled = True
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Cron scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        try:
            self.scheduler.shutdown()
        except SchedulerNotRunningError:
            pass
        logger.info("Cron scheduler stopped")

    def list_jobs(self) -> Dict[str, Any]:
        """Alias for get_job_status"""
        return {j['task_id']: j for j in self.get_job_status()}
    
    def get_job_status(self) -> List[Dict]:
        """Get status of all scheduled jobs"""
        status = []
        for task_id, task in self.tasks.items():
            job = self.scheduler.get_job(task_id)
            nrt = getattr(job, 'next_run_time', None) if job else None
            status.append({
                'task_id': task_id,
                'name': task.name,
                'enabled': task.enabled,
                'next_run': nrt.isoformat() if nrt else None,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'run_count': task.run_count,
                'last_error': task.last_error
            })
        return status
    
    def _setup_default_jobs(self):
        """Setup default scheduled jobs"""
        # These are placeholders - actual functions would be implemented
        pass
    
    def _job_wrapper(self, task_id: str, func: callable, args: tuple, kwargs: dict):
        """Wrapper to track job execution"""
        task = self.tasks.get(task_id)
        if not task or not task.enabled:
            return
        
        task.last_run = datetime.now()
        task.run_count += 1
        
        try:
            func(*args, **kwargs)
            task.last_error = None
            logger.info(f"Job {task.name} ({task_id}) completed successfully")
        except Exception as e:
            task.last_error = str(e)
            logger.error(f"Job {task.name} ({task_id}) failed: {e}")


class AutomatedTasks:
    """Collection of automated business tasks"""
    
    def __init__(self, vault_path: str, mcp_server):
        self.vault_path = Path(vault_path)
        self.mcp = mcp_server
        self.vault_path = Path(vault_path)
    
    def daily_briefing(self):
        """Generate daily business briefing"""
        logger.info("Generating daily briefing...")
        
        briefing_dir = self.vault_path / "Briefings"
        briefing_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        briefing_file = briefing_dir / f"{today}_Daily_Briefing.md"
        
        # This would integrate with actual business data
        content = f"""---
generated: {datetime.now().isoformat()}
period: {today}
---

# Daily Business Briefing - {today}

## Executive Summary
Daily briefing generated automatically.

## Revenue
- **Today**: $0
- **MTD**: $0
- **Target**: $5,000/month

## Tasks
- [ ] Review pending approvals
- [ ] Process new leads
- [ ] Follow up on pending invoices

## Alerts
- No critical alerts

---
*Generated by AI Employee*
"""
        
        briefing_file.write_text(content)
        logger.info(f"Daily briefing generated: {briefing_file}")
    
    def weekly_audit(self):
        """Weekly business audit"""
        logger.info("Running weekly audit...")
        
        audit_dir = self.vault_path / "Audits"
        audit_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        audit_file = audit_dir / f"{today}_Weekly_Audit.md"
        
        content = f"""---
generated: {datetime.now().isoformat()}
period: Weekly
---

# Weekly Business Audit - {today}

## Revenue Analysis
- **This Week**: $0
- **Last Week**: $0
- **Trend**: Stable

## Completed Tasks
- [ ] Hackathon0 Bronze Tier Foundation
- [ ] FileSystemWatcher implementation
- [ ] Obsidian vault setup

## Pending Actions
- [ ] Review pending approvals
- [ ] Follow up on leads

## Subscription Audit
*No subscriptions to review*

## Proactive Suggestions
1. Set up Gmail watcher for email automation
2. Implement LinkedIn posting schedule
3. Create WhatsApp template responses

---
*Generated by AI Employee*
"""
        
        audit_file.write_text(content)
        logger.info(f"Weekly audit generated: {audit_file}")
    
    def subscription_audit(self):
        """Audit subscriptions for cost optimization"""
        logger.info("Running subscription audit...")
        
        # This would integrate with actual subscription data
        audit_dir = self.vault_path / "Audits"
        audit_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        audit_file = audit_dir / f"{today}_Subscription_Audit.md"
        
        content = f"""---
generated: {datetime.now().isoformat()}
type: subscription_audit
---

# Subscription Audit - {datetime.now().strftime('%Y-%m-%d')}

## Active Subscriptions
| Service | Cost/Month | Last Used | Status |
|---------|------------|-----------|--------|
| *None configured* | | | |

## Alerts
- No subscription alerts

## Recommendations
- Add subscription tracking to Business_Goals.md
- Set up monthly review

---
*Generated by AI Employee*
"""
        
        audit_file.write_text(content)
        logger.info(f"Subscription audit generated: {audit_file}")
    
    def process_pending_approvals(self):
        """Process pending approval files"""
        try:
            pending_dir = self.vault_path / "Pending_Approval"
            if not pending_dir.exists():
                return
            
            for file in pending_dir.glob("*.json"):
                try:
                    with open(file) as f:
                        data = json.load(f)
                    request_id = data.get('id')
                    if request_id and self.mcp:
                        self.mcp.approval_workflow.pending_requests[request_id] = data
                        logger.info(f"Loaded pending approval: {request_id}")
                except Exception as e:
                    logger.error(f"Failed to process approval file {file}: {e}")
        except Exception as e:
            logger.error(f"Error in process_pending_approvals: {e}")
    
    def cleanup_old_files(self, days: int = 30):
        """Clean up old processed files"""
        logger.info(f"Cleaning up files older than {days} days...")
        
        folders = ['Done', 'Approved', 'Rejected']
        cutoff = datetime.now() - timedelta(days=days)
        
        for folder in folders:
            folder_path = self.vault_path / folder
            if folder_path.exists():
                for file in folder_path.iterdir():
                    if file.is_file():
                        mtime = datetime.fromtimestamp(file.stat().st_mtime)
                        if mtime < cutoff:
                            file.unlink()
                            logger.info(f"Removed old file: {file}")
    
    def update_dashboard(self):
        """Update Dashboard.md with live vault state"""
        logger.info("Updating Dashboard.md...")

        now = datetime.now()
        today = now.strftime('%Y-%m-%d')

        # Count files in each vault folder
        def count_files(subdir: str) -> int:
            d = self.vault_path / subdir
            return len([f for f in d.iterdir() if f.is_file()]) if d.exists() else 0

        needs_action = count_files('Needs_Action')
        pending_approval = count_files('Pending_Approval')
        approved = count_files('Approved')
        rejected = count_files('Rejected')
        plans = count_files('Plans')
        inbox = count_files('Inbox')
        completed = count_files('Completed')

        # Count today's actions from logs
        today_log = self.vault_path / 'Logs' / f'{today}.json'
        actions_today = 0
        errors_today = 0
        recent_actions = []
        if today_log.exists():
            try:
                entries = json.loads(today_log.read_text())
                actions_today = len(entries)
                for e in entries[-5:]:
                    at = e.get('action_type', '?')
                    st = e.get('status', '?')
                    ts = e.get('created_at', '?')[:19]
                    recent_actions.append((ts, at, st))
                    if st in ('failed', 'error'):
                        errors_today += 1
            except Exception:
                pass

        # Status indicators
        pending_status = "⚠️" if pending_approval > 0 else "✅"
        needs_status = "⚠️" if needs_action > 0 else "✅"

        content = f"""# Dashboard - Personal AI Employee Real-Time Status

*Last Updated: {now.strftime('%Y-%m-%d %H:%M')}*

---

## System Status
- **AI Employee**: ✅ ONLINE
- **FileSystemWatcher**: ✅ RUNNING
- **Scheduler**: ✅ RUNNING (6 jobs)
- **Last Action**: {recent_actions[-1][0] if recent_actions else 'N/A'}

---

## Real-Time Metrics
| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Actions Today | {actions_today} | 10+ | {"🔄" if actions_today < 10 else "✅"} |
| Needs Action | {needs_action} | < 5 | {needs_status} |
| Pending Approvals | {pending_approval} | 0 | {pending_status} |
| Errors Today | {errors_today} | 0 | {"❌" if errors_today > 0 else "✅"} |

---

## Folder Status
| Folder | Files | Status |
|--------|-------|--------|
| Inbox | {inbox} | {"🟡 Has files" if inbox > 0 else "🟢 Empty"} |
| Needs_Action | {needs_action} | {"🟡 Waiting" if needs_action > 0 else "🟢 Empty"} |
| Plans | {plans} | {"🟡 Has plans" if plans > 0 else "🟢 Empty"} |
| Pending_Approval | {pending_approval} | {"🔴 Needs review" if pending_approval > 0 else "🟢 Empty"} |
| Approved | {approved} | {"🟡 Awaiting execution" if approved > 0 else "🟢 Empty"} |
| Rejected | {rejected} | {"🟡 Has rejections" if rejected > 0 else "🟢 Empty"} |
| Completed | {completed} | {"🟢 Has history" if completed > 0 else "🟢 Empty"} |

---

## Recent Activity
| Time | Action | Status |
|------|--------|--------|
{chr(10).join(f"| {ts} | {at} | {st} |" for ts, at, st in recent_actions) if recent_actions else "| — | — | — |"}

---

## Alerts
{pending_approval > 0 and f"- 🔴 {pending_approval} approval(s) pending review" or "- ✅ No pending approvals"}
{errors_today > 0 and f"- ❌ {errors_today} error(s) today" or "- ✅ No errors detected"}
{needs_action > 0 and f"- 🟡 {needs_action} action(s) waiting in Needs_Action/" or "- ✅ No queued actions"}

---

*Automatically updated by Scheduler — last refresh: {now.strftime('%Y-%m-%d %H:%M')}*
"""
        (self.vault_path / 'Dashboard.md').write_text(content)
        logger.info("Dashboard.md updated")

    def generate_ceo_briefing(self):
        """Generate CEO briefing"""
        briefing_dir = self.vault_path / "Briefings"
        briefing_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime('%Y-%m-%d')
        briefing_file = briefing_dir / f"{today}_CEO_Briefing.md"
        
        content = f"""---
generated: {datetime.now().isoformat()}
type: ceo_briefing
---

# CEO Briefing - {today}

## Executive Summary
Weekly business performance review.

## Key Metrics
- **Revenue This Week**: $0
- **Revenue MTD**: $0
- **Target**: $5,000/month
- **Progress**: 0%

## Completed This Week
- ✅ Hackathon0 Bronze Tier Foundation
- ✅ FileSystemWatcher implementation
- ✅ Obsidian vault structure
- ✅ Dashboard, Handbook, Business Goals

## Pending Items
- [ ] Gmail Watcher implementation
- [ ] WhatsApp Watcher implementation
- [ ] LinkedIn Post automation
- [ ] MCP Server integration

## Strategic Decisions Needed
1. Prioritize Silver Tier features
2. Define approval workflows
3. Set up monitoring alerts

---
*Generated by AI Employee*
"""
        
        briefing_file.write_text(content)
        logger.info(f"CEO briefing generated: {briefing_file}")


class ScheduledTaskManager:
    """High-level task manager for common business schedules"""
    
    def __init__(self, vault_path: str, mcp_server):
        self.scheduler = CronScheduler(vault_path)
        self.tasks = AutomatedTasks(vault_path, mcp_server)
        self._setup_default_schedule()
    
    def _setup_default_schedule(self):
        """Setup default business schedule"""
        
        # Daily briefing at 8 AM
        self.scheduler.add_cron_job(
            'daily_briefing',
            'Daily Morning Briefing',
            self.tasks.daily_briefing,
            '0 8 * * *'  # 8 AM daily
        )
        
        # Weekly audit on Monday 9 AM
        self.scheduler.add_cron_job(
            'weekly_audit',
            'Weekly Business Audit',
            self.tasks.weekly_audit,
            '0 9 * * 1'  # Monday 9 AM
        )
        
        # Monthly subscription audit on 1st at 10 AM
        self.scheduler.add_cron_job(
            'subscription_audit',
            'Monthly Subscription Audit',
            self.tasks.subscription_audit,
            '0 10 1 * *'  # 1st of month 10 AM
        )
        
        # CEO briefing on Monday 7 AM
        self.scheduler.add_cron_job(
            'ceo_briefing',
            'CEO Weekly Briefing',
            self.tasks.generate_ceo_briefing,
            '0 7 * * 1'  # Monday 7 AM
        )
        
        # Cleanup old files monthly
        self.scheduler.add_cron_job(
            'cleanup_files',
            'Monthly File Cleanup',
            lambda: self.tasks.cleanup_old_files(30),
            '0 2 1 * *'  # 1st of month 2 AM
        )
        
        # Check approvals every 5 minutes
        self.scheduler.add_interval_job(
            'check_approvals',
            'Check Pending Approvals',
            self._check_approvals,
            300  # 5 minutes
        )

        # Update dashboard every 5 minutes
        self.scheduler.add_interval_job(
            'update_dashboard',
            'Update Dashboard.md',
            self._update_dashboard,
            300  # 5 minutes
        )
    
    def _check_approvals(self):
        """Check for approval file changes"""
        try:
            self.tasks.process_pending_approvals()
        except Exception as e:
            logger.error(f"Error checking approvals: {e}")

    def _update_dashboard(self):
        """Refresh Dashboard.md with live state"""
        try:
            self.tasks.update_dashboard()
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
    
    def start(self):
        self.scheduler.start()
        self._update_dashboard()
    
    def stop(self):
        self.scheduler.shutdown()
    
    def get_status(self) -> List[Dict]:
        return self.scheduler.get_job_status()
    
    def add_custom_job(self, task_id: str, name: str, func: callable, 
                       cron_expression: str = None, interval_seconds: int = None,
                       run_at: datetime = None) -> str:
        """Add a custom scheduled job"""
        if cron_expression:
            return self.scheduler.add_cron_job(task_id, name, func, cron_expression)
        elif interval_seconds:
            return self.scheduler.add_interval_job(task_id, name, func, interval_seconds)
        elif run_at:
            return self.scheduler.add_one_time_job(task_id, name, func, run_at)
        else:
            raise ValueError("Must provide cron_expression, interval_seconds, or run_at")
    
    def remove_job(self, task_id: str):
        self.scheduler.remove_job(task_id)
    
    def get_status(self) -> List[Dict]:
        return self.scheduler.get_job_status()