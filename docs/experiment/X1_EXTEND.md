# X1_EXTEND — keo dai cua so do tu 30 thang len 48 thang (2022-01 -> 2025-12)

Pre-reg: `docs/prereg/PREREG_X1.md` (commit `91d7b93`), viet va commit TRUOC khi chay bat ky thu gi.
Nhiem vu: `n_eff ~ 908` khoi 72h la tuong chan moi ket luan; chi DO DAI LICH SU mua duoc power.
Hai the cho phan biet: `C3` (68,278 / 30.76% / maxDD -13.31 / UW 96 / 961 lenh) va
`C3_FULL` (72,699 / 34.10% / -12.46 / 81 / 1,059 lenh).

---

## 0. RUI RO — doc TRUOC

1. 🔴 **Sau X1 khong con holdout nao trong 2021-2025.** Chi con 2026 (`HoldoutSeal`, du lieu
   pred/gate 2026 da bi xoa khoi Oracle). Validate cuoi cung = forward test that.
2. 🔴 **Bins nguon van la `predwf_G015x26` — bo bins KHONG tai lap duoc.** X1 khong sua duoc
   no ky thuat nay; xem muc 2.2. Doi sang `predwf_G015_v2` se lam `C3` doi so va mat neo.
3. 🔴 **Chan B (2021H2) BI BO.** Ly do cung, khong phai "kho" — xem muc 1.2.
4. ⚠️ Dia Oracle 93% day. Dataset WFO cua X1 (~4G) phai xoa ngay sau khi chay xong 2 arm.

---

## 1. §1 AUDIT DU LIEU — chan B di/khong

### 1.1 Chan F (2024-07 -> 2025-12): **DI DUOC. Khong co blocker.**

Blocker kha di nhat ma de bai neu ra (`wfo_gate_pred.csv` va Tool1 f0..f39) **deu khong phai
blocker** — nhung `wfo_gate_pred.csv` dung **vua khit**:

| dau vao | do thuc | ket luan |
|---|---|---|
| `claudedata/wfo_gate_pred.csv` (p15) | 2021-03-31 17:00 -> **2025-12-31 23:59**, 2,500,260 dong (phut) | **vua du, het mep** — khong the di xa hon 2025-12-31 |
| Aerospike `test/ai_pred_market_gate_wfo` | 2,500,260 object = **cung mep** | vua du |
| Tool1 `f0..f39` = `ds_feat15m/features_*.t1c.gz` (FILE tren dia, khong phai Aerospike) | 2021-01 -> **2026-07**, 23 file | du |
| `label_15m/funding_label_*.pb` | 2021-01 -> **2026-10**, 24 file | du |
| `claudedata/oi/oi_percoin_full.bin` | 2021-01-01 -> **2026-06-30**, 140,924,110 rec | du |
| `java/fsrun/CLOSES_1H.bin` | 2021-01-01 01:00 -> **2026-01-01 00:00**, 10,322,386 rec | **vua du** |
| `claudedata/predwf_G015x26/` | **16 fold** `20220101`..`20251001`, ts 2021-12-31 17:00 -> **2025-12-31 16:45** (+7) | du, dung 16 quarter |
| ticker `kaggle_data_hpo/daily/` | 2,008 file 2021-01-01..2026-07-01; **1,461/1,461 ngay** cua 2022-01-01..2025-12-31 | du, khong thieu ngay |
| `selector_pred_out/symbol_map.csv` (781 sym) | phu **554/554** symbol trong bins 2025Q4 va **554/554** trong label 2025Q4 | du (khong can regenerate) |
| `java/exchange_info_pin.json` | 892 symbol, dump tu `ClientSingleton` (2026-09-03) | **khong can regenerate** |
| `HoldoutSeal.SEAL_MS` | 2026-01-01 | `SIM_END_DATE=20251231` **duoi seal**, khong can `HOLDOUT_UNSEAL` |

**Ba artifact trung gian bi ghim tai 2024-07-01 => PHAI rebuild** (day moi la cong viec that):

