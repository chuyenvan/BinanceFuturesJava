# PREREG — GATE-SCALE SWEEP: tang SO LENH SACH bang 1 num, roi do RUI RO theo n

Chot **TRUOC** khi chay bat ky sim moi nao. Ngay 2026-09-24. Branch `module`
(HEAD `dc5aecc` / `329be43`; runner+scorer commit ngay sau file nay). Sim chay **tren Kaggle CPU
kernel** (`docs/runbooks/KAGGLE_SIM.md`, `docs/runbooks/KAGGLE_SIM_48M.md`) — **KHONG** chay Java/sim tren Oracle
(Oracle chi duoc `mvn -o package`). **KHONG** `claude-run`/Claude Code. **KHONG** push. DEV only
(cua so `2021-07-01 .. 2025-12-31`, KHONG cham 2026).

---

## 0. Vi sao co vong nay

Owner (chat): *"cần tăng nhiều lệnh, giảm tỉ lệ lãi cũng ok, nhưng tôi nghĩ nó GIẢM RỦI RO"*, va
*"sẵn sàng maxDD 30–40%, chỉ là lỗ tạm thời, đánh 1x nên không chạy được tk"*.

Vong `PREREG_GATESCALE`/`RESULT_GATESCALE` (2026-09-12) da quet **3 diem** scale {0.80, 1.30, 1.70}
tren cua so `wfo_ds_x1` **2022-01..2025-12 (48 thang)** va ket luan **0/3 PASS** (tieu chi khi do
la `d CAGR > 1.4823*sd_boot`); trong do T130/T170 **khong** duoc doc theo maxDD/UW/toan-ky nhu
bai nay, va **khong** co diem nao giua 1.00 va 1.70. Vong nay lam **phep do sach, mot chieu**:
**bien thien n DUY NHAT** bang 1 num, giu moi thu khac co dinh, roi do **rui ro (maxDD/UW/venh)
nhu mot HAM CUA n** tren cua so DEV day du 2021-07..2025-12.

Cau hoi trung tam (chot truoc, xem §8): khi n tang thi **rui ro TOT hon hay XAU hon**?

---

## 1. Su that da xac minh (dung lai, khong suy dien lai)

| moc | cau hinh | cua so | n (leg) | equity | md5 `printDone.csv` |
|---|---|---|---|---|---|
| **T170** (`x1_gs_t170`, `SIM_GATE_DYN_SCALE=1.70`) | gate scale 1.70 | 2021-07..2025-12 | **1,089** | **111,070** | `efb793e2468ca3a7318da0f0ad23d4fc` |
| **T100** (`x1_c3_full`, khong khai key => 1.0) | gate scale 1.00 | 2021-07..2025-12 | **2,559** | **121,770** | `dc16e4da6ff6cb7b8d41c592bc3d9c45` |

Cac su that dung lai (da cong bo, khong do lai):

- `x1_gs_t170` va `x1_c3_full` **khac nhau DUNG 1 dong** (`SIM_GATE_DYN_SCALE=1.70`) — kiem bang
  `diff` (docs/prereg/PREREG_GATESCALE.md §1; da kiem lai trong vong nay, xem commit runner).
- `SIM_GATE_DYN_SCALE` = **nhan 1 he so vao KET QUA `dyn_thr` da tinh** trong `EntryGate.pass`
  (sim + live dung chung). `>1` = CHAT hon (it lenh), `<1` = LONG hon. Khong khai / `<=0` => 1.0.
  `scale=1.0` => `x*1.0` IEEE-exact => byte-identical voi `x1_c3_full`.
- Kaggle sim T170 tren cua so 2021-07..2025-12 la **byte-identical** voi Oracle
  (`docs/runbooks/KAGGLE_SIM_48M.md` §0/§4) => Kaggle la Oracle-tuong-duong cho profile/cua so nay.
