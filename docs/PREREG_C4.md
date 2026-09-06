# PREREG_C4 — thang GIA TRI cua gate: `retEnd` (net015) vs `maxFav`, va bins TAI SINH

Viet + commit **TRUOC** khi chay bat ky arm nao. Khong sua sau khi thay so.
Nen: `docs/AGENT_RUNBOOK.md` muc 0.2. Cua so DEV = **48 thang 2022-01-01 -> 2025-12-31**
(`SIM_END_DATE=20251231`, duoi `HoldoutSeal` 2026-01-01 — **khong unseal**).

## 0. Cau hoi

`build_map.py` giu NGUYEN multiset `P(win)` cua model GIA TRI trong tung tick, chi gan lai
coin nao nhan gia tri nao theo thu hang cua **S1**. Nen tang GIA TRI (`symbolPred`) di vao he
qua **hai** duong:
1. **gate tang 2** — `dyn_thr = SIM_MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, score/0.15*MULT)`,
   tang don dieu theo `score` => phan phoi `P(win)` thap hon => nguong thap hon => **admit nhieu hon**;
2. **ban le trailing** — `symbolPred <= 0.29` -> STRONG (cap 0.08), nguoc lai WEAK (cap 0.03).

`L1_SHADOW_C3` muc 4 da do: o **duong (2)** gia tri KHONG load-bearing (thay bang hang so
o ca hai cuc -> 0/5 rate ngoai CI). C4 hoi ve **duong (1)**: doi ca THANG DO co lam doi
he thong khong?

## 1. Ba arm — chi doi MOT thu: bins nguon vao `build_map.py`

S1 order giu nguyen tuyet doi (`pred_s1a2x1.parquet`, sha256 `2618fe1a…`), profile giu
nguyen `profiles/x1_c3.properties` (chi doi `WFO_FUNDING_PRED_DIR`), jar giu nguyen.

| arm | bins GIA TRI nguon | nhan cua model gia tri | ghi chu |
|---|---|---|---|
| `C4_parity` | `claudedata/predwf_G015x26/` (16 fold) | `retEnd_4h > 0.015` | = `X1_C3`. Cong hoi quy. |
| `C4_maxfav` | `predwf_G015_v2` mo rong 16 fold | `maxFav_4h >= 0.06` | **can train them 6 fold** (20240701..20251001) bang `g72_train.py` CPU |
| `C4_regen` | `/home/ubuntu/g3x26/regen/` (16 fold) | `retEnd_4h > 0.015` (predict tu 18 model goc) | chung minh bins TAI SINH thay duoc bins goc o tang sim |

## 2. Cong hoi quy (phai PASS truoc khi doc bat cu so nao khac)

`C4_parity` phai ra **byte-identical** `X1_C3`:
`n = 2,058` · `equity = 98,523` · md5 `printDone.csv` = `d39da2940dfd815f60772f70517750bf`.
FAIL => DUNG, khong doc arm nao khac (nghia la moi truong da troi).

## 3. Tieu chi — RATE, khong phai equity

Do tren `printDone.csv`, **toan 48 thang VA theo tung nam**. CI = bootstrap khoi **72h x 1.21**
(he so 1.21 = ty le `edge5` GPU-vs-CPU tren nen between-seed, `docs/BENCH_DEVICE.md` muc 4.2),
do TRONG cung moi truong.

**Rate chat luong** (5): `win%`, `TSloss%`, `mean(profit|STOP_MARKET_DONE)`,
`mean(profit|STOP_LOSS_DONE)`, `mean(margin)`.
**Do admission** (bao rieng, KHONG dem vao quy tac quyet dinh — la co hoc, khong phai chat luong):
so lenh `n`; ty le trung khoa `(sym, start)` voi `C4_parity`; phan phoi `symbolPred` p10/50/90;
so candidate-minute pass gate.

**Rang buoc cung** (bao cao, khong tune): `maxDD <= 15%`/nam · khong nam am ·
khong quy < −5%. `UW <= 120` **da khong con dat duoc** tren 48 thang (`X1_EXTEND` muc 7) —
bao cao, khong dung lam cong.

## 4. Quy tac quyet dinh (chot truoc)

- **`C4_maxfav` KHAC `C4_parity`** khi va chi khi **>= 2 rate chat luong cung huong, ngoai CI**,
  tren **toan 48 thang**. `n` va `mean(margin)` mot minh KHONG tinh (hai mat cua cung mot
  su kien co hoc — `AGENT_RUNBOOK` muc 4, ket luan gate 0.006).
