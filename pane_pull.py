#!/usr/bin/env python3
"""Pull panes from anywhere in the Herdr session into the current tab."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
STATUS = {"working": "●", "blocked": "!", "done": "✓", "idle": "○"}
HEADER = "tab: mark   enter: pull in, split right   alt-d: split down   esc: cancel"


def herdr(*args: str) -> Dict[str, Any]:
    done = subprocess.run([HERDR, *args], capture_output=True, text=True)
    try:
        reply = json.loads(done.stdout)
    except ValueError:
        raise RuntimeError(done.stderr.strip() or done.stdout.strip() or "herdr failed")
    if "error" in reply:
        raise RuntimeError(reply["error"].get("message", "herdr error"))
    return reply["result"]


def split_ratios(count: int) -> List[float]:
    """Share of each split its target keeps, so the focused pane and the
    `count` pulled panes all end up the same size.

    Every pulled pane is split off the one pulled just before it, so the first
    target keeps 1/(count+1) and each later one a bigger share of what is left.
    """
    return [1 / (count + 1 - step) for step in range(count)]


def candidate_lines(
    panes: List[Dict[str, Any]],
    workspaces: Dict[str, str],
    tabs: Dict[str, str],
    here_tab: str,
) -> List[str]:
    home = os.path.expanduser("~")
    lines = []
    for pane in panes:
        if pane["tab_id"] == here_tab:
            continue
        title = pane.get("label") or pane.get("terminal_title_stripped") or pane.get("agent") or "shell"
        cwd = str(pane.get("cwd") or "")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        where = f"{workspaces.get(pane['workspace_id'], '?')} › {tabs.get(pane['tab_id'], '?')}"
        status = STATUS.get(str(pane.get("agent_status")), " ")
        lines.append(f"{pane['pane_id']}\t{status} {title}  │  {where}  │  {cwd}")
    return lines


def pull(picked: List[str], here_pane: str, here_tab: str, direction: str) -> None:
    target, view_moved = here_pane, False
    try:
        for pane_id, ratio in zip(picked, split_ratios(len(picked))):
            # Herdr answers a move out of or into a zoomed tab with success and
            # changed=false, and un-zooming switches the view to that tab.
            for pane in (target, pane_id):
                if herdr("pane", "layout", "--pane", pane)["layout"]["zoomed"]:
                    herdr("pane", "zoom", pane, "--off")
                    view_moved = True
            moved = herdr(
                "pane", "move", pane_id,
                "--tab", here_tab,
                "--target-pane", target,
                "--split", direction,
                "--ratio", f"{ratio:.4f}",
                "--no-focus",
            )["move_result"]
            if not moved["changed"]:
                raise RuntimeError(f"{pane_id} was not moved ({moved.get('reason')})")
            # A moved pane is renumbered into this workspace; chain off its new id.
            target = moved["pane"]["pane_id"]
    finally:
        if view_moved:
            herdr("tab", "focus", here_tab)


def main() -> int:
    context = json.loads(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON") or "{}")
    here_pane, here_tab = context.get("focused_pane_id"), context.get("tab_id")
    if not (here_pane and here_tab):
        raise RuntimeError("Herdr did not report a focused pane")

    lines = candidate_lines(
        herdr("pane", "list")["panes"],
        {w["workspace_id"]: w["label"] for w in herdr("workspace", "list")["workspaces"]},
        {t["tab_id"]: t["label"] for t in herdr("tab", "list")["tabs"]},
        here_tab,
    )
    if not lines:
        raise RuntimeError("No panes outside this tab.")

    fzf = subprocess.run(
        [
            "fzf", "--multi", "--reverse", "--delimiter=\t", "--with-nth=2..",
            "--expect=alt-d", f"--header={HEADER}",
            "--preview", f"{HERDR} pane read {{1}} --source visible --format ansi",
            "--preview-window=down,60%,follow",
        ],
        input="\n".join(lines), stdout=subprocess.PIPE, text=True,
    )
    key, *chosen = fzf.stdout.splitlines() or [""]
    if fzf.returncode != 0 or not chosen:
        return 0
    pull([line.split("\t", 1)[0] for line in chosen], here_pane, here_tab, "down" if key == "alt-d" else "right")
    return 0


def selftest() -> None:
    if not shutil.which("fzf"):
        raise SystemExit("pane-pull needs fzf on PATH")
    for count in range(1, 6):
        sizes, rest = [], 1.0
        for ratio in split_ratios(count):
            sizes.append(rest * ratio)
            rest -= sizes[-1]
        assert all(abs(size - rest) < 1e-9 for size in sizes), (count, sizes, rest)
    lines = candidate_lines(
        [
            {"pane_id": "w1:p1", "tab_id": "w1:t1", "workspace_id": "w1", "agent_status": "idle"},
            {"pane_id": "w2:p1", "tab_id": "w2:t1", "workspace_id": "w2", "label": "api", "agent_status": "working"},
        ],
        {"w2": "work"}, {"w2:t1": "main"}, "w1:t1",
    )
    assert lines == ["w2:p1\t● api  │  work › main  │  "], lines
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        selftest()
        raise SystemExit(0)
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        # The popup closes with the process, so hold it open to show the error.
        print(f"pane-pull: {error}")
        input("press enter to close")
        raise SystemExit(1)
