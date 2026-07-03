from fpdf import FPDF
import os

class HackathonPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 8, 'Personal AI Employee - Hackathon 0 (Bronze Tier)', align='R')
            self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    def section_title(self, title):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(25, 60, 120)
        self.cell(0, 10, title)
        self.ln(4)
        self.set_draw_color(25, 60, 120)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(6)

    def sub_section(self, title):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(50, 90, 150)
        self.cell(0, 8, title)
        self.ln(6)

    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet_point(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin)
        self.cell(5, 5.5, '-')
        self.set_x(self.l_margin + 5)
        self.multi_cell(self.w - self.r_margin - (self.l_margin + 5), 5.5, text)

    def bold_bullet(self, bold_part, rest):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(40, 40, 40)
        self.set_x(self.l_margin)
        self.cell(5, 5.5, '-')
        self.set_x(self.l_margin + 5)
        bold_w = self.get_string_width(bold_part) + 1
        self.cell(bold_w, 5.5, bold_part)
        self.set_font('Helvetica', '', 10)
        self.multi_cell(self.w - self.r_margin - (self.l_margin + 5 + bold_w), 5.5, rest)


pdf = HackathonPDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)

# ---- COVER PAGE ----
pdf.add_page()
pdf.ln(40)
pdf.set_font('Helvetica', 'B', 28)
pdf.set_text_color(25, 60, 120)
pdf.cell(0, 14, 'Personal AI Employee', align='C')
pdf.ln(14)
pdf.set_font('Helvetica', '', 20)
pdf.set_text_color(60, 100, 160)
pdf.cell(0, 12, 'Hackathon 0 - Bronze Tier', align='C')
pdf.ln(12)
pdf.set_font('Helvetica', '', 14)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 10, 'Building Autonomous AI Employees in 2026', align='C')
pdf.ln(20)

pdf.set_draw_color(25, 60, 120)
pdf.set_line_width(0.8)
pdf.line(60, pdf.get_y(), 150, pdf.get_y())
pdf.ln(20)

pdf.set_font('Helvetica', '', 11)
pdf.set_text_color(80, 80, 80)
pdf.cell(0, 7, 'An AI-Powered Virtual Employee System with:', align='C')
pdf.ln(7)
pdf.cell(0, 7, 'File Monitoring  |  Email Integration  |  Approval Workflows', align='C')
pdf.ln(7)
pdf.cell(0, 7, 'WhatsApp Automation  |  LinkedIn Management  |  Scheduled Tasks', align='C')
pdf.ln(30)

pdf.set_font('Helvetica', 'I', 10)
pdf.set_text_color(130, 130, 130)
pdf.cell(0, 7, 'Hackathon Project 2026', align='C')
pdf.ln(7)
pdf.cell(0, 7, 'Fully Functional Bronze Tier Foundation', align='C')

# ---- TABLE OF CONTENTS ----
pdf.add_page()
pdf.section_title('Table of Contents')
pdf.ln(4)

toc_items = [
    '1.  Executive Summary',
    '2.  Project Overview',
    '3.  Core Architecture',
    '4.  Key Features & Components',
    '5.  Technology Stack',
    '6.  System Workflow',
    '7.  Vault & Memory Structure',
    '8.  Security & Approval System',
    '9.  Use Cases',
    '10. Roadmap & Future Tiers',
    '11. What is Included',
    '12. Setup & Deployment',
]
for item in toc_items:
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(50, 90, 150)
    pdf.cell(0, 8, item)
    pdf.ln(8)

# ---- 1. EXECUTIVE SUMMARY ----
pdf.add_page()
pdf.section_title('1. Executive Summary')
pdf.body_text(
    'Hackathon 0 introduces the Bronze Tier of the Personal AI Employee - an autonomous AI-powered virtual '
    'employee system designed for modern business operations. This foundational tier implements a complete '
    'Perception -> Reasoning -> Action pipeline, enabling businesses to automate routine tasks while maintaining '
    'full human oversight through an integrated approval workflow.'
)
pdf.body_text(
    'The system uses an Obsidian vault as its long-term memory layer, provides modular watchers for different '
    'input channels (file system, email, messaging, social media), and a Model Context Protocol (MCP) server '
    'for centralized action coordination. It is designed from Day 1 to be extensible to higher tiers (Silver, Gold).'
)
pdf.body_text(
    'Key capabilities include: automated file processing, Gmail integration, WhatsApp Web automation, LinkedIn '
    'management, scheduled briefings and audits, human-in-the-loop approval workflows, and full action audit trails.'
)

