# PREREG_EXEC_PROBE — chi phí thực thi đo trên shadow so với giả định của sim

Ngày 2026-10-21, viết **trước khi có bất kỳ dòng `[EXEC-PROBE]` thật nào** (probe chưa deploy). Sau commit này không đổi định nghĩa,
ngưỡng, N hay script chấm. Script chấm: `research/exec_probe/xp_score.py` (cùng commit). Code probe: nhánh `v1.1/exec-probe`
(`com.binance.chuyennd.ops.ExecProbe*`), cờ `LIVE_EXEC_PROBE=1`, thiết kế `docs/plan/GOLIVE_GAP_C3LIVE.md` §4.

## 1. Mục đích và phạm vi dùng kết quả

- Câu hỏi: với độ trễ thật của 242 (sim khớp ở close nến quyết định M, live gửi lệnh sau ~6–10 s) và sổ lệnh thật lúc đó, mỗi leg
  C3 (vào/DCA) và mỗi lần thoát của sổ giấy **tốn bao nhiêu so với giá sim dùng**, và có vượt giả định chi phí của sim không.
- Kết quả **CHỈ** dùng cho: size pilot (10 000 USDT như kế hoạch / giảm / hoãn) và ưu tiên adapter (G2 kiểu thoát).
- **CẤM** dùng để tune chiến lược: không đổi gate/selector/ngưỡng/arm/trailing/time-stop, không thêm bộ lọc coin theo trượt đo được,
  không chọn tham số sim bằng chi phí đo được. Một ý tưởng như vậy ⇒ pre-reg mới trên dữ liệu khác.
- Probe chỉ log, không đổi quyết định (bằng chứng: §6).

## 2. Dữ liệu

- Nguồn: dòng `[EXEC-PROBE] 1,...` trong log app 242 từ lúc deploy probe (owner trích `grep -a '\[EXEC-PROBE\]'`; agent không đọc 242).
- Header cố định (38 cột, `ExecProbe.HEADER`). Giá sim: leg vào/DCA = `priceClose` nến M (= `order.priceEntry`, giá sổ giấy ghi);
  thoát trailing = SL (giá ledger); time-stop = `price_realtime` của nhịp.
- Tập E = `ev ∈ {ENTRY, DCA}`, `status ∈ {ok, short}`, `src = ws`. Tập X = `ev = EXIT` cùng lọc.
- Cột chính cho E: `slip_x025` nếu `PAPER_EQUITY` 242 ≥ 20 000 (qty ×0,25 ≈ pilot 10k so với sổ giấy 35k), ngược lại `slip_bps`.
- Giả định sim (bps, dương = bất lợi), theo bucket `bar_ret` nến M (`EntryCost.bucketOf`):
  ECMEAS "thực" (CI_trên P0, `docs/result/EXEC_RESULT.md` §6a) NC 7 · C1 18 · C2 19 · C4 32; stress (P0max) 23 · 33 · 41 · 101.
  Chân ra: `SIM_SLIPPAGE_RATE` 0,67 bps; trailing sim khớp đúng SL. Phí taker không tính (như nhau sim/live).

## 3. Khi nào chấm

- Chấm MỘT lần khi |E| ≥ **100** (X báo cáo nếu ≥ 30, dưới đó chỉ mô tả). Không nhìn kết quả trung gian để quyết định dừng sớm
  (được xem số dòng và tỉ lệ status cho vận hành).
- Hạn cứng 30 ngày sau deploy: chưa đủ 100 ⇒ chỉ mô tả, **không verdict**, quyết định pilot theo luật cũ.

## 4. Kiểm hợp lệ (tất cả đạt mới có verdict)

| mã | điều kiện |
|---|---|
| V1 | phủ: (ok+short)/mọi dòng E ≥ 90 % (no_book/rate_capped/empty_book là lỗi đo) |
| V2 | trung vị `lat_snap_ms` ≤ 3 000 |
| V3 | trung vị \|`ex_lag_ms`\| ≤ 2 000 (đồng hồ / trễ stream) |
| V4 | 0 dòng `src=mock` |
| V5 | nếu owner cung cấp số leg sổ giấy (`legs.csv`/log `[SHADOW] open|add-leg`) cùng cửa sổ: số dòng E lệch ≤ 5 % |

## 5. Chỉ số và ngưỡng cảnh báo (cố định)

- excess_i = slip_i − giả định ECMEAS "thực" theo bucket của leg. Báo median/mean/p90/p99, CI95 của median bằng bootstrap theo cụm
  (cụm = `t_bar_close`), B = 2 000, seed 20261021. Kèm phân rã drift (mid vs giá sim) / impact (VWAP vs mid), theo bucket, `lat_dec_ms`.

| mã | điều kiện | ý nghĩa |
|---|---|---|
| W1 | median(excess) > 0 VÀ CI95 dưới > 0 | sim lạc quan về chi phí vào |
| W2 | p90(slip) > 170 bps | đuôi vượt luật pilot 1,7 % |
| W3 | > 2 % leg có slip > 250 bps | C2 kill-switch sẽ kích hoạt thường xuyên |
| W4 | X trailing ≥ 30 và (median slip > 10 bps hoặc p90 > 170 bps) | chân ra lệch sim (SL sim khớp đúng giá) |
| W5 | > 10 % leg `short` (depth 20 mức không đủ notional) | sổ mỏng so với size |
| W6 | W1 và median(excess) > 25 bps | sim lạc quan đáng kể |

Verdict: **RED_SIZE** nếu W2 ∨ W3 ∨ W5 ∨ W6 ⇒ đề xuất pilot giảm một nửa (5 000) hoặc hoãn, owner quyết; **AMBER** nếu W1 ∨ W4
(không RED) ⇒ pilot 10 000 như kế hoạch, kèm số stress hậu kiểm (ΣPnL sim − chi phí đo, chỉ thông tin) và ưu tiên G2 nếu W4;
**GREEN** nếu không có W nào ⇒ pilot 10 000. Không verdict ⇒ luật cũ.

## 6. Bằng chứng probe không đổi quyết định (trước deploy)

Theo ADDENDUM d (`PREREG_SHADOW2_PROMOTION.md`, nhánh research/vz-e1): (1) bytecode: chỉ THÊM lệnh ở 2 method
(`createOrderBuyRequest`, `ShadowBookC3.tick`), mọi method khác IDENTICAL; (2) unit test `ExecProbeShadowEquivTest` (cùng kịch bản
sổ giấy, probe tắt/bật ⇒ trace quyết định trùng khớp); (3) harness OFFLINE `ops/verify/harness_xp.sh` (HARNESS_OFFLINE=1, websocket
mock): out/fund byte-identical với eea5adec ở mọi lượt, ledger/state sổ giấy lượt probe bật == tắt. Kết quả ghi ở báo cáo commit.

## 7. Giới hạn

1. Ảnh chụp sổ ≠ khớp thật: không có hàng đợi, không có tác động của chính lệnh ta lên sổ, sổ có thể hồi trong lúc chụp.
2. Thời điểm chụp = `t_dec` + kết nối websocket (~0,3–1 s): gần lúc live gửi lệnh nhưng không trùng.
3. Depth 20 mức có thể không đủ cho chân lớn (cột `fill_frac`, phần thiếu tính ở mức xấu nhất ⇒ bảo thủ).
4. Quyết định là của sổ GIẤY c3_shadow (size theo equity giấy); pilot dùng cột ×0,25 như xấp xỉ tuyến tính.
5. Thoát trailing của sổ giấy xét mỗi 10 s trên `price_realtime` (Aerospike), live trên sàn sẽ khác (G2).
