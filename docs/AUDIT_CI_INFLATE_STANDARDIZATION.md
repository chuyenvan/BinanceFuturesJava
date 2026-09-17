# AUDIT — CHUAN HOA `CI_INFLATE` (GIAI DOAN 1: CHI AUDIT, CHUA FIX)

> **Trang thai: AUDIT THUAN TUY.** Khong sua mot dong `.py`/`.java` nao, khong chay sim,
> khong chay lai bootstrap. Moi con so duoi day suy ra bang **so hoc tu CI DA CONG BO**
> trong cac RESULT doc + `k` DA KHAI BAO trong cac PREREG doc.
>
> **Giai doan 2 (tham so hoa `CI_INFLATE` theo `k` trong `c3_rates.py`/`x1_rates.py`) CHUA LAM**
> — cho MASTER review audit nay truoc.
>
> Nen: `docs/CI_REAUDIT.md`, `docs/PREREG_CI.md`, `docs/AUDIT_READJUDICATE_CI_RESCORE.md`,
> `RESULT_DCA_MORELEGS_V4.md` PHU LUC A.

---

## 0. KET LUAN MOT DONG

**KHONG round nao doi tu NULL sang PASS.** Co **7 rate rieng le** mat y nghia thong ke khi ap he
so dung, nhung **khong rate nao trong so do bien mot config NULL thanh config THANG** — chung deu
la rate ma *baseline* dang thang, hoac thuoc config da FAIL rang buoc cung. **Khong quyet dinh
lich su nao bi dao nguoc.**

Nhung co **2 round dung he so SAI THEO HUONG QUA CHAT ma KHONG the tai tinh tu doc** (DCA_ROUND_CAP,
DCA_AGG_PERCOIN — dung `1.7936` thay `1.4823`) — can chay lai `readjud_rescore` de ket luan. Xem muc 5.

---

## 1. CONG THUC + QUY UOC

```
CI_INFLATE_dung(k) = sqrt(2 * ln k)     voi k >= 2
CI_INFLATE_dung(1) = 1.0                (k=1: khong co multiplicity, giu CI goc)
```
`k` = **so ung vien (candidate/config) duoc kiem dinh so voi baseline TRONG DUNG round do**.
Baseline/control **khong** tinh la ung vien (xac lap o `AUDIT_READJUDICATE_CI_RESCORE` muc 2).

| k | 1 | 2 | 3 | 4 | 5 | 8 | 11 | 256 |
|---|---|---|---|---|---|---|---|---|
| `sqrt(2 ln k)` | 1.0000 | **1.1774** | **1.4823** | 1.6651 | 1.7941 | **2.0393** | 2.1899 | 3.3302 |

**Hang so `1.21` trong `c3_rates.py:33` ung voi `k = exp(1.21²/2) = 2.079`** — khong phai so nguyen,
khong co can cu nao trong repo. Day la gia tri lich su.

### 1.1 Cach tai tinh (so hoc, khong can chay lai bootstrap)

`x1_rates.ci_pair_df` dong 54 no rong CI **quanh TAM**, khong quanh 0:
```python
lo, hi = c - (c-lo)*CI_INFLATE,  c + (hi-c)*CI_INFLATE      # c = (lo+hi)/2
```
=> tu CI DA CONG BO `[lo,hi]` o he so `F`: `c=(lo+hi)/2`, `h=(hi-lo)/2`, **`h0 = h/F`** (nua-do-rong
GOC). Voi he so moi `F'`: **0 bi loai tru <=> `F' < F_crit`** voi

```
F_crit = F * |c| / h
```

`F_crit` la "he so toi da ma rate do van con y nghia". Bang muc 4 dung dung cong thuc nay.

### 1.2 ⚠️ HUONG CUA HIEU CHINH PHU THUOC LOAI PHEP KIEM — phai tach bach

| loai tieu chi | round dung | he so LON hon => | he so NHO hon => |
|---|---|---|---|
| **WIN-test**: ">= 2 rate TOT ngoai CI" | DEV2021_READJUDICATE, K_DENSITY, 5MGRID, DCA_SIGNAL_*, V4, 2X, GATEWIDEN, REGIME | **CHAT hon** (kho thang) | LONG hon (de thang) |
| **VETO-test**: "0 rate XAU ngoai CI" | DCA_ROUND_CAP, DCA_AGG_PERCOIN, BD_SIZE_ADAPT, SEL_BIGDOWN | **LONG hon** (de qua veto) | **CHAT hon** (de bi veto) |