| artifact | mep cu | X1 |
|---|---|---|
| `featv2/feat_v2.parquet` | `T_END` 2024-07-01, 4,884,420 dong | `feat_v2_x1.parquet` toi 2026-01-01, **10,265,224 dong** |
| `ledger/cand_dev.parquet` | `T1` 2024-07-01, 1,220,490 dong | `cand_dev_x1.parquet`, **7,020,129 dong**, 21,396 tick |
| `pred_s1a2.parquet` + `predwf_map_s1a2/` | 10 fold | `pred_s1a2x1` + `predwf_map_s1a2_x1/` 16 fold |

Ngoai ra `ledger.py` co mot bay im lang: glob nhan `funding_label_202[1-4]*.pb` — **khong khop
2025**. Neu chay nguyen ban voi `T1=2026-01-01` thi ledger se lang le thieu toan bo 2025 ma
khong bao loi. Da tham so hoa (`X1_LBGLOB`).

### 1.2 Chan B (2021-07 -> 2021-12): **KHONG DI**

Ly do quyet dinh (khong phai "kho", ma **loai tru nhau ve logic**):

Recipe `D1_DATA_AUDIT §B` doi **cat 2 OI feature khoi `KEEP` cua `s1_rank.py`** (9 -> 7) vi OI
chi co 1 coin/thang toi 2021-11. Nhung `KEEP` la tham so **TOAN CUC**: doi no thi **MOI fold
doi**, ke ca 10 fold 2022-2024.

=> bins `predwf_map_s1a2` fold cu khong con byte-identical
=> **cong parity noi bo (X1_C3 cat toi 2024-06-30 == C3 = 68,278 / 961) FAIL theo dinh nghia**
=> so 2022-2024 moi khong con so sanh duoc voi `C3`/`C3_FULL`.

Tuc: **hoac co chan B (7 feature), hoac giu duoc neo C3 (9 feature). Khong the ca hai.**
Vi nhiem vu la PHAN BIET C3 vs C3_FULL, neo C3 la thu khong duoc mat.

Hai ly do phu, deu la so do thuc:

- **G015 co 5 OI feature, va OI thuc su bat dau 2021-12** (`D1 §A.5`: 242 cung khong co
  2021-01..2021-11, khong copy ve duoc). Fold `20210701` se train tren ma tran 45 cot voi 5 cot
  ~100% NaN roi cham OOS 2021Q3 cung ~100% NaN. `g72_train.py` khong co xu ly rieng cho NaN —
  no de XGBoost tu hoc huong mac dinh (`merge_asof` tol 2h -> NaN, khong fillna, khong drop).
  XGBoost **chay duoc**, nhung day la **dut gay cau truc ma tran feature**, khong phai dich
  phan bo. Model fold 2021 khong cung ho uoc luong voi 15 fold con lai; xep chung vao mot bang
  "rate theo nam" la sai ve phuong phap.
- Loi ich nho va o cho xau nhat: 6 thang / 54 = 11% do dai, va la 6 thang **it tick nhat**
  (`D1 §B.0`: ledger 2021-07 chi 13,200 dong, 2021-08 10,163 — so voi hang tram nghin tu 2022).

**=> Cua so X1 = 48 thang (2022-01-01 -> 2025-12-31), khong phai 54.**

### 1.3 Hai sai lech co y so voi de bai (ghi ro, khong giau)

**(a) Nguon bins = `predwf_G015x26`, KHONG phai `predwf_G015_v2`.**
De bai yeu cau bins moi sinh tu `g72_train.py`. Nhung `build_map.py` doc `predwf_G015x26`, va
bins dang deploy (`predwf_map_s1a2`, sinh ra `C3` = 68,278) chinh la **S1-rank ap len phan phoi
P(win) cua G015x26** — do thuc: so ban ghi va kich thuoc tung file cua `predwf_map_s1a2` trung
khop tuyet doi `predwf_G015x26`. Doi nguon sang G015_v2 => 10 bins fold cu doi => cong
byte-identical FAIL => mat neo C3.
=> X1 dung G015x26 cho **ca 16 fold** (nhat quan fold cu/moi, giu duoc ca hai cong).
=> **No ky thuat**: G015x26 khong tai lap duoc (`docs/result/G015CUT_RESULT.md`). Chuyen sang G015_v2
la mot job RIENG, phai do lai toan bo baseline. `g72_train.py` **khong duoc dung trong X1** —
nguoi doc sau khong duoc tuong X1 da tai lap G015.

