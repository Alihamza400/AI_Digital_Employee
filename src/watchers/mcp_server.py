"""
MCP Server - Model Context Protocol Server for AI Employee Actions
"""
import uuid
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, fields
from threading import Lock

from .gmail_watcher import GmailSender
from .whatsapp_watcher import WhatsAppSender
from .linkedin_watcher import LinkedInPoster
from .playwright_manager import manager as pw_manager

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions the AI Employee can perform"""
    SEND_EMAIL = "send_email"
    CREATE_DRAFT = "create_draft"
    SEND_WHATSAPP = "send_whatsapp"
    POST_LINKEDIN = "post_linkedin"
    CREATE_DRAFT_LINKEDIN = "create_draft_linkedin"
    SEND_SMS = "send_sms"
    MAKE_PAYMENT = "make_payment"
    CREATE_INVOICE = "create_invoice"
    SCHEDULE_MEETING = "schedule_meeting"
    CREATE_TASK = "create_task"
    WEB_SEARCH = "web_search"
    FILE_OPERATION = "file_operation"

    @classmethod
    def _missing_(cls, value):
        """Allow lookup by name or value case-insensitively"""
        value_lower = str(value).lower().replace(" ", "_")
        for member in cls:
            if member.value == value_lower:
                return member
        for member in cls:
            if member.name.lower() == value_lower:
                return member
        return None


class ActionStatus(Enum):
    """Status of an action request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ActionRequest:
    """Represents an action request from the AI"""
    id: str
    action_type: ActionType
    parameters: Dict[str, Any]
    status: ActionStatus
    created_at: str
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    requires_approval: bool = True
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'action_type': self.action_type.value,
            'parameters': self.parameters,
            'status': self.status.value,
            'created_at': self.created_at,
            'approved_at': self.approved_at,
            'executed_at': self.executed_at,
            'completed_at': self.completed_at,
            'result': self.result,
            'error': self.error,
            'requires_approval': self.requires_approval
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ActionRequest':
        data = data.copy()
        at = ActionType(data['action_type'])
        if at is None:
            at = ActionType.CREATE_TASK
        data['action_type'] = at
        data['status'] = ActionStatus(data['status']) if data.get('status') else ActionStatus.PENDING
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class ApprovalWorkflow:
    """Manages the human-in-the-loop approval workflow"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.pending_dir = self.vault_path / "Pending_Approval"
        self.approved_dir = self.vault_path / "Approved"
        self.rejected_dir = self.vault_path / "Rejected"
        
        # Create directories
        for dir_path in [self.pending_dir, self.approved_dir, self.rejected_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.pending_requests: Dict[str, dict] = {}
        self._lock = Lock()
        self._load_pending()
    
    def _load_pending(self):
        """Load pending requests from filesystem"""
        for file in self.pending_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    self.pending_requests[data['id']] = data
            except Exception as e:
                logger.error(f"Failed to load pending request {file}: {e}")
    
    def create_approval_request(self, action: 'ActionRequest') -> Path:
        """Create an approval request file"""
        request_data = action.to_dict()
        request_data['requires_approval'] = True
        
        filename = f"APPROVAL_{action.action_type.value}_{action.id}.json"
        filepath = self.pending_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(request_data, f, indent=2)
        
        with self._lock:
            self.pending_requests[action.id] = request_data
        
        logger.info(f"Created approval request: {filepath}")
        return filepath
    
    def approve(self, request_id: str) -> bool:
        """Approve a pending request"""
        with self._lock:
            if request_id not in self.pending_requests:
                return False
            
            request = self.pending_requests[request_id]
            request['status'] = 'approved'
            request['approved_at'] = datetime.now().isoformat()
            
            # Move to approved folder
            self._move_request(request_id, self.approved_dir)
            
            logger.info(f"Approved request: {request_id}")
            return True
    
    def reject(self, request_id: str, reason: str = "") -> bool:
        """Reject a pending request"""
        with self._lock:
            if request_id not in self.pending_requests:
                return False
            
            request = self.pending_requests[request_id]
            request['status'] = 'rejected'
            request['rejection_reason'] = reason
            request['rejected_at'] = datetime.now().isoformat()
            
            # Move to rejected folder
            self._move_request(request_id, self.rejected_dir)
            
            logger.info(f"Rejected request: {request_id} - {reason}")
            return True
    
    def _move_request(self, request_id: str, target_dir: Path):
        """Move request file to target directory"""
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Find and move the file
        for file in self.pending_dir.glob(f"*{request_id}*.json"):
            target = target_dir / file.name
            file.rename(target)
            break
    
    def get_pending(self) -> List[Dict]:
        """Get all pending requests"""
        with self._lock:
            return list(self.pending_requests.values())
    
    def get_request(self, request_id: str) -> Optional[Dict]:
        """Get a specific request"""
        with self._lock:
            return self.pending_requests.get(request_id)


class ActionExecutor:
    """Executes approved actions"""
    
    def __init__(self, mcp_server: 'MCPServer'):
        self.mcp = mcp_server
        self.handlers: Dict[ActionType, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default action handlers"""
        self.handlers = {
            ActionType.SEND_EMAIL: self._send_email,
            ActionType.CREATE_DRAFT: self._create_draft,
            ActionType.SEND_WHATSAPP: self._send_whatsapp,
            ActionType.POST_LINKEDIN: self._post_linkedin,
            ActionType.CREATE_DRAFT_LINKEDIN: self._create_draft_linkedin,
            ActionType.FILE_OPERATION: self._file_operation,
            ActionType.WEB_SEARCH: self._web_search,
            ActionType.CREATE_TASK: self._create_task,
            ActionType.CREATE_INVOICE: self._create_invoice,
            ActionType.SCHEDULE_MEETING: self._schedule_meeting,
        }
    
    def register_handler(self, action_type: ActionType, handler: Callable):
        """Register a custom action handler"""
        self.handlers[action_type] = handler
    
    def execute(self, action: ActionRequest) -> Dict:
        """Execute an approved action"""
        if action.status != ActionStatus.APPROVED:
            return {'success': False, 'error': f'Action not approved: {action.status.value}'}
        
        handler = self.handlers.get(action.action_type)
        if not handler:
            return {'success': False, 'error': f'No handler for action type: {action.action_type.value}'}
        
        try:
            action.status = ActionStatus.EXECUTING
            action.executed_at = datetime.now().isoformat()
            
            result = handler(action.parameters)
            
            action.status = ActionStatus.COMPLETED
            action.completed_at = datetime.now().isoformat()
            action.result = result
            
            logger.info(f"Executed action {action.id}: {action.action_type.value}")
            return {'success': True, 'result': result}
            
        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error = str(e)
            logger.error(f"Action {action.id} failed: {e}")
            return {'success': False, 'error': str(e)}
    
    # Default handlers
    def _send_email(self, params: Dict) -> Dict:
        return self.mcp.gmail_sender.send_email(
            params.get('to', ''),
            params.get('subject', ''),
            params.get('body', ''),
            params.get('attachments')
        )
    
    def _create_draft(self, params: Dict) -> Dict:
        return self.mcp.gmail_sender.create_draft(
            params.get('to', ''),
            params.get('subject', ''),
            params.get('body', '')
        )
    
    def _send_whatsapp(self, params: Dict) -> Dict:
        return self.mcp.whatsapp_sender.send_message(
            params.get('phone', ''),
            params.get('message', '')
        )
    
    def _post_linkedin(self, params: Dict) -> Dict:
        return self.mcp.linkedin_poster.post_content(
            params.get('content', ''),
            params.get('images')
        )
    
    def _create_draft_linkedin(self, params: Dict) -> Dict:
        return self.mcp.linkedin_poster.create_draft(params.get('content', ''))

    def _file_operation(self, params: Dict) -> Dict:
        operation = params.get('operation', '')
        path = Path(params.get('path', ''))
        content = params.get('content', '')

        if operation == 'create_file':
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            logger.info(f"Created file: {path}")
            return {'success': True, 'path': str(path)}

        if operation == 'delete_file':
            if path.exists():
                path.unlink()
                return {'success': True}
            return {'success': False, 'error': 'File not found'}

        return {'success': False, 'error': f'Unknown operation: {operation}'}

    def _web_search(self, params: Dict) -> Dict:
        query = params.get('query', '')
        if not query:
            return {'success': False, 'error': 'No query provided'}
        try:
            browser = pw_manager.create_context(headless=True, args=["--no-sandbox"])
            page = browser.pages[0]
            page.goto(f'https://html.duckduckgo.com/html/?q={query.replace(" ", "+")}')
            results = []
            for r in page.query_selector_all('.result__body')[:10]:
                title_el = r.query_selector('.result__title a')
                snippet_el = r.query_selector('.result__snippet')
                if title_el:
                    results.append({
                        'title': title_el.inner_text().strip(),
                        'href': title_el.get_attribute('href', ''),
                        'snippet': snippet_el.inner_text().strip() if snippet_el else ''
                    })
            browser.close()
            return {'success': True, 'results': results, 'count': len(results)}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {'success': False, 'error': str(e)}

    def _create_task(self, params: Dict) -> Dict:
        title = params.get('title', 'Untitled Task')
        description = params.get('description', '')
        priority = params.get('priority', 'medium')
        task_id = str(uuid.uuid4())[:8]
        path = self.mcp.vault_path / 'Plans' / f'TASK_{task_id}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"""---
