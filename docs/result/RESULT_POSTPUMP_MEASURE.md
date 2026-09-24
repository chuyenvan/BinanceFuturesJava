# RESULT_POSTPUMP_MEASURE — do tin hieu "post-pump" tren TOAN BO lenh (n=1089)

> **MO TA (descriptive) — KHONG chay sim, KHONG sua `.java`, KHONG push.**
> Thuc hien dung `docs/prereg/PREREG_POSTPUMP_MEASURE.md` (commit `f8ebac7`). Script
> `research/analysis/postpump_measure.py`. Du lieu: `printDone.csv` T170 (n=1089, md5
> `efb793e2...`) + `CLOSES_1H.bin` + `selector_pred_out/symbol_map.csv`.
> 2026-09-17.

## 1. Nhom (dinh nghia GIU NGUYEN)

| nhom | dinh nghia | n |
|---|---|---|
| `SUP` | `profit <= -20` | **49** |
| `DOI_CHUNG` | phan con lai | **1040** |
| tong | | **1089** |

- `mom30d` tinh duoc **839/1089** lenh; **250 lenh (23%) NaN** vi coin moi niem yet
  (< 30 ngay truoc entry). Trong do **12/49 lenh SUP** khong co du 30 ngay lich su
  (coin niem yet gan day) — tu than no da la mot quan sat quan trong (xem muc Gioi han).

## 2. (a) So sanh mom30d giua SUP vs DOI_CHUNG

| thong so | SUP (n=37) | DOI_CHUNG (n=802) | hieu (SUP - DC) |
|---|---|---|---|
| **mean mom30d (%)** | **+48.95** | **+47.66** | **+1.29** |
| **median mom30d (%)** | **+21.86** | **+5.33** | **+16.53** |

- **Bootstrap CI block-72h** cho hieu MEAN (2000 rep, seed `20260905`), **x1.21**:
  - CI raw (percentile 2.5/97.5): **[-47.40, +40.68]**
  - CI sau inflate x1.21: **[-56.65, +49.93]**
  - sd_boot = 22.09; **CI CHUA 0**.
- **Tieu chi (a) KHONG dat**: hieu mean mom30d (SUP - DOI_CHUNG) khong khac 0 co y nghia.
  Mau n=8 trong DIAG (mean +57 vs -3.7) **khong lap lai** tren toan bo 49 lenh: trung binh
  ca hai nhom deu co momentum 30d cao duong (~+48), vi he vao lenh coin momentum.

## 3. (b) Bucket theo mom30d (decile) — co don dieu khong?

Decile theo mom30d tang dan (n=839 lenh mom30d hop le, rank-based):

| decile | mom30d (min..max, %) | n | n_SUP | ti le SUP (%) | mean PnL (USD) | tong PnL (USD) |
|---|---|---|---|---|---|---|
| 1 | -95.7 .. -62.5 | 84 | 3 | 3.6 | +136.3 | +11,453 |
| 2 | -62.5 .. -51.9 | 84 | 3 | 3.6 | +70.9 | +5,958 |
| 3 | -51.8 .. -39.4 | 84 | 2 | 2.4 | +75.7 | +6,363 |
| 4 | -39.2 .. -16.8 | 84 | 6 | 7.1 | +33.2 | +2,791 |
| 5 | -16.8 .. +6.6 | 84 | 3 | 3.6 | +73.2 | +6,147 |
| 6 | +6.6 .. +34.4 | 83 | 2 | 2.4 | +45.8 | +3,799 |
| 7 | +34.5 .. +63.8 | 84 | 6 | 7.1 | +46.2 | +3,880 |
| 8 | +63.8 .. +105.1 | 84 | 3 | 3.6 | +71.2 | +5,978 |
| 9 | +106.8 .. +198.1 | 84 | 5 | 6.0 | +81.8 | +6,872 |
| 10 | +198.9 .. +1910.5 | 84 | 4 | 4.8 | +24.6 | +2,067 |

- Spearman rho(bucket, ti le SUP) = **+0.389** (nguong >= +0.7); D1 = 3.6%, D10 = 4.8%.
- **Tieu chi (b) KHONG dat**: ti le SUP **KHONG don dieu tang** theo momentum (D10 4.8% thap
  hon ca D4/D7 7.1%). Khong co xu huong "momentum cao -> de sup" ro rang.

## 4. (c) Theo nam 2021-2025

