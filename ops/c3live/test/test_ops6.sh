#!/usr/bin/env bash
# =============================================================================
# test_ops6.sh - [OPS6] test tren 242 GIA (thu muc tam tren Oracle) cho: golive_pilot_on.sh (thanh cong, tung nhanh loi, ssh dut tung pha,
#   N1 ssh dut sau khi bot DA dung + owner drain, owner drain chen giua, KS nguoi khac, gate sai/het han/size, rollback A-02),
#   A-02 (mo phong logic dinh KillSwitchEngine jar hotfix luc khoi dong: ban OPS5 fa95289b = TRUOC sua, repo = SAU sua; ha 10000->1000,
#   10000->5000, tang 1000->10000), golive_make_gate_pilot.sh, boot guard T20 (install 2 lan, watchdog THAT + wrapper luc "boot", undrain, go cai).
#   bash ops/c3live/test/test_ops6.sh /tmp/<thu_muc>      => "TEST PASS n/n" | "TEST FAIL ... p/n"
# AN TOAN: SSH_242 = ssh GIA (chay cuc bo, tiem loi theo LOAI lenh); PATH dat ssh/scp CHAN (bat ky ssh/scp THAT nao => ghi log + rc 255, test FAIL).
#   KHONG 242, KHONG Binance (curl GIA), Telegram GIA (file), crontab GIA (file), systemd GIA (thu muc), python 242 = python3 Oracle.
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
REPO=$(cd "$HERE/../.." && pwd)
W=${1:?"thieu thu muc tam (/tmp/...)"}
case "$W" in /tmp/*) ;; *) echo "TEST FAIL: thu muc tam phai trong /tmp"; exit 1;; esac
chmod -R u+w "$W" 2>/dev/null; rm -rf "$W"; mkdir -p "$W"
git -C "$HERE" diff --quiet HEAD -- . || { echo "TEST FAIL: $HERE co sua CHUA commit (m1) - commit truoc"; exit 1; }
export A1_APPROVED_OPS=$W/a1_approved_ops.commit; git -C "$HERE" rev-parse HEAD > "$A1_APPROVED_OPS"
mkdir -p "$W/guardbin"; for b in ssh scp; do printf '#!/bin/bash\necho "%s $*" >> %s/guard_blocked.log\nexit 255\n' "$b" "$W" > "$W/guardbin/$b"; chmod +x "$W/guardbin/$b"; done
export PATH="$W/guardbin:$PATH"
TID=o6_$$; PN="BinanceOrderTradingManager fk_$TID"
cleanup() {
  local p L
  for p in $(ls /proc | grep -E '^[0-9]+$'); do
    [ "$p" = $$ ] && continue; [ -O "/proc/$p" ] || continue
    L=$( { tr '\0' ' ' < /proc/$p/cmdline; echo; readlink /proc/$p/cwd; } 2>/dev/null)
    case "$L" in *"$W"*|*"fk_$TID"*) case " $(ps -o ppid= -p $$ 2>/dev/null) $$ " in *" $p "*) ;; *) kill -9 "$p" 2>/dev/null;; esac;; esac
  done; :
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
N=0; P=0; FAILS=""
chk() { N=$((N + 1)); if eval "$2"; then P=$((P + 1)); echo "PASS $N $1"; else FAILS="$FAILS #$N"; echo "FAIL $N $1"; printf '%s\n' "${OUT:-}" | grep -E 'FAIL|DUNG|KHAN|TU CHOI|WAIT|XONG|ROLLBACK|unbound|a02|TU_CHOI' | tail -12 | sed 's/^/     | /'; fi; }
# ---------------------------------------------------------------- 242 gia
F=$W/v_t_m; mkdir -p "$F/conf" "$F/bin" "$F/logs" "$F/run" "$F/target" "$W/deploy/run" "$W/gates" "$W/api" "$W/py/bin"
ln -s "$(command -v python3)" "$W/py/bin/python3"
SKEY=fakekey_o6_$(printf '%030d' 7); printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=fakesecret_o6_%030d\n' "$SKEY" 9 > "$W/keys_sub.env"; chmod 600 "$W/keys_sub.env"
SK8=$(printf '%s' "$SKEY" | sha256sum | cut -c1-8)
cat > "$W/env.micro" <<EOT
export LIVE_PROFILE=c3_live
export LIVE_KILLSW_MODE=act
# [v1.2 golive_micro_on 20261119_093053] MICRO-LIVE
export LIVE_ADAPTER=live
export C3_CAPITAL=1000
export SHADOW_NO_PUSH=false
export LIVE_ENTRY_ENABLED=true
export LIVE_C3_KEYS_FILE=$W/keys_sub.env
export C3_EXCLUDE_LEGACY_HELD=false
export LIVE_APPLY_GRID_RATIO=true
export LIVE_DCA_GRID_ENABLED=true
export LIVE_SEED_EXCLUDE_DECISION_MIN=1
EOT
echo 'JAR hotfix gia o6' > "$F/target/binance-java-sdk-1.2.4.jar"; JM=$(md5sum < "$F/target/binance-java-sdk-1.2.4.jar" | cut -c1-32)
echo "$PN" > "$F/FAKE_PN"; echo "$W/ksim.py" > "$F/FAKE_KSIM"; echo "$W/PAUSE" > "$F/FAKE_PAUSE_PATH"
# --- mo phong KillSwitchEngine (jar hotfix) LUC KHOI DONG + danh gia equity dau tien. Trich logic (v1.2/hotfix-ks 76134a52):
#   constructor: loadPeak() -> loadLatch() -> checkResetRequest() (KillSwitchEngine.java:398-402)
#   loadPeak :409-436 file run/c3live_killsw_peak "<so> adapter=<tag>", tag = adapterTag(LIVE_ADAPTER)+"_c3eq" (OpsHooks.java:91,96); tag khac => bo
#   loadLatch :999-1063 "acct_peak" chi nap khi "acct_peak_adapter" == tag ; checkResetRequest :1090-1153 reset_peak=1 => peak/acctPeak NaN + xoa file dinh
#   equity c3 = C3_CAPITAL + realized + funding + upl (C3MainEquity.java:146) - o day = C3_CAPITAL + FAKE_PNL
#   C6 onBookOwnPeak :711-728 (peak = max(peak, eq), dd = eq/peak - 1), A40 onAccountEquity :549-568 (acctPeak tuong tu); dd <= -0.40 => FLATTEN
cat > "$W/ksim.py" <<'PYS'
import json, math, os
tag = (os.environ.get("LIVE_ADAPTER", "").strip().lower() or "off") + "_c3eq"
cap = float(os.environ.get("C3_CAPITAL", "10000"))
pnl = float(open("FAKE_PNL").read()) if os.path.exists("FAKE_PNL") else 0.0
PF, LF, RQ = "run/c3live_killsw_peak", "run/killsw_latch.json", "run/killsw_reset.req"
nan = float("nan"); peak = nan; acct = nan; o = {"version": 1, "latch": "NONE", "codes": [], "c2_events_ms": []}; src = []
if os.path.exists(PF):
    t = open(PF).read().split()
    tg = [x[8:] for x in t if x.startswith("adapter=")]
    if tg and tg[-1] == tag and float(t[0]) > 0: peak = float(t[0]); src.append("peak_file=%s" % t[0])
    else: src.append("peak_file_bo_qua(tag)")
if os.path.exists(LF):
    o = json.load(open(LF))
    if "acct_peak" in o and o.get("acct_peak_adapter") == tag: acct = float(o["acct_peak"]); src.append("acct_peak=%s" % o["acct_peak"])
if os.path.exists(RQ):
    r = json.load(open(RQ)); o["latch"] = "NONE"; o["codes"] = []; o["c2_events_ms"] = []
    if int(r.get("reset_peak", 0)) == 1:
        peak = nan; acct = nan
        if os.path.exists(PF): os.remove(PF)
    os.rename(RQ, RQ + ".done_sim"); src.append("reset_req(reset_peak=%s)" % r.get("reset_peak"))
eq = cap + pnl
peak = eq if math.isnan(peak) or eq > peak else peak
acct = eq if math.isnan(acct) or eq > acct else acct
dd = eq / peak - 1.0; dda = eq / acct - 1.0
fl = dd <= -0.40 + 1e-12 or dda <= -0.40 + 1e-12
print("[KILLSW-SIM] tag=%s nap=[%s] eq=%.2f peak_C6=%.2f dd_C6=%.4f acct_peak_A40=%.2f dd_A40=%.4f => %s" % (tag, " ".join(src) or "-", eq, peak, dd, acct, dda, "FLATTEN" if fl else "OK"))
if fl:
    print("[KILLSW] LATCH action=FLATTEN (truoc %s) code=C6 codes=[C6] detail=dd=%.4f eq=%.2f peak=%.2f" % (o.get("latch"), dd, eq, peak))
    o["latch"] = "FLATTEN"; o["codes"] = ["C6"]
open(PF, "w").write("%s adapter=%s\n" % (peak, tag))
o["acct_peak"] = acct; o["acct_peak_adapter"] = tag; o["adapter"] = tag
open(LF, "w").write(json.dumps(o, separators=(",", ":")) + "\n")
print("[KILLSW] HOURLY hour=sim mode=act open=0 U=0.0000 eq=%.2f peak=%.2f dd=%.4f acct_eq=%.2f acct_peak=%.2f acct_dd=%.4f latch=%s" % (eq, peak, dd, eq, acct, dda, o.get("latch")))
open("run/ksim_last.txt", "w").write("eq=%.2f dd_C6=%.4f dd_A40=%.4f %s\n" % (eq, dd, dda, "FLATTEN" if fl else "OK"))
PYS
cat > "$F/bin/daemon.sh" <<'EOD'
#!/usr/bin/env bash
cd "$(dirname "$0")/.."
PN=$(cat FAKE_PN)
case "$1" in
  stop) [ -f FAKE_NOSTOP ] && exit 0
    [ -f FAKE_PAUSE_PATH ] && echo "STOP PAUSE=$(head -c 40 "$(cat FAKE_PAUSE_PATH)" 2>/dev/null | tr -d '\n')" >> run/stop_trace.txt
    pkill -f "$PN"; sleep 0.3; pkill -9 -f "$PN"; :
    [ -f FAKE_DRAIN_ON_STOP ] && { rm -f FAKE_DRAIN_ON_STOP; echo "golive_live_off drain 20990101_000002" > run/KILL_SWITCH; }
    [ -f FAKE_KILL_AFTER_STOP ] && { rm -f FAKE_KILL_AFTER_STOP; kill -9 $PPID; }
    : ;;
  start)
    if [ -f FAKE_KILL_ON_START ]; then rm -f FAKE_KILL_ON_START
      [ -f FAKE_DRAIN_ON_KILL ] && { rm -f FAKE_DRAIN_ON_KILL; echo "golive_live_off drain 20990101_000003" > run/KILL_SWITCH; }
      [ -f FAKE_WD_START_ON_KILL ] && { rm -f FAKE_WD_START_ON_KILL; bash bin/daemon.sh start >/dev/null 2>&1; }   # "watchdog" start TRUOC khi ssh chet
      kill -9 $PPID; exit 0; fi
    set -a; . conf/env.sh; set +a; export PN
    D=$(TZ=Asia/Ho_Chi_Minh date '+%d/%m/%Y %H:%M:%S.000')
    SIM=$(python3 -I "$(cat FAKE_KSIM)" 2>&1)
    nohup bash -c 'exec -a "$PN" sleep 900' >/dev/null 2>&1 &
    sleep 0.5
    PUSHV=OFF; [ ! -e run/KILL_SWITCH ] && PUSHV=ON
    {
      echo "$D INFO [main] x: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager"
      echo "$D WARN [main] x: [LIVE_PROFILE=c3_live] BAT - hanh vi C3 day du PUSH=$PUSHV (SHADOW_NO_PUSH=${SHADOW_NO_PUSH:-})"
      echo "$D INFO [x] x: [LIVE-DCA-GRID] LIVE_DCA_GRID_ENABLED=true profileC3=true levels=[-0.5] legs=3 weights=[1.0] scale=6.0 applyRatio=true"
      echo "$D INFO [x] x: [LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true - gia lap"
      echo "$D WARN [main] x: [C3-LIVE] khoi dong adapter=LIVE gateway=c3scope(live) book=run/c3live_book.json cum=18 c3_capital=${C3_CAPITAL:-?}.0 tai_khoan=CHINH(pham vi c3) killSwitchArmed=true"
      printf '%s\n' "$SIM" | sed "s|^|$D WARN [main] x: |"
      echo "$D INFO [C3LIVE-STREAM] x: [C3-LIVE-STREAM] da ket noi"
      echo "$D INFO [main] x: [C3-LIVE-RECON] khoi dong: ok=true closedWhileDown=[]"
      [ -f FAKE_KHAN_IF_CAP ] && [ "$(cat FAKE_KHAN_IF_CAP)" = "${C3_CAPITAL:-}" ] && echo "$D ERROR [x] x: [C3-LIVE] KHAN gia lap (von ${C3_CAPITAL})"
      [ -f FAKE_ORDERS ] && cat FAKE_ORDERS
    } >> logs/full.log
    if [ "$PUSHV" = OFF ] && [ ! -f FAKE_NOPUSHON ]; then
      nohup bash -c 'for i in $(seq 1 300); do sleep 1; [ -e run/KILL_SWITCH ] || { echo "$(TZ=Asia/Ho_Chi_Minh date "+%d/%m/%Y %H:%M:%S.000") WARN [x] x: [C3-LIVE] PUSH doi trang thai -> ON" >> logs/full.log; exit 0; }; done' >/dev/null 2>&1 &
    fi ;;
esac
EOD
chmod +x "$F/bin/daemon.sh"
# --- ssh GIA (nhu test_swap_jar): lenh ghi ra file roi exec (cmdline khong chua mau PROC_PAT); PLAN "<LOAI> before|after <n>" => rc 255
cat > "$W/fakessh.sh" <<'EOS'
#!/usr/bin/env bash
T=$(mktemp "$FAKESSH_PLAN.cmd.XXXXXX"); printf '%s' "$*" > "$T"; exec bash "${FAKESSH_PLAN%/*}/fakessh2.sh" "$T"
EOS
cat > "$W/fakessh2.sh" <<'EOS'
#!/usr/bin/env bash
CF=$1; CMD=$(cat "$CF"); rm -f "$CF"; IN=""; [ -t 0 ] || IN=$(cat)
C=OTHER
case "$IN" in *END_RS*) C=RESTART;; *END_RB*) C=ROLLBACK;; *END_CHK*) C=CHK;; *END_STATE*) C=STATE;; *END_API*) C=API;; *END_KSU*) C=KSU;; esac
case "$CMD" in *END_PHASE*) C=PHASE;; *END_BG*) C=BG;; *"PUSH doi trang thai"*) C=PUSHWAIT;; *KILL_SWITCH.ok_*) C=KSOFF;; *KSR=*) C=KSRESTORE;; esac
echo "$C" >> "${FAKESSH_PLAN}.log"
M=""; if [ -f "$FAKESSH_PLAN" ]; then
  L=$(grep -m1 "^$C " "$FAKESSH_PLAN"); if [ -n "$L" ]; then set -- $L; n=$3
    if [ "$n" -gt 0 ]; then M=$2; sed -i "0,/^$C .*/s//$C $2 $((n - 1))/" "$FAKESSH_PLAN"; fi; fi; fi
