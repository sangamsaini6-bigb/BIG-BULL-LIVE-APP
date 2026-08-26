import os
import re
import html
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

APP_NAME = "BIG.BULL Live App"
WEBHOOK_KEY = os.getenv("APP_WEBHOOK_KEY", "CHANGE_ME")
VIEW_KEY = os.getenv("APP_VIEW_KEY", "")
DB_PATH = os.getenv("APP_DB_PATH", "bigbull_app.db")

app = FastAPI(title=APP_NAME, version="1.0.0")
STATIC_DIR = Path(__file__).parent / "static"

def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            event TEXT NOT NULL,
            symbol TEXT,
            timeframe TEXT,
            step INTEGER,
            lot REAL,
            entry REAL,
            sl REAL,
            tp REAL,
            setup_range REAL,
            cycle_pl REAL,
            raw_text TEXT NOT NULL
        )""")
        con.execute("""
        CREATE TABLE IF NOT EXISTS state(
            id INTEGER PRIMARY KEY CHECK(id=1),
            updated_at TEXT,
            status TEXT,
            symbol TEXT,
            timeframe TEXT,
            setup_range REAL,
            buy_entry REAL,
            buy_sl REAL,
            buy_tp REAL,
            sell_entry REAL,
            sell_sl REAL,
            sell_tp REAL,
            step INTEGER DEFAULT 0,
            lot REAL,
            direction TEXT,
            cycle_pl REAL,
            raw_text TEXT
        )""")
        con.execute("""INSERT OR IGNORE INTO state(id,status,step) VALUES(1,'WAITING',0)""")

@app.on_event("startup")
def startup():
    init_db()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def strip_html(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", "", s)
    return s.replace("\r", "").strip()

def fnum(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

def fint(pattern: str, text: str) -> Optional[int]:
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def ftext(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None

def detect_event(text: str) -> str:
    u = text.upper()
    if "NEW SETUP DETECTED" in u:
        return "NEW_SETUP"
    if "RECOVERY WARNING" in u:
        return "RECOVERY_WARNING"
    if "RECOVERY SELL" in u:
        return "RECOVERY_SELL"
    if "RECOVERY BUY" in u:
        return "RECOVERY_BUY"
    if "BUY ACTIVE" in u:
        return "BUY_ACTIVE"
    if "SELL ACTIVE" in u:
        return "SELL_ACTIVE"
    if "TP HIT" in u:
        return "TP_HIT"
    if "CYCLE FAILED" in u or "FINAL SL HIT" in u:
        return "CYCLE_FAILED"
    if "STRUCTURE SKIPPED" in u:
        return "STRUCTURE_SKIPPED"
    if "MANUAL CLOSE" in u:
        return "MANUAL_CLOSE"
    return "MESSAGE"

def parse_message(text: str) -> Dict[str, Any]:
    clean = strip_html(text)
    event = detect_event(clean)

    symbol = ftext(r"📊\s*(?:Symbol:\s*)?([A-Za-z0-9._-]+)", clean)
    if not symbol:
        symbol = ftext(r"\bSymbol:\s*([A-Za-z0-9._-]+)", clean)
    timeframe = ftext(r"Timeframe:\s*([^\n]+)", clean)
    setup_range = fnum(r"(?:Structure\s+)?Range:\s*([-+]?\d+(?:\.\d+)?)", clean)
    step = fint(r"Step:\s*(\d+)", clean)
    lot = fnum(r"Lot:\s*([-+]?\d+(?:\.\d+)?)", clean)
    entry = fnum(r"(?:📍\s*)?Entry:\s*([-+]?\d+(?:\.\d+)?)", clean)
    sl = fnum(r"(?:🛑\s*)?SL:\s*([-+]?\d+(?:\.\d+)?)", clean)
    tp = fnum(r"(?:🎯\s*)?TP:\s*([-+]?\d+(?:\.\d+)?)", clean)

    cycle_pl = None
    for pat in [
        r"Cycle Net:\s*[^\d+\-]*([-+]?\d+(?:\.\d+)?)",
        r"Running Cycle:\s*[^\d+\-]*([-+]?\d+(?:\.\d+)?)",
        r"Cycle P/L:\s*[^\d+\-]*([-+]?\d+(?:\.\d+)?)",
    ]:
        cycle_pl = fnum(pat, clean)
        if cycle_pl is not None:
            break

    buy_entry = buy_sl = buy_tp = sell_entry = sell_sl = sell_tp = None
    if event == "NEW_SETUP":
        mb = re.search(r"BUY SETUP(.*?)(?:SELL SETUP|RECOVERY|$)", clean, re.I | re.S)
        ms = re.search(r"SELL SETUP(.*?)(?:RECOVERY|$)", clean, re.I | re.S)
        if mb:
            b = mb.group(1)
            buy_entry = fnum(r"Entry:\s*([-+]?\d+(?:\.\d+)?)", b)
            buy_sl = fnum(r"SL:\s*([-+]?\d+(?:\.\d+)?)", b)
            buy_tp = fnum(r"TP:\s*([-+]?\d+(?:\.\d+)?)", b)
        if ms:
            s = ms.group(1)
            sell_entry = fnum(r"Entry:\s*([-+]?\d+(?:\.\d+)?)", s)
            sell_sl = fnum(r"SL:\s*([-+]?\d+(?:\.\d+)?)", s)
            sell_tp = fnum(r"TP:\s*([-+]?\d+(?:\.\d+)?)", s)

    direction = None
    if event in ("BUY_ACTIVE", "RECOVERY_BUY"):
        direction = "BUY"
    elif event in ("SELL_ACTIVE", "RECOVERY_SELL"):
        direction = "SELL"

    return {
        "event": event,
        "symbol": symbol,
        "timeframe": timeframe,
        "setup_range": setup_range,
        "step": step,
        "lot": lot,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "cycle_pl": cycle_pl,
        "direction": direction,
        "buy_entry": buy_entry,
        "buy_sl": buy_sl,
        "buy_tp": buy_tp,
        "sell_entry": sell_entry,
        "sell_sl": sell_sl,
        "sell_tp": sell_tp,
        "raw_text": clean,
    }

def check_view_key(x_app_key: Optional[str]):
    if VIEW_KEY and x_app_key != VIEW_KEY:
        raise HTTPException(status_code=401, detail="Invalid app key")

def update_state(p: Dict[str, Any]):
    status_map = {
        "NEW_SETUP": "NEW SETUP",
        "BUY_ACTIVE": "BUY ACTIVE",
        "SELL_ACTIVE": "SELL ACTIVE",
        "RECOVERY_BUY": "RECOVERY BUY",
        "RECOVERY_SELL": "RECOVERY SELL",
        "RECOVERY_WARNING": "RECOVERY WARNING",
        "TP_HIT": "TP HIT",
        "CYCLE_FAILED": "CYCLE FAILED",
        "STRUCTURE_SKIPPED": "SKIPPED",
        "MANUAL_CLOSE": "CLOSED",
        "MESSAGE": "MESSAGE",
    }
    with db() as con:
        cur = con.execute("SELECT * FROM state WHERE id=1").fetchone()
        s = dict(cur) if cur else {}

        if p["event"] == "NEW_SETUP":
            s.update({
                "step": 0, "lot": None, "direction": None, "cycle_pl": None,
                "buy_entry": p["buy_entry"], "buy_sl": p["buy_sl"], "buy_tp": p["buy_tp"],
                "sell_entry": p["sell_entry"], "sell_sl": p["sell_sl"], "sell_tp": p["sell_tp"],
            })

        for k in ("symbol","timeframe","setup_range","step","lot","direction","cycle_pl"):
            if p.get(k) is not None:
                s[k] = p[k]

        # For active/recovery messages, fill the matching side from Entry/SL/TP.
        if p.get("direction") == "BUY":
            if p.get("entry") is not None: s["buy_entry"] = p["entry"]
            if p.get("sl") is not None: s["buy_sl"] = p["sl"]
            if p.get("tp") is not None: s["buy_tp"] = p["tp"]
        if p.get("direction") == "SELL":
            if p.get("entry") is not None: s["sell_entry"] = p["entry"]
            if p.get("sl") is not None: s["sell_sl"] = p["sl"]
            if p.get("tp") is not None: s["sell_tp"] = p["tp"]

        if p["event"] in ("TP_HIT","CYCLE_FAILED","MANUAL_CLOSE"):
            s["step"] = 0

        con.execute("""
        UPDATE state SET
          updated_at=?, status=?, symbol=?, timeframe=?, setup_range=?,
          buy_entry=?, buy_sl=?, buy_tp=?, sell_entry=?, sell_sl=?, sell_tp=?,
          step=?, lot=?, direction=?, cycle_pl=?, raw_text=?
        WHERE id=1
        """, (
            now_iso(), status_map.get(p["event"], p["event"]),
            s.get("symbol"), s.get("timeframe"), s.get("setup_range"),
            s.get("buy_entry"), s.get("buy_sl"), s.get("buy_tp"),
            s.get("sell_entry"), s.get("sell_sl"), s.get("sell_tp"),
            s.get("step",0), s.get("lot"), s.get("direction"), s.get("cycle_pl"),
            p.get("raw_text")
        ))

def save_event(p: Dict[str, Any]):
    with db() as con:
        con.execute("""
        INSERT INTO events(created_at,event,symbol,timeframe,step,lot,entry,sl,tp,setup_range,cycle_pl,raw_text)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            now_iso(), p["event"], p.get("symbol"), p.get("timeframe"), p.get("step"),
            p.get("lot"), p.get("entry"), p.get("sl"), p.get("tp"),
            p.get("setup_range"), p.get("cycle_pl"), p.get("raw_text")
        ))
        # Keep the DB small.
        con.execute("""
        DELETE FROM events WHERE id NOT IN
        (SELECT id FROM events ORDER BY id DESC LIMIT 500)
        """)

