# RESULT_CLOSE_BIGGAP — quet "dinh CLOSE × giveback LON" tren harness offline

Ngay: 2026-09-23. Pre-reg: `docs/PREREG_CLOSE_BIGGAP.md` (**commit `7349c39`**, chot TRUOC khi do).
Vong nay **thuan Python offline** — **KHONG** chay Java/sim tren Oracle (shadow dang `active`), **KHONG**
`claude-run`/Claude Code, **KHONG** dung slot Kaggle, **KHONG** cham 2026, **KHONG push**.
Trung gian: `/home/ubuntu/exitfit/biggap/` (`results.pkl`, `biggap_table.csv`, `biggap_summary.txt`, `run.log`).

---

## 0. KET LUAN (doc truoc)

1. **KHONG co policy nao dat dieu kien GO da chot.** Dem tren **18 policy MOI** (15 chinh + 3 phu;
   moc F3 tinh rieng):
   - (a) TEST `SumPnL` **VA** `Calmar` cung > P0: **15/18** dat (moc F3 cung dat ⇒ 16/19 neu tinh ca moc).
   - (b) TRAIN khong xau di (ca 2 thuoc): **1/18** dat (**BB_50_12**).
   - (c) CI bootstrap block-ngay (2000 rep, seed 20260923, **x1.21 × sqrt(2 ln 15) = x2.816**) khong chua 0:
     **0/18** dat (ke ca CI **khong** inflate cung chua 0).
   ⇒ **NULL theo dung tieu chi da chot**; policy "sap dat" nhat = **BB_50_12** ⇒ danh **"CHUA DU KET LUAN"**.
2. 🔴 **Cong kiem chung thuoc (chot TRUOC §5) TRUOT 1/2** ⇒ phai doc ket qua bang **SumPnL + capture**,
   **KHONG** duoc dung `Calmar`/`maxDD` proxy de ket luan:
   - (1) `SumPnL` P0 toan DEV = **73 973** vs sim that **76 070** ⇒ lech **2.76%**, va lech nay **dung bang
     phan funding** (76070 − 73973 = **2 097** ≈ funding DEV −951/−1123 da ghi o `RESULT_EXIT_FIT` §5.2 —
     replay khong co funding). ⇒ thuoc SumPnL **khop**.
   - (2) `Calmar` proxy P0 **5.59** vs F3 **5.71** ⇒ **DAO** so voi sim that (P0 **4.64** > F3 **3.52**).
     ⇒ Theo pre-reg §5: **proxy KHONG dung duoc**, moi so `Calmar*/maxDD*` duoi day chi la **thong tin phu**.
3. **Gia thuyet cua owner bi BAC BO tren thuoc capture:** **khong** policy nao tang capture o **bat ky**
   nhom nao (`cap≥20%` P0 **0.689** vs tot nhat khac **0.667**; `cap≥50%` P0 **0.839** vs **0.798**).
   Gap cang lon ⇒ capture cang **GIAM** (BB_90_nc: 0.100 / 0.382). Thu SumPnL tang khong den tu
   "giu duoc nhieu hon cua song lon" ma tu **giu lenh lau hon (hold median 4h → 30h)** va thoat **gan
   entry** hon (BB_90_nc: dinh 100% ⇒ thoat o +10%).
4. **Nhom dinh ≥100% trong TEST = RONG** doi voi P0/F3 (n=0) ⇒ khong ket luan duoc ve "song lon" tren
   TEST o moc 100%; o moc ≥20/≥50% thi **nhom KHONG co dinh giua cac policy** (cua so giu dai hon ⇒ dinh
   do duoc lon hon) — day la **thien lech phan loai**, phai ghi ro (xem §7.4).
5. **Tra loi cau hoi "co nen quay lai nua khong": KHONG** — day la vong NULL thu 5 tren truc exit/gap
   (hinge → ladder → peak-close → 17 policy → 20 policy) va `RESULT_CAPACITY_DIAG` da chi ra nut co nam o
   **CONG AI** (0.0047% ung vien PASS), khong o exit.

---

## 1. Cong parity (dieu kien tien quyet)

Chay lai `research/exitfit/parity.py` truoc khi quet — **PASS** nguyen cac nguong:
status **100.00%** (≥99), phut khop **100.00%** (≥97), ≤2' **100.00%** (≥99), `tp` **99.82%** (≥95),
median |ΔPnL no-funding| **0.0000** (≤0.02), n=1089 leg, 0 mismatch.
⇒ harness dung de do; **moi ket luan duoi day dung tren no**.

