"""Generate an enterprise-grade PDF report for the AI Digital Employee project."""

import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from fpdf import FPDF
except ImportError:
    print("fpdf2 not installed. Run: uv sync")
    sys.exit(1)

REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)

PRIMARY = (37, 99, 235)
DARK = (30, 41, 59)
ACCENT = (124, 58, 237)
LIGHT_BG = (248, 250, 252)
MEDIUM_GRAY = (100, 116, 139)
BORDER = (226, 232, 240)
WHITE = (255, 255, 255)
GREEN = (34, 197, 94)
AMBER = (245, 158, 11)


ASCII_MAP = str.maketrans({
    "\u2014": "---",
    "\u2013": "--",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "*",
    "\u2026": "...",
    "\u00a0": " ",
})


def _a(text: str) -> str:
    return text.translate(ASCII_MAP)


class EnterpriseReport(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=25)
        self._in_cover = False

    def header(self):
        if self._in_cover:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MEDIUM_GRAY)
        self.cell(0, 6, "AI Digital Employee  |  Enterprise Architecture Report", align="L")
        self.ln(4)
        self.set_draw_color(*BORDER)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        if self._in_cover:
            return
        self.set_y(-20)
        self.set_draw_color(*BORDER)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MEDIUM_GRAY)
        total = self.page_no() - 1
        self.cell(0, 10, f"Page {self.page_no() - 1} of {total}", align="C")

    def cover_page(self):
        self._in_cover = True
        self.add_page()
        self.set_fill_color(*DARK)
        self.rect(0, 0, 210, 125, "F")
        self.set_y(28)
        self.set_font("Helvetica", "B", 34)
        self.set_text_color(*WHITE)
        self.cell(0, 15, "AI DIGITAL EMPLOYEE", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font("Helvetica", "", 14)
        self.set_text_color(196, 181, 253)
        self.cell(0, 10, "Enterprise Autonomous Agent System", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(12)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.5)
        self.line(70, self.get_y(), 140, self.get_y())
        self.ln(12)
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*WHITE)
        self.cell(0, 7, "Prepared by: Ali Hamza", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, f"Date: {datetime.now().strftime('%B %d, %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, "Classification: Internal  |  Version 1.0", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(30)
        self.set_y(140)
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.3)
        self.line(30, self.get_y(), 180, self.get_y())
        self.ln(6)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*MEDIUM_GRAY)
        self.cell(0, 6, "CONFIDENTIAL", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, "This document contains proprietary system architecture", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, "and may not be distributed without authorization.", align="C", new_x="LMARGIN", new_y="NEXT")
        self._in_cover = False

    def toc_page(self):
        self.add_page()
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(*DARK)
        self.cell(0, 14, "Contents", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 60, self.get_y())
        self.ln(10)

    def toc_entry(self, num, title):
        self.set_font("Helvetica", "", 11)
        self.set_text_color(*DARK)
        self.cell(0, 8, _a(f"  {num}.  {title}"), new_x="LMARGIN", new_y="NEXT")

    def section_title(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*DARK)
        self.cell(0, 12, _a(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*PRIMARY)
        self.set_line_width(0.6)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(6)

    def sub_title(self, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*DARK)
        self.cell(0, 8, _a(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, _a(text))
        self.ln(2)

    def bullet(self, text, indent=15):
        x0 = self.l_margin
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*DARK)
        self.set_x(x0 + indent)
        self.set_text_color(*PRIMARY)
        self.cell(5, 5.5, "* ", new_x="RIGHT")
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, _a(text))

    def colored_box(self, title, text, color=PRIMARY):
        self.ln(2)
        r, g, b = color
        self.set_fill_color(r, g, b)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, _a(f"  {title}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_fill_color(*LIGHT_BG)
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 9)
        self.multi_cell(0, 5, _a("  " + text), fill=True)
        self.ln(2)

    def add_table(self, headers, rows, col_widths=None):
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)
        self.ln(2)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*PRIMARY)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, _a(f" {h}"), border=True, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*DARK)
        for ri, row in enumerate(rows):
            fill = ri % 2 == 0
            if fill:
                self.set_fill_color(*LIGHT_BG)
            else:
                self.set_fill_color(*WHITE)
            for i, cell_text in enumerate(row):
                self.cell(col_widths[i], 6, _a(f" {cell_text}"), border=True, fill=True, align="C" if i > 0 else "L")
            self.ln()
        self.ln(2)

    def divider(self):
        self.ln(2)
        self.set_draw_color(*BORDER)
        self.set_line_width(0.2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)


