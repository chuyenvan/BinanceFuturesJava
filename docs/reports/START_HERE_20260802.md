# START HERE — session mới (2026-08-02) — đọc file này TRƯỚC

> Chi tiết đầy đủ: `HANDOFF_20260802_leg1_edge_dca_reframe.md`. File này = trạng thái + lệnh để chạy tiếp NGAY.

## Kết luận cứng đã chốt (có số, đừng đo lại)
- **leg1 có edge THẬT +2.2%/lệnh** vs base-rate LỖ −1% (leg1_econ.py, 42.6M label). Engine có lãi, không phải beta.
- **DCA là add-on HIẾM** (99% cụm chỉ leg1). 1:1:2:6 tệ nhất. Grid nên NÔNG+phẳng. Phao F≈−70% gần miễn phí.
- **Trailing giveback-floor** (`TS_GIVEBACK_FLOOR`): +24% PnL cùng maxDD → BẬT.
- **rank-K8 gỡ no-trades**: mọi window có lệnh, đều LÃI, hết dồn w15.
- **Harness fix P0+P1** (`WFO_HARNESS_FIX`, default OFF): %OOS-dương 6%→88% (frozen).
- **HPO argmax OVERFIT**: N=30 search chỉ 69% < frozen 88% (Verdict M tái xác nhận). → **DEPLOY FROZEN, đừng tune bằng argmax.**

## Config frozen "tốt nhất hiện tại" (loose_k8, 88% %OOS-lenient)
`TS_GIVEBACK_FLOOR=true SELECTOR_RANK_TOPK=8 SIM_MIN_MOMENTUM_15M=0.008 DCA_GRID_ENABLED=true DCA_GRID_SCALAR=true`
`DCA_GRID_L1=-0.30 DCA_GRID_STEP=0.20 DCA_GRID_LEGS=3 DCA_GRID_W_RATIO=1.0 DCA_GRID_SCALE=4`
`DCA_TIER_MARGIN_ENABLED=true DCA_TIER_CAP_BASE=0.50 DCA_TIER_CAP_STEP=0.10 SIM_BREAKER_MODE=OFF SIM_APPLY_FUNDING=true`
Dataset: `wfo_ds_ret2wf_4h_ff`. Chạy frozen = `wfo_fanout ... 1 42 2 5 <tag> "<env>,WFO_HARNESS_FIX=true"`.

## ⚠️ Lệnh đọc verdict ĐÚNG (wfo_report đọc md CACHE jar cũ — KHÔNG tin nó)
```
ssh Oracle "cd /home/ubuntu/claudedata/.run/oracle_worker_cwd && \
  WFO_STATE_HOST=103.157.218.226 WFO_STATE_PORT=3222 WFO_STATE_NS=ticker WFO_HARNESS_FIX=true \
  java -cp /home/ubuntu/java/simulator/gatecount.jar \
  com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator report strategy_window" | grep -E 'aggregate\[HARNESS|VERDICT'
```
(Tool `_wfo_coord_cmd` đã patch passthrough WFO_HARNESS_FIX — sync ở orchestrator/mcp_tools-v3.py nhưng bản Oracle mới là bản chạy.)

## ĐANG CHẠY (đọc đầu session mới)
- `dcaoff_k8` fanout (Oracle 2 node, n=1 frozen, DCA OFF) — so với loose_k8(88%) xem DCA hiếm có cộng ròng không.
  Đọc: grep pnl các log `wfo_dcaoff_k8_w*.log` + coordinator report (lệnh trên). DCA-off ≈ loose_k8 ⇒ BỎ DCA cho gọn.

## STEP 2 còn lại (frozen A/B, KHÔNG HPO search; jobstore serial — 1 fanout/lần)
Mỗi cut: 1 fanout frozen n=1, đọc raw PnL/window + posRatio-lenient + maxDD. So với loose_k8 baseline.
- Trailing: `TS_GIVEBACK_RATIO` {0.3,0.5,0.7} × `TS_MIN_GAP` {0.005,0.01,0.02}.
- DCA: grid {−20/−40/−60} vs {−30/−50/−70}; `DCA_GRID_W_RATIO` {1.0,1.5}; phao `HARD_SL_PCT`/F {0.65,0.70,0.75}.

## STEP 3 — làm mịn rank-K8 (sau step 2)
`SELECTOR_RANK_TOPK` {5,8,12} × `SELECTOR_RANK_OFFSET` {0,1,2}. Cân tần suất vs chất lượng.

## Nợ nhỏ
- N=30 với FROZEN genome (không argmax) để có WFE sạch — hoặc bỏ WFE khỏi verdict cho frozen (WFE=oosPnl/isPnl vô nghĩa khi không search).
- Chưa commit rác phiên cũ (notebooklm_ready...). git status còn bẩn — chờ Uni.
- Hạ tầng đã fix & giữ: symlink ticker ở oracle_worker_cwd/kaggle_data_hpo; pandas trên Oracle; 5 kernel wfo-worker bake loose_k8; jar Kaggle java-run-lc = scalar (md5 1c422f25).

## Commit phiên này
dab4d48 (scalar DCA + trailing-floor + verify_stage + leg1-edge), d13c7c2 (harness P0/P1), 28efb8d (tool passthrough + handoff).
