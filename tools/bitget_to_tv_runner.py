import os, json, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
import sys

# garantir import depuis /opt/trading/tools (bitget_feed.py est là)
if "/opt/trading/tools" not in sys.path:
    sys.path.insert(0, "/opt/trading/tools")

from bitget_feed import fetch_candles_usdt_futures


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: str, default):
    try:
        p = Path(path)
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: str, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _post_json(url: str, payload: dict, timeout: int = 15) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", errors="replace")
        return json.loads(raw) if raw else {}


def main():
    # relire ENV ICI (pas au top-level)
    tv_url   = os.environ.get("TV_WEBHOOK_URL", "http://127.0.0.1:8000/tv").strip()
    key      = os.environ.get("TV_WEBHOOK_KEY", "").strip()
    engine   = os.environ.get("TV_ENGINE", "COINM_SHORT").strip()
    symbol   = os.environ.get("SYMBOL", "BTCUSDT").strip()
    tf_sec   = int(os.environ.get("TF_SEC", "300"))
    poll_s   = int(os.environ.get("POLL_S", "5"))
    sl_pts   = float(os.environ.get("SL_PTS", "10"))
    dry_run  = os.environ.get("DRY_RUN", "0") == "1"
    force    = (os.environ.get("FORCE_SIGNAL") or "").strip().upper()  # BUY/SELL/AUTO
    one_shot = os.environ.get("ONE_SHOT", "0") == "1"
    state_f  = os.environ.get("STATE_FILE", "/opt/trading/state/bitget_tv_state.json").strip()

    if not key:
        print("TV_WEBHOOK_KEY missing in env")
        raise SystemExit(2)

    if force not in ("", "AUTO", "BUY", "SELL"):
        force = "AUTO"
    if force == "":
        force = "AUTO"

    print(
        f"RUNNER start symbol={symbol} tf_sec={tf_sec} poll_s={poll_s} "
        f"engine={engine} DRY_RUN={dry_run} FORCE_SIGNAL={force}"
    )

    state = _load_json(state_f, {})
    last_ts = int(state.get("last_ts_ms") or 0)

    while True:
        try:
            print(f"fetching candles: symbol={symbol} tf_sec={tf_sec} ...")
            cs = fetch_candles_usdt_futures(symbol, tf_sec, limit=3)
            if not cs:
                time.sleep(poll_s)
                continue

            c = cs[-1]  # bitget_feed.Candle(ts_ms, o,h,l,c,...)
            bar_ts = int(getattr(c, "ts_ms", 0) or 0)
            o = float(getattr(c, "o", 0) or 0)
            close = float(getattr(c, "c", 0) or 0)

            if bar_ts <= 0 or close <= 0:
                time.sleep(poll_s)
                continue

            # dedup: ne pas renvoyer le même bar
            if bar_ts == last_ts:
                time.sleep(poll_s)
                continue

            # signal
            if force in ("BUY", "SELL"):
                signal = force
            else:
                signal = "BUY" if close >= o else "SELL"

            # SL simple en points
            sl = close - sl_pts if signal == "BUY" else close + sl_pts

            tf_label = str(tf_sec // 60) if tf_sec % 60 == 0 else str(tf_sec)

            payload = {
                "key": key,
                "engine": engine,
                "signal": signal,
                "symbol": symbol,
                "tf": tf_label,
                "price": close,
                "sl": sl,
                "tp": None,
                "reason": f"bitget bar-close ts={bar_ts}",
                "_ts": _utc_now_iso(),
            }

            if dry_run:
                print(f"[{datetime.now().isoformat()}] DRY_RUN payload={json.dumps(payload)}")
                # update state to simulate dedup (optionnel). Ici oui, pour se comporter comme réel.
                last_ts = bar_ts
                _save_json(state_f, {"last_ts_ms": last_ts, "updated_at": _utc_now_iso()})
                if one_shot:
                    return
                time.sleep(poll_s)
                continue

            try:
                resp = _post_json(tv_url, payload, timeout=15)
                print(f"[{datetime.now().isoformat()}] sent {signal} {symbol} close={close} ts={bar_ts} resp={resp}")
                last_ts = bar_ts
                _save_json(state_f, {"last_ts_ms": last_ts, "updated_at": _utc_now_iso()})
                if one_shot:
                    return
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                print(f"[{datetime.now().isoformat()}] TV HTTPError {e.code}: {body}")

            time.sleep(poll_s)

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] fetch ERROR: {repr(e)}")
            time.sleep(poll_s)


if __name__ == "__main__":
    main()
