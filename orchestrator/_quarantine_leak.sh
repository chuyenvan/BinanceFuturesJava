#!/bin/bash
# Quarantine leaked WFO artifacts (reversible mv, keep as evidence). Verify v4 (read-only).
CD=/home/ubuntu/claudedata
Q=$CD/_LEAKED_QUARANTINE
mkdir -p "$Q"
printf 'Quarantined 2026-08-03 boi audit leak: predict_wf single-cutoff full-history (2021-2026) + dataset nhiem.\nDo NOT use. Giu lam bang chung + regression-test.\n' > "$Q/README.txt"

echo "==V4_VERIFY (read-only, chua move)"
echo "-- v4 manifest:"; grep -E 'source|Provenance|leakFree|fundingRaw|Count|exportedAt|Range' "$CD/wfo_dataset_v4/manifest.txt" 2>/dev/null || echo "no v4 manifest"
echo "-- v4 build src:"; grep -rl 'wfo_dataset_v4' "$CD/.run/"*.sh 2>/dev/null | head -3
grep -rhoE 'wfo_dataset_v4.*|WFO_FUNDING_PRED_DIR=[^ ]+' "$CD/.run/build"*.sh 2>/dev/null | head

echo "==QUARANTINE (mv)"
for p in wf_pred_ret2/predict_wf_20260101.bin wfo_ds_ret2_4h wfo_dataset_leaked_restricted; do
  if [ -e "$CD/$p" ]; then
    n=$(echo "$p" | tr '/' '_')
    mv "$CD/$p" "$Q/$n.LEAKED" && echo "MOVED: $p"
  else
    echo "MISSING: $p"
  fi
done
KL=/home/ubuntu/kaggle_pred_cand/out/predict_wf_20260101.bin
if [ -e "$KL" ]; then
  mv "$KL" "$Q/kaggle_pred_cand_predict_wf_20260101.bin.LEAKED" && echo "MOVED: kaggle_leak"
else
  echo "MISSING: kaggle_leak"
fi

echo "==RESULT"
ls -la "$Q"
echo "-- disk:"; df -h /home/ubuntu | tail -1
