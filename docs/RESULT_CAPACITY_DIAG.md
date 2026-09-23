# RESULT_CAPACITY_DIAG — chan doan "vi sao NULL suot": **hap thu** hay **thuoc do sai**?

Ngay: 2026-09-23. Pre-reg: `docs/PREREG_CAPACITY_DIAG.md` (**commit `aedf535`**, chot TRUOC khi do).
Vong nay **thuan Python offline** — KHONG chay Java/sim tren Oracle (shadow `c3` van `active`), KHONG
`claude-run`/Claude Code, KHONG dung slot Kaggle, **KHONG cham 2026**, **KHONG push**.
Trung gian: `/home/ubuntu/capdiag/`. Bien the do: `simout_series.json`, `metrics.json`, `rank.py`,
`capacity.py`, `ticklog_parse.py`, `parse_simout.py`.

---

## 0. KET LUAN (doc truoc)

1. **H1 — "he bi KIN CHO" ⇒ ❌ SAI (khong kín chỗ).** Tren T170/DEV: `max U = marginRunning/equity = 0.469`
   < nguong `0.9 × U_MAX = 0.54`; **0/1644 ngay** cham nguong; `NO_BUDGET` = **0 dong** tren 10,198,019
   quyet dinh ung vien (do lai doc lap tu `cand.bin.gz`); khoa symbol = **5.46%** (nguong 20%);
   so ung vien/phut = **7.57** (<= top-K = 8) ⇒ tran `NUMBER_ENTRY_EACH_SIGNAL=2` khong chi phoi leg
   selector (75% so leg). **Rang buoc binding KHONG phai cho (slot/von) ma la CONG AI**: 17,925,650 ung
   vien ⇒ **841 PASS** (0.0047%). ⇒ **"NULL suot" KHONG duoc giai thich bang hap thu cong suat.**
2. **H2 — "thuoc do SAI cho exit" ⇒ ✅ DUNG (theo dung tieu chi da chot).** Xep 7 bien the exit:
   hang CU (`meanP`) `L1 > F3 > V3 > V2 > L3 > L2 > V1` vs hang MOI (`Calmar`) `L1 > V3 > L3 > V2 > V1 > L2 > F3`
   ⇒ **Kendall tau = 0.333**, **7/21 cap dao dau** (nguong chot: >= 2). Ro nhat: **F3** hang **2/7** theo
   `meanP` (va **cao nhat** `mP|SM = 134.6`) nhung hang **7/7 (cuoi)** theo `Calmar` — va `SumPnL` cua F3
   **thap hon P0** (75 812 vs 76 070).
3. ⇒ **Ca hai deu dung mot phan, nhung trong tam khac han chan doan cu**: khung "di tim cong thuc gap
   tot hon" that bai mot phan vi **thuoc do (rate do chinh luat exit dinh nghia)** — khong phai vi he het cho.
4. **De xuat (KHONG tu tich hop):** xem §4 — (a) doi **tieu chi cham exit** sang **Calmar/maxDD +
   SumPnL + capture** (do lai cac vong cu, phai pre-reg moi); (b) **KHONG** dau tu them vao exit
   (3 vong da NULL); (c) neu muon tang "so cuoc doc lap" thi phai vuot qua **cong AI** (96% ung vien chet
   o day), khong phai slot/von.

---

## 1. VIEC A — DO "MUC DO KIN CHO" (tu `logs/sim.out` T170 + ticklog)

### 1.1 Liet ke moi cho chan entry (doc code, file:dong) — da chot o pre-reg §2.1
C1 tran so lenh/tin hieu (`Simulator…:333,339-342`) · C2 `symbolLocked` (`:336,347-353`) ·
C3 `isSymbolRunning` nhanh selector (`:431,760-765`) · C4 `managerBudget==null` khi `u>=U_MAX` (`TradeUtils:125-143`,
`Configs:156`) · C5 nghet bac grid (`:1359-1362`) · C6 tier3+DCA (`:1306-1311`) · C7 gate AI (`:1255-1266`) ·
C8 pump-dump (`:1272-1275`) · C9 pred null (`:1246-1249`) · C10 ticker unavailable · C11 tick-block (OFF) ·
C12 `CONC_CAP_*` (OFF).

