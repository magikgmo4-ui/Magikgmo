#!/usr/bin/env python3
import os, json, time, sqlite3, uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("PERF_DB_PATH", os.path.join(APP_DIR, "perf.db"))

# ---- Telegram (optional) ----
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
NO_ACTIVITY_MIN = int(os.getenv("PERF_NO_ACTIVITY_MIN", "30"))
DD_ALERT_PCT = float(os.getenv("PERF_DD_ALERT_PCT", "5.0"))  # % global
ENGINE_DD_ALERT_PCT = float(os.getenv("PERF_ENGINE_DD_ALERT_PCT", "7.0"))  # % engine

EQUITY0 = float(os.getenv("PERF_EQUITY0", "10000"))  # simulated start equity

app = FastAPI(title="perf", version="1.0")

# ---------------- Models ----------------
class PerfEvent(BaseModel):
    type: str = Field(..., description="OPEN|CLOSE|UPDATE")
    ts: Optional[str] = Field(None, description="ISO8601, default now")
    engine: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = Field(None, description="LONG|SHORT")
    entry: Optional[float] = None
    stop: Optional[float] = None
    qty: Optional[float] = None
    risk_usd: Optional[float] = None
    trade_id: Optional[str] = None
    exit: Optional[float] = None
    mark: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

# ---------------- DB ----------------
def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY,
      ts TEXT NOT NULL,
      type TEXT NOT NULL,
      engine TEXT,
      symbol TEXT,
      trade_id TEXT,
      payload TEXT NOT NULL
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
      trade_id TEXT PRIMARY KEY,
      engine TEXT NOT NULL,
      symbol TEXT NOT NULL,
      side TEXT NOT NULL,
      entry_ts TEXT NOT NULL,
      entry REAL NOT NULL,
      stop REAL NOT NULL,
      qty REAL NOT NULL,
      risk_usd REAL NOT NULL,
      exit_ts TEXT,
      exit REAL,
      status TEXT NOT NULL DEFAULT 'OPEN',
      pnl_real REAL NOT NULL DEFAULT 0.0,
      r_real REAL NOT NULL DEFAULT 0.0
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_engine ON trades(engine)")
    con.commit()
    con.close()

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()

def insert_event(ev: PerfEvent):
    con = db()
    cur = con.cursor()
    eid = "E_" + uuid.uuid4().hex[:16]
    ts = ev.ts or now_iso()
    payload = ev.model_dump()
    cur.execute(
        "INSERT INTO events(id, ts, type, engine, symbol, trade_id, payload) VALUES(?,?,?,?,?,?,?)",
        (eid, ts, ev.type, ev.engine, ev.symbol, ev.trade_id, json.dumps(payload, ensure_ascii=False))
    )
    con.commit()
    con.close()
    return eid, ts

def create_trade_from_open(ev: PerfEvent) -> str:
    if not all([ev.engine, ev.symbol, ev.side, ev.entry is not None, ev.stop is not None, ev.qty is not None, ev.risk_usd is not None]):
        raise HTTPException(400, "OPEN requires engine,symbol,side,entry,stop,qty,risk_usd")
    trade_id = ev.trade_id or f"T_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{ev.engine}_{uuid.uuid4().hex[:6]}"
    con = db()
    cur = con.cursor()
    cur.execute("""
      INSERT INTO trades(trade_id,engine,symbol,side,entry_ts,entry,stop,qty,risk_usd,status)
      VALUES(?,?,?,?,?,?,?,?,?,'OPEN')
    """, (trade_id, ev.engine, ev.symbol, ev.side, ev.ts or now_iso(), float(ev.entry), float(ev.stop), float(ev.qty), float(ev.risk_usd)))
    con.commit()
    con.close()
    return trade_id

def close_trade(ev: PerfEvent):
    if not ev.trade_id or ev.exit is None:
        raise HTTPException(400, "CLOSE requires trade_id and exit")
    con = db()
    cur = con.cursor()
    tr = cur.execute("SELECT * FROM trades WHERE trade_id=?", (ev.trade_id,)).fetchone()
    if not tr:
        con.close()
        raise HTTPException(404, "trade_id not found")
    if tr["status"] != "OPEN":
        con.close()
        raise HTTPException(409, "trade already closed")

    entry = float(tr["entry"])
    qty = float(tr["qty"])
    risk_usd = float(tr["risk_usd"])
    side = tr["side"]

    exit_px = float(ev.exit)
    pnl = (exit_px - entry) * qty if side == "LONG" else (entry - exit_px) * qty
    r = pnl / risk_usd if risk_usd != 0 else 0.0

    cur.execute("""
      UPDATE trades
      SET exit_ts=?, exit=?, status=?, pnl_real=?, r_real=?
      WHERE trade_id=?
    """, (ev.ts or now_iso(), exit_px, "CLOSED", pnl, r, ev.trade_id))
    con.commit()
    con.close()