- **Rao cung dang chan khong phai maxDD.** `docs/runbooks/RISK_APPETITE.md` §6 (2026-09-24, chot cua user)
  ghi ro: T170 −11.84% · T100 −16.13% · GD92 −16.55% — **ca ba duoi ca tran CU 30%**; rang buoc
  **dang chan that su** la **`UW <= 200`** (T100 248 · GD92 278) va **tap trung 1 coin `<= 15%`**
  (T100 27.08–28.35%). Ngoai ra `margin/(quantity*entry) = 1.0000 tren 1089/1089 leg` (1x, khong
  don bay) => drawdown la tam thoi.

---

## 2. Thiet ke — 1 num, thang chot truoc

- **Num duy nhat:** `SIM_GATE_DYN_SCALE` (khong them/sua key nao khac; exit hien tai, DCA, selector,
  funding, breaker **giu nguyen**).
- **Thang chot TRUOC (6 diem, khong them/bo/doi sau khi thay so):**
  **{1.70 (moc incumbent), 1.55, 1.40, 1.25, 1.10, 1.00 (= T100 base)}**.
- Ky vong co che: n **don dieu** theo chieu nghich voi scale (scale nho => n lon). Neu khong don
  dieu => co che sai / ket qua degenerate, phai ghi ro.
- Profile moi (4 cai): `profiles/x1_gs_t155.properties`, `x1_gs_t140.properties`,
  `x1_gs_t125.properties`, `x1_gs_t110.properties` — moi file = **ban copy cua
  `x1_c3_full.properties` + DUNG 1 dong** `SIM_GATE_DYN_SCALE=<v>` (cung khuon `x1_gs_t130`/
  `x1_gs_t170` da co). Chung minh bang `diff` (da kiem).

---

## 3. Cong parity (BAT BUOC — chay TRUOC khi doc ket qua)

| diem | tai lieu | md5 `printDone.csv` bat buoc |
|---|---|---|
| 1.70 | `kaggle_sim/out/t170-x1-2021` | `efb793e2468ca3a7318da0f0ad23d4fc` |
| 1.00 | `kaggle_sim/out/hn-t100` | `dc16e4da6ff6cb7b8d41c592bc3d9c45` |

Kiem bang `md5sum` tren chinh 2 file. **Khac => DUNG, bao RO, khong doc tiep bat ky so nao.**
(2 dong nay da duoc kiem trong vong nay: **khop ca hai**.)

---

## 4. Chan chay — TAI SU DUNG cai da co, chi chay moi cho muc thieu

Moi chan: bundle `chuyendinh/sim-x1-2021-bundle` (dataset `wfo_ds_x1_2021`, `leakFreeFrom=2021-07-01`),
`sim_end_date=20251231`, `code_sha` ghi trong runner, **KHONG** override key nao khac.

| scale | tag | trang thai | ly do |
|---|---|---|---|
| 1.70 | `t170-x1-2021` | **TAI SU DUNG** | da co tren bundle nay, md5 `efb793e2` khop Oracle (`docs/runbooks/KAGGLE_SIM_48M.md` §0), `n=1089/equity=111070` khop |
| 1.00 | `hn-t100` | **TAI SU DUNG** | profile `x1_c3_full` = scale 1.0; md5 `dc16e4da` = md5 chuan cua T100 (da xac nhan o `RESULT_GD92_X_EXIT`/`RESULT_EXIT_HIGH_N`); `n=2559/equity=121770` khop |
| 1.55 | `gs-t155` | **CHAY MOI** (Kaggle) | profile moi, chua co chan nao |
| 1.40 | `gs-t140` | **CHAY MOI** (Kaggle) | profile moi, chua co chan nao |
| 1.25 | `gs-t125` | **CHAY MOI** (Kaggle) | profile moi, chua co chan nao |
| 1.10 | `gs-t110` | **CHAY MOI** (Kaggle) | profile moi, chua co chan nao |

### 4b. SUA CO CHE CHAY (amend 2026-09-24, ghi TRUOC khi co bat ky ket qua nao)