🔴 **Chot TRUOC o pre-reg:** `NUMBER_ENTRY_EACH_SIGNAL` **chi ap cho leg tin hieu thi truong**
(`getTopSymbolArray`), **khong** ap cho leg selector (di het top-K = 8).

### 1.2 Nguon so + ket qua — (a) so ung vien muon vao ma khong vao duoc, tach theo LY DO

| nguon | pham vi | do tin cay |
|---|---|---|
| `[GATE] n_cand/n_pass` trong `sim.out` | **T170**, 2021-07-01..2025-12-31 (1644 ngay) | cum cua **chinh duong sim** |
| `cand.bin.gz` (`/home/ubuntu/tick/R5_TL`, `R6_TL`) parse lai doc lap (32B/row) | profile **C2b** (env-mode), DEV 2022-01..2024-06 | **do lai tu file goc**, khop byte voi `docs/TICKLOG_RESULT.md` §5 |

**(a-1) T170 — tu `sim.out` (chinh duong sim):**

| chi tieu | P0 | L1 | L2 | L3 | F3 | V1 | V2 | V3 |
|---|---|---|---|---|---|---|---|---|
| `n_cand` (ung vien qua cong, tru BIG_DOWN) | 17 925 650 | 17 904 842 | 17 885 012 | 17 921 513 | 17 883 070 | 17 935 225 | 17 921 013 | 17 933 968 |
| `n_pass` | **841** | 838 | 839 | 841 | **791** | 847 | 843 | 847 |
| pass rate | **0.0047%** | 0.0047% | 0.0047% | 0.0047% | 0.0044% | 0.0047% | 0.0047% | 0.0047% |

⇒ **7.57 ung vien/phut** (17 925 650 / (1644 × 1440)); **99.9953% ung vien bi cong AI chan**.

**(a-2) Phan ra theo LY DO (do lai doc lap tu `cand.bin.gz`, R5_TL — profile C2b; T170 khong co ticklog):**

| ly do | so quyet dinh | % | co che |
|---|---|---|---|
| `GATE_REJECT` (C7) | 9 635 332 | **94.482%** | gate AI (MOM15 + pred) |
| `ALREADY_OPEN` (C2/C3, **khoa symbol**) | **556 318** | **5.455%** | symbol dang co vi the |
| `GRID_EXHAUSTED` (C5) | 3 619 | 0.035% | het bac grid DCA |
| `NO_TICKER` (C10) | 1 725 | 0.017% | — |
| `ENTERED` | 1 025 | **0.010%** | vao lenh that |
| **`NO_BUDGET` (C4 — von/`U_MAX`)** | **0** | **0.000%** | **khong bao gio xay ra** |

⇒ khop tung so voi `docs/TICKLOG_RESULT.md` §5 (bang cu), va khop **cheo** voi T170: tong cua so ung
vien `8 × 1644 × 1440 = 18 938 880` tru `n_cand = 17 925 650` ⇒ **1 013 230 (5.350%) bi bo qua vi KHOA
SYMBOL** — gan bang dung 5.455% do truc tiep tu C2b. Hai profile khac nhau, hai duong do khac nhau,
cung mot ket qua ⇒ **so dang tin**.

### 1.3 (b) % thoi gian rang buoc CHO la BINDING — tu series NGAY `sim.out` (T170)