# ---------------- Analytics ----------------
def get_last_event_ts() -> Optional[str]:
    con = db()
    row = con.execute("SELECT ts FROM events ORDER BY ts DESC LIMIT 1").fetchone()
    con.close()
    return row["ts"] if row else None

def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def equity_series(include_open_live: bool = False, marks: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    # Equity based on CLOSED trades only (default)
    con = db()
    rows = con.execute("SELECT exit_ts, pnl_real FROM trades WHERE status='CLOSED' ORDER BY exit_ts").fetchall()
    con.close()

    eq = EQUITY0
    series = [{"ts": None, "equity": eq}]
    for r in rows:
        eq += float(r["pnl_real"])
        series.append({"ts": r["exit_ts"], "equity": eq})

    if include_open_live and marks:
        # add current open PnL as a last point
        con = db()
        open_rows = con.execute("SELECT trade_id, side, entry, qty FROM trades WHERE status='OPEN'").fetchall()
        con.close()
        live = 0.0
        for tr in open_rows:
            tid = tr["trade_id"]
            if tid not in marks:
                continue
            entry = float(tr["entry"])
            qty = float(tr["qty"])
            side = tr["side"]
            mark = float(marks[tid])
            live += (mark - entry) * qty if side == "LONG" else (entry - mark) * qty
        series.append({"ts": now_iso(), "equity": eq + live, "note": "includes_open_live"})
    return series

def max_drawdown(series: List[Dict[str, Any]]) -> Dict[str, float]:
    peak = -1e18
    max_dd = 0.0
    max_dd_pct = 0.0
    for p in series:
        eq = float(p["equity"])
        peak = max(peak, eq)
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0
    return {"max_dd": max_dd, "max_dd_pct": max_dd_pct}

def kpis() -> Dict[str, Any]:
    con = db()
    trades = con.execute("SELECT * FROM trades").fetchall()
    con.close()

    total = len(trades)
    closed = [t for t in trades if t["status"] == "CLOSED"]
    open_tr = [t for t in trades if t["status"] == "OPEN"]

    wins = [t for t in closed if float(t["pnl_real"]) > 0]
    winrate = (len(wins) / len(closed) * 100.0) if closed else 0.0
    avg_r = (sum(float(t["r_real"]) for t in closed) / len(closed)) if closed else 0.0
    pnl = sum(float(t["pnl_real"]) for t in closed)

    open_risk = {}
    for t in open_tr:
        open_risk[t["engine"]] = open_risk.get(t["engine"], 0.0) + float(t["risk_usd"])

    eq = equity_series(include_open_live=False)
    dd = max_drawdown(eq)

    # engine KPIs
    engines = {}
    for t in trades:
        e = t["engine"]
        engines.setdefault(e, {"total":0, "closed":0, "wins":0, "pnl":0.0, "avg_r":0.0, "rs":[], "open_risk":0.0})
        engines[e]["total"] += 1
        if t["status"] == "OPEN":
            engines[e]["open_risk"] += float(t["risk_usd"])
        else:
            engines[e]["closed"] += 1
            engines[e]["pnl"] += float(t["pnl_real"])
            engines[e]["rs"].append(float(t["r_real"]))
            if float(t["pnl_real"]) > 0:
                engines[e]["wins"] += 1

    for e, d in engines.items():
        d["winrate"] = (d["wins"]/d["closed"]*100.0) if d["closed"] else 0.0
        d["avg_r"] = (sum(d["rs"])/len(d["rs"])) if d["rs"] else 0.0
        d.pop("rs", None)

    return {
        "equity0": EQUITY0,
        "total_trades": total,
        "closed_trades": len(closed),
        "open_trades": len(open_tr),
        "winrate_pct": winrate,
        "avg_r": avg_r,
        "pnl_realized": pnl,
        "equity_last": eq[-1]["equity"],
        "max_dd": dd["max_dd"],
        "max_dd_pct": dd["max_dd_pct"],
        "open_risk_by_engine": open_risk,
        "engines": engines,
        "last_event_ts": get_last_event_ts(),
    }

# ---------------- Telegram sender ----------------
def telegram_send(text: str):
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        return
    import urllib.request, urllib.parse
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=10).read()
    except Exception:
        pass

