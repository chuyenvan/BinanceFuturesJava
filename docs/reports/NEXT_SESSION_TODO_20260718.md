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


## 🌙 CHẠY ĐÊM 17→18 (Uni ngủ; master orchestrate, dùng agents cho việc nặng)
- **Tự chạy (0 token):** `ladder_1784297380` — tr24 (11/16 lúc ghi) → tr72 → DỪNG ở gate `decide_tr`.
  Sáng đọc `wfo_report_ev2_tr24.md` + `_tr72.md`, chấm pass-criteria, so proxy +14.8. KHÔNG tự trả gate
  (verdict = việc Uni).
- **Agent chuẩn bị (KHÔNG deploy/chạy):** thêm config `TRAIL_PEAK_MODE=high|close` (high=mặc định=hành vi cũ;
  close=anchor trailing theo priceClose thay maxPrice — chống wick/giật) + metric premature-stop-rate.
  Build jar local verify compile. Commit để Uni review sáng. KHÔNG đụng WFO đang chạy, KHÔNG deploy Oracle.
- **KHÔNG parallel được** high-vs-close với kill-test: chung jobstore-226 → phải chạy SAU tr72 (hoặc sau verdict).

## ☀️ AGENDA SÁNG (bàn với Uni)
1. Verdict +TR (tr24 vs tr72 vs pass-criteria + proxy). Sống → decompose (code LADDER_FORCE_TIMESTOP → REF/B0).
   Chết → nút thắt = entry (edge +0.72 mỏng), quay lại selector.
2. Review diff TRAIL_PEAK_MODE của agent → nếu +TR sống: deploy jar + chạy ladder high-vs-close (nối sau).
3. Chốt thứ tự: (a) decompose entry/trailing, (b) high-vs-close, (c) trailing sweep (arm/giveback/horizon).

## ON-THE-HORIZON (đừng rơi)
- TRAIL_PEAK_MODE high|close + premature-stop metric (agent đang prep).
- 2s/tick study: **BỎ** (không đủ độ phủ, Uni chốt 2026-07-17).
- Long-term entry features (SMA200 slope/regime) → chỉ nếu +TR chết & quay lại entry-veto (KHÔNG cho SL).
- Kaggle-WFO kernel bake env (nếu ladder chạy lặp nhiều) → lấy lại 5 node tăng tốc.


## ⚑ VERDICT +TR (2026-07-18) — FAIL, hệ ≈ BREAKEVEN capital-constrained
Kill-test `ladder_1784297380` (parked ở decide_tr, KHÔNG trả — để tham chiếu). tr24 & tr72 đều FAIL:
WFE median 0.20, SUCCESS 4-5/16, BURN 5-6/16, ZERO 4 (2022 = EV2 pred chỉ có 2023+, artifact).
- **Execution SẠCH (C pass):** lỗ BURN cực nhỏ (−0.02%..−0.52% vốn/window), maxDD worst 9%, 0 margin-call.
  → KHÔNG over-leverage/bug sizing. Net toàn kỳ ≈ **+0.6% ~2.5 năm = FLAT**.
- **Kết luận:** proxy +14.8/kèo là ẢO; edge selector +0.72 gross bị phí 0.2%×nghìn-lệnh + fill ăn sạch → breakeven.
  **Nút thắt = ENTRY edge quá mỏng.** Trailing/SL không phải thủ phạm.
- Lưu ý: kill-test gate-OFF (ABLATION_MODE=B). Chưa loại trừ gate-ON tip breakeven→dương.

## ĐANG CHẠY / HƯỚNG
- **Gate-ON confirm** (rẻ, 1 WFO): `wfo_fanout wfo_ds_ev2 ... ABLATION_MODE=A,WFO_DISABLE_DCA=1,TIME_STOP_HOURS=24`
  tag `ev2_gateon`. So vs tr24 (gate-off). Đọc `wfo_report_ev2_gateon.md`.
- **Kiến trúc entry:** gate=KHI-NÀO (market timing, pred.bin, fail standalone 43.8%); selector=COIN-NÀO (EV2 per-coin, edge mỏng).
  2 trục vuông góc. Redesign B: (1) selector + feature dài hạn, (2) gate timing, (3) **HỢP NHẤT 1 model** (market+coin+long-term
  → P(coin lời NGAY) — học tương tác "pump trong downtrend dễ về 0"). Nghiêng (3) hoặc (1).
- **B chặn:** feature dài hạn (SMA200 slope, trend-vs-BTC, dist-from-SMA200) CHƯA export trong ff (dài nhất hiện là 24H)
  → cần sửa Java exporter + re-export ff + retrain. Không phải Kaggle-1-lệnh.

## ĐÃ DỌN
- close-run (ladder_peak) STOP (moot vì +TR high đã fail). Jar deployed hiện = TRAIL_PEAK_MODE (md5 ba2fbda9, default high).


## ⭐ BREAKTHROUGH + FAITHFULNESS PASS (2026-07-18 chiều)

### Faithfulness tích hợp EV2→WFO = PASS (gỡ nỗi lo "test sai do code")
- Entry-match winIdx=8 (2024Q1): **100% (97/97) entry truy vết về pred EV2**, đúng coin/ts, p6 median 0.71. Không entry lạ.
- 3 lớp nhất quán: placebo PASS + (proxy +0.72 − ma sát 0.8% ≈ WFO breakeven) + entry-match 100%.
- → **Verdict regime-timing là THẬT, không phải bug.** Log-flag `WFO_LOG_ENTRIES` env-gated commit ebad0c5.
- Lưu ý: sim gate = score threshold 0.15 (nới hơn p6≥0.7) → nhận vài pick [0.66,0.70). Không bug, có thể siết.

### oiz-veto = ĐÒN BẨY SỐ 1 (chưa cần short/feature mới)
Lọc entry theo oi_z (giữ 30% tốt nhất): net **0.52→1.95/kèo (4×)**, **CHOP 0→+1.88**, tpq 460→121.
Sau slippage 0.6%: net +1.35, chop +1.28 — **dương CẢ 2 regime**. f8/f14/f22 tương tự (cùng họ OI/vol).
→ **Fix regime-timing.** CAVEAT: Q chọn post-hoc → **cần WFO xác nhận real-path** + slippage thật. ĐÂY LÀ ƯU TIÊN 1.

### short = ĐÒN BẨY SỐ 2, alpha CÓ THẬT
Classifier dự dump **AUC 0.85 (4h)** > long 0.74. Accounting v1 (SL chặt 8 + target +6 cố định) tệ =
RR ngược. **Đã sửa v2** (kernel short-selector v2 đang chạy): SL rộng {8,15,20,30} + let-dump-run (−retEnd_H,
stop nếu rise≥S), horizon 4h/12h/24h. Chờ kết quả v2 để xem short net_chop dương ở SL/horizon nào.

### ĐANG CHẠY / NEXT
- short-selector v2 (Kaggle) — chờ.
- **ƯU TIÊN 1: đưa oi_z veto vào WFO real-path** (entry gate = p6 AND oi_z≤Q) → xác nhận +1.9 net + chop dương
  có sống capital-constrained không. Đây là con đường ngắn nhất tới hệ có lời.
- slippage: HOÃN (làm sensitivity 0.1/0.3/0.6 khi ráp; đo thật để sát go-live).
- short: nếu v2 net_chop dương → theo short_strategy_roadmap.md (hard-SL + funding ON + sim riêng).