| chi tieu | P0 | L1 | L2 | L3 | F3 | V1 | V2 | V3 |
|---|---|---|---|---|---|---|---|---|
| `max U` (margin/equity, dinh ngay) | **0.469** | 0.474 | 0.474 | 0.469 | 0.473 | 0.466 | 0.469 | 0.467 |
| ngay co `U >= 0.54` (= 0.9×U_MAX) | **0** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ngay co `U >= 0.30` | 41 (2.5%) | 46 | 47 | 41 | 45 | 42 | 42 | 43 |
| trung vi `U` | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| p90 `U` | 0.136 | 0.146 | 0.147 | 0.136 | 0.151 | 0.136 | 0.137 | 0.133 |
| leg mo dong thoi: max / trung binh | **31 / 0.80** | 31 / 0.84 | 33 / 0.87 | 31 / 0.81 | **40 / 0.89** | 31 / 0.79 | 31 / 0.81 | 31 / 0.80 |
| % ngay co 0 leg mo (moc 07:00) | 77.4% | 76.3% | 74.9% | 77.4% | 76.3% | 77.6% | 77.3% | 77.6% |
| turnover slot (gio giu / thoi gian) | 0.791 | 0.823 | 0.852 | 0.793 | 0.880 | 0.778 | 0.799 | 0.781 |

⇒ **Von va slot gan nhu TRONG**: tran `U_MAX=0.60` bi cham xa (max 0.469); trung binh chi **0.8 leg mo
dong thoi** tren universe **863 symbol** (0.09%). `NO_BUDGET = 0` ⇒ **khong co ngay nao von la rang buoc**.

### 1.4 (c) So tick co it nhat 1 ung vien bi chan / tong tick co tin hieu

- **T170:** so phut co ung vien ~ `17 925 650 / 7.57 ~= 2.37M` (≈ **100%** so phut cua 1644 ngay);
  trong do **1 013 230** luot bi khoa symbol ⇒ **~% phut co >= 1 ung vien bi chan ≈ 99.99%**.
- **Do truc tiep (C2b, `cand.bin.gz`):** 1 274 285 phut co ung vien; **1 274 270 phut (99.9988%)** co
  **>= 1 ung vien BI CHAN**; chi **395/372 phut** (R5/R6) co >= 1 lenh VAO. So ung vien/phut: min 8,
  **trung vi 8**, max 18 ⇒ top-K **luon kin** (pool >= 8) ⇒ **top-K cut khong phai rang buoc**.

### 1.5 PHAN QUYET H1 (theo nguong da chot o pre-reg §2.4)

| dieu kien (chot TRUOC) | nguong | do duoc | dat? |
|---|---|---|---|
| (a) `max U >= 0.54` tren >= 1% ngay, hoac `NO_BUDGET >= 1%` ung vien | 0.54 / 1% | **0.469 / 0/1644 ngay; 0/10 198 019 dong** | ❌ |
| (b) khoa symbol (`ALREADY_OPEN`) >= 20% quyet dinh | 20% | **5.455%** (C2b) / **5.350%** (T170, suy ra) | ❌ |
| (c) >= 20% so phut co `>= numberOrder` ung vien khong khoa bi cat boi tran C1 | 20% | **RO** — tran C1 khong ap cho leg selector; khong co log cho leg tin hieu thi truong | **RO** |

⇒ **H1 = SAI**: he **khong kin cho**; ca hai chi tieu do duoc deu duoi nguong rat xa. Chi tiet (c) la
**RO** (khong bia) — nhung 75% so leg (821/1089) nam o nhanh **khong** chiu tran C1, nen C1 khong the la
nut co chinh.

**He qua truc tiep cho cau hoi goc:** vi chi **5.35%** ung vien bi khoa symbol, moi thay doi exit chi co
the **xao lai toi da ~5% tap lenh** — dung bang do lon do duoc: F3 **-50 leg (-4.6%)**, L1 -3, L2 -2,
L3 0, V1/V2/V3 +6/+2/+6. ⇒ exit la mot **nhieu loan bien nho**, khong phai don bay.

---

## 2. VIEC C — DO LAI CAC BIEN THE EXIT BANG THUOC KHAC

### 2.1 Bang day du (moi so tinh lai tu `printDone.csv` + `logs/sim.out` cua chinh tung chan)

