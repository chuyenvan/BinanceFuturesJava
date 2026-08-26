#!/bin/bash
# cpcv_fanout.sh STAGE  — dieu phoi Kaggle master-worker cho CPCV validation (deterministic, resume).
# STAGE: upload | kernels | parity | fanout | poll | verdict | all
set -u
KG=/home/ubuntu/kaggle_latest_venv/bin/kaggle
U=chuyendinh
JAR=/home/ubuntu/java/cpcv.jar
CFG=/home/ubuntu/cpcv/run/config.properties
DS=/home/ubuntu/wfo_ds_VAL
CELLS=/home/ubuntu/cpcv/wf_full/cells.jsonl
BCELLS=/home/ubuntu/cpcv/baseline_cells.jsonl
BORACLE=/home/ubuntu/cpcv/baseline_oracle.jsonl
WORKER=/home/ubuntu/cpcv/run_cpcv_worker.py
W=/home/ubuntu/cpcv/kg
N=5
TICK="$U/wfo-ticker-2024h1 $U/wfo-ticker-2024h2 $U/wfo-ticker-2025h1 $U/wfo-ticker-2025h2"
L=/home/ubuntu/cpcv/fanout.log
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$L"; }

mkjson(){ printf '{"title":"%s","id":"%s/%s","licenses":[{"name":"CC0-1.0"}]}\n' "$2" "$U" "$2" > "$1/dataset-metadata.json"; }

ds_ready(){ # id  -> echo status
  $KG datasets status "$U/$1" 2>/dev/null | head -1
}
ds_push(){ # dir  id
  mkjson "$1" "$2"
  if [ "$(ds_ready "$2")" = "ready" ]; then
    ( cd "$1"; $KG datasets version -m "upd" -d >>"$L" 2>&1 )
  else
    ( cd "$1"; $KG datasets create -r skip >>"$L" 2>&1 )
  fi
}
ds_wait(){ # id
  for i in $(seq 1 60); do [ "$(ds_ready "$1")" = "ready" ] && { log "ds $1 ready"; return 0; }; sleep 10; done
  log "ds $1 NOT ready (timeout)"; return 1
}
kmeta(){ # dir  name  cells_ds
  local srcs="\"$U/cpcv-jar\",\"$U/wfo-ds-val\",\"$U/$3\""
  for t in $TICK; do srcs="$srcs,\"$t\""; done
  cat > "$1/kernel-metadata.json" <<EOF
{"id":"$U/$2","title":"$2","code_file":"run_cpcv_worker.py","language":"python",
 "kernel_type":"script","is_private":true,"enable_gpu":false,"enable_internet":true,
 "dataset_sources":[$srcs],"competition_sources":[],"kernel_sources":[]}
EOF
}
kstatus(){ $KG kernels status "$U/$1" 2>/dev/null | head -3; }

stage_upload(){
  log "UPLOAD start"
  rm -rf "$W"; mkdir -p "$W/ds_jar" "$W/ds_wfo" "$W/cells_parity"
  cp "$JAR" "$W/ds_jar/cpcv.jar"; cp "$CFG" "$W/ds_jar/config.properties"
  ds_push "$W/ds_jar" "cpcv-jar"
  cp "$DS"/*.bin "$DS/manifest.txt" "$W/ds_wfo/"
  ds_push "$W/ds_wfo" "wfo-ds-val"
  cp "$BCELLS" "$W/cells_parity/cells.jsonl"
  ds_push "$W/cells_parity" "cpcv-cells-parity"
  split -d -n l/$N "$CELLS" "$W/shard_"
  for i in $(seq 0 $((N-1))); do
    d="$W/cells_$i"; mkdir -p "$d"; cp "$W/shard_0$i" "$d/cells.jsonl"
    ds_push "$d" "cpcv-cells-$i"
  done
  ds_wait "cpcv-jar"; ds_wait "wfo-ds-val"; ds_wait "cpcv-cells-parity"
  for i in $(seq 0 $((N-1))); do ds_wait "cpcv-cells-$i"; done
  log "UPLOAD done"
}
stage_kernels(){
  log "KERNELS build"
  mkdir -p "$W/k_parity"; cp "$WORKER" "$W/k_parity/run_cpcv_worker.py"; kmeta "$W/k_parity" "cpcv-w-parity" "cpcv-cells-parity"
  for i in $(seq 0 $((N-1))); do
    d="$W/k_$i"; mkdir -p "$d"; cp "$WORKER" "$d/run_cpcv_worker.py"; kmeta "$d" "cpcv-w-$i" "cpcv-cells-$i"
  done
  log "KERNELS done"
}
stage_parity(){
  log "PARITY push"
  ( cd "$W/k_parity"; $KG kernels push -p . >>"$L" 2>&1 )
  for i in $(seq 1 90); do s=$(kstatus "cpcv-w-parity"); echo "$s" | grep -qi complete && break; echo "$s" | grep -qi error && { log "PARITY kernel error"; return 1; }; sleep 20; done
  rm -rf "$W/out_parity"; mkdir -p "$W/out_parity"
  $KG kernels output "$U/cpcv-w-parity" -p "$W/out_parity" >>"$L" 2>&1
  python3 /home/ubuntu/cpcv/parity_check.py "$W/out_parity/out.jsonl" "$BORACLE" | tee -a "$L"
}

stage_fanout(){
  log "FANOUT push $N kernels"
  for i in $(seq 0 $((N-1))); do ( cd "$W/k_$i"; $KG kernels push -p . >>"$L" 2>&1 ); log "pushed cpcv-w-$i"; done
}
stage_poll(){
  log "POLL $N kernels"
  for i in $(seq 0 $((N-1))); do
    for t in $(seq 1 180); do s=$(kstatus "cpcv-w-$i"); echo "$s" | grep -qi complete && { log "cpcv-w-$i complete"; break; }; echo "$s" | grep -qi error && { log "cpcv-w-$i ERROR"; break; }; sleep 20; done
    rm -rf "$W/out_$i"; mkdir -p "$W/out_$i"
    $KG kernels output "$U/cpcv-w-$i" -p "$W/out_$i" >>"$L" 2>&1
  done
  cat "$W"/out_*/out.jsonl > /home/ubuntu/cpcv/wf_full/results.jsonl
  log "MERGED $(wc -l < /home/ubuntu/cpcv/wf_full/results.jsonl) rows -> results.jsonl"
}
stage_verdict(){
  log "VERDICT"
  cd /home/ubuntu/cpcv
  python3 run_cpcv_validation.py data_tiers.json /home/ubuntu/cpcv/wf_full --n 200 --seed 42 >>"$L" 2>&1
  log "verdict.json:"; cat /home/ubuntu/cpcv/wf_full/verdict.json | tee -a "$L"
}
case "${1:-all}" in
  upload) stage_upload;;
  kernels) stage_kernels;;
  parity) stage_parity;;
  fanout) stage_fanout;;
  poll) stage_poll;;
  verdict) stage_verdict;;
  all) stage_upload && stage_kernels && stage_parity && stage_fanout && stage_poll && stage_verdict;;
  *) echo "usage: $0 upload|kernels|parity|fanout|poll|verdict|all";;
esac
