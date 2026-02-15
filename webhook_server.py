import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# =========================
# CONFIG
# =========================
load_dotenv("/opt/trading/.env")

SECRET = (os.getenv("WEBHOOK_SECRET") or "").strip()
TZ_NAME = (os.getenv("TZ") or "America/Montreal").strip()

JOURNAL_PATH = Path(os.getenv("JOURNAL_PATH") or "/opt/trading/journal.md")
RAW_LOG_PATH = Path(os.getenv("RAW_LOG_PATH") or "/opt/trading/logs/tv_webhooks.jsonl")
STATE_PATH = Path(os.getenv("STATE_PATH") or "/opt/trading/state/router_state.json")

ENGINE_LOCK = (os.getenv("ENGINE_LOCK") or "true").lower() in ("1", "true", "yes", "on")
TZ = ZoneInfo(TZ_NAME)

KNOWN_ENGINES = {"COINM_SHORT", "USDTM_LONG", "GOLD_CFD_LONG", "TV_TEST", "NGROK_TEST"}
AGGRESSIVE_ENGINES = {"COINM_SHORT", "USDTM_LONG"}  # lock only these

app = FastAPI()


# =========================
# FILE HELPERS
# =========================
def _now() -> datetime:
    return datetime.now(TZ)

def _ensure_paths() -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not JOURNAL_PATH.exists():
        JOURNAL_PATH.write_text("# Journal de bord trading\n\n", encoding="utf-8")
    if not RAW_LOG_PATH.exists():
        RAW_LOG_PATH.write_text("", encoding="utf-8")
    if not STATE_PATH.exists():
        STATE_PATH.write_text(
            json.dumps({"active_engine": None, "updated_at": None}, indent=2),
            encoding="utf-8",
        )

def _load_state() -> Dict[str, Any]:
    _ensure_paths()
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"active_engine": None, "updated_at": None}

def _save_state(state: Dict[str, Any]) -> None:
    _ensure_paths()
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _append_raw(payload: Dict[str, Any]) -> None:
    _ensure_paths()
    line = json.dumps({"ts": _now().isoformat(), "payload": payload}, ensure_ascii=False)
    with RAW_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def _append_journal(text: str) -> None:
    _ensure_paths()
    with JOURNAL_PATH.open("a", encoding="utf-8") as f:
        f.write(text)


# =========================
# VALIDATION
# =========================
def _require_secret(payload: Dict[str, Any]) -> None:
    if not SECRET:
        raise HTTPException(status_code=500, detail="Server misconfigured: WEBHOOK_SECRET missing")
    if payload.get("key") != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

def _get_str(payload: Dict[str, Any], k: str, default: str = "") -> str:
    v = payload.get(k, default)
    return str(v).strip()

def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    engine = _get_str(payload, "engine", "UNKNOWN")
    signal = _get_str(payload, "signal", "UNKNOWN")
    symbol = _get_str(payload, "symbol", "UNKNOWN")
    tf = _get_str(payload, "tf", "UNKNOWN")

    def num(x, default=0.0):
        try:
            return float(x)
        except Exception:
            return float(default)

    out = dict(payload)
    out["engine"] = engine
    out["signal"] = signal
    out["symbol"] = symbol
    out["tf"] = tf
    out["price"] = num(payload.get("price", 0))
    out["tp"] = num(payload.get("tp", 0))
    out["sl"] = num(payload.get("sl", 0))
    return out


# =========================
# ROUTER / POLICY
# =========================
def _engine_lock_check(engine: str) -> None:
    if not ENGINE_LOCK:
        return
    if engine not in AGGRESSIVE_ENGINES:
        return

    state = _load_state()
    active = state.get("active_engine")
    if active and active in AGGRESSIVE_ENGINES and active != engine:
        raise HTTPException(
            status_code=409,
            detail=f"Engine lock: active_engine={active}. Refusing engine={engine}.",
        )

def _set_active_engine(engine: str) -> None:
    state = _load_state()
    state["active_engine"] = engine
    state["updated_at"] = _now().isoformat()
    _save_state(state)

def _format_journal_entry(payload: Dict[str, Any]) -> str:
    dt = _now().strftime("%Y-%m-%d %H:%M")
    engine = payload["engine"]
    sig = payload["signal"]
    symbol = payload["symbol"]
    tf = payload["tf"]
    title = f"{dt} | TV Webhook | {engine} | {symbol} {tf} | {sig}"

    reason = _get_str(payload, "reason", "")
    raw = json.dumps(payload, indent=2, ensure_ascii=False)

    lines = [f"\n## {title}\n"]
    i = 1
    lines.append(f"{i}. **Signal**: `{sig}`"); i += 1
    lines.append(f"{i}. **Engine**: `{engine}`"); i += 1
    lines.append(f"{i}. **Symbol/TF**: `{symbol}` / `{tf}`"); i += 1
    lines.append(f"{i}. **Price**: `{payload.get('price')}`"); i += 1
    lines.append(f"{i}. **TP**: `{payload.get('tp')}`"); i += 1
    lines.append(f"{i}. **SL**: `{payload.get('sl')}`"); i += 1
    if reason:
        lines.append(f"{i}. **Reason**: {reason}"); i += 1

    lines.append(f"{i}. **Payload brut**:\n```json\n{raw}\n```")
    return "\n".join(lines) + "\n"


# =========================
# ENDPOINT
# =========================
@app.post("/tv")
async def tv_webhook(req: Request):
    try:
        payload = await req.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    _append_raw(payload)          # log brut
    _require_secret(payload)      # sécurité
    p = _normalize_payload(payload)

    # engine sanity
    if p["engine"] not in KNOWN_ENGINES and p["engine"] != "UNKNOWN":
        p["engine"] = "UNKNOWN"

    _engine_lock_check(p["engine"])

    if p["engine"] in AGGRESSIVE_ENGINES:
        _set_active_engine(p["engine"])

    _append_journal(_format_journal_entry(p))
    return {"ok": True}