| tag | n_leg | cum | **SumPnL** | **meanP** | win% | TSloss% | mP\|SM | mP\|SL | **CAGR%** | **maxDD%** | **Calmar** | Sortino | hold(h) | turn | leg/ngay |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **P0** (baseline) | 1089 | 1069 | **76 070** | 69.853 | 87.97 | 9.73 | 119.80 | -393.29 | 29.25 | **-6.30** | **4.64** | 0.93 | 31 210 | 0.791 | 0.663 |
| **L1** | 1086 | 1066 | **79 757** | **73.441** | 87.94 | 9.58 | 124.75 | -411.04 | 30.19 | -6.37 | **4.74** | 0.96 | 32 435 | 0.823 | 0.661 |
| **L2** | 1087 | 1068 | 74 740 | 68.758 | 88.32 | 9.48 | 117.62 | -398.02 | 28.90 | -6.69 | 4.32 | 0.91 | 33 585 | 0.852 | 0.662 |
| **L3** | 1089 | 1069 | 76 230 | 70.000 | 87.97 | 9.73 | 119.89 | -392.66 | 29.29 | -6.30 | 4.65 | 0.94 | 31 283 | 0.793 | 0.663 |
| **F3** (dinh=CLOSE) | 1039 | 1020 | 75 812 | 72.966 | 87.97 | **11.45** | **134.60** | -403.54 | 29.18 | **-8.30** | **3.52** | 0.88 | 34 708 | **0.880** | **0.632** |
| **V1** gap 0.05 | 1095 | 1075 | 72 314 | 66.040 | 88.04 | 9.68 | 115.11 | -391.76 | 28.26 | -6.52 | 4.33 | 0.89 | 30 686 | 0.778 | 0.666 |
| **V2** gap 0.12 | 1091 | 1071 | 77 466 | 71.004 | 88.18 | 9.53 | 120.46 | -398.31 | 29.60 | -6.40 | 4.62 | 0.95 | 31 511 | 0.799 | 0.664 |
| **V3** weak 0.17 | 1095 | 1075 | **79 287** | 72.409 | 87.95 | 9.77 | 123.73 | -401.50 | **30.07** | -6.42 | 4.68 | 0.94 | 30 804 | 0.781 | 0.666 |

**Cong kiem tra:** `SumPnL` cua P0 = **76 070** = `equity_final − equity_start = 111070 − 35000` (khop),
CAGR 29.25% khop 29.27% cua `RESULT_TRAIL_HINGE`, `maxDD` ngay -6.30% la **can duoi** cua -11.84% (do phan
giai NGAY, da ghi o pre-reg §3.5.1) ⇒ thuoc MOI do dung duong.

### 2.2 Xep hang 2 thuoc + Kendall tau (theo dung tieu chi da chot o pre-reg §3.4)

```
hang CU  (meanP) : L1 > F3 > V3 > V2 > L3 > L2 > V1
hang MOI (Calmar): L1 > V3 > L3 > V2 > V1 > L2 > F3
Kendall tau(meanP, Calmar) = +0.333   (c=14, d=7, n=21)
so cap DAO DAU = 7  (nguong chot: H2=DUNG khi tau<=0 HOAC >=2 cap dao dau)
```

| cap dao dau | theo `meanP` | theo `Calmar` |
|---|---|---|
| **L2 vs F3** | L2 **kem** hon | L2 **tot** hon |
| L2 vs V1 | L2 tot hon | L2 kem hon |
| L3 vs F3 | L3 kem hon | L3 tot hon |
| L3 vs V2 | L3 kem hon | L3 tot hon |
| **F3 vs V1** | F3 **tot** hon | F3 **kem** hon |
| **F3 vs V2** | F3 **tot** hon | F3 **kem** hon |
| **F3 vs V3** | F3 **tot** hon | F3 **kem** hon |

