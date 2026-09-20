"""
Contract test between the opencode subagent definition and the executor.

The subagent is instructed to emit only the action types in its table. If that
table drifts from what the executor can actually run, the agent will queue
requests that fail with "No handler for action type" and get archived to
Completed/failed/ — silently breaking the workflow.
"""

import re
from pathlib import Path

import pytest

from src.watchers.mcp_server import ActionType, MCPServer

AGENT_FILE = Path(".opencode/agents/ai-employee.md")


@pytest.fixture(scope="module")
def agent_doc() -> str:
    assert AGENT_FILE.exists(), "the ai-employee subagent definition is missing"
    return AGENT_FILE.read_text()


@pytest.fixture(scope="module")
def frontmatter(agent_doc: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", agent_doc, re.DOTALL)
    assert match, "agent definition has no YAML frontmatter"
    return match.group(1)


def _documented_action_types(agent_doc: str) -> set:
    """Action types named in the markdown table's first column."""
    rows = re.findall(r"^\|\s*`([A-Z_]+)`\s*\|", agent_doc, re.MULTILINE)
    return set(rows)


def test_agent_runs_as_primary(frontmatter):
    """
    `mode: subagent` makes `opencode run --agent ai-employee` silently fall back
    to the default build agent, so the reasoning watcher would never reason.
    """
    assert re.search(r"^mode:\s*primary\s*$", frontmatter, re.MULTILINE)


def test_documented_action_types_exist_in_enum(agent_doc):
    documented = _documented_action_types(agent_doc)
    assert documented, "no action types were documented for the subagent"

    known = {member.name for member in ActionType}
    unknown = documented - known
    assert not unknown, f"agent documents action types the executor does not know: {unknown}"


def test_every_documented_action_type_has_a_handler(tmp_path, agent_doc):
    documented = _documented_action_types(agent_doc)
    executor = MCPServer(str(tmp_path), {}).action_executor

    missing = sorted(name for name in documented if ActionType[name] not in executor.handlers)
    assert not missing, f"documented action types with no executor handler: {missing}"


def test_agent_is_told_the_exact_action_type_values(agent_doc):
    """The agent must emit lowercase enum values, not the uppercase names."""
    for member in ActionType:
        if member.name in _documented_action_types(agent_doc):
            assert member.value in agent_doc.lower()


def test_file_operation_documents_only_supported_operations(agent_doc):
    supported = {"create_file", "delete_file"}
    row = next(
        (
            line
            for line in agent_doc.splitlines()
            if "`FILE_OPERATION`" in line and line.startswith("|")
        ),
        None,
    )
    assert row, "FILE_OPERATION is not documented"

    documented = set(re.findall(r"`?\"(create_file|delete_file)\"`?", row))
    assert documented == supported


def test_agent_never_claims_to_execute_directly(agent_doc):
    """The human-in-the-loop guarantee depends on the prompt enforcing it."""
    assert "Never execute actions directly" in agent_doc
    assert "always create approval requests" in agent_doc
