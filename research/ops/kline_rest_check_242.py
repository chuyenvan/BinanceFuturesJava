#!/usr/bin/env python3
"""KFIX F7 — healthcheck nen 1m 242 vs REST Binance (chay TREN ORACLE, cron moi gio). CHI DOC 242.
Moi lan: doc record Aerospike 242 `ticker.kline_1m_opt` cua 5 phut DA DONG gan nhat (now-7'..now-3', da qua pass settle
+30 s cua ingest), chon ~20 symbol (10 totalUsdt lon nhat + 10 ngau nhien theo gio), goi REST fapi/v1/klines (limit 10,
weight 1/symbol => ~20 weight/gio) va so 5 truong float32 (cho phep 1 ulp lam tron). Lech > 0 o => canh bao Telegram qua
tg.env cua health_242.sh (TG_TOKEN=/TG_CHAT= hoac tele-token:/tele-chat-id:; KHONG in token/chat id). Khong co tg.env =>
ghi ALERT_PENDING_NEED_OWNER_CHANNEL.txt. Log: $STATE_DIR/kline_check.log (1 dong/lan).
Dung: kline_rest_check_242.py [--dry-run] [--symbols 20] [--minutes 5]
"""
import argparse, datetime, json, logging, os, random, re, struct, sys, time, urllib.error, urllib.parse, urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kline_rest_check_242")
MN = 60000
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
STATE_DIR = os.environ.get("HEALTH242_DIR", "/home/ubuntu/claude_master/health242")
TG_ENV = os.environ.get("HEALTH242_TG_ENV", "/home/ubuntu/.config/health242/tg.env")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kline_backfill_242 as kb  # noqa: E402  decode() dung chung (khop proto Java)


def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def tg_creds():
    """Parse tg.env nhu health_242.sh. Tra (token, chat) hoac (None, None). KHONG log gia tri."""
    if not os.access(TG_ENV, os.R_OK):
        return None, None
    tok = chat = None
    for line in open(TG_ENV):
        line = line.strip().replace('"', "")
        line = re.sub(r"^export\s+", "", line)
        m = re.match(r"^(TG_TOKEN=|tele-token:\s*)(.+)$", line)
        if m and tok is None:
            tok = m.group(2).strip()
        m = re.match(r"^(TG_CHAT=|tele-chat-id:\s*)(.+)$", line)
        if m and chat is None:
            chat = m.group(2).strip()
    return tok, chat


def send(msg, dry):
    msg = "[242-KLINE] " + msg
    if dry:
        log.info("WOULD_SEND: %s", msg)
        return
    tok, chat = tg_creds()
    if not tok or not chat:
        with open(os.path.join(STATE_DIR, "ALERT_PENDING_NEED_OWNER_CHANNEL.txt"), "a") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), msg))
        log.warning("NO_CHANNEL (thieu tg.env) — ghi ALERT_PENDING")
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
    try:
        with urllib.request.urlopen("https://api.telegram.org/bot%s/sendMessage" % tok, data=data, timeout=15) as r:
            log.info("SENT http=%d", r.status)
    except Exception as e:
        log.error("gui Telegram loi: %s", type(e).__name__)      # khong in URL (chua token)


def rest_last(sym, limit=10):
    u = "https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=1m&limit=%d" % (sym, limit)
    with urllib.request.urlopen(u, timeout=10) as r:
        rows = json.loads(r.read())
    return {int(x[0]): (f32(x[1]), f32(x[2]), f32(x[3]), f32(x[4]), f32(x[7])) for x in rows}


def ulp_le1(a, b):
    ia = struct.unpack("<i", struct.pack("<f", a))[0]
    ib = struct.unpack("<i", struct.pack("<f", b))[0]
    return abs(ia - ib) <= 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--symbols", type=int, default=20)
    ap.add_argument("--minutes", type=int, default=5)
    a = ap.parse_args()
    os.makedirs(STATE_DIR, exist_ok=True)
    now = int(time.time() * 1000)
    last = now // MN * MN - 3 * MN                       # phut moi nhat duoc kiem: da dong >= 2' (qua settle +30s)
    mins = [last - i * MN for i in range(a.minutes)][::-1]
    db = kb.AS("103.157.218.242", 3222)
    recs = {m: kb.decode(r[0]) for m in mins for r in [db.get(m)] if r[0] is not None}
    if not recs:
        send("FAIL: khong doc duoc record 242 %s..%s" % (kb.k7(mins[0]), kb.k7(mins[-1])), a.dry_run)
        return
    ref = recs[max(recs)]
    top = sorted(ref, key=lambda s: -ref[s][4])[: a.symbols // 2]
    rest_pool = sorted(set(ref) - set(top))
    rnd = random.Random(now // 3600000).sample(rest_pool, min(len(rest_pool), a.symbols - len(top)))
    cells = bad = miss = err = 0
    ex = []
    for s in top + rnd:
        try:
            R = rest_last(s + "USDT")
        except urllib.error.HTTPError as e:
            err += 1
            if e.code in (418, 429):
                log.error("REST %d (rate limit/ban IP) — DUNG kiem lan nay, khong goi tiep", e.code)
                break
            log.warning("REST %s loi: %s", s, e)
            continue
        except Exception as e:
            err += 1
            log.warning("REST %s loi: %s", s, e)
            continue
        for m, rec in recs.items():
            if s not in rec or m not in R:
                miss += 1
                continue
            cells += 1
            if not all(ulp_le1(x, y) for x, y in zip(rec[s], R[m])):
                bad += 1
                if len(ex) < 5:
                    ex.append("%s@%s q242/qREST=%.4f" % (s, kb.k7(m)[9:], rec[s][4] / R[m][4] if R[m][4] else -1))
        time.sleep(0.05)
    summ = "cells=%d lech=%d (%.2f%%) thieu=%d rest_err=%d phut=%s..%s vd=%s" % (
        cells, bad, 100.0 * bad / max(cells, 1), miss, err, kb.k7(mins[0]), kb.k7(mins[-1]), ex)
    if not a.dry_run:
        with open(os.path.join(STATE_DIR, "kline_check.log"), "a") as f:
            f.write("%s %s %s\n" % (datetime.datetime.now(TZ7).isoformat(timespec="seconds"), "FAIL" if bad else "OK", summ))
    log.info("%s %s", "FAIL" if bad else "OK", summ)
    if bad > 0:
        send("FAIL nen 1m 242 != REST: " + summ, a.dry_run)


if __name__ == "__main__":
    main()
