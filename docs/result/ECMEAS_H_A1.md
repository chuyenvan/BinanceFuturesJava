# ECMEAS (H) — phát hành lại 2026 theo A1 (bỏ TradFi + INDEX) — 2026-10-29

**Vì sao có bản này:** cùng lý do `GOLIVE_QUARTERLY_2026_A1.md` — prereg `docs/prereg/PREREG_HO2026_NOTF.md:69` yêu cầu
phát hành lại **ECMEAS H** khi D3 = VẬT CHẤT (đã đo: `docs/result/HO2026_NOTF.md` §4, ΔROI_W9 x14 **+3,33 pp**).

**ECMEAS (H)** ở đây = bộ chỉ số HO 2026 của scorer `ecm_mtm_h` (`research/analysis/ecm_mtm_h.py` → `ho4_score_a.py`):
equity MTM **phút**, giá close 1m Binance Vision, cửa sổ theo giờ +07 `W9` (01-01→10-01), `Q1`, `Q2`, `Q3`,
`H1` (01-01→07-01, định nghĩa của `HO4_RESULT_A.json`); `ROI = ΣPnL / equity MTM đầu cửa sổ`; `maxDD` phút trong cửa sổ.
**Không** đổi luật/ngưỡng; chỉ đổi universe (A1 = A0 − TradFi − INDEX, hiệu lực 2026).

## 0. Nguồn & kiểm

- A1: `~/kaggle_sim/out/nt-x14-s*`, `nt-k24-s-s*`, `nt-k24-b-s*` (24 kernel HO2026_NOTF, 8 seed).
- A0: `ho4-k24-s-s*`, `ho4-k24-b-s*`, `tsx-ho-x14-s*` — chấm lại **cùng hàm** trong `ho_tradfi_wk/notf_mtm.json`
  (không có bản ECMEAS H 2026 nào được công bố trước đó; đây là lần đầu, nên cột "gốc" = A0 chấm cùng scorer).
- MTM chạy lại trong task này (8 run x14): `miss=0, nofile=0, nosym=0, fetch ok=0/fail=0` (offline, 220 symbol/615 file/274 ngày),
  `eqcheck.final_ok=true` + `upd_vs_result=true` 8/8; khớp `notf_mtm.json` với `max|Δ| < 1e-6` trên `n/sum_pnl/roi/maxdd`
  của W9/Q1/Q2/Q3 × 8 seed.
- Số chi tiết: `docs/result/golive_quarterly_a1/ecm_h_a1.json`.

## 1. x14 (gói go-live v1.1) — mean 8 seed

| Cửa sổ | ROI % A0 → **A1** | maxDD % A0 → **A1** | ΣPnL USD A0 → **A1** | Sharpe A0 → **A1** | Sortino A0 → **A1** | % thời gian có vị thế | % ngày có vào lệnh | seed ROI > 0 |
|---|---|---|---|---|---|---|---|---|
| W9 | 12,49 → **15,82** | −5,71 → **−5,79** | 18 105 → **22 883** | 2,35 → **2,68** | 4,76 → **5,74** | 33,6 → 32,5 | 11,0 → 10,3 | 8/8 → **8/8** |
| H1 | 12,20 → **17,02** | −5,58 → **−5,74** | 20 117 → **27 048** | 3,44 → **4,10** | 9,39 → **13,82** | 25,4 → 25,2 | 9,8 → 9,4 | 8/8 → **8/8** |
| Q1 | 6,48 → **6,68** | −5,58 → **−5,74** | 9 389 → **9 664** | 3,66 → **3,80** | 11,70 → 12,44 | 27,2 → 26,6 | 6,9 → 6,5 | 8/8 → **8/8** |
| Q2 | 5,37 → **9,69** | −3,31 → **−3,14** | 10 728 → **17 384** | 3,35 → **4,44** | 8,30 → **16,57** | 23,5 → 23,8 | 12,6 → 12,2 | 8/8 → **8/8** |
| Q3 | 0,27 → **−1,03** | −4,07 → **−4,16** | −2 012 → **−4 165** | 0,29 → **−0,61** | 0,79 → −0,80 | 49,9 → 46,9 | 13,3 → 12,2 | 5/8 → **0/8** |

DD xấu nhất theo seed: W9 −5,14 → −5,36 %; H1 −5,14 → −5,20 %; Q3 −2,49 → −3,68 %.

## 2. k24-b (base) — mean 8 seed

