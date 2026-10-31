#!/usr/bin/env bash
# =============================================================================
# guard_oracle_no_write_242.sh — CHAN test/mvn tren ORACLE ghi Aerospike 242 (nguon su co mapper 31/10).
#   DRY=1 bash ~/claude_master/deploy/guard_oracle_no_write_242.sh   # in thay doi, khong ghi
#   bash ~/claude_master/deploy/guard_oracle_no_write_242.sh          # go YES
#   REMOVE=1 bash ...                                                  # go bo
# KHONG chan cong 3222 tren 242: (1) v_t_m + collectData tren 242 noi Aerospike qua IP 103.157.218.242 (khong qua
# localhost) => chan "moi IP tru localhost" se GIET LEGACY; (2) shadow_c3 Oracle (LIVE_IS_SHADOW_HOST=true, chi doc),
# health_242/kline_rest_check/ing_qf_check DOC 242:3222 hop le. Cach chan: Live242WriteGuard (co san trong code):
# LIVE_IS_SHADOW_HOST=true + LIVE_WRITE_242_ENABLED=false cho MOI mvn (~/.mavenrc, surefire fork ke thua env) va shell
# dang nhap (~/.profile). KHONG dung gateway openclaw / shadow_c3 / cron. Claw dang chay chi nhan khi goi mvn moi.
# =============================================================================
set -uo pipefail
TAG="# [guard-no-write-242 20261031]"
BLOCK="export LIVE_IS_SHADOW_HOST=true $TAG
export LIVE_WRITE_242_ENABLED=false $TAG"
DRY=${DRY:-0}
echo "== Tien trinh Oracle dang noi 242:3222 (chi de biet; khong dung toi):"
for p in $(ss -tnp 2>/dev/null | grep '103.157.218.242\]*:3222' | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
  echo "  pid=$p $(ps -o args= -p $p | cut -c1-120) | LIVE_IS_SHADOW_HOST=$(tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -o '^LIVE_IS_SHADOW_HOST=.*' | cut -d= -f2)"
done
grep -q 'mavenrc' /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn && echo "OK mvn doc ~/.mavenrc" || { echo "DUNG: mvn khong doc ~/.mavenrc"; exit 1; }
for f in ~/.mavenrc ~/.profile; do
  if [ "${REMOVE:-0}" = 1 ]; then
    echo "== $f: se go $(grep -c "guard-no-write-242" $f 2>/dev/null || echo 0) dong"
  elif grep -q "guard-no-write-242" $f 2>/dev/null; then
    echo "== $f: da co (idempotent, khong them)"
  else
    echo "== $f: se them:"; echo "$BLOCK" | sed 's/^/   + /'
  fi
done
[ "$DRY" = 1 ] && { echo "DRY=1: khong ghi."; exit 0; }
echo ">>> Go YES de ap dung:"; read -r ANS; [ "$ANS" = YES ] || { echo "Huy."; exit 1; }
TS=$(date +%Y%m%d_%H%M%S)
for f in ~/.mavenrc ~/.profile; do
  [ -f $f ] && cp -p $f $f.bak_guard242_$TS
  if [ "${REMOVE:-0}" = 1 ]; then
    [ -f $f ] && sed -i '/guard-no-write-242/d' $f
  elif ! grep -q "guard-no-write-242" $f 2>/dev/null; then
    echo "$BLOCK" >> $f
  fi
done
V=$(bash -c '. ~/.mavenrc 2>/dev/null; echo "$LIVE_IS_SHADOW_HOST/$LIVE_WRITE_242_ENABLED"')
echo "Kiem: ~/.mavenrc => LIVE_IS_SHADOW_HOST/LIVE_WRITE_242_ENABLED = $V (mong: true/false; REMOVE => /)"
echo "XONG. Backup *.bak_guard242_$TS. Luu y: tool owner nao CAN ghi 242 tu Oracle bang mvn phai chay voi MAVEN_SKIP_RC=1."