# ---------------- Background monitors ----------------
_last_no_activity_sent = 0.0
_last_dd_sent = 0.0

def monitors_loop():
    global _last_no_activity_sent, _last_dd_sent
    while True:
        time.sleep(10)
        # no activity
        ts = get_last_event_ts()
        if ts:
            dt = parse_iso(ts)
            mins = (datetime.now(dt.tzinfo) - dt).total_seconds() / 60.0
            if mins > NO_ACTIVITY_MIN and (time.time() - _last_no_activity_sent) > 900:
                telegram_send(f"⚠️ PERF: no activity {int(mins)}m — check Pine/ngrok/tv-webhook")
                _last_no_activity_sent = time.time()

        # drawdown
        info = kpis()
        dd_pct = float(info["max_dd_pct"])
        if dd_pct > DD_ALERT_PCT and (time.time() - _last_dd_sent) > 900:
            telegram_send(f"🧯 PERF: global DD {dd_pct:.2f}% > {DD_ALERT_PCT:.2f}%")
            _last_dd_sent = time.time()

@app.on_event("startup")
def startup():
    init_db()
    import threading
    t = threading.Thread(target=monitors_loop, daemon=True)
    t.start()

# ---------------- Routes ----------------
@app.post("/perf/event")
def perf_event(ev: PerfEvent):
    ev.type = ev.type.upper().strip()
    if ev.type not in ("OPEN","CLOSE","UPDATE"):
        raise HTTPException(400, "type must be OPEN|CLOSE|UPDATE")

    # store event first
    eid, ts = insert_event(ev)

    if ev.type == "OPEN":
        trade_id = create_trade_from_open(ev)
        return {"ok": True, "event_id": eid, "trade_id": trade_id, "ts": ts}

    if ev.type == "CLOSE":
        close_trade(ev)
        return {"ok": True, "event_id": eid, "trade_id": ev.trade_id, "ts": ts}

    # UPDATE: stored only for now
    return {"ok": True, "event_id": eid, "ts": ts}

@app.get("/perf/summary")
def perf_summary():
    return kpis()

@app.get("/perf/equity")
def perf_equity():
    series = equity_series(include_open_live=False)
    return {"series": series, "dd": max_drawdown(series)}

@app.get("/perf/open")
def perf_open():
    con = db()
    rows = con.execute("""
        SELECT trade_id, engine, symbol, side, entry_ts, entry, stop, qty, risk_usd
        FROM trades WHERE status='OPEN'
        ORDER BY entry_ts DESC
    """).fetchall()
    con.close()
    return {"open": [dict(r) for r in rows]}
from fastapi import Query

@app.get("/perf/open")
def perf_open_trades():
    con = db()
    rows = con.execute("""
        SELECT trade_id, engine, symbol, side, status, entry_ts, entry, stop, qty, risk_usd
        FROM trades
        WHERE status='OPEN'
        ORDER BY entry_ts DESC
    """).fetchall()
    con.close()
    return {"open": [dict(r) for r in rows]}

@app.get("/perf/trades")
def perf_trades(
    limit: int = Query(50, ge=1, le=500),
    engine: str | None = None,
    status: str | None = None,   # OPEN / CLOSED
    symbol: str | None = None,
):
    con = db()
    where = []
    params = {}

    if engine:
        where.append("engine = :engine")
        params["engine"] = engine
    if status:
        where.append("status = :status")
        params["status"] = status.upper()
    if symbol:
        where.append("symbol = :symbol")
        params["symbol"] = symbol

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = con.execute(f"""
        SELECT trade_id, status, engine, symbol, side,
               entry, stop, exit,
               qty, risk_usd,
               pnl_real, r_real,
               entry_ts, exit_ts
        FROM trades
        {where_sql}
        ORDER BY entry_ts DESC
        LIMIT :limit
    """, {**params, "limit": limit}).fetchall()

    con.close()
    return {"trades": [dict(r) for r in rows], "limit": limit, "filters": params}
from fastapi.responses import HTMLResponse