Doi chieu phu: `tau(meanP, SumPnL) = 0.714`; `tau(meanP, Sortino) = 0.429`.

⇒ **H2 = DUNG theo tieu chi da chot** (tau 0.333 > 0 nhung **7 >= 2 cap dao dau**).
🔴 **Noi that, de khong thoi phong:** neu lay **SumPnL** lam thuoc moi thi tau len **0.714** — tuc **khong**
phai moi thuoc deu dao; **nguon dao chinh la Calmar / maxDD** (va mot phan Sortino). Cau chuyen cu the la
**F3**: no **thang** tren moi rate do luat exit dinh nghia (`meanP` hang 2/7, `mP|SM` **cao nhat** 134.60,
capture nhom dinh >= 100% 0.385 > 0.262), nhung **thua** tren moi thuoc rui ro: `maxDD` -8.30% (te nhat),
`Calmar` 3.52 (cuoi bang), `SumPnL` 75 812 (< P0). Do dung la **"so 2 thuoc khac nhau"** — rate cu do
*chat luong lenh*, Calmar do *duong von*.

### 2.3 Capture ratio (M7) — bien the nao co `trailTrace.csv`

| tag | >=20%: n / med cap / SumPnL | >=50%: n / med cap / SumPnL | >=100%: n / med cap / SumPnL |
|---|---|---|---|
| **P0** (`tl-part`) | 123 / **0.662** / 51 997 | 29 / 0.406 / 23 049 | 21 / **0.262** / **15 906** |
| **L1** | 146 / 0.624 / 64 330 | 38 / 0.574 / 33 532 | 23 / 0.326 / 19 155 |
| **L2** | 166 / 0.537 / 64 223 | 48 / **0.537** / **36 679** | 23 / **0.441** / **19 637** |
| **L3** | 123 / 0.662 / 52 210 | 29 / 0.406 / 23 307 | 22 / 0.309 / 17 655 |
| **F3** | 160 / **0.663** / 60 519 | 30 / 0.466 / 20 196 | 21 / 0.385 / 13 399 |
| V1/V2/V3 | **RO** — khong co `trailTrace.csv` (chay 2026-09-19, truoc khi co co trace) | | |

⇒ **L2** dat capture nhom song lon TOT NHAT (`>=100%`: 0.441 vs P0 0.262, `SumPnL` 19 637 vs 15 906)
**nhung** L2 te nhat hang nhi (`Calmar 4.32`, `maxDD -6.69`, `SumPnL` 74 740) ⇒ lai mot lan nua: **thuoc
"capture" va thuoc "duong von" khong cung ket luan**. Luu y nhom `>= X%` la **hau-chon theo dinh da xay ra**
(canh bao cua `RESULT_TRAIL_LADDER`), nen khong duoc doc nhu bang chung GO.

### 2.4 PHAN QUYET H2

**DUNG.** Voi 7 bien the exit co cung tap entry (khac nhau < 5% leg), xep hang theo **rate do luat exit
dinh nghia** (`meanP` / `win%` / `TSloss%` / `mP|SM`) va xep hang theo **Calmar** chi trung **tau = 0.333**,
**7 cap dao dau** — trong do **F3** la ca ro nhat (hang 2/7 vs hang 7/7) va **L2** nguoc lai. Ket luan:
**rate cu la thuoc SAI (hoac it nhat: khong day du) cho quyet dinh exit**; phai cham lai bang thuoc
rui ro/von.

---

## 3. Tra loi thang 2 cau hoi cua owner

| cau hoi | tra loi | so cu the |
|---|---|---|
| **He co bi "kin cho" khong? ⇒ "NULL suot" co phai do hap thu khong?** | **KHONG kin cho ⇒ KHONG phai do hap thu** | `max U = 0.469 < 0.54`; 0/1644 ngay cham tran `U_MAX`; `NO_BUDGET = 0/10 198 019`; khoa symbol 5.46% (nguong 20%); 0.8 leg mo dong thoi / 863 symbol; rang buoc binding = **cong AI** (17 925 650 -> 841 PASS, 0.0047%) |
| **Thuoc do co sai cho exit khong?** | **CO — theo tieu chi da chot** | `tau(meanP, Calmar) = 0.333`, **7 cap dao dau**/21; F3: hang 2/7 -> 7/7; L2: hang 6/7 -> 6/7 nhung dao 2 cap; SumPnL F3 < P0 |