**(b) 2 arm chay TUAN TU tren Oracle voi `TICKER_SOURCE=file`, khong phai song song Kaggle.**
`KAGGLE_SIM §6`: bins **khong di qua duong Kaggle** — kernel chi chay sim tren dataset DA BUILD.
Duong Kaggle se phai upload dataset moi (~4G) + ticker 2024h2/2025 (~3.6G) = ~7.8G bang thong
de doi ~15 phut wall-clock. `KAGGLE_SIM §1` da do thuc **Kaggle == Oracle+`file` byte-for-byte**,
va `C3`/`C3_FULL` deu chay tren Kaggle (duong `file`). Oracle dang rong.
=> chay Oracle + `file` (neo 60395, dung ho voi C3), tiet kiem 7.8G upload.

---

## 2. PROVENANCE + CONG BYTE-IDENTICAL — **4/4 PASS**

Chuoi chay: `research/pipeline/x1/run_x1.sh` (log `/home/ubuntu/x1log/chain.out`), 2026-09-05
20:55 -> 21:10. Moi script X1 la ban SAO tham so hoa qua env cua script goc; mac dinh = hanh vi cu.

| cong | do gi | ket qua |
|---|---|---|
| **G1** `feat_v2_x1.parquet` | 9 cot KEEP cua S1, moi dong `ts <= 2024-07-01` vs `feat_v2.parquet` | **PASS** — dung **4,884,420** dong, bang tuyet doi (`equal_nan`) |
| **G2** `cand_dev_x1.parquet` | moi cot, `ts < T1 cu`, cung thu tu vs `cand_dev.parquet` | **PASS** — dung **1,220,490** dong |
| **G3** `pred_s1a2x1.parquet` | `score` 10 fold cu vs `pred_s1a2.parquet` | **PASS** — dung **774,270** dong, `score` bang tuyet doi |
| **G4** `predwf_map_s1a2_x1/` | sha256 10 bin cu vs `BINS_MANIFEST.md` muc 2 | **PASS** — 10/10 trung (`beb9b1ad…`, `46d74f5a…`, …) |

Diem dang chu y: tong so dong OOS cua 10 fold dau (122,951 + 173,071 + 32,405 + 63,220 + 37,998
+ 13,195 + 8,311 + 30,527 + 203,329 + 89,263) = **774,270**, khop tuyet doi so dong cua
`pred_s1a2.parquet` — nghia la viec mo rong universe (627 cot gia thay vi ~300) va mo rong thoi
gian **khong lam dich mot dong nao** cua qua khu.

Dataset WFO: `manifest.txt` `foldCount=16`, `maxFoldSpanDays=91`, `leakFreeFrom=2022-01-01`,
`binsSha256=b87762312620f31769a8ef0160ec8132a5482c8f235d86e3364b59cce022a862`,
`marketCount=2,554,812` `predCount=2,500,260` `fundingCount=2,043,446`.
`HOLDOUT SEAL` da cat 312,322 ban ghi market >= 2026-01-01 (dung nhu thiet ke).

## 3. CONG PARITY NOI BO — **IDENTICAL, ca hai arm**

| arm | cat `end < 2024-06-30` | tham chieu | ket qua |
|---|---|---|---|
| `X1_C3` | **961** dong | `C3_BASE` 961 dong (md5 `38be0cb3…`) | **IDENTICAL** |
| `X1_C3_FULL` | **1,059** dong | `C3_FULL` 1,059 dong (md5 `85083e46…`) | **IDENTICAL** |

0 lenh bi dong cuong buc tai bien 2024-06-30 o ban tham chieu => tap so sanh la toan bo.
=> Keo dai cua so **khong doi mot lenh nao** cua 30 thang dau. Moi khac biet duoi day la
**thong tin moi**, khong phai nhieu tu viec doi input.

