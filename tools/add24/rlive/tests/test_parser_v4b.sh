#!/bin/bash
# ADD24 test (f): log TONG HOP (dinh dang lay tu ma nguon 76134a52) + 1 dong [C3-LIVE] la => parser dem unmatched=1, V4b FAIL;
# bo dong la => V4b PASS (moi quy tac grep == parsed). Ket qua: $1 (json).
set -u
T=$(cd "$(dirname "$0")/.." && pwd); OUTJ=${1:-/dev/shm/add24/test_parser_v4b.json}
D=$(mktemp -d /dev/shm/add24/tp.XXXX)
cat > $D/ok.log <<'L'
01/01/2026 00:11:06.100 INFO  [x] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT AAAUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-AAAUSDT-29454490-0 qty=225 budget=22.5 legIdx=0 notional=22.5 U_before=0.0
01/01/2026 00:11:06.200 INFO  [x] c.b.c.c.x.C3LiveOrderExecutor: [C3-LIVE-EXEC] AAAUSDT c3-AAAUSDT-29454490-0 ACK thieu avgPrice => gia 0.1 tu stream sau 50 ms
01/01/2026 00:11:07.000 INFO  [x] c.b.c.c.f.FillAccounting: [C3-LIVE-FILL] xac nhan qua stream AAAUSDT c3-AAAUSDT-29454490-0 qty=225 avg=0.1 ref=0.1
01/01/2026 00:12:06.000 WARN  [x] c.b.c.c.e.C3LiveEntry: [C3-LIVE] KHONG vao lenh BBBUSDT PREDICT_SYMBOL_TRADE NO_EQUITY
01/01/2026 00:13:06.000 INFO  [x] c.b.c.c.e.TrailingStopManager: [C3-LIVE-TRAIL] arm AAAUSDT entry=0.1 px=0.107 peak=0.107 SL=0.104
01/01/2026 00:13:07.000 INFO  [x] c.b.c.c.e.TrailingStopManager: [C3-LIVE-TRAIL] AAAUSDT ARM stop=0.104 cid=c3s-AAAUSDT-1-1 mode=closePosition (cu=null 0)
01/01/2026 00:20:07.000 WARN  [x] c.b.c.c.e.TrailingStopManager: [C3-LIVE-TRAIL] AAAUSDT stop c3s-AAAUSDT-1-2 se kich ngay (-2021: gia da duoi stop) => dong MARKET reduce-only
01/01/2026 00:20:08.000 INFO  [x] c.b.c.c.b.LiveBookC3: [C3-LIVE-BOOK] dong cum AAAUSDT ly do=TRAIL legs=1 qty=225 avg=0.1 exitQty=225 exitAvg=0.103 realized=0.6 phi=0.02
01/01/2026 00:21:00.000 WARN  [x] c.b.c.a.MinuteCompletenessGuard: [MINUTE-INCOMPLETE] phut=20260101 00:20 co=10 can=99 trung_vi60du=100 ky_vong_ex=NA cho=0ms doc_lai=0 => KHONG mo lenh moi phut nay
01/01/2026 00:21:06.000 INFO  [x] c.b.c.t.DetectEntrySignal2TradeNormal: Btc ticker size: 1000 20251231 07:41 -> 20260101 00:20
01/01/2026 00:22:00.000 WARN  [x] c.b.c.c.r.C3MainEquity: [C3-LIVE-EQ] positions() loi IO => khong co equity c3 (chan mo moi, A40 giu trang thai)
01/01/2026 00:23:00.000 INFO  [x] c.b.c.c.r.C3LiveRuntime: [C3-LIVE] HOURLY cum=1 margin=1 pending=0
L
cp $D/ok.log $D/bad.log
echo '01/01/2026 00:30:00.000 WARN  [x] c.b.c.c.r.Foo: [C3-LIVE] dong moi khong co quy tac XYZ' >> $D/bad.log
r=()
for k in ok bad; do
  python3 -I $T/live_log_parse.py --log-files $D/$k.log --start '2026-01-01 00:00' --end '2026-01-01 02:00' --out $D/p_$k --mode full > /dev/null 2>&1
  bash $T/v4b.sh $D/p_$k/counts.json '2026-01-01 00:00' '2026-01-01 02:00' $D/v4b_$k.json $D/$k.log > $D/v4b_$k.txt 2>&1
done
python3 - "$D" "$OUTJ" <<'PY'
import json, sys, csv
d, o = sys.argv[1:3]
ok = json.load(open(d + '/v4b_ok.json')); bad = json.load(open(d + '/v4b_bad.json'))
blk = list(csv.DictReader(open(d + '/p_ok/block.csv'))); tick = list(csv.DictReader(open(d + '/p_ok/tick_dts.csv')))
c = json.load(open(d + '/p_ok/counts.json'))['counts']
res = {'v4b_ok_PASS': ok['ok'] is True, 'v4b_bad_FAIL': bad['ok'] is False and bad['unmatched_c3live_lines'] == 1,
       'parsed_each_rule_once': all(c[k]['parsed'] == 1 for k in ('SUBMIT', 'EXEC_ACK', 'FILL_STREAM', 'KHONG_VAO', 'TRAIL_arm', 'TRAIL_STOP', 'EXIT_2021', 'BOOK_CLOSE', 'INC_MIN', 'TICK', 'EQ_UNAVAIL')),
       'block_star_dts': len(blk) == 1 and blk[0]['symbol'] == '*' and int(blk[0]['decision_ts']) == int(tick[0]['dts'])}
res['ok'] = all(res.values())
json.dump(res, open(o, 'w'), indent=1); print(json.dumps(res))
sys.exit(0 if res['ok'] else 1)
PY
RC=$?; rm -rf $D; exit $RC