| nam | n | n_SUP | ti le SUP (%) | mean mom30d SUP | mean mom30d DOI_CHUNG |
|---|---|---|---|---|---|
| 2021 | 127 | 2 | 1.6 | +18.2 | +96.5 |
| 2022 | 171 | 8 | 4.7 | -27.7 | -15.7 |
| 2023 | 102 | 1 | 1.0 | +116.7 | +63.6 |
| 2024 | 228 | 9 | 3.9 | +108.3 | +89.1 |
| 2025 | 211 | 17 | 8.1 | +53.2 | +14.4 |

- Mo ta: ti le SUP tang dan ve sau (2025 = 8.1%); 2025 la nam co nhieu lenh sup nhat va la nam
  doi chung co momentum trung binh thap nhat (+14.4). Khong dung cho quyet dinh.

## 5. (d) Danh doi (bat buoc) — what-if, KHONG re-run

Loc "bo lenh co mom30d > nguong". Chi tinh tren PnL **DA XAY RA** (what-if), **KHONG re-run sim**.
Bao cao toan bo bang, **khong chon nguong tot nhat**.

| nguong | gia tri mom30d | lenh bi loc | SUP bi loc (lo tranh USD) | lenh LAI bi loc (lai mat USD) | lo nhe bi loc | **PnL rong thay doi (USD)** |
|---|---|---|---|---|---|---|
| **p75** | +77.45% | 210 | 10 (+8,398) | 186 (-24,274) | 14 | **-12,171** |
| **p90** | +198.23% | 84 | 4 (+5,741) | 76 (-8,694) | 4 | **-2,067** |
| **p95** | +277.53% | 42 | 1 (+1,316) | 38 (-4,391) | 3 | **-2,281** |

- O CA 3 nguong, so lenh **LAI bi loc** va **lai mat di** deu **LON HON** so lenh SUP bi loc va
  lo tranh duoc => **PnL rong thay doi AM** (loc momentum lam giam tong PnL, khong tang).

## 6. Feature phu (kiem lai ket luan cu — mo ta, khong dung cho quyet dinh)

| feature (tai entry) | SUP (mean / median) | DOI_CHUNG (mean / median) | nhan xet |
|---|---|---|---|
| vol30d (%) | 3.03 / 2.45 | 2.54 / 2.03 | khac biet nhe (nhu DIAG) |
| drawdown30d (%) | -39.0 / -39.8 | -37.3 / -37.2 | khong khac biet |
| symbolPred (1-P(win)) | 0.202 / 0.176 | 0.180 / 0.170 | khong phan biet duoc |
| tuoi niem yet (ngay) | 253 / 114 | 294 / 165 | SUP tre hon (median 114 vs 165) |

- Nhat quan voi DIAG: vol/drawdown/symbolPred khong phan biet; them mot quan sat: SUP co median
  tuoi niem yet tre hon (~50 ngay), nhat quan voi viec 12/49 SUP qua moi de tinh duoc mom30d.

## 7. KET LUAN (theo tieu chi chot truoc)

- (a) CI (sau inflate x1.21) cua hieu mean mom30d = **[-56.65, +49.93]** → **CHUA 0** → FAIL.
- (b) ti le SUP khong don dieu tang theo bucket momentum (rho +0.389, D10 4.8% < D4/D7 7.1%) → FAIL.
- => **NULL**. Tin hieu "post-pump" (momentum 30d cao truoc khi sup) **KHONG duoc xac nhan tren
  toan bo 49 lenh**. Mau n=8 trong cua so UW dai nhat la artifact cua mau nho.
- **DUNG** — khong de xuat ap dung, khong chay sim tiep.

## 8. Gioi han (phai ghi)

- Lenh la **conditional**: chi gom lenh he THUC SU da vao; khong suy ra gi ve coin/lenh bi loai
  hay co hoi mat di.
- What-if (muc 5) **khong tinh duoc** tac dong danh muc / giai phong margin / tuong quan vi the
  cung luc; chi la tong PnL da xay ra.
- **n_SUP = 49 nho**; tren mom30d chi con **37** (12 SUP qua moi de tinh). Decile ~5 SUP/decile.
- **Khong co CI** cho bang danh doi (what-if).
- `mom30d` dung close 1h (khong phai gia entry chinh xac); 30 ngay = 720 gio.

Co-Authored-By: Claude (subagent) — phan tich mo ta, pre-reg truoc, khong push.