# ---- 2. PROJECT OVERVIEW ----
pdf.add_page()
pdf.section_title('2. Project Overview')
pdf.body_text(
    'The Personal AI Employee is a multi-tier autonomous assistant that handles business operations without '
    'constant human supervision. Think of it as hiring a full-time employee who works 24/7, never sleeps, '
    'and handles thousands of routine tasks while escalating only the decisions that truly need your attention.'
)
pdf.body_text(
    'The system follows the "Obsidian Vault as Memory" pattern: the AI reads its instructions, goals, and '
    'context from markdown files in the vault, writes plans and status updates back to the vault, and '
    'maintains a complete audit trail of all actions taken. This makes the system transparent, debuggable, '
    'and auditable at every step.'
)
pdf.body_text(
    'Tier Structure: Platinum (Enterprise) < Gold < Silver < Bronze (Foundation)',
)

# ---- 3. CORE ARCHITECTURE ----
pdf.add_page()
pdf.section_title('3. Core Architecture')
pdf.body_text(
    'The system follows a clean three-layer architecture:'
)
pdf.ln(2)
pdf.sub_section('Perception Layer (Watchers)')
pdf.body_text(
    'Four modular watchers continuously monitor different input channels. Each watcher runs in its own '
    'background thread and writes detected events as structured action files into the vault. Watchers '
    'include FileSystem, Gmail, WhatsApp, and LinkedIn monitors.'
)
pdf.sub_section('Reasoning Layer (MCP Server)')
pdf.body_text(
    'The Model Context Protocol server serves as the central brain. It maintains the approval workflow, '
    'executes authorized actions, manages action history, coordinates between watchers, and provides '
    'lazy-loaded service clients for Gmail, WhatsApp, and LinkedIn.'
)
pdf.sub_section('Memory Layer (Obsidian Vault)')
pdf.body_text(
    'An Obsidian vault acts as the AI\'s long-term memory. It stores instructions (Company Handbook), '
    'goals (Business Goals), incoming tasks (Inbox/Needs_Action), pending approvals (Pending_Approval), '
    'completed actions (Done), plans (Plans), logs (Logs), briefings (Briefings), and audits (Audits).'
)

# ---- 4. KEY FEATURES ----
pdf.add_page()
pdf.section_title('4. Key Features & Components')
pdf.ln(2)

features = [
    ('FileSystemWatcher', 'Monitors a drop folder using watchdog file events. Automatically copies dropped '
     'files (invoices, documents, contracts) to Needs_Action with metadata creation and removes originals.'),
    ('GmailWatcher + GmailSender', 'Monitors Gmail inbox for important unread emails via Google API. '
     'Creates action items for flagged/important emails. Can send replies and create drafts.'),
    ('WhatsAppWatcher + WhatsAppSender', 'Uses Playwright browser automation to monitor WhatsApp Web for '
     'messages containing business keywords (urgent, invoice, payment). Can send outbound messages.'),
    ('LinkedInWatcher + LinkedInPoster', 'Monitors LinkedIn notifications via browser automation. Features '
     'a template-based post creator supporting 5 post types: Business Update, Case Study, Thought Leadership, '
     'Promotional, and Engagement posts using Jinja2 templates.'),
    ('ApprovalWorkflow', 'Human-in-the-loop approval system. All sensitive actions create JSON approval '
     'files in Pending Approval. Moving to Approved or Rejected directories signals the decision.'),
    ('ActionExecutor', 'Executes approved actions including sending emails, WhatsApp messages, LinkedIn posts, '
     'scheduling meetings, creating tasks, and file operations.'),
    ('CronScheduler', 'Background scheduler for periodic tasks: daily morning briefings (8 AM), weekly '
     'business audits (Monday 9 AM), monthly subscription audits (1st of month 10 AM), CEO briefings, '
     'and approval queue checking every 5 minutes.'),
    ('Dashboard', 'Real-time system status displayed in the vault as a markdown dashboard with watcher '
     'status, pending tasks, and system health indicators.'),
]

for name, desc in features:
    pdf.bold_bullet(name + ': ', desc)
    pdf.ln(1)

