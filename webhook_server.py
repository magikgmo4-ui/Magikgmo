import os
import json
import math
import time
import html
import pathlib
import urllib.request
import urllib.parse
import requests

PERF_URL = os.getenv("PERF_URL", "http://127.0.0.1:8010/perf/event")

def perf_open(engine: str, symbol: str, side: str, entry: float, stop: float, qty: float, risk_usd: float, meta: dict | None = None):
    payload = {
        "type": "OPEN",
        "engine": engine,
        "symbol": symbol,
        "side": side,
        "entry": float(entry),
        "stop": float(stop),
        "qty": float(qty),
        "risk_usd": float(risk_usd),
        "meta": meta or {}
    }
    try:
        requests.post(PERF_URL, json=payload, timeout=2)
    except Exception:
        # perf est optionnel: ne jamais casser le webhook
        pass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse

try:
    from dotenv import load_dotenv
    load_dotenv("/opt/trading/.env")
except Exception:
    pass


APP_TITLE = "TV Webhook Server"
BASE_DIR = pathlib.Path("/opt/trading")
STATE_DIR = BASE_DIR / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

JOURNAL_PATH = BASE_DIR / "journal.md"
EVENTS_JSONL = STATE_DIR / "events.jsonl"
ROUTER_STATE = STATE_DIR / "router_state.json"
RISK_CONFIG = STATE_DIR / "risk_config.json"

TV_WEBHOOK_KEY = os.getenv("TV_WEBHOOK_KEY", "").strip()
OPS_ADMIN_KEY = os.getenv("OPS_ADMIN_KEY", "").strip()

TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "0").strip() in ("1", "true", "True", "yes", "YES")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Inactivity alert (used by dashboard "stale" logic)
INACTIVITY_SEC_DEFAULT = int(os.getenv("INACTIVITY_SEC", "3600"))  # 1h

# Engines
AGGRESSIVE_ENGINES = {"COINM_SHORT", "USDTM_LONG"}  # lock enforced across these
ALL_ENGINES = {"COINM_SHORT", "USDTM_LONG", "GOLD_CFD_LONG", "TV_TEST", "NGROK_TEST"}

app = FastAPI(title=APP_TITLE)


# -------------------- Utils --------------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

def safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def read_json_file(path: pathlib.Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json_file(path: pathlib.Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

def append_jsonl(path: pathlib.Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def ensure_router_state() -> Dict[str, Any]:
    st = read_json_file(ROUTER_STATE, {})
    if not isinstance(st, dict):
        st = {}
    st.setdefault("active_engine", None)
    st.setdefault("updated_at", None)
    write_json_file(ROUTER_STATE, st)
    return st

def set_router_state(active_engine: Optional[str]) -> Dict[str, Any]:
    st = ensure_router_state()
    st["active_engine"] = active_engine
    st["updated_at"] = iso_utc(utc_now())
    write_json_file(ROUTER_STATE, st)
    return st

def telegram_send(text: str) -> bool:
    if not TELEGRAM_ENABLED:
        return False
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": "true"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            _ = resp.read()
        return True
    except Exception:
        return False


# -------------------- Risk --------------------
def load_risk_config() -> Dict[str, Any]:
    cfg = read_json_file(RISK_CONFIG, {})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.setdefault("accounts", {})
    cfg.setdefault("gold_cfd", {})
    return cfg

def _get_equity_and_risk_pct(acct: dict) -> Tuple[float, float]:
    # equity can be "equity" or "equity_usd"
    equity = float(acct.get("equity_usd", acct.get("equity", 0)) or 0)

    # risk_pct can be 0.01 (1%), or 1 (1%), or 1.0 (1%), or 2 (2%)
    rp = acct.get("risk_pct", 0)
    try:
        rp = float(rp)
    except Exception:
        rp = 0.0

    if rp <= 0:
        risk_pct = 0.0
    elif rp <= 1.0:
        # treat as fraction
        risk_pct = rp
    else:
        # treat as percent
        risk_pct = rp / 100.0

    return equity, risk_pct

def round_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    return math.floor(x / step + 1e-12) * step

def risk_quote(engine: str, price: float, sl: float, tp: float) -> Dict[str, Any]:
    cfg = load_risk_config()
    accounts = cfg.get("accounts", {}) or {}
    acct = accounts.get(engine, {}) or {}

    equity, risk_pct = _get_equity_and_risk_pct(acct)
    risk_usd = equity * risk_pct

    distance = abs(price - sl)
    if distance <= 0 or risk_usd <= 0:
        return {
            "ok": True,
            "type": "LINEAR_FALLBACK",
            "risk_usd": round(risk_usd, 6),
            "risk_real_usd": 0,
            "distance": round(distance, 6),
            "qty": 0
        }

    # Default linear: PnL per 1 qty per $ move = 1 (fallback)
    qty = risk_usd / distance

    if engine == "GOLD_CFD_LONG":
        min_units = safe_float(acct.get("min_units", acct.get("min_qty", 0.1))) or 0.1
        units_step = safe_float(acct.get("units_step", acct.get("qty_step", 0.1))) or 0.1
        qty = max(qty, min_units)
        qty = round_step(qty, units_step)
        qty = round(qty, 6)
        risk_real = qty * distance
        return {
            "ok": True,
            "type": "GOLD_CFD_OZ" if (cfg.get("gold_cfd", {}) or {}).get("units_are_oz", True) else "GOLD_CFD",
            "risk_usd": round(risk_usd, 6),
            "risk_real_usd": round(risk_real, 6),
            "distance": round(distance, 6),
            "qty": qty
        }

    # COINM/USDTM: keep generic sizing (you can later plug real contract specs)
    min_qty = safe_float(acct.get("min_qty", 0.001)) or 0.001
    qty_step = safe_float(acct.get("qty_step", 0.001)) or 0.001
    qty = max(qty, min_qty)
    qty = round_step(qty, qty_step)
    qty = round(qty, 6)
    risk_real = qty * distance
    return {
        "ok": True,
        "type": "LINEAR_FALLBACK",
        "risk_usd": round(risk_usd, 6),
        "risk_real_usd": round(risk_real, 6),
        "distance": round(distance, 6),
        "qty": qty
    }


# -------------------- Events / Metrics --------------------
def read_events(limit: int = 50) -> List[Dict[str, Any]]:
    if limit <= 0:
        return []
    if not EVENTS_JSONL.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        lines = EVENTS_JSONL.read_text(encoding="utf-8").splitlines()
        for ln in lines[-limit:]:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
        return out
    except Exception:
        return []

def parse_ts(evt: Dict[str, Any]) -> Optional[datetime]:
    ts = evt.get("_ts")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

def metrics(window_min: int = 60, limit: int = 50, inactivity_sec: int = INACTIVITY_SEC_DEFAULT) -> Dict[str, Any]:
    evs = read_events(limit=limit)
    now = utc_now()

    buy = 0
    sell = 0
    last_ts: Optional[datetime] = None

    # Events per minute (last window_min)
    cutoff = now - timedelta(minutes=max(1, window_min))
    per_min: Dict[str, int] = {}

    # Last per engine
    last_per_engine: Dict[str, Dict[str, Any]] = {}

    for e in evs:
        sig = (e.get("signal") or "").upper()
        if sig == "BUY":
            buy += 1
        elif sig == "SELL":
            sell += 1

        ts = parse_ts(e)
        if ts and (last_ts is None or ts > last_ts):
            last_ts = ts

        if ts and ts >= cutoff:
            k = ts.strftime("%Y-%m-%dT%H:%M")
            per_min[k] = per_min.get(k, 0) + 1

        eng = (e.get("engine") or "").strip()
        if eng:
            prev = last_per_engine.get(eng)
            if not prev:
                last_per_engine[eng] = e
            else:
                pts = parse_ts(prev)
                if ts and pts and ts > pts:
                    last_per_engine[eng] = e
                elif ts and not pts:
                    last_per_engine[eng] = e

    last_age_sec = None
    if last_ts:
        last_age_sec = int((now - last_ts).total_seconds())

    # Build engine status list
    engines_rows = []
    for eng, e in sorted(last_per_engine.items(), key=lambda x: x[0]):
        ts = parse_ts(e)
        age = int((now - ts).total_seconds()) if ts else None
        status = "OK" if (age is not None and age <= inactivity_sec) else "STALE"
        engines_rows.append({
            "engine": eng,
            "status": status,
            "signal": e.get("signal"),
            "symbol": e.get("symbol"),
            "tf": e.get("tf"),
            "price": e.get("price"),
            "age_sec": age,
            "reason": e.get("reason"),
        })

    return {
        "ok": True,
        "limit": limit,
        "window_min": window_min,
        "total": len(evs),
        "buy": buy,
        "sell": sell,
        "last_event_age_sec": last_age_sec,
        "events_per_min": per_min,
        "last_per_engine": engines_rows,
    }


# -------------------- Webhook --------------------
def _is_local_client(req: Request) -> bool:
    try:
        host = (req.client.host or "").strip()
    except Exception:
        host = ""
    return host in ("127.0.0.1", "::1")

def require_key(req: Request, payload: Dict[str, Any]) -> None:
    """Validate secret key.
    - If TV_WEBHOOK_KEY is set: require exact match.
    - If TV_WEBHOOK_KEY is NOT set: allow only localhost clients (dev mode).
    """
    if not TV_WEBHOOK_KEY:
        if not _is_local_client(req):
            raise HTTPException(status_code=403, detail="Missing TV_WEBHOOK_KEY (set env) — remote access blocked")
        return
    got = (payload.get("key") or "").strip()
    if got != TV_WEBHOOK_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret")

def enforce_lock(engine: str) -> None:
    st = ensure_router_state()
    active = st.get("active_engine")
    if not active:
        return
    if active == engine:
        return
    # enforce lock only across aggressive engines
    if engine in AGGRESSIVE_ENGINES and active in AGGRESSIVE_ENGINES:
        raise HTTPException(status_code=409, detail=f"Engine locked: active_engine={active}")

def write_journal_entry(evt: Dict[str, Any]) -> None:
    ts_local = datetime.now().strftime("%Y-%m-%d %H:%M")
    engine = evt.get("engine", "")
    signal = evt.get("signal", "")
    symbol = evt.get("symbol", "")
    tf = evt.get("tf", "")
    price = evt.get("price", 0)
    tp = evt.get("tp", 0)
    sl = evt.get("sl", 0)
    reason = evt.get("reason", "")

    entry = []
    entry.append(f"\n## {ts_local} | TV Webhook | {engine} | {symbol} {tf} | {signal}\n")
    entry.append(f"1. **Signal**: `{signal}`\n")
    entry.append(f"2. **Engine**: `{engine}`\n")
    entry.append(f"3. **Symbol/TF**: `{symbol}` / `{tf}`\n")
    entry.append(f"4. **Price**: `{price}`\n")
    entry.append(f"5. **TP**: `{tp}`\n")
    entry.append(f"6. **SL**: `{sl}`\n")
    if reason != "":
        entry.append(f"7. **Reason**: {reason}\n")
        entry.append("8. **Payload brut**:\n")
    else:
        entry.append("7. **Payload brut**:\n")

    entry.append("```json\n")
    entry.append(json.dumps(evt, ensure_ascii=False, indent=2))
    entry.append("\n```\n")

    with JOURNAL_PATH.open("a", encoding="utf-8") as f:
        f.write("".join(entry))


@app.post("/tv")
async def tv_webhook(req: Request):
    payload = await req.json()

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON must be object")
    require_key(req, payload)
    engine = (payload.get("engine") or "").strip()
    signal = (payload.get("signal") or "").strip().upper()
    symbol = (payload.get("symbol") or "").strip()
    tf = str(payload.get("tf") or "").strip()
    price = safe_float(payload.get("price"))
    tp = safe_float(payload.get("tp"))
    sl = safe_float(payload.get("sl"))
    reason = (payload.get("reason") or "").strip()

    if engine == "":
        raise HTTPException(status_code=400, detail="Missing engine")
    if engine not in ALL_ENGINES and engine not in {"COINM_SHORT", "USDTM_LONG", "GOLD_CFD_LONG"}:
        # allow future engines but keep sane
        pass
    if signal not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="signal must be BUY or SELL")

    enforce_lock(engine)

    # If engine is aggressive, set lock to it when first used
    if engine in AGGRESSIVE_ENGINES:
        st = ensure_router_state()
        if not st.get("active_engine"):
            set_router_state(engine)
    # --- RISK SIZING (quote) ---
    q = risk_quote(engine, price=price, sl=sl, tp=tp) if (price and sl) else None
    if not q:
        raise HTTPException(status_code=400, detail="Missing/invalid price or sl for risk sizing")

    # Guard: never ledger trades with qty/risk = 0
    if (not q.get("qty")) or ((q.get("risk_real_usd") or 0) <= 0 and (q.get("risk_usd") or 0) <= 0):
        raise HTTPException(status_code=400, detail="Risk quote invalid (qty/risk is 0)")

    side = "LONG" if signal == "BUY" else "SHORT"
    risk_for_perf = q.get("risk_real_usd") or q.get("risk_usd") or 0.0

    # --- PERF: OPEN trade ledger (non-bloquant) ---
    perf_open(
        engine=engine,
        symbol=symbol,
        side=side,
        entry=price,
        stop=sl,
        qty=q["qty"],
        risk_usd=risk_for_perf,
        meta={"tf": tf, "tp": tp, "reason": reason, "src": "/tv"}
    )

    evt = {
        "key": payload.get("key", None),
        "engine": engine,
        "signal": signal,
        "symbol": symbol,
        "tf": tf,
        "price": price,
        "tp": tp,
        "sl": sl,
        "reason": reason,
        "_ts": iso_utc(utc_now()),
        "_ip": req.client.host if req.client else None,
        "qty": q["qty"],
        "risk_usd": q.get("risk_usd", None),
        "risk_real_usd": q.get("risk_real_usd", None),
}

    append_jsonl(EVENTS_JSONL, evt)
    write_journal_entry(evt)

    # Telegram notify (simple, readable)
    if TELEGRAM_ENABLED:
        # include sizing quote if possible
        q = risk_quote(engine, price=price, sl=sl, tp=tp) if (price and sl) else None
        qty_txt = ""
        if q and q.get("qty"):
            qty_txt = f"\nqty: {q['qty']} | risk_usd: {q.get('risk_usd')}"
        msg = f"{signal} {symbol} {tf}\nengine: {engine}\nprice: {price} | tp: {tp} | sl: {sl}\nreason: {reason}{qty_txt}"
        telegram_send(msg)

    return {"ok": True}


# -------------------- API --------------------
@app.get("/api/state")
def api_state():
    st = ensure_router_state()
    return {
        "ok": True,
        "active_engine": st.get("active_engine"),
        "updated_at": st.get("updated_at"),
        "ts": iso_utc(utc_now()),
    }

@app.get("/api/events")
def api_events(limit: int = 50):
    evs = read_events(limit=limit)
    return {"ok": True, "count": len(evs), "events": evs}

@app.get("/api/metrics")
def api_metrics(limit: int = 50, window_min: int = 60, inactivity_sec: int = INACTIVITY_SEC_DEFAULT):
    return metrics(window_min=window_min, limit=limit, inactivity_sec=inactivity_sec)

@app.get("/api/risk/quote")
def api_risk_quote(engine: str, price: float, sl: float, tp: float):
    q = risk_quote(engine=engine, price=price, sl=sl, tp=tp)
    return {"ok": True, "quote": q}

@app.post("/api/reset_lock")
async def api_reset_lock(req: Request):
    body = await req.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON must be object")
    k = (body.get("ops_key") or "").strip()
    if not OPS_ADMIN_KEY:
        raise HTTPException(status_code=500, detail="OPS_ADMIN_KEY not set")
    if k != OPS_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    st = set_router_state(None)
    return {"ok": True, "state": st}


# -------------------- Dashboard (Trading Ops) --------------------
DASH_HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>TV Webhook — Trading Ops</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; background:#0b1020; color:#e6e8ee; }
  .wrap { padding: 22px 26px; }
  h1 { margin: 0 0 8px; font-size: 28px; }
  .sub { opacity:.85; font-size: 14px; display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
  .pill { background:#121a33; border:1px solid #24315c; padding: 6px 10px; border-radius: 999px; }
  .grid { margin-top: 18px; display:grid; grid-template-columns: 520px 1fr; gap:18px; }
  .card { background:#0f1833; border:1px solid #22305a; border-radius: 18px; padding: 16px; box-shadow: 0 12px 30px rgba(0,0,0,.25); }
  .row { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
  .kpi { display:flex; gap:12px; margin-top: 12px; flex-wrap:wrap; }
  .k { background:#0b132a; border:1px solid #22305a; border-radius: 14px; padding: 12px 14px; min-width: 130px; }
  .k .t { opacity:.7; font-size: 12px; }
  .k .v { font-size: 22px; margin-top: 6px; }
  input { background:#0b132a; border:1px solid #22305a; color:#e6e8ee; padding:10px 12px; border-radius: 12px; outline:none; width: 260px; }
  button { background:#1f3bff; border:0; color:white; padding:10px 12px; border-radius: 12px; cursor:pointer; font-weight:600; }
  button:hover { filter: brightness(1.05); }
  table { width:100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }
  th, td { text-align:left; padding: 10px 8px; border-bottom: 1px solid #22305a; }
  th { opacity:.8; font-weight:600; }
  .badge { display:inline-block; padding: 4px 10px; border-radius: 999px; font-weight:700; font-size: 12px; }
  .buy { background: rgba(34,197,94,.18); color:#22c55e; border:1px solid rgba(34,197,94,.35); }
  .sell { background: rgba(239,68,68,.18); color:#ef4444; border:1px solid rgba(239,68,68,.35); }
  .ok { background: rgba(34,197,94,.18); color:#22c55e; border:1px solid rgba(34,197,94,.35); }
  .stale { background: rgba(245,158,11,.18); color:#f59e0b; border:1px solid rgba(245,158,11,.35); }
  .muted { opacity:.72; }
  .small { font-size: 12px; opacity:.75; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
</style>
</head>
<body>
<div class="wrap">
  <h1>TV Webhook — Trading Ops</h1>
  <div class="sub">
    <span class="pill">Auto refresh ~2s</span>
    <span class="pill">Data: last <span id="limit">50</span> events</span>
    <span class="pill">Inactivity alert: <span id="inact">1h</span></span>
    <span class="pill">Endpoints: <span class="mono">/api/state</span> <span class="mono">/api/events</span> <span class="mono">/api/metrics</span></span>
  </div>

  <div class="grid">
    <div class="card">
      <div class="row">
        <span class="badge stale" id="stateBadge">STATE</span>
        <span class="pill mono">active_engine: <span id="active_engine">-</span></span>
        <span class="pill mono">updated_at: <span id="updated_at">-</span></span>
      </div>

      <div class="row" style="margin-top:12px;">
        <input id="opsKey" placeholder="OPS_ADMIN_KEY"/>
        <button id="resetBtn">Reset Lock</button>
      </div>

      <div class="kpi">
        <div class="k"><div class="t">Total (limit)</div><div class="v" id="k_total">-</div></div>
        <div class="k"><div class="t">BUY</div><div class="v" id="k_buy">-</div></div>
        <div class="k"><div class="t">SELL</div><div class="v" id="k_sell">-</div></div>
        <div class="k"><div class="t">Last event age</div><div class="v" id="k_age">-</div></div>
      </div>

      <div style="margin-top:14px;" class="muted">Events per minute (last 60 min)</div>
      <div class="pill mono" style="margin-top:8px; overflow:auto; max-height: 120px;" id="perMin">-</div>

      <div style="margin-top:14px;" class="muted">Last signal per engine</div>
      <table id="engTable">
        <thead>
          <tr>
            <th>Engine</th><th>Status</th><th>Signal</th><th>Symbol</th><th>TF</th><th>Price</th><th>Age</th><th>Reason</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>

      <div class="small mono" style="margin-top:10px;">last refresh: <span id="refTs">-</span></div>
    </div>

    <div class="card">
      <div class="row">
        <span class="badge stale">RECENT</span>
        <span class="pill mono">limit=<span id="limit2">50</span></span>
      </div>
      <table id="evTable">
        <thead>
          <tr>
            <th>Time (UTC)</th><th>Engine</th><th>Signal</th><th>Symbol</th><th>TF</th><th>Price</th><th>TP</th><th>SL</th><th>Reason</th><th>IP</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const LIMIT = 50;
const WINDOW_MIN = 60;
const INACT_SEC = 3600;

document.getElementById("limit").textContent = LIMIT;
document.getElementById("limit2").textContent = LIMIT;
document.getElementById("inact").textContent = "1h";

function ageFmt(sec){
  if(sec === null || sec === undefined) return "-";
  if(sec < 60) return sec + "s";
  if(sec < 3600) return Math.floor(sec/60) + "m";
  return Math.floor(sec/3600) + "h";
}

async function fetchJson(url){
  const r = await fetch(url, {cache:"no-store"});
  return await r.json();
}

function esc(x){
  if(x===null||x===undefined) return "";
  return String(x)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function refresh(){
  try{
    const [st, evs, met] = await Promise.all([
      fetchJson("/api/state"),
      fetchJson(`/api/events?limit=${LIMIT}`),
      fetchJson(`/api/metrics?limit=${LIMIT}&window_min=${WINDOW_MIN}&inactivity_sec=${INACT_SEC}`)
    ]);

    document.getElementById("active_engine").textContent = st.active_engine || "-";
    document.getElementById("updated_at").textContent = st.updated_at || "-";

    document.getElementById("k_total").textContent = met.total;
    document.getElementById("k_buy").textContent = met.buy;
    document.getElementById("k_sell").textContent = met.sell;
    document.getElementById("k_age").textContent = ageFmt(met.last_event_age_sec);

    // per minute compact
    const keys = Object.keys(met.events_per_min || {}).sort();
    let per = keys.slice(-30).map(k => `${k}: ${met.events_per_min[k]}`).join("\n");
    document.getElementById("perMin").textContent = per || "-";

    // engine table
    const tbody = document.querySelector("#engTable tbody");
    tbody.innerHTML = "";
    (met.last_per_engine || []).forEach(r => {
      const tr = document.createElement("tr");
      const status = r.status || "STALE";
      const stBadge = status === "OK" ? "ok" : "stale";
      const sig = (r.signal||"").toUpperCase();
      const sigBadge = sig === "BUY" ? "buy" : (sig === "SELL" ? "sell" : "stale");
      tr.innerHTML = `
        <td class="mono">${esc(r.engine)}</td>
        <td><span class="badge ${stBadge}">${esc(status)}</span></td>
        <td><span class="badge ${sigBadge}">${esc(sig)}</span></td>
        <td class="mono">${esc(r.symbol)}</td>
        <td class="mono">${esc(r.tf)}</td>
        <td class="mono">${esc(r.price)}</td>
        <td class="mono">${ageFmt(r.age_sec)}</td>
        <td class="mono">${esc(r.reason)}</td>
      `;
      tbody.appendChild(tr);
    });

    // events table
    const evBody = document.querySelector("#evTable tbody");
    evBody.innerHTML = "";
    (evs.events || []).slice().reverse().forEach(e => {
      const tr = document.createElement("tr");
      const sig = (e.signal||"").toUpperCase();
      const sigBadge = sig === "BUY" ? "buy" : (sig === "SELL" ? "sell" : "stale");
      tr.innerHTML = `
        <td class="mono">${esc(e._ts)}</td>
        <td class="mono">${esc(e.engine)}</td>
        <td><span class="badge ${sigBadge}">${esc(sig)}</span></td>
        <td class="mono">${esc(e.symbol)}</td>
        <td class="mono">${esc(e.tf)}</td>
        <td class="mono">${esc(e.price)}</td>
        <td class="mono">${esc(e.tp)}</td>
        <td class="mono">${esc(e.sl)}</td>
        <td class="mono">${esc(e.reason)}</td>
        <td class="mono">${esc(e._ip)}</td>
      `;
      evBody.appendChild(tr);
    });

    document.getElementById("refTs").textContent = new Date().toISOString();
  } catch (e){
    // ignore
  }
}

document.getElementById("resetBtn").addEventListener("click", async () => {
  const k = document.getElementById("opsKey").value.trim();
  if(!k) return;
  try{
    const r = await fetch("/api/reset_lock", {
      method:"POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ops_key: k})
    });
    await r.json();
  } catch(e){}
  refresh();
});

refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""

@app.get("/dash", response_class=HTMLResponse)
def dash():
    return HTMLResponse(content=DASH_HTML)
