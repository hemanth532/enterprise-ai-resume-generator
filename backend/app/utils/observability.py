import asyncio
import json
from datetime import datetime
from pathlib import Path

LOG_ROOT = Path(__file__).resolve().parents[1] / "logs"
SESSION_LOG_FILES: dict[str, Path] = {}


def _ensure_log_dir(session_id: str) -> Path:
    path = LOG_ROOT / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_session_log_path(session_id: str) -> Path:
    if session_id not in SESSION_LOG_FILES:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"pipeline-{timestamp}.json"
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