# ---- 5. TECHNOLOGY STACK ----
pdf.add_page()
pdf.section_title('5. Technology Stack')
pdf.ln(2)

pdf.sub_section('Core Language & Runtime')
pdf.bullet_point('Python 3.12+ with modern async/await patterns')
pdf.bullet_point('Type-safe with Pydantic v2 for data validation')
pdf.bullet_point('Configuration via pydantic-settings & dotenv')

pdf.ln(2)
pdf.sub_section('File System Monitoring')
pdf.bullet_point('watchdog (>=6.0.0) - Event-driven file system monitoring')
pdf.bullet_point('Handles file creation, modification, and deletion events')

pdf.ln(2)
pdf.sub_section('Email Integration')
pdf.bullet_point('Google API Python Client for Gmail API')
pdf.bullet_point('OAuth 2.0 authentication with google-auth')
pdf.bullet_point('Send, draft, and read emails programmatically')

pdf.ln(2)
pdf.sub_section('Browser Automation')
pdf.bullet_point('Playwright (>=1.60.0) - Cross-browser automation')
pdf.bullet_point('WhatsApp Web and LinkedIn browser sessions')
pdf.bullet_point('Persistent browser contexts with saved sessions')

pdf.ln(2)
pdf.sub_section('Backend & Scheduling')
pdf.bullet_point('FastAPI - MCP Server HTTP endpoints')
pdf.bullet_point('APScheduler - Cron-based task scheduling')
pdf.bullet_point('httpx - Async HTTP client for API calls')

pdf.ln(2)
pdf.sub_section('Memory & Templates')
pdf.bullet_point('Obsidian vault as persistent markdown-based memory')
pdf.bullet_point('Jinja2 - Template engine for LinkedIn post generation')
pdf.bullet_point('croniter - Cron expression parsing for scheduling')

pdf.ln(2)
pdf.sub_section('Security')
pdf.bullet_point('cryptography - Data encryption for sensitive information')
pdf.bullet_point('OAuth 2.0 - Secure Google API authentication')

# ---- 6. SYSTEM WORKFLOW ----
pdf.add_page()
pdf.section_title('6. System Workflow')
pdf.ln(2)

steps = [
    ('1. Input Detection', 'Watchers monitor their respective channels (Inbox folder, Gmail, WhatsApp, LinkedIn). '
     'When new input is detected, a structured action file is created in Needs Action/ with full metadata.'),
    ('2. Task Creation', 'The AI reads the Needs Action/ folder, analyzes each task, and creates a plan in Plans/. '
     'The task is moved to In Progress/ while being worked on.'),
    ('3. Approval Request', 'For sensitive actions (sending emails, making payments, posting on social media), '
     'an Approval request JSON file is created in Pending Approval/ containing the action type, parameters, '
     'and a unique approval ID.'),
    ('4. Human Review', 'The human reviews pending approvals by reading the JSON files. Moving the file to '
     'Approved/ signals consent; moving to Rejected/ cancels the action. The system checks every 5 minutes.'),
    ('5. Execution', 'Approved actions are executed by the Action Executor. Results are logged to Logs/ '
     'with timestamps, and the task is moved to Done/.'),
    ('6. Audit & Reporting', 'All actions are permanently logged in structured JSON format. The Dashboard '
     'is updated in real-time. Scheduled briefings and audits are generated automatically.'),
]

for title, desc in steps:
    pdf.bold_bullet(title + ': ', desc)
    pdf.ln(2)

# ---- 7. VAULT STRUCTURE ----
pdf.add_page()
pdf.section_title('7. Vault & Memory Structure')
pdf.body_text(
    'The Obsidian vault serves as the AI\'s persistent memory and communication medium. Every file is a '
    'plain-text markdown file that can be read by both humans and AI.'
)
pdf.ln(2)

