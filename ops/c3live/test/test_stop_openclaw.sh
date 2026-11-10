#!/usr/bin/env bash
# test_stop_openclaw.sh — test GIA cho stop_openclaw_gateway.sh (systemctl/crontab gia, process gia; KHONG dung openclaw that).
#   bash ops/c3live/test/test_stop_openclaw.sh /tmp/t_oc
HERE=$(cd "$(dirname "$0")/.." && pwd); S=$HERE/stop_openclaw_gateway.sh
W=${1:?thu muc tam}; rm -rf "$W"; mkdir -p "$W/home/.openclaw/state" "$W/log"; TAG=octest_$$
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }
PATT="fakeclaw/dist/index.js gateway $TAG"
cat > $W/sc.sh <<EOF
#!/bin/bash
c=\$2; st=$W/unit
case \$c in
  is-active) cat \$st.active 2>/dev/null || echo inactive;;
  is-enabled) cat \$st.enabled 2>/dev/null || echo disabled;;
  disable) echo disabled > \$st.enabled;;
  enable) echo enabled > \$st.enabled;;
  stop) echo inactive > \$st.active; [ -f $W/NOKILL ] || pkill -f "$PATT";;
esac
EOF
cat > $W/ct.sh <<EOF
#!/bin/bash
if [ "\$1" = -l ]; then cat $W/cron 2>/dev/null; elif [ "\$1" = - ]; then cat > $W/cron; else cp "\$1" $W/cron; fi
EOF
start() { echo active > $W/unit.active; echo enabled > $W/unit.enabled
  bash -c "exec -a 'node $PATT --port 1' sleep 300" >/dev/null 2>&1 & sleep 0.5; }
alive() { pgrep -f "$PATT" >/dev/null; }
E() { env OC_SYSTEMCTL="bash $W/sc.sh" OC_CRONTAB="bash $W/ct.sh" OC_PAT="$PATT" OC_LOGDIR=$W/log HOME=$W/home "$@"; }
printf '@reboot /home/x/.npm-global/bin/openclaw gateway start\n0 * * * * echo giu_nguyen\n# openclaw cu da comment\n' > $W/cron
cp $W/cron $W/cron.orig; echo sqlite-gia > $W/home/.openclaw/state/openclaw.sqlite
echo "== stop_openclaw_gateway (gia)"
start
OUT=$(E DRY=1 bash $S 2>&1); RC=$?
chk "DRY=1: in trang thai + ke hoach (disable, stop, comment 1 dong cron), KHONG doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && echo \"\$OUT\" | grep -q 'systemctl --user disable' && echo \"\$OUT\" | grep -q 'comment 1 dong crontab' && alive && grep -qx enabled $W/unit.enabled && cmp -s $W/cron $W/cron.orig"
OUT=$(echo NO | E bash $S 2>&1); RC=$?
chk "khong go YES => huy, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy' && alive && grep -qx enabled $W/unit.enabled && cmp -s $W/cron $W/cron.orig"
OUT=$(echo YES | E bash $S 2>&1); RC=$?
chk "YES: disable + stop unit => 0 process, unit inactive/disabled, XONG" "[ $RC = 0 ] && ! alive && grep -qx disabled $W/unit.enabled && grep -qx inactive $W/unit.active && echo \"\$OUT\" | grep -q 'XONG: openclaw gateway DA DUNG'"
chk "YES: crontab dong openclaw (ca @reboot) bi comment #OC_OFF, dong khac giu nguyen, co backup + lenh bat lai 1 dong" "grep -q '^#OC_OFF @reboot' $W/cron && grep -qx '0 \* \* \* \* echo giu_nguyen' $W/cron && ls $W/log/crontab.bak_openclaw_* >/dev/null 2>&1 && echo \"\$OUT\" | grep -q 'systemctl --user enable --now openclaw-gateway.service && crontab $W/log/crontab.bak_openclaw_'"
chk "KHONG xoa du lieu openclaw (sqlite con)" "grep -qx sqlite-gia $W/home/.openclaw/state/openclaw.sqlite"
cp $W/cron.orig $W/cron; start; touch $W/NOKILL
OUT=$(echo YES | E bash $S 2>&1); RC=$?; rm -f $W/NOKILL
chk "process chay ngoai unit (stop khong giet) => TERM theo cmdline => 0 process, XONG" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '=> TERM' && ! alive"
OUT=$(echo YES | E bash $S 2>&1); RC=$?
chk "chay lai khi da dung: idempotent, XONG, khong ghi crontab lan 2" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'XONG' && ! echo \"\$OUT\" | grep -q 'disable openclaw-gateway.service'"
pkill -f "$PATT" 2>/dev/null
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
