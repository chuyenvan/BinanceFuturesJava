#!/usr/bin/env bash
# test_cleanup_disk_242.sh — test GIA cleanup_disk_242.sh (khong cham 242): thu muc gia, process gia giu jar mo, SSH_242="bash -c".
# Chay: bash ops/c3live/test/test_cleanup_disk_242.sh <thu_muc_tam>
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd); CL=$HERE/cleanup_disk_242.sh
W=${1:?thu muc tam}; rm -rf "$W"; mkdir -p "$W"; W=$(cd "$W" && pwd)
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }
TAG=fakecl$$
md5() { md5sum < "$1" | cut -c1-32; }
J=binance-java-sdk-1.2.4.jar
mk() {   # dung lai cay thu muc gia
  pkill -f "$TAG" 2>/dev/null; sleep 0.3
  rm -rf "$W/vtm" "$W/ing" "$W/logdir"; mkdir -p "$W"/vtm/{target,logs/archived,backup_l3_x} "$W"/ing/{target,logs} "$W/logdir"
  printf 'RUN-V' > "$W/vtm/target/$J"; printf 'RUN-I' > "$W/ing/target/$J"
  printf 'R4Q' > "$W/vtm/target/$J.rollback_r4q"; printf 'R4Q' > "$W/vtm/target/$J.v12swap_dup"
  printf 'V11' > "$W/vtm/target/$J.bak_v12pre_20261103_1033"; touch -d '40 days ago' "$W/vtm/target/$J.bak_v12pre_20261103_1033"
  printf 'PINNED' > "$W/vtm/target/$J.pinned_only"; touch -d '90 days ago' "$W/vtm/target/$J.pinned_only"
  printf 'OLDSWAP' > "$W/vtm/target/$J.bak_swap_20260101"; touch -d '90 days ago' "$W/vtm/target/$J.bak_swap_20260101"
  printf 'JUNK-S' > "$W/vtm/target/$J.bak_shadow_ "; touch -d '60 days ago' "$W/vtm/target/$J.bak_shadow_ "
  printf 'JUNK-M' > "$W/vtm/target/$J.a b z"; touch -d '60 days ago' "$W/vtm/target/$J.a b z"
  for i in 1 2 3 4; do printf "JUNK$i" > "$W/vtm/target/$J.junk$i"; touch -d "$((50 - i)) days ago" "$W/vtm/target/$J.junk$i"; done
  printf 'QF3' > "$W/ing/target/$J.bak_ingqf_x"; printf 'OLDI' > "$W/ing/target/$J.old1"; touch -d '30 days ago' "$W/ing/target/$J.old1"
  printf 'OLDI2' > "$W/ing/target/$J.old2"; printf 'OLDI3' > "$W/ing/target/$J.old3"; touch -d '20 days ago' "$W/ing/target/$J.old2" "$W/ing/target/$J.old3"
  printf 'BKJAR' > "$W/vtm/backup_l3_x/$J"; printf 'conf' > "$W/vtm/backup_l3_x/env.sh"
  seq 1 20000 > "$W/vtm/logs/full.log.1"; touch -d '30 days ago' "$W/vtm/logs/full.log.1"; echo now > "$W/vtm/logs/full.log"
  seq 1 100 > "$W/ing/logs/full.log.2"; touch -d '10 days ago' "$W/ing/logs/full.log.2"
  echo old > "$W/vtm/logs/archived/full.log.2025-09-25.0.gz"; touch -d '400 days ago' "$W/vtm/logs/archived/full.log.2025-09-25.0.gz"
  echo z > "$W/z"; echo b > "$W/vtm/target/b"   # bay: tach tu 'a b z' khong duoc dung toi
  # script tro md5: PINNED + bat buoc
  { echo "OLD_MD5=$(md5 "$W/vtm/target/$J.pinned_only")"; echo "R=$(printf R4Q | md5sum | cut -c1-32) V11=$(printf V11 | md5sum | cut -c1-32)";
    echo "QF3=$(printf QF3 | md5sum | cut -c1-32) RUNV=$(printf RUN-V | md5sum | cut -c1-32) RUNI=$(printf RUN-I | md5sum | cut -c1-32)"; } > "$W/pins.sh"
  setsid bash -c "cd '$W/vtm' && exec 3<'$W/vtm/target/$J' && exec -a 'java x.BinanceOrderTradingManager $TAG' sleep 600" >/dev/null 2>&1 < /dev/null &
  setsid bash -c "cd '$W/ing' && exec 3<'$W/ing/target/$J' && exec -a 'java x.BinanceDataIngestor $TAG' sleep 600" >/dev/null 2>&1 < /dev/null &
  sleep 0.5
}
export SSH_242="bash -c" CL_APP="$W/vtm" CL_ING="$W/ing" CL_LOGDIR="$W/logdir" CL_JOURNAL=0 CL_SCRIPTS="$W/pins.sh" \
  CL_PP_V="BinanceOrderTradingManager $TAG" CL_PP_I="BinanceDataIngestor $TAG" \
  CL_REQ_V="$(printf RUN-V | md5sum | cut -c1-32) $(printf R4Q | md5sum | cut -c1-32) $(printf V11 | md5sum | cut -c1-32)" \
  CL_REQ_I="$(printf RUN-I | md5sum | cut -c1-32) $(printf QF3 | md5sum | cut -c1-32)"
