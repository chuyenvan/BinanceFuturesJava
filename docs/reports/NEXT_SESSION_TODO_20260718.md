# HANDOFF 2026-07-18 — đọc file này + docs/rules/ce-buttons.md là đủ ngữ cảnh.

## 🔒 2 QUY TẮC (chi tiết trong ce-buttons.md §"2 QUY TẮC VẬN HÀNH")
- **R1 CE-first:** config-động/lặp ≥2 lần → viết nút/pipeline; thiếu param thì bổ sung, KHÔNG SSH tay.
  One-off đặc thù → cơm nhưng track script vào repo. Đừng block science để xây infra.
- **R2 Handoff-luôn:** sau mỗi milestone cập nhật file này (live+concise+trim). Không bê full context.

## ĐANG CHẠY (check trước tiên)
- **`ce pipe_status ladder_1784297380`** — KILL-TEST +TR (bỏ DCA + bỏ gate + nuôi let-winner-run).
  9 step: tr24 (TIME_STOP_HOURS=24) → tr72 → gate `decide_tr`. Oracle-only 2-worker, ~nhiều giờ/stage.
  Khi tới `decide_tr` (WAITING_LLM): kéo `wfo_report_ev2_tr24.md` + `_tr72.md`, chấm pass-criteria
  (70% OOS-dương / WFE median≥0.5 / worst maxDD≤50%), so proxy +14.8/kèo (chắc chắn tụt khi capital-constrained).
  Trả gate: ghi `mcp_ce/pipe_ladder_1784297380_LLM_ANSWER.json {"answer":"..."}` + `ce pipe_resume`.

## SO ĐÃ CHỐT (verified) — chi tiết: docs/insights/sl4h_label_experiment.md
- Kiến trúc: **bỏ DCA + bỏ gate + EV2 selector n6 + exit nuôi-lâu**. DCA edge ~0 (Track A); EV2 edge thật
  (placebo PASS) nhưng **mỏng: trade-weighted +0.72/kèo P0.7**, 2026 ≈ 0.
- Chọn-n: **n6** (n3 biên ~0, n9/n15 kém/median-inflated).
- **Price-SL KHÔNG giúp** (fix hại, adaptive q90 ≈ none) → trụ SL đóng (âm); chặn đuôi chỉ còn entry-veto.
- **Trailing nuôi-lâu là đòn bẩy** (proxy E5 24h +14.8; điều-kiện-hóa theo P9 LÀM HẠI → nuôi hết, đừng lọc).
- V4.2 objective: archive (không sửa được evenness; tần suất giải bằng horizon 12h). gate-model=market model (FAIL WFO).

## LADDER (khung baseline — cure "đi mù")
`B0(take-all) → REF(no-SL,đóng4h) → +TR(nuôi24/72) → [+SL price BỎ]`. Mỗi trụ = 1 delta trên REF, cùng WFO.
- REF cần code **`LADDER_FORCE_TIMESTOP`** (buộc time-stop cả lệnh đã-arm) — CHƯA làm, thêm sau khi +TR sống.
- Design đầy đủ: docs/insights/slhard_sim_ladder_DESIGN.md.

## HẠ TẦNG (đã verified turn này)
- Jar `/home/ubuntu/java/simulator/preflight-v42.jar` MD5 `9c1334a7` (TIME_STOP_HOURS env-wire). Backup .bak_20260717.
- Dataset `/home/ubuntu/claudedata/wfo_ds_ev2` (EV2 funding, symId gate-check PASS). funding.bin 372MB = đúng (per-min fill).
- Converter `orchestrator/tools/ev2_csv_to_predictwf.py`; ladder pipeline `orchestrator/pipelines/ladder.json`.
- Push gần nhất: bace1ba (ladder+TIME_STOP env). CHƯA COMMIT: ce-buttons 2-rule + file handoff này → gộp commit.

## SAU KHI +TR CÓ VERDICT
- PASS → code LADDER_FORCE_TIMESTOP → thêm stage REF/B0 → decompose ladder (quy công entry vs trailing).
- FAIL → cả hướng nuôi-lâu chết capital-constrained → xem lại entry (edge mỏng +0.72, decay 2026).