## 2. Bang ket qua (2 moc + 15 chinh + 3 phu; don vi = cum; `*` = thuoc proxy da TRUOT kiem chung)

**TEST 2024-01..2025-12 (n=604 cum — harness giu NGUYEN tap entry cua T170), xep theo TEST SumPnL:**

| policy | TEST SumPnL | Calmar* | maxDD* | cap≥20% | cap≥50% | n(≥100%) / cap | n | TSloss% | hold med | CI raw (x/tr) | TRAIN SumPnL | TRAIN maxDD* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **BB_90_nc** | **89 632** | 10.18 | −9.24% | 0.100 | 0.382 | 39 / 0.542 | 604 | 9.9 | 30h | [−49.5, 167.4] | **13 508** | −7.15% |
| BB_90_35 | 75 575 | 8.34 | −9.88% | 0.256 | 0.556 | 20 / 0.706 | 604 | 9.9 | 25h | [−23.2, 104.1] | 17 828 | −6.17% |
| BB_90_20 | 66 848 | 6.46 | −11.55% | 0.423 | 0.644 | 2 / 0.794 | 604 | 9.9 | 19h | [−14.6, 71.6] | 19 246 | −5.79% |
| BB_70_35 | 59 883 | 5.79 | −11.79% | 0.297 | 0.560 | 11 / 0.688 | 604 | 9.9 | 15h | [−13.7, 49.1] | 20 286 | −5.35% |
| BB_90_12 | 59 475 | 5.72 | −11.87% | 0.565 | 0.754 | 0 / — | 604 | 9.9 | 14h | [−15.0, 50.0] | 24 308 | −5.10% |
| BB_70_20 | 58 774 | 5.61 | −11.99% | 0.364 | 0.641 | 1 / 0.822 | 604 | 9.9 | 14h | [−14.1, 51.0] | 21 035 | −5.28% |
| **BB_50_12** | 58 544 | 6.38 | −10.51% | 0.574 | 0.722 | 0 / — | 604 | 9.9 | 7h | [−9.5, 40.4] | **26 360** | −4.93% |
| BB_70_nc | 57 968 | 5.22 | −12.75% | 0.294 | 0.296 | 18 / 0.399 | 604 | 9.9 | 15h | [−38.7, 73.7] | 17 633 | −5.44% |
| BB_50_08 | 57 223 | 6.40 | −10.28% | 0.658 | 0.786 | 0 / — | 604 | 9.9 | 7h | [−7.6, 34.8] | 25 482 | −5.10% |
| BB_50_nc | 57 098 | 6.14 | −10.70% | 0.487 | 0.486 | 4 / 0.489 | 604 | 9.9 | 9h | [−20.1, 44.3] | 21 580 | −5.23% |
| **F3** (moc) | 56 496 | 5.71 | −11.40% | 0.661 | 0.727 | 0 / — | 604 | 9.9 | 6h | [−13.8, 37.8] | 24 387 | −5.12% |
| BB_70_08 | 56 441 | 5.98 | −10.89% | 0.662 | 0.786 | 0 / — | 604 | 9.9 | 8h | [−9.6, 34.7] | 24 393 | −5.10% |
| BB_50_35 | 56 408 | 6.08 | −10.70% | 0.487 | 0.494 | 4 / 0.654 | 604 | 9.9 | 8h | [−14.1, 37.3] | 23 198 | −5.22% |
| BB_90_08 | 56 031 | 6.00 | −10.79% | 0.667 | 0.798 | 0 / — | 604 | 9.9 | 9h | [−9.9, 33.9] | 24 984 | −5.17% |
| BB_70_12 | 55 478 | 5.59 | −11.49% | 0.561 | 0.737 | 0 / — | 604 | 9.9 | 11h | [−16.8, 39.5] | 23 932 | −4.97% |
| BB_50_20 | 55 255 | 5.79 | −11.05% | 0.491 | 0.613 | 0 / — | 604 | 9.9 | 8h | [−15.1, 36.6] | 24 573 | −5.17% |
| LAD_L1_close | 54 543 | 5.93 | −10.68% | 0.585 | 0.599 | 1 / 0.634 | 604 | 9.9 | 7h | [−15.2, 33.3] | 24 235 | −4.94% |
| LAD_L2_close | 53 438 | 5.56 | −11.19% | 0.505 | 0.527 | 3 / 0.569 | 604 | 9.9 | 8h | [−21.6, 33.8] | 22 349 | −5.20% |
| LAD_L3_close | 47 192 | 4.68 | −11.99% | 0.384 | 0.214 | 0 / — | 604 | 9.9 | 3h | [−29.9, 20.5] | 25 238 | −5.32% |
| **P0 = T170** (moc) | **46 827** | 5.59 | −9.99% | **0.689** | **0.839** | 0 / — | 604 | **8.4** | 4h | — | 22 897 | −4.41% |

