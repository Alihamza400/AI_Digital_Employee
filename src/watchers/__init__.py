"""
Watchers Package - All watchers and related components
"""
from .base_watcher import BaseWatcher
from .filesystem_watcher import FileSystemWatcher, DropFolderHandler
from .gmail_watcher import GmailWatcher, GmailSender
from .whatsapp_watcher import WhatsAppWatcher, WhatsAppSender
from .linkedin_watcher import LinkedInWatcher, LinkedInPoster, LinkedInPostCreator
from .ai_reasoning_watcher import AIReasoningWatcher, NeedsActionHandler
from .approval_watcher import ApprovalWatcher, ApprovalHandler, PendingHandler
from .approval_server import ApprovalServer, start_approval_server
from .playwright_manager import PlaywrightManager, manager as playwright_manager
from .mcp_server import (
    MCPServer, 
    ApprovalWorkflow, 
    ActionType, 
    ActionStatus, 
    ActionRequest
)
from .scheduler import (
    CronScheduler, 
    ScheduledTaskManager, 
    AutomatedTasks
)

__all__ = [
    # Base
    "BaseWatcher",
    # File System
    "FileSystemWatcher",
    "DropFolderHandler",
    # Gmail
    "GmailWatcher",
    "GmailSender",
    # WhatsApp
    "WhatsAppWatcher",
    "WhatsAppSender",
    # LinkedIn
    "LinkedInWatcher",
    "LinkedInPoster",
    "LinkedInPostCreator",
    # AI Reasoning
    "AIReasoningWatcher",
    "NeedsActionHandler",
    # Approval
    "ApprovalWatcher",
    "ApprovalHandler",
    "PendingHandler",
    "ApprovalServer",
    "start_approval_server",
    # Playwright
    "PlaywrightManager",
    "playwright_manager",
    # MCP Server
    "MCPServer",
    "ApprovalWorkflow",
    "ActionType",
    "ActionStatus",
    "ActionRequest",
    # Scheduler
    "CronScheduler",
    "ScheduledTaskManager",
    "AutomatedTasks",
]