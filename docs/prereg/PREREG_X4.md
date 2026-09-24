# PREREG_X4 - CHOT cau hinh TRAILING tren DEV 48 thang

Viet va commit **TRUOC** khi chay. Khong sua sau khi thay so.
Nen: `X1_C3` (= `c3_min` + bins X1), cua so **2022-01-01 -> 2025-12-31**, `SIM_END_DATE=20251231`,
bins `predwf_map_s1a2_x1` (`binsSha256=b8776231...`), jar X3 `01ca3461fb98f5c78e0a98055c5fe948`
(cac key X3 mac dinh TAT). **KHONG cham holdout 2026, khong `HOLDOUT_UNSEAL`.**

---

## 0. RUI RO / GIOI HAN - doc TRUOC

1. **Day la buoc CHOT, co chon** - khac X2/X3 (kham pha). Rui ro lon nhat la **chon theo nhieu**:
   N=10 => `E[max nhieu]` = `2.57 x sqrt(2 ln 10)` = **5.5pp CAGR**. Vi vay equity **KHONG duoc dung
   de chon**; tieu chi la rate + CI khoi-72h x1.21.
2. **Truc G (`SIM_TS_MAX_GAP`) va H (`SIM_TS_PNOPUMP_WEAK_THR`) tung la KEY CHET** (`W1` muc 3/4:
   5/5 run byte-identical parity) vi truoc B1 `mergeOrder` khong chep `symbolPred` => `pnp = 1f`
   => 100% WEAK. Sau B1 hai key nay **moi song**. Bat buoc kiem CO HOC truoc khi doc ket qua
   (muc 3) - `DumpConfig` doi gia tri la **CHUA DU**, day dung la cai bay da lam W1 mat 5 run.
3. **X3 da dong truc "ai duoc cap nao"** (rank selector: NULL, va ly do co hoc - khong ton tai
   gradient chat luong theo rank). X4 hoi cau khac han: **cap la BAO NHIEU**.
4. **UW (underwater) KHONG con la rang buoc cung trong dot nay** - X3 muc 6.1 do duoc `X3_R6`
   khong phan biet duoc voi PARITY o MOI rate muc lenh (0/8 ngoai CI, `n` va `win%` giong het)
   nhung `UW 2022` nhay 64 -> 159 ngay. UW ghi lai lam **chi bao**, khong loai arm.
5. **Khong tune sau khi thay so.** Grid dong o 9 bien the + 1 parity; chi duoc them **DUNG 1**
   run to hop neu >= 2 truc doi (muc 6.4), da dang ky truoc la **run 11**.

---

## 1. CO CHE dang chay (sau B1) - phai hieu dung truoc khi quet

`OrderTargetInfoTest.trailRate()` -> `TradeUtils`:

```java
pnp    = (symbolPred != null) ? symbolPred : 1f;         // null -> coi nhu YEU
maxGap = (pnp > TS_PNOPUMP_WEAK_THR) ? TS_MAX_GAP_WEAK : TS_MAX_GAP;
gap    = min(maxProfitRate * TS_GIVEBACK_RATIO, maxGap);
rate   = round((maxProfitRate - gap) / 0.005) * 0.005;
```

Arm o `+7%` (`SIM_RATE_PROFIT_STOP_MARKET=0.07`). **Trailing chi chay SAU arm.**
Bon hang so `0.08 / 0.03 / 0.5` va ban le `0.29` **chua bao gio duoc quet tren jar sach**.

Duong doc cau hinh (da `grep` xac nhan trong `Configs.java`):

| key profile | field Java | noi doc |
|---|---|---|
| `SIM_TS_MAX_GAP` | `TS_MAX_GAP` | `Configs.java:501` (static block SIM override) |
| `SIM_TS_MAX_GAP_WEAK` | `TS_MAX_GAP_WEAK` | `Configs.java:502` |
| `SIM_TS_PNOPUMP_WEAK_THR` | `TS_PNOPUMP_WEAK_THR_OVR` -> `tsPnoPumpWeakThr()` | `Configs.java:498` |
| `TS_GIVEBACK_RATIO` (KHONG co tien to `SIM_`) | `TS_GIVEBACK_RATIO` | `Configs.java:173` |

---

## 2. GRID - one-at-a-time, moi muc = mot profile copy

Moi profile = `profiles/x1_c3.properties` doi **DUNG mot dong** (truc U doi hai dong).