vault_items = [
    ('Inbox/', 'Drop files here for automatic processing'),
    ('Needs Action/', 'Tasks awaiting AI analysis and action'),
    ('In Progress/', 'Tasks currently being worked on'),
    ('Done/', 'Completed tasks archive'),
    ('Plans/', 'AI-generated execution plans'),
    ('Pending Approval/', 'Actions awaiting human sign-off'),
    ('Approved/', 'Human-approved actions ready for execution'),
    ('Rejected/', 'Declined actions archive'),
    ('Logs/', 'Structured JSON audit trail (date-stamped)'),
    ('Briefings/', 'Auto-generated daily/weekly briefings'),
    ('Audits/', 'Weekly and monthly audit reports'),
    ('Accounting/', 'Financial records and logs'),
    ('LinkedIn Templates/', 'Jinja2 post templates'),
    ('Dashboard.md', 'Real-time system health dashboard'),
    ('Company Handbook.md', 'Rules of Engagement (98 lines)'),
    ('Business Goals.md', 'KPIs, targets, active projects'),
]

for folder, desc in vault_items:
    pdf.bold_bullet(folder, ' - ' + desc)

# ---- 8. SECURITY ----
pdf.add_page()
pdf.section_title('8. Security & Approval System')
pdf.ln(2)

pdf.sub_section('Human-in-the-Loop (HITL)')
pdf.body_text(
    'Sensitive operations require explicit human approval before execution. The system never auto-executes '
    'financial transactions, external communications (email, WhatsApp, LinkedIn), or file operations '
    'without explicit consent. The Company Handbook enforces this constitutionally.'
)

pdf.sub_section('Action Types Requiring Approval')
action_types = [
    'SEND_EMAIL - Sending any outbound email',
    'CREATE_DRAFT - Creating email drafts for review',
    'SEND_WHATSAPP - Sending WhatsApp messages',
    'POST_LINKEDIN - Publishing LinkedIn posts',
    'SEND_SMS - Sending SMS messages',
    'MAKE_PAYMENT - Any financial transaction',
    'CREATE_INVOICE - Invoice generation',
    'SCHEDULE_MEETING - Calendar scheduling',
    'CREATE_TASK - Task creation in external systems',
    'WEB_SEARCH - External web searches',
    'FILE_OPERATION - File system modifications',
]
for at in action_types:
    pdf.bullet_point(at)

pdf.ln(2)
pdf.sub_section('Data Privacy')
pdf.body_text(
    'Sensitive data is encrypted at rest. Google API credentials use OAuth 2.0 tokens. '
    'Playwright browser sessions are stored locally. No data is sent to third-party services '
    'without explicit approval. All actions are logged with full traceability.'
)

pdf.sub_section('Decision Authority Matrix')
pdf.body_text(
    'The Company Handbook defines a clear authority matrix: routine file operations are auto-approved, '
    'internal communications require manager approval, external communications and financial transactions '
    'always require CEO/human approval. Escalation procedures are defined for ambiguous situations.'
)

# ---- 9. USE CASES ----
pdf.add_page()
pdf.section_title('9. Use Cases')
pdf.ln(2)

use_cases = [
    ('Freelancer / Solopreneur',
     'Automate client communication, invoice processing, file organization, and social media posting. '
     'Never miss a client email or urgent WhatsApp message again.'),
    ('Small Business Owner',
     'Handle employee task management, vendor communication, meeting scheduling, and business audit '
     'reports. Get daily briefings on business health without manual tracking.'),
    ('Digital Agency',
     'Manage multiple client LinkedIn accounts, monitor incoming project files, automate status '
     'reporting, and maintain organized client communication.'),
    ('Consultant / Coach',
     'Automate LinkedIn thought leadership content, manage client scheduling, process intake forms, '
     'and send automated follow-ups and invoices.'),
    ('Operations Manager',
     'Monitor file drops from multiple teams, automate approval workflows, generate weekly audit '
     'reports, and maintain organized project documentation.'),
    ('Startup Founder',
     'Get CEO briefings every Monday morning, automated subscription audits, weekly business reviews, '
     'and keep your finger on the pulse without micromanaging.'),
]

for name, desc in use_cases:
    pdf.bold_bullet(name + ': ', desc)
    pdf.ln(2)

# ---- 10. ROADMAP ----
pdf.add_page()
pdf.section_title('10. Roadmap & Future Tiers')
pdf.ln(2)

pdf.sub_section('Bronze Tier (Complete) - Hackathon 0')
pdf.body_text(
    'Core foundation: FileSystemWatcher, Gmail integration, Approval Workflow, Obsidian vault memory, '
    'MCP Server, Cron Scheduler, Company Handbook, Dashboard, Audit Trail. WhatsApp and LinkedIn '
    'watchers coded and ready (requires Playwright browsers).'
)