| Cửa sổ | ROI % A0 → **A1** | maxDD % A0 → **A1** | ΣPnL USD A0 → **A1** | Sharpe | Sortino | % thời gian có vị thế | % ngày vào lệnh | seed ROI > 0 |
|---|---|---|---|---|---|---|---|---|
| W9 | 10,19 → **13,38** | −5,75 → **−5,79** | 14 758 → **19 336** | 1,99 → **2,33** | 3,97 → **4,92** | 32,8 → 31,6 | 11,0 → 10,3 | 8/8 → 8/8 |
| H1 | 9,90 → **14,55** | −5,58 → **−5,74** | 16 723 → **23 412** | 2,93 → **3,63** | 7,86 → **11,99** | 24,1 → 23,9 | 9,8 → 9,4 | 8/8 → 8/8 |
| Q1 | 4,45 → **4,54** | −5,58 → **−5,74** | 6 425 → **6 553** | 2,70 → 2,79 | 8,52 → 8,82 | 24,6 → 24,0 | 6,9 → 6,5 | 8/8 → 8/8 |
| Q2 | 5,23 → **9,58** | −3,34 → **−3,14** | 10 297 → **16 858** | 3,25 → **4,38** | 8,03 → **16,06** | 23,5 → 23,8 | 12,6 → 12,2 | 8/8 → 8/8 |
| Q3 | 0,27 → **−1,03** | −4,07 → **−4,16** | −1 965 → **−4 076** | 0,29 → −0,61 | 0,79 → −0,80 | 49,9 → 46,9 | 13,3 → 12,2 | 5/8 → **0/8** |

## 3. k24-s (E0, cost-penalty) — mean 8 seed

| Cửa sổ | ROI % A0 → **A1** | maxDD % A0 → **A1** | ΣPnL USD A0 → **A1** | Sharpe | Sortino | % thời gian có vị thế | % ngày vào lệnh | seed ROI > 0 |
|---|---|---|---|---|---|---|---|---|
| W9 | 8,88 → **12,16** | −5,77 → **−5,72** | 9 262 → **12 663** | 1,81 → **2,18** | 3,35 → **4,49** | 34,4 → 31,9 | 11,5 → 10,9 | 8/8 → 8/8 |
| H1 | 9,55 → **14,79** | −5,54 → **−5,67** | 11 682 → **17 127** | 2,96 → **3,85** | 7,70 → **13,82** | 25,5 → 24,3 | 10,5 → 10,1 | 8/8 → 8/8 |
| Q1 | 4,61 → **4,71** | −5,54 → **−5,67** | 4 810 → **4 904** | 3,14 → 3,26 | 9,94 → 10,56 | 25,3 → 24,1 | 8,1 → 7,8 | 8/8 → 8/8 |
| Q2 | 4,71 → **9,63** | −3,51 → **−3,17** | 6 871 → **12 223** | 2,94 → **4,42** | 6,94 → **19,02** | 25,7 → 24,5 | 12,9 → 12,4 | 8/8 → 8/8 |
| Q3 | −0,59 → **−2,29** | −4,29 → **−4,53** | −2 420 → **−4 463** | −0,20 → −1,35 | −0,06 → −1,77 | 52,0 → 46,9 | 13,5 → 12,4 | 3/8 → **0/8** |

## 4. Đọc số

1. **Cả 3 cấu hình đều cải thiện W9 và H1 mạnh**, đều nằm ở **Q2** (ROI +4,3…+4,9 pp); Q1 gần như đứng yên (+0,09…+0,20 pp).
2. **Chất lượng lợi nhuận tốt hơn:** Sharpe W9 x14 2,35 → 2,68; Sortino Q2 x14 8,30 → 16,57 (đuôi lỗ mỏng hơn), dù
   **maxDD W9 sâu hơn nhẹ** (−5,71 → −5,79 % mean; theo seed xấu nhất −5,14 → −5,36 %).
3. **Q3 tệ hơn ở mọi cấu hình** (0/8 seed ROI > 0), maxDD Q3 x14 −4,07 → −4,16 %, seed xấu nhất −2,49 → −3,68 %. Q3 vốn FAIL
   ở cả A0/A1 ⇒ không dùng để nâng hạng.
4. **Thời gian phơi nhiễm giảm** (W9 x14 33,6 → 32,5 %), số ngày vào lệnh giảm nhẹ ⇒ ít lệnh hơn nhưng lãi/cụm cao hơn.
5. **CHƯA GIẢI THÍCH cơ chế** của +3,3 pp W9 (kế thừa HO2026_NOTF §6: chưa tách phần slot TF vs market/gate/ALT_EW; không có
   ablation trong prereg). Q3 xấu thêm cũng chưa giải thích.

## 5. Giới hạn

- Đây là **sensitivity/release số**, KHÔNG phải holdout mới: HO 2026 và các số A0 đã được nhìn trước khi chốt prereg
  (`PREREG_HO2026_NOTF.md:5` khai thật).
- Chỉ số A0 ở đây do **chấm lại** cùng scorer (không phải bản công bố cũ) ⇒ dùng để so cặp, không dùng làm "số lịch sử".
- Không chạy kernel, không gọi API, không tải dữ liệu; dung lượng tạo ~40 KB JSON.