## 4. BANG CHINH — 48 thang (2022-01-01 -> 2025-12-31)

`equity`/`CAGR` **khong phai tieu chi**.

| arm | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `X1_C3` | 2,058 | 85.33 | 14.87 | 7.178 | −21.848 | 2.863 | 1,918 | −13.31 | **302** | 98,523 | 29.58 |
| `X1_C3_FULL` | 2,266 | 84.69 | 14.96 | 7.333 | −19.570 | 3.308 | 1,945 | −12.46 | **227** | 111,428 | 33.63 |

(30 thang cu de doi chieu: `C3` 961 / 85.12 / 15.30 / 7.452 / −18.827 / 3.432 / 1,397 /
−13.31 / 96 / 68,278; `C3_FULL` 1,059 / 84.89 / 15.77 / 7.190 / −16.236 / 3.496 / 1,410 /
−12.46 / 81 / 72,699.)

## 5. RATE THEO NAM

| arm | nam | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin |
|---|---|---|---|---|---|---|---|---|
| `X1_C3` | 2022 | 360 | 83.33 | 16.39 | 6.552 | −22.859 | 1.732 | 892 |
| `X1_C3` | 2023 | 290 | 88.62 | 12.07 | 8.887 | −13.228 | 6.218 | 1,609 |
| `X1_C3` | 2024 | 624 | 85.74 | 15.06 | 7.266 | −15.520 | 3.833 | 1,892 |
| `X1_C3` | **2025** | **784** | **84.69** | **15.05** | 6.738 | **−28.941** | **1.368** | 2,524 |
| `X1_C3_FULL` | 2022 | 406 | 82.27 | 17.00 | 6.240 | −17.534 | 2.200 | 856 |
| `X1_C3_FULL` | 2023 | 308 | 88.64 | 13.64 | 8.487 | −11.463 | 5.767 | 1,688 |
| `X1_C3_FULL` | 2024 | 668 | 86.23 | 14.52 | 7.232 | −15.701 | 3.902 | 1,944 |
| `X1_C3_FULL` | **2025** | **884** | **83.26** | **14.82** | 7.491 | **−26.105** | 2.513 | 2,535 |

### CI khoi-72h x1.21, hieu `X1_C3_FULL − X1_C3`

| pham vi | rate CHAT LUONG ngoai CI (bo `n`, `mMargin`) | chi tiet |
|---|---|---|
| **TOAN 48 thang** | **1** | `mP\|SL` **+2.278** [+0.629, +4.175] |
| 2022 | 0 | rong nhat: `mP\|SL` +5.325 [−0.652, +13.388] |
| 2023 | 0 | (`n` +18 va `mMargin` +79 ngoai CI — bien co hoc) |
| 2024 | 0 | (`n` +44 ngoai CI — bien co hoc) |
| **2025** | **2 nhung NGUOC HUONG** | `win%` **−1.436** [−2.880, −0.013] (FULL **xau hon**) va `mP\|SL` **+2.835** [+0.667, +5.748] (FULL tot hon) |

## 6. DCA THEO NAM — gia thuyet "an FTX mot lan" **BI BAC BO**

| arm | nam | n_leg1 | **n_leg2+** | **pnl_leg2+** | meanP_leg2+ |
|---|---|---|---|---|---|
| `X1_C3` | 2022-2025 | — | **0** | 0 | — (DCA tat, `1,0,0,0`) |
| `X1_C3_FULL` | 2022 | 386 | **20** | **+2,758.3** | +14.28 |
| `X1_C3_FULL` | 2023 | 308 | 0 | 0 | — |
| `X1_C3_FULL` | 2024 | 666 | **2** | **−164.2** | −10.61 |
| `X1_C3_FULL` | **2025** | 852 | **32** | **+4,813.2** | **+23.92** |

=> DCA **KHONG** chi no o quy sap 2022. No no manh hon o 2025 (**32 leg**, PnL **+4,813**,
lon hon ca 2022) — mot regime khac han FTX. **Tieu chi 2 cua quy tac quyet dinh DAT.**

