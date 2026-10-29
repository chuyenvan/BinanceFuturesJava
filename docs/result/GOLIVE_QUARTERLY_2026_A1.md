# GOLIVE_QUARTERLY 2026 — phát hành lại theo A1 (bỏ TradFi + INDEX) — 2026-10-29

**Vì sao có bản này:** prereg `docs/prereg/PREREG_HO2026_NOTF.md:69` — *"nếu |ΔROI_W9| > 1,0 pp ⇒ phát hành lại
GOLIVE_QUARTERLY 2026 và ECMEAS H theo A1"*. `docs/result/HO2026_NOTF.md` (4f5e109e) đo **D3 = VẬT CHẤT**
(ΔROI_W9 = +3,28 pp k24-s, +3,33 pp x14) ⇒ bản này thay **số 2026** của `GOLIVE_QUARTERLY.md` (giữ nguyên file cũ).
Bản A1 **không** đổi luật/tham số nào; chỉ đổi universe (A1 = A0 − TradFi − INDEX, hiệu lực từ 2026).

**Phạm vi phát hành lại: CHỈ 2026 (Q1/Q2/Q3 + W9).** DEV 2021H2–2025 **giữ nguyên** vì A1 chỉ đổi universe trong cửa sổ
UNSEAL 2026; đoạn ≤2025-12-31 của 24 kernel A1 **trùng từng dòng** với A0 (HO2026_NOTF §3 V3, §5 V5; A0'(b) md5
`6989a312/7cc8864c/bb609455`). Vì vậy bảng DEV trong `GOLIVE_QUARTERLY.md` **không** bị thay.

## 0. Cách làm (ĐÚNG pipeline gốc, không chạy kernel mới)

- Code: `research/golive_quarterly/quarterly.py` — dùng nguyên `load()/clusters()/deferred()/build()/metrics()`;
  quy ước y nguyên bản gốc (quý theo **giờ +07**, `ph0 = 2026-01-01`, ROI = ΣPnL thực hiện / số dư thực hiện đầu quý,
  maxDD phút, DD lũy kế từ đầu 2026, Calmar = CAGR quy năm / |maxDD quý|).
- MTM: đúng đường `mtm_ho.py` (hàm `ecm_mtm_h` → `ho4_score_a`: giá close 1m Vision, cache `ecm_px`, **offline**;
  `fetch ok=0, fail=0, miss=0, nofile=0`, 220 symbol/615 file/274 ngày).
- Nguồn lệnh: `~/kaggle_sim/out/nt-x14-s{42,7,13,21,99,123,777,2024}/storage/printDone.csv` (A1, 8 seed).
  P0 (mốc defer-cluster theo quy ước cũ) = `nt-k24-b-s*` cùng seed. Cờ X14 lấy từ `result.json` của chính run A1:
  `SIM_LOSER_TS_EXT_DAYS = 20260205-20260214,20260216-20260217,20260224-20260225,20260606-20260607,20260610-20260611`
  = **18 ngày / 5 khoảng** (A0: 15 ngày / 4 khoảng, `tsx/ho/ho_flags.json`).
- Script: `research/golive_quarterly/a1_release.py`; số: `docs/result/golive_quarterly_a1/`
  (`quarterly_a1_by_seed.csv`, `summary_a1.json`, `ecm_h_a1.json`).
- **Kiểm:** (i) MTM chạy lại khớp `ho_tradfi_wk/notf_mtm.json` với `max|Δ| < 1e-6` cho `n/sum_pnl/roi/maxdd` cả 4 cửa sổ × 8 seed;
  (ii) `eqcheck.final_ok=True`, `upd_vs_result=true` 8/8; (iii) kiểm trục: `flat_maxabs = 0.0` mọi seed (equity = số dư khi
  phẳng), trục sai (không trừ 7 h) lệch 4,7–5,9k USD; (iv) `n_defer` 13–14 cụm/seed khớp cửa sổ `[TSX]` 18 ngày.

## A. Hiệu quả theo quý — gốc (A0) vs A1, median 8 seed [min … max]

| Quý | ROI % A0 | ROI % A1 | CAGR quý năm % A0 → A1 | maxDD quý % A0 → A1 | DD lũy kế % A0 → A1 | Calmar A0 → A1 |
|---|---|---|---|---|---|---|
| 2026Q1 | 6,53 | **6,71** [4,97 … 8,13] | 28,78 → 29,66 | −5,62 → **−5,68** [−6,33 … −5,20] | −5,62 → −5,68 | 5,34 → 5,22 |
| 2026Q2 | 6,86 | **11,62** [9,16 … 13,23] | 30,38 → 55,26 | −3,24 → **−3,12** [−3,39 … −3,01] | −5,62 → −5,68 | 9,75 → 17,16 |
| 2026Q3 | −1,22 | **−2,41** [−3,86 … −1,63] | −4,78 → −9,28 | −3,79 → **−3,91** [−5,26 … −3,68] | −5,62 → −5,68 | −1,21 → −2,40 |
| **HO 2026 W9** | **12,68** | **15,11** [13,89 … 18,74] | 17,32 → **20,72** | −5,62 → **−5,68** [−6,33 … −5,36] | −5,62 → −5,68 | 3,24 → **3,49** |

ΣPnL (USD, median [min … max]): Q1 9 536 → **9 597** [7 509 … 11 451]; Q2 10 858 → **18 340** [13 942 … 20 028];
Q3 −2 000 → **−4 142** [−7 021 … −2 757]; W9 18 106 → **22 565** [20 296 … 26 201].
ret MTM: Q1 6,53→6,71 · Q2 5,31→10,07 · Q3 0,27→**−1,00** · W9 12,68→15,11.