| truc | key | muc | tag |
|---|---|---|---|
| - | (khong doi) | base | `X4_PARITY` |
| **G** | `SIM_TS_MAX_GAP` | 0.05 / **0.08** / 0.12 | `X4_G05`, `X4_G12` |
| **W** | `SIM_TS_MAX_GAP_WEAK` | 0.015 / **0.03** / 0.05 | `X4_W015`, `X4_W05` |
| **R** | `TS_GIVEBACK_RATIO` | 0.3 / **0.5** / 0.7 | `X4_R03`, `X4_R07` |
| **H** | `SIM_TS_PNOPUMP_WEAK_THR` | 0.20 / **0.29** / 0.40 | `X4_H20`, `X4_H40` |
| **U** | `SIM_TS_MAX_GAP` = `SIM_TS_MAX_GAP_WEAK` = 0.05 | (ban le vo hieu) | `X4_U05` |

= **9 bien the + 1 parity = 10 run.** Thu tu chay: `PARITY, G05, H20, G12, H40, W015, W05, R03, R07, U05`
(hai truc "tung chet" G/H chay som nhat de phat hien key chet trong 2 run dau).

---

## 3. CONG CO HOC - phai PASS truoc khi doc bat ky ket qua nao

| cong | tieu chi | hanh dong neu FAIL |
|---|---|---|
| **C1 parity** | `X4_PARITY` md5 `printDone.csv` = **`d39da2940dfd815f60772f70517750bf`** (= `X1_C3` = `X3_PARITY`), `n` = 2,058, `b:98523` | `exit 9`, khong chay arm nao |
| **C2 key song** | md5 cua **moi** arm **KHAC** parity | arm nao trung parity = **KEY CHET** tren truc do -> bao null CO HOC, khong doc rate |
| **C3 DumpConfig** | 4 key doi duoc gia tri hieu dung khi doc tu profile | dung, tim duong doc |
| **C4 TSloss bat bien** | `n STOP_LOSS_DONE` cua **moi** arm = **306** (= parity) | **DUNG va tim bug** - trailing chi tac dong sau arm, dieu kien arm khong phu thuoc cap |

C4 la phep kiem manh nhat cua dot nay: X3 da do `n_SL = 306` giong het o ca 4 arm. Neu X4 lam
doi con so nay thi mot trong hai gia dinh co hoc ("trailing chi sau arm" / "arm khong phu thuoc cap")
sai, va toan bo bang so mat nghia.

**KHONG sua engine trong dot nay.** Jar giu nguyen `01ca3461...` cua X3 => cong hoi quy C1 duoc
thua ke nguyen ven. Nhanh STRONG/WEAK duoc suy **CHINH XAC** tu `printDone.csv`
(`STRONG <=> symbolPred_leg1 <= thr_cua_arm`, `null -> WEAK`), dung dung boolean ma engine tinh -
khong can them dong log SLF4J, va do la ly do KHONG phai rebuild jar. Kiem chung: cach suy nay
tai lap **83.8% STRONG** cua `X3_PARITY` (`docs/experiment/X3_RANKCAP_SL50.md` muc 3).

---

## 4. TIEU CHI PRIMARY (rate, khong phai equity)

Do tren **toan 48 thang** VA **tung nam**:

1. Phan bo `profit | STOP_MARKET_DONE`: `p10 / p25 / med / p75 / p90 / **mean**`, va `sum(pnl | SM)`.
2. `win%`.
3. `TSloss%` va `n STOP_LOSS_DONE` (cong C4 - **phai KHONG doi**).
4. `mean(profit | STOP_LOSS_DONE)`, `p10 loser`.
5. Tach **STRONG / WEAK**: `n` va `mean(profit)` tung nhanh (ban le cua chinh arm do).

CI: **block-72h bootstrap paired, 2000 rep, x1.21, seed 20260905**, luoi khoi CHUNG neo o
`2022-01-01` (giong `x3_rates.py`). "Ngoai CI" = CI cua hieu `arm - PARITY` khong chua 0.

---

## 5. RANG BUOC CUNG (theo NAM)

- **R1** `maxDD <= 15%` tung nam.
- **R2** khong nam am.
- **R3** khong quy < `-5%`.
- **(chi bao, KHONG loai)** UW tung nam - ghi lai de user quyet (muc 0.4).

---

## 6. QUY TAC QUYET DINH - chot TRUOC khi thay so

1. Voi moi truc, xet `mean(profit|SM)` co **don dieu** theo muc khong (3 diem: thap / base / cao).
   Truc **khong don dieu** => **giu base** cho truc do.
