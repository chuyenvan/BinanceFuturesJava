# Reconcile LIVE (242) vs WFO-best canonical — param sweep 2026-08-17

Trả lời câu hỏi Uni: "bộ param WFO tốt nhất là gì, sao live chạy RATE_PROFIT_STOP_MARKET=0.03 mà canonical 0.05, còn gì vênh nữa?"
Nguồn canonical: `wfo_canonical_config_2026-08-15.md` + `strategy_exit_sweep_results_2026-08-16.md`. Live: đọc `/proc/<pid>/environ`
process thật (pid 9246 = BinanceOrderTradingManager) + Configs.java (literal default) + config.properties(242).

## ⚠️ BẪY: config.properties(242) KHÔNG phản ánh param live thật
Nhiều key kinh tế cốt lõi được **hardcode literal trong Configs.java, KHÔNG đọc từ config.properties**:
`RATE_FEE=0.002f (final)`, `RATE_PROFIT_STOP_MARKET=0.03f`, `NUMBER_ENTRY_EACH_SIGNAL=2`, `LEVERAGE_ORDER=1`.
→ config.properties(242) ghi `RATE_PROFIT_STOP_MARKET=0.01`, `RATE_FEE=0.0015`, `NUMBER_ENTRY=4` đều **bị bỏ qua**.
Muốn biết param live thật phải đọc Configs.java default + env override (SIM_*), KHÔNG tin config.properties.

## Bảng đối chiếu (live thật vs canonical WFO-best)
| Param | Canonical WFO-best | Live 242 (thật) | Nguồn live | Trạng thái |
|---|---|---|---|---|
| Grid entry | 15m | 15 (default, LIVE_ENTRY_GRID_MIN không set) | Configs default | ✅ khớp |
| SELECTOR_RANK_TOPK | 5 | **5** | env pid9246 | ✅ khớp |
| Gate threshold (MIN_MOMENTUM_15M) | 0.008 (deploy phiên này) | **0.008** | env SIM_MIN_MOMENTUM_15M | ✅ khớp (gate đang review Track2) |
| **moveSL RATE_PROFIT_STOP_MARKET** | **0.05** | **0.03** | Configs literal, env KHÔNG set | ❌ **VÊNH** |
| RATE_FEE (round-trip) | 0.002 | 0.002 | Configs final literal | ✅ khớp (config.properties 0.0015 bị bỏ qua) |
| NUMBER_ENTRY_EACH_SIGNAL | 2 | 2 | Configs literal | ✅ khớp (config 4 bị bỏ qua, cả 2 phía) |
| LEVERAGE | 1x | 1x | Configs literal | ✅ khớp |
| Exit genome (TS_GIVEBACK 0.5, TS_DYNAMIC_K 0.29774, TS_PROFIT_MULTIPLIER 5.21847, DCA −0.50/−0.75/−0.90 w1,1,3,8, TIME_STOP=0, HARD_SL=0) | default (canonical dùng genome default) | default (KHÔNG env override nào) | env pid9246 sạch | ✅ khớp |
| CAPITAL_START | 35,000 (sim) | 14,000 | — | ~ scale-only, không đổi hành vi/lệnh |

## KẾT LUẬN: chỉ 1 divergence thật — moveSL 0.03 vs 0.05
Mọi param khác khớp canonical. Điểm vênh duy nhất có ý nghĩa chiến lược: **live moveSL = 0.03, canonical = 0.05.**

### Vì sao đáng sửa (khớp đúng triệu chứng "ăn ít")
- moveSL = ngưỡng lãi tối thiểu để bắt đầu dời SL (trailing). Thấp hơn ⇒ trailing SIẾT SỚM ⇒ cắt lãi sớm = **lướt chặt**.
  Live 0.03 nằm ở sườn lướt của đường inverted-U; đỉnh PnL ở 0.05.
- `strategy_exit_sweep_results` (sim thật 2021-2026, slippage 0.3%+funding, genome default): 0.02→+17,171 | **0.05→+19,676 ĐỈNH** |
  0.10→−4,587 sụp. 0.03 nội suy ~+18,4k ⇒ 0.05 hơn 0.03 ~+7% PnL trên sim tương đối (code comment TASK-139 còn nêu 2.4x ở
  bản sweep cũ — KHÔNG dùng con số này, lấy mốc bảo thủ ~+7%).
- Doc exit-sweep từng kết luận "config hiện tại đã ở đỉnh 0.05" nhưng **tưởng nhầm default=0.05**; thực tế default=0.03 ⇒
  kết luận đúng phải là **bump live 0.03→0.05**. Reconcile này sửa lại giả định sai đó.

### Fix đề xuất (CHỜ Uni duyệt — mutate live money-trading)
Thêm env `SIM_RATE_PROFIT_STOP_MARKET=0.05` vào launcher daemon của BinanceOrderTradingManager rồi restart.
- Static block Configs đã áp SIM_* trong live (đã chứng minh qua SIM_MIN_MOMENTUM_15M=0.008 có hiệu lực) ⇒ set env sẽ ăn.
- Rủi ro restart: có thể đang giữ lệnh mở → restart giữa lệnh. Cần chọn thời điểm + xác nhận state lệnh trước.
- KHÔNG tự ý restart live; chờ Uni.

## Provenance cần xác nhận (không phải param, nhưng ảnh hưởng đúng/sai)
- Selector model live `Funding_Classifier_Final.onnx` (788KB, swap hôm nay 08:19) — giả định = canonical G015-net015-K5
  (rank-K=5 env khớp). Nên verify hash/nguồn nếu muốn chắc.
- Gate model `Model_Regressor_Return15M.onnx` (144,774B, 16:27) = fold_20 WFO đã deploy phiên này. ✅
