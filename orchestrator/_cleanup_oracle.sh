#!/bin/bash
# Don Oracle: xoa cung dataset da CONFIRMED leaked/contaminated (giu 1 file bang chung + moi predict_wf SOURCE dir).
CD=/home/ubuntu/claudedata
Q=$CD/_LEAKED_QUARANTINE
echo "== BEFORE"; df -h /home/ubuntu | tail -1

echo "== (1) xoa quarantine severe-leak/contaminated (giu 1 evidence predict_wf)"
rm -rf "$Q/wfo_ds_ret2_4h.LEAKED" "$Q/wfo_dataset_v4.LEAKED" "$Q/wfo_dataset_leaked_restricted.LEAKED" 2>/dev/null && echo "rm quarantine datasets OK"
rm -f "$Q/kaggle_pred_cand_predict_wf_20260101.bin.LEAKED" 2>/dev/null && echo "rm kaggle dup evidence OK (giu wf_pred_ret2 evidence)"

echo "== (2) xoa 6 old dataset contaminated (audit confirmed, unused, superseded by ret2wf_ff)"
for d in wfo_dataset wfo_dataset_v3 wfo_dataset_v5 wfo_dataset_v6 wfo_dataset_clean wfo_dataset_wf_v3; do
  if [ -e "$CD/$d" ]; then
    sz=$(du -sh "$CD/$d" 2>/dev/null | cut -f1)
    rm -rf "$CD/$d" && echo "DELETED $d ($sz)"
  else
    echo "SKIP (missing) $d"
  fi
done

echo "== AFTER"; df -h /home/ubuntu | tail -1
echo "== con lai (wfo_ds*/wfo_dataset*):"; du -sh $CD/wfo_ds* $CD/wfo_dataset* 2>/dev/null
echo "== quarantine con lai (evidence):"; ls -la $Q 2>/dev/null