@app.get("/health")
def health():
    return {"ok": True, "app": APP_NAME}

@app.post("/tv/{key}")
async def tradingview_webhook(key: str, request: Request):
    if key != WEBHOOK_KEY or WEBHOOK_KEY == "CHANGE_ME":
        raise HTTPException(status_code=401, detail="Invalid webhook key")

    raw = await request.body()
    body_text = raw.decode("utf-8", errors="replace")
    msg_text = body_text

    try:
        data = json.loads(body_text)
        if isinstance(data, dict):
            msg_text = str(data.get("text") or data.get("message") or body_text)
    except Exception:
        pass

    parsed = parse_message(msg_text)
    save_event(parsed)
    update_state(parsed)
    return {"ok": True, "event": parsed["event"]}

@app.get("/api/state")
def api_state(x_app_key: Optional[str] = Header(default=None)):
    check_view_key(x_app_key)
    with db() as con:
        row = con.execute("SELECT * FROM state WHERE id=1").fetchone()
    return dict(row) if row else {"status":"WAITING"}

@app.get("/api/history")
def api_history(limit: int = 50, x_app_key: Optional[str] = Header(default=None)):
    check_view_key(x_app_key)
    limit = max(1, min(limit, 100))
    with db() as con:
        rows = con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

@app.get("/", response_class=HTMLResponse)
def home():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

@app.get("/manifest.webmanifest")
def manifest():
    return Response((STATIC_DIR / "manifest.webmanifest").read_text(encoding="utf-8"),
                    media_type="application/manifest+json")

@app.get("/sw.js")
def sw():
    return Response((STATIC_DIR / "sw.js").read_text(encoding="utf-8"),
                    media_type="application/javascript")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
