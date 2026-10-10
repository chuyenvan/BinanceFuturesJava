# HO3b — cổng ADDENDUM-4 (agent HO3b, 2026-10-10)

Pre-reg: ADDENDUM-4 `c321709b` (nguyên văn MASTER), §4a/§4b/§2 `62c0cd67`, §4b-bis `d21485df`, §4c `27fa291b` — tất cả commit TRƯỚC khi đo. Không số Q3 nào được tính/nhìn (Q3 chỉ: dựng ticker, đếm phút/symbol). Số H1 dưới đây là số H1 đã công bố ở HO26. JSON: `docs/result/ho3/{gate4,gate4_diag,mk_build,check_ho3b-mk-*,oi_h1cmp,oi_rebuild_summary,f37_ho26}.json`.

## KẾT LUẬN (rủi ro trước)

**Cổng 3 (OI) FAIL và cổng 4 (market inline, kinh tế) FAIL ⇒ theo luật ngân sách ADDENDUM-4: DỪNG, báo MASTER, không sửa.** B3/B4/B5 KHÔNG làm; 0 kernel holdout Q3.

| kernel (SIM_END_DATE=20260701, stress) | n H1 mới / ho26 | trùng (sym, start ±1′) | ngưỡng | ΣPnL_S mới / ho26 | \|Δ\| | ngưỡng | kết luận |
|---|---|---|---|---|---|---|---|
| k24-s-s42 | 228 / 221 | 173 = **75,9%** | ≥ 95% | 10 772 / 10 675 | **0,9%** | ≤ 5% | FAIL (trùng) |
| b0-s-s42 | 182 / 174 | 142 = **78,0%** | ≥ 95% | 6 363 / 7 446 | **14,5%** | ≤ 5% | FAIL (cả hai) |

Toàn vẹn: 2 kernel đủ check (jar b7c89f09, override, pred md5 `66bcced9…`, TICKER26 181/181, market_ds, FUND_REBUILD_OK, UNSEAL, penalty 0,01675); **phần DEV (start < 2026-01-01) printDone trùng từng dòng với ho26** (k24 3 517, b0 2 492 dòng) ⇒ khác biệt chỉ đến từ input H1. FUND_REBUILD: 0 bản ghi lệch trên phút chung, 24 phút cũ vắng chỉ vì generator bỏ phút, 8 132 phút mới.

Mô tả (không vào cổng, không sửa): trùng theo tháng của lệnh mới — k24: T1 38/38, T2 73/75, T5 3/3, **T6 59/112**; b0: T1 40/40, T2 50/52, T4 3/5, T5 2/2, **T6 47/83** ⇒ lệch dồn ở tháng 6. Thước tham chiếu cùng phép đo giữa ho26 s42 và 7 seed khác CÙNG cấu hình (chỉ khác model p15): k24 trùng 57–67%, |ΔΣPnL| 0–31%; b0 trùng 57–84%, |ΔΣPnL| 11–79% ⇒ nhiễu đường đi của sim lớn hơn nhiều mức 95%/5%; thay md inline gây lệch NHỎ HƠN đổi seed p15, nhưng vẫn không đạt ngưỡng đã chốt.

## Cổng 3 — OI dựng lại từ Vision (feature → mô hình, H1, §4a)

OI ghép = file ghim ts < 2026-01-01 00:00 +07 + dựng lại Vision ts ≥ (769/863 symbol có dữ liệu, 47,27 M dòng, 0 symbol lỗi tải; quy ước NEW 518 091 / NEW_MID 12 828 / OLD 2 388 / OLD_MID 9 file-ngày). JSON `docs/result/ho3/gate3_rebuilt.json` (+ đối chứng `gate3_pinned.json`).

| thành phần | kết quả | ngưỡng | kết luận |
|---|---|---|---|
| net015 p0 (9 478 905 ô, khoá trùng 100%) | spearman **0,99978** | ≥ 0,99 | đạt |
| net015 p0 | ô \|Δ\| ≤ 1e-3: **94,27%** | ≥ 99% | **FAIL** |
| bins (S1 + build_map, 9 478 905 ô, khoá trùng) | ô trùng (4 giá trị ≤ 1e-6): **91,29%** | ≥ 99% | **FAIL** |

⇒ **Cổng 3 FAIL.** Mô tả theo tháng (không vào cổng): net015 ô ≤1e-3 T1–T5 = 99,81–99,91%, **T6 = 68,8%**; bins T1–T5 = 96,6–98,5%, **T6 = 62,0%**. Nguyên nhân chính khớp phép so dữ liệu (`oi_h1cmp.json`): OI dựng lại vs file ghim T1–T5 ls/taker ≥ 99,94%, oi_delta ≥ 99,73%, nhưng **T6 chỉ 52–61%** (file ghim build 08-05 khác Vision hiện tại cả tháng 6); oi_z lệch nhỏ mọi tháng (lịch sử Vision khác lúc build ghim, tương đối ~1e-4). Kể cả T1–T5, bins chỉ ~97–98% vì S1 xếp hạng nhạy với lệch nhỏ của `ls_global`/`rk_oi_delta24h`.

Lỗi thực thi đã sửa TRƯỚC khi có số cổng (phát hiện qua kiểm toàn vẹn G-B4a trên DEV 2025Q4): file OI giờ ghép bị ghi little-endian (np.concatenate đổi byte order) ⇒ G-B4a DEV FAIL 20,4% ⇒ sửa `astype(ODT)`, chạy lại; G-B4a sau sửa 0,038% ô lệch (đúng 7 giờ 2026-01-01 00:00–06:00 +07 nằm trong cửa sổ DEV feat_v2 nhưng sau mép OI dựng lại). Lần chạy lỗi lưu ở `g3r_bug_endian/` (không dùng).

