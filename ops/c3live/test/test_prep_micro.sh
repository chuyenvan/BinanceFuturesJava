#!/usr/bin/env bash
# =============================================================================
# test_prep_micro.sh - chay THU dry_prep_micro_restart.sh voi "242 GIA" tren dia Oracle (SSH_242="bash -c", SCP_242=cp).
#   KHONG ssh, KHONG dung 242 that, KHONG goi Binance.   bash ops/c3live/test/test_prep_micro.sh <thu_muc_tam>
# Ket qua: "TEST PASS n/n" hoac "TEST FAIL ...".
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
W=${1:?"thieu thu muc tam"}; rm -rf "$W"; mkdir -p "$W"
PN="BinanceOrderTradingManager fake242prep"
cleanup() { pkill -f "$PN" 2>/dev/null; pkill -f "sleep 60; grep -q" 2>/dev/null; true; }
trap cleanup EXIT
F=$W/v_t_m; S=$W/shadow_c3
mkdir -p "$F/conf" "$F/bin" "$F/logs" "$F/run" "$F/target" "$S" "$W/deploylog" "$W/book"
cat > "$F/conf/env.sh" <<'EOF'
export LIVE_PROFILE=c3_live
export LIVE_ADAPTER=dry
export C3_CAPITAL=10000
export LIVE_SEED_EXCLUDE_DECISION_MIN=1
export LIVE_APPLY_GRID_RATIO=true
export LIVE_DCA_GRID_ENABLED=true
export TELEGRAM_BOT_TOKEN=faketokprep
EOF
echo "fake jar r4u3fin2 MINUTE-FIN" > "$F/target/binance-java-sdk-1.2.4.jar"
NJ=$(md5sum < "$F/target/binance-java-sdk-1.2.4.jar" | cut -c1-32)
TGS=$(printf %s faketokprep | sha256sum | cut -c1-8)
printf 'L1USDT\nL2USDT\nL3USDT\nL4USDT\nHANAUSDT\nZZUSDT\n' > "$F/run/legacy_symbols.csv"
cat > "$S/open_positions.csv" <<'EOF'
sym,ts_first,avg_entry,qty,rank,symbol_pred,price_sl,peak_rate,leg_count,first_entry,ts_last
#realized,100.5000000000,,,,,,,,,
L1USDT,1794664860000,0.5,200.0,-1,0.4,,0.0,1,0.5,1794664860000
HANAUSDT,1794664860000,1.0,100.0,25,0.2,,0.0,1,1.0,1794664860000
L2USDT,1794664860000,2.0,50.0,-1,0.3,,0.01,1,2.0,1794664860000
OKUSDT,1794664860000,4.0,25.0,5,0.1,,0.0,1,4.0,1794664860000
L3USDT,1794664860000,1.0,100.0,-1,0.3,,0.0,1,1.0,1794664860000
EOF
cat > "$W/grr.py" <<'EOF'
import sys, struct, zlib, time, numpy as np, snappy, datetime as dt
MAGIC = 0x47525231; REC = np.dtype([('t', '>i8'), ('r', '>f4')])
def enc(rec):
    c = snappy.compress(rec.astype(REC).tobytes()); return struct.pack('>IiI', MAGIC, len(c), zlib.crc32(c) & 0xffffffff) + c
def dec(b):
    i, out = 0, []
    while i + 12 <= len(b):
        mg, ln, crc = struct.unpack('>IiI', b[i:i + 12]); c = b[i + 12:i + 12 + ln]
        assert mg == MAGIC and len(c) == ln and zlib.crc32(c) & 0xffffffff == crc
        out.append(np.frombuffer(snappy.uncompress(c), REC)); i += 12 + ln
    assert i == len(b); return np.concatenate(out)