id: {task_id}
title: {title}
priority: {priority}
status: pending
created: {datetime.now().isoformat()}
---

# {title}

**Priority:** {priority}
**Status:** Pending

## Description
{description}

## Actions
- [ ] Review task
- [ ] Execute
- [ ] Move to Completed/

---
*Created by AI Employee*
"""
        path.write_text(content)
        logger.info(f"Task created: {path}")
        return {'success': True, 'task_id': task_id, 'path': str(path)}

    def _create_invoice(self, params: Dict) -> Dict:
        try:
            from fpdf import FPDF
        except ImportError:
            return {'success': False, 'error': 'fpdf not installed'}
        invoice_id = params.get('invoice_id', str(uuid.uuid4())[:8])
        client = params.get('client', 'Client')
        items = params.get('items', [])
        if not items:
            return {'success': False, 'error': 'No invoice items provided'}
        total = sum(i.get('amount', 0) * i.get('quantity', 1) for i in items)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 20)
        pdf.cell(0, 12, 'INVOICE', align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f'Invoice #: {invoice_id}', new_x='LMARGIN', new_y='NEXT')
        pdf.cell(0, 6, f'Client: {client}', new_x='LMARGIN', new_y='NEXT')
        pdf.cell(0, 6, f'Date: {datetime.now().strftime("%Y-%m-%d")}', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(6)
        col_w = (190 - 40) / 4
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(col_w, 8, 'Item', border=1, fill=True)
        pdf.cell(20, 8, 'Qty', border=1, fill=True, align='C')
        pdf.cell(col_w, 8, 'Rate', border=1, fill=True, align='R')
        pdf.cell(col_w, 8, 'Amount', border=1, fill=True, align='R')
        pdf.ln()
        pdf.set_font('Helvetica', '', 10)
        for item in items:
            name = item.get('description', 'Item')
            qty = item.get('quantity', 1)
            rate = item.get('amount', 0)
            amt = rate * qty
            pdf.cell(col_w, 7, name[:30], border=1)
            pdf.cell(20, 7, str(qty), border=1, align='C')
            pdf.cell(col_w, 7, f'${rate:.2f}', border=1, align='R')
            pdf.cell(col_w, 7, f'${amt:.2f}', border=1, align='R')
            pdf.ln()
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(col_w * 2 + 20, 8, '', border=0)
        pdf.cell(col_w, 8, 'Total:', border=1, align='R')
        pdf.cell(col_w, 8, f'${total:.2f}', border=1, align='R')
        pdf.ln(12)
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(0, 5, 'Thank you for your business.', align='C')
        accounting_dir = self.mcp.vault_path / 'Accounting'
        accounting_dir.mkdir(parents=True, exist_ok=True)
        filename = f'Invoice_{invoice_id}.pdf'
        filepath = accounting_dir / filename
        pdf.output(str(filepath))
        logger.info(f"Invoice created: {filepath}")
        return {'success': True, 'path': str(filepath), 'total': total}

    def _schedule_meeting(self, params: Dict) -> Dict:
        summary = params.get('summary', 'Meeting')
        description = params.get('description', '')
        start_time = params.get('start_time', '')
        end_time = params.get('end_time', '')
        attendees = params.get('attendees', [])
        timezone = params.get('timezone', 'UTC')

        if not start_time or not end_time:
            return {'success': False, 'error': 'start_time and end_time are required (ISO format)'}

        if isinstance(attendees, str):
            attendees = [a.strip() for a in attendees.split(',') if a.strip()]

        try:
            creds_dict = self.mcp.config.get('calendar_token_json', {})
            if not creds_dict or not creds_dict.get('refresh_token'):
                return {'success': False, 'error': 'Calendar not configured — run auth_calendar.py'}
            creds = Credentials.from_authorized_user_info(creds_dict)
            if not creds.valid and creds.refresh_token:
                creds.refresh(Request())
            service = build('calendar', 'v3', credentials=creds)

            event = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': timezone},
                'end': {'dateTime': end_time, 'timeZone': timezone},
                'attendees': [{'email': e} for e in attendees],
                'reminders': {'useDefault': True},
            }

            created = service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"Meeting created: {created.get('htmlLink')}")
            return {
                'success': True,
                'event_id': created.get('id'),
                'link': created.get('htmlLink'),
                'summary': summary,
                'start': start_time,
                'end': end_time,
            }
        except Exception as e:
            logger.error(f"Calendar event creation failed: {e}")
            return {'success': False, 'error': str(e)}


class MCPServer:
    """Main MCP Server coordinating all AI Employee capabilities"""
    
    def __init__(self, vault_path: str, config: Dict[str, Any] = None):
        self.vault_path = Path(vault_path)
        self.config = config or {}
        
        # Initialize directories
        self._setup_directories()
        
        # Initialize components
        self.approval_workflow = ApprovalWorkflow(vault_path)
        self.action_executor = ActionExecutor(self)
        
        # Initialize service clients (lazy loaded)
        self._gmail_sender = None
        self._gmail_watcher = None
        self._whatsapp_sender = None
        self._whatsapp_watcher = None
        self._linkedin_poster = None
        self._linkedin_watcher = None
        self._linkedin_creator = None
        self._scheduler = None
        
        # Action history
        self.action_history: List[ActionRequest] = []
        self._load_history()
        
        logger.info("MCP Server initialized")
    
    def _setup_directories(self):
        """Setup required directory structure"""
        dirs = [
            'Inbox', 'Needs_Action', 'In_Progress', 'Done', 'Plans',
            'Pending_Approval', 'Approved', 'Rejected', 'Logs', 
            'Briefings', 'Audits', 'Accounting', 'LinkedIn_Templates'
        ]
        for dir_name in dirs:
            (self.vault_path / dir_name).mkdir(parents=True, exist_ok=True)
    
    def _load_history(self):
        """Load action history from logs"""
        log_dir = self.vault_path / 'Logs'
        if log_dir.exists():
            for log_file in log_dir.glob('*.json'):
                try:
                    with open(log_file) as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                if 'action_type' in item:
                                    self.action_history.append(ActionRequest.from_dict(item))
                except Exception as e:
                    logger.error(f"Failed to load history from {log_file}: {e}")
    
    def _save_action(self, action: ActionRequest):
        """Save action to history log"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.vault_path / 'Logs' / f'{today}.json'
        
        logs = []
        if log_file.exists():
            try:
                with open(log_file) as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(action.to_dict())
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    # Properties for lazy loading
    @property
    def gmail_sender(self):
        if self._gmail_sender is None:
            client_config = self.config.get('gmail_client_config', {})
            token_data = self.config.get('gmail_token_json', {})
            self._gmail_sender = GmailSender(client_config, token_data)
        return self._gmail_sender
    
    @property
    def gmail_watcher(self):
        if self._gmail_watcher is None:
            client_config = self.config.get('gmail_client_config', {})
            token_data = self.config.get('gmail_token_json', {})
            self._gmail_watcher = GmailWatcher(
                self.vault_path, client_config, token_data
            )
        return self._gmail_watcher
    
    @property
    def whatsapp_sender(self):
        if self._whatsapp_sender is None:
            session_path = self.config.get('whatsapp_session', 'whatsapp_session')
            self._whatsapp_sender = WhatsAppSender(session_path)
        return self._whatsapp_sender
    
    @property
    def whatsapp_watcher(self):
        if self._whatsapp_watcher is None:
            session_path = self.config.get('whatsapp_session', 'whatsapp_session')
            self._whatsapp_watcher = WhatsAppWatcher(self.vault_path, session_path)
        return self._whatsapp_watcher
    
    @property
    def linkedin_poster(self):
        if self._linkedin_poster is None:
            session_path = self.config.get('linkedin_session', 'linkedin_session')
            self._linkedin_poster = LinkedInPoster(session_path)
        return self._linkedin_poster
    
    @property
    def linkedin_watcher(self):
        if self._linkedin_watcher is None:
            session_path = self.config.get('linkedin_session', 'linkedin_session')
            self._linkedin_watcher = LinkedInWatcher(self.vault_path, session_path)
        return self._linkedin_watcher
    
    @property
    def linkedin_creator(self):
        if self._linkedin_creator is None:
            self._linkedin_creator = LinkedInPostCreator(self.vault_path)
        return self._linkedin_creator
    
    @property
    def scheduler(self):
        if self._scheduler is None:
            self._scheduler = CronScheduler(self.vault_path)
        return self._scheduler
    
    def create_action(self, action_type: ActionType, parameters: Dict, 
                      requires_approval: bool = True) -> ActionRequest:
        """Create a new action request"""
        action = ActionRequest(
            id=str(uuid.uuid4())[:8],
            action_type=action_type,
            parameters=parameters,
            status=ActionStatus.PENDING if requires_approval else ActionStatus.APPROVED,
            created_at=datetime.now().isoformat(),
            requires_approval=requires_approval
        )
        
        if requires_approval:
            self.approval_workflow.create_approval_request(action)
        else:
            # Auto-approve
            action.status = ActionStatus.APPROVED
            action.approved_at = datetime.now().isoformat()
        
        self.action_history.append(action)
        self._save_action(action)
        
        logger.info(f"Created action: {action.id} ({action_type.value})")
        return action
    
    def execute_action(self, action_id: str) -> Dict:
        """Execute an approved action"""
        action = next((a for a in self.action_history if a.id == action_id), None)
        if not action:
            return {'success': False, 'error': 'Action not found'}
        
        result = self.action_executor.execute(action)
        self._save_action(action)
        return result
    
    def approve_action(self, action_id: str) -> bool:
        """Approve a pending action"""
        action = next((a for a in self.action_history if a.id == action_id), None)
        if not action:
            return False
        
        approved = self.approval_workflow.approve(action_id)
        if approved:
            action.status = ActionStatus.APPROVED
            action.approved_at = datetime.now().isoformat()
            self._save_action(action)
        return approved
    
    def reject_action(self, action_id: str, reason: str = "") -> bool:
        """Reject a pending action"""
        rejected = self.approval_workflow.reject(action_id, reason)
        if rejected:
            action = next((a for a in self.action_history if a.id == action_id), None)
            if action:
                action.status = ActionStatus.REJECTED
                action.error = reason
                self._save_action(action)
        return rejected
    
    def get_pending_actions(self) -> List[ActionRequest]:
        """Get all pending actions"""
        return [a for a in self.action_history if a.status == ActionStatus.PENDING]
    
    def get_action_history(self) -> List[ActionRequest]:
        """Get full action history"""
        return self.action_history
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get pending approvals from workflow"""
        return self.approval_workflow.get_pending()
    
    # High-level convenience methods
    def send_email(self, to: str, subject: str, body: str, 
                   attachments: List[str] = None, requires_approval: bool = True) -> ActionRequest:
        """Create email send action"""
        return self.create_action(
            ActionType.SEND_EMAIL,
            {'to': to, 'subject': subject, 'body': body, 'attachments': attachments},
            requires_approval
        )
    
    def create_email_draft(self, to: str, subject: str, body: str) -> ActionRequest:
        """Create email draft action (no approval needed for drafts)"""
        return self.create_action(
            ActionType.CREATE_DRAFT,
            {'to': to, 'subject': subject, 'body': body},
            requires_approval=False
        )
    
    def send_whatsapp(self, phone: str, message: str, 
                      requires_approval: bool = True) -> ActionRequest:
        """Create WhatsApp send action"""
        return self.create_action(
            ActionType.SEND_WHATSAPP,
            {'phone': phone, 'message': message},
            requires_approval
        )
    
    def post_linkedin(self, content: str, images: List[str] = None,
                      requires_approval: bool = True) -> ActionRequest:
        """Create LinkedIn post action"""
        return self.create_action(
            ActionType.POST_LINKEDIN,
            {'content': content, 'images': images or []},
            requires_approval
        )
    
    def create_linkedin_draft(self, content: str) -> ActionRequest:
        """Create LinkedIn draft (no approval needed)"""
        return self.create_action(
            ActionType.CREATE_DRAFT_LINKEDIN,
            {'content': content},
            requires_approval=False
        )
    
    def schedule_meeting(self, summary: str, start_time: str, end_time: str,
                          description: str = "", attendees: List[str] = None,
                          timezone: str = "UTC", requires_approval: bool = True) -> ActionRequest:
        return self.create_action(
            ActionType.SCHEDULE_MEETING,
            {
                'summary': summary, 'start_time': start_time, 'end_time': end_time,
                'description': description, 'attendees': attendees or [],
                'timezone': timezone,
            },
            requires_approval
        )

    def create_linkedin_post(self, template: str, **kwargs) -> str:
        """Create a LinkedIn post from template"""
        return self.linkedin_creator.create_post(template, **kwargs)
    
    def list_linkedin_templates(self) -> List[str]:
        """List available LinkedIn templates"""
        return self.linkedin_creator.list_templates()
    
    def get_status(self) -> Dict:
        """Get server status"""
        return {
            'vault_path': str(self.vault_path),
            'actions_pending': len(self.get_pending_actions()),
            'actions_total': len(self.action_history),
            'gmail_configured': self._gmail_sender is not None,
            'whatsapp_configured': self._whatsapp_sender is not None,
            'linkedin_configured': self._linkedin_poster is not None,
            'scheduler_running': self._scheduler is not None,
        }


# Convenience function to create and start the server
def create_mcp_server(vault_path: str, config: Dict = None) -> MCPServer:
    """Create and initialize MCP Server"""
    server = MCPServer(vault_path, config)
    return server