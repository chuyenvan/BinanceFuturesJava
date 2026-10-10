# HO3b — cổng ADDENDUM-4 (agent HO3b, 2026-10-10)

Pre-reg: ADDENDUM-4 `c321709b` (nguyên văn MASTER), §4a/§4b/§2 `62c0cd67`, §4b-bis `d21485df`, §4c `27fa291b` — tất cả commit TRƯỚC khi đo. Không số Q3 nào được tính/nhìn (Q3 chỉ: dựng ticker, đếm phút/symbol). Số H1 dưới đây là số H1 đã công bố ở HO26. JSON: `docs/result/ho3/{gate4,gate4_diag,mk_build,check_ho3b-mk-*,oi_h1cmp,oi_rebuild_summary,f37_ho26}.json`.

## KẾT LUẬN (rủi ro trước)

**Cổng 4 (market inline, kinh tế) FAIL ⇒ theo luật ngân sách ADDENDUM-4: DỪNG, báo MASTER, không sửa.** B3/B4/B5 KHÔNG làm; 0 kernel holdout Q3.

| kernel (SIM_END_DATE=20260701, stress) | n H1 mới / ho26 | trùng (sym, start ±1′) | ngưỡng | ΣPnL_S mới / ho26 | \|Δ\| | ngưỡng | kết luận |
|---|---|---|---|---|---|---|---|
| k24-s-s42 | 228 / 221 | 173 = **75,9%** | ≥ 95% | 10 772 / 10 675 | **0,9%** | ≤ 5% | FAIL (trùng) |
| b0-s-s42 | 182 / 174 | 142 = **78,0%** | ≥ 95% | 6 363 / 7 446 | **14,5%** | ≤ 5% | FAIL (cả hai) |

Toàn vẹn: 2 kernel đủ check (jar b7c89f09, override, pred md5 `66bcced9…`, TICKER26 181/181, market_ds, FUND_REBUILD_OK, UNSEAL, penalty 0,01675); **phần DEV (start < 2026-01-01) printDone trùng từng dòng với ho26** (k24 3 517, b0 2 492 dòng) ⇒ khác biệt chỉ đến từ input H1. FUND_REBUILD: 0 bản ghi lệch trên phút chung, 24 phút cũ vắng chỉ vì generator bỏ phút, 8 132 phút mới.

Mô tả (không vào cổng, không sửa): trùng theo tháng của lệnh mới — k24: T1 38/38, T2 73/75, T5 3/3, **T6 59/112**; b0: T1 40/40, T2 50/52, T4 3/5, T5 2/2, **T6 47/83** ⇒ lệch dồn ở tháng 6. Thước tham chiếu cùng phép đo giữa ho26 s42 và 7 seed khác CÙNG cấu hình (chỉ khác model p15): k24 trùng 57–67%, |ΔΣPnL| 0–31%; b0 trùng 57–84%, |ΔΣPnL| 11–79% ⇒ nhiễu đường đi của sim lớn hơn nhiều mức 95%/5%; thay md inline gây lệch NHỎ HƠN đổi seed p15, nhưng vẫn không đạt ngưỡng đã chốt.

## Cổng 5 — exporter Java gốc trên Kaggle (lát H1 2026-03-01..03-08, §4c)

Hạ tầng CHẠY ĐƯỢC: kernel `ho3b-x-h1slice` (Aerospike CE 7.2.0.6 trong kernel, Ubuntu 24.04; mọi host → 127.0.0.1) nạp 21 600 phút kline (Java `IngestTickerFileToAerospike`), 20 968 phút market, 831 funding + mapper + 698 lifecycle; 3 exporter rc=0 (`ExportGateDataset` 10 081 dòng, Tool1 `FF_UNFILTERED=1` 361 503 / mặc định 261 618 bản ghi, `ExportFundingLabel` 362 338 dòng). JSON `docs/result/ho3/slice_cmp.json`.

| thành phần | kết quả theo thước §4c | ngưỡng | kết luận | mô tả (không vào cổng) |
|---|---|---|---|---|
| gate 33 V3FULL | 10 080/10 080 dòng; ô khớp **93,83%** | ≥ 99,9% | FAIL | lệch CHỈ ở 31 h đầu (03-01 cả ngày + 03-02 tới 07:00: breadth/basket/funding — rổ coin cần lịch sử > 48 h warm-up mặc định của tool); **từ 03-02 07:00: 100%** |
| Tool1 (biến thể `FF_UNFILTERED=1`) | khoá (ts,sym) 360 960 = HO26 **100%** (biến thể mặc định: 17 469 khoá ⇒ loại; provenance = unfiltered); ô trong 0,01·IQR **99,23%** | ≥ 99,9% | FAIL | lệch chỉ 03-01 (98,5% dòng) + 03-02 (26%); **từ 03-03: 100% ô** |
| nhãn `nBars_72h` | khoá HO26 tìm thấy 362 338/362 878; trùng **57,1%** | ≥ 99,9% | FAIL | 03-01..03-04: **100%**; từ 03-05 = 0–29% vì tool không nhìn quá ngày `end` (20260308) ⇒ thiếu 72 h nhìn trước |

Đọc: cả 3 FAIL đều do CẤU HÌNH LÁT của tôi (warm-up 48 h mặc định quá ngắn cho rổ coin; nhãn cần `end` ≥ lát + 72 h), không phải do nguồn/exporter: sau warm-up và trong vùng đủ nhìn trước, exporter Java trên Kaggle tái hiện HO26 **100%**. Theo ADDENDUM-4 vẫn ghi FAIL; chạy lại với lead-in ≥ 7 ngày và `end` ≥ lát + 4 ngày (ngưỡng giữ nguyên) chỉ làm khi MASTER cho tiếp (đang DỪNG do cổng 4).