**Ghi chu quan trong (khong duoc doc sai):** exit **khong** bi chan boi cho — nhung exit **cung khong co
nhieu cho de cai thien**: no chi doi duoc < 5% tap lenh (phan bi khoa symbol), nen moi bien the exit
tu nhien chi la **nhieu loan bien nho**. Do la ly do **co cau** (khong phai "vo nghia") khien 4 vong exit
(P0 -> hinge V1V2V3 -> ladder L1L2L3 -> peak-close F3 -> exit-fit 17 policy) deu ra NULL/thin: **khong
phai he het cho, ma la exit khong phai don bay manh**.

---

## 4. DE XUAT BUOC TIEP (KHONG tu tich hop)

1. **Cham lai cac vong exit da co bang thuoc RUI RO** (Calmar/maxDD/Sortino + SumPnL + capture), **pre-reg
   moi**, TRUOC khi ket luan vong nao "NULL": 4 vong cu deu cham bang rate do luat exit dinh nghia ⇒
   ket luan "NULL" cua chung chi dung cho thuoc CU. 🔴 Canh bao: **F3** la ung vien **DUY NHAT** doi hang
   manh (2/7 -> 7/7) theo huong **XAU** — tuc neu cham lai, F3 se **bi loai dut khoat** (hien no dang la
   "cua hep con sang" cua `RESULT_EXIT_FIT`).
2. **Do lai thuoc do "rate" cho exit:** bat ky lan do exit nao trong tuong lai phai bao **it nhat**
   `SumPnL` + `Calmar` + `maxDD` song song voi rate; neu chi bao rate thi ket luan **khong** chuyen duoc
   sang quyet dinh.
3. **Khong** dau tu them vao exit (P0, hinge, ladder, peak-close, 17 policy = 4 vong NULL). Cua con lai
   khong nam o exit.
4. **Nut co that nam o CONG AI** (96%+ ung vien chet o do, 0.0047% pass), khong o slot/von (`U_MAX` cham
   xa mot nua). Neu muon tang "so cuoc doc lap" / doi phan phoi lenh thi phai lam o **cong/selection**,
   khong phai exit/sizing.
5. **Chua lam duoc trong vong nay (RO, ghi ro):** (a) `NUMBER_ENTRY_EACH_SIGNAL` cho **leg tin hieu thi
   truong** (BIG_DOWN) khong co counter ⇒ chua do duoc muc cat cua C1; (b) 1 phan capture ratio cua hinge
   V1/V2/V3 (khong co `trailTrace.csv`); (c) khong co ticklog cho **T170** (chi co C2b) ⇒ phan ra theo ly do
   phai suy tu C2b + kiem cheo bang `n_cand` cua T170.

---

## 5. Commit (KHONG push)

- `aedf535` — **`docs/PREREG_CAPACITY_DIAG.md`** (chot TRUOC khi do: nguong H1 1%/20%/20%, thuoc MOI
  M1..M8, tieu chi Kendall tau / so cap dao dau cho H2).
- commit CUOI cua vong nay (subject *result(capacity-diag)*, xem `git log --oneline -1`) — tai lieu nay
  + `research/analysis/capdiag/*` (`parse_simout.py`, `capacity.py`, `metrics.py`, `rank.py`, `ticklog_parse.py`).

Tai san dung lai duoc (thuan Python, khong JVM): `research/analysis/capdiag/*` +
`/home/ubuntu/capdiag/{simout_series.json,metrics.json}`; ngoai repo, khong commit.
