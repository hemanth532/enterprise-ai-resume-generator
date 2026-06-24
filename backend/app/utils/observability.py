import asyncio
import json
from datetime import datetime
from pathlib import Path

LOG_ROOT = Path(__file__).resolve().parents[1] / "logs"
SESSION_LOG_FILES: dict[str, Path] = {}


def _ensure_log_dir(session_id: str) -> Path:
    # Ensure the root logs directory exists; do not create per-session subfolders.
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    return LOG_ROOT


def _build_session_log_path(session_id: str) -> Path:
    def _sanitize_session_id(sid: str) -> str:
        # Keep only alnum, dash and underscore; replace others with underscore. Limit length.
        safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in sid)
        return safe[:64]

    if session_id not in SESSION_LOG_FILES:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        safe_id = _sanitize_session_id(session_id)
        filename = f"pipeline-{safe_id}-{timestamp}.json"
        SESSION_LOG_FILES[session_id] = _ensure_log_dir(session_id) / filename
    return SESSION_LOG_FILES[session_id]


def _write_json_file(path: Path, payload: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


async def write_step_observability(session_id: str, step: str, status: str, detail: str) -> None:
    log_path = _build_session_log_path(session_id)
    event = {
        "session_id": session_id,
        "step": step,
        "status": status,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    def _append_event() -> None:
        if log_path.exists():
            with log_path.open("r", encoding="utf-8") as handle:
                existing = json.load(handle)
            if isinstance(existing, list):
                existing.append(event)
            else:
                existing = [existing, event]
        else:
            existing = [event]
        _write_json_file(log_path, existing)

    await asyncio.to_thread(_append_event)