=> Mot round dung he so QUA LON: neu la WIN-test thi **da tu phat**, neu la VETO-test thi **da tu tha**.
Day la ly do phai tach hai nhom khi doc bang muc 3.

---

## 2. BANG KIEM KE TOAN BO ROUND CO CHAY CI

| # | Round | doc | loai test | `CI_INFLATE` DA DUNG | `k` da khai bao (nguon) | `CI_INFLATE` DUNG | lech | huong sai |
|---|---|---|---|---|---|---|---|---|
| 1 | **DEV2021_READJUDICATE** (chon T170) | `RESULT_DEV2021_READJUDICATE` | WIN | **1.21** | **2** (PREREG dong 27: "2 variant T170,T130") | **1.1774** | +2.8% | qua chat |
| 2 | **K_DENSITY** (K12/K16) | `K12_RESULT` | WIN | **1.21** | **2** (PREREG dong 28 tu ghi "k=2 => 1.177 < 1.21") | **1.1774** | +2.8% | qua chat |
| 3 | **5MGRID** | `RESULT_5MGRID` | WIN | **1.21** | **1** (chi 1 arm 5M vs parity) | **1.0000** | +21.0% | qua chat |
| 4 | **REGIME_GATE** | `RESULT_REGIME_GATE` | WIN | **1.21** | **1** (PREREG dong 52: "k=1, 1 config duy nhat") | **1.0000** | **+21.0%** | qua chat |
| 5 | **DCA_SIGNAL_GATE V1** | `RESULT_DCA_SIGNAL_GATE` | WIN | **1.21** | **3** (X=-5/-8/-12%) | **1.4823** | **−18.4%** | **qua long** |
| 6 | **DCA_SIGNAL_GATE V2** | `RESULT_DCA_SIGNAL_GATE_V2` | WIN | **1.21** | **3** | **1.4823** | −18.4% | qua long |
| 7 | **DCA_GATEWIDEN_V3** | `RESULT_DCA_GATEWIDEN_V3` | WIN | **1.21** | **3** | **1.4823** | −18.4% | qua long |
| 8 | **DCA_MORELEGS_V4** | `RESULT_DCA_MORELEGS_V4` | WIN | **1.21** | **8** (PREREG dong 127: "Tong: 8 config") | **2.0393** | **−40.7%** | **qua long (nang nhat)** |
| 9 | **2X_HALFSIZE** | `RESULT_2X_HALFSIZE` | WIN | **1.21** | **3** (V1,V2,V3) | **1.4823** | −18.4% | qua long |
| 10 | **BD_THRESHOLD_FRAGILITY** | `RESULT_BD_THRESHOLD_FRAGILITY` | WIN | **1.21** | **>=4** (thr −0.025/−0.028/…) | **>=1.6651** | −27% | qua long |
| 11 | **BOOKCAP** | `RESULT_BOOKCAP` | WIN | **1.21** (rate) / 1.4823 (CAGR) | **3** (CAP12/CAP16/NOT40) | **1.4823** | −18.4% (rate) | qua long o tang rate |
| 12 | **GATESCALE** | `PREREG_GATESCALE` | WIN | 1.21 (rate) / **1.4823** (CAGR) | **3** (0.80/1.30/1.70) | **1.4823** | 0% o tang CAGR | ✓ dung o CAGR |
| 13 | **B_FOLLOWUP** | `RESULT_B_FOLLOWUP` | WIN | **1.48** | **3** | **1.4823** | ~0% | ✓ **DUNG** |
| 14 | **SL_ADAPTIVE_SWEEP** | `PREREG_SL_ADAPTIVE_SWEEP` | WIN | **1.48** | **3** | **1.4823** | ~0% | ✓ **DUNG** |
| 15 | **FLATGRID** | `RESULT_FLATGRID` | WIN | **1.1774** | **2** (KEEPSCALE/KEEPLEG0) | **1.1774** | 0% | ✓ **DUNG** |
| 16 | **GD92_RECHECK** | `PREREG_GD92_RECHECK` | WIN | **1.1774** | **2** | **1.1774** | 0% | ✓ **DUNG** |
| 17 | **NOBD_READJUDICATE** | `PREREG_NOBD_READJUDICATE` | WIN | **1.1774** | **2** | **1.1774** | 0% | ✓ **DUNG** |
| 18 | **SEL_BIGDOWN** | `RESULT_SEL_BIGDOWN` | VETO | **1.4823** | **3** (DROP/MIX/DROP_TOP8) | **1.4823** | 0% | ✓ **DUNG** |
| 19 | **BD_SIZE_ADAPT** | `RESULT_BD_SIZE_ADAPT` | VETO | **1.4823** | **3** | **1.4823** | 0% | ✓ **DUNG** |
| 20 | **DCA_ROUND_CAP** | `RESULT_DCA_ROUND_CAP` | **VETO** | **1.7936** (`1.21 × 1.4823`) | **3** | **1.4823** | **+21.0%** | **qua chat** ⚠️ |
| 21 | **DCA_AGG_PERCOIN** | `RESULT_DCA_AGG_PERCOIN` | **VETO** | **1.7936** (`1.21 × 1.4823`) | **3** | **1.4823** | **+21.0%** | **qua chat** ⚠️ |
| 22 | **PAIRED_CALIB** | `PAIRED_CALIB` | WIN | **2.35** (`sqrt(2 ln 256)`) | **256** (Sobol wave-1) | **3.3302** | −29.4% | qua long (ghi 2.35 nhung sqrt(2ln256)=3.33) |
| 23 | **D3D4_FILTER_SIM** | `RESULT_D3D4_FILTER_SIM` | WIN | **1.21** | **11** (post-hoc, doc tu ghi "multiplicity 11") | **2.1899** | −44.7% | qua long |
| 24 | **CI_REAUDIT nhom A/B** | `CI_REAUDIT` | phan loai 3-muc | **1.0** (khong inflate) | 16 cap | — | — | co y khong inflate (da ghi ro) |