- **`C4_regen` thay duoc bins goc** khi: hoac `printDone.csv` byte-identical `C4_parity`,
  hoac (neu khong byte-identical) **0/5 rate ngoai CI** VA ty le trung khoa `(sym,start)` >= 99%.
- Ket qua null duoc bao cao la null. **Khong de cu baseline moi trong dot nay.**

## 5. Du doan ghi TRUOC (ke ca khi sai)

### 5.1 Du doan cua master (de bai)
Phan phoi khac han (`p_mean` 0.34095 cua `G015_v2` vs 0.46416 cua `x26`) => `dyn_thr` thap hon
=> **admit nhieu hon** => `TSloss%` **tang**. Tuc thang gia tri **CO** load-bearing o gate,
**nguoc** voi ket luan L1 o tang trailing.

### 5.2 Du doan cua toi (agent)
1. `C4_parity` byte-identical — xac suat ~0.97. (Rui ro duy nhat: dataset WFO build lai
   khong deterministic.)
2. `C4_regen` **KHONG** byte-identical `C4_parity`, nhung **0/5 rate ngoai CI** va trung khoa
   `(sym,start)` **>= 99.5%**. Ly do: `max|d| = 1.192e-07` (1 ULP float32) tren `p0` du de LAT
   vai tick sat nguong `dyn_thr`, va `AGENT_RUNBOOK` muc 4 da do rang duoi sizing compound
   thi `n` khong bat bien voi thay doi vi mo (0.1-0.9%). Xac suat byte-identical ~0.25.
3. `C4_maxfav`: **admit nhieu hon** (`n` tang **>= 15%**) — dong y voi master ve CHIEU. Nhung
   toi du doan **1-2** rate chat luong ngoai CI chu khong phai >= 3, va `TSloss%` tang **duoi
   2pp**. Ly do de nghi ngo hieu ung lon: `build_map` giu nguyen multiset trong tick, nen
   phan phoi thay doi la thay doi **muc** cua ca tick chu khong phai thu tu; ma `X1_EXTEND`
   muc 10.4 do duoc `%STRONG` chi trai 6.8pp theo rank => thang gia tri gan nhu **truc giao**
   voi thu tu chon coin. Neu `n` tang manh ma 5/5 rate van trong CI thi ket luan la
   "thang gia tri chi doi **so luong**, khong doi **chat luong**" — do la ket qua co thong tin.
4. `symbolPred` p50 cua `C4_maxfav` se **thap hon** parity ~0.18 (0.29 vs 0.475) => ty le
   nhanh STRONG (`<= 0.29`) tang tu ~84% len **> 95%**. Day la hieu ung phu bat buoc phai
   bao, vi no lam `C4_maxfav` KHONG phai phep thu sach cho rieng gate.

🔴 **Diem yeu da biet cua thiet ke nay** (ghi truoc, khong bao chua): doi bins gia tri doi
**dong thoi** ca gate (duong 1) LAN ban le trailing (duong 2). C4 **khong tach duoc** hai
kenh. Neu `C4_maxfav` khac parity, phai chay them mot arm khoa `SIM_TS_PNOPUMP_WEAK_THR`
de quy trach nhiem — **khong nam trong dot nay**.

## 6. Cong xac minh cua Viec A (ghi truoc khi chay kernel)

Train lai fold 8 (cutoff `20240101`) bang `research/pipeline/g015_net_train.py` tren **Kaggle
GPU** (dung device sinh ra neo), cung seed 42, so predict voi model goc `model_f8_4h.json`
tren cung tap OOS rows:

| do | nguong PASS | can cu |
|---|---|---|
| `spearman` gop | **>= 0.98** | `spearman(x26, sel_models_net015)` = **0.98325** — hai lan chay GPU cung nhan (`G3_X26_RECOVERY` muc 3.6 / H3) |
| top-8 moi tick trung | **>= 95%** | — |
| `< 0.95` | FAIL — hyperparam/feature con sai, doi chieu lai log, toi da 3 lan thu | — |

**KHONG** doi bit-identical: `BENCH_DEVICE` muc 3 do duoc GPU dung RNG lay mau khac
(`Cover` lech 31/31 node) + quantile sketch `hist` khac (`Split` lech 11/31); ghim seed
khong cuu duoc. `BENCH_DEVICE` muc 5: doi seed tren cung mot may cho spearman 0.9817.
Chay them **1 fold tren Oracle CPU** — **tham khao**, khong phai cong (BENCH_DEVICE muc 7.3:
khong duoc ghep cap so tu hai moi truong trong mot so sanh).