## Cổng 5 — exporter Java gốc trên Kaggle (lát H1 2026-03-01..03-08, §4c)

Hạ tầng CHẠY ĐƯỢC: kernel `ho3b-x-h1slice` (Aerospike CE 7.2.0.6 trong kernel, Ubuntu 24.04; mọi host → 127.0.0.1) nạp 21 600 phút kline (Java `IngestTickerFileToAerospike`), 20 968 phút market, 831 funding + mapper + 698 lifecycle; 3 exporter rc=0 (`ExportGateDataset` 10 081 dòng, Tool1 `FF_UNFILTERED=1` 361 503 / mặc định 261 618 bản ghi, `ExportFundingLabel` 362 338 dòng). JSON `docs/result/ho3/slice_cmp.json`.

| thành phần | kết quả theo thước §4c | ngưỡng | kết luận | mô tả (không vào cổng) |
|---|---|---|---|---|
| gate 33 V3FULL | 10 080/10 080 dòng; ô khớp **93,83%** | ≥ 99,9% | FAIL | lệch CHỈ ở 31 h đầu (03-01 cả ngày + 03-02 tới 07:00: breadth/basket/funding — rổ coin cần lịch sử > 48 h warm-up mặc định của tool); **từ 03-02 07:00: 100%** |
| Tool1 (biến thể `FF_UNFILTERED=1`) | khoá (ts,sym) 360 960 = HO26 **100%** (biến thể mặc định: 17 469 khoá ⇒ loại; provenance = unfiltered); ô trong 0,01·IQR **99,23%** | ≥ 99,9% | FAIL | lệch chỉ 03-01 (98,5% dòng) + 03-02 (26%); **từ 03-03: 100% ô** |
| nhãn `nBars_72h` | khoá HO26 tìm thấy 362 338/362 878; trùng **57,1%** | ≥ 99,9% | FAIL | 03-01..03-04: **100%**; từ 03-05 = 0–29% vì tool không nhìn quá ngày `end` (20260308) ⇒ thiếu 72 h nhìn trước |

Đọc: cả 3 FAIL đều do CẤU HÌNH LÁT của tôi (warm-up 48 h mặc định quá ngắn cho rổ coin; nhãn cần `end` ≥ lát + 72 h), không phải do nguồn/exporter: sau warm-up và trong vùng đủ nhìn trước, exporter Java trên Kaggle tái hiện HO26 **100%**. Theo ADDENDUM-4 vẫn ghi FAIL; chạy lại với lead-in ≥ 7 ngày và `end` ≥ lát + 4 ngày (ngưỡng giữ nguyên) chỉ làm khi MASTER cho tiếp (đang DỪNG do cổng 4).

## Kiểm bổ sung §4b-bis — Tool1 dùng md inline (mô tả, KHÔNG đổi PASS/FAIL cổng 4)

Tool1 cột #6 (index 5) = `rateDown15MAvg` (cột `rateDownAvg` không nằm trong 40 feature). Thay bằng md inline Kernel A trên H1 (md có tại 9 478 905/9 478 905 ô), ONNX predict, so theo thước cổng 3: spearman **0,99864**; ô \|Δp0\| ≤ 1e-3 **96,79%**; bins ô trùng **96,76%** (đều theo tháng 96,0–97,4%). ⇒ Theo thước cổng 3 (≥ 99%) md inline đi qua Tool1 cũng KHÔNG đạt; khác biệt đều trên mọi tháng (không dồn T6). JSON `docs/result/ho3/t1md.json`.

## Tổng hợp cho MASTER

| Cổng | Kết quả | Ghi chú |
|---|---|---|
| 1 kline 242 | dùng (MASTER đã chốt) | ticker Q3 tháng 7–8 đã dựng (bộ ghi byte-exact), tháng 9 dừng |
| 2 funding Vision | dùng; 37 symbol thiếu có **24 lệnh H1** ở 18/48 run ho26 | pickle funding Q3 sẵn |
| 3 OI Vision | **FAIL** (p0 ≤1e-3 94,27%; bins 91,29%) | đối chứng file ghim tái hiện HO26 100% byte ⇒ lệch do dữ liệu (T6 ghim ≠ Vision) |
| 4 market inline | **FAIL** (trùng lệnh 75,9/78,0%; \|ΔΣPnL_S\| 0,9/14,5%) | nhiễu seed p15 cùng thước: trùng 57–84%, \|ΔΣPnL\| 0–79% |
| 4b-bis Tool1 md | không đạt thước cổng 3 (96,8%) | ngoài phạm vi cổng 4 |
| 5 exporter Kaggle | FAIL theo thước lát (93,8 / 99,2 / 57,1%) | do warm-up/nhìn trước của lát; sau warm-up 100% |

Theo luật ngân sách ADDENDUM-4: cổng 3 và 4 FAIL ⇒ DỪNG, không sửa, không B3/B4/B5. Câu hỏi cho MASTER (không tự quyết): (a) thước kinh tế 95%/5% chặt hơn nhiễu seed p15 của chính sim — giữ hay đổi sang thước so với dải seed; (b) OI: chấp nhận Vision (khác ghim chủ yếu T6) hay tìm nguồn OI live 242 (`open_interest` sets) cho Q3; (c) có cho chạy lại lát cổng 5 với warm-up ≥ 7 ngày và `end` ≥ lát + 4 ngày.