`sim-x1-2021-bundle` la **SNAPSHOT** (`docs/runbooks/KAGGLE_SIM.md` §0.4) va chi chua **3 profile**:
`prof_x1_c3_full`, `prof_x1_gs_t170`, `prof_x1_c3_full_regime_brc` (kiem bang
`KaggleApi.dataset_list_files` co phan trang `nextPageToken`: 28 file). 4 profile MOI cua thang
chot **KHONG** co trong bundle (tao sau 2026-09-21) ⇒ push kernel voi profile do thi kernel
**exit** `MISSING /kaggle/input/**/prof_x1_gs_t155.properties` (da xay ra that: tag `sim-gs-t155`
vu 1 = ERROR; 3 chan con lai khong tao duoc kernel).

⇒ **Doi sang DUONG OVERRIDE** (dung khuon `research/analysis/exithighn_run.py` da dung cho T100):
`profile=x1_c3_full` + **DUNG 1** override `SIM_GATE_DYN_SCALE=<v>`. Kernel **COPY** profile roi ghi
override vao ban copy (`KERNEL_TEMPLATE`: `pairs` = profile, `ov` = overrides) ⇒ `prof_run.properties`
ra **DUNG bang noi dung** `profiles/x1_gs_t1*.properties` (tru `WFO_FUNDING_PRED_DIR` bi tro vao
mount Kaggle) ⇒ **4 profile file van la ban ghi tuong duong** cua thiet ke, khong doi thiet ke.
Khong doi thang chot, khong doi num, khong doi diem nao. Kiem chung tu output: `prof_run.properties`
cua tung chan phai co `SIM_GATE_DYN_SCALE=<v>` (ghi vao **RESULT**, khong suy dien).

**Khong dung lai `java/devrun/CALIB_T130` / `X1_GS_T130_2021` / `CALIB_T210`** (da kiem trong vong
nay): ca ba la run **Oracle** (`TIME_RUN=20210701`, dataset `wfo_ds_x1_2021`) nhung scale cua chung
la **1.30** (`CALIB_T130` ≡ `X1_GS_T130_2021`, n=1580, md5 `68510567`) va **2.10** (`CALIB_T210`,
n=808) — **khong nam trong thang chot**. Thang chot la {1.70, 1.55, 1.40, 1.25, 1.10, 1.00}, nen
du chung dung dataset thi cung **khong duoc dung** (dung luat "khong them bien the"). Ghi ro de
khong ai tuong thieu.

**Jar:** dung `sim.jar` **mac dinh trong bundle** (= HEAD `ba3d7ba`, build 2026-09-21 17:50) — dung
CHINH jar da tao ra `t170-x1-2021` (md5 `efb793e2`) => moc 1.70 va 4 diem moi chay tren CUNG 1 jar.
Khong upload jar moi (khong doi code: key da co tren `module` tu commit `71a713f`; 9 file `src/`
sau `ba3d7ba` deu la co default-OFF: `TS_PEAK_MODE=high`, `TS_LADDER` off, `SIM_TICK_BLOCK` off =>
khong doi hanh vi, da duoc chung minh byte-identical o `RESULT_PEAK_CLOSE`/`RESULT_TRAIL_LADDER`).
Chan 1.00 (`hn-t100`) chay bang jar `sim-jar-exithighn` (cherry-pick rolling **tro**) nhung md5 ra
**dung `dc16e4da`** = md5 chuan cua T100 => tuong duong.

---

## 5. Do luong cho MOI diem (bat buoc, in het)

1. **Co che:** n leg, meanP/leg (USDT), win%, TSloss%, hold med, turnover, SumPnL.
2. **5 rate chat luong vs T170** (= `1.70`, moc incumbent): `win%`, `TSloss%`, `mP|SM`, `mP|SL`,
   `meanP` — CI **block-72h, 2000 rep, seed 20260905, x1.21**, neo block co dinh `2021-07-01`
   (khuon `research/analysis/gd92xexit_score.py::ci_pair`). "NGOAI CI" = ngoai o **x1.21**.
   (Phu, KHONG quyet dinh: cung hieu do o do rong `inflate(k=5)=1.7941`.)