[ "$M" = before ] && exit 255
printf '%s' "$IN" | bash -c "$CMD"; rc=$?
[ "$M" = after ] && exit 255
exit $rc
EOS
touch "$W/sshplan"
cat > "$W/fakecurl.sh" <<EOC
#!/bin/bash
cfg=\$(cat); u=\$(printf '%s' "\$cfg" | sed -n 's/^url = "\([^"?]*\).*/\1/p'); n=\${u##*/}
p=\${u%/*}; n2=\${p##*/}_\$n; [ -f "$W/api/\$n2.json" ] && n=\$n2
printf '%s' "\$cfg" | grep -q 'X-MBX-APIKEY: fakekey_' || { printf '{"code":-2015}\nHTTP=401'; exit 0; }
c=200; [ -f "$W/api/\$n.code" ] && c=\$(cat "$W/api/\$n.code")
printf 'HTTP/1.1 %s\r\nx-mbx-used-weight-1m: 77\r\n\r\n' "\$c" >&2
cat "$W/api/\$n.json" 2>/dev/null; printf '\nHTTP=%s' "\$c"
EOC
chmod +x "$W/fakecurl.sh"
api() { printf '%s' "$2" > "$W/api/$1.json"; }
api account '{"totalMarginBalance":"10979.20","availableBalance":"10500.00","assets":[{"asset":"USDT","walletBalance":"1008.00","marginBalance":"1008.00","marginAvailable":true},{"asset":"BFUSD","walletBalance":"10000","marginBalance":"9971.2","marginAvailable":true}]}'
api multiAssetsMargin '{"multiAssetsMargin":true}'; api dual '{"dualSidePosition":false}'; api positionRisk '[]'; api openOrders '[]'; api openAlgoOrders '[]'
api apiRestrictions '{"ipRestrict":true,"enableWithdrawals":false,"enableFutures":true,"enableReading":true}'
# --- crontab GIA Oracle + 242, sbin / systemd GIA (boot guard), watchdog gia ho tro WD_PRESTART
cat > "$W/oracron.sh" <<EOC
case "\$1" in -l) [ -f $W/oracron.txt ] && cat $W/oracron.txt || { echo "no crontab" >&2; exit 1; } ;; -) cat > $W/oracron.txt ;; *) exit 2 ;; esac
EOC
echo '*/5 * * * * /home/ubuntu/ops/health_242.sh # HEALTH' > "$W/oracron.txt"
SB=$W/sbin; mkdir -p "$SB" "$W/systemd"
# [luot3 m-5] systemctl GIA CO TRANG THAI: daemon-reload nap drop-in (tru khi $W/fsc_broken); show -p ExecStartPre in theo trang thai nap
cat > $W/fsc.sh <<EOF5
#!/bin/bash
DFX=$W/systemd/h242-trading.service.d/c3-autodrain.conf
case "\$1" in
  daemon-reload) if [ -f \$DFX ] && [ ! -f $W/fsc_broken ]; then grep '^ExecStartPre=.' \$DFX | tail -1 | sed 's/^ExecStartPre=//; s/ .*//' > $W/fsc_state; else echo $SB/h242-prestart.sh > $W/fsc_state; fi ;;
  show) p=\$(cat $W/fsc_state 2>/dev/null || echo $SB/h242-prestart.sh); echo "ExecStartPre={ path=\$p ; argv[]=\$p x y ; ignore_errors=no ; start_time=[n/a] ; status=0/0 }" ;;
esac
EOF5
printf '#!/bin/bash\necho "deps ok (gia)"\nexit 0\n' > "$SB/h242-prestart.sh"; chmod 755 "$SB/h242-prestart.sh"
printf '#!/bin/bash\nPRESTART=${WD_PRESTART:-/usr/local/sbin/h242-prestart.sh}\n' > "$SB/h242_watchdog.sh"
printf '#!/bin/bash\ncase "$1" in -l) cat %s/ct242 2>/dev/null;; -) cat > %s/ct242;; esac\n' "$W" "$W" > "$W/ct242.sh"
printf '*/2 * * * * %s/h242_watchdog.sh >> /var/lib/h242_watchdog/cron.out 2>&1\n3,18,41,48 * * * * cd /x && bash exinfo.sh # C3LIVE_EXINFO\n' "$SB" > "$W/ct242"; cp "$W/ct242" "$W/ct242_0"
# --- prereg repo GIA (quyet dinh owner + mien)
PR=$W/prereg; mkdir -p "$PR/docs/prereg"; git -C "$PR" init -q
echo "Q1 10000 Q2 jar hotfix Q3 g_exec/g_exit Q4_OWNER Q4 boot guard" > "$PR/docs/prereg/OWNER_DECISION_PILOT_1121_ADD1.md"
git -C "$PR" add -A; git -C "$PR" -c user.name=t -c user.email=t@t commit -qm od; ODC=$(git -C "$PR" rev-parse HEAD)
echo "mien X14 B2 C1 (test)" > "$PR/docs/prereg/OWNER_DECISION_MIEN_TEST.md"; git -C "$PR" add -A; git -C "$PR" -c user.name=t -c user.email=t@t commit -qm mien; MRC=$(git -C "$PR" rev-parse --short HEAD)
printf 'golive_check_lev SUB t key_sha8=x KET QUA: DAT\nvon_kiem=10000\n' > "$W/lev10000.txt"
echo "bang chung g_exec (test): 73 leg" > "$W/ev_gexec.md"; echo "bang chung g_exit (test): 12 lenh thoat" > "$W/ev_gexit.md"
export SSH_242="bash $W/fakessh.sh" FAKESSH_PLAN=$W/sshplan SCP_242=false RHOST="" APP_DIR=$F PROC_PAT="$PN" WD_PAUSE=$W/PAUSE WD_PAUSE_MAX_S=300 \
  LOGDIR=$W/deploy GATE_DIR=$W/gates GL_MON_FLAG=$W/deploy/golive_monitor.on KEYS_FILE=$W/keys_sub.env SUB_KEY_SHA8=$SK8 C3_ACCOUNT=SUB \
  PY242=$W/py/bin/python3 CURL242=$W/fakecurl.sh DEPLOY_TG_SINK=$W/tg.txt NJ_MD5=$JM ING_PAT=o6_khong_co_ingestor_$$ CANARY_PAT=canary_early_o6_NONE_$$ \
  ORA_CRONTAB_CMD="bash $W/oracron.sh" MON_PIN_ROOT=$W/pinned MON_LOCK=$W/locks/golive_monitor.lock \
  AD_SBIN=$SB AD_SYSTEMD_DIR=$W/systemd AD_SYSTEMCTL="bash $W/fsc.sh" AD_CT242="bash $W/ct242.sh" \
  POST_WAIT_S=1 POST_ROUNDS=4 SSH_RETRY_S=0 FORCE_TIME=1 MIN_MEM_MB=100 RB_LOG_WAIT_S=10 RB_LOG_POLL_S=1 PREREG_REPO=$PR \
  GL_TEST=1 LEV_EV=$W/lev10000.txt GL_MICRO_START="$(date -d '8 days ago' '+%F %T %z')"   # [luot3 m-7] ghi de CHI hieu luc khi GL_TEST=1
