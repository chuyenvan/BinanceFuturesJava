#!/usr/bin/env python3
import aerospike, datetime, sys, json

HOST = "127.0.0.1"
PORT = 3222
NS = "test"
SET_TICKER = "kline_1m_opt"
SET_FUNDING = "funding_data"
SET_MAPPER = "symbol_mapper"

client = aerospike.client({"hosts": [(HOST, PORT)]}).connect()

def daterange(d0, d1):
    d = d0
    while d < d1:
        yield d
        d += datetime.timedelta(days=1)

START = datetime.date(2021, 1, 1)
END = datetime.date(2026, 7, 1)  # exclusive per pipeline convention (checked separately)

print(f"== TICKER ({SET_TICKER}) coverage {START} -> {END} (exclusive) ==")
missing_days = []
partial_days = []
first_has_data = None
last_has_data = None
total_days = 0
total_present = 0
total_slots = 0

for d in daterange(START, END):
    total_days += 1
    base = datetime.datetime(d.year, d.month, d.day)
    keys = []
    for m in range(1440):
        ts = base + datetime.timedelta(minutes=m)
        keystr = ts.strftime("%Y%m%d-%H%M")
        keys.append((NS, SET_TICKER, keystr))
    try:
        br = client.batch_read(keys)
    except Exception as e:
        print(f"ERROR day {d}: {e}")
        continue
    present = sum(1 for r in br.batch_records if r.result == 0)
    total_present += present
    total_slots += 1440
    if present == 0:
        missing_days.append(d.isoformat())
    elif present < 1440:
        partial_days.append((d.isoformat(), present))
    if present > 0:
        if first_has_data is None:
            first_has_data = d.isoformat()
        last_has_data = d.isoformat()
    if total_days % 200 == 0:
        print(f"... progress {d.isoformat()} present_so_far={total_present}/{total_slots}", file=sys.stderr)

print(f"total_days_checked={total_days}")
print(f"first_day_with_data={first_has_data}")
print(f"last_day_with_data={last_has_data}")
print(f"total_minutes_present={total_present} / total_minutes_checked={total_slots} ratio={total_present/total_slots:.6f}")
print(f"fully_missing_days count={len(missing_days)}")
if missing_days:
    print("missing_days sample (first 30):", missing_days[:30])
    print("missing_days sample (last 30):", missing_days[-30:])
print(f"partial_days count={len(partial_days)}")
if partial_days:
    print("partial_days sample (first 30):", partial_days[:30])

print()
print(f"== SYMBOL_MAPPER ({SET_MAPPER}) ==")
try:
    key = (NS, SET_MAPPER, "global_id_map")
    (k, meta, bins) = client.get(key)
    if bins:
        for binname, val in bins.items():
            if isinstance(val, dict):
                print(f"bin={binname} map_size={len(val)}")
                syms = list(val.keys())
                print("sample symbols:", syms[:10])
                print("has BTCUSDT:", "BTCUSDT" in val, "has ETHUSDT:", "ETHUSDT" in val)
            else:
                print(f"bin={binname} type={type(val)}")
    else:
        print("symbol_mapper record EMPTY/None")
except Exception as e:
    print(f"ERROR reading symbol_mapper: {e}")

print()
print(f"== FUNDING_DATA ({SET_FUNDING}) scan ==")
count = [0]
symbols = []
def cb(record):
    key, meta, bins = record
    count[0] += 1
    if key and len(key) >= 3 and key[2] is not None:
        symbols.append(key[2])
    elif count[0] <= 5:
        print("record with no userKey:", key)

try:
    scan = client.scan(NS, SET_FUNDING)
    scan.foreach(cb)
    print(f"funding_data total records scanned={count[0]}")
    print(f"records with userKey={len(symbols)}")
    print("sample symbols:", symbols[:15])
    print("has BTCUSDT:", "BTCUSDT" in symbols, "has ETHUSDT:", "ETHUSDT" in symbols)
except Exception as e:
    print(f"ERROR scanning funding_data: {e}")

client.close()
