# PREREG_LATENCY_FILL — ĐỘ TRỄ + GIÁ KHỚP vs NẾN QUYẾT ĐỊNH ⇒ phân biệt (a) lệch mốc / (b) latency / (c) look-ahead

Ngày chốt: **2026-09-29**, viết **TRƯỚC** khi đo bất kỳ số kết quả nào của vòng này. Sau khi thấy số **KHÔNG sửa
thiết kế** (mọi thay đổi ⇒ AMENDMENT có lý do, ghi cuối file, commit trước khi xem số bị ảnh hưởng).

Ràng buộc (cứng): **0 sim** (KHÔNG chạy Java/sim trên Oracle) · **đọc 242 READ-ONLY** (`ssh -p 2222 -i
~/.ssh/id_rsa_chuyennd root@103.157.218.242`), **KHÔNG ghi/sửa/restart/kill**, **KHÔNG đọc key/secret**, file tạm trên
242 cấm (copy về Oracle rồi xử lý) · thuần Python + 1 helper Java deserialize (chạy trên Oracle, không phải sim) ·
**KHÔNG push file dữ liệu** (chỉ code/doc/json kết quả) · **DEV ≤ 2025-12-31** · output tool nhỏ · `nice -n 10`.

Nguồn bối cảnh (đọc trước, KHÔNG tính lại): `RESULT_COST_TRUTH.md` (§4) · `RESULT_LIVE_FILLS_AUDIT.md` ·
`RULERS_CURRENT.md` §13 · `AGENT_RUNBOOK.md` · `PLAN_OPENCLAW_ADDENDUM_20260928.md` §A/§D.

## 0. CÂU HỎI QUYẾT ĐỊNH

`RESULT_COST_TRUTH` đo slip "vào lúc sập" = **+1,675 %/chân** (n=37) so với **close của NẾN CHỨA FILL**, trong khi
sim vào ở **close của NẾN QUYẾT ĐỊNH** (`Simulator…:1372`). Cần phân biệt 3 khả năng loại trừ nhau:

- **(a) lệch mốc đo (không bias)**: +1,675 % chỉ vì so với nhầm nến (fill-candle thay vì decision-candle);
  đo lại vs close nến quyết định thì slip ≈ 0.
- **(b) LATENCY live**: fill khớp MUỘN (một lượt quét ~228 s) giữa cú sập ⇒ chi phí THẬT của live; slip_dec > 0
  và **tăng theo latency**.
- **(c) look-ahead thật của sim**: slip_dec > 0 nhưng **latency ≈ 0** ⇒ sim vào ở close nến quyết định là giá
  "biết sau" không khả thi về thời gian.

**Tiên nghiệm (ghi để không tự lừa, sẽ kiểm bằng số):** (1) `RESULT_COST_TRUTH` KHÔNG có `level` thật (proxy bằng
nền giá của FILL-candle); vòng này có `level` thật từ `OrderTargetInfo.marketLevel`. (2) fill thật khớp tại
**open của nến kế tiếp** (log "Push redis order" ~M+1:00:03–10, fill ~M+1:00:06), tức latency end-to-end từ close
nến quyết định đến fill dự kiến **~7–30 s** (≠ 228 s). (3) +1,675 % phần lớn là hiệu ứng "fill ở open nến đỏ, so với
close nến đỏ" = (a); phần dư nếu có sẽ nhỏ.

## 1. NGUỒN DỮ LIỆU (chốt trước · chỉ ĐO, không sinh mới)

| Thành phần | Nguồn | Loại |
|---|---|---|
| `level` thật + nến quyết định (startTime/priceOpen/priceClose) của từng intent | `storage/data/order/<YYYYMMDD>/<SYM>-<ts>` trên **242** (2850 file, `OrderTargetInfo.marketLevel`), deserialize bằng helper Java → `orders_dump.csv` | ĐO |
| Fill thật (giá/khối lượng/thời gian) | `research/live_fills_audit/data/trades.csv` (991 fill, từ `RESULT_LIVE_FILLS_AUDIT`) | ĐO |
| Vai trò lệnh (mở/đóng) + thời điểm đặt lệnh | `research/live_fills_audit/data/orders.csv` (388 lệnh, `time`/`side`/`reduceOnly`) | ĐO |

**Đơn vị phân tích = LỆNH VÀO (`orderId`, side=BUY, reduceOnly=False)** — mỗi lệnh vào = 1 "chân VÀO", khớp với
đúng 1 intent. Lệnh thị trường quét nhiều mức giá (trung bình ~2,2 fill/lệnh) ⇒ **gom fill theo `orderId`** lấy giá
trung bình trọng số theo qty (KHÔNG đếm mỗi fill là 1 chân — khác `RESULT_COST_TRUTH`).

## 2. KHỚP INTENT ↔ LỆNH (chốt trước · tất định)

Với mỗi lệnh BUY-entry (`orders.csv`): chọn intent `OrderTargetInfo` cùng `symbol` có `startTime` **lớn nhất** thoả
`startTime ≤ order.time` **và** `order.time − startTime ≤ 3600 s` (1 h). Nếu không có intent ⇒ lệnh **UNMATCHED**
(báo n, không bịa). Mỗi intent chỉ dùng cho 1 lệnh (dedupe theo cặp `(symbol, startTime)`).

## 3. ĐẠI LƯỢNG MỖI CHÂN (định nghĩa chốt trước)

