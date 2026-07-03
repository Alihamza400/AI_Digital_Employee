"""
Approval CLI - List, approve, or reject pending requests
"""
import sys
import json
from pathlib import Path

VAULT = Path("AI_Employee_Vault")
PENDING = VAULT / "Pending_Approval"
APPROVED = VAULT / "Approved"
REJECTED = VAULT / "Rejected"

PENDING.mkdir(parents=True, exist_ok=True)
APPROVED.mkdir(parents=True, exist_ok=True)
REJECTED.mkdir(parents=True, exist_ok=True)


def list_pending():
    files = sorted(PENDING.glob("*.json"))
    if not files:
        print("No pending approval requests.")
        return []

    print(f"\n{'ID':<8} {'Type':<22} {'Summary':<40} {'File'}")
    print("-" * 80)
    for f in files:
        try:
            data = json.loads(f.read_text())
            req_id = data.get('id', '?')[:8]
            action_type = data.get('action_type', '?')
            params = data.get('parameters', {})
            summary = str(list(params.values())[0] if params else '')[:38]
            print(f"{req_id:<8} {action_type:<22} {summary:<40} {f.name}")
        except Exception as e:
            print(f"{'ERROR':<8} {'?':<22} {str(e):<40} {f.name}")
    return files


def approve(filename):
    src = PENDING / filename
    if not src.exists():
        print(f"File not found: {filename}")
        return False
    dst = APPROVED / filename
    src.rename(dst)
    print(f"✅ Approved: {filename}")
    return True


def reject(filename):
    src = PENDING / filename
    if not src.exists():
        print(f"File not found: {filename}")
        return False
    dst = REJECTED / filename
    src.rename(dst)
    print(f"❌ Rejected: {filename}")
    return True


def show(filename):
    src = PENDING / filename
    if not src.exists():
        print(f"File not found: {filename}")
        return
    data = json.loads(src.read_text())
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "list":
        list_pending()

    elif args[0] == "approve" and len(args) >= 2:
        for fname in args[1:]:
            approve(fname)

    elif args[0] == "reject" and len(args) >= 2:
        for fname in args[1:]:
            reject(fname)

    elif args[0] == "show" and len(args) >= 2:
        show(args[1])

    elif args[0] == "all":
        files = list_pending()
        if files:
            print(f"\nCommands:")
            print(f"  python3 approve.py approve <filename>")
            print(f"  python3 approve.py reject <filename>")

    else:
        print("Usage:")
        print("  python3 approve.py              List pending")
        print("  python3 approve.py list         List pending")
        print("  python3 approve.py show <file>   Show details")
        print("  python3 approve.py approve <file> [file...]  Approve")
        print("  python3 approve.py reject <file>  [file...]  Reject")