## 7. RANG BUOC CUNG THEO NAM — **CA HAI ARM FAIL 2024 va 2025**

maxDD/UW do tu chuoi equity `b+unP` cuoi ngay, `cummax` **reset dau moi nam**.

| arm | nam | maxDD% | UW (ngay) | ret_nam% | quy_min% | PASS |
|---|---|---|---|---|---|---|
| `X1_C3` | 2022 | −13.31 | 64 | +9.54 | −4.75 | PASS |
| `X1_C3` | 2023 | −2.63 | 57 | +64.26 | +8.32 | PASS |
| `X1_C3` | 2024 | −11.12 | **121** | +42.80 | −4.59 | **FAIL** (UW > 120) |
| `X1_C3` | **2025** | −12.17 | **302** | +9.61 | −2.80 | **FAIL** (UW > 120) |
| `X1_C3_FULL` | 2022 | −12.46 | 64 | +17.30 | +0.63 | PASS |
| `X1_C3_FULL` | 2023 | −2.51 | 45 | +60.43 | +7.80 | PASS |
| `X1_C3_FULL` | 2024 | −11.36 | **121** | +45.36 | −4.64 | **FAIL** (UW > 120) |
| `X1_C3_FULL` | **2025** | −10.60 | **227** | +16.45 | −2.47 | **FAIL** (UW > 120) |

- `maxDD` va "khong nam am" va "khong quy < −5%": **PASS moi nam, ca hai arm**
  (quy xau nhat: `X1_C3` 2022Q4 −4.75, 2024Q2 −4.59; `X1_C3_FULL` 2024Q2 −4.64).
- Cai vo la **UW**: 2024 vuot dung 1 ngay (121); **2025 vuot gap 2.5 lan** (302 / 227).
- 🔴 Nguong `UW <= 120` duoc dat khi chi co 30 thang du lieu, noi UW lon nhat quan sat duoc
  la 96 ngay. Voi 48 thang no **khong con la nguong ma he thong dat duoc** — ke ca baseline
  hien tai. **Bao cao, khong tune.**

## 8. PHAN QUYET

Quy tac chot truoc (`PREREG_X1` muc 6): `C3_FULL` duoc nhan lam baseline **chi khi ca 3 dieu**:

| # | dieu kien | ket qua |
|---|---|---|
| 1 | thang `C3` **>= 2 rate cung huong, ngoai CI**, tren toan cua so | ❌ **KHONG** — dung **1** (`mP\|SL` +2.278) |
| 2 | DCA co PnL leg 2+ **duong o >= 2 nam khac nhau** | ✅ **CO** — 2022 (+2,758 / 20 leg) va 2025 (+4,813 / 32 leg) |
| 3 | PASS rang buoc cung o **moi** nam | ❌ **KHONG** — FAIL UW 2024 (121) va 2025 (227) |

### => **GIU `C3` LAM BASELINE.** `C3_FULL` KHONG duoc nhan.

**Nhung ly do bac bo DA DOI, va phai ghi ro:**

- Gia thuyet cu — *"DCA chi an FTX mot lan"* — **da bi bac bo bang do luong**. DCA no o
  **hai regime cach nhau 3 nam**, va lan 2025 **manh hon** lan 2022 (32 leg vs 20, +4,813 vs
  +2,758). Day la ket qua chinh cua X1 va la thong tin **duong** cho `C3_FULL`.
- Cai chan `C3_FULL` bay gio la **chung co muc RATE con mong** (1/5 rate chat luong ngoai CI,
  y het ket qua 30 thang — CI hep lai nhung hieu ung cung nho lai) va **rang buoc cung UW**,
  ma `C3` **cung vi pham y het**. Tuc dieu kien 3 khong con phan biet duoc hai the.
- Rieng 2025, hai rate ngoai CI **nguoc huong**: `C3_FULL` **thua** ve `win%` (−1.44pp) va
  **thang** ve `mP|SL` (+2.84pp). Do la dung mot danh doi da biet (nhan them lenh xau de
  DCA go lo), khong phai cai tien don huong.