| ký hiệu | định nghĩa |
|---|---|
| `t_decision` | = `startTime + 60 s` (thời điểm nến quyết định đóng; sim vào tại close nến này) |
| nến quyết định | nến 1m tại `startTime` (phút sim sẽ dùng), `close = priceClose`, `open = priceOpen` |
| `t_fill` | = `min(time_ms)` của các fill trong lệnh (thời điểm khớp đầu tiên) |
| `fill` | = Σ(price·qty)/Σ(qty) trên các fill của lệnh (giá vào bình quân) |
| `latency (s)` | = `(t_fill − t_decision) / 1000` |
| `slip_dec` | = `(fill − close) / close` (BUY; dương = BẤT LỢI = chi phí) |
| `bar_ret` | = `(close − open) / open` của nến quyết định (độ sập của nến quyết định) |

## 4. PHÂN NHÓM (chốt trước)

- **Theo `level` thật**: `PREDICT_SYMBOL_TRADE` · `BIG_DOWN` · `DCA_LEVEL1` (báo cả nhóm khác nếu có: `SMALL_DOWN_15M`,
  `MEDIUM_DOWN`, `BIG_UP`, `SMALL_UP`).
- **Theo độ sập nến quyết định**: `sập` = `bar_ret ≤ −1 %` · `không sập` = `bar_ret > −1 %` (ngưỡng `−1 %` khớp
  `CRASH_PROXY` của `RESULT_COST_TRUTH`).

**Trục VERDICT chính = độ sập nến quyết định** (2 nhóm). Trục `level` báo cáo mô tả (không dùng cho verdict).

## 5. CI (chốt trước)

Block bootstrap **block-72h · 2000 rep · seed `20260905` · `inflate(k)`**, `k = số nhóm của trục so sánh`:
trục sập k=2 (`inflate(2)=1,1774`); trục level k=3 (`inflate(3)=1,4823`). Báo `mean`/`median` + CI95 (raw + inflate).
Báo riêng `inflate(5)=1,7941` cho nhóm sập (đối chiếu convention `RESULT_COST_TRUTH`). `k` tính trên số nhóm có dữ liệu.

## 6. LUẬT KẾT LUẬN (chốt TRƯỚC, không đổi sau khi thấy số)

Với `slip_dec` nhóm **sập** (nến quyết định ≤ −1 %):

1. **CI chứa 0** ⇒ **(a) lệch mốc đo** (không bias) — dừng, KHÔNG rescore.
2. **Dương NGOÀI CI** và **tăng theo latency** (Spearman/Pearson dương + binned mean đơn điệu tăng) ⇒ **(b) latency**.
3. **Dương NGOÀI CI** nhưng **latency ≈ 0** (median latency nhóm sập ≤ ~10 s và không tăng theo latency) ⇒ **nghi (c)
   look-ahead** — mô tả cơ chế bằng code sim (`Simulator…:1372`), không rescore bằng phạt latency.

Ngưỡng "tăng theo latency": Spearman `ρ(slip_dec, latency)` trong nhóm sập **> 0,3** VÀ binned (theo median latency)
mean slip_dec **đơn điệu tăng**. Nếu n nhóm sập quá nhỏ (< 20) ⇒ CI thoái hoá, chỉ **mô tả** + nêu rõ không kết luận.

## 7. RESCORE HẬU KIỂM (chỉ khi (b) hoặc (c) — chốt trước công thức)

Áp phạt **`P = mean(slip_dec nhóm sập)`** cho leg sim có **nến vào ≤ −1 %** (đọc nến 1m từ ticker offline Oracle
`/home/ubuntu/kaggle_data_hpo/ticker_*.bin.gz`), arm **`p2-r0-base`** và **`p2-r4-base`** (`kaggle_sim/out/`).
Báo **ΔCAGR / ΔCalmar_MTM** và trạng thái **T1–T4** (dùng `reset_rule_score.py`), khai rõ là **xấp xỉ**
(không chạy lại sim, chỉ trừ phạt tuyến tính trên `pnl` của leg sập). Nếu verdict (a) ⇒ KHÔNG rescore.

## 8. HẠN CHẾ (khai trước)

1. `BIG_DOWN` có thể **vắng mặt** trong dữ liệu intent (live đang là `c3_shadow`/LEGACY, 0 entry BIG_DOWN giai đoạn
   20260424–20260912) ⇒ trục level báo cáo theo dữ liệu thực tế, KHÔNG bịa nhóm rỗng.
2. 119/2850 file intent (20260424–20260505) **trước cửa sổ fill** (fill từ 2026-06-24) ⇒ không ảnh hưởng khớp; ~6 lệnh
   UNMATCHED (cửa sổ 1 h, hoặc fill sau 20260912 khi hết file intent) ⇒ báo n, loại khỏi CI.
3. `latency` đo từ `t_fill − (close nến quyết định)` (mốc sim), KHÔNG dùng wall-clock log "Push redis" (bỏ qua ~3–10 s
   hằng số giữa close và push — không đổi kết luận so sánh tương đối).
4. `slip_dec` dùng giá khớp bình quân (weighted), không mô phỏng spread/impact nội phút.
5. Mọi số mô tả quá khứ DEV/live (≤ 2025-12-31 cho sim; live 2026 đã đóng phần trước), không cam kết forward.

## 9. TÁI LẬP (dự kiến)

```bash
# 1) copy intent từ 242 về Oracle (đọc-only), deserialize bằng helper Java:
#    java -cp ".:<jar>:<snappy>" OrderIntentDump <order_root> orders_dump.csv
# 2) phân tích (0 sim):
python3 research/analysis/latency_fill.py --orders orders_dump.csv --json docs/result/latency_fill.json
```