ms7 = lambda s: int((dt.datetime.fromisoformat(s) - dt.timedelta(hours=7)).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
m = sys.argv[1]
if m == 'gen':
    t0 = ms7('2026-10-01T13:00'); t1 = (int(time.time() * 1000) // 60000 - 30) * 60000
    ts = np.repeat(np.arange(t0, t1, 60000, dtype=np.int64), 2); rng = np.random.default_rng(1)
    r = (rng.random(len(ts)) * 0.007).astype(np.float32)
    w = (ts >= ms7('2026-10-30T03:40')) & (ts < ms7('2026-10-30T04:10')); r[w] = 0.02
    rec = np.zeros(len(ts), REC); rec['t'] = ts; rec['r'] = r
    open(sys.argv[2], 'wb').write(b''.join(enc(rec[i:i + 4096]) for i in range(0, len(rec), 4096)))
elif m == 'append':
    t = (int(time.time() * 1000) // 60000) * 60000; rec = np.zeros(6, REC); rec['t'] = [t - 120000] * 3 + [t - 60000] * 3; rec['r'] = 0.001
    open(sys.argv[2], 'ab').write(enc(rec))
elif m == 'rewrite':
    rec = dec(open(sys.argv[2], 'rb').read()); open(sys.argv[2], 'wb').write(enc(rec))
elif m == 'count':
    print(len(dec(open(sys.argv[2], 'rb').read())))
elif m == 'check':   # check <file> <n_expect>
    rec = dec(open(sys.argv[2], 'rb').read()); t = rec['t']
    nw = int(((t >= ms7('2026-10-30T03:40')) & (t < ms7('2026-10-30T04:10'))).sum())
    print('N=%d NW=%d SORTED=%s' % (len(t), nw, bool(np.all(np.diff(t) >= 0)))); sys.exit(0 if (nw == 0 and len(t) == int(sys.argv[3])) else 1)
EOF
python3 "$W/grr.py" gen "$F/run/gate_ratio_live.bin"
N0=$(python3 "$W/grr.py" count "$F/run/gate_ratio_live.bin")
cat > "$F/bin/daemon.sh" <<EOF
#!/usr/bin/env bash
cd "\$(dirname "\$0")/.."
case "\$1" in
  stop) pkill -f '$PN'; sleep 1
        [ -f FAKE_FLUSH ] && python3 $W/grr.py append run/gate_ratio_live.bin
        [ -f FAKE_REWRITE ] && { python3 $W/grr.py rewrite run/gate_ratio_live.bin; rm -f FAKE_REWRITE; } ;;
  start)
    set -a; . conf/env.sh; set +a
    nohup bash -c 'exec -a "$PN" sleep 900' >/dev/null 2>&1 &
    sleep 1; D=\$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000')
    NO=\$(grep -vcE '^(#|sym,)' $S/open_positions.csv); [ -f FAKE_BADOPEN ] && { NO=99; rm -f FAKE_BADOPEN; }
    RZ=\$(sed -n 's/^#realized,\([^,]*\),.*/\1/p' $S/open_positions.csv); RZ=\$(awk -v r="\$RZ" 'BEGIN{print r+0}')
    U=\$(awk -F, 'NR>1 && !/^#/ {s+=\$3*\$4} END{printf "%.4f", s/35100.5}' $S/open_positions.csv)
    GS=\$(python3 $W/grr.py count run/gate_ratio_live.bin)
    {
      echo "\$D WARN [main] x: [C3-LIVE] khoi dong adapter=\$(echo \$LIVE_ADAPTER | tr a-z A-Z) gateway=dry"
      echo "\$D INFO [main] x: [MINUTE-FIN] BAT - phut DU"
      echo "\$D INFO [x] x: [LIVE-DCA-GRID] LIVE_DCA_GRID_ENABLED=true profileC3=true applyRatio=true"
      echo "\$D INFO [x] x: [LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true"
      echo "\$D INFO [main] x: [C3-LIVE-RECON] khoi dong: ok=true closedWhileDown=[]"
      echo "\$D INFO [main] x: [GATE-RATIO] LIVE nap buffer: size=\$GS firstTs=20261001 13:00 (warm-up=armed)"
      echo "\$D INFO [x] x: ShadowBookC3: [SHADOW] so vi the giay khoi tao, ledger=x state=y open=\$NO realized=\$RZ paperEquity=35000.0"
      echo "\$D INFO [pool-3-thread-1] x: [LEGACY] managed 43: AAAUSDT,BBBUSDT"
      echo "\$D INFO [pool-1-thread-1] x: [GATE] scale=1.5500 topk=24 base=0.00800 n_cand=3 n_rej=3 n_pass=0 n_skipfull=0 u=\$U"
    } >> logs/full.log ;;
esac
EOF
chmod +x "$F/bin/daemon.sh"
D=$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000')
{ echo "$D INFO [pool-3-thread-1] x: [LEGACY] managed 43: AAAUSDT,BBBUSDT"; for i in 1 2 3 4 5 6; do echo "$D INFO [p] x: [GATE-RATIO] q_t=0.0069 q_t9=0.0069 buffer=$N0 eval=10 pass=0"; done; } > "$F/logs/full.log"
(cd "$F" && bin/daemon.sh start >/dev/null)
echo "{\"target_jar\": \"r4u3fin\", \"target_md5\": \"$NJ\"}" > "$W/gm.json"
# manifest phai khop (M5): chay ban sao script + lib + manifest tu thu muc tam (khong sua repo)
M=$W/ops; mkdir -p "$M"; cp -p "$HERE"/golive_lib.sh "$HERE"/dry_prep_micro_restart.sh "$HERE"/GOLIVE_MANIFEST.md5 "$M"/
for f in $(awk '{print $2}' "$HERE/GOLIVE_MANIFEST.md5"); do [ -e "$M/$f" ] || cp -p "$HERE/$f" "$M/"; done
SC=$M/dry_prep_micro_restart.sh
export PROC_PAT="$PN" SSH_242="bash -c" SCP_242=cp RHOST="" APP_DIR=$F SHADOW_DIR=$S LOGDIR=$W/deploylog WD_PAUSE=$W/PAUSE WD_PAUSE_MAX_S=60 \
  NJ_MD5=$NJ TG_SHA8=$TGS PURGE_SYMS=L1USDT,L2USDT,L3USDT,L4USDT EXP_EXCL_N=60 Q_LO=0 Q_HI=1 PAPER_EQ=35000 FORCE_TIME=1 MIN_MEM_MB=1 \
  POST_WAIT_S=2 POST_ROUNDS=3 RB_LOG_WAIT_S=10 RB_LOG_POLL_S=1 BOOK_SNAP_SH=$W/khong_co.sh BOOK_DIR=$W/book GMICRO_TARGET=$W/gm.json \
  DEPLOY_TG_ENV=$W/khong_co_tg.env DEPLOY_TG_SINK=$W/tg.txt GL_SSH_TRIES=1 SSH_RETRY_S=1 GATE_DIR=$W/gates
P=0; N=0
chk() { N=$((N + 1)); if eval "$2"; then P=$((P + 1)); echo "  ok  $1"; else echo "  FAIL $1"; echo "$OUT" | tail -25 | sed 's/^/       | /'; fi; }
m5() { md5sum < "$1" | cut -c1-32; }
# Oracle dung chung: test khac (test_fake242) co the chay process gia ten UserStreamSoak/C3LiveCanary => gl_state242 bao canary. Cho het (<=120 s).
qw() { local i; for i in $(seq 1 60); do [ "$(pgrep -fc 'C3LiveCanary|UserStreamSoak')" = 0 ] && return 0; sleep 2; done; echo "  (canary/soak ngoai test van chay)"; }
GM0=$(m5 "$F/run/gate_ratio_live.bin"); OM0=$(m5 "$S/open_positions.csv")
echo "== 1. DRY=1: chi doc, khong ghi 242 gia"
qw; OUT=$(DRY=1 bash "$SC" 2>&1); RC=$?
chk "DRY PASS, rc 0, 2 file khong doi, khong co file .prep_prefix" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ \$(m5 $F/run/gate_ratio_live.bin) = $GM0 ] && [ \$(m5 $S/open_positions.csv) = $OM0 ] && ! ls $F/run/*.prep_prefix_* >/dev/null 2>&1"
chk "DRY ke hoach: xoa 3 (L1,L2,L3), giu 2 (HANA,OK), bo 60 ban ghi" "echo \"\$OUT\" | grep -q 'XOA 3: L1USDT,L2USDT,L3USDT' && echo \"\$OUT\" | grep -q 'GIU 2: HANAUSDT,OKUSDT' && echo \"\$OUT\" | grep -q 'N_EXCL=60'"
echo "== 2. rank=-1 legacy NGOAI PURGE_SYMS => TU CHOI truoc YES"
sleep 1; qw; OUT=$(echo YES | PURGE_SYMS=L1USDT,L2USDT bash "$SC" 2>&1); RC=$?
chk "rc 1, BAD=L3USDT, khong doi file, bot khong restart" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"BAD='L3USDT'\" && [ \$(m5 $S/open_positions.csv) = $OM0 ] && [ \$(m5 $F/run/gate_ratio_live.bin) = $GM0 ]"
echo "== 3. so ban ghi bo != EXP_EXCL_N => TU CHOI"
sleep 1; qw; OUT=$(echo YES | EXP_EXCL_N=59 bash "$SC" 2>&1); RC=$?
chk "rc 1, khong doi file" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL so ban ghi bo = 60' && [ \$(m5 $F/run/gate_ratio_live.bin) = $GM0 ]"
echo "== 4. chay that, JVM flush 1 chunk luc stop (append-only) => XONG"
touch "$F/FAKE_FLUSH"
sleep 1; qw; OUT=$(echo YES | bash "$SC" 2>&1); RC=$?; rm -f "$F/FAKE_FLUSH"
TS4=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "rc 0 XONG, so giay con HANA+OK + header + #realized giu nguyen" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '=== XONG' && [ \$(grep -vcE '^(#|sym,)' $S/open_positions.csv) = 2 ] && grep -q '^HANAUSDT,' $S/open_positions.csv && grep -q '^OKUSDT,' $S/open_positions.csv && grep -qx '#realized,100.5000000000,,,,,,,,,' $S/open_positions.csv && [ \"\$(head -1 $S/open_positions.csv)\" = 'sym,ts_first,avg_entry,qty,rank,symbol_pred,price_sl,peak_rate,leg_count,first_entry,ts_last' ]"
chk "buffer moi: N = N0 + 6 (flush) - 60, 0 ban ghi cua so, sort tang, chunk sach" "python3 $W/grr.py check $F/run/gate_ratio_live.bin $((N0 + 6 - 60))"
chk "backup 2 file + md5 = ban goc (buffer backup = goc + chunk flush)" "[ \$(m5 $S/open_positions.csv.bak_prep_$TS4) = $OM0 ] && [ \"\$(cat $S/open_positions.csv.bak_prep_$TS4.md5)\" = $OM0 ] && [ \$(python3 $W/grr.py count $F/run/gate_ratio_live.bin.bak_prep_$TS4) = $((N0 + 6)) ]"
chk "hau kiem: SHADOW_open=2, U giay khop, 0 GATE-SEED, VERIFY=OK, smoke_start_ms ghi, PAUSE go" "echo \"\$OUT\" | grep -q 'OK SHADOW_open=2' && echo \"\$OUT\" | grep -q 'OK U_giay=' && echo \"\$OUT\" | grep -q 'OK 0_GATE-SEED' && echo \"\$OUT\" | grep -q 'VERIFY=OK' && python3 -c \"import json,sys; sys.exit(0 if len(str(json.load(open('$W/gm.json'))['smoke_start_ms']))==13 else 1)\" && [ ! -e $W/PAUSE ]"
chk "1 process sau XONG" "[ \$(pgrep -fc '$PN') = 1 ]"
# tra trang thai goc cho test sau
\cp -p "$S/open_positions.csv.bak_prep_$TS4" "$S/open_positions.csv"; python3 "$W/grr.py" gen "$F/run/gate_ratio_live.bin"; GM0=$(m5 "$F/run/gate_ratio_live.bin")
echo "== 5. buffer bi viet lai (prefix doi) giua luc tinh va stop => sua file loi => khoi phuc + start trang thai cu"
touch "$F/FAKE_REWRITE"; GMR=""
sleep 1; qw; OUT=$(echo YES | bash "$SC" 2>&1); RC=$?
TS5=$(echo "$OUT" | grep -o 'TS=[0-9_]*' | head -1 | cut -d= -f2)
chk "rc 1, FAIL prefix_buffer_doi, 2 file = backup (trang thai luc stop), so giay KHONG doi, 1 process" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'prefix_buffer_doi_tu_luc_tinh' && echo \"\$OUT\" | grep -q 'TU_CHOI sau stop' && [ \$(m5 $F/run/gate_ratio_live.bin) = \$(cat $F/run/gate_ratio_live.bin.bak_prep_$TS5.md5) ] && [ \$(m5 $S/open_positions.csv) = $OM0 ] && [ \$(pgrep -fc '$PN') = 1 ]"
python3 "$W/grr.py" gen "$F/run/gate_ratio_live.bin"; GM0=$(m5 "$F/run/gate_ratio_live.bin")
echo "== 6. hau kiem TRUOT (JVM bao open=99) => ROLLBACK 2 file + restart, adapter=dry"
touch "$F/FAKE_BADOPEN"
sleep 1; qw; OUT=$(echo YES | bash "$SC" 2>&1); RC=$?
chk "rc 1, FAIL SHADOW_open=99, Da ROLLBACK, 2 file ve goc, 1 process, PAUSE go" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL SHADOW_open=99' && echo \"\$OUT\" | grep -q 'Da ROLLBACK xong' && [ \$(m5 $F/run/gate_ratio_live.bin) = $GM0 ] && [ \$(m5 $S/open_positions.csv) = $OM0 ] && [ \$(pgrep -fc '$PN') = 1 ] && [ ! -e $W/PAUSE ]"
echo "== 7. script khong co trong manifest => TU CHOI (M5)"
cp -p "$SC" "$M/x.sh"; echo "# sua" >> "$SC"; qw; OUT=$(DRY=1 bash "$SC" 2>&1); RC=$?; \cp -p "$M/x.sh" "$SC"
chk "script bi sua khac manifest => TU CHOI rc 1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'TU CHOI \[M5\]'"
[ "$P" = "$N" ] && echo "TEST PASS $P/$N" || echo "TEST FAIL $P/$N"