- 🔴 **Khong duoc doc nguoc**: `C3_FULL` co equity cao hon 13% (111,428 vs 98,523) va UW ngan
  hon 75 ngay. Ca hai **khong phai tieu chi** (`sd(dCAGR)`). Neu lan sau ai do nhac
  `C3_FULL` vi so equity, day la cho de doc lai.

**Buoc tiep hop ly (khong lam trong dot nay):** thu nghiem tiep theo cho DCA phai nham vao
`n_eff` chu khong vao equity — hoac cho nhieu leg hon o *cung* muc rui ro, hoac do DCA nhu mot
truc rieng tren 48 thang voi pre-reg 1 rate duy nhat (`mP|SL`) da khai bao truoc.

## 9. EQUITY / CAGR / `n_eff` — bao rieng, **khong phai tieu chi**

| arm | equity cuoi | CAGR% | maxDD% (48t) | UW (48t) |
|---|---|---|---|---|
| `X1_C3` | 98,523 | 29.58 | −13.31 | 302 |
| `X1_C3_FULL` | 111,428 | 33.63 | −12.46 | 227 |

`sd(dCAGR)` cho cua so 48 thang: **khong tim thay so do** — 2.57pp la con so cua cua so 30
thang, **khong duoc tai su dung**. Chua co bo run du lon tren cua so moi de uoc luong lai.

### `n_eff` moi

⚠️ **Dinh chinh don vi**: `n_eff ≈ 908` cua `F4_TIMING` la **muc TICK cua tang gate**
(`n = 86,615` tick -> `n_eff ≈ 908`), **khong phai** don vi cua rate muc lenh. So sanh truc
tiep "167 vs 908" la sai don vi.

Don vi dung cho rate muc lenh = **so khoi 72h CO it nhat 1 lenh** (chinh la don vi ma
bootstrap khoi-72h dang rut):

| arm | cua so | n lenh | ngay | **khoi 72h co lenh** | lenh/khoi |
|---|---|---|---|---|---|
| `C3_BASE` | 30 thang | 961 | 894 | **89** | 10.8 |
| `C3_FULL` | 30 thang | 1,059 | 894 | **93** | 11.4 |
| **`X1_C3`** | **48 thang** | **2,058** | **1,442** | **167** | 12.3 |
| **`X1_C3_FULL`** | **48 thang** | **2,266** | **1,442** | **174** | 13.0 |

=> `n_eff` muc lenh **x1.88** (89 -> 167). CI ky vong hep lai **~x1.37** (`sqrt(1.88)`).
Do dung la do lon quan sat duoc: CI cua `mP|SL` tu 30 thang [khong ghi lai] xuong
[+0.629, +4.175]; con o **2022 rieng** (n=406/360, gan bang co mau cu) CI van rong
[−0.652, +13.388] va khong ket luan duoc gi.

Cho tang gate (muc tick), viec keo dai 30 -> 48 thang se nang `n_eff` tick-level tu ~908 len
**~1,450** theo ty le do dai lich su — **chua do**, chi la suy ra tu quan he tuyen tinh ma
`F4_TIMING` muc 4 khang dinh.

**Ket luan ve power**: x1.88 la that nhung **khong du de doi ket luan**. Voi 48 thang,
`C3_FULL − C3` van chi co **1** rate chat luong ngoai CI — y het voi 30 thang. Do la ket qua
**null co thong tin**: hieu ung DCA nho hon nguong ma cua so nay phan biet duoc, khong phai
"chua do du min".

## 10. § 2025 KHAC GI 2022-2024 — **mo ta, KHONG tune**

### 10.1 Universe no gap doi, gate mo nhieu gap 5 lan

| do | 2022 | 2023 | 2024 | **2025** |
|---|---|---|---|---|
| coin co gia trong `CLOSES_1H` (cuoi nam) | 136 | 239 | 347 | **591** |
| tick 15m gate MO co label (`cand_dev_x1`) | 2,926 | 510 | 2,258 | **11,653** |
| dong pool ledger | 391,389 | 90,730 | 620,928 | **5,470,604** |
| coin THUC SU vao lenh (`X1_C3`) | 108 | 142 | 219 | **251** |
| ti le bin co score S1 (fold cuoi nam) | 0.051 | 0.016 | 0.093 | **0.770** (2025Q4) |