**8/24 round dung dung he so. 11/24 qua long. 5/24 qua chat.**

---

## 3. TAI TINH VERDICT — 7 RATE DOI TRANG THAI, **0 ROUND DOI VERDICT**

Bang duoi dung cong thuc muc 1.1 tren **CI DA CONG BO**. `F_crit` = he so toi da con giu y nghia.

| round / rate | CI da cong bo | `F` dung | `F_crit` | y nghia o `F` | y nghia o `F` **DUNG** | DOI? |
|---|---|---|---|---|---|---|
| **DCA_SIGNAL_V1** DCA5 `TSloss` (config hon) | [0.150, 3.309] | 1.21 | **1.325** | CO | **KHONG** | **doi** |
| DCA_SIGNAL_V1 DCA8 `TSloss` | [0.487, 3.395] | 1.21 | 1.615 | CO | CO | — |
| DCA_SIGNAL_V1 DCA12 `TSloss` | [0.436, 2.699] | 1.21 | 1.676 | CO | CO | — |
| DCA_SIGNAL_V1 DCA8 `win` (T170 hon) | [0.582, 4.364] | 1.21 | 1.582 | CO | CO | — |
| **V4** DS_GS085 `meanP` (T170 hon) | [0.704, 4.433] | 1.21 | **1.667** | CO | **KHONG** | **doi** |
| **V4** DS_K12 `win` (T170 hon) | [2.634, 11.124] | 1.21 | **1.961** | CO | **KHONG** | **doi** |
| **V4** DS_K12 `meanP` (T170 hon) | [0.026, 3.870] | 1.21 | **1.226** | CO | **KHONG** | **doi** |
| **V4** DS_DCA30 `win` (T170 hon) | [0.260, 8.571] | 1.21 | **1.286** | CO | **KHONG** | **doi** |
| V4 DS_GS085 `win` | [5.152, 12.980] | 1.21 | 2.803 | CO | CO | — |
| V4 DS_GS085 `TSloss` | [−11.436, −3.214] | 1.21 | 2.156 | CO | CO | — |
| **2X_HALFSIZE** V3 `TSloss` (XAU) | [0.41, 4.31] | 1.21 | **1.464** | CO | **KHONG** | **doi** |
| 2X_HALFSIZE V3 `meanP` (XAU) | [−1.57, −0.25] | 1.21 | 1.668 | CO | CO | — |
| **GATEWIDEN_V3** c3 `meanP` (T170 hon) | [0.059, 2.019] | 1.21 | **1.283** | CO | **KHONG** | **doi** |
| GATEWIDEN_V3 c3 `win` (T170 hon) | [2.693, 7.405] | 1.21 | 2.593 | CO | CO | — |
| **K_DENSITY** K12 `TSloss` (XAU) | [0.487, 2.705] | 1.21 | 1.741 | CO | CO (1.177) | — |
| **5MGRID** `win` (XAU) | [−3.856, −0.263] | 1.21 | 1.387 | CO | CO (1.000) | — |
| **5MGRID** `TSloss` (XAU) | [0.269, 3.592] | 1.21 | 1.406 | CO | CO (1.000) | — |
| **REGIME** `win` (T170 hon) | [0.55, 5.60] | 1.21 | 1.474 | CO | CO (1.000) | — |
| **REGIME** `TSloss` (T170 hon) | [−6.64, −1.49] | 1.21 | 1.910 | CO | CO | — |
| **REGIME** `meanP` (T170 hon) | [0.29, 2.05] | 1.21 | 1.609 | CO | CO | — |
| **T170 readjud** `win` @1.177 | [+0.051, +7.965] | 1.177 | 1.192 | CO | CO | — |