3. **Rao cung — BAO CAO CA HAI CHUAN** (xem §6): **(S1)** va **(S2)**, moi chuan kiem **theo nam
   LAN toan ky**.
4. **maxDD · UW** (nam + toan ky) — output TRUNG TAM.
5. **Do venh theo nam:** SD va range (`max-min`) cua `ret%` theo nam.
6. **relative SE = SE/mean:** bootstrap block-72h, 2000 rep, cua **meanP/leg**; `relSE = SE/mean`.
   Kiem dinh luat `relSE ~ 1/sqrt(n)` bang ti so `relSE * sqrt(n)` (hang so => dung luat; giam =>
   n moi it gia tri hon 1/sqrt(n)). So voi T170.
7. **Bang PnL chi tiet theo nam:** n · PnL(USDT) · ret% · maxDD% · UW · qmin% · equity · P/F — cho
   **moi** diem.

---

## 6. Rao cung — dinh nghia CHOT TRUOC (S1/S2)

**(S1) — RISK_APPETITE hien hanh (ban §1, maxDD 30%/nam):**

| rang buoc | nguong |
|---|---|
| `maxDD` | `<= 30%` (theo nam **VA** toan ky) |
| `UW` | `<= 200` ngay (theo nam **VA** toan ky) |
| quy xau nhat | `>= -15%` |
| nam am | **khong** (`ret%` nam `>= 0`) |
| tap trung 1 coin | `<= 15%` equity (toan ky) |

**(S2) — noi maxDD len 40%** (giu nguyen UW / nam / quy / tap trung):

| rang buoc | nguong |
|---|---|
| `maxDD` | `<= 40%` (theo nam **VA** toan ky) |
| con lai | **y het (S1)** |

**Ghi chu tranh cai (ghi truoc):** `docs/runbooks/RISK_APPETITE.md` **§6 (2026-09-24)** da noi `maxDD` theo
nam len `<= 40%` theo chot cua user. Nghia la **S2 chinh la rao HIEN HANH neu tinh §6**, con **S1 la
rao theo ban §1** (30%). Task yeu cau bao cao CA HAI, nen vong nay bao cao ca hai va **khong duoc
doi nguong nao sau khi thay so**.

### 6b. (S3) — rao HIEN HANH sau commit `0c2a8a5` (dang ky TRUOC khi co ket qua)

Trong luc vong nay dang chay, mot commit KHAC (`0c2a8a5 baseline(2026-09-24)`) da vao branch va
cap nhat `docs/runbooks/RISK_APPETITE.md` §7 (user chot lan 2): **`maxDD <= 40%/nam` · `UW <= 250 ngay` ·
`quy xau nhat >= -20%` · `khong nam am` · tap trung `<= 15%`**. User kem chi dan *"uu tien nhat la
nhieu lenh de on dinh"* — dung chu de cua vong nay.

⇒ Vong nay bao cao them **chuan (S3) = rao hien hanh §7** (khong thay S1/S2 — S1/S2 van la nguong
**quyet dinh** theo task/pre-reg). S3 la chuan **UNG VIEN DI TIEP** (veto), KHONG phai bang chung.

```
S1 = maxDD<=30% | UW<=200 | qmin>=-15% | ko nam am | conc<=15%   (quyet dinh theo task)
S2 = maxDD<=40% | UW<=200 | qmin>=-15% | ko nam am | conc<=15%
S3 = maxDD<=40% | UW<=250 | qmin>=-20% | ko nam am | conc<=15%   (= RISK_APPETITE §7, hien hanh)
```

