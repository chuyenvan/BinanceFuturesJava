# RESULT_GATEDYN2 — grid 2 chieu pct × window (time rolling) quanh GD92

Pre-reg: `docs/prereg/PREREG_GATEDYN2.md` (`1c1ecca`). Nen X1_C3_FULL 48 thang, gate 33f goc, bins X1,
TICKER_SOURCE=file. Dataset dung chung `wfo_ds_x1_gd2` (da xoa sau khi cham). Parity chay lai
md5 `2478e90d…` khop. Ghi chu van hanh: 2 lan bi gateway restart cat giua run — da chay lai
cac sim dut, ket qua duoi la ban HOAN CHINH cua 6/6 run.

## 1. Bang chinh (equity KHONG phai tieu chi)

| run | pct/W | n | win% | TSloss% | mP\|SL | meanP | maxDD% | UW | equity | CV quy |
|---|---|---|---|---|---|---|---|---|---|---|
| PARITY_R | 0.008 | 2,266 | 84.69 | 14.96 | −19.570 | 3.308 | −12.46 | 227 | 111,428 | 0.712 |
| **GD92** | **0.92/90** | **2,355** | **84.12** | **15.67** | **−17.026** | **3.509** | **−13.21** | **116** | **128,979** | **0.518** |
| G90W60 | 0.90/60 | 2,490 | 83.53 | 16.39 | −17.057 | 3.321 | **−15.22** | 221 | 124,625 | 0.469 |
| G90W120 | 0.90/120 | 2,503 | 83.62 | 16.34 | −17.933 | 3.300 | **−18.73** | 223 | 108,251 | 0.525 |
| G92W60 | 0.92/60 | 2,328 | 84.15 | 15.68 | −17.327 | 3.384 | −14.51 | 183 | 130,175 | 0.483 |
| G92W120 | 0.92/120 | 2,320 | 83.92 | 15.91 | −16.981 | 3.539 | −12.33 | 153 | 125,953 | 0.538 |
| G94W60 | 0.94/60 | 2,142 | 83.75 | 15.97 | −17.175 | 3.339 | −13.43 | 185 | 112,171 | 0.498 |
| G94W120 | 0.94/120 | 1,680 | **77.80** | **27.32** | −8.875 | 2.793 | **−16.81** | **575** | 45,134 | 0.537 |

## 2. Rang buoc cung (maxDD<=15%/nam, UW<=120, khong nam am, quy>=-5%) — CHI GD92 PASS

| run | 2022 | 2023 | 2024 | 2025 | qmin | UW | PASS |
|---|---|---|---|---|---|---|---|
| PARITY_R | 17.3 | 60.4 | 45.3 | 16.5 | −4.6 | 227 | FAIL (UW) |
| **GD92** | 7.2 | 74.1 | 44.3 | 36.8 | −4.6 | **116** | **PASS** |
| G90W60 | 8.1 | 74.7 | 43.3 | 31.6 | **−6.4** | 221 | FAIL (UW+qmin) |
| G90W120 | 13.6 | 83.2 | 41.1 | 5.4 | **−5.1** | 223 | FAIL (UW+qmin) |
| G92W60 | 7.9 | 72.4 | 49.6 | 33.6 | −4.6 | 183 | FAIL (UW) |
| G92W120 | 10.2 | 79.5 | 39.7 | 30.2 | **−5.0** | 153 | FAIL (UW+qmin) |
| G94W60 | 4.6 | 68.4 | 38.7 | 31.2 | −3.4 | 185 | FAIL (UW) |
| G94W120 | **−7.8** | 19.9 | 20.2 | **−2.9** | **−7.8** | 575 | FAIL (nam am, UW, qmin) |

## 3. PHAN QUYET — GD92 (0.92/90d) van la diem toi uu duy nhat PASS; grid xac nhan vung on dinh

- **6/6 bien the moi deu FAIL rang buoc cung** (UW 153-575, hoac qmin < −5, hoac nam am o
  G94W120). KHONG co bien the nao thay duoc GD92.
- **W=90 la diem ngot**: W=60 (UW 183) qua nhanh/nhieu churn; W=120 (UW 153, qmin −5.0) qua
  cham/tre drift. Ca hai huong deu xau hon GD92 (UW 116).
- **pct 0.92 la diem ngot**: pct 0.90 mo rong qua (n +124-237, UW 221-223), pct 0.94 chat qua
  (G94W60 UW 185; G94W120 tham hoa: win 77.8%, TSloss 27.3%, 2022 −7.8%, UW 575, equity 45k —
  W=120 + pct cao = gate chet nghet o 2022-23 roi mo vang o 2024-25).
- CV quy: GD92 0.518 nam giua day 0.469-0.538 — khong phai thap nhat nhung la diem duy nhat
  can bang do deu + chat luong + rang buoc.
- G92W60 co equity cao nhat (130,175) nhung UW 183 FAIL — equity khong phai tieu chi (dung
  pre-reg muc 2 quy tac 4).

=> **GIU GD92 (SIM_GATE_ROLLING_PCT=0.92, SIM_GATE_ROLLING_DAYS=90)** lam config de xuat.
Grid khang dinh: 0.90-0.94 × 60-120d la vung "gan on dinh" ve CV/rate nhung chi 0.92×90 qua
duoc cong rang buoc cung. Bai hoc: UW<=120 la rang buoc khe — chi pct 0.92/W 90 (can bang
giua thich nghi va on dinh) dat.

## 4. Viec tiep theo (can user duyet)
1. Chot GD92 vao profile san xuat: `SIM_GATE_ROLLING_PCT=0.92`, `SIM_GATE_ROLLING_DAYS=90`
   (them vao `x1_c3_full.properties` hoac ban copy san xuat). Day la doi baseline C3_FULL —
   chay lai parity/regression sau khi chot.
2. Khong tune them pct/W (grid da phu 2 chieu, quota het). Neu muon do sau: deadband 2 nguong
   chong flap — pre-reg moi rieng.
3. Cac artifact giu lai: 6 profile `x1_gd2_*.properties`, `research/analysis/gd_evenness.py`,
   printDone 6 run trong devrun/. Dataset `wfo_ds_x1_gd2` da xoa.