def generate_report():
    pdf = EnterpriseReport()

    # ── Cover Page ──────────────────────────────────────────────────────
    pdf.cover_page()

    # ── Table of Contents ───────────────────────────────────────────────
    pdf.toc_page()
    sections = [
        "Executive Summary",
        "System Architecture",
        "Core Capabilities",
        "Technology Stack",
        "Security Architecture",
        "Deployment",
        "Development Roadmap",
        "Conclusion",
    ]
    for i, title in enumerate(sections, 1):
        pdf.toc_entry(i, title)

    # ── 1. Executive Summary ─────────────────────────────────────────────
    pdf.section_title("1. Executive Summary")
    pdf.body_text(
        "The AI Digital Employee is a production-grade autonomous agent system designed to "
        "automate business communication workflows while maintaining strict human oversight. "
        "Built on a Perception-Reasoning-Action architecture, it monitors multiple channels "
        "including email, messaging, and professional networks, processes information through "
        "an LLM-powered reasoning engine, and executes approved actions via a modular MCP server."
    )
    pdf.body_text(
        "This system represents a significant advancement in enterprise automation by combining "
        "six specialized watchers, an AI subagent for contextual decision-making, and a "
        "comprehensive action execution layer \u2014 all orchestrated through a file-based memory "
        "system that ensures complete auditability and transparency."
    )
    pdf.sub_title("Key Value Propositions")
    pdf.bullet("Reduce response time across all communication channels")
    pdf.bullet("Maintain full human control with approval-gated execution")
    pdf.bullet("Complete audit trail via file-based vault (no database required)")
    pdf.bullet("Modular architecture \u2014 each component independently deployable")
    pdf.bullet("Docker-native deployment for cloud or on-premise infrastructure")

    # ── 2. System Architecture ───────────────────────────────────────────
    pdf.section_title("2. System Architecture")
    pdf.body_text(
        "The system follows a layered architecture pattern with four distinct tiers, each "
        "responsible for a specific phase of the autonomous agent lifecycle. Data flows "
        "unidirectionally from Perception through Reasoning to Action, with human approval "
        "serving as the critical gate between planning and execution."
    )
    pdf.sub_title("2.1 Layer 1: Perception \u2014 Multi-Channel Watchers")
    pdf.add_table(
        ["Watcher", "Channel", "Technology", "Trigger"],
        [
            ["GmailWatcher", "Email", "Gmail API (OAuth 2.0)", "Polls unread mail"],
            ["WhatsAppWatcher", "Messaging", "Playwright Browser", "Polls WhatsApp Web"],
            ["LinkedInWatcher", "Social", "Playwright + Jinja2", "Polls notifications"],
            ["FileSystemWatcher", "Files", "watchdog (inotify)", "File system events"],
            ["AIReasoningWatcher", "Internal", "opencode subprocess", "Action file trigger"],
            ["ApprovalWatcher", "Approval", "File rename watcher", "Decision signals"],
        ],
        [36, 26, 48, 38],
    )
    pdf.sub_title("2.2 Layer 2: Reasoning \u2014 AI Brain")
    pdf.body_text(
        "When an action file lands in the Needs_Action directory, the @ai-employee opencode "
        "subagent activates. It reads the Company Handbook for business rules, Business Goals "
        "for strategic alignment, and the live Dashboard for current metrics. The agent then "
        "generates a detailed execution plan and a structured approval request for human review."
    )
    pdf.sub_title("2.3 Layer 3: Action \u2014 MCP Server")
    pdf.body_text(
        "The Model Context Protocol (MCP) server exposes 10 action tools spanning communication, "
        "productivity, document generation, and research. Each tool independently integrates with "
        "its external service via OAuth or browser automation. Approved actions are executed "
        "sequentially with full error handling and logging."
    )
    pdf.sub_title("2.4 Layer 4: Memory \u2014 Obsidian Vault")
    pdf.body_text(
        "All system state resides in an Obsidian-compatible Markdown vault. This file-based "
        "approach eliminates database dependencies while providing complete transparency. Every "
        "plan, approval request, and execution log is stored as a flat file, enabling full "
        "audit trail reconstruction. The vault is automatically initialized on first run and "
        "persists across container restarts via Docker volumes."
    )
    pdf.divider()
    pdf.sub_title("Data Flow")
    pdf.body_text(
        "The complete data flow follows a unidirectional pipeline: Watchers detect signals and "
        "write action files to Needs_Action. The AIReasoningWatcher triggers the opencode "
        "subagent, which reads context, writes plans to Plans/, and creates approval requests "
        "in Pending_Approval/. The ApprovalWatcher monitors for human decisions (via CLI or "
        "web UI), then routes approved requests to the MCP Server for execution. All outcomes "
        "are logged to Logs/ and archived to Completed/ or Rejected/."
    )

    # ── 3. Core Capabilities ────────────────────────────────────────────
    pdf.section_title("3. Core Capabilities")
    pdf.body_text(
        "The AI Digital Employee provides comprehensive communication automation across six "
        "major capability domains, each designed to handle real-world business workflows."
    )
    capabilities = [
        ("Email Automation",
         "Monitors Gmail for important communications using the Gmail API with OAuth 2.0. "
         "AI crafts context-aware replies using company guidelines. Every outbound message "
         "requires human approval, preventing unauthorized communications."),
        ("WhatsApp Integration",
         "Leverages Playwright browser automation to interact with WhatsApp Web. "
         "Persistent sessions eliminate repeated QR scans. AI-generated responses maintain "
         "brand voice and require approval before delivery."),
        ("LinkedIn Management",
         "Monitors LinkedIn notifications and supports post creation via Jinja2 templates. "
         "Five pre-built template types: business updates, case studies, thought leadership, "
         "promotional content, and engagement posts."),
        ("Calendar Scheduling",
         "Integrates with Google Calendar API for automated meeting creation. Supports "
         "attendee management, timezone handling, and smart scheduling."),
        ("Document Generation",
         "Generates professional PDF invoices using fpdf2. Supports file operations for "
         "document management and structured task creation for workflow tracking."),
        ("Web Research",
         "Automated web search capability for competitive analysis, market research, and "
         "data gathering. Results are structured and citable for downstream use."),
    ]
    for i, (title, desc) in enumerate(capabilities):
        pdf.colored_box(title, desc, PRIMARY if i % 2 == 0 else ACCENT)

    # ── 4. Technology Stack ─────────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("4. Technology Stack")
    pdf.body_text(
        "The system is built on a modern, type-safe Python 3.12 foundation with carefully "
        "selected technologies for each architectural layer."
    )
    pdf.add_table(
        ["Technology", "Purpose", "Rationale"],
        [
            ["Python 3.12", "Core runtime", "Type-safe, fast, widely adopted"],
            ["OpenCode CLI", "AI reasoning engine", "LLM-powered subagent orchestration"],
            ["uv", "Package management", "10x faster than pip"],
            ["Gmail API", "Email", "Official Google API (OAuth 2.0)"],
            ["Calendar API", "Scheduling", "Google Calendar integration"],
            ["Playwright", "Browser automation", "WhatsApp, LinkedIn, Web Search"],
            ["FastAPI", "Web framework", "Approval UI server"],
            ["Jinja2", "Templating", "LinkedIn post templates"],
            ["fpdf2", "PDF generation", "Invoice creation"],
            ["APScheduler", "Task scheduling", "Cron-based job management"],
            ["pydantic-settings", "Configuration", "Type-safe .env management"],
            ["Docker", "Containerization", "Production deployment"],
            ["Ruff / Black", "Linting", "Code quality enforcement"],
        ],
        [40, 38, 70],
    )

    # ── 5. Security Architecture ─────────────────────────────────────────
    pdf.section_title("5. Security Architecture")
    pdf.body_text(
        "Security is architected into the system at every layer, from credential management "
        "to execution gating. The following principles govern the design."
    )
    pdf.add_table(
        ["Principle", "Implementation"],
        [
            ["Zero secrets in code", "All credentials in .env (gitignored)"],
            ["In-memory credentials", "OAuth tokens reconstructed at runtime"],
            ["Human-in-the-loop", "Every action requires explicit approval"],
            ["Prompt injection defense", "System prompt enforces approval gate"],
            ["Isolated API keys", "opencode keys stored outside project tree"],
            ["Container safety", "Secrets injected at runtime, never baked into image"],
            ["Audit trail", "All decisions logged in immutable vault files"],
        ],
        [55, 110],
    )
    pdf.divider()
    pdf.sub_title("Compliance")
    pdf.body_text(
        "The system's file-based architecture naturally supports compliance requirements. "
        "Every action is logged with timestamps, decision rationale, and execution status. "
        "Logs are stored as daily JSON files in the vault, enabling straightforward export "
        "to SIEM systems or audit platforms. The human-in-the-loop approval model ensures "
        "that no action executes without documented authorization."
    )

    # ── 6. Deployment ──────────────────────────────────────────────────
    pdf.section_title("6. Deployment")
    pdf.body_text(
        "The system is Docker-native and deploys in a single command. The container image "
        "includes Python 3.12, Node.js 24, OpenCode CLI, and Playwright with Chromium."
    )
    pdf.sub_title("6.1 Container Architecture")
    pdf.body_text(
        "The Docker image uses a multi-stage build pattern: system dependencies first, "
        "then Node.js + opencode CLI, followed by Python dependencies via uv, and finally "
        "Playwright browser installation. The vault is mounted as a persistent volume with "
        "automatic template initialization on first run via entrypoint.sh."
    )
    pdf.sub_title("6.2 Deployment Options")
    pdf.bullet("Local development: uv run python -m src.scripts.main")
    pdf.bullet("Docker: docker compose up --build -d")
    pdf.bullet("Tunnel mode (public URL): --tunnel flag via localhost.run")
    pdf.bullet("Approval web UI: http://localhost:8080")

    # ── 7. Development Roadmap ─────────────────────────────────────────
    pdf.section_title("7. Development Roadmap")
    pdf.body_text(
        "The project follows a phased development approach, with foundation and core "
        "capabilities already in production. Enterprise features and cloud-scale deployments "
        "are in active development."
    )
    pdf.add_table(
        ["Phase", "Status", "Features"],
        [
            ["Foundation", "Complete", "File vault, watchers, base architecture"],
            ["Core", "Complete", "Gmail, WhatsApp, LinkedIn, Calendar integration"],
            ["Enterprise", "Complete", "Docker, CI/CD, security, approval system"],
            ["Gold", "In Progress", "Multi-tenant support, web UI, SMS, payments"],
            ["Cloud", "Planned", "Team collaboration, analytics, API gateway"],
        ],
        [34, 28, 88],
    )
    pdf.divider()
    pdf.sub_title("Future Enhancements")
    pdf.bullet("Multi-tenant architecture for team deployment")
    pdf.bullet("SMS integration via Twilio for alerting")
    pdf.bullet("Payment processing via Stripe API")
    pdf.bullet("Interactive web dashboard with analytics")
    pdf.bullet("API gateway for external system integration")

    # ── 8. Conclusion ──────────────────────────────────────────────────
    pdf.section_title("8. Conclusion")
    pdf.body_text(
        "The AI Digital Employee represents a new paradigm in enterprise automation \u2014 one where "
        "autonomous agents augment human workers rather than replace them. By combining multi-channel "
        "perception, LLM-powered reasoning, and human-gated execution, the system delivers "
        "measurable productivity gains while maintaining complete control and auditability."
    )
    pdf.body_text(
        "The modular architecture ensures the system can grow with organizational needs, adding "
        "new watchers, action tools, or deployment targets without disrupting existing workflows. "
        "The file-based vault guarantees transparency and portability, freeing the system from "
        "proprietary database lock-in."
    )
    pdf.ln(10)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.3)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*MEDIUM_GRAY)
    pdf.cell(0, 7, _a('"The future of work is human-AI collaboration, not replacement."'), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(14)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 6, _a("Contact: Ali Hamza  |  Email: raialihamza58@gmail.com"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _a("Repository: github.com/Alihamza400/AI_Digital_Employee"), align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Save ────────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"AI_DIGITAL_EMPLOYEE_REPORT_{timestamp}.pdf"
    pdf.output(str(path))
    return path


if __name__ == "__main__":
    path = generate_report()
    print(f"Report generated: {path}")