### 3.1 Vi sao **KHONG round nao doi verdict**

7 rate doi trang thai, phan theo 3 nhom — **khong nhom nao tao ra mot nguoi thang moi**:

1. **6/7 rate la rate ma BASELINE dang thang** (V4 x4, GATEWIDEN x1, DCA_SIGNAL_V1 DCA5 TSloss la
   rate *config* thang nhung config do van 0 rate TOT o tieu chi cuoi). Mat y nghia o day chi lam
   **baseline thang bot ro rang**, khong lam config nao dat nguong ">= 2 rate TOT".
   - V4: ca 8 config van **0 rate TOT ngoai CI** (cot cuoi bang V4 = 0 cho tat ca). Verdict NULL giu.
   - GATEWIDEN_V3: 3 config van NULL — va ly do loai chinh la **UW=221 > tran 120**, khong phai CI.
2. **1/7 la rate XAU** (2X V3 `TSloss`): so rate XAU cua V3 tut **2 → 1**. Nhung 2X bi loai vi
   **CAGR tut 5–8pp + UW no 92→221–223 vi pham tran 120**. Verdict NULL giu.
3. **T170 (round quan trong nhat) khong doi**: da duoc re-score doc lap o
   `AUDIT_READJUDICATE_CI_RESCORE` — o he so DUNG `1.1774` (k=2) T170 co **3** rate ngoai CI
   (nhieu hon 2 rate da bao cao o 1.21) => **T170 THANG ro hon ban goc**. Xac nhan lai bang cong
   thuc muc 1.1: `win` CI [+0.051,+7.965] co `F_crit = 1.192 > 1.177` — con y nghia, sat nguong.

> ⚠️ **Do nhay cua T170**: `F_crit(win) = 1.192`. Neu ai do lap luan `k=3` (1.4823) thi T170 tut
> xuong 1 rate; `k=4` (1.6651) tut 0 rate. `AUDIT_READJUDICATE_CI_RESCORE` muc 5 da ghi canh bao
> nay va ghi ro: ke ca khi do, **quay ve T100 cung khong hop le vi T100 tu vi pham rang buoc cung
> 2/5 nam**. Audit nay khong thay doi ket luan do.

---

## 4. HAI CASE PnL MASTER HOI RIENG

| case | he so dung | `k` | he so DUNG | verdict cu | verdict sau hieu chinh |
|---|---|---|---|---|---|
| **SEL_BIGDOWN / DROP** (equity +28%, CAGR +7.30pp) | **1.4823** | 3 | **1.4823** | NULL | **KHONG DOI** — he so da DUNG san |
| **DCA_ROUND_CAP / LOOSE** (CAGR +3.26pp, maxDD tot hon) | **1.7936** ⚠️ | 3 | **1.4823** | PRIMARY PASS, bi veto tap trung | **KHONG THE TAI TINH** — xem muc 5 |

**SEL_BIGDOWN:** he so da dung chuan. Doc ghi *"Khong bien the nao cham du 1/3 rate ngoai CI (chua
noi 2/3) => khong can noi rong them. Ket luan NULL KHONG phu thuoc he so multiplicity."* Ke ca ha ve
`1.0` (khong inflate) cung khong du: khoang cach tu 0/3 len 2/3 la qua xa. **Nguyen nhan NULL la
n=248 leg + duoi nang, KHONG phai `CI_INFLATE`.** Chuan hoa he so **khong cuu** duoc case nay.

