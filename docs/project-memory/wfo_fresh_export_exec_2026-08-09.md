# FRESH EXPORT 0.10 — EXEC LOG (2026-08-09/10)

> Uni chốt: TOP_PCT=**0.10**, grid **1m tuyệt đối**, label filtered khớp features. Log để session sau tiếp nối.

## ✅ HOÀN TẤT tới build_ds+validate (2026-08-10 06:29)
Chuỗi: export filtered 0.10 → selector canonical → build_ds → validate PASS + ký.
**Dataset canonical: `/home/ubuntu/claudedata/wfo_ds_canon_1m_h4h`** (market.bin 55MB + pred.bin/gate 44MB + funding.bin/selector 374MB + manifest). `VALIDATED_BY=python-validator@2026-08-10T06:29+0700-PASS`.
- manifest: codeGitSha=**8741f85154e04d57c48da9c55472cea7e55eed2a**, leakFreeFrom=**2023-01-01**, horizonIdx=**0**(4h), foldCount=**14**, sourcePredSet=ai_pred_market_gate_wfo, fundingPredDir=/home/ubuntu/claudedata/predwf_canon.
- validate: 14 fold OOS 2023-01→2026-06-30 span 90-92d nan=0%, OOS sớm nhất=2023-01-01, market/pred/funding off-grid=0. WARN 1 (gate 921,600 ts <2023-01 = warmup, vô hại vì funding.bin bắt đầu 2023-01). FAIL 0.

## DỮ LIỆU + CODE (đường dẫn)
- Kaggle: `funding-selector-wfo-data-1m` (features .t1c filtered 0.10 + label .pb + oi_percoin_full.bin full-native + symbol_map.csv), `sel1m-code` (gen+readers, pb2 patch), `wfo-gate-pred-1m`.
- Windows repo `E:\educa\source\github\20260415\BinanceFuturesJava` HEAD=8741f85. Kernel dirs `C:\Users\pc\sel1m_kernel_n0..n3` (gen5nodes.py). gen `C:\Users\pc\sel1m_code\`. 14 predict_wf `C:\Users\pc\predwf_canon\` = Oracle `/home/ubuntu/claudedata/predwf_canon/`.
- Oracle jar build_ds/fanout: `binance-fresh-20260809.jar` (khớp code_sha; ExportWfoDataset). Fanout framework jar = `gatecount.jar`.
- Vận hành ssh Oracle qua Git ssh: `C:\Users\pc\_ora2.bat` (dùng `"C:\Program Files\Git\usr\bin\ssh.exe"`). scp Git. nohup phải `</dev/null`.

## SELECTOR CANONICAL (v7) — cách chạy (nếu cần lại)
Gen = canonical `ml/training/gen_funding_wf_predictions.py` + sửa: `build_features_memmap` **đọc Tool1 THEO NĂM** (không giữ a full) + merge_asof per-năm (OI full-native, biên lo−OI_TOL) + ghi memmap tofile-append; fold-training memmap. `block_lo=c`, `FIRST_CUTOFF=20230101`, HORIZONS=4h, NUM_NODES=4. Env kernel: SELECTOR_GRID_MIN=1, CHUNK_YEARS=1, MMAP_DIR=/kaggle/working (KHÔNG /tmp=tmpfs), LABEL_CSV=glob .pb. Verify local per-year==full & memmap==in-RAM (ALL_MATCH). Kết quả: 59,440,991 rows, base 4h≈0.15, leak-free.
**Bài học OOM (5 vòng):** giữ a+ao full + tích luỹ chunks = OOM; /tmp=tmpfs (memmap tốn RAM); kaggle output kẹt nếu memmap to nằm /kaggle/working (crash bỏ qua os.remove). Fix cuối: per-year read + memmap đĩa thật → peak ~14GB.

## MAPPER + GATE (đã verify)
- Mapper: 776 symId, 0 thiếu csv; corr ret15m vs Binance Vision = 1.000 (BTC/KEY/SFP/ILV). 8 symId trùng (843-850) ngoài data, vô hại.
- Gate: `wfo_gate_pred.csv` 2.76M, 14 fold WF leak-free, **coverage 2023+ = 99.98%**. Set Aerospike `ai_pred_market_gate_wfo` ĐÃ nạp (build_ds đọc predCount=2,760,442). Kaggle `wfo-gate-pred-1m`.

## ⏭️ CÒN LẠI — FANOUT (strategy WFO, frozen verdict-M)
Dataset đã sẵn sàng. Chạy backtest/HPO frozen genome trên `wfo_ds_canon_1m_h4h`:
- Frozen loose_k8 (88% %OOS): `TS_GIVEBACK_FLOOR=true SELECTOR_RANK_TOPK=8 SIM_MIN_MOMENTUM_15M=0.008 DCA_GRID_ENABLED=true DCA_GRID_SCALAR=true DCA_GRID_L1=-0.30 DCA_GRID_STEP=0.20 DCA_GRID_LEGS=3 DCA_GRID_W_RATIO=1.0 DCA_GRID_SCALE=4 DCA_TIER_MARGIN_ENABLED=true DCA_TIER_CAP_BASE=0.50 DCA_TIER_CAP_STEP=0.10 SIM_BREAKER_MODE=OFF SIM_APPLY_FUNDING=true` + `WFO_HARNESS_FIX=true`.
- Jar `gatecount.jar`, `WfoCoordinator/WfoWorker` package `com.binance.chuyennd.ai_ml.wfo.framework`. Verdict đọc qua `WfoCoordinator report` (KHÔNG tin wfo_report md cache).
- ⚠️ **LANDMINE: jobstore box 226 (103.157.218.226:3222 ns=ticker) đã quyết RETIRE** — kiểm còn sống? repoint sang Oracle? (wfo_fanout tự reset coordinator). Cần chốt trước khi fanout.
- N=1 (frozen, 1 sample) trước → đọc verdict/PnL/posRatio/maxDD → N=30 confirm.

## DỌN RÁC KAGGLE (Uni tự xoá web): funding-tool1-features(-unfiltered), funding-predict-1m-v1, funding-predict-v1, funding-model-v1, wfo-ds-ret2-4h-ff, wfo-oizgate, wfo-dataset-wf-leakfree, wfo-dataset-wf-v3, hpo-ticker-mini. (+ predwf_merge cũ 15m-OI trên Windows; 8 symId trùng 843-850.)