`CI raw (x/tr)` = CI bootstrap block-ngay cua hieu `net/trade` TEST vs P0 **chua** inflate; CI **dung de
ket luan** = raw **×2.816** (vi du BB_50_12: `[−62.0, +100.8]`).

## 3. Doc bang

1. **Moi policy "close" (KE CA F3 — chi doi dinh, khong doi cap) deu > P0 tren TEST SumPnL**
   (thap nhat `LAD_L3_close` 47 192 > 46 827). ⇒ **khong the quy phan tang cho "cap lon"**: do la hieu ung
   cua **dinh CLOSE** (F3), da bi **sim THAT bac bo** o `RESULT_PEAK_CLOSE` (`fa26996`: harness +20.6%
   net/trade nhung sim that equity −0.23%, SumPnL −259, **mat 50 lenh**, `TSloss%` +1.72 ngoai CI XAU).
   Harness o day cung bao `TSloss%` 8.4 → **9.9** cho **moi** policy close — **cung dau** voi sim that.
2. **Truc "cap lon" chi co tac dung o cuc doan ratio 0.9 va cap ≥0.35/None**, va o do **TRAIN sup**:
   BB_90_nc TEST +91% nhung TRAIN **−41%** (13 508 vs 22 897); BB_90_35 TEST +61%, TRAIN −22%.
   Trong khi cap/ratio vua phai (BB_50_08/12) thi TEST +22%/+25% va TRAIN +11..15% — **nhung** khong vuot
   duoc CI. ⇒ quan he **khong on dinh theo che do**, khong phai "hieu ung chuan".
3. **Capture ratio (M4) — gia thuyet owner BI BAC BO:** khong policy nao > P0 o `cap≥20%`/`cap≥50%`;
   gap cang lon ⇒ capture cang nho (BB_90_nc 0.100/0.382). Chi tiet co che: gap = `ratio×peak` ⇒
   `rate_SL = (1−ratio)×peak` ⇒ voi ratio 0.9 thi SL **luon** o `0.1×peak` (ratchet ep `SL > entry`)
   ⇒ thoat **gan entry**, giu rat lau (hold med 30h, turnover 2.40 vs P0 0.935). **Khong phai "an duoc
   nhieu hon cua song lon"** ma la "khong bi cat som, bo lai gan het".
4. **Cham nhom (hau-chon, chi de doc)**: nhom `≥20%` TEST — P0 n=66, med peak 0.278, med exit 0.180,
   SumPnL 25 935; BB_90_nc n=**225**, med peak **0.429**, med exit **0.050**, SumPnL 126 191.
   ⇒ nhom **phinh ra** vi giu lau hon (cung tap lenh, cua so do dinh dai hon) — **khong** duoc doc la
   "bat duoc nhieu song lon hon". O `≥50%`: BB_90_nc med exit **0.333** < P0 **0.425** (bo lai nhieu hon/l enh).

## 4. Multiplicity — so policy da do

**20 policy do trong vong nay** (20 dong bang; trong do **18 policy MOI**) = **2 moc** (P0/T170, F3) + **15 chinh** (ratio 0.5/0.7/0.9 × cap
0.08/0.12/0.20/0.35/None) + **3 phu** (bac thang L1/L2/L3, dinh close). Cong don truc exit toi nay:
hinge 3 + ladder 3 + peak-close 1 + exit-fit 17 + **vong nay 18 (khong tinh moc)**.
CI ket luan **da inflate x2.816** (= 1.21 × sqrt(2 ln 15)) cho 15 policy chinh — **va van chua 0**.

## 5. Tra loi thang cau hoi cua owner

> "Gap bi cap o 3%/8% ⇒ rung la bi cat. Muon giveback to len theo dinh."

- **Bo cap lam tang SumPnL TRONG TEST — dung, nhung khong phai vi ly do owner nghi:** khong phai
  "cat it hon nen song sot song lon" (capture **giam** o moi nhom), ma vi **giu lenh lau hon** va thoat
  o `(1−ratio)×peak` gan entry. Phan tang nay **khong on dinh** (cung cong thuc lam TRAIN sup 41% o
  cuc doan manh nhat) va **khong qua duoc CI** (ke ca raw).
