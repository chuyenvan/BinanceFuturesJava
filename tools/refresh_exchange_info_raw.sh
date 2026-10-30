#!/usr/bin/env bash
# refresh_exchange_info_raw.sh — [UNIVERSE-A1 fixA 2026-10-30]
# DUY TRI anh chup raw /fapi/v1/exchangeInfo (co contractType/underlyingType/onboardDate/serverTime)
# cho UniverseA1Filter (UNIVERSE_A1=1). JVM tu RELOAD theo mtime (UniverseA1Filter.maybeReload, 1 stat/phut).
#
# NGUYEN TAC:
#  - KHONG goi Binance tu Oracle. Nguon hop le: (a) file tren 242 lay qua ssh CHI DOC, hoac (b) file owner cung cap.
#  - KHONG cai crontab (owner quyet dinh). Script nay chi chay khi duoc goi.
#  - Khong ghi gi len 242. Chi `ssh ... cat <path>` roi validate tren Oracle.
#  - Validate: JSON hop le, co serverTime, >= MIN_TF symbol TF (luat TradFiClassifier), moi symbol co
#    contractType/underlyingType (khong phai dump SDK). Sai => KHONG thay file dich.
#
# Dung:
#   refresh_exchange_info_raw.sh                 # lay tu 242 (SRC_SSH/SRC_PATH)
#   refresh_exchange_info_raw.sh --local FILE    # validate + cai FILE (owner cung cap; .gz duoc)
#   refresh_exchange_info_raw.sh --check FILE    # chi validate, khong ghi
# Env: SRC_SSH, SRC_PATH, DEST (mac dinh ~/claude_master/universe_a1/exchangeInfo_raw.json), MIN_TF=200, MAX_AGE_H=72.
set -u
SRC_SSH=${SRC_SSH:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SRC_PATH=${SRC_PATH:-/home/chuyennd/java/v_t_m/data/exchangeInfo_raw.json}
DEST=${DEST:-/home/ubuntu/claude_master/universe_a1/exchangeInfo_raw.json}
MIN_TF=${MIN_TF:-200}
MAX_AGE_H=${MAX_AGE_H:-72}
TMP=$(mktemp /tmp/exinfo.XXXXXX.json) || exit 1
trap 'rm -f "$TMP"' EXIT

mode=${1:-pull}
case "$mode" in
  --check|--local)
    src=${2:-}
    [ -n "$src" ] && [ -f "$src" ] || { echo "FAIL: thieu file $src"; exit 2; }
    case "$src" in *.gz) zcat "$src" > "$TMP" ;; *) cp "$src" "$TMP" ;; esac
    ;;
  pull)
    # CHI DOC tren 242 (cat qua ssh). Timeout 90s, khong ghi 242.
    if ! timeout 90 $SRC_SSH "cat $SRC_PATH" > "$TMP" 2>/dev/null || [ ! -s "$TMP" ]; then
      echo "FAIL: khong doc duoc $SRC_PATH tren 242 (hoac rong). Owner can xac nhan nguon/duong dan."; exit 3
    fi
    ;;
  *) echo "usage: $0 [--check FILE | --local FILE]"; exit 2 ;;
esac

python3 - "$TMP" "$MIN_TF" "$MAX_AGE_H" <<'PY' || { echo "FAIL: validate exchangeInfo that bai — KHONG thay file dich"; exit 4; }
import json,sys,time,datetime
p,min_tf,max_age_h=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
d=json.load(open(p))
sy=d.get('symbols'); assert isinstance(sy,list) and len(sy)>200, "thieu mang symbols"
st=d.get('serverTime')
assert isinstance(st,(int,float)) and st>0, "thieu serverTime (raw /fapi/v1/exchangeInfo)"
age_h=(time.time()*1000-st)/3600000.0
assert age_h <= max_age_h, f"snapshot qua cu: {age_h:.1f}h > {max_age_h}h"
crypto={'COIN','INDEX','PREMARKET'}
tf=0; ix=0; with_fields=0
for s in sy:
    if not isinstance(s,dict): continue
    ct=(s.get('contractType') or '').upper(); ut=(s.get('underlyingType') or '')
    if ct and ut: with_fields+=1
    if 'TRADIFI' in ct or 'TRADFI' in ct or (ut and ut.upper() not in crypto): tf+=1
    if ut.upper()=='INDEX': ix+=1
assert with_fields >= 0.9*len(sy), f"qua nhieu symbol thieu contractType/underlyingType ({with_fields}/{len(sy)}) — nghi dump SDK"
assert tf >= min_tf, f"chi {tf} TF < {min_tf} — khong phai raw exchangeInfo"
print(f"OK: symbols={len(sy)} tf={tf} index={ix} with_fields={with_fields} serverTime={datetime.datetime.utcfromtimestamp(st/1000)}Z age={age_h:.2f}h")
PY

if [ "$mode" = "--check" ]; then
  echo "check-only: khong ghi $DEST"; exit 0
fi
mkdir -p "$(dirname "$DEST")"
cp -f "$TMP" "$DEST.tmp" && mv -f "$DEST.tmp" "$DEST"
echo "INSTALLED: $DEST ($(stat -c %s "$DEST") bytes, mtime $(date -d @$(stat -c %Y "$DEST") '+%F %T'))"
echo "NHAC: script nay KHONG tu chay. Owner quyet dinh dat cron (vi du 03:10 hang ngay) va duong dan tren host live."
