# RESULT_GATEDYN — gate p15 dong theo phan vi truot (rolling percentile) tren X1_C3_FULL 48 thang

Pre-reg: `docs/prereg/PREREG_GATEDYN.md` (`3cdccd0`). Co che co san: `GateRollingThreshold.java`
(key `SIM_GATE_ROLLING_PCT/DAYS` qua profile, khong rebuild jar). Nen: X1_C3_FULL 48 thang,
gate 33-feature goc, bins `predwf_map_s1a2_x1`, `TICKER_SOURCE=file`. Dataset dung chung
`wfo_ds_x1_gd` (4.0G, da xoa sau khi cham). Parity chay lai = md5 `2478e90d…` (khop tuyet doi).

## 0. Van de goc (do truoc khi chay)
Gate nguong cung 0.008: ty le thoi gian gate mo dao dong 0.5% (2023Q3) -> 96.4% (2026Q1) do
p15 drift (median 0.0034 -> 0.0101) => so lenh/quy mat can bang: parity n/quy 51..423,
std 100.8, CV 0.712 (16 quy 2022Q1..2025Q4).

## 1. Bang chinh (equity KHONG phai tieu chi)

| run | pct | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity | CV quy | min/max quy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PARITY_R | 0.008 cung | 2,266 | 84.69 | 14.96 | 7.333 | −19.570 | 3.308 | 1,945 | −12.46 | 227 | 111,428 | 0.712 | 51/423 |
| GD88 | 0.88 | 2,661 | 83.22 | 16.88 | 7.414 | −18.027 | 3.121 | 1,890 | −18.94 | 223 | 99,382* | 0.494 | 59/300 |
| **GD92** | **0.92** | **2,355** | **84.12** | **15.67** | **7.324** | **−17.026** | **3.509** | **1,841** | **−13.21** | **116** | **128,979** | **0.518** | **46/272** |
| GD96 | 0.96 | 1,873 | 84.04 | 15.64 | 7.323 | −17.066 | 3.508 | 1,640 | −11.90 | 175 | 104,680 | 0.559 | 40/230 |

\* GD88 equity can kiem lai tu log (bang chinh tool in maxDD −18.94, UW 223).

## 2. Tieu chi PRIMARY (do deu lenh theo quy) — GD92 DAT
- **CV quy giam 27.3%** (0.712 -> 0.518), yeu cau >= 20%: DAT. GD88 giam 30.6% (0.494),
  GD96 giam 21.5% (0.559).
- **min-quy**: parity 51 -> GD92 46 (-9.8%, trong gioi han -20%), GD88 59 (+15.7%), GD96 40 (-21.6%, VI PHAM gioi han).
- Peak quy cao nhat: parity 423 (2025Q4) -> GD92 272 (2024Q4), GD88 300, GD96 230.

## 3. Rate chat luong + CI (block 72h x1.21) — chi GD92 sach
| run | toan cua so | 2022 | 2023 | 2024 | 2025 | doc |
|---|---|---|---|---|---|---|
| GD88 | **2 XAU**: win% −1.45 CI [−2.96,−0.02], TSloss% +1.91 CI [+0.47,+3.39] | 0 | 1 (meanP −1.41 XAU) | 1 (TSloss% XAU) | 0 | **LOAI** |
| **GD92** | 0 XAU; 1 TOT: **mP\|SL +2.54** CI [+0.05,+5.36] | 0 | 0 | 0 | 0 XAU; 2 TOT (TSloss% −3.22, meanP +1.46) | **PASS** |
| GD96 | 0 XAU; 1 TOT (mP\|SL +2.50) | 0 | 1 XAU (win% −3.32) | 0 | 0 | **LOAI** |

GD88: gate mo rong qua (n +395) loang chat luong. GD96: 2023 win% xau ngoai CI.

## 4. Rang buoc cung — chi GD92 PASS
| run | maxDD% | UW | nam am? | quy_min | PASS |
|---|---|---|---|---|---|
| PARITY_R | −12.46 | 227 | khong | −4.6 (2024Q2) | **FAIL** (UW>120) |
| GD88 | **−18.94** | 223 | khong | −5.4 | FAIL (maxDD + UW) |
| **GD92** | −13.21 | **116** | khong | −4.6 | **PASS** |
| GD96 | −11.90 | 175 | khong | −4.1 | FAIL (UW) |

GD92 la bien the DUY NHAT PASS rang buoc cung — UW giam 227 -> 116 nho gate dong chan bot vao
2024Q4/2025Q1 (quy parity mo rong qua nho p15 cao) va mo them o 2023 (quy parity ngheo).

## 5. PHAN QUYET — GD92 (pct=0.92, window=90d) THANG o tang sim
Dat ca 3 dieu kien pre-reg muc 4: PRIMARY (CV −27%, min-quy trong han), 0 rate XAU ngoai CI
(chi rate TOT), PASS rang buoc cung (UW 116). Equity 128,979 vs 111,428 bao rieng (cung huong
nhung KHONG phai tieu chi). GD88/GD96 LOAI (vi pham rate/rang buoc).

**Khac B4 (NULL tren C2b cu):** tren nền C3_FULL engine da sua (B1/B2/B3) + cua so 48 thang,
rolling gate pct 0.92 CAI THIEN ca do deu lan rang buoc cung. Luu y: p15 cua GATEFEAT 27-feature
da bi NULL o tang sim (xem RESULT_GATEFEAT), nen gate 33-feature giu nguyen la nen dung.

## 6. Viec tiep theo (KHONG tu chay — can user duyet)
1. **Config de xuat cho production/sim**: them vao profile `x1_c3_full.properties` (hoac ban
   copy san xuat): `SIM_GATE_ROLLING_PCT=0.92`, `SIM_GATE_ROLLING_DAYS=90`. Luu y: day la doi
   baseline C3_FULL — can user duyet truoc khi chot. Neu chot, chay lai cac cong parity/regression
   de xac nhan khong troi.
2. Kiem tra them: pct quanh 0.92 (0.90/0.94) de xem co tot hon nua khong — pre-reg moi, KHONG
   tune tren pre-reg nay (quota 3 da dung het).
3. Chat luong gate OOS (IC) cua GD92 so voi parity — do bo sung neu can.
4. Dataset `wfo_ds_x1_gd` da xoa. Cac artifact giu lai: 4 profile `x1_gd{88,92,96}.properties`
   (da commit), `research/analysis/gd_evenness.py`, printDone cua 4 run trong devrun/.