2025 mot minh chiem **78%** tong pool ledger cua ca 5 nam. Moi thong ke GOP tren 48 thang
deu bi 2025 keo — day la ly do bang rate theo nam (muc 5) la bat buoc, khong phai trang tri.

### 10.2 Cai KHONG doi — va du doan cua toi SAI o day

`TSloss%` va `win%` cua `X1_C3` **on dinh xuyen 4 nam**: TSloss 16.4 / 12.1 / 15.1 / **15.1**;
win 83.3 / 88.6 / 85.7 / **84.7**. Phan bo `status` 2025: 666 `STOP_MARKET_DONE` / 118
`STOP_LOSS_DONE` = dung ty le cu.

⚠️ **Du doan ghi truoc cua toi (`PREREG_X1` muc 8) SAI 2/5:**
- (1) Toi doan `TSloss%` 2025 **xau di con 17-21%** va `win%` tut ve 81-84%. **SAI** — 15.05%
  va 84.69%, tuc **`C3` GIU duoc ca hai**. Lap luan "universe no x2.2 ma `TOPK=8` khong doi
  nen ty le chon tut" **khong dan toi rate xau hon** nhu toi tuong.
- (2) Toi doan `n` 2025 >= 1.5 lan 2024. **SAI** — 784 vs 624 = **x1.26**.
- (3) Toi doan DCA khong duong o 2023/2024 va "co the" duong 2025, dat xac suat `C3_FULL`
  duoc nhan ~30%. **DUNG phan DCA** (2023 = 0 leg, 2024 = −164, 2025 = +4,813), **DUNG ca ket
  luan cuoi** (khong nhan) nhung **sai ly do**: no truot o tieu chi 1 va 3, khong phai o tieu chi 2.
- (4) Toi doan rui ro nhat o 2025Q1 (~40% co quy < −5%). **SAI** — 2025Q1 la quy **TOT nhat**
  cua 2025 (+12.7%); cai vo la **UW**, khong phai quy am.
- (5) Toi doan `n_eff` moi 1,300-1,600. **SAI don vi** — muc lenh la 167 khoi (tu 89); con
  1,450 la con so cua tang tick (chua do). Xem muc 9.

### 10.3 Cai THUC SU doi: **do sau cua lenh thua**, khong phai tan suat

`mean(profit|SL)` theo nam: −22.86 / −13.23 / −15.52 / **−28.94**.
Phan vi cua `profit|STOP_LOSS_DONE`:

| nam | n | p10 | med | p90 | min |
|---|---|---|---|---|---|
| 2022 | 59 | −51.6 | −18.1 | −6.5 | −86.9 |
| 2023 | 35 | −27.7 | −10.8 | −1.2 | −43.4 |
| 2024 | 94 | −29.4 | −13.4 | −2.6 | −61.1 |
| **2025** | **118** | **−54.8** | **−23.2** | **−7.2** | **−94.6** |

=> 2025 khong thua **nhieu hon**, ma thua **sau gap ~2 lan** 2024 o moi phan vi. Cong voi
`meanP` tut con **1.368** (thap nhat 4 nam) => day la kenh duy nhat 2025 an tien.

### 10.4 Ban le trailing: 2025 gan nhu chi con nhanh STRONG

`symbolPred` cua leg-1 <= 0.29 (= STRONG, cap giveback 0.08):

| nam | STRONG% | median hold (gio) |
|---|---|---|
| 2022 | 69.2 | 13.4 |
| 2023 | 53.1 | 13.6 |
| 2024 | 91.8 | 13.8 |
| **2025** | **95.4** | **9.0** |