**DCA_ROUND_CAP:** dung `1.7936` = **1.21 × 1.4823** — tuc **nhan CHONG** hang so lich su voi he so
multiplicity (double-inflate). Day la VETO-test, nen he so qua lon = **qua DE qua veto**. Hieu chinh
xuong `1.4823` lam CI **hep lai 21%** => **de xuat hien rate XAU hon** => PRIMARY co the tu PASS
thanh FAIL. **Huong doi la CHAT hon, khong phai long hon** — khong phai rui ro NULL→PASS.

---

## 5. NHUNG GI AUDIT NAY **KHONG** TAI TINH DUOC (can chay lai, Giai doan 2)

| round | ly do | anh huong |
|---|---|---|
| **DCA_ROUND_CAP** | RESULT chi in point-estimate + nhan "(trong CI)", **khong in bien CI** cho `win`/`TSloss` | co the doi PRIMARY PASS → FAIL (chat hon) |
| **DCA_AGG_PERCOIN** | y het tren | y het tren |
| **BD_SIZE_ADAPT** | khong in bien CI; nhung doc tu ghi *"khong bien the nao cham 2/3 rate NGAY CA CHUA ap multiplicity"* => **an toan, khong the doi** | khong |
| **BD_THRESHOLD_FRAGILITY** | khong in bien CI + `k` khong khai bao ro | chua ro |
| **BOOKCAP / D3D4 / PAIRED_CALIB** | in mot phan; `k` post-hoc, dinh nghia khac | chua ro |

Cach xu ly da co san: `research/analysis/readjud_rescore.py` (da dung cho T170) doc lai
`printDone.csv` cu + chay lai bootstrap, **khong can chay sim**. Chi can mo rong tag list.

---

## 6. BA LOI HE THONG VE DINH NGHIA `k` (cau hoi 5 cua MASTER)

**Dinh nghia `k` KHONG nhat quan giua cac round.** Ba kieu dem khac nhau cung ton tai:

1. **Dem dung = so ung vien trong round** (chuan) — DEV2021_READJUDICATE (k=2), SEL_BIGDOWN (k=3),
   V4 (k=8), REGIME (k=1). ✓
2. **Khong dem, chi vien dan hang so** — 5 round (DCA_SIGNAL_GATE V1/V2, GATEWIDEN_V3, 2X_HALFSIZE,
   DCA_SIGNAL_GATE) vien `PREREG_2X_HALFSIZE` muc 5: *"CI khoi-72h x1.21 **da bao k=3 multiplicity**"*.
   **Khang dinh nay SAI ve so hoc**: `sqrt(2 ln 3) = 1.4823 ≠ 1.21`. `1.21` chi bao duoc `k=2.08`.
   Day la nguon goc cua 5/11 round "qua long" — mot **loi truyen ngon** tu mot doc sang doc khac.
3. **Nhan chong hang so voi he so** — DCA_ROUND_CAP + DCA_AGG_PERCOIN: `1.21 × 1.4823 = 1.7936`.
   Hieu nham `1.21` la "he so nen" roi nhan them multiplicity. Double-counting.

**Ngoai ra, mot tranh chap ve PHAM VI `k` da duoc ghi nhan** (`AUDIT_READJUDICATE_CI_RESCORE` muc 5.2):
`sqrt(2 ln k)` chi hieu chinh **trong mot round**; toan chuong trinh da chay rat nhieu round
(GATESCALE, GATEDYN, REGIME, V1–V4, K_DENSITY…) nen "garden of forking paths" cap chuong trinh lon
hon nhieu. Audit nay **khong** giai quyet van de do — no chi chuan hoa tang round.

---

## 7. KHUYEN NGHI CHO GIAI DOAN 2 (de xuat, **chua lam**)

1. Tham so hoa: `c3_rates.CI_INFLATE` -> ham `inflate(k) = sqrt(2*ln k) if k>1 else 1.0`, `k`
   truyen tu CLI, **bat buoc**, khong co default — de khong ai vo tinh dung lai `1.21`.
2. Ghi `k` + he so vao header output de moi RESULT doc tu mang bang chung.
3. Bat buoc RESULT doc **in bien CI day du** cho moi rate (khong dung "(trong CI)") — de moi audit
   sau nay tai tinh duoc bang so hoc, khong phai chay lai.