**CANH BAO nen (ghi truoc, KHONG doi thiet ke):** commit `0c2a8a5` cung doi **BASELINE nghien cuu**
sang `FLATGRID KEEPLEG0` (`DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0`, parity md5
`99e42b75cf1a2142f9cd14dc72e371ba`, 1085 leg). Thang chot cua vong nay **da bi khoa tren nen
`x1_c3_full`/`x1_gs_t170` (DCA `1,1,3,8`)** voi 2 cong parity `efb793e2`/`dc16e4da` — **KHONG doi
nen** (doi nen la doi thiet ke + pha 2 cong parity). Ket qua vong nay vi vay duoc dan nhan la
**do tren NEN CU (DCA 1,1,3,8)**; muon ket luan cho baseline MOI thi phai chay vong moi. `qmin` = return quy xau nhat (tinh trong nam), `conc` = dinh
`sum(margin)/equity` theo `(sym,end)` (khuon `gd92xexit_score.conc_max`).

---

## 7. Luat quyet dinh — CHOT TRUOC (khong doi sau khi thay so)

- **R-PASS(Sx)** (rao cung) = qua **het** rang buoc (Sx) **theo nam LAN toan ky**.
- **E-PASS** (bang chung) = `>= 2/5` rate **ngoai CI x1.21 cung huong TOT** so T170 **VA**
  `0` rate **XAU ngoai CI**. (Nguong bang chung `>=2` giu nguyen theo `RISK_APPETITE.md`;
  huong TOT: `win%`/`mP|SM`/`mP|SL`/`meanP` tang, `TSloss%` giam.)
- **PASS(Sx)** (day du) = `R-PASS(Sx)` **VA** `E-PASS`.
- Khi tra loi (b): uu tien **R-PASS(S1)** (cau hoi cua owner la RUI RO), bao kem muc **PASS(S2)** va
  muc **PASS day du**.
- **Ky vong ghi truoc (co the sai, phai bao dung):** n tang => **UW toan ky va tap trung 1 coin XAU
  di** (nhieu lenh hon tren cung 863 symbol + book mo lon hon), `maxDD` co the van PASS ca S1 lan S2
  (vi deu duoi 30%). => **du doan: khong muc nao ngoai moc T170 PASS (S1) toan ky** ⇒ tra loi (b)
  **"khong co"**; (c) **"tang lenh KHONG giam rui ro"** o nghia rao cung (UW/tap trung), du SD
  `ret%` nam co the giam nhe. Neu nguoc lai => la ket qua **bat ngo**, phai ghi ro.
- Ket qua duong (neu co) **chi la UNG VIEN**, can forward; **khong tu tich hop san xuat**.
- Neu **khong muc nao ngoai moc PASS (S1)** ⇒ **NULL** va tra loi (b) = **"khong co"**.

---

## 8. Cau hoi trung tam phai tra loi (bang so)

- **(a)** Khi n tang, `maxDD` / `UW` / **do venh nam** TOT hon hay XAU hon? Co ve **duong cong rui
  ro theo n** khong (don dieu? cuc tri? bang phang?).
- **(b)** Muc scale nao cho **n CAO NHAT ma PASS (S1)**? va **PASS (S2)**?
- **(c)** Neu n tang ma rui ro **xau dan** ⇒ noi ro **"tang lenh KHONG giam rui ro trong du lieu
  nay"**, kem **so**.

---

## 9. Thu tu bat buoc + khong lam

1. Commit file nay (+ profile + runner + scorer) **TRUOC** khi push kernel.
2. Cong parity §3 (md5 2 moc). Khac => DUNG.
3. Chay 4 chan moi tren Kaggle (4 kernel song song; **khong** chay sim/JVM tren Oracle).
4. Fetch + cham diem (§5). Kiem che co che (n don dieu theo scale).
5. `docs/result/RESULT_GATESCALE_SWEEP.md` + ket luan (a)(b)(c). Commit SAU (khong push).
6. Don temp.

**Khong lam:** khong doi thang chot; khong them key/biên the; khong chay 2026/holdout; khong chay
Java tren Oracle (chi `mvn -o package` neu can build); khong push; khong tu tich hop; khong doi
nguong S1/S2/CI sau khi thay so.
