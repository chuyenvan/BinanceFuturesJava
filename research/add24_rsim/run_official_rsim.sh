#!/bin/bash
# ADD24 R-SIM LUOT CHINH THUC OW1 - prereg 6ee84f17 + ERRATA1 29152e39 (+ ERRATA2 neu MASTER ra). Lenh sim start [2026-07-01; 2026-09-16) +07,
# warm-up buffer 2026-04-02..06-30 (V9 dem 2026Q2 tu 04-01), du lieu <= 2026-09-30 23:59 +07. CHI 1 LAN, SAU A1 duyet harness/launcher.
# + ERRATA2 bb91e639: 2 lane duong gia trong nen (CHINH sim O-L-H-C, DO NHAY O-H-L-C, chi bao cao), khop stop min(SL,open), bo loc pin sim,
# S-G2 gate CA QUY 2026Q3 (sel/follow 07-01..09-30 23:59), S-SZ leg0 moi cum (ke ca cum DCA).
# + ERRATA3 050912ca (LUOT5): B3 N10 = dang giu -> luot 1 (OW1_p1, lane sim) xac dinh N10, n10_held.py xoa nen symbol N10 trong khoang sim
#   giu -> FX_N10; 2 lane chinh thuc chay tren FX_N10; S-G2 cham THO; verdict_e3.py (B1 S-X(b) ti le moi, B2 [-0,2 %; +0,2 %], B4 N11).
# + ERRATA4 03bb65e0 (LUOT6): 1a rig "theo vet" TIER LUOI sim (L12, ADD24_SIMTIER = l6_inputs/simtier_code.csv tu code a8690d46);
#   1b cong V-TIER (vtier.py tren l6_inputs: tier luoi vs tier theo gio, KHONG tai lai ticker) -> cum TIER_DIV loai khoi S-X/S-SZ/S-D;
#   1c co SIM_TIER_STALE luon bat; bang ket qua RESULT_E4.json (summarize_official.py).
# + LUOT7 (EB25/EB28/EB29): mkt toan san CHI cho ngay UTC co gia sim cham bac grid (cum rig theo vet) -> rig co nhanh DCA; S-D OW1 dem
#   ca leg DCA rig ma sim khong co (rig_extra); ssz_inputs_l7.py (giu margin vi the huy niem yet toi luc sim dong; thu tu BIG_DOWN = HashSet sim).
# + ERRATA5 0740e790 (LUOT8): bo cham R1-R6 (score_rsim.py), KET LUAN bang verdict_rsim.py (R7: HUY > FAIL > INSUFFICIENT > PASS_CAN_OWNER;
#   cong lap dat L3/L12 rig_t <= START; co SIM_TIER_STALE + BD_ORDER luon bat); mkt OW1 = dung 09-15..09-22 UTC (EB24).
# usage: run_official_rsim.sh <A1_REF> 29152e39,bb91e639,050912ca,03bb65e0,0740e790
set -u
A1REF=${1:?A1_REF}; ERR=${2:?ERRATA_COMMITS}
[ "$ERR" = "29152e39,bb91e639,050912ca,03bb65e0,0740e790" ] || { echo "TU CHOI: errata phai = 29152e39,bb91e639,050912ca,03bb65e0,0740e790"; exit 9; }
( cd $HOME/claude_master/w3/add24/b/l6_inputs && md5sum -c --quiet MD5SUMS ) || { echo "TU CHOI: l6_inputs md5 sai"; exit 9; }
export ADD24_SIMTIER=$HOME/claude_master/w3/add24/b/l6_inputs/simtier_code.csv
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_ow1; OUT=$S/out_ow1
LOCK=$B/OFFICIAL_ADD24_RSIM.lock; DONE=$B/OFFICIAL_ADD24_RSIM.done
[ -e "$DONE" ] && { echo "TU CHOI: luot chinh thuc DA chay ($DONE)"; exit 9; }
exec 9>"$LOCK"; flock -n 9 || { echo "TU CHOI: khoa $LOCK dang giu"; exit 9; }
FREE=$(df -BM / | awk 'NR==2{gsub("M","",$4);print $4}'); [ "$FREE" -ge 15300 ] || { echo "DUNG: dia / con ${FREE}M < 15300M"; exit 8; }
MA=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$MA" -ge 10000 ] || { echo "DUNG: MemAvailable ${MA}M < 10000M"; exit 8; }
M=$(md5sum < /dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43 | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || { echo "TU CHOI md5 stub $M"; exit 3; }
LOG=$B/official_rsim_$(date +%Y%m%d_%H%M%S).log
{
set -x
echo "OFFICIAL ADD24 R-SIM start $(date -Is) A1=$A1REF ERRATA=$ERR harness_DEV-A=$(cd $HOME/claude_master/w3/add24_wt && git rev-parse HEAD)"
( cd $B && sha256sum *.py *.sh jsrc/com/binance/chuyennd/*/*/*.java jsrc/com/binance/chuyennd/*/*/*/*.java jsrc/com/binance/chuyennd/*/*/*/*/*.java 2>/dev/null ) > $B/official_code_sha256.txt
rm -rf "$FX" "$OUT"; mkdir -p "$FX" "$OUT" "$S/kl_ref_ow1" "$S/kl_ow1"
[ -f $S/kg_pin/exchange_info_pin.json ] && [ "$(md5sum < $S/kg_pin/exchange_info_pin.json | cut -d" " -f1)" = 5a815948d8909ea5b9615b28e28b53da ] || { echo "TU CHOI: thieu pin sim 5a815948"; exit 7; }
DS=$HOME/claude_master/w3/ho5/a3/data26/ds
python3 $B/conv_rsim.py --warm_lo 2026-04-01 --lo 2026-07-01 --hi 2026-10-01 --bins $DS/predict_wf_20260401.bin $DS/predict_wf_20260701.bin --out "$FX" || exit 11
python3 $B/check_conv.py "$FX" 20260701 20261001 || exit 12
# EB5/EB6: cum nhieu leg (DCA) co leg0 TRONG [07-01, 09-16) => can mkt toan thi truong; OW1 da dem = 0 (1 cum leg0 06-25: loai, dem)
NDCA=$(python3 -c "
import csv, collections
g=collections.defaultdict(list)
for r in csv.DictReader(open('$HOME/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv')): g[(r['sym'],r['end'])].append(r['start'])
print(sum(1 for v in g.values() if len(v)>1 and '20260701'<=min(v)[:8]<'20260916'))")
echo "OW1 cum DCA co leg0 trong cua so = $NDCA"
[ "$NDCA" -eq 0 ] || { echo "DUNG (EB5): $NDCA cum DCA leg0 trong OW1 - can mkt (mau dev2_run.sh) -> MASTER"; exit 13; }
KL_OUT=$S/kl_ow1 KL_BEG='20260615 00:00' KL_END='20261001 00:00' python3 -I $B/dl_klines.py || exit 14
python3 -I $B/dl_avail.py --cand "$FX/cand.csv.gz" --lo 2026-07-01 --hi 2026-10-01 --out "$FX" || exit 15
python3 -I $B/dl_ref.py 2026-07-01 2026-10-01 "$S/kl_ref_ow1" || exit 16
# EB25: ngay can mkt (gia SIM cham bac grid cua cum leg0 trong [07-01, 10-01)) -> dl_mkt_days (EB24: tu choi ngay UTC >= 09-30)
( cd $B/l7_inputs && md5sum -c --quiet MD5SUMS ) || { echo "TU CHOI: l7_inputs md5 sai"; exit 9; }
mkdir -p $S/mkt_ow1
python3 $B/mkt_days_ow1.py $B/l6_inputs/cums.csv 1782838800000 1790787600000 $S/mkt_ow1/cums_ow1.csv || exit 29
$B/run_pricedue.sh 1782838800000 1790787600000 $S/mkt_ow1/pricedue.csv $S/mkt_ow1/cums_ow1.csv $B/l7_inputs/closes.csv.gz || exit 29
MDAYS=$(python3 $B/mkt_days_ow1.py $B/l6_inputs/cums.csv 1782838800000 1790787600000 x $S/mkt_ow1/pricedue.csv)
echo "MKT_DAYS=$MDAYS"
[ "$MDAYS" = "2026-09-15,2026-09-16,2026-09-17,2026-09-18,2026-09-19,2026-09-20,2026-09-21,2026-09-22" ] || { echo "DUNG: ngay mkt khac ERRATA5 (09-15..09-22) -> MASTER"; exit 29; }
MKTOPT=""
if [ -n "$MDAYS" ]; then python3 -I $B/dl_mkt_days.py "$MDAYS" $S/mkt_ow1 || exit 29
  # giu PHUT gia cham bac + 16 phut truoc (bo nho rig = n_sym x 5 x (END - phut mkt dau) float, ReplayData.loadMkt; thu DEV7M5 16 ngay)
  python3 -I $B/mkt_filter.py $S/mkt_ow1/mkt.csv.gz $S/mkt_ow1/pricedue.csv $S/mkt_ow1/mkt_f.csv.gz 1782838800000 1790787600000 20000000 > $S/mkt_ow1/mkt_filter.json || exit 29
  cat $S/mkt_ow1/mkt_filter.json; MKTOPT="--mkt $S/mkt_ow1/mkt_f.csv.gz"; fi
python3 -I $B/build_fx.py --fx "$FX" --kl "$S/kl_ow1" --klref "$S/kl_ref_ow1" --end 2026-10-01 --patch_settling --warm_from 2026-04-02 --pin $S/kg_pin/exchange_info_pin.json --end_pad $MKTOPT || exit 17
KL_DIR=$S/kl_ow1 python3 $B/ssz_inputs_l7.py 20260701 20260916 "$FX" > "$FX/ssz_ref_precheck.txt" 2>&1 || exit 18
# ERRATA4 1b: V-TIER (chi du lieu sim da tinh: tier_hourly <= 09-30 23:59 +07, dca_all, simtier_code)
python3 $B/vtier.py 20260701 20260916 "$OUT/vtier.json" $B/l6_inputs $B/l6_inputs/simtier_code.csv || exit 26
python3 -c "import json,sys; v=json.load(open('$OUT/vtier.json')); sys.exit(0 if v['status']!='FAIL_MOMENTS' else 1)" || { echo "DUNG: moc cap nhat tier sim moi trong cua so -> MASTER"; exit 26; }
# ERRATA3 B3: luot 1 xac dinh N10 (guard production chan lenh sim) -> FX_N10 (nen symbol N10 bi xoa trong khoang sim giu)
ADD24_INTRABAR=sim flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh OW1_p1 "$FX" "$OUT" || exit 19
python3 $B/n10_held.py "$OUT/OW1_p1" "$FX" "${FX}_n10" || exit 19
FX=${FX}_n10
for L in sim sens; do
  N=OW1_$L
  ADD24_INTRABAR=$L flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N "$FX" "$OUT" || exit 19
  $B/run_ssz.sh "$OUT/$N" "$FX" || exit 20
  grep -q "^simtier=installed" "$OUT/$N/add24_meta.txt" || { echo "DUNG: L12 tier luoi chua cai"; exit 27; }
  python3 $B/score_rsim.py "$OUT/$N" "$FX" 20260701 20260916 --quarter 2026Q3 --vtier "$OUT/vtier.json" --json "$OUT/$N/score.json" > "$OUT/$N/score.txt" 2>&1 || exit 21
  python3 $B/gates_rsim.py "$OUT/$N" "$FX" > "$OUT/$N/gates.json" || exit 22
  python3 -I $B/classify_sx.py "$OUT/$N" "$FX" 20260701 20260916 $L > "$OUT/$N/classify_sx.txt" 2>&1 || exit 23
  python3 $B/verdict_e3.py "$OUT/$N" "$FX" > "$OUT/$N/verdict_e3.txt" 2>&1 || exit 25
  python3 $B/verdict_rsim.py "$OUT/$N" "$FX" "$OUT/vtier.json" > "$OUT/$N/verdict_rsim.txt" 2>&1 || exit 25
  ( cd "$OUT/$N" && sha256sum verdict_rsim.json verdict_e3.json sim_tier3_block.csv score.json gates.json classify_sx.json result.json legs.csv fills.csv events.csv outcomes.csv trace_dec.csv.gz ssz_jar.csv env_used.sh run.log add24_meta.txt ) > "$OUT/$N/SHA256SUMS"
  mkdir -p $B/official_ow1/$N && cp "$OUT/$N/"{verdict_rsim.json,verdict_rsim.txt,verdict_e3.json,sim_tier3_block.csv,score.json,score.txt,gates.json,classify_sx.json,classify_sx.txt,SHA256SUMS,env_used.sh,add24_meta.txt} $B/official_ow1/$N/
  python3 -c "
import json;r=json.load(open('$OUT/$N/result.json'));r.get('stats',{}).pop('equity',None)
json.dump(r,open('$B/official_ow1/$N/result_noPnL.json','w'),indent=1)"
done
python3 -I $B/lane_diff.py "$OUT/OW1_sim/score.json" "$OUT/OW1_sens/score.json" > $B/official_ow1/lane_diff.json || exit 24
( cd "$FX" && sha256sum * ) > $B/official_ow1/FX_SHA256SUMS
cp "$OUT/vtier.json" $S/mkt_ow1/mkt_manifest.json $S/mkt_ow1/mkt_filter.json $S/mkt_ow1/pricedue.csv $B/official_ow1/ 2>/dev/null; cp $B/l6_inputs/MD5SUMS $B/official_ow1/l6_inputs_MD5SUMS
python3 $B/summarize_official.py "$OUT/OW1_sim" "$OUT/OW1_sens" $B/official_ow1/lane_diff.json "$OUT/vtier.json" $B/official_ow1/RESULT_E4.json || exit 28
# KET LUAN R-SIM (R7) = verdict_rsim lane CHINH (sim); lane do nhay chi bao cao (ERRATA3 B6)
python3 -c "import json; a=json.load(open('$OUT/OW1_sim/verdict_rsim.json')); b=json.load(open('$OUT/OW1_sens/verdict_rsim.json')); json.dump(dict(RESULT=a['RESULT'], main=a, sens_report=b['RESULT'], lane_diff=json.load(open('$B/official_ow1/lane_diff.json'))), open('$B/official_ow1/RESULT_RSIM.json','w'), indent=1, default=str); print('RESULT_RSIM', a['RESULT']['result'])"
cp "$FX/manifest_conv.json" "$FX/fx_check.json" "$FX/n10_held.json" $B/official_ow1/
date -Is > "$DONE"
echo "OFFICIAL ADD24 R-SIM done $(date -Is) -> $B/official_ow1 (khong mo truoc A1)"
} > "$LOG" 2>&1
echo "log=$LOG"
