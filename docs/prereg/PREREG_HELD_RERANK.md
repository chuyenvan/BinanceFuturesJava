# PREREG_HELD_RERANK — thu hồi waste held-symbol (re-rank sau khi bỏ coin đang giữ)

Ngày 2026-10-06 (GMT+7). Chốt TRƯỚC mọi số của vòng này (cổng offline, code, sim). MASTER chốt thiết kế; agent không đổi sau khi thấy số.
Bối cảnh: gate "đều lệnh" rolling ratio đang chạy (K24, ρ≈6,2e-5). Đo 0-sim đã thấy "cap-then-skip": coin ĐANG GIỮ chiếm slot top-K mà KHÔNG sinh lệnh ⇒ 4,5% candidate-flow bị "đốt" (`b0_lock_cells = 1 638 117 / 36 282 547`). Thu hồi ≈ +30 lệnh/năm, KHÔNG nới ρ, KHÔNG hạ chất lượng gate.
Ràng buộc: 0 Java sim trên Oracle (chỉ `mvn -o test` + build), 0 chạm 242/shadow_c3, 0 merge, DEV ≤ 2025-12-31 (2026 niêm phong), Kaggle ≤ 2 kernel song song, df < 500 MB ⇒ dừng.

## 1. Cơ chế (thiết kế CỐ ĐỊNH)
- Key `SELECTOR_HELD_RERANK` (đọc qua `Cfg` trong `Configs`, mặc định **false**).
- Khi true, trong vòng lặp selector top-K: coin đang giữ được bỏ qua **TRƯỚC** `rank++` (không chiếm slot K). Rank chỉ đếm ứng viên "tươi" (không giữ). Khi false: hành vi hiện tại "cap-then-skip" y nguyên.
- Áp cho CẢ sim (`SimulatorMarketLevelTicker1MStopLoss`) lẫn live (`DetectEntrySignal2TradeNormal`) — cùng quy ước, giữ parity live↔backtest.
- Gate KHÔNG đổi: cùng ρ, cùng q_t, cùng threshold, cùng `GateRatioBuffer`. Chỉ số ứng viên tươi được đánh giá tăng lên (marginal = rank K+1, K+2… chịu CÙNG ngưỡng gate).

## 2. Điểm sửa dự kiến (file:line pin lại lúc implementation)
| file | sửa |
|---|---|
| `tradecore/Configs.java` | field `SELECTOR_HELD_RERANK=false`; `Cfg.get("SELECTOR_HELD_RERANK")` → `Boolean.parseBoolean` |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` (vòng rank top-K) | key ON ⇒ bỏ held trước rank++ (đối xứng quy ước "cap-then-skip" hiện tại) |
| `trading/DetectEntrySignal2TradeNormal.java` (vòng rank top-K) | key ON ⇒ bỏ held trước rank++ (chỗ `symbol2Pos.containsKey` hiện đang `continue` SAU rank++) |
| `src/test/.../HeldRerankTest.java` (mới) | ON/OFF: OFF byte-identical; ON đếm rank chỉ ứng viên tươi |

Kiểm: `mvn -o test` 0 fail; jar sha256 ghi vào RESULT; dataset Kaggle riêng.

## 3. Cổng byte-identical OFF (trước khi chạy ON)
- Class diff `target/classes` (build HEAD vs build branch): chỉ được khác các class ở §2 + class test; mọi class khác byte-identical.
- Kaggle P0 = B0@K16 OFF (profile `r4_kg0_k16_f015_g155` + B0OV): parity md5 `printDone` như run chuẩn. FAIL ⇒ DỪNG, không chạy ON.

## 4. Cổng offline TRƯỚC sim
- Đo lại waste held-symbol chính xác trên gate-replay (`chain_n_audit.py` stage `gaterep`): số ô ứng viên top-K bị held chiếm, theo K ∈ {8,16,24,32} ⇒ ước lượng Δn/năm (≈ +4,5% × n hiện tại ≈ +30).
- Xác nhận re-rank KHÔNG đổi tập ngày-mở, chỉ tăng số ứng viên tươi/ngày-mở.

## 5. Sim (Kaggle)
- 8 seed × ON @K24 = profile `r4_kg0_k16_f015_g155` + B0OV + `SELECTOR_RANK_TOPK=24` + `SELECTOR_HELD_RERANK=true`; OFF ghép cặp = run K24 đã có (skipfull OFF: `n700-a1`, `gabl-seed7`, `gsb-*`).
- Thước: CAGR22 / maxDD22 / Calmar22 / maxDD toàn kỳ / n-năm (đóng 2022–2025 / 4). Reuse `selector_ablation_driver` + `arm_metrics`, KHÔNG viết lại.

## 6. Luật GO (CỐ ĐỊNH)
- **C1** mean(Δn/năm, 8 cặp) > 0, kỳ vọng ≈ +30 (4,5%).
- **C2** mean(ΔCAGR22) ≥ −0,5 pp (paired t 8 cặp, df 7).
- **C3** mọi seed ON: |maxDD MTM| ≤ 40% (toàn kỳ và 2022+).
- **C4** mean(Calmar22 ON) ≥ 0,95 × mean(Calmar22 OFF).
- KHÔNG thêm biến thể (không đổi K/ρ/pct). GO chỉ là đề xuất cho MASTER; không merge, không deploy.

## 7. Rủi ro khai trước
- Marginal rank K+1..K+held có selector-score thấp hơn ⇒ chất lượng lệnh thêm có thể thấp hơn trung bình; C2/C4 chặn nếu lệch quá.
- n = 8 seed, hiệu ứng nhỏ (+30 lệnh) ⇒ sức mạnh thống kê thấp; chấp nhận, báo rõ.
