# PREREG_GATE_ROOTCAUSE — Nut that cua gate dong bang: LECH NGUON/THANG DO p15 + luat gate bieu dien theo don vi NGUON LIVE

**Trang thai: DE XUAT. CHUA AP DUNG VAO PRODUCTION, KHONG DEPLOY.** Chot TRUOC khi do/khong chay bat cu chan sim nao.
Nguon chan doan: `docs/audit/DIAG_GATE_FROZEN_20260926.md` (+ `.json`), `docs/prereg/PREREG_GATE_RECAL.md` +
`docs/result/RESULT_GATE_RECAL.md`.

## 0. Nut that (mot cau)

`DIAG_GATE_FROZEN` ket luan **HIEU CHUAN**, `RESULT_GATE_RECAL` ket luan **nguong phan vi cuon KHONG cuu duoc** vi
`thr_final = max(rolling, dyn)` => **dyn luon thang** => van > p100 cua p15 live. Nut that con lai:
**nguong gate dang duoc bieu dien bang DON VI cua BO PRED DEV (`pred.bin`), trong khi model LIVE xuat p15 khac phan bo.**
Bai nay do **dinh luong** cai lech do, roi **thiet ke luat gate bieu dien theo chinh nguon live**, va **kiem tren DEV**.

**Cau hoi duy nhat:** hai phan bo p15 (DEV `pred.bin` vs model LIVE 2026) lech nhau **chi THANG DO (scale)** hay
**ca HINH DANG (shape)**? Neu **scale** => co the map bang 1 thua so. Neu **shape** => bat buoc nguong phai tinh
tu chinh nguon live (phan vi cuon cua chuoi p15 live).

## 1. Nguon so + RANH GIOI FIT (CUNG)

| ky hieu | nguon | vai tro |
|---|---|---|
| `S_dev` | `wfo_ds_x1_2021/pred.bin` cot `predReturn15M` (1 phut; DUNG y chuoi `predictionMap` cua sim) | **FIT** |
| `S_live` | 242 `full.log` `market[15M:x%]` (12/08/2026 -> nay, model live) | **CHI CHAN DOAN** |
| `S_shadow` | Oracle `shadow_c3/app/logs/full.log` `market[15M:x%]` (20-26/09) | **CHI CHAN DOAN** |

- **FIT CHI <= 2025-12-31**: moi lua chon nguong/`Q`/`W`/he so **chi** dung `S_dev` (<=2025-12-31). Cua so sim = 2021-07-01..2025-12-31.
- **2026 (`S_live`, `S_shadow`) CHI duoc DOC de chan doan** (do phan bo, uoc ty le pass) theo dung `DIAG_...`; **KHONG**
  dung de chon nguong, khong fit, khong chon `Q`, khong mo holdout lai. Khai RO o moi bang co 2026.
- Khong chay Java/sim tren Oracle. Khong deploy/restart/sua config production/242/ONNX/`NUM_FEATURES`/duong LIVE.
  Khong push git.

## 2. VIEC 1 — Do lech nguon (cac chi so DONG BANG truoc)

Voi moi nguon: `p1 p5 p25 p50 p75 p95 p99 max`, `min`, `n`. Them:
- **thuong so scale** `r_p = p_live / p_dev` tai tung phan vi; `r*` = trung vi cac `r_p`.
- **chi so hinh dang** `D = max(r_p)/min(r_p)` (tren cac phan vi), va `spread = (p99-p50)/(p50-p5)` cho tung nguon.
- **ky vong so mau >= thr** (thr ∈ {1,705% ; 2,947% ; 3,760%} = cac nguong dang ton tai) theo tung nguon, kem
  p-value Poisson (ky vong = ty le dev x n_live).
- Uoc **ty le pass theo luat cuon live**: ap nguong `quantile_Q` cua cua so 30 ngay cua chinh `S_live` (chan doan) => ty le mau pass.

**Luat quyet dinh SCALE vs SHAPE (chot TRUOC):**
- **SCALE** <=> (a) `D <= 1,5` **VA** (b) sau khi lay `r*`, `p99_live/(r*·p99_dev) ∈ [0,80 ; 1,25]` **VA**
  (c) tuong tu cho `max`: `max_live/(r*·max_dev) ∈ [0,80 ; 1,25]`.
- Nguoc lai => **SHAPE**.

**Ky vong ghi truoc (TRUOC khi do):** **SHAPE** — dung huong "trung vi live CAO hon dev, duoi live NGAN hon"
(`DIAG_` §3.3: p50 0,910% vs 0,545% => `r_50 ~ 1,67`; max 2,30% vs 12,26% => `r_max ~ 0,19`) => `D >> 1,5`.
He qua ky vong: **KHONG the map bang 1 thua so** => nguong bat buoc tinh tu chinh nguon live.

## 3. VIEC 2 — Thiet ke luat gate moi (DE XUAT, khong deploy)

Bieu dien nguong theo **don vi cua chinh nguon live**: `roll = quantile_Q( p15_past W ngay )`, CAUSAL (cua so `[t-W,t)`),
`W = 30` ngay (hang so, khong fit), `Q ∈ {0.995, 0.998, 0.999}` (3 diem khoa). **Xu ly DY TERM** (`thr_final=max(...)`
dang khien dyn luon thang) bang 3 phuong an:

| pa | dinh nghia | cai dat (khong sua code) | ky vong entry/thang | rui ro |
|---|---|---|---|---|
| **A** `thay dyn` | `thr = max(base, roll)` cho MOI leg; dyn bi thay han boi phan vi cuon | `SIM_GATE_P15_Q=Q` + `SIM_GATE_DYN_SCALE=0.001` (dyn -> ~1e-6 < base => max = roll) | ~ `(1-Q)` x 96 tick/ngay x he so chon loc (do tren DEV, chuyen duoc vi luat la phan vi) | **qua rong** => nhieu lenh rac; mat tac dung chong "momentum gia" cua dyn |
| **B** `giu dyn + hieu chuan lai` | giu dang dyn nhung nhan them he so `c` cho phan bo live: `thr = c·dyn(sp)` | `SIM_GATE_DYN_SCALE=c` (giu dyn, khong cuon) | ~ do tren DEV bang arm `B`, `c` chon tu ty so phan vi live/dev (chan doan) | `c` **khong fit duoc tren DEV** (ban chat B la hieu chuan theo live); neu `c` sai => lai > p100 |
| **C** `tat han dyn` | bo dyn khi nguon la model live; `thr` = san co so | `P15_Q` khong khai + `DYN_SCALE -> 0` (hoac `base` phang) | = luat phang `base=0,80%` => pass ~p52 cua live => **rat nhieu lenh** | **qua rong nhat**; `RESULT_FLATGATE` da do bo dyn = **-61pp CAGR** |

- Cach do moi pa: **entry/thang** (n = so lenh / so ngay x 30,44) + **chat luong lenh 5 rate** (`x1_rates.py`) + CI khoi-72h.
- Tieu chi "qua rong" (chot truoc): `entry/thang > 30` **hoac** `meanP/lenh` giam co y nghia so voi doi chieu
  (**CI 95% cua hieu >= 0 bi loai tru theo huong am**) **hoac** `conc` (top-1) > 15 / `qmin` < -20 / vi pham rao `maxDD/UW`.

## 4. VIEC 3 — Kiem chung tren DEV (chot truoc khi chay)

- Nen = **KEEPLEG0** (`prof_x1_gs_t170` + `DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0`), cua so **2021-07-01..2025-12-31**,
  bundle `sim-x1-2021-bundle`, **nhip selector 15'** (`SIM_ENTRY_SAMPLE_MIN=15`) = khop thiet ke live.
- **KHONG sua code** => **parity CA HAI** phai xanh bang cung jar: `cd-par-kg0` md5 `99e42b75cf1a2142f9cd14dc72e371ba`
  va `cd-par-t170` md5 `efb793e2468ca3a7318da0f0ad23d4fc`. (Neu buoc nao do phai sua code: mac dinh giu nguyen, va
  cong parity CA HAI phai chay lai truoc moi so khac.)
- **Doi chieu** = `cd-sel15` (nhip 15', gate cu): n=744, 13,77 entry/thang, eq 71.718, CAGR 17,29%, maxDD -6,27, UW 166.
- **Chan chay (toi da 5, song song; chi phi Kaggle 0):**
  1. `rc-par-kg0` (parity, md5 `99e42b75…`) 2. `rc-par-t170` (parity, md5 `efb793e2…`)
  3. `rc-a-q995` 4. `rc-a-q998` 5. `rc-a-q999` — **phuong an A** (KEEPLEG0 + `SAMPLE_MIN=15` + `P15_Q=Q` + `DYN_SCALE=0.001`).
- Neu con slot/thoi gian: `rc-b-s070` / `rc-b-s100` = phuong an **B** (`SAMPLE_MIN=15` + `DYN_SCALE=0,70/1,00`, khong cuon).
  Chan bi cat phai **khai ro**.
- **Luat quyet dinh (chot truoc):** pa **kha thi** <=> (i) `entry/thang ∈ [5,30]`; (ii) **khong "qua rong"** theo §3;
  (iii) **0/5 rate ngoai CI** (block-72h, 2000 rep, seed `20260905`, hieu chinh `k=3` => nguong `1,4823·sd`) so voi `cd-sel15`;
  (iv) qua het rao cung tung nam. **`k = 3`** (nhu `RESULT_GATE_RECAL`), hieu chinh `1,4823`.
- Ky vong ghi truoc: pa A **co the qua rong** (entry/thang > `cd-sel15`), chat luong lenh giam; neu vay => **DONG, giu gate hien tai**.
- Chuyen sang live: neu pa A kha thi tren DEV, **ty le entry/thang cua luat phan vi la chuyen duoc** (khac nguong tuyet doi),
  nhung **van phai xac nhan bang do ty le pass tren chinh chuoi p15 live (`S_live`, chan doan)** — neu khong khop thi ghi ro.

## 5. VIEC 4 — Cau hoi phai tra loi (chot truoc)

1. Hai phan bo p15 lech the nao (so) — **scale hay shape**?
2. Co map bang **1 thua so** khong; neu co la bao nhieu, co hop ly ve co che khong?
3. Luat gate moi (A/B/C): pa nao kha thi nhat, **entry/thang ky vong**, rui ro gi?
4. De **deploy** duoc thi can gi (buoc, nguoi duyet, rollback) — **KHONG tu deploy**.

## 6. Khong lam

- Khong fit/cham tren 2026; 2026 chi DOC de chan doan (khai ro).
- Khong doi `EntryGate` hang so / `base` / bins / selector / exit / trailing / sizing; **khong sua code** (dung key co san).
- Khong restart/sua env/profile production/242; khong dong 242; khong chay Java/sim tren Oracle.
- Khong push git; commit SOM.

## 7. Tai lieu lien quan

- `docs/audit/DIAG_GATE_FROZEN_20260926.md` (+`.json`) — chan doan dong bang.
- `docs/prereg/PREREG_GATE_RECAL.md` + `docs/result/RESULT_GATE_RECAL.md` — nguong phan vi cuon (0/4 PASS, vi `max(rolling,dyn)`).
- `docs/result/RESULT_FLATGATE.md` — bo dyn = -61pp CAGR.
- `docs/audit/LEAN_GATE_AUDIT.md` — gop cong thuc ve `EntryGate`.