4. Chay lai `readjud_rescore` cho 2 round o muc 5 (DCA_ROUND_CAP, DCA_AGG_PERCOIN).
5. **Khong hoi to doi verdict nao** — audit nay cho thay khong can.

---

## 8. KY LUAT

- KHONG chay sim, KHONG sua `.py`/`.java`, KHONG doi verdict nao.
- KHONG 242, KHONG `git push`, holdout 2026 nguyen ven.

---

# PHU LUC — GIAI DOAN 2 (2026-09-17): FIX SCRIPT + RESCORE 2 ROUND

> Duyet boi MASTER sau khi doc Giai doan 1. **Khong chay sim moi** — chi doc lai `printDone.csv`
> da co va chay lai bootstrap voi he so DUNG. Khong hoi to verdict cua 22 round con lai.

## B.1 Thay doi script

| file | thay doi |
|---|---|
| `research/analysis/c3_rates.py` | **go `CI_INFLATE = 1.21`**; them `inflate(k)` (`k=1 -> 1.0`, `k>=2 -> sqrt(2 ln k)`, `k` BAT BUOC, nem `ValueError` neu `None`); them `LEGACY_CI_INFLATE = 1.21` (CHI de tai lap nguyen van doc cu); them module `__getattr__` **nem `AttributeError` co huong dan** khi ai do truy cap `CI_INFLATE` |
| `research/analysis/x1_rates.py` | `--k` **BAT BUOC** (khong default, thieu thi `SystemExit` kem huong dan); `F_INFLATE` dat mot lan o `main()`; **header in `k` + he so + block/nrep/seed**; guard `RuntimeError` neu goi `ci_pair_df` ma chua dat he so. (Bang CI cua `x1_rates` von **da in day du `lo`/`hi`** — giu nguyen.) |
| `research/analysis/dca_round_cap_score.py` | `CI_TOTAL = C.inflate(3)` thay `C.CI_INFLATE * sqrt(2 ln 3)` (**bo nhan chong**); header in `k` + he so + ghi chu ban cu 1.7936 |
| `research/analysis/dca_agg_percoin_score.py` | y het tren |

**KHONG doi**: `BLOCK_H=72`, `NREP=2000`, `SEED=20260905`, cong thuc bootstrap, `rates()`, percentile 2.5/97.5.

**CO Y KHONG patch**: `x2_rates.py`, `x3_rates.py`, `x4_rates.py` (round X2/X3/X4 da dong). Chung
tham chieu `C.CI_INFLATE` nen **tu nem `AttributeError` kem huong dan** — day la hanh vi an toan
mong muon (fail LOUD, khong am tham dung so sai). Bon script chan doan co hang so `CI_INFLATE=1.21`
RIENG (`postpump_measure.py`, `pumpdump_detect.py`, `pumpdump_ohlcv.py`, `trend_rank_ic.py`)
**khong bi dong** — chung la cong cu DO (rank-IC), khong phai bo cham verdict; sua se lam doi so
da cong bo ma khong co mandate.

**Da co san tu truoc**: `research/analysis/score_k.py` von **da dung chuan** (`--k` bat buoc,
`sqrt(2 ln k)`, in day du `lo`/`hi`). Giai doan 2 nay dua `x1_rates` ve cung chuan voi no.

## B.2 RESCORE — **CA 2 ROUND DOI TU PRIMARY PASS SANG PRIMARY FAIL**

He so cu `1.7936` (= `1.21 × 1.4823`, nhan chong) -> he so dung **`1.482304`** (k=3).
CI **hep lai 21%** => nhieu rate vuot ra ngoai CI hon => **VETO-test CHAT hon**.

### DCA_ROUND_CAP (`X1_GS_T170_2021` = baseline)

| variant | `win%` hieu | CI95 @1.4823 | ngoai CI | rate XAU | PRIMARY cu | **PRIMARY moi** |
|---|---|---|---|---|---|---|
| `CAP10` | 0.000 | [0.000, 0.000] | - | 0 | PASS | PASS (byte-identical, no-op) |
| **`CAP10_LOOSE`** | **−1.327** | **[−2.424, −0.042]** | **YES** | **1** | PASS | **FAIL** |
| **`LOOSE`** | **−1.390** | **[−2.487, −0.116]** | **YES** | **1** | PASS | **FAIL** |

