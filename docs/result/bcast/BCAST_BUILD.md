# BCAST_BUILD — dựng kho backcast 2020 (B1–B3), agent BCAST, 2026-10-12

Pre-reg **`596c1ef8`** (`docs/prereg/PREREG_BACKCAST_RESERVOIR.md`, hiệu lực trước mọi kernel). B0 `a8ce5302`. JSON `docs/result/bcast/BCAST_BUILD.json`. Script `research/analysis/bcast_*.py`. Không PnL, không mở printDone/equity.

## Kết luận (rủi ro trước)
- **B1 PASS, P3-DET PASS** (exporter 387/387 file md5 trùng; chuỗi 19/19), **sim kỹ thuật PASS** (`bcast-tech`, exit hợp lệ, 548 lệnh, printDone niêm phong md5 `2b7ded8f4dd023b0267212ab65d16e83`). Dataset private `chuyendinh/bcast-2020-2021h1-p1` (406 file, 699 MB, md5 == MANIFEST kernel 100 %).
- Rủi ro: (1) **OI NaN 100 %** — file ghim `e3887f63` không có hàng nào trước 2021-01-01 UTC (kể cả BTC 2020-09+), nên 5 cột OI net015 và `ls_global`/`rk_oi_delta24h` S1 rỗng toàn kho (đã khai §3b). (2) Universe nhỏ: bins 23 symbol (2020-05) → 78 (2020-12); BTCUSDT/ETHUSDT có trong ticker/market/gate nhưng exporter Tool1 không xuất ⇒ không có trong net015/bins (không giao dịch qua nhánh PREDICT; chưa đối chiếu với DEV). (3) Lần đẩy `bcast-tech` thứ nhất ERROR trước khi Java chạy (`FUND_HO4_FAIL selfcheck`, n_old=0): khối tự kiểm `ho4p1_fund_block` chỉ thu bản ghi DEV ở đoạn prefix (ts < lo), với lo = 2020 thì đoạn DEV nằm ở vòng giữa. Sửa harness (thu `_rs` cả vòng giữa; logic + ngưỡng tự kiểm giữ nguyên) rồi đẩy lại 1 lần; không có printDone ở lần 1. (4) Chuỗi `bcast-ch20-b` chạy 68′ trên Kaggle (a: 5′) — chậm hạ tầng, output trùng md5.

## B1 — manifest (Vision `futures/um`, công cụ gốc HO4-P1)
| Thành phần | Kernel | Kiểm |
|---|---|---|
| ticker 1′ | `bcast-x20-a` (25′; exporter jar `99c5f040`) | 369 ngày UTC 20200101..20210103, **mọi ngày 1 440 phút**, 3..80 symbol/ngày; md5 raw = `ticker_raw_md5.json` |
| universe/tháng | — | 11, 24, 24, 24, 25, 30, 36, 42, 61, 70, 77, 80 (2020-01..12); 86 (2021-01) |
| market.bin | `bcast-ch20-a` | 526 620 phút [2020-01-01 +07, 2021-01-01 +07) (= 527 040 − 420 phút đầu không có dữ liệu Vision), NaN 0, ts tăng, md5 `232ee1e5…` |
| store gate 33 V3FULL | exporter `gate` (710 s) | 526 620 dòng, **NaN 0** (cả warm-up) |
| pred.bin 8 seed | chuỗi | 526 620 dòng/seed, NaN 0, ts tăng; s42 `9bdb720f…`, s7 `080d3d2b…`, s13 `591368e2…`, s21 `5a743867…`, s99 `2b9bc7db…`, s123 `ee4a787f…`, s777 `0f50847e…`, s2024 `5dd6d792…` |
| net015 4 fold | chuỗi (ONNX `7921ceaf`) | 128 525 / 192 637 / 340 459 / 617 512 dòng, NaN 0; OI NaN mọi dòng |
| feat_v2 KEEP9 | chuỗi | 347 163 dòng (CLOSES_1H 402 153 bản ghi, 86 symbol) |
| pool + S1 (`af706dc6`) | chuỗi | pool 102 854 / 2 545 tick, feat_cov 0,974, NaN score 0; 0 symbol ngoài map 781 |
| bins 4 fold | chuỗi | `968aa154…` / `00836856…` / `d3b23cb3…` / `4d4578fa…`; NaN p0 0, ts không giảm; symbol/tháng 9..78 |
| funding.bin (trong kernel sim) | `bcast-tech` | 526 620 bản ghi trên lưới market kho, prefix/suffix bundle 0, md5 `669d2206…`; tự kiểm DEV 257 433/257 433 trùng byte |
| Symbol loại | — | LENDUSDT, BTCSTUSDT (ngoài mapper 863); thiếu funding Vision: 0; đuôi settle: 0; id mapper trùng 843–850: không có symbol 2020 |

## B2 — kiểm (không PnL)
- **P3-DET exporter** `bcast-x20-a` vs `-b`: **387/387** md5 trùng (ticker 369, market dump, gate, Tool1 5, nhãn 5, CLOSES_1H, funding, lifecycle, universe).
- **P3-DET chuỗi** `bcast-ch20-a` (trên x-a) vs `-b` (trên x-b): **19/19** md5 trùng (pred×8, market, net015×4, bins×4, S1, feat_v2).
- **Sim kỹ thuật `bcast-tech`** (B0, s42, phí gốc, jar `b7c89f09`, TIME_RUN=20200101, SIM_END_DATE=20210101): java_rc 1 (quy ước template: hợp lệ khi có done + printDone), ok=True, mapper 863, TICKER_BCAST 369/369, FUND_HO4_OK, pred md5 đúng, date_first 20200101, date_last 20201231, **n = 548 lệnh (549 dòng), md5 printDone `2b7ded8f4dd023b0267212ab65d16e83`**, 132 s. Output ở `~/kaggle_sim/sealed/bcast-tech` (chmod 700). Chưa ai đọc printDone/equity.

## B3 — dataset + hướng dẫn
- `chuyendinh/bcast-2020-2021h1-p1` (private): phẳng; Kaggle tự giải nén `.gz` ⇒ kiểm ticker bằng `ticker_raw_md5.json`, gate/Tool1 bằng `raw_md5_nonticker` trong JSON. `MANIFEST_bcast.json` = md5 + đường dẫn gốc trong kernel.
- Hướng dẫn mở kho: `docs/plan/BACKCAST_RESERVOIR.md`.
- Cache Oracle đã xoá sau khi ghi md5 (`BCAST_BUILD.json` → dataset.manifest); còn lại JSON nhỏ + thư mục niêm phong.
