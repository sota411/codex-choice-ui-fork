#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import json
import re
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REQUIRED_FIELDS = [
    "要件",
    "調査",
    "設計判断",
    "試行錯誤",
    "実装",
    "確認",
    "残課題",
]

PLACEHOLDER_VALUES = {
    "",
    "todo",
    "tbd",
    "未記入",
    "未定",
    "あとで書く",
}

PENDING_OPEN_RE = re.compile(r"<!--\s*codex-memo:pending\b(?P<meta>[^>]*)-->")
PENDING_CLOSE = "<!-- /codex-memo:pending -->"
DONE_OPEN_PREFIX = "<!-- codex-memo:done"
DONE_CLOSE = "<!-- /codex-memo:done -->"


@dataclass(frozen=True)
class PendingBlock:
    meta: str
    body: str
    malformed: bool = False


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: codex_memo_guard.py prompt|stop|pre-commit")

    mode = sys.argv[1]
    if mode == "prompt":
        return run_prompt()
    if mode == "stop":
        return run_stop()
    if mode == "pre-commit":
        return run_pre_commit()
    raise SystemExit(f"unknown mode: {mode}")


def run_prompt() -> int:
    payload = read_payload()
    memo_path = memo_path_for_payload(payload)
    if not memo_path.is_file():
        return 0

    session_id = str(payload["session_id"])
    turn_id = str(payload["turn_id"])
    with memo_lock(memo_path):
        text = read_text_or_empty(memo_path)
        write_state(payload, memo_path)

        if has_done_marker(text, session_id, turn_id):
            return 0

        if find_pending_blocks(text, session_id=session_id, turn_id=turn_id):
            emit_user_prompt_context(
                "memo.md に今回の turn の codex-memo:pending が残っています。"
                "作業終了前に各項目を埋め、pending を done に変更してください。"
            )
            return 0

        now = datetime.now(ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M")
        entry = build_entry(now, session_id, turn_id)
        if text and not text.endswith("\n"):
            text += "\n"
        if not text:
            text = "# 作業メモ\n\n"
        memo_path.write_text(text + entry, encoding="utf-8")

    emit_user_prompt_context(
        "memo.md に今回の作業メモ枠を追加しました。"
        "最終回答前に要件、調査、設計判断、試行錯誤、実装、確認、残課題を埋め、"
        "codex-memo:pending を codex-memo:done に変更してください。"
    )
    return 0


def run_stop() -> int:
    payload = read_payload()
    state = read_state(payload)
    if state is None:
        return 0

    memo_path = Path(str(state["memo_path"]))
    with memo_lock(memo_path):
        reason = validation_failure_reason(
            memo_path,
            session_id=str(payload["session_id"]),
            turn_id=str(payload["turn_id"]),
            require_done=True,
        )
    if reason is None:
        return 0

    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


def run_pre_commit() -> int:
    root = repo_root(Path.cwd())
    memo_path = root / "memo.md"
    if not memo_path.is_file():
        return 0

    with memo_lock(memo_path):
        reason = validation_failure_reason(memo_path)
    if reason is None:
        return 0

    print(reason, file=sys.stderr)
    return 1


def read_payload() -> dict[str, object]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("hook payload is empty")
    payload = json.loads(raw)
    for key in ("cwd", "session_id", "turn_id"):
        if key not in payload:
            raise KeyError(f"hook payload missing required key: {key}")
    return payload


def memo_path_for_payload(payload: dict[str, object]) -> Path:
    return Path(str(payload["cwd"])) / "memo.md"


def repo_root(cwd: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        root = result.stdout.strip()
        if root:
            return Path(root)
    return cwd


def state_dir() -> Path:
    return Path.home() / ".cache" / "codex-memo-guard"


@contextmanager
def memo_lock(memo_path: Path):
    lock_dir = state_dir() / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(memo_path.resolve()).encode("utf-8")).hexdigest()
    lock_path = lock_dir / f"{key}.lock"
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def state_path(session_id: object, turn_id: object) -> Path:
    key = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{session_id}-{turn_id}")
    return state_dir() / f"{key}.json"


def write_state(payload: dict[str, object], memo_path: Path) -> None:
    state_dir().mkdir(parents=True, exist_ok=True)
    state_path(payload["session_id"], payload["turn_id"]).write_text(
        json.dumps(
            {
                "session_id": payload["session_id"],
                "turn_id": payload["turn_id"],
                "memo_path": str(memo_path),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def read_state(payload: dict[str, object]) -> dict[str, object] | None:
    path = state_path(payload["session_id"], payload["turn_id"])
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_entry(timestamp: str, session_id: object, turn_id: object) -> str:
    return (
        f"## {timestamp} - Codex turn {turn_id}\n"
        f"<!-- codex-memo:pending session={session_id} turn={turn_id} -->\n"
        "- 要件: TODO\n"
        "- 調査: TODO\n"
        "- 設計判断: TODO\n"
        "- 試行錯誤: TODO\n"
        "- 実装: TODO\n"
        "- 確認: TODO\n"
        "- 残課題: TODO\n"
        "<!-- /codex-memo:pending -->\n\n"
    )


def validation_failure_reason(
    memo_path: Path,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
    require_done: bool = False,
) -> str | None:
    if not memo_path.exists():
        if require_done:
            return "memo.md がありません。今回の作業メモを戻してから終了してください。"
        return None

    text = memo_path.read_text(encoding="utf-8")

    if session_id is not None and turn_id is not None:
        if has_done_marker(text, session_id, turn_id):
            return None

        blocks = find_pending_blocks(text, session_id=session_id, turn_id=turn_id)
        if blocks:
            return pending_blocks_failure_reason(blocks)

        if require_done:
            return (
                "memo.md に今回の turn のメモ枠がありません。"
                "今回の要件、調査、設計判断、試行錯誤、実装、確認、残課題を追記し、"
                f"`<!-- codex-memo:done session={session_id} turn={turn_id} -->` "
                f"から `{DONE_CLOSE}` までの完了ブロックとして残してください。"
            )
        return None

    blocks = list(find_pending_blocks(text))
    if not blocks:
        if has_pending_marker(text):
            return (
                "memo.md に codex-memo:pending が残っていますが、開始/終了マーカーの対応が壊れています。"
                "該当箇所を整理し、完了済みなら done マーカーへ変更してください。"
            )
        return None

    return pending_blocks_failure_reason(blocks)


def pending_blocks_failure_reason(blocks: list[PendingBlock]) -> str:
    problems: list[str] = []
    for index, block in enumerate(blocks, start=1):
        if block.malformed:
            problems.append(f"{index}件目の pending メモに終了マーカーがありません")
            continue
        missing = missing_required_fields(block.body)
        if missing:
            problems.append(f"{index}件目の未記入項目: {', '.join(missing)}")
        else:
            problems.append(
                f"{index}件目は項目入力済みですが pending マーカーが残っています"
            )

    detail = " / ".join(problems)
    return (
        f"memo.md の今回分が未完了です。{detail}。"
        "各項目を埋め、該当ブロックの開始マーカーを "
        f"`{DONE_OPEN_PREFIX} ... -->`、終了マーカーを `{DONE_CLOSE}` に変更してください。"
        "`なし` は明示的な記録として許可します。"
    )


def has_pending_marker(text: str) -> bool:
    return "codex-memo:pending" in text


def has_done_marker(text: str, session_id: str, turn_id: str) -> bool:
    done_open = re.compile(r"<!--\s*codex-memo:done\b(?P<meta>[^>]*)-->")
    for match in done_open.finditer(text):
        meta = marker_meta(match.group("meta"))
        if meta.get("session") != session_id:
            continue
        if meta.get("turn") != turn_id:
            continue
        close_index = text.find(DONE_CLOSE, match.end())
        if close_index != -1:
            return True
    return False


def marker_meta(raw_meta: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in raw_meta.split():
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        values[key] = value
    return values


def find_pending_blocks(
    text: str,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
) -> list[PendingBlock]:
    blocks: list[PendingBlock] = []
    for match in PENDING_OPEN_RE.finditer(text):
        meta = match.group("meta").strip()
        if session_id is not None or turn_id is not None:
            values = marker_meta(meta)
            if session_id is not None and values.get("session") != session_id:
                continue
            if turn_id is not None and values.get("turn") != turn_id:
                continue

        close_index = text.find(PENDING_CLOSE, match.end())
        if close_index == -1:
            blocks.append(PendingBlock(meta=meta, body="", malformed=True))
            continue
        blocks.append(
            PendingBlock(
                meta=meta,
                body=text[match.end() : close_index],
            )
        )
    return blocks


def missing_required_fields(body: str) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        pattern = re.compile(
            rf"(?m)^\s*[-*]\s*{re.escape(field)}\s*[:：]\s*(?P<value>.*)$"
        )
        match = pattern.search(body)
        if match is None:
            missing.append(field)
            continue
        value = normalize_value(match.group("value"))
        if is_placeholder(value):
            missing.append(field)
    return missing


def normalize_value(value: str) -> str:
    return value.strip().strip("`").strip()


def is_placeholder(value: str) -> bool:
    lowered = value.casefold()
    return lowered in PLACEHOLDER_VALUES or lowered.startswith("todo")


def read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def emit_user_prompt_context(message: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": message,
                }
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        if len(sys.argv) > 1 and sys.argv[1] in {"prompt", "stop"}:
            print(f"memo guard failed: {error}", file=sys.stderr)
            raise SystemExit(2)
        raise