## B. Lệnh / cụm / leg / win — A0 vs A1

| Quý | Đợt vào | Cụm | Leg | Win % cụm | PnL/cụm USD |
|---|---|---|---|---|---|
| 2026Q1 | 23,5 → **23,0** [21 … 27] | 131 → **133,5** [112 … 138] | 132 → **134,5** [112 … 140] | 88,7 → **89,6** [86,9 … 92,0] | 71,2 → **74,4** [61,6 … 83,0] |
| 2026Q2 | 31,0 → **35,0** [28 … 46] | 146 → **167,5** [146 … 203] | 148 → **170,0** [148 … 208] | 86,1 → **92,4** [90,7 … 93,8] | 71,9 → **101,7** [90,5 … 117,0] |
| 2026Q3 | 32,0 → **28,5** [26 … 35] | 157,5 → **148,0** [138 … 159] | 163 → **154,0** [144 … 167] | 79,9 → **78,1** [75,5 … 81,1] | −12,9 → **−26,1** [−49,1 … −18,0] |
| HO W9 | 87,5 → **85,0** [77 … 108] | 441 → **451,5** [396 … 496] | 452,5 → **463,0** [404 … 509] | 84,1 → **86,9** [85,4 … 87,6] | 41,2 → **51,2** [45,6 … 54,4] |

## C. Phơi nhiễm / thoát / chi phí — A0 vs A1

| Quý | Phơi nhiễm TB % / max % / cụm đồng thời max | Giữ median h | Trailing / Time-stop 168h / X14 / Khác | Phí USD | Funding USD | Ngày không vị thế / không vào lệnh / ngày cờ |
|---|---|---|---|---|---|---|
| 2026Q1 | 3,47/47,6/42 → **3,20/48,1/42,5** | 8,88 → **7,39** | 113/4/9/4 → **116/4/9/4** | 273 → **284** | −370 → **−346** | 63/84/14 → **63,5/84/14** |
| 2026Q2 | 3,16/43,3/41 → **2,79/41,6/38** | 7,70 → **6,33** | 126/15,5/5/0 → **156/7,5/4/0** | 310 → **390** | −733 → **−826** | 67/80/1 → **67/80/4** |
| 2026Q3 | 4,86/39,3/28 → **4,94/39,3/27** | 9,10 → **10,90** | 128/33,5/0/0 → **117/33,5/0/0** | 433 → **434** | −693 → **−721** | 42/79/0 → **45/81/0** |
| HO W9 | 4,03/47,6/42 → **3,79/48,1/42,5** | 8,64 → **7,22** | 370/53/14/4 → **385,5/46,5/13/4** | 1 087 → **1 106** | −1 786 → **−1 913** | 168/243/15 → **175,5/244,5/18** |

## D. Đọc số (mô tả, không tune)

1. **Toàn bộ ΔROI W9 (+2,43 pp median; +3,33 pp mean theo HO2026_NOTF) đến từ Q2** (6,86 → 11,62): Q2 có thêm 4 đợt vào,
   +21,5 cụm, win 86,1 → 92,4 %, PnL/cụm 71,9 → 101,7 USD. Q1 gần như không đổi (+0,18 pp).
2. **Q3 xấu thêm −1,19 pp** (median): ít đợt vào hơn (32 → 28,5), PnL/cụm −12,9 → −26,1. Vẫn **0/8 seed dương** (NOTF D4).
3. **Rủi ro không xấu đi đáng kể:** maxDD W9 −5,62 → −5,68 % (sâu thêm 0,06 pp; xấu nhất seed −6,33 % so −6,67 % của A0 — **nông hơn**
   ở đuôi xấu), Calmar W9 3,24 → 3,49. DD quý sâu nhất vẫn là Q1.
4. **Chi phí tăng nhẹ:** phí W9 1 087 → 1 106 USD (+1,8 %), funding −1 786 → −1 913 USD (−7 %), do nhiều cụm hơn
   (451,5 vs 441) và giữ ngắn hơn (7,22 h vs 8,64 h).
5. **Cờ X14 tăng 15 → 18 ngày** (thêm 2026-06-06/07 và 06-10) — do universe đổi, không phải đổi luật. Số cụm X14 được
   hoãn 14 → 13 (W9).
6. **CHƯA GIẢI THÍCH cơ chế** (giữ nguyên kết luận HO2026_NOTF §6): chưa tách được phần "slot TF giải phóng" vs "market/gate/
   ALT_EW đổi"; không có ablation trong prereg. Q3 xấu thêm cũng chưa giải thích chi tiết.
7. Bảng này **không** dùng để nâng hạng/nới luật; Q3 vẫn FAIL như bản gốc.

## E. Artefact & giới hạn

- Không chạy kernel Kaggle mới, không gọi Binance REST/API, không tải dữ liệu; chỉ đọc artefact đã có
  (`nt-*` printDone/result.json + cache `ecm_px`).
- File cũ `docs/result/GOLIVE_QUARTERLY.md` và `docs/result/golive_quarterly/*` **giữ nguyên** (bản A0).
- Dung lượng tạo: ~60 KB (CSV/JSON) + 2 file .md. Không có file trung gian còn lại (`golive_quarterly_a1_wk/run.log` giữ làm log chạy).