Cac rate khac cua ca hai variant van TRONG CI: `tsloss` +0.335 [−1.225,+2.087] / +0.232
[−1.322,+1.970]; `mp_sm` +0.562 [−0.252,+1.295] / +0.483 [−0.331,+1.217]; `meanP` +0.834
[−0.179,+1.765] / +0.860 [−0.142,+1.779]. `mp_sl` cua `LOOSE` +4.835 [+0.138,+9.556] ngoai CI
nhung **huong TOT** (khong phai XAU).

### DCA_AGG_PERCOIN (`X1_GS_T170_2021` = baseline)

| variant | `win%` hieu | CI95 @1.4823 | ngoai CI | rate XAU | PRIMARY cu | **PRIMARY moi** |
|---|---|---|---|---|---|---|
| **`LOOSE_AGG30`** | **−1.390** | **[−2.487, −0.116]** | **YES** | **1** | PASS | **FAIL** |
| **`LOOSE_AGG30_PC15`** | **−1.327** | **[−2.424, −0.042]** | **YES** | **1** | PASS | **FAIL** |
| **`LOOSE_PC15`** | **−1.327** | **[−2.424, −0.042]** | **YES** | **1** | PASS | **FAIL** |

### B.2.1 Doc ket qua

- **Huong doi dung nhu Giai doan 1 du bao: CHAT hon, KHONG phai NULL→PASS.** Khong co case nao
  "duoc cuu" boi viec chuan hoa.
- Rate bat duoc la **`win%` giam ~1.3–1.4pp** — noi nguong DCA **lam ti le lenh thang giam co y
  nghia thong ke**. O he so cu (qua rong) dieu nay bi che khuat.
- Ca hai round truoc day da bi loai boi **chan tap trung** (`max1coin` 12.51%/17.15% > parity 9.77%).
  Nay chung **con truot them ca PRIMARY**. => **Ket luan loai bo cua hai round duoc CUNG CO, khong
  phai dao nguoc.**
- Rieng `LOOSE` con **VUOT co che**: `max_round_margin` 15,085 = **11.52% equity > tran 10%**
  (ban cu ghi nhan roi).
- `CAP10` van la no-op byte-identical (mo ta cu dung).

### B.2.2 He qua cho cau hoi "co mo lai case nay khong"

Con so PnL hap dan cua `LOOSE` (CAGR 29.27→32.53, equity +11.9%, maxDD −11.84→−9.64) **van dung**
— nhung nay no di kem **mot rate chat luong XAU co y nghia thong ke** (`win%` −1.39pp), **tang tap
trung 1 coin len 17.15%**, va **vuot tran co che 10%**. Tuc day **khong** phai "so dep bi luat qua
chat vui dap" — no la mot danh doi THAT: nhieu lenh hon, moi lenh te hon, rui ro tap trung cao hon.
Day la du lieu cho MASTER quyet, khong phai khuyen nghi.

## B.3 Dinh chinh dong sai da lan truyen

`docs/PREREG_2X_HALFSIZE.md` muc 5 — **KHONG xoa, KHONG viet lai**. Da chen mot khoi
`> **[DINH CHINH 2026-09-17]**` ngay duoi tieu de muc, ghi ro: cau "x1.21 da bao k=3 multiplicity"
sai ve so hoc, he so dung cho k=3 la 1.4823, dong nay da lan sang 4 pre-reg khac, va **khong round
nao doi verdict**. Phan con lai cua tai lieu giu nguyen.

## B.4 Artifact

| | |
|---|---|
| Output rescore | `/tmp/rc_new.txt` (DCA_ROUND_CAP), `/tmp/agg_new.txt` (DCA_AGG_PERCOIN) tren Oracle |
| Tag da dung | `X1_GS_T170_2021` (baseline) + `_CAP10` / `_CAP10_LOOSE` / `_LOOSE` / `_LOOSE_AGG30` / `_LOOSE_AGG30_PC15` / `_LOOSE_PC15` |
| Khong chay sim | moi `printDone.csv` la ban cu, khong sinh lai |
| Kiem tra guard | `c3_rates.CI_INFLATE` -> `AttributeError` (da verify); `inflate(1/2/3/8)` = 1.0 / 1.177410 / 1.482304 / 2.039334 (da verify) |