np() { pgrep -fc "$PN"; }
pid() { pgrep -f "$PN" | head -1; }
penv() { tr '\0' '\n' < /proc/$(pid)/environ 2>/dev/null; }
envcap() { sed -n 's/^export C3_CAPITAL=//p' "$F/conf/env.sh" | tail -1; }
nosec() { ! printf '%s' "$1" | grep -q "$SKEY\|fakesecret_o6" && ! grep -rqs "$SKEY\|fakesecret_o6" "$W/deploy" "$W/tg.txt" "$W/gates"; }
cat "$HERE/golive_monitor.sh" "$HERE/golive_lib.sh" | md5sum | cut -c1-12 | sed 's/$/ test_ops6/' > "$W/gates/A1_APPROVED_MONITOR.md5"
bash "$HERE/install_cron_golive_monitor.sh" > "$W/install_cron.out" 2>&1 || { echo "TEST FAIL: khong cai duoc cron monitor GIA"; cat "$W/install_cron.out" | tail -5; exit 1; }
# micro dang chay: von 1000, so live, dinh 1005 (jar da day dinh), latch NONE, co micro dry_ts, heartbeat monitor
reset242() {   # $1 = C3_CAPITAL dinh trong file dinh (mo phong JVM micro da chay)
  bash "$F/bin/daemon.sh" stop >/dev/null 2>&1; sleep 0.3
  rm -f "$F"/run/KILL_SWITCH* "$F"/run/.golive_* "$F"/run/*.a02_* "$F"/run/killsw_reset.req* "$F"/conf/env.sh.bak_* "$F"/FAKE_[A-JL-OQ-Z]* "$F/FAKE_KHAN_IF_CAP" "$F/FAKE_KILL_AFTER_STOP" "$F/FAKE_KILL_ON_START" "$F/FAKE_NOSTOP" "$F/FAKE_PNL" "$W/PAUSE"
  echo "$PN" > "$F/FAKE_PN"; echo "$W/ksim.py" > "$F/FAKE_KSIM"
  cp "$W/env.micro" "$F/conf/env.sh"
  printf '%s adapter=live_c3eq\n' "${1:-1005}" > "$F/run/c3live_killsw_peak"
  printf '{"version":1,"latch":"NONE","codes":[],"since_ms":0,"detail":"-","c2_events_ms":[],"acct_peak":%s,"acct_peak_adapter":"live_c3eq","adapter":"live_c3eq","last_reset_at_ms":0,"updated_ms":1}\n' "${1:-1005}" > "$F/run/killsw_latch.json"
  : > "$W/sshplan"; : > "$W/tg.txt"; rm -f "$W/sshplan.log"
  printf 'C3_ACCOUNT=SUB\nKEYS_FILE=%s\nby=golive_micro_on TS=20261119_093053\ndry_ts=20261119_093053\n' "$W/keys_sub.env" > "$W/deploy/golive_monitor.on"
  touch "$W/deploy/run/monitor_heartbeat"
  printf 'tmb0=10979.20\nc3_capital=1000\nkey_sha8=%s\nbase_id=micro_test\nrebase_t=%s\nreason=micro test\n' "$SK8" "$(date +%s)" > "$W/deploy/c3sub_eq_base.txt"; cp -p "$W/deploy/c3sub_eq_base.txt" "$W/eqbase0"
  (cd "$F" && bin/daemon.sh start >/dev/null 2>&1); sleep 0.5
}
reset242 1005
# =============================================================================== T20 boot guard: cai (DRY / that / lan 2)
echo "== T20 boot guard: install_242_autodrain (242 gia)"
MGE() { env PILOT_SIZE=10000 OWNER_DECISION=$ODC G_EXEC="Q4_OWNER n=73 ref=$MRC 73/100 leg that (test)" G_EXEC_EV=$W/ev_gexec.md \
  G_EXIT="Q4_OWNER n=12 ref=$MRC thieu mau thoat (test)" G_EXIT_EV=$W/ev_gexit.md MIEN_X14="MIEN ref=$MRC owner mien X14 (test)" \
  MIEN_B2="MIEN ref=$MRC owner mien B2 (test)" MIEN_C1="MIEN ref=$MRC owner mien C1 (test)" "$@"; }   # GL_MICRO_START: export chung (8 ngay truoc)
OUT=$(MGE DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "T12b make_gate_pilot: boot guard CHUA cai => TU CHOI (T20 bat buoc)" '[ $RC = 1 ] && echo "$OUT" | grep -q "boot guard T20 CHUA CAI"'
OUT=$(DRY=1 bash "$HERE/install_242_autodrain.sh" 2>&1 < /dev/null); RC=$?
chk "T20 install DRY=1: in ke hoach, KHONG doi cron 242 / sbin / systemd" '[ $RC = 0 ] && echo "$OUT" | grep -q "DRY PASS" && cmp -s $W/ct242 $W/ct242_0 && [ ! -e $SB/h242-prestart-c3.sh ] && [ ! -e $W/systemd/h242-trading.service.d ]'
B0=$(pid)
OUT=$(echo YES | bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
DF=$W/systemd/h242-trading.service.d/c3-autodrain.conf
chk "T20 install: wrapper = c3_autodrain_prestart.sh repo, cron watchdog WD_PRESTART, drop-in ExecStartPre (reset + wrapper), KHONG restart bot" '[ $RC = 0 ] && cmp -s $HERE/c3_autodrain_prestart.sh $SB/h242-prestart-c3.sh && grep -q "WD_PRESTART=$SB/h242-prestart-c3.sh $SB/h242_watchdog.sh" $W/ct242 && grep -q C3LIVE_EXINFO $W/ct242 && grep -qx "ExecStartPre=" $DF && grep -qx "ExecStartPre=$SB/h242-prestart-c3.sh $F com.binance.chuyennd.trading.BinanceOrderTradingManager" $DF && [ "$(pid)" = "$B0" ]'
C1=$(md5sum < $W/ct242)
OUT=$(echo YES | bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
chk "T20 install lan 2 => KHONG DOI (idempotent), cron 242 byte-giong" '[ $RC = 0 ] && echo "$OUT" | grep -q "KHONG DOI (da cai dung" && [ "$(md5sum < $W/ct242)" = "$C1" ]'
# =============================================================================== T12b make_gate_pilot
echo "== T12b golive_make_gate_pilot.sh"
G=$W/gates/GOLIVE_GATE_PILOT.ok
OUT=$(MGE DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate DRY: du bang chung => in gate, KHONG ghi file" '[ $RC = 0 ] && echo "$OUT" | grep -q "^boot_guard=CAI" && echo "$OUT" | grep -q "DRY=1: KHONG ghi" && [ ! -e $G ]'
OUT=$(env PILOT_SIZE=10000 OWNER_DECISION=$ODC G_EXEC="Q4_OWNER n=73 ref=$MRC x" G_EXEC_EV=$W/ev_gexec.md G_EXIT="Q4_OWNER n=12 ref=$MRC x" G_EXIT_EV=$W/ev_gexit.md MIEN_X14="MIEN ref=$MRC t" MIEN_B2="MIEN ref=$MRC t" MIEN_C1="MIEN ref=$MRC t" GL_MICRO_START="2026-11-19 09:31:00 +07" bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: moc micro THAT 2026-11-19 09:31 +07 (hom nay < 7 ngay), khong MIEN_MICRO7 => TU CHOI, khong ghi" '[ $RC = 1 ] && echo "$OUT" | grep -q "micro moi .* ngay < 7 ke tu 2026-11-19 09:31:00 +07" && [ ! -e $G ]'
OUT=$(env PILOT_SIZE=10000 OWNER_DECISION=$ODC G_EXEC="Q4_OWNER n=73 ref=$MRC x" G_EXEC_EV=$W/ev_gexec.md G_EXIT="Q4_OWNER n=12 ref=$MRC x" G_EXIT_EV=$W/ev_gexit.md MIEN_X14="MIEN ref=$MRC t" MIEN_B2="MIEN ref=$MRC t" MIEN_C1="MIEN ref=$MRC t" MIEN_MICRO7="MIEN ref=$MRC owner mien 7 ngay (test)" GL_MICRO_START="2026-11-19 09:31:00 +07" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: micro < 7 ngay + MIEN_MICRO7 owner (ref commit) => chap nhan, ghi micro7=MIEN_OWNER" '[ $RC = 0 ] && echo "$OUT" | grep -q "micro7=MIEN_OWNER MIEN ref=$MRC"'
for v in MIEN_X14 MIEN_B2 MIEN_C1; do
  OUT=$(MGE $v= DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
  chk "make_gate: thieu $v (chua co quyet dinh owner) => TU CHOI (khong mac dinh)" '[ $RC = 1 ] && echo "$OUT" | grep -q "$v=.* CHUA co quyet dinh owner"'
done
OUT=$(MGE MIEN_B2="MIEN ref=deadbeef0 sai" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: MIEN_B2 ref khong phai commit prereg => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "MIEN_B2 ref=deadbeef0 khong phai commit"'
OUT=$(MGE G_EXEC="Q4_OWNER ref=$MRC khong co n" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: g_exec Q4_OWNER thieu n=<so mau thuc te> => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "G_EXEC Q4_OWNER thieu n="'
OUT=$(MGE G_EXIT="Q4_OWNER n=12 khong co ref" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: g_exit Q4_OWNER thieu ref=<commit owner> => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "G_EXIT Q4_OWNER thieu ref="'
OUT=$(MGE G_EXIT="TRUOT 45 0.6 20 test" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: g_exit=TRUOT => TU CHOI (ADD3)" '[ $RC = 1 ] && echo "$OUT" | grep -q "G_EXIT=TRUOT"'
OUT=$(MGE G_EXEC_EV=$W/khong_co.md DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: file bang chung g_exec thieu => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "G_EXEC_EV=.* thieu"'
for s in "" 7000 1000 100000; do
  OUT=$(MGE PILOT_SIZE=$s DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
  chk "make_gate: size='$s' (chi nhan 5000|10000, bat buoc) => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "PILOT_SIZE"'
done
OUT=$(MGE OWNER_DECISION=1234567 DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: OWNER_DECISION khong phai commit => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "OWNER_DECISION=.* khong phai commit"'
OUT=$(MGE NJ_MD5=00000000000000000000000000000000 DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate: jar DANG chay != NJ_MD5 => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "jar DANG chay .* != NJ_MD5"'
cp -p $F/run/killsw_latch.json $W/latch.bak; sed -i 's/"latch":"NONE"/"latch":"NO_NEW_ENTRY"/' $F/run/killsw_latch.json
OUT=$(MGE DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?; cp -p $W/latch.bak $F/run/killsw_latch.json
chk "make_gate: latch != NONE => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "latch kill-switch = NO_NEW_ENTRY"'
printf 'x\n' >> $SB/h242-prestart-c3.sh
OUT=$(MGE DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?; cp $HERE/c3_autodrain_prestart.sh $SB/h242-prestart-c3.sh
chk "make_gate: wrapper boot guard tren 242 KHAC ban repo (md5) => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "boot guard T20 CHUA CAI"'
OUT=$(MGE bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "make_gate THAT: ghi gate (umask 077), qua gl_gate_pilot, co size/g_exec/g_exit/mien/owner_decision/so lenh/boot_guard/body_sha256" '[ $RC = 0 ] && [ "$(stat -c %a $G)" = 600 ] && grep -qx "size=10000" $G && grep -q "^owner_decision=$ODC file=docs/prereg/OWNER_DECISION_PILOT_1121_ADD1.md sha256=" $G && grep -q "^so_lenh_that_luc_tao=vao_FILLED:" $G && grep -q "^g_exec_ev=$W/ev_gexec.md sha256=" $G && tail -1 $G | grep -qE "^body_sha256=[0-9a-f]{64}$" && echo "$OUT" | grep -q "OK gate PILOT"'
cp -p $G $W/gate_ok
# gate sua tay / het han / size / thieu truong => pilot_on TU CHOI (DRY)
regate() { python3 - "$1" "$2" "$3" <<'PYG'
import hashlib, sys, re
src, out, ops = sys.argv[1], sys.argv[2], sys.argv[3]
L = open(src).read().rstrip("\n").split("\n")[:-1]
for op in ops.split(";"):
    if not op: continue
    k, v = op.split("=", 1)
    L = [x for x in L if not x.startswith(k + "=")] + ([k + "=" + v] if v != "DEL" else [])
b = "\n".join(L) + "\n"
open(out, "w").write(b + "body_sha256=" + hashlib.sha256(b.encode()).hexdigest() + "\n")
PYG
}
pd() { OUT=$(DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?; }
rm -f $G; pd
chk "pilot_on DRY: thieu gate => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "chua co cong G-PILOT hop le"'
sed 's/^size=10000$/size=10001/' $W/gate_ok > $G; pd
chk "pilot_on: gate bi SUA TAY (size, khong tinh lai sha) => TU CHOI body_sha256" '[ $RC = 1 ] && echo "$OUT" | grep -q "body_sha256_sai"'
regate $W/gate_ok $G "created_ms=$(( ($(date +%s) - 200000) * 1000 ))"; pd
chk "pilot_on: gate HET HAN (tao > 48 h) => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "het_han"'
regate $W/gate_ok $G "expires_ms=$(( ($(date +%s) - 10) * 1000 ))"; pd
chk "pilot_on: gate expires_ms da qua => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "expires_ms_da_qua"'
regate $W/gate_ok $G "size=20000"; pd
chk "pilot_on: gate size=20000 (ngoai 5000|10000) => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "size=.20000._ngoai"'
regate $W/gate_ok $G "jar_md5=6418035652970000000000000000000a"; pd
chk "pilot_on: gate jar_md5 sai jar dang chay => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "jar_md5!="'
regate $W/gate_ok $G "mien_b2=DEL"; pd
chk "pilot_on: gate thieu mien_b2 => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "mien_b2_thieu"'
regate $W/gate_ok $G "boot_guard=CHUA_CAI x"; pd
chk "pilot_on: gate boot_guard != CAI => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "boot_guard_chua_CAI"'
regate $W/gate_ok $G "g_exit=TRUOT 40 0.5 20"; pd
chk "pilot_on: gate g_exit=TRUOT => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "g_exit_thieu/sai"'
cp -p $W/gate_ok $G
mv $SB/h242-prestart-c3.sh $W/wr.bak; pd; mv $W/wr.bak $SB/h242-prestart-c3.sh
chk "pilot_on: boot guard bi go tren 242 sau khi tao gate => precheck TU CHOI (doc lai)" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL boot guard 242 DA CAI"'
rm -f $W/py/bin/python3; pd; ln -s "$(command -v python3)" $W/py/bin/python3
chk "pilot_on: khong co python 242 (A-02 khong sua duoc acct_peak) => precheck TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL A-02: rollback ha von dat lai duoc dinh"'
echo 'export LIVE_C3_KILLSW_PEAK_FILE=run/khac' >> $F/conf/env.sh; pd; cp $W/env.micro $F/conf/env.sh
chk "pilot_on: env.sh ghi de duong dan file dinh => precheck TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "ghi de duong dan dinh/latch/KS=.LIVE_C3_KILLSW_PEAK_FILE"'
pd
chk "pilot_on DRY: gate dung + boot guard + A-02 => DRY PASS, 242 khong doi (env, process)" '[ $RC = 0 ] && echo "$OUT" | grep -q "DRY PASS" && [ "$(envcap)" = 1000 ] && echo "$OUT" | grep -q "OK   boot guard 242 DA CAI" && echo "$OUT" | grep -q "LEV_CLUSTER_MAX voi von 10000 = 900"'
# =============================================================================== ban OPS5 fa95289b (TRUOC sua) - ban sao tam, pin tam
OLD=$W/old; mkdir -p "$OLD"; git -C "$REPO" archive fa95289bea8933d7b2b0c827b0d1fbef58a1e1d7 ops/c3live | tar -x -C "$OLD"
git -C "$OLD" init -q && git -C "$OLD" -c user.name=t -c user.email=t@t add -A && git -C "$OLD" -c user.name=t -c user.email=t@t commit -qm old && git -C "$OLD" rev-parse HEAD >> "$A1_APPROVED_OPS"
OH=$OLD/ops/c3live
cat "$OH/golive_monitor.sh" "$OH/golive_lib.sh" | md5sum | cut -c1-12 | sed 's/$/ test_ops6 ban cu/' >> "$W/gates/A1_APPROVED_MONITOR.md5"
yp() { LN0=$(wc -l < "$F/logs/full.log"); OUT=$(echo 'YES PILOT' | bash "${1:-$HERE}/golive_pilot_on.sh" 2>&1); RC=$?; }
newlog() { tail -n +$(( LN0 + 1 )) "$F/logs/full.log"; }
latch() { sed -n 's/.*"latch":"\([A-Z_]*\)".*/\1/p' "$F/run/killsw_latch.json"; }
simok() { grep -q "eq=$1 dd_C6=0.0000 dd_A40=0.0000 OK" "$F/run/ksim_last.txt" && [ "$(latch)" = NONE ] && ! newlog | grep -q 'LATCH action=FLATTEN'; }
# =============================================================================== pilot_on THAT
echo "== pilot_on (SAU sua) - duong thanh cong + A-02 chieu TANG"
reset242 1005; cp -p $W/gate_ok $G; yp
chk "pilot_on XONG: 1000 -> 10000 (env.sh + process), KS script go, PUSH ON, PAUSE go, moc tmb0 c3_capital=10000, Telegram" '[ $RC = 0 ] && echo "$OUT" | grep -q "XONG: PILOT C3_CAPITAL=10000" && [ "$(envcap)" = 10000 ] && penv | grep -qx C3_CAPITAL=10000 && [ ! -e $F/run/KILL_SWITCH ] && [ ! -e $W/PAUSE ] && grep -qx c3_capital=10000 $W/deploy/c3sub_eq_base.txt && grep -q "PILOT BAT" $W/tg.txt && newlog | grep -q "PUSH doi trang thai -> ON"'
chk "A-02 TANG 1000 -> 10000 (dinh cu 1005): a02 dat lai dinh jar truoc start (dinh tinh tu luc pilot bat), JVM 10000: dd C6 = dd A40 = 0, khong FLATTEN" 'echo "$OUT" | grep -q "INFO a02: DOI VON C3_CAPITAL 1000 -> 10000" && simok 10000.00 && ls $F/run/c3live_killsw_peak.a02_golive_pilot_on_* >/dev/null 2>&1'
reset242 1500; cp -p $W/gate_ok $G; yp $OH
chk "A-02 TANG - TRUOC sua (ban OPS5): micro dang DD -33 % (dinh 1500, cao nhat co the ma chua latch) => JVM 10000: dinh tu nang len 10000, dd = 0 (KHONG co DD am gia khi tang x10)" '[ $RC = 0 ] && grep -q "eq=10000.00 dd_C6=0.0000 dd_A40=0.0000 OK" $F/run/ksim_last.txt'
reset242 1500; cp -p $W/gate_ok $G; yp
chk "A-02 TANG - SAU sua: cung dinh 1500 => dat lai co chu dich, dd = 0 (nguong -40 % tinh tu equity luc pilot bat)" '[ $RC = 0 ] && simok 10000.00'
echo "== pilot_on hau kiem TRUOT => rollback HA VON (A-02 TRUOC / SAU sua)"
reset242 1005; cp -p $W/gate_ok $G; echo 10000 > $F/FAKE_KHAN_IF_CAP; yp $OH
chk "A-02 TRUOC sua (ban OPS5 fa95289b): rollback 10000 -> 1000 sau khi JVM 10000 day dinh => JVM 1000 nap dinh 10000 => dd -0.90 => FLATTEN GIA (latch FLATTEN)" '[ $RC = 1 ] && echo "$OUT" | grep -q "Da ROLLBACK xong" && grep -q "eq=1000.00 dd_C6=-0.9000 dd_A40=-0.9000 FLATTEN" $F/run/ksim_last.txt && [ "$(latch)" = FLATTEN ]'
reset242 1005; cp -p $W/gate_ok $G; echo 10000 > $F/FAKE_KHAN_IF_CAP; yp
chk "pilot_on SAU sua: hau kiem TRUOT => ROLLBACK ve 1000 rc1, KS ve nhu truoc (PUSH), moc tmb0 tra lai byte-giong, PAUSE go" '[ $RC = 1 ] && echo "$OUT" | grep -q "Da ROLLBACK xong: live C3_CAPITAL=1000. run/KILL_SWITCH sau rollback: PUSH" && [ "$(envcap)" = 1000 ] && penv | grep -qx C3_CAPITAL=1000 && cmp -s $W/eqbase0 $W/deploy/c3sub_eq_base.txt && [ ! -e $W/PAUSE ]'
chk "A-02 SAU sua: rollback HA von 10000 -> 1000 => a02 dat lai dinh TRUOC start: JVM 1000 dd = 0, KHONG FLATTEN, latch NONE" 'echo "$OUT" | grep -q "INFO a02: rollback DOI VON C3_CAPITAL 10000 -> 1000" && simok 1000.00'
echo "== A-02 ha von 10000 -> 5000 qua gl_restart (so live giu)"
a02drv() { bash -c ". '$1/golive_lib.sh' >/dev/null 2>&1; GL_NAME=golive_a02t; TS=\$(date +%Y%m%d_%H%M%S)_\$\$; LOG=/dev/null; gl_restart 'export C3_CAPITAL=5000' '' none 1; echo \"\$RS\"" 2>&1; }
up10k() { reset242 1005; sed -i 's/^export C3_CAPITAL=1000$/export C3_CAPITAL=10000/' $F/conf/env.sh; bash $F/bin/daemon.sh stop >/dev/null 2>&1; (cd $F && bin/daemon.sh start >/dev/null 2>&1); sleep 0.5; LN0=$(wc -l < $F/logs/full.log); }
up10k; OUT=$(a02drv $OH)
chk "A-02 TRUOC sua: JVM 10000 (dinh 10000) -> gl_restart C3_CAPITAL=5000 => dd -0.50 => FLATTEN GIA" 'grep -q "eq=5000.00 dd_C6=-0.5000 dd_A40=-0.5000 FLATTEN" $F/run/ksim_last.txt && [ "$(latch)" = FLATTEN ]'
up10k; OUT=$(a02drv $HERE)
chk "A-02 SAU sua: cung kich ban 10000 -> 5000 => a02 truoc start, dd = 0, KHONG FLATTEN; env + process 5000" 'echo "$OUT" | grep -q "INFO a02: DOI VON C3_CAPITAL 10000 -> 5000" && simok 5000.00 && [ "$(envcap)" = 5000 ] && penv | grep -qx C3_CAPITAL=5000'
up10k; rm -f $W/py/bin/python3; sed -i 's/"latch":"NONE"/"latch":"NO_NEW_ENTRY"/' $F/run/killsw_latch.json; OUT=$(a02drv $HERE); ln -s "$(command -v python3)" $W/py/bin/python3
chk "A-02 SAU sua: khong python + latch != NONE (khong dat lai duoc) => KHONG ha von: env.sh ve 10000 (khop dinh), start lai 10000, FAIL ro" 'echo "$OUT" | grep -q "FAIL a02_doi_von_khong_dat_lai_duoc_dinh" && [ "$(envcap)" = 10000 ] && penv | grep -qx C3_CAPITAL=10000 && grep -q "eq=10000.00 dd_C6=0.0000" $F/run/ksim_last.txt'
up10k; rm -f $W/py/bin/python3; OUT=$(a02drv $HERE); ln -s "$(command -v python3)" $W/py/bin/python3
chk "A-02 SAU sua: khong python + latch NONE => killsw_reset.req reset_peak=1 (co che jar) => JVM 5000 dd = 0" 'echo "$OUT" | grep -q "OK a02_yeu_cau_reset_peak" && simok 5000.00 && ls $F/run/killsw_reset.req.done_sim >/dev/null 2>&1'
echo "== N1: ssh dut sau khi bot DA dung + owner drain chen giua"
reset242 1005; cp -p $W/gate_ok $G; touch $F/FAKE_KILL_ON_START $F/FAKE_DRAIN_ON_KILL; yp $OH
chk "N1 TRUOC sua (ban OPS5): bao SAI 'bot live KHONG bi dung', env.sh GIU C3_CAPITAL=10000 (von moi), bot KHONG chay, PAUSE da go => watchdog se start von MOI duoi drain" '[ $RC = 1 ] && echo "$OUT" | grep -q "bot live KHONG bi dung" && [ "$(envcap)" = 10000 ] && [ "$(np)" = 0 ] && [ ! -e $W/PAUSE ]'
reset242 1005; cp -p $W/gate_ok $G; touch $F/FAKE_KILL_ON_START $F/FAKE_DRAIN_ON_KILL; yp
chk "N1 SAU sua (pha stopped): 'OK da_stop' that, KHONG bao 'bot KHONG dung', env.sh ve 1000, ROLLBACK start von cu (process 1000), KS owner GIU NGUYEN byte, ket qua DRAIN, PAUSE go, moc tmb0 tra lai" '[ $RC = 1 ] && echo "$OUT" | grep -q "OK da_stop (bot DA DUNG o lan chay truoc" && ! echo "$OUT" | grep -q "bot live KHONG bi dung" && [ "$(envcap)" = 1000 ] && penv | grep -qx C3_CAPITAL=1000 && [ "$(cat $F/run/KILL_SWITCH)" = "golive_live_off drain 20990101_000003" ] && echo "$OUT" | grep -q "run/KILL_SWITCH sau rollback: DRAIN" && [ ! -e $W/PAUSE ] && cmp -s $W/eqbase0 $W/deploy/c3sub_eq_base.txt && [ "$(np)" = 1 ]'
reset242 1005; cp -p $W/gate_ok $G; touch $F/FAKE_KILL_AFTER_STOP $F/FAKE_DRAIN_ON_STOP; yp
chk "N1 SAU sua (chet ngay sau stop, CHUA ghi pha stopped): nhan biet qua process => cung ket qua: env 1000, rollback start von cu, KS owner giu, DRAIN" '[ $RC = 1 ] && echo "$OUT" | grep -q "OK da_stop (bot DA DUNG" && [ "$(envcap)" = 1000 ] && penv | grep -qx C3_CAPITAL=1000 && [ "$(cat $F/run/KILL_SWITCH)" = "golive_live_off drain 20990101_000002" ] && [ "$(np)" = 1 ]'
echo "== owner drain / KS nguoi khac"
reset242 1005; cp -p $W/gate_ok $G; LNW=$(wc -l < $F/logs/full.log)
( for i in $(seq 1 900); do grep -q '^golive_pilot_on ' $F/run/KILL_SWITCH 2>/dev/null && tail -n +$LNW $F/logs/full.log | grep -q 'c3_capital=10000' && { printf 'golive_live_off drain 20990101_9\n' > $F/run/KILL_SWITCH; exit 0; }; sleep 0.2; done ) & OWP=$!
yp; kill $OWP 2>/dev/null; wait $OWP 2>/dev/null
chk "owner drain chen giua (sau start JVM 10000, truoc go KS) => rollback 1000 rc1, KS owner GIU NGUYEN byte, A-02 dat lai dinh (dd 0)" '[ $RC = 1 ] && [ "$(cat $F/run/KILL_SWITCH)" = "golive_live_off drain 20990101_9" ] && [ "$(envcap)" = 1000 ] && simok 1000.00'
reset242 1005; cp -p $W/gate_ok $G; printf 'golive_monitor 20261121_1 KHAN x\n' > $F/run/KILL_SWITCH; P0=$(pid); yp
chk "KS nguoi khac (monitor KHAN) co san => precheck TU CHOI, KHONG ghi de, bot khong dung" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL khong co run/KILL_SWITCH, hoac" && [ "$(cat $F/run/KILL_SWITCH)" = "golive_monitor 20261121_1 KHAN x" ] && [ "$(pid)" = "$P0" ] && [ "$(envcap)" = 1000 ]'
reset242 1005; cp -p $W/gate_ok $G; printf 'c3_autodrain 20261121_101500 caller=h242_watchdog.sh\n' > $F/run/KILL_SWITCH; P0=$(pid); yp
chk "[luot3 n-2] KS chi co token boot guard c3_autodrain => TU CHOI (khong go ngam), KS byte giu, bot khong dung, lenh tiep theo boot_undrain" '[ $RC = 1 ] && [ "$(cat $F/run/KILL_SWITCH)" = "c3_autodrain 20261121_101500 caller=h242_watchdog.sh" ] && [ "$(pid)" = "$P0" ] && [ "$(envcap)" = 1000 ] && echo "$OUT" | grep -q "LENH OWNER (dung 1): DRY=1 bash .*golive_boot_undrain.sh"'
echo "== ssh dut tung pha"
spl() { reset242 1005; cp -p $W/gate_ok $G; printf "$1" > $W/sshplan; }
spl 'STATE before 99\n'; P0=$(pid); yp
chk "ssh mat luc doc trang thai (kiem truoc) => TU CHOI rc1, khong doi" '[ $RC = 1 ] && [ "$(pid)" = "$P0" ] && [ "$(envcap)" = 1000 ] && [ ! -e $F/run/KILL_SWITCH ]'
spl 'BG before 99\n'; P0=$(pid); yp
chk "ssh mat luc doc boot guard => precheck FAIL boot guard, TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL boot guard 242 DA CAI" && [ "$(pid)" = "$P0" ]'
spl 'RESTART after 1\n'; yp
chk "ssh dut SAU khoi restart (1 lan) => doc pha, chay lai idempotent, XONG rc0 (1 JVM, 10000)" '[ $RC = 0 ] && echo "$OUT" | grep -q "pha_da_xong_truoc" && [ "$(np)" = 1 ] && [ "$(envcap)" = 10000 ] && [ ! -e $F/run/KILL_SWITCH ]'
spl 'RESTART before 99\nPHASE before 99\n'; P0=$(pid); yp
chk "ssh dut han o restart => KHAN rc2 'KHONG ket luan' (noi ro env co the von moi), KS script dat; that: bot von cu khong bi dung" '[ $RC = 2 ] && echo "$OUT" | grep -q "KHONG ket luan" && echo "$OUT" | grep -q "CO THE da co C3_CAPITAL=10000" && grep -q "^golive_pilot_on .* ssh_restart_khong_ro" $F/run/KILL_SWITCH && [ "$(envcap)" = 1000 ] && [ "$(pid)" = "$P0" ]'
spl 'CHK before 99\n'; yp
chk "ssh mat luc hau kiem => rollback 1000 rc1, A-02 dd 0" '[ $RC = 1 ] && echo "$OUT" | grep -q "Da ROLLBACK xong: live C3_CAPITAL=1000" && simok 1000.00 && [ "$(envcap)" = 1000 ]'
spl 'ROLLBACK after 1\n'; echo 10000 > $F/FAKE_KHAN_IF_CAP; yp
chk "ssh dut SAU khoi rollback (1 lan) => chay lai idempotent (chi KIEM), rc1, a02 khong lam lai, dd 0" '[ $RC = 1 ] && echo "$OUT" | grep -q "rollback da start o lan truoc" && simok 1000.00 && [ "$(np)" = 1 ]'
spl 'KSOFF before 99\n'; yp
chk "ssh mat luc go KS cua minh => KHAN rc2, KS script CON (drain), env 10000" '[ $RC = 2 ] && grep -q "^golive_pilot_on " $F/run/KILL_SWITCH && [ "$(envcap)" = 10000 ] && grep -q KHAN $W/tg.txt'
spl 'PUSHWAIT before 99\n'; yp
chk "ssh mat luc cho PUSH ON => dat lai KS push_khong_ON (xac nhan) + KHAN rc2" '[ $RC = 2 ] && grep -q "push_khong_ON" $F/run/KILL_SWITCH && [ "$(np)" = 1 ]'
reset242 1005; cp -p $W/gate_ok $G; OUT=$(echo YES | bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "pilot_on: go YES (khong phai 'YES PILOT') => huy, khong doi" '[ $RC = 0 ] && echo "$OUT" | grep -q "Huy. Khong doi gi." && [ "$(envcap)" = 1000 ]'
# =============================================================================== T20 boot guard luc "boot": watchdog THAT (ban sao ops/h242_watchdog.sh) + wrapper da cai
echo "== T20 boot guard: watchdog THAT + wrapper (token co TRUOC khi bot start), undrain, go cai"
WDC=$W/wd_real.sh; cp "$REPO/ops/h242_watchdog.sh" "$WDC"
MCN=com.o6_$$.Main; WF=$W/wdapp; mkdir -p "$WF/conf" "$WF/run" "$WF/bin"; printf 'export LIVE_ADAPTER=live\n' > "$WF/conf/env.sh"
printf '#!/bin/bash\ncd %s\n{ if [ -e run/KILL_SWITCH ]; then echo "KS_AT_START=1 $(tr "\\n" "|" < run/KILL_SWITCH)"; else echo KS_AT_START=0; fi; } >> start_trace.txt\nnohup bash -c "sleep 300; : o6wd_%s" %s >/dev/null 2>&1 &\n' "$WF" "$$" "$MCN" > "$WF/bin/start.sh"; chmod 755 "$WF/bin/start.sh"
cat > "$SB/wrshim.sh" <<EOW
#!/bin/bash
AD_ORIG_PRESTART=$SB/h242-prestart.sh AD_STATE_DIR=$W/adstate AD_TG_SINK=$W/tgad.txt exec bash $SB/h242-prestart-c3.sh "\$@"
EOW
chmod 755 "$SB/wrshim.sh"
wdk() { local p; for p in $(pgrep -f -- "o6wd_$$" 2>/dev/null); do kill "$p" 2>/dev/null; done; sleep 0.3; rm -rf "$W/wd"; }
WDRUN() { env -i PATH="$W/guardbin:/usr/bin:/bin" HOME=$W WD_APP=$WF WD_MAIN_CLASS=$MCN WD_STATE_DIR=$W/wd WD_TG_ENV=$W/khong_co WD_START_CMD="bash $WF/bin/start.sh" WD_START_WAIT_SEC=3 WD_START_BACKOFF_SEC=0 WD_PRESTART=$SB/wrshim.sh bash "$WDC" >/dev/null 2>&1; sleep 1; }
wdk; rm -f "$WF/run/KILL_SWITCH" "$WF/start_trace.txt"; WDRUN
chk "T20 boot (bot KHONG chay, chua co KS): watchdog goi wrapper TRUOC start => luc start.sh chay run/KILL_SWITCH DA CO dung 1 dong token c3_autodrain; bot len (drain)" 'grep -qE "^KS_AT_START=1 c3_autodrain [0-9]{8}_[0-9]{6} caller=[A-Za-z0-9_.-]*\|$" $WF/start_trace.txt && [ "$(pgrep -fc -- o6wd_$$)" -ge 1 ] && grep -qxE "c3_autodrain [0-9]{8}_[0-9]{6} caller=[A-Za-z0-9_.-]*" $WF/run/KILL_SWITCH && grep -q "DA DAT run/KILL_SWITCH" $W/tgad.txt'
wdk; printf 'golive_live_off drain 20261121_1\n' > "$WF/run/KILL_SWITCH"; : > "$WF/start_trace.txt"; WDRUN
chk "T20 boot khi da co KS cua owner: wrapper THEM dong token (>>), dong owner GIU NGUYEN (dong 1) - token co truoc start" '[ "$(head -1 $WF/run/KILL_SWITCH)" = "golive_live_off drain 20261121_1" ] && [ $(grep -c "" $WF/run/KILL_SWITCH) = 2 ] && grep -qE "^KS_AT_START=1 golive_live_off drain 20261121_1\|c3_autodrain " $WF/start_trace.txt'
wdk
chk "T20 systemd: drop-in xoa ExecStartPre goc roi chay wrapper (ExecStartPre chay TRUOC ExecStart theo systemd) - kiem file" 'grep -qx "\[Service\]" $DF && [ "$(grep -c "^ExecStartPre=" $DF)" = 2 ]'
# undrain tren 242 gia (bot dang chay, KS owner + token boot guard)
reset242 1005; printf 'golive_live_off drain 20261121_1\nc3_autodrain 20261121_101500 caller=h242_watchdog.sh\n' > $F/run/KILL_SWITCH; cp $F/run/KILL_SWITCH $W/ks_mix
OUT=$(DRY=1 bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "boot_undrain DRY: in TRUOC (2 dong, 1 c3_autodrain) + SAU du kien (con 1 dong khac => van drain), KHONG ghi" '[ $RC = 0 ] && echo "$OUT" | grep -q "DRY PASS" && echo "$OUT" | grep -q "TRUOC: 2 dong, trong do 1 dong boot guard" && echo "$OUT" | grep -q "con 1 dong NGUOI KHAC" && cmp -s $W/ks_mix $F/run/KILL_SWITCH'
OUT=$(echo 'YES' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "boot_undrain: go 'YES' (khong phai 'YES MO LAI') => huy, khong doi" '[ $RC = 0 ] && echo "$OUT" | grep -q "Huy" && cmp -s $W/ks_mix $F/run/KILL_SWITCH'
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "boot_undrain: CHI go dong c3_autodrain, dong owner GIU NGUYEN byte, ban truoc .bu_<TS>, bao 'VAN DRAIN', in SAU; [luot3 MASTER] rc 1 'CHUA MO: con dong cua golive_live_off x1' + VIEC TIEP THEO + lenh live_off undrain" '[ $RC = 1 ] && echo "$OUT" | grep -q "CHUA MO: .* dong cua golive_live_off x1" && echo "$OUT" | grep -q "LENH OWNER (dung 1): MODE=undrain bash .*golive_live_off.sh" && [ "$(cat $F/run/KILL_SWITCH)" = "golive_live_off drain 20261121_1" ] && cmp -s $W/ks_mix $(ls $F/run/KILL_SWITCH.bu_* | head -1) && echo "$OUT" | grep -q "VAN DRAIN" && echo "$OUT" | grep -q "SAU: 1 dong, 0 dong c3_autodrain"'
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "boot_undrain lan 2 (khong con dong c3_autodrain) => KHONG CAN, KS owner khong doi" '[ $RC = 0 ] && echo "$OUT" | grep -q "KHONG CAN" && [ "$(cat $F/run/KILL_SWITCH)" = "golive_live_off drain 20261121_1" ]'
reset242 1005; printf 'c3_autodrain 20261121_101500 caller=h242_watchdog.sh\n' > $F/run/KILL_SWITCH; bash $F/bin/daemon.sh stop >/dev/null 2>&1; (cd $F && bin/daemon.sh start >/dev/null 2>&1); sleep 0.5
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "boot_undrain: KS CHI co token boot guard => doi ten .bootok_<TS>, bot PUSH ON (doc log), Telegram" '[ $RC = 0 ] && [ ! -e $F/run/KILL_SWITCH ] && ls $F/run/KILL_SWITCH.bootok_* >/dev/null 2>&1 && echo "$OUT" | grep -q "DA MO: dong c3_autodrain go" && grep -q "BOOT UNDRAIN" $W/tg.txt'
reset242 1005; printf 'c3_autodrain 20261121_101500 caller=x;rm\n' > $F/run/KILL_SWITCH
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "boot_undrain: dong 'gan giong' token (ky tu la) KHONG khop TRON => khong go" '[ $RC = 0 ] && echo "$OUT" | grep -q "KHONG CAN" && grep -q "caller=x;rm" $F/run/KILL_SWITCH'
rm -f $F/run/KILL_SWITCH
OUT=$(echo YES | MODE=rollback bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
chk "T20 go cai (MODE=rollback): cron 242 = ban dau (byte), drop-in xoa, wrapper -> .off_<TS>, KHONG restart bot" '[ $RC = 0 ] && cmp -s $W/ct242 $W/ct242_0 && [ ! -e $DF ] && [ ! -e $SB/h242-prestart-c3.sh ] && ls $SB/h242-prestart-c3.sh.off_* >/dev/null 2>&1 && [ "$(np)" = 1 ]'
OUT=$(MGE DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "sau go cai boot guard: make_gate_pilot TU CHOI lai" '[ $RC = 1 ] && echo "$OUT" | grep -q "boot guard T20 CHUA CAI"'
# =============================================================================== LUOT 2 B1: unit / cron / watchdog dong 39 NHU 242 (MASTER doc 21/11 21:49)
echo "== LUOT 2 B1: h242-trading.service CO ExecStartPre=h242-prestart.sh san, cron watchdog KHONG WD_PRESTART, watchdog dong 39"
MCX=com.binance.chuyennd.trading.BinanceOrderTradingManager
cat > "$W/systemd/h242-trading.service" <<EOU
[Unit]
Description=h242 trading (noi dung theo MASTER doc 242)
[Service]
Type=oneshot
RemainAfterExit=yes
Environment=H242=1
ExecStartPre=$SB/h242-prestart.sh $F $MCX
ExecStart=$F/bin/daemon.sh start
ExecStop=$F/bin/daemon.sh stop
EOU
cp "$W/systemd/h242-trading.service" "$W/unit0"
printf '#!/bin/bash\necho "$#|$1|$2" >> %s/orig_args.log\nexit $(cat %s/pre_rc 2>/dev/null || echo 0)\n' "$W" "$W" > "$SB/h242-prestart.sh"; chmod 755 "$SB/h242-prestart.sh"
{ printf '#!/bin/bash\n'; for i in $(seq 2 38); do echo "# dong $i (watchdog 242)"; done
  echo 'PRESTART=${WD_PRESTART:-/usr/local/sbin/h242-prestart.sh}'
  echo "# test: /usr/local/sbin tren 242 = $SB o day => wrapper can AD_ORIG_PRESTART (tren 242 dung mac dinh /usr/local/sbin/h242-prestart.sh)"
  printf 'env -i PATH=/usr/bin:/bin AD_ORIG_PRESTART=%s/h242-prestart.sh AD_STATE_DIR=%s/adstate AD_TG_SINK=%s/tgad.txt "$PRESTART" "%s" "%s"; echo "WD_PRESTART_RC=$? PRESTART=$PRESTART" >> %s/wd39.log\n' "$SB" "$W" "$W" "$F" "$MCX" "$W"; } > "$SB/h242_watchdog.sh"; chmod 755 "$SB/h242_watchdog.sh"
printf '*/2 * * * * %s/h242_watchdog.sh >> /var/lib/h242_watchdog/cron.out 2>&1\n7,22,37,52 * * * * cd /x && bash exinfo_refresh_242.sh # C3LIVE_EXINFO_REFRESH\n' "$SB" > "$W/ct242"; cp "$W/ct242" "$W/ct242_b1"
rm -f "$SB"/h242-prestart-c3.sh*; rm -rf "$W/systemd/h242-trading.service.d"
OUT=$(echo YES | bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
chk "B1 install tren cau hinh 242 that: cron watchdog THEM tien to WD_PRESTART=wrapper (giu redirect, dong exinfo giu), unit KHONG bi sua, drop-in tao moi" '[ $RC = 0 ] && grep -qx "\*/2 \* \* \* \* WD_PRESTART=$SB/h242-prestart-c3.sh $SB/h242_watchdog.sh >> /var/lib/h242_watchdog/cron.out 2>&1" $W/ct242 && grep -q C3LIVE_EXINFO_REFRESH $W/ct242 && cmp -s $W/unit0 $W/systemd/h242-trading.service && [ -f $DF ]'
chk "B1 tinh: watchdog dong 39 nguyen van '\''PRESTART=\${WD_PRESTART:-...}'\''; wrapper goi DUNG file goc cua unit (/usr/local/sbin/h242-prestart.sh) voi \"\$@\" va giu rc goc != 0" '[ "$(sed -n 39p $SB/h242_watchdog.sh)" = "PRESTART=\${WD_PRESTART:-/usr/local/sbin/h242-prestart.sh}" ] && grep -qF "ORIG=\${AD_ORIG_PRESTART:-/usr/local/sbin/h242-prestart.sh}" $HERE/c3_autodrain_prestart.sh && grep -qF "\"\$ORIG\" \"\$@\"; rc=\$?" $HERE/c3_autodrain_prestart.sh && grep -qF "_RC=\$rc; exit \"\$rc\"" $HERE/c3_autodrain_prestart.sh'
# mo phong systemd: ExecStartPre hieu luc = unit + drop-in (dong "ExecStartPre=" rong XOA danh sach truoc), chay lan luot, rc != 0 => KHONG ExecStart
sdpre() { { grep '^ExecStartPre=' "$W/systemd/h242-trading.service"; grep '^ExecStartPre=' "$DF"; } | while IFS= read -r l; do v=${l#ExecStartPre=}; [ -z "$v" ] && echo __RESET__ || echo "$v"; done \
  | awk '/^__RESET__$/{n=0; next} {a[++n]=$0} END{for(i=1;i<=n;i++) print a[i]}'; }
sdstart() {   # in SD_RC=<rc pre> SD_START=0|1 KS_LUC_START=0|1
  local c rc=0
  while IFS= read -r c; do env AD_ORIG_PRESTART=$SB/h242-prestart.sh AD_STATE_DIR=$W/adstate AD_TG_SINK=$W/tgad.txt bash -c "$c" >/dev/null 2>&1; rc=$?; [ $rc = 0 ] || break; done < <(sdpre)
  if [ $rc = 0 ]; then echo "SD_RC=0 SD_START=1 KS_LUC_START=$([ -e $F/run/KILL_SWITCH ] && echo 1 || echo 0)"; else echo "SD_RC=$rc SD_START=0 KS_LUC_START=$([ -e $F/run/KILL_SWITCH ] && echo 1 || echo 0)"; fi; }
chk "B1 systemd: ExecStartPre hieu luc = DUNG 1 lenh = wrapper $F $MCX (goc KHONG chay 2 lan, thu tu: reset roi wrapper)" '[ "$(sdpre)" = "$SB/h242-prestart-c3.sh $F $MCX" ] && [ "$(grep "^ExecStartPre=" $DF | head -1)" = "ExecStartPre=" ]'
rm -f $F/run/KILL_SWITCH $W/orig_args.log; echo 0 > $W/pre_rc; R1=$(sdstart)
chk "B1 systemd boot: prestart GOC chay 1 lan voi DUNG 2 tham so ($F, main class), roi token c3_autodrain => KS CO luc ExecStart" '[ "$R1" = "SD_RC=0 SD_START=1 KS_LUC_START=1" ] && [ "$(cat $W/orig_args.log)" = "2|$F|$MCX" ] && grep -qxE "c3_autodrain [0-9]{8}_[0-9]{6} caller=[A-Za-z0-9_.-]*" $F/run/KILL_SWITCH'
rm -f $F/run/KILL_SWITCH $W/orig_args.log; echo 1 > $W/pre_rc; R1=$(sdstart); echo 0 > $W/pre_rc
chk "B1 systemd: prestart GOC tra rc 1 (deps chua san) => wrapper tra NGUYEN rc 1 => KHONG ExecStart; [luot3 m-4] token KS DA ghi TRUOC goc (giu - lan start sau van drain)" '[ "$R1" = "SD_RC=1 SD_START=0 KS_LUC_START=1" ] && [ "$(cat $W/orig_args.log)" = "2|$F|$MCX" ]'
rm -f $F/run/KILL_SWITCH $W/orig_args.log $W/wd39.log
CL=$(grep 'h242_watchdog.sh' $W/ct242 | sed -E 's#^\*/2 \* \* \* \* ##; s#/var/lib/h242_watchdog/cron.out#'"$W"'/cron.out#')
env -i PATH="$W/guardbin:/usr/bin:/bin" sh -c "$CL"
chk "B1 cron watchdog (dong cron sau cai, chay bang sh nhu cron): PRESTART = wrapper (WD_PRESTART tu dong cron), wrapper goi goc 2 tham so, KS token co, rc 0" 'grep -qx "WD_PRESTART_RC=0 PRESTART=$SB/h242-prestart-c3.sh" $W/wd39.log && [ "$(cat $W/orig_args.log)" = "2|$F|$MCX" ] && grep -qxE "c3_autodrain [0-9]{8}_[0-9]{6} caller=[A-Za-z0-9_.-]*" $F/run/KILL_SWITCH'
rm -f $F/run/KILL_SWITCH $W/wd39.log
CL0=$(sed -E 's#^\*/2 \* \* \* \* ##; s#/var/lib/h242_watchdog/cron.out#'"$W"'/cron.out#' $W/ct242_b1 | grep h242_watchdog)
env -i PATH="$W/guardbin:/usr/bin:/bin" sh -c "$CL0"
chk "B1 doi chung: dong cron TRUOC khi cai (khong WD_PRESTART) => watchdog dung mac dinh /usr/local/sbin/h242-prestart.sh (KHONG qua wrapper, khong drain) - dung nhu MASTER thay tren 242" 'grep -q "PRESTART=/usr/local/sbin/h242-prestart.sh" $W/wd39.log && [ ! -e $F/run/KILL_SWITCH ]'
# =============================================================================== LUOT 2 B2: golive_pilot_down.sh
echo "== LUOT 2 B2: golive_pilot_down.sh (ha von, chi khi phang)"
pdn() { LN0=$(wc -l < "$F/logs/full.log"); OUT=$(printf '%s\n' "${2:-}" | bash "$HERE/golive_pilot_down.sh" $1 2>&1); RC=$?; }
rstart() { bash $F/bin/daemon.sh stop >/dev/null 2>&1; (cd $F && bin/daemon.sh start >/dev/null 2>&1); sleep 0.5; }
up10k; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 5000 2>&1); RC=$?
chk "pilot_down DRY 10000 -> 5000 (phang): DRY PASS, IN von cu->moi, equity c3, du kien 5000, dinh dat lai, dung -40 % = 3000 USDT (lo 2000), so vi the; 242 khong doi" '[ $RC = 0 ] && echo "$OUT" | grep -q "DRY PASS" && echo "$OUT" | grep -q "von C3_CAPITAL: 10000 -> 5000" && echo "$OUT" | grep -q "so c3 0 cum, san 0 vi the" && echo "$OUT" | grep -q "equity c3 hien tai .*eq=10000.00" && echo "$OUT" | grep -q "du kien sau ha = 5000 + 0.00 = 5000.00" && echo "$OUT" | grep -q "dinh C6/A40 se DAT LAI" && echo "$OUT" | grep -q "equity c3 <= 3000.00 USDT (lo them 2000.00" && [ "$(envcap)" = 10000 ]'
up10k; echo -300 > $F/FAKE_PNL; rstart; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 5000 2>&1); RC=$?
chk "pilot_down DRY: realized cong don -300 (ledger KHONG reset - quyet dinh MASTER) => IN ro: du kien 5000 + -300.00 = 4700.00, dung -40 % <= 2820.00" '[ $RC = 0 ] && echo "$OUT" | grep -q "realized + funding cong don .*: -300.00 USDT" && echo "$OUT" | grep -q "= 5000 + -300.00 = 4700.00" && echo "$OUT" | grep -q "equity c3 <= 2820.00"'
for t in 7000 10000 ""; do up10k; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" $t 2>&1); RC=$?
  chk "pilot_down: von dich '$t' (chi 5000|1000) => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "von dich"'; done
reset242 1005; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 1000 2>&1); RC=$?
chk "pilot_down: von hien tai 1000, dich 1000 (khong phai HA) => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL C3_CAPITAL hien tai (1000) > dich 1000"'
up10k; echo '{"clusters":[{"symbol":"C01USDT","legs":[{"cid":"c3-C01USDT-1-0","state":"CONFIRMED","exec_qty":"10"}],"exit_qty":"0"}]}' > $F/run/c3live_book.json
OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 5000 2>&1); RC=$?; rm -f $F/run/c3live_book.json
chk "pilot_down: so c3 con 1 cum (chua phang) => TU CHOI + huong dan drain" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL so c3 PHANG: 0 cum (co 1; con vi the => MODE=drain"'
up10k; api positionRisk '[{"symbol":"C01USDT","positionAmt":"10"}]'; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 5000 2>&1); RC=$?; api positionRisk '[]'
chk "pilot_down: tk con con vi the tren san => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL tk con PHANG"'
up10k; P0=$(pid); pdn 5000 "YES"
chk "pilot_down: go 'YES' (khong phai 'YES HA VON 5000') => huy, khong doi" '[ $RC = 0 ] && echo "$OUT" | grep -q "Huy. Khong doi gi." && [ "$(envcap)" = 10000 ] && [ "$(pid)" = "$P0" ]'
up10k; pdn 5000 "YES HA VON 5000"
chk "pilot_down XONG 10000 -> 5000 (khong KS): env + process 5000, a02 dinh dat lai (dd 0, khong FLATTEN), KS script go, PUSH ON, moc tmb0 c3_capital=5000, Telegram" '[ $RC = 0 ] && echo "$OUT" | grep -q "XONG: HA VON C3_CAPITAL=5000" && [ "$(envcap)" = 5000 ] && penv | grep -qx C3_CAPITAL=5000 && echo "$OUT" | grep -q "INFO a02: DOI VON C3_CAPITAL 10000 -> 5000" && simok 5000.00 && [ ! -e $F/run/KILL_SWITCH ] && newlog | grep -q "PUSH doi trang thai -> ON" && grep -qx c3_capital=5000 $W/deploy/c3sub_eq_base.txt && grep -q "HA VON XONG" $W/tg.txt'
up10k; printf 'golive_live_off drain 20261121_5\n' > $F/run/KILL_SWITCH; pdn 1000 "YES HA VON 1000"
chk "pilot_down dich 1000 voi tham so grid MAC DINH code (F_BASE 0.03, weights 1,1,3,8: leg0 2.31 < 5) => D-01 TU CHOI (dung kiem chung pilot_on)" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL D-01 leg0 du kien >= 5" && [ "$(envcap)" = 10000 ]'
up10k; printf 'golive_live_off drain 20261121_5\n' > $F/run/KILL_SWITCH; pdn 5000 "YES HA VON 5000"
chk "pilot_down XONG khi owner DRAIN co san (10000 -> 5000): KS owner GIU NGUYEN byte, bot VAN DRAIN (khong PUSH ON), env + process 5000, dd 0" '[ $RC = 0 ] && echo "$OUT" | grep -q "VAN DRAIN" && [ "$(cat $F/run/KILL_SWITCH)" = "golive_live_off drain 20261121_5" ] && [ "$(envcap)" = 5000 ] && penv | grep -qx C3_CAPITAL=5000 && simok 5000.00 && ! newlog | grep -q "PUSH doi trang thai -> ON"'
up10k; echo 5000 > $F/FAKE_KHAN_IF_CAP; pdn 5000 "YES HA VON 5000"
chk "pilot_down hau kiem TRUOT (KHAN o von 5000) => ROLLBACK ve 10000 rc1, a02 lai (JVM 5000 da chay) dd 0, moc tmb0 tra lai" '[ $RC = 1 ] && echo "$OUT" | grep -q "Da ROLLBACK xong: live C3_CAPITAL=10000" && [ "$(envcap)" = 10000 ] && penv | grep -qx C3_CAPITAL=10000 && simok 10000.00 && cmp -s $W/eqbase0 $W/deploy/c3sub_eq_base.txt'
up10k; printf 'RESTART after 1\n' > $W/sshplan; pdn 5000 "YES HA VON 5000"
chk "pilot_down ssh dut SAU khoi restart (1 lan) => doc pha, chay lai idempotent, XONG 5000" '[ $RC = 0 ] && echo "$OUT" | grep -q "pha_da_xong_truoc" && [ "$(envcap)" = 5000 ] && simok 5000.00'
# =============================================================================== LUOT 3 (A1 audit cbcea237: M-1, m-1..m-9, n-2, n-4, n-6, muc 14)
echo "== LUOT 3"
reset242 1005; printf 'c3_autodrain 20261121_101500 caller=h242_watchdog.sh\n' > $F/run/KILL_SWITCH; cp $F/run/KILL_SWITCH $W/ks_ad
(cd $F; nohup bash -c 'exec -a "$(cat FAKE_PN)" sleep 120' >/dev/null 2>&1 < /dev/null &) >/dev/null 2>&1; sleep 0.3
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "M-1 boot_undrain: 2 JVM => DUNG rc1, KHONG go KS (byte), in VIEC TIEP THEO + 1 lenh owner" '[ $RC = 1 ] && echo "$OUT" | grep -q "so process bot = 2" && cmp -s $W/ks_ad $F/run/KILL_SWITCH && echo "$OUT" | grep -q "VIEC TIEP THEO" && [ "$(echo "$OUT" | grep -c "LENH OWNER (dung 1)")" = 1 ] && echo "$OUT" | grep -q "run/KILL_SWITCH: 1_dong:c3_autodrainx1"'
reset242 1005; cp $W/ks_ad $F/run/KILL_SWITCH; bash $F/bin/daemon.sh stop >/dev/null 2>&1
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "M-1 boot_undrain: 0 process (bot chua chay) => DUNG rc1, KS giu, lenh tiep theo = cho bot chay roi DRY" '[ $RC = 1 ] && cmp -s $W/ks_ad $F/run/KILL_SWITCH && echo "$OUT" | grep -q "bot: 0 process (DANG_DUNG)" && echo "$OUT" | grep -q "LENH OWNER (dung 1): khong chay gi them: bot CHUA chay"'
reset242 1005; cp $W/ks_ad $F/run/KILL_SWITCH; sed -i 's/"latch":"NONE"/"latch":"FLATTEN"/' $F/run/killsw_latch.json
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "M-1 boot_undrain: latch FLATTEN => DUNG rc1, KHONG go KS" '[ $RC = 1 ] && echo "$OUT" | grep -q "latch kill-switch = FLATTEN" && cmp -s $W/ks_ad $F/run/KILL_SWITCH'
reset242 1005; cp $W/ks_ad $F/run/KILL_SWITCH; rm -f $F/run/killsw_latch.json
OUT=$(DRY=1 bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "M-1 boot_undrain DRY: latch NOFILE (chua co file) => DUNG rc1 (can NONE)" '[ $RC = 1 ] && echo "$OUT" | grep -q "latch kill-switch = NOFILE"'
reset242 1005; cp $W/ks_ad $F/run/KILL_SWITCH
OUT=$(echo 'YES MO LAI' | NJ_MD5=0123456789abcdef0123456789abcdef bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "M-1 boot_undrain: jar DANG chay != NJ_MD5 (jar la) => DUNG rc1, KHONG go KS" '[ $RC = 1 ] && echo "$OUT" | grep -q "jar DANG chay .* != pin NJ_MD5" && cmp -s $W/ks_ad $F/run/KILL_SWITCH'
reset242 1005; cp $W/ks_ad $F/run/KILL_SWITCH; sed -i 's/^export LIVE_ADAPTER=live$/export LIVE_ADAPTER=dry/' $F/conf/env.sh; bash $F/bin/daemon.sh stop >/dev/null 2>&1; (cd $F && bin/daemon.sh start >/dev/null 2>&1); sleep 0.5
OUT=$(echo 'YES MO LAI' | bash "$HERE/golive_boot_undrain.sh" 2>&1); RC=$?
chk "M-1 boot_undrain: process LIVE_ADAPTER=dry => DUNG rc1, KHONG go KS" '[ $RC = 1 ] && echo "$OUT" | grep -q "LIVE_ADAPTER=.dry. != live" && cmp -s $W/ks_ad $F/run/KILL_SWITCH'
echo "-- m-1 C3_CAPITAL dong cuoi"
reset242 1005; cp -p $W/gate_ok $G; echo 'export C3_CAPITAL="1000"' >> $F/conf/env.sh; pd
chk "m-1 pilot_on: dong CUOI env.sh export C3_CAPITAL=\"1000\" (ngoac) => precheck FAIL ro rang, TU CHOI, VIEC TIEP THEO" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL \[m-1\] C3_CAPITAL DONG CUOI env.sh" && echo "$OUT" | grep -q "VIEC TIEP THEO"'
reset242 1005; cp -p $W/gate_ok $G; printf 'export C3_CAPITAL=2000\nexport C3_CAPITAL=1000\n' >> $F/conf/env.sh; pd
chk "m-1 pilot_on: env.sh co 3 dong C3_CAPITAL (1000, 2000, 1000), DONG CUOI 1000 = process => OK (khong gia dinh 1 dong)" '[ $RC = 0 ] && echo "$OUT" | grep -q "OK   \[m-1\] C3_CAPITAL DONG CUOI"'
up10k; echo 'export C3_CAPITAL=7000' >> $F/conf/env.sh; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 5000 2>&1); RC=$?
chk "m-1 pilot_down: dong CUOI env.sh 7000 != process 10000 => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL \[m-1\] C3_CAPITAL DONG CUOI env.sh (.7000.)"'
up10k; echo 'export C3_CAPITAL=10000 # ghi chu' >> $F/conf/env.sh; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 5000 2>&1); RC=$?
chk "m-1 pilot_down: dong CUOI co chu thich (khong phai so tron) => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL \[m-1\]"'
up10k; sed -i 's/^export C3_CAPITAL=10000$/export C3_CAPITAL="10000"/' $F/conf/env.sh; M0=$(md5sum < $F/conf/env.sh); OUT=$(a02drv $HERE)
chk "m-1 gl_restart: dong cuoi backup '\"10000\"' (khong so tron) -> 5000 => FAIL C3_CAPITAL_dong_cuoi_khong_phai_so_tron, env.sh VE GOC (byte), KHONG dat lai dinh, 1 JVM" 'echo "$OUT" | grep -q "FAIL C3_CAPITAL_dong_cuoi_khong_phai_so_tron" && [ "$(md5sum < $F/conf/env.sh)" = "$M0" ] && [ -e $F/run/c3live_killsw_peak ] && ! ls $F/run/c3live_killsw_peak.a02_* >/dev/null 2>&1 && [ "$(np)" = 1 ]'
echo "-- m-2 / n-4 ssh dut, watchdog start giua chung, cat tung pha HA VON"
a02cut() { bash -c ". '$HERE/golive_lib.sh' >/dev/null 2>&1; GL_RESUME_MAX=0; GL_NAME=golive_a02t; TS=\$(date +%Y%m%d_%H%M%S)_\$\$; LOG=/dev/null; gl_restart 'export C3_CAPITAL=5000' '' none 1; echo \"\$RS\"" 2>&1; }
up10k; touch $F/FAKE_KILL_AFTER_STOP; OUT=$(a02cut); sleep 0.5
chk "n-4 HA VON cat NGAY SAU stop (chua kip ghi pha): env.sh VAN 10000 (chua doi), dinh C6 giu, bot dung => trang thai nhat quan" '[ "$(np)" = 0 ] && [ "$(envcap)" = 10000 ] && [ -e $F/run/c3live_killsw_peak ]'
(cd $F && bin/daemon.sh start >/dev/null 2>&1); sleep 0.5
chk "n-4 ... watchdog start luc do => JVM 10000 + dinh 10000: dd 0, KHONG FLATTEN (khong co 'von thap + dinh cao + bot chay')" 'grep -q "eq=10000.00 dd_C6=0.0000 dd_A40=0.0000 OK" $F/run/ksim_last.txt && [ "$(latch)" = NONE ]'
up10k; touch $F/FAKE_KILL_ON_START; OUT=$(a02cut); sleep 0.5
chk "n-4 HA VON cat LUC start (sau a02 + env 5000): bot dung, env 5000, dinh da go (.a02_)" '[ "$(np)" = 0 ] && [ "$(envcap)" = 5000 ] && [ ! -e $F/run/c3live_killsw_peak ] && ls $F/run/c3live_killsw_peak.a02_* >/dev/null 2>&1'
(cd $F && bin/daemon.sh start >/dev/null 2>&1); sleep 0.5
chk "n-4 ... watchdog start luc do => JVM 5000 dinh lay lai tu equity 5000: dd 0, KHONG FLATTEN" 'grep -q "eq=5000.00 dd_C6=0.0000 dd_A40=0.0000 OK" $F/run/ksim_last.txt && [ "$(latch)" = NONE ]'
up10k; touch $F/FAKE_KILL_ON_START $F/FAKE_WD_START_ON_KILL; pdn 5000 "YES HA VON 5000"
chk "m-2 pilot_down: ssh chet luc start + 'watchdog' start JVM giua chung (pha stopped) => chay lai: thay process DANG CHAY => dung LAI roi moi start, 1 JVM 5000, dd 0" '[ $RC = 0 ] && echo "$OUT" | grep -q "WARN pha_stopped_nhung_process_DANG_CHAY" && [ "$(np)" = 1 ] && penv | grep -qx C3_CAPITAL=5000 && simok 5000.00'
echo "-- m-3 watchdog: flock, PAUSE rollback, khong start lan 2"
lockh() { python3 -c "import fcntl,time; f=open('$W/.lock','a'); fcntl.flock(f,fcntl.LOCK_EX); time.sleep($1)" & LKP=$!; sleep 0.3; }
reset242 1005; cp -p $W/gate_ok $G; lockh 12; yp; kill $LKP 2>/dev/null; wait $LKP 2>/dev/null
chk "m-3 restart CHO luot watchdog dang giu .lock (3 s) roi moi dung bot, XONG" '[ $RC = 0 ] && echo "$OUT" | grep -qE "OK watchdog_khong_con_luot_dang_chay \(cho [1-9][0-9]*s" && [ "$(envcap)" = 10000 ]'
reset242 1005; cp -p $W/gate_ok $G; lockh 60; P0=$(pid); LN0=$(wc -l < "$F/logs/full.log"); OUT=$(echo 'YES PILOT' | GL_WD_LOCK_WAIT_S=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?; kill $LKP 2>/dev/null; wait $LKP 2>/dev/null
chk "m-3 watchdog giu .lock qua GL_WD_LOCK_WAIT_S => TU CHOI rc1 TRUOC stop: bot khong dung (pid), env 1000, KS cua minh go, PAUSE go" '[ $RC = 1 ] && echo "$OUT" | grep -q "watchdog_dang_giu_lock_qua_1s" && [ "$(pid)" = "$P0" ] && [ "$(envcap)" = 1000 ] && [ ! -e $F/run/KILL_SWITCH ] && [ ! -e $W/PAUSE ]'
reset242 1005; cp -p $W/gate_ok $G; echo 10000 > $F/FAKE_KHAN_IF_CAP; rm -f $F/run/stop_trace.txt; LNW=$(wc -l < $F/logs/full.log)
( for i in $(seq 1 900); do tail -n +$LNW $F/logs/full.log | grep -q 'c3_capital=10000' && { sleep 0.3; rm -f $W/PAUSE; exit 0; }; sleep 0.1; done ) & OWP=$!
yp; kill $OWP 2>/dev/null; wait $OWP 2>/dev/null
chk "m-3 rollback bat dau MUON (PAUSE restart DA het han / mat) => rollback ghi LAI PAUSE han moi token C3GOLIVE_RB_ TRUOC stop, xong go PAUSE, 1 JVM 1000" '[ $RC = 1 ] && echo "$OUT" | grep -q "OK watchdog_PAUSE_rollback token=.C3GOLIVE_RB_golive_pilot_on" && tail -1 $F/run/stop_trace.txt | grep -q "PAUSE=C3GOLIVE_RB_golive_pilot_on" && [ ! -e $W/PAUSE ] && [ "$(np)" = 1 ] && [ "$(envcap)" = 1000 ]'
mkdir -p $W/pyx; printf '#!/bin/bash\ncase "$*" in *killsw_latch.json*) ;; *) exec python3 "$@";; esac\nif [ -f %s/intr ]; then n=$(( $(cat %s/intr) - 1 )); if [ $n -le 0 ]; then rm -f %s/intr; (cd %s; nohup bash -c '"'"'exec -a "$(cat FAKE_PN)" sleep 120'"'"' >/dev/null 2>&1 < /dev/null &) >/dev/null 2>&1 < /dev/null; sleep 0.3; else echo $n > %s/intr; fi; fi\nexec python3 "$@"\n' $W $W $W $F $W > $W/pyx/python3; chmod +x $W/pyx/python3
reset242 1005; cp -p $W/gate_ok $G; echo 10000 > $F/FAKE_KHAN_IF_CAP; echo 2 > $W/intr; PY242=$W/pyx/python3 yp
chk "m-3 'watchdog' start JVM giua rollback (sau stop, truoc start) => rollback KHONG start lan 2 (1 JVM), KS them dong rb_jvm_da_chay, KHAN rc2" '[ $RC = 2 ] && echo "$OUT" | grep -q "FAIL KHAN rb_jvm_DA_CHAY_truoc_start" && [ "$(np)" = 1 ] && grep -q "rb_jvm_da_chay_truoc_start" $F/run/KILL_SWITCH && echo "$OUT" | grep -q "LENH OWNER (dung 1): bash .*golive_monitor.sh"'
reset242 1005; cp -p $W/gate_ok $G; echo 1 > $W/intr; PY242=$W/pyx/python3 yp
chk "m-3 'watchdog' start JVM giua restart (sau a02, truoc start) => restart KHONG start lan 2, FAIL KHAN => rollback dung ca 2, start von cu: 1 JVM 1000" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL KHAN jvm_DA_CHAY_truoc_start" && [ "$(np)" = 1 ] && [ "$(envcap)" = 1000 ] && penv | grep -qx C3_CAPITAL=1000'
echo "-- m-4 wrapper fail-closed + monitor kiem boot guard"
WA=$W/wapp; mkdir -p $WA/conf $WA/run; adw() { rm -f $WA/run/KILL_SWITCH; env AD_ORIG_PRESTART=$W/origx.sh AD_STATE_DIR=$W/adst AD_TG_SINK=$W/tgw.txt bash $HERE/c3_autodrain_prestart.sh $WA x >/dev/null 2>&1; echo $?; }
printf '#!/bin/bash\nexit %s\n' 0 > $W/origx.sh; chmod +x $W/origx.sh
rm -f $WA/conf/env.sh; R=$(adw)
chk "m-4 wrapper: KHONG doc duoc LIVE_ADAPTER (env.sh mat) => coi nhu live: token c3_autodrain, rc 0" '[ "$R" = 0 ] && grep -qxE "c3_autodrain [0-9]{8}_[0-9]{6} caller=[A-Za-z0-9_.-]*" $WA/run/KILL_SWITCH'
printf 'export LIVE_ADAPTER=dry\n' > $WA/conf/env.sh; R=$(adw)
chk "m-4 wrapper: LIVE_ADAPTER=dry (ro rang) => KHONG drain" '[ "$R" = 0 ] && [ ! -e $WA/run/KILL_SWITCH ]'
printf 'export LIVE_ADAPTER=live\n' > $WA/conf/env.sh; printf '#!/bin/bash\n[ -e %s/run/KILL_SWITCH ] && echo KS_TRUOC_GOC=1 > %s/orig_saw || echo KS_TRUOC_GOC=0 > %s/orig_saw\nexit 1\n' $WA $W $W > $W/origx.sh; R=$(adw)
chk "m-4 wrapper: token ghi TRUOC prestart goc (goc thay KS), goc rc 1 => rc 1 + token GIU" '[ "$R" = 1 ] && grep -qx KS_TRUOC_GOC=1 $W/orig_saw && [ -e $WA/run/KILL_SWITCH ]'
reset242 1005; OUT=$(DRY=1 bash "$HERE/golive_monitor.sh" 2>&1)
chk "m-4 monitor: boot guard DA CAI => khong canh bao boot_guard" '! echo "$OUT" | grep -q "boot_guard_MAT"'
chmod 644 $SB/h242-prestart-c3.sh; OUT=$(DRY=1 bash "$HERE/golive_monitor.sh" 2>&1); RC=$?; chmod 755 $SB/h242-prestart-c3.sh
chk "m-4 monitor: wrapper MAT quyen x => KHAN boot_guard_MAT (x=0), rc 2" '[ $RC = 2 ] && echo "$OUT" | grep -q "KHAN (canh bao, KHONG dat KILL_SWITCH):.*boot_guard_MAT(.*x=0"'
cp $DF $W/df.bak; rm -f $DF; OUT=$(DRY=1 bash "$HERE/golive_monitor.sh" 2>&1); RC=$?; cp $W/df.bak $DF
chk "m-4 monitor: drop-in systemd MAT => KHAN boot_guard_MAT (dropin=0)" '[ $RC = 2 ] && echo "$OUT" | grep -q "boot_guard_MAT(.*dropin=0"'
echo "-- m-5 installer: systemctl show xac nhan"
OUT=$(echo YES | MODE=rollback bash "$HERE/install_242_autodrain.sh" 2>&1); cp $W/ct242 $W/ct242_m5
OUT=$(echo YES | bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
chk "m-5 install voi systemctl CO TRANG THAI: sau daemon-reload show ExecStartPre = wrapper => XONG" '[ $RC = 0 ] && echo "$OUT" | grep -q "SYSTEMD_EXECSTARTPRE=wrapper" && [ -f $DF ]'
OUT=$(echo YES | MODE=rollback bash "$HERE/install_242_autodrain.sh" 2>&1); touch $W/fsc_broken
OUT=$(echo YES | bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?; rm -f $W/fsc_broken
chk "m-5 install: systemd KHONG nap drop-in (show = prestart goc) => ROLLBACK NGAY: crontab cu (byte), drop-in xoa, wrapper .off, rc1 + bao loi" '[ $RC = 1 ] && echo "$OUT" | grep -q "DA ROLLBACK" && cmp -s $W/ct242 $W/ct242_m5 && [ ! -e $DF ] && [ ! -e $SB/h242-prestart-c3.sh ]'
OUT=$(echo YES | bash "$HERE/install_242_autodrain.sh" 2>&1)
echo "-- m-6 live_off undrain CHI go dong cua minh"
lou() { OUT=$(echo YES | env MODE=undrain "$@" bash "$HERE/golive_live_off.sh" 2>&1); RC=$?; }
reset242 1005; printf 'golive_live_off drain 20261122_1\nc3_autodrain 20261121_101500 caller=h242_watchdog.sh\n' > $F/run/KILL_SWITCH; lou
chk "m-6 live_off undrain: drain owner + c3_autodrain => CHI go dong drain, dong c3_autodrain GIU, rc1, chi dan golive_boot_undrain.sh" '[ $RC = 1 ] && [ "$(cat $F/run/KILL_SWITCH)" = "c3_autodrain 20261121_101500 caller=h242_watchdog.sh" ] && echo "$OUT" | grep -q "golive_boot_undrain.sh"'
lou
chk "m-6 live_off undrain: chi con c3_autodrain => KHONG doi gi rc1 (khong xoa file)" '[ $RC = 1 ] && [ "$(cat $F/run/KILL_SWITCH)" = "c3_autodrain 20261121_101500 caller=h242_watchdog.sh" ]'
reset242 1005; printf 'golive_live_off drain 20261122_1\n\n' > $F/run/KILL_SWITCH; lou
chk "m-6 live_off undrain: CHI dong cua minh (+ dong trong) => go file (.off_<TS>), rc0" '[ $RC = 0 ] && [ ! -e $F/run/KILL_SWITCH ] && ls $F/run/KILL_SWITCH.off_* >/dev/null 2>&1'
reset242 1005; printf 'golive_live_off drain 20261122_1\ngolive_monitor 20261122_2 KHAN x\n' > $F/run/KILL_SWITCH; lou
chk "m-6 live_off undrain: dong golive_monitor KHAN KHONG co XOA_DONG_MONITOR=YES => giu, rc1" '[ $RC = 1 ] && [ "$(cat $F/run/KILL_SWITCH)" = "golive_monitor 20261122_2 KHAN x" ] && echo "$OUT" | grep -q "XOA_DONG_MONITOR=YES"'
lou XOA_DONG_MONITOR=YES
chk "m-6 live_off undrain XOA_DONG_MONITOR=YES => go dong monitor, file het, rc0" '[ $RC = 0 ] && [ ! -e $F/run/KILL_SWITCH ]'
echo "-- m-7 gate / n-6 LEV_EV / m-8"
OUT=$(MGE G_EXEC="GREEN 73 leg khong n khong ref" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "m-7 make_gate: G_EXEC GREEN thieu n= / ref= => TU CHOI (moi dang bat buoc)" '[ $RC = 1 ] && echo "$OUT" | grep -q "G_EXEC GREEN thieu n=" && echo "$OUT" | grep -q "G_EXEC GREEN thieu ref="'
OUT=$(MGE G_EXIT="DAT n=0 ref=$MRC x" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "m-7 make_gate: G_EXIT n=0 => TU CHOI (n >= 1)" '[ $RC = 1 ] && echo "$OUT" | grep -q "G_EXIT DAT thieu n="'
echo x > $PR/docs/prereg/KHAC.md; git -C $PR add -A; git -C $PR -c user.name=t -c user.email=t@t commit -qm khac; KRC=$(git -C $PR rev-parse --short HEAD)
OUT=$(MGE MIEN_B2="MIEN ref=$KRC commit khong cham OWNER_DECISION" DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "m-7 make_gate: ref = commit CO THAT nhung KHONG cham docs/prereg/OWNER_DECISION_* => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "MIEN_B2 ref=$KRC khong phai commit cham docs/prereg/OWNER_DECISION_"'
OUT=$(MGE GL_TEST=0 DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "m-7 make_gate KHONG GL_TEST=1: ghi de GL_MICRO_START / PREREG_REPO / NJ_MD5 bi BO QUA (canh bao), dung moc that => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "bo qua ghi de GL_MICRO_START" && echo "$OUT" | grep -q "bo qua ghi de NJ_MD5" && echo "$OUT" | grep -q "ke tu 2026-11-19 09:31:00 +07"'
grep -qx test=1 $W/gate_ok; T1=$?
reset242 1005; cp -p $W/gate_ok $G; OUT=$(GL_TEST=0 DRY=1 bash "$HERE/golive_pilot_on.sh" 2>&1); RC=$?
chk "m-7 gate test=1 (tao voi GL_TEST=1) => pilot_on KHONG GL_TEST=1 TU CHOI" '[ $T1 = 0 ] && [ $RC = 1 ] && echo "$OUT" | grep -q "gate_TEST(test=1)_KHONG_dung_cho_242_that"'
for op in "g_exec=Q4_OWNER n=0 ref=$MRC x:g_exec_thieu_n" "g_exit=DAT n=5 ref=$KRC x:g_exit_ref_khong_phai_commit_OWNER_DECISION" "owner_decision=$ODC file=docs/prereg/OWNER_DECISION_PILOT_1121_ADD1.md sha256=$(printf '%064d' 0):owner_decision_sha256_lech" "micro_start=2026-11-01 00:00:00 +07 micro_days=21 micro7=DU (>= 7 ngay):micro_start_lech" "test=DEL:thieu_dong_test" "lev_ev=DEL:lev_ev_thieu"; do
  regate $W/gate_ok $G "${op%:*}"; pd
  chk "m-7 gl_gate_pilot kiem LAI: ${op%%=*} sai => pilot_on TU CHOI (${op##*:})" '[ $RC = 1 ] && echo "$OUT" | grep -q "${op##*:}"'
done
cp -p $W/gate_ok $G; cp -p $W/lev10000.txt $W/lev.bak; echo x >> $W/lev10000.txt; pd; cp -p $W/lev.bak $W/lev10000.txt
chk "n-6 gate: file LEV_EV bi doi sau khi tao gate (sha256) => pilot_on TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "lev_ev_thieu/file_doi"'
OUT=$(MGE LEV_EV= DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "n-6 make_gate: thieu LEV_EV => TU CHOI + huong dan LEV_CAP=10000 golive_check_lev.sh" '[ $RC = 1 ] && echo "$OUT" | grep -q "LEV_EV=.* thieu / rong - chay: LEV_CAP=10000"'
printf 'golive_check_lev SUB x key_sha8=x KET QUA: DAT\nvon_kiem=1000\n' > $W/lev1000.txt
OUT=$(MGE LEV_EV=$W/lev1000.txt DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "n-6 make_gate: LEV_EV kiem von 1000 (von process) != size 10000 => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "von_kiem=.1000. != PILOT_SIZE .10000."'
printf 'golive_check_lev SUB x key_sha8=x KET QUA: CANH BAO\nvon_kiem=10000\n' > $W/levcb.txt
OUT=$(MGE LEV_EV=$W/levcb.txt DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "n-6 make_gate: LEV_EV KET QUA khong DAT => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "khong co .KET QUA: DAT."'
cp $W/lev10000.txt $W/levold.txt; touch -d '3 days ago' $W/levold.txt
OUT=$(MGE LEV_EV=$W/levold.txt DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); RC=$?
chk "n-6 make_gate: LEV_EV cu > 48 h => TU CHOI" '[ $RC = 1 ] && echo "$OUT" | grep -q "LEV_EV .* cu [0-9]*s >= 172800s"'
printf '01/01/2026 00:00:00.000 INFO x [C3-LIVE-ORDER] status=FILLED cid=c3-OLDUSDT-1-0\n' > $F/logs/full.log.1; touch -d '30 days ago' $F/logs/full.log.1
OUT=$(MGE DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); V0=$(echo "$OUT" | sed -n 's/.*FILLED (log, uniq cid): vao=\([0-9]*\).*/\1/p')
touch $F/logs/full.log.1; OUT2=$(MGE DRY=1 bash "$HERE/golive_make_gate_pilot.sh" 2>&1); V1=$(echo "$OUT2" | sed -n 's/.*FILLED (log, uniq cid): vao=\([0-9]*\).*/\1/p'); rm -f $F/logs/full.log.1
chk "m-8 make_gate dem lenh: CHI full.log (+ full.log.1 khi xoay SAU moc micro): .1 cu => bo, .1 moi => tinh (+1)" 'echo "$OUT" | grep -q "(logs/full.log)" && echo "$OUT2" | grep -q "(logs/full.log.1 logs/full.log)" && [ $((V0 + 1)) = "$V1" ]'
chk "m-8 make_gate: lenh dem = timeout 120 + nice 19 (+ ionice neu co)" 'grep -q "timeout 120 nice -n 19 \\\\\$IO grep" $HERE/golive_make_gate_pilot.sh && grep -q "ionice -c3" $HERE/golive_make_gate_pilot.sh'
echo "-- m-9 a02 python giu quyen file latch"
up10k; chmod 640 $F/run/killsw_latch.json; OUT=$(a02drv $HERE)
chk "m-9 a02 python ghi killsw_latch.json nguyen tu (tmp cung thu muc + replace) GIU mode 640, khong con .a02tmp" 'echo "$OUT" | grep -q "OK a02_acct_peak_A40_go" && [ "$(stat -c %a $F/run/killsw_latch.json)" = 640 ] && ! ls $F/run/*.a02tmp >/dev/null 2>&1'
echo "-- n-2 KS c3_autodrain => TU CHOI"
up10k; printf 'c3_autodrain 20261121_101500 caller=h242_watchdog.sh\n' > $F/run/KILL_SWITCH; OUT=$(DRY=1 bash "$HERE/golive_pilot_down.sh" 5000 2>&1); RC=$?
chk "n-2 pilot_down: KS co dong c3_autodrain => TU CHOI, lenh tiep theo = golive_boot_undrain.sh (sau dieu tra)" '[ $RC = 1 ] && echo "$OUT" | grep -q "FAIL run/KILL_SWITCH KHONG co dong c3_autodrain" && echo "$OUT" | grep -q "LENH OWNER (dung 1): DRY=1 bash .*golive_boot_undrain.sh"'
# =============================================================================== tong
chk "AN TOAN: KHONG co lenh ssh/scp THAT nao duoc goi trong toan bo test" '[ ! -s $W/guard_blocked.log ]'
chk "khong lo key/secret (log deploy, gate, Telegram)" 'nosec "$OUT"'
echo "TEST $([ -z "$FAILS" ] && echo PASS || echo "FAIL$FAILS") $P/$N"