T=$W/vtm/target
echo "== cleanup_disk_242: DRY / apply / ten co dau cach / ban cuoi md5 / fail-closed"
mk
OUT=$(cd "$W" && bash "$CL" 2>&1); RC=$?
chk "DRY: rc=0, liet ke xoa junk + ten co dau cach (dung ten), KHONG xoa gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -qF 'SE xoa v_t_m/[$J.bak_shadow_ ]' && echo \"\$OUT\" | grep -qF 'SE xoa v_t_m/[$J.a b z]' && [ -f '$T/$J.bak_shadow_ ' ] && [ -f '$T/$J.junk1' ] && ! echo \"\$OUT\" | grep -q 'No such file'"
chk "DRY: giu ban CUOI cua md5 duoc script tro toi (pinned_only, mtime 90 ngay) + v1.1 bak_v12pre + r4q + bak_swap theo ten" "echo \"\$OUT\" | grep -q 'GIU (md5 trong danh sach.*\[$J.pinned_only\]' && echo \"\$OUT\" | grep -q '\[$J.bak_v12pre_20261103_1033\]' && ! echo \"\$OUT\" | grep -q 'SE xoa.*pinned_only\|SE xoa.*bak_v12pre\|SE xoa.*rollback_r4q\|SE xoa.*bak_swap'"
OUT=$(cd "$W" && bash "$CL" --apply 2>&1); RC=$?
chk "APPLY: xoa junk1-2 + 2 ten co dau cach + jar trong backup_*, GIU junk3-4 (2 moi nhat), pinned_only, r4q x2, v1.1, bak_swap, jar dang chay" "[ $RC = 0 ] && [ ! -e '$T/$J.junk1' ] && [ ! -e '$T/$J.junk2' ] && [ -f '$T/$J.junk3' ] && [ -f '$T/$J.junk4' ] && [ ! -e '$T/$J.bak_shadow_ ' ] && [ ! -e '$T/$J.a b z' ] && [ -f '$T/$J.pinned_only' ] && [ -f '$T/$J.rollback_r4q' ] && [ -f '$T/$J.v12swap_dup' ] && [ -f '$T/$J.bak_v12pre_20261103_1033' ] && [ -f '$T/$J.bak_swap_20260101' ] && [ -f '$T/$J' ] && [ ! -e '$W/vtm/backup_l3_x/$J' ] && [ -f '$W/vtm/backup_l3_x/env.sh' ]"
chk "APPLY: ten co dau cach KHONG lam xoa file khac (z, target/b con)" "[ -f '$W/z' ] && [ -f '$T/b' ]"
chk "APPLY: log da dong >14 ngay -> archived/full.log.1.<ngay>.gz (gzip -t), log <14 ngay va full.log giu; archive log4j cu KHONG bi xoa" "ls '$W/vtm/logs/archived/' | grep -q '^full.log.1.[0-9]\{8\}.gz\$' && gzip -t '$W/vtm/logs/archived/'full.log.1.*.gz && [ ! -e '$W/vtm/logs/full.log.1' ] && [ -f '$W/vtm/logs/full.log' ] && [ -f '$W/ing/logs/full.log.2' ] && [ -f '$W/vtm/logs/archived/full.log.2025-09-25.0.gz' ]"
chk "APPLY collectData: giu jar dang chay + QF3 + 2 moi nhat (old2, old3), xoa old1" "[ -f '$W/ing/target/$J' ] && [ -f '$W/ing/target/$J.bak_ingqf_x' ] && [ -f '$W/ing/target/$J.old2' ] && [ -f '$W/ing/target/$J.old3' ] && [ ! -e '$W/ing/target/$J.old1' ]"
mk; mkdir -p "$W/noproc"
OUT=$(cd "$W" && CL_PROC="$W/noproc" bash "$CL" --apply 2>&1); RC=$?
chk "mat quyen doc /proc => ABORT truoc khi xoa, khong doi gi" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT/FAIL: khong doc duoc' && [ -f '$T/$J.junk1' ] && [ -f '$T/$J.bak_shadow_ ' ]"
pkill -f "BinanceOrderTradingManager $TAG"; sleep 0.3
setsid bash -c "cd '$W/vtm' && exec -a 'java x.BinanceOrderTradingManager $TAG' sleep 600" >/dev/null 2>&1 < /dev/null & sleep 0.5
OUT=$(cd "$W" && bash "$CL" --apply 2>&1); RC=$?
chk "jar cua JVM khong co trong danh sach file dang mo => ABORT, khong doi gi" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'khong thay jar dang chay' && [ -f '$T/$J.junk1' ]"
mk; sed -i '/V11=/d' "$W/pins.sh"
OUT=$(cd "$W" && bash "$CL" --apply 2>&1); RC=$?
chk "script khong con tro md5 bat buoc (v1.1) => ABORT truoc ssh, khong doi gi" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: danh sach md5 lay tu script thieu md5 bat buoc' && [ -f '$T/$J.junk1' ]"
mk
OUT=$(cd "$W" && CL_SCRIPTS="$W/pins.sh:$W/khong_co.sh" bash "$CL" 2>&1); RC=$?
chk "script nguon mat => ABORT" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT: khong doc duoc script'"
pkill -f "$TAG" 2>/dev/null
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