Hai quan sat di cung nhau: 2025 **95.4%** lenh di nhanh STRONG (cap rong 8% thay vi 3%) va
median thoi gian giu **tut tu 13.8h xuong 9.0h**. Ket hop voi muc 10.3: cap giveback rong
tren mot universe coin moi/bien dong hon => lenh thang chot nhanh hon, lenh thua roi sau hon
truoc khi cham time-stop 168h. **Day la mo ta, khong phai de xuat sua** — `SIM_TS_MAX_GAP` va
`SIM_TS_PNOPUMP_WEAK_THR` la vung trang cua `W1` va bat ky dong cham nao vao chung sau khi
DA THAY bang nay se la tune-after-the-fact.

### 10.5 S1 selector: edge5 2025 CAO NHAT

`edge5` (top-5 vs pool, outcome `g1lite`) theo nam tren OOS: 2022 **+6.25%** / 2023 **+8.89%** /
2024 **+8.52%** / **2025 +19.34%** (11,653 tick). Toan bo 16 fold: **+15.41%**, `t = 72.3`.
Tuc selector S1 **khong xuong cap** o universe lon — no manh len. Cai xau di nam o tang exit
(muc 10.3), khong o tang chon coin.

---

## 11. ARTIFACT + LENH TAI LAP

| artifact | duong dan | kich thuoc / sha |
|---|---|---|
| featv2 mo rong | `/home/ubuntu/featv2/feat_v2_x1.parquet` | 2,038,889,420 B, 10,265,224 dong |
| ledger mo rong | `/home/ubuntu/ledger/cand_dev_x1.parquet` | 7,020,129 dong, 21,396 tick |
| S1 pred 16 fold | `/home/ubuntu/ledger/pred_s1a2x1.parquet` | 64,056,011 B, sha256 `2618fe1a0235d8ed3602f7b4bf37d8ba611e4e6c923854e10184d036065309fe` |
| bins selector 16 fold | `/home/ubuntu/predwf_map_s1a2_x1/` | **930,971,390 B**, sha256 tung file trong `BINS_SHA256` + `research/pipeline/BINS_MANIFEST.md` muc X1 |
| dataset WFO | `/home/ubuntu/wfo_ds_x1` (4.0G) | **DA XOA sau khi chay** (dia 93%); tai tao bang `run_x1_sim.sh` |
| run | `/home/ubuntu/java/devrun/X1_C3`, `X1_C3_FULL` | md5 printDone `d39da2940dfd815f60772f70517750bf` / `2478e90d4e6147bf4cc64f75967ef47d` |

```bash
R=/home/ubuntu/src/BinanceFuturesJava
bash $R/research/pipeline/x1/run_x1.sh        # G1 -> ledger -> G2 -> S1 -> G3 -> map -> G4
bash $R/research/pipeline/x1/run_x1_sim.sh    # dataset + 2 arm (Oracle, TICKER_SOURCE=file)
python3 $R/research/analysis/x1_rates.py X1_C3 X1_C3_FULL
python3 $R/research/analysis/qret_ladder.py X1_C3 X1_C3_FULL
```

## 12. NO KY THUAT MOI / CON MO

1. 🔴 **`predwf_G015x26` van la bo bins khong tai lap duoc** va bay gio da lan sang ca 6 fold
   moi (2024H2-2025). Muon go, phai do lai toan bo baseline voi `predwf_G015_v2` mo rong —
   job rieng, se lam `C3` doi so.
2. 🔴 **`UW <= 120` khong con la nguong dat duoc** tren 48 thang (ke ca baseline). Can user
   quyet lai nguong, hoac chap nhan UW dai la dac tinh cua he — **khong duoc tu ha nguong.**
3. ⚠️ `wfo_gate_pred.csv` het o **2025-12-31 23:59**. Muon do 2026 phai sinh lai gate CSV
   VA mo `HoldoutSeal` — tuc **dot holdout cuoi cung**. Khong lam khi chua co quyet dinh cua user.
4. ⚠️ `ledger.py` ban goc co glob `funding_label_202[1-4]*.pb` — chay no voi `T1` sau 2025 se
   **lang le thieu 2025**. Ban X1 da tham so hoa; ban goc **chua sua** (de khong pha tai lap).
5. ⚠️ Chan B (2021H2) van chua co duong nao lam duoc ma giu duoc neo C3 — xem muc 1.2.
