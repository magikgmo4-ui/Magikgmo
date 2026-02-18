"""Adaptateur clair: WebhookEvent -> PerfEvent.

- Input: dict (payload webhook normalisé)
- Output: dict (payload pour /perf/event) ou None

Objectif: centraliser le mapping et la génération trade_id.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_hash(obj: Any) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]


def build_trade_id(engine: str, symbol: str, side: str, payload: Dict[str, Any]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]  # ms
    return f"T_{ts}_{engine}_{symbol}_{side}_{_short_hash(payload)}"


def webhook_event_to_perf_event(evt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convertit un événement webhook en événement PerfEvent.

    Attendu (minimal):
      - engine, symbol, side (ou signal BUY/SELL), price/entry, sl/stop, qty
      - event_type: OPEN/UPDATE/CLOSE (ou trade_event), sinon None

    Remarque:
      - Les SIGNAL (alertes non-exécutées) ne doivent pas aller dans perf.
    """
    event_type = (evt.get("event_type") or evt.get("trade_event") or "").upper().strip()
    if event_type == "":
        # compat: certaines alertes utilisent juste signal BUY/SELL -> on considère OPEN
        # mais uniquement si on a entry+stop+qty
        event_type = "OPEN"

    if event_type == "SIGNAL":
        return None

    # normaliser side
    side = (evt.get("side") or "").upper().strip()
    if side == "":
        sig = (evt.get("signal") or "").upper().strip()
        if sig == "BUY":
            side = "LONG"
        elif sig == "SELL":
            side = "SHORT"

    engine = (evt.get("engine") or "").strip()
    symbol = (evt.get("symbol") or "").strip()

    entry = evt.get("entry", None)
    if entry is None:
        entry = evt.get("price", None)

    stop = evt.get("stop", None)
    if stop is None:
        stop = evt.get("sl", None)

    qty = evt.get("qty", None)

    # CLOSE
    exit_ = evt.get("exit", None)

    if event_type in {"OPEN", "UPDATE"}:
        if engine == "" or symbol == "" or side == "" or entry is None or stop is None or qty is None:
            return None
    if event_type == "CLOSE":
        if engine == "" or symbol == "" or side == "" or exit_ is None:
            return None

    trade_id = (evt.get("trade_id") or "").strip()
    if trade_id == "":
        trade_id = build_trade_id(engine, symbol, side, evt)

    out: Dict[str, Any] = {
        "type": event_type,
        "ts": evt.get("ts") or evt.get("_ts") or _utc_iso_now(),
        "trade_id": trade_id,
        "engine": engine,
        "symbol": symbol,
        "side": side,
        "meta": evt.get("meta") or {},
    }

    if event_type in {"OPEN", "UPDATE"}:
        out["entry"] = float(entry)
        out["stop"] = float(stop)
        out["qty"] = float(qty)
        # best-effort risk
        for k in ("risk_real_usd", "risk_usd"):
            if evt.get(k) is not None:
                out["risk_usd"] = float(evt[k])
                break

    if event_type == "CLOSE":
        out["exit"] = float(exit_)
        if evt.get("qty") is not None:
            out["qty"] = float(evt["qty"])

    return out
