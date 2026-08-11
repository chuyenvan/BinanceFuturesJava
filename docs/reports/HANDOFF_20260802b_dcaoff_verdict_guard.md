# HANDOFF 2026-08-02 (b) — dcaoff verdict + guard chong-de — ĐỌC TRƯỚC

> Nối từ `START_HERE_20260802.md` / `HANDOFF_20260802_leg1_edge_dca_reframe.md`.
> Phiên này: chạy lại dcaoff (fail cũ do infra), chốt "bỏ DCA", vá lỗ hổng wipe, quyết bỏ WFE khỏi verdict frozen.

## 1. dcaoff_k8 — ĐÃ TRẢ LỜI: bỏ DCA cho gọn (có số)
Run cũ FAIL chỉ vì Aerospike 226 rớt kết nối tạm (không phải kết quả chiến lược). Chạy lại sạch 16/16,
config = frozen + `DCA_GRID_ENABLED=false DCA_GRID_SCALAR=false DCA_TIER_MARGIN_ENABLED=false`,
n=1 seed=42, 2 Oracle worker, `gatecount.jar`, `WFO_HARNESS_FIX=true`. So với loose_k8 (DCA on):

| Metric | loose_k8 (DCA on) | dcaoff (DCA off) |
|---|---|---|
| %OOS-dương lenient | 88% (14/16) | 88% (14/16) |
| Tổng OOS PnL | ~14,192 | ~16,826 (+18%) |
| maxDD-OOS xấu nhất | 19.6% | 23.8% |
| Window âm | w3(2022Q4), w14(2025Q3) | w9(2024Q2), w14(2025Q3) |

→ **DCA không cộng ròng.** Chỉ tái phân phối: cứu w3 (−17→+388) nhưng làm hỏng w9 (+800→−435). Robustness
bằng nhau, PnL cao hơn, engine gọn hơn. maxDD nhỉnh +4pp (winner chạy to hơn) nhưng vẫn xa ngưỡng 50%.
Report lưu: `.run/mcp_ce/wfo_report_dcaoff_k8.md` (và loose baseline `wfo_report_loose_k8_full.md`).

## 2. Verdict frozen — BỎ WFE (Uni chốt)
WFE = OOS/IS của một cuộc SEARCH → vô nghĩa với config frozen (không search). Verdict frozen từ nay đọc
2 tiêu chí áp dụng được: **%OOS-dương ≥ 70% + maxDD-OOS ≤ 50%**.
→ **DCA-off frozen PASS** (88% ≥70, 23.8% ≤50). loose_k8 cũng PASS (88%, 19.6%). "FAIL" in ra chỉ là
artifact WFE, bỏ qua.
Cơ chế genome (đọc `StrategyWfoTask`): env frozen chỉ đổi CẤU TRÚC gene, 14/16 gene còn lại range mở →
N>1 = search = argmax OVERFIT (đã xác nhận: loose N=30 search 69% < frozen 88%). Muốn WFE frozen thật cần
cờ Java `WFO_FREEZE_GENOME` pin toàn bộ gene + rebuild jar — HOÃN (không cần cho deploy).

## 3. Lỗ hổng wipe — ĐÃ VÁ (Python, không rebuild jar)
Root cause (đọc `WfoJobStore.java`): jobstore 226 dùng CHUNG set `wfo_jobs` + 1 index `__job_index__`,
job-id `strat-wNN` không tách theo tag → mỗi `wfo_fanout` reset đè lên nhau. Đó là cách confirm_n30 (N=30)
mất verdict: dcaoff reset đè trước khi kịp lưu report.
Fix: thêm `_autosnap_prev_report()` vào `cmd_wfo_fanout` (mcp_tools-v3.py) — TRƯỚC khi reset, tự snapshot
report run trước ra `wfo_report_autosnap_<ts>.md` nếu còn window DONE. Dùng `report <group>` + jar của run
(gatecount) để ra bản P1 lenient đúng. Non-fatal. **Đã test live**: snapshot đúng 16 DONE / 88% lenient.
py_compile OK; repo + bản Oracle `/home/ubuntu/claudedata/.run/mcp_tools-v3.py` đã sync (md5 khớp). +36 dòng.
Namespace tách-theo-tag đúng nghĩa (Java `WFO_STATE_SET` per-tag) HOÃN: cần rebuild jar, mà jobstore serial
nên autosnap đã đủ chặn mất verdict.

## 4. STEP 2 — SẴN SÀNG (nền = DCA-off frozen)
Baseline chốt: DCA-off frozen (PASS 88%/24%). Sweep so với baseline này, mỗi lần 1 cụm, đọc raw PnL/window
+ %OOS lenient + maxDD:
- **Trailing** (ưu tiên — chỗ tiền): `TS_GIVEBACK_RATIO` {0.3,0.5,0.7} × `TS_MIN_GAP` {0.005,0.01,0.02}.
- **Phao F**: `HARD_SL_PCT` {0.65,0.70,0.75} (đã đo cliff ~−70).
- Bỏ nhánh DCA sweep (đã chốt DCA không cộng ròng).
Lệnh mẫu (Oracle): `cd /home/ubuntu/claudedata/.run && CE_RUN_DIR=.../mcp_ce CE_LOCKS_DIR=.../locks
WFO_HARNESS_FIX=true python3 mcp_tools-v3.py wfo_fanout <ds> <gatecount.jar> 1 42 2 0 <tag> "<env>"`.
Đọc verdict ĐÚNG: `WfoCoordinator report strategy_window` với `WFO_HARNESS_FIX=true` + `gatecount.jar`
(KHÔNG dùng wfo_report trần / preflight-v42.jar → ra bản cache strict sai).

## 5. Nợ / chờ Uni
- **Commit** (Uni tự thời điểm): `orchestrator/mcp_tools-v3.py` +36 (guard autosnap). git vẫn bẩn từ phiên cũ.
- Optional: cờ `WFO_VERDICT_NO_WFE` (Java) để tool tự in PASS cho frozen — hiện đọc tay 2 tiêu chí.
- Optional: `WFO_FREEZE_GENOME` nếu sau này cần WFE frozen thật.

## Hạ tầng phiên này
- SSH từ local Windows: dùng `C:\Program Files\Git\usr\bin\ssh.exe` (System32 OpenSSH hỏng, exit 255).
- `mcp_tools-v3.py` chạy TRÊN Oracle, cần env `CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce` +
  `CE_LOCKS_DIR=.../locks` (mặc định trỏ `/workspace` → PermissionError).
- 226 Aerospike (`103.157.218.226:3222`) từng rớt ~14:19–14:24, sau đó OK. Kiểm trước khi fanout.