2. Truc don dieu: chon muc co `mean(profit|SM)` **cao nhat** ma `win%` **khong giam ngoai CI**
   VA **PASS R1-R3**.
3. Truc **U**: neu `|mean(profit|SM)_U - mean(profit|SM)_base|` **nam trong CI** => ban le 0.29
   **VO DUNG** => **khuyen nghi U** (mot cap duy nhat, it tham so hon). **Don gian thang khi hoa.**
4. Cau hinh CHOT = base + cac truc co thay doi theo (2). **Neu >= 2 truc doi thi chay them DUNG
   MOT run to hop** (`X4_COMBO`, dang ky truoc la **run 11**) de xac nhan khong tuong tac xau;
   neu `X4_COMBO` xau hon tong hop cac truc rieng le o `mean(profit|SM)` ngoai CI, **giu base**.
5. Neu khong truc nao doi => ghi **"trailing DONG, base giu"**.

Equity/CAGR bao rieng, **dan nhan "khong phai tieu chi"** (N=10 => 5.5pp).

---

## 7. DU DOAN GHI TRUOC

### 7.1 Du doan cua MASTER (nguyen van, phai kiem)

> "Toi (master) du doan **moi truc deu khong don dieu** va **U hoa** - 'doi hinh dang, tong khong
> doi' vi `exit = peak - min(peak*r, cap)` la so hoc tren phan bo `peak` do thi truong quyet."

### 7.2 Du doan cua agent thuc thi (dinh luong, de doi chieu)

| do | du doan | xac suat |
|---|---|---|
| Cong C4 (`n_SL` = 306 o ca 10 run) | PASS | 90% |
| Truc G don dieu tren `mean\|SM)` | KHONG | 70% |
| Truc W don dieu tren `mean\|SM)` | KHONG (W1 truc B da null tren engine cu, 0/7 rate don dieu) | 75% |
| Truc R don dieu tren `mean\|SM)` | KHONG | 65% |
| Truc H don dieu tren `mean\|SM)` | KHONG | 70% |
| `med(profit\|SM)` giam don dieu khi noi cap (G va W) | **CO** (so hoc: cap chat => chot sat dinh) | 80% |
| `p90(profit\|SM)` tang don dieu khi noi cap | CO | 60% |
| `X4_U05` khac `PARITY` ngoai CI o `mean\|SM)` | KHONG (hoa) | 70% |
| Ket cuc: **base giu nguyen** (khong truc nao doi) | 55% |
| Ket cuc: dung 1 truc doi | 30% |
| Ket cuc: >= 2 truc doi (phai chay `X4_COMBO`) | 15% |

**Co so cua du doan**: `C3_BASELINE` muc 4 va `X3` muc 4 da do **hai lan** rang doi cap chi lam
**doi hinh dang** phan bo winner (than <-> duoi phai) chu khong doi `mean`: B1 (them STRONG) cho
`mean|SM` -0.024pp; `X3_R2` (bot STRONG) cho -0.097pp. Ca hai deu trong CI. `mean` la dai luong
**bao toan** duoi phep bien doi nay vi `peak` do thi truong quyet, cap chi quyet **cat o dau tren
mot duong peak da co san**.

Nhung co MOT ly do de van phai quet: cac phep do tren deu o **quanh base** (0.08/0.03). Truc R
(`TS_GIVEBACK_RATIO`) **chua bao gio duoc quet mot lan nao** ke ca tren engine cu, va no la tham so
duy nhat tac dong len CA HAI nhanh dong thoi (no nhan vao `peak`, khong phai hang so cap).

---

## 8. DUONG CHAY

Oracle tuan tu (`TICKER_SOURCE=file`, ~12.9 phut/run) hoac Kaggle 5 slot song song.
Quyet dinh do bang so, ghi vao bao cao: `docs/experiment/X3_RANKCAP_SL50.md` muc 11 da do
**upload 5.32 GB @ 3.23 MB/s = 27.5 phut** va bundle `sim-c2b-bundle` **chua bao gio duoc
version cho cua so 48 thang** (`funding.bin` hien tai la ban 30 thang, 1.83 GB).

---

## 9. CAM

- Khong `SIM_END_DATE` > `20251231`, khong `HOLDOUT_UNSEAL`.
- Khong push. Commit branch `module`.
- Khong them muc ngoai grid (+ toi da 1 run to hop da dang ky).
- Khong sua pre-reg nay sau khi thay so.
- Python `logging`, Java SLF4J. Khong `print()`.