- **Cai owner thuc su muon** (giu duoc nhieu hon cua nhip 2x/3x) **khong xay ra o BAT KY policy nao**
  theo thuoc capture; o nhom ≥50% TEST, policy tot nhat ve SumPnL lai thoat o **0.333/0.425** cua dinh
  = **bo lai nhieu hon P0**.
- Va quan trong: **harness khong dinh gia duoc** phan "giu lenh lau hon ⇒ chiem symbol/slot lau hon ⇒
  mat luot vao moi" — chinh phan lam **F3 tut tren sim that (−50 lenh)**. Moi so TEST o day (n=604 co dinh)
  la **can TREN** cua ung vien close-mode.

## 6. Phan quyet theo tieu chi da chot

| dieu kien (chot TRUOC §6) | dem | policy |
|---|---|---|
| (a) TEST `SumPnL` > P0 **VA** `Calmar` > P0 | **15/18** (16/19 ke ca moc F3) | tat ca tru `BB_70_nc`, `LAD_L2_close`, `LAD_L3_close` |
| (a)+(b) TRAIN khong xau di | **1/18** | **`BB_50_12`** (TE 58 544 / Calmar 6.38; TR 26 360 / Calmar 6.60) |
| (a)+(b)+(c) CI khong chua 0 | **0/18** | — |

⇒ **KET LUAN: NULL.** `BB_50_12` = **"CHUA DU KET LUAN"**: diem tot o **ca TRAIN lan TEST** tren ca SumPnL
va Calmar-vA **CI block-ngay chua 0** (raw `[−9.5, +40.4]` x/tr; da inflate `[−62.0, +100.8]`) — dung
kieu "chua du ket luan" da chot, **khong** duoc coi la "hon".
⇒ **KHONG de xuat sim Kaggle** (pre-reg §6: chi de xuat khi (a)+(b)+(c)).
⇒ **Dong huong nay.** Cua hep duy nhat neu owner **van** muon chi 1 slot (KHONG phai de xuat cua vong
nay, ghi de lam RO): `x1_gs_t170_close` + `TS_MAX_GAP=0.12`/`TS_MAX_GAP_WEAK=0.12` (chi doi 1 con so
tren nen F3 da co) — **nhung** du kien truoc: no se lap lai dung that bai cua F3 (TSloss% xau hon, mat
lenh), vi toan bo ho nay dung tren hieu ung harness **da bi bac bo**. Uu tien thap.

## 7. Gioi han (ghi TRUOC trong pre-reg, khong phai bao chua sau)

1. Replay **khong** mo phong entry/sizing/von ⇒ `SumPnL` la tong PnL tung lenh; `Calmar/maxDD` la
   **proxy** va **da TRUOT** cong kiem chung (P0 5.59 vs F3 5.71 nguoc sim that 4.64 > 3.52) ⇒ **khong**
   dung de ket luan.
2. **Funding** bi loai ⇒ lech SumPnL P0 2.76% dung bang phan funding (2 097 USDT); chenh giua cac policy
   la bac 2 (funding phu thuoc thoi diem dong) — khong doi thu tu.
3. n=604 co dinh cho moi policy = **n cua T170**; harness **khong** tai hien duoc phan mat lenh do giu
   lau (sim that F3 −50 lenh) ⇒ so TEST la **can TREN**.
4. Nhom `≥X%` **khong co dinh** giua cac policy (cua so giu dai ⇒ dinh do duoc lon hon) ⇒ nhom `≥100%`
   TEST rong voi P0/F3 (n=0) nhung co **39** voi BB_90_nc — **thien lech phan loai**, khong doc nhu bang chung.
5. Moi so la **in-sample DEV**; ket qua duong van chi la ung vien can forward/sim.

## 8. Commit (KHONG push)

- `7349c39` — `docs/PREREG_CLOSE_BIGGAP.md` (chot TRUOC khi do).
- commit CUOI cua vong nay (subject *result(close-biggap)*, xem `git log --oneline -1`) —
  `research/exitfit/sweep_biggap.py` + tai lieu nay.

Tai san dung lai duoc: `/home/ubuntu/exitfit/biggap/{results.pkl,biggap_table.csv,biggap_summary.txt,run.log}`
(ngoai repo, khong commit). Cache nen `/home/ubuntu/exitfit/bars.pkl` giu nguyen (dung lai duoc).