@app.get("/perf/ui", response_class=HTMLResponse)
def perf_ui():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Perf Control Center</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 18px; }
    .row { display:flex; gap:14px; flex-wrap:wrap; align-items:flex-start; }
    .card { border:1px solid #2223; border-radius:14px; padding:14px; min-width: 320px; }
    h1 { margin:0 0 12px; font-size: 22px; }
    h2 { margin:0 0 10px; font-size: 16px; opacity:.85; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border-bottom:1px solid #2222; padding: 6px 8px; text-align:left; vertical-align: top; }
    input, button { padding:8px 10px; border-radius:10px; border:1px solid #2223; }
    button { cursor:pointer; }
    .muted { opacity:.7; }
    code { background:#0001; padding:2px 6px; border-radius:8px; }
  </style>
</head>
<body>
  <h1>Perf Control Center</h1>

  <div class="row">
    <div class="card" style="flex:1">
      <h2>Summary</h2>
      <pre id="summary" class="muted">loading...</pre>
      <button onclick="refreshAll()">Refresh</button>
    </div>

    <div class="card" style="flex:1">
      <h2>Close trade</h2>
      <div class="row">
        <div>
          <div class="muted">trade_id</div>
          <input id="close_id" style="width:360px" placeholder="T_..."/>
        </div>
        <div>
          <div class="muted">exit</div>
          <input id="close_exit" style="width:140px" placeholder="5038.5"/>
        </div>
      </div>
      <div style="margin-top:10px;">
        <button onclick="closeTrade()">Send CLOSE</button>
        <span id="close_res" class="muted"></span>
      </div>
    </div>
  </div>

  <div class="row" style="margin-top:14px;">
    <div class="card" style="flex:1">
      <h2>Open trades</h2>
      <div class="muted">Tip: clique un trade_id pour le copier.</div>
      <table id="open_tbl"></table>
    </div>

    <div class="card" style="flex:1">
      <h2>Last trades</h2>
      <table id="trades_tbl"></table>
    </div>
  </div>

<script>
async function jget(url){ const r=await fetch(url); return await r.json(); }
function esc(s){ return (s??"").toString().replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;"); }
function mkRow(cells){ return "<tr>"+cells.map(c=>"<td>"+c+"</td>").join("")+"</tr>"; }
function copyText(t){ navigator.clipboard.writeText(t); }

async function refreshAll(){
  const s = await jget("/perf/summary");
  document.getElementById("summary").textContent = JSON.stringify(s, null, 2);

  const o = await jget("/perf/open");
  const open = o.open || [];
  let h = "<tr><th>trade_id</th><th>engine</th><th>symbol</th><th>side</th><th>entry</th><th>stop</th><th>qty</th><th>risk</th><th>ts</th></tr>";
  for(const t of open){
    const id = esc(t.trade_id);
    h += mkRow([
      `<a href="#" onclick="copyText('${id}'); document.getElementById('close_id').value='${id}'; return false;"><code>${id}</code></a>`,
      esc(t.engine), esc(t.symbol), esc(t.side),
      esc(t.entry), esc(t.stop), esc(t.qty), esc(t.risk_usd),
      esc(t.entry_ts)
    ]);
  }
  document.getElementById("open_tbl").innerHTML = h;

  const tr = await jget("/perf/trades?limit=50");
  const trades = tr.trades || [];
  let ht = "<tr><th>trade_id</th><th>status</th><th>engine</th><th>side</th><th>entry</th><th>exit</th><th>pnl</th><th>R</th><th>ts</th></tr>";
  for(const t of trades.slice(0,50)){
    const id = esc(t.trade_id);
    ht += mkRow([
      `<code>${id}</code>`,
      esc(t.status), esc(t.engine), esc(t.side),
      esc(t.entry), esc(t.exit ?? ""),
      esc(t.pnl_real ?? ""), esc(t.r_real ?? ""),
      esc(t.entry_ts)
    ]);
  }
  document.getElementById("trades_tbl").innerHTML = ht;
}

async function closeTrade(){
  const id = document.getElementById("close_id").value.trim();
  const ex = parseFloat(document.getElementById("close_exit").value);
  if(!id || !isFinite(ex)){ document.getElementById("close_res").textContent="missing trade_id or exit"; return; }
  const r = await fetch("/perf/event", {
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body: JSON.stringify({type:"CLOSE", trade_id:id, exit:ex})
  });
  const j = await r.json();
  document.getElementById("close_res").textContent = " → " + JSON.stringify(j);
  await refreshAll();
}

refreshAll();
</script>
</body>
</html>
"""