pdf.ln(1)
pdf.sub_section('Silver Tier (Next)')
pdf.body_text(
    'Full WhatsApp and LinkedIn integration, multi-account support, advanced Gmail filtering, '
    'improved error handling, web search capability, enhanced scheduling with calendar integration, '
    'and richer notification system.'
)

pdf.ln(1)
pdf.sub_section('Gold Tier')
pdf.body_text(
    'Odoo ERP integration for accounting and invoicing, CEO briefing automation, advanced analytics '
    'dashboard, CRM integration, multi-language support, and AI-powered decision recommendations.'
)

pdf.ln(1)
pdf.sub_section('Platinum Tier (Enterprise)')
pdf.body_text(
    'Multi-employee support with role-based access, team coordination, advanced AI reasoning with '
    'RAG (Retrieval Augmented Generation), custom plugin system, white-label deployment, and '
    'enterprise SSO/SAML integration.'
)

# ---- 11. WHAT'S INCLUDED ----
pdf.add_page()
pdf.section_title('11. What is Included')
pdf.ln(2)

pdf.sub_section('Complete Source Code')
pdf.body_text(
    'Fully functional Python 3.12+ project with modular architecture. All watchers, MCP server, '
    'approval workflow, schedulers, and vault structure are complete and tested.'
)

pdf.sub_section('Obsidian Vault')
pdf.body_text(
    'Pre-built vault with Company Handbook (98 lines of constitutional rules), Business Goals '
    '(Q2 2026 targets, KPIs, active projects), Dashboard (real-time status), and all required folders.'
)

pdf.sub_section('Documentation')
pdf.body_text(
    'Comprehensive README with architecture overview, setup instructions, configuration guide, '
    'testing procedures, and future roadmap. Inline code documentation throughout.'
)

pdf.sub_section('Configuration Files')
pdf.body_text(
    'pyproject.toml with all dependencies, .python-version (3.12), .gitignore, credentials template, '
    'uv.lock for deterministic builds.'
)

pdf.sub_section('Test Files & Test Results')
pdf.body_text(
    'Multiple test files demonstrating FileSystemWatcher functionality, integration test outputs, '
    'and comprehensive test results showing system behavior.'
)

pdf.sub_section('Action History & Logs')
pdf.body_text(
    'Complete audit trail with 30+ action entries spanning multiple days, including approved/rejected '
    'actions, showing the full system workflow in action.'
)

# ---- 12. SETUP ----
pdf.add_page()
pdf.section_title('12. Setup & Deployment')
pdf.ln(2)

pdf.sub_section('Prerequisites')
pdf.bullet_point('Python 3.12 or higher')
pdf.bullet_point('Obsidian (for vault access, optional)')
pdf.bullet_point('Google Cloud project (for Gmail API, optional)')

pdf.ln(2)
pdf.sub_section('Quick Start')
pdf.bullet_point('Clone repository')
pdf.bullet_point('Create virtual environment: python -m venv .venv')
pdf.bullet_point('Install dependencies: pip install -e .')
pdf.bullet_point('Run FileSystemWatcher: python start_watcher.py')
pdf.bullet_point('Run full system: python main.py')
pdf.bullet_point('Drop files into AI_Employee_Vault/Inbox/')

pdf.ln(2)
pdf.sub_section('Configuration')
pdf.body_text(
    'Copy credentials.json to the vault directory for Gmail integration. '
    'Edit Company Handbook.md to customize the AI\'s behavioral rules. '
    'Edit Business Goals.md to set your own KPIs and targets. '
    'Run playwright install for WhatsApp/LinkedIn browser automation.'
)

pdf.ln(4)
pdf.set_draw_color(25, 60, 120)
pdf.set_line_width(0.3)
pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
pdf.ln(6)

pdf.set_font('Helvetica', 'B', 12)
pdf.set_text_color(25, 60, 120)
pdf.cell(0, 8, 'Ready to Deploy Your AI Employee Today.', align='C')

# ---- OUTPUT ----
output_path = '/home/ali-hamza/public/Hackathon0/Personal_AI_Employee_Hackathon0_Bronze_Tier.pdf'
pdf.output(output_path)
print(f'PDF generated successfully: {output_path}')
print(f'Total pages: {pdf.page_no()}')
