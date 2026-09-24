# PREREG_BLACKSWAN_2510 — stress THIEN NGA DEN quanh 2025-10-10/11 (alt cascade)

Chot **TRUOC khi do** — 2026-09-24, branch `module`. Moi phep do trong
`docs/result/RESULT_BLACKSWAN_2510.md` phai nam trong danh sach duoi day; phat sinh ngoai danh sach
ghi ro la **kham pha (exploratory)**, khong duoc dung lam ket luan.

## 0. Cau hoi cua owner

*"khong phai quan tam live voi backtest... chi can toi 1 su kien thien nga den lech 1,2 lenh la ket
qua do KHONG DUNG — co the he se MAT HET LAI trong 1 lan lech do hoac am nang... nhu su kien 11.10
ay no ko sap nhu truoc do ma alt sap."*

⇒ Day la cau hoi **RUI RO DUOI (tail)**, KHONG phai trung binh. Phai do duoc:
"**mot su kien co the xoa sach lai khong**", va "**tran tap trung + KEEPLEG0 co bound duoc thiet hai khong**".

## 1. Rang buoc (BAT BUOC)

- **KHONG** `claude-run`/Claude Code. **KHONG** chay Java/sim tren Oracle (Oracle chi `mvn -o package`).
  Neu buoc nao BAT BUOC phai sim (stress slip that su) ⇒ **Kaggle** (`docs/runbooks/KAGGLE_SIM.md`).
- **Thuan Python offline** tren artifact DA CO + du lieu 1m (`/home/ubuntu/kaggle_data_hpo/`).
- **DEV only**: moi leg co `end <= 2025-12-31`. **Khong doc 2026**, khong dung `_SEALED_2026_*`.
- Ket qua trung gian: `/home/ubuntu/blackswan/`. Script: `research/analysis/blackswan_2510.py`.
  Log qua module `logging` (khong `print`).
- **Khong push.** Commit branch `module`.

## 2. Du lieu (chi doc)

| nhan | thu muc | n leg | md5 `printDone.csv` |
|---|---|---|---|
| **T170** (`x1_gs_t170`, nen cu) | `kaggle_sim/out/t170-x1-2021/` | 1,089 | `efb793e2…` |
| **KEEPLEG0** (BASELINE moi) | `java/devrun/FG_KEEPLEG0/` | 1,085 | `99e42b75…` |
| **T100** (`x1_c3_full`) | `kaggle_sim/out/hn-t100/` | 2,559 | `dc16e4da…` |
| **GD92** | `kaggle_sim/out/hn-g92/` | 2,632 | `cd913759…` |
| `CC_TIGHT_T170` (doi chieu cap 0.05/5%) | `java/devrun/CC_TIGHT_T170/` | 1,009 | `fad1b63e…` |

- Equity NGAY: dong `Update YYYYMMDD HH:MM => b:… unP:…` trong `logs/sim.out` (1 dong/ngay).
- Du lieu 1m: `ticker_YYYYMMDD.bin.gz` (phut **UTC**, mo bang `research/analysis/jbin.py`).

**Mui gio (BAT BUOC xu ly):** cot `start`/`end` cua `printDone.csv` la **GMT+7** (local).
Moi phep so sanh voi du lieu 1m (UTC) phai **tru 7h** truoc.

## 3. Cua so su kien (dinh nghia TRUOC)

- **W (UTC)** = `2025-10-09 00:00Z .. 2025-10-13 23:59Z` (5 ngay UTC).
- Tuong duong local GMT+7: `2025-10-09 07:00 .. 2025-10-14 06:59`.
- **Ngay su kien E** = `2025-10-10` (UTC). (Su that da co: dinh exposure `52,151 USDT @ 2025-10-11 04:22`
  local = **2025-10-10 21:22 UTC** ⇒ dinh exposure nam TRONG ngay su kien.)
- Leg "dang mo trong W" = `start <= W_end` VA `end >= W_start` (sau khi doi sang UTC).

## 4. VIEC A — xac nhan su kien bang du lieu 1m (mo ta, khong suy dien)

Mo `ticker_20251008..20251013`, truc **BTC/ETH** va phan bo **ALT** (moi symbol `*USDT` tru BTC/ETH
va stablecoin `USDC/USDT/DAI/FDUSD/TUSD/BUSD/EUR/FDUSD`).

1. **Bien do ngay**: `r_d = close(23:59 d)/close(23:59 d-1) - 1` cho tung coin, tung ngay trong W.
2. **Phan bo ALT theo NGAY**: p1/p10/p50/p90/p99 + worst-20 coin cua `r_d` (moi ngay trong W).
3. **Phan bo ALT theo GIO**: `r_h = close(h)/close(h-1) - 1`, gop theo gio trong W; in
   p1/p10/p50/p90/p99 cua tung gio cho 24 gio cua ngay E + 12 gio truoc/sau.
4. **Gio cao diem**: gio (UTC) co `p1` ALT thap nhat, va **phut** BTC cham day trong W.
5. **Sap bao nhieu** = `close cuoi W / close dau W - 1` theo coin: p1/p10/p50/p90/p99, worst-20.

## 5. VIEC B — he da bi gi trong W (artifact that)

1. **Leg dang mo trong W** (4 nen): so leg, `Σpnl` (tich luy DAT duoc trong W theo `end`),
   top-10 leg theo `margin`, **coin nang nhat** (margin lon nhat tai dinh).
2. **`sim.out`**: `max drop equity trong W` = `min_t(eq_t / max_{s<=t} eq_s - 1)` voi `t` ∈ W,
   neo `max` tinh tu dau W.
3. **% LAI LUY KE bi xoa**: `lai_truoc = eq(W_start) - CAPITAL_START`,
   `lai_sau = eq(W_end) - CAPITAL_START`; `xoa = (lai_truoc - lai_sau)/lai_truoc`.
4. **% lai 2025 truoc vs sau su kien**: `Σpnl` leg co `end` trong 2025 VA `end < W_start` (truoc)
   vs `end > W_end` (sau) vs `end ∈ W` (trong).

`CAPITAL_START = 35,000`.

## 6. VIEC C — stress execution (khai bao TRUOC)

**Mo hinh chi phi (do TRUOC, kiem bang du lieu):** tren `printDone.csv` cua CA 4 nen, quan he
`pnl = margin*(profit/100) - c*margin - funding` dung **tuyet doi tuyet doi** voi **`c = 0.008`**
(`c` = 0.008000 o min = p1 = med = p99 = max tren 100% leg cua T170/KEEPLEG0/T100/GD92;
`profit` = rate GROSS %, `funding` = phi funding da tra). Khop comment `Configs.java:164` "= 0.008"
(0.002 fee 1 chieu + 2×0.003 slippage). ⇒ **cost/leg = `0.008 × margin`**.

1. **Slip/phi x k** (k = 2, 5, 10) tren **MOI leg co `end ∈ W`**:
   `ΔPnL = -(k-1) × 0.008 × Σ margin(W)` ⇒ `ΔCAGR`.
   (Khong doi so leg/khong doi diem — chi doi chi phi, dung tinh than `SIM_*_RATE` override.)
2. **1 coin ve -90% / -100% trong khi dang giu**: thiet hai = `(0.90 | 1.00) × max_t(margin_1coin/equity(t))`.
   - **KHONG cap**: lay `max_t` do tu artifact (so da co: T170 9.77% / T100 28.51% / GD92 14.38%).
   - **CO cap `CONC_CAP_PERCOIN_PCT=0.15`**: tran ty le ve **15%** ⇒ thiet hai <= `0.15×0.90 = 13.5%`.
   - **Do lai bang replay offline** (KHONG phai sim): xet leg theo thu tu `start`, giu `margin mo/coin`,
     **chan HAN leg moi** neu `(margin_coin + margin_leg)/equity(ngay) > 0.15`; do lai `n leg`,
     `Σpnl`, `max_t(margin_coin/equity)` ⇒ so sanh "co/khong cap". Ghi ro day la **xap xi**,
     khong phai sim (equity dung moc NGAY, khong phai moc phut).
   - **Doi chieu artifact THAT**: `CC_TIGHT_T170` (cap 0.05/5%) — chay that, dung de kiem huong.

## 7. VIEC D — kich ban "1–2 lenh lech" (trong tam)

1. Lay **1 va 2 leg co `margin` lon nhat dang mo trong W** (moi nen).
2. Kich ban lech: leg do **khong thoat duoc** (exit fail) ⇒ chiu `-X%` (X = 20/50/80/90/100) tren margin,
   thay `pnl` goc bang `-X%×margin`. Tinh lai **ΔPnL toan ky, ΔCAGR, ΔmaxDD** (equity ngay).
3. **Nguong xoa sach** (goc cau hoi owner): voi leg lon nhat,
   `X*_nam  = lai 2025 / margin_leg`, `X*_ky = (eq_end - CAPITAL_START) / margin_leg`
   (giu 2 leg: `Σpnl_nam / (m1+m2)`). Bao `X*` theo % margin.
   - `lai 2025` = `eq(2025-12-31) - eq(2024-12-31)` (theo dong `sim.out`).

## 8. Nguong dien giai (chot TRUOC)

- **BOUND** neu `X*_nam > 100%` (mot su kien lech toi da khong the xoa sach lai 1 nam).
- **KHONG BOUND** neu ton tai kich ban `X <= 100%` (lech THAT, khong phai gia dinh) xoa sach lai 1 nam.
- Voi stress chi phi: coi la **nghiem trong** neu `ΔPnL(W) > 50%` lai ca nam 2025.
- Moi so trung binh phai kem **so ca nhan (per-event)**, khong duoc trinh bay nhu ky vong.

## 9. Cach bao cao (bat buoc)

- Moi bang ghi **md5 printDone** va **n leg** de cong parity.
- Moi ket luan RUI RO phai noi ro **co/khong co CI**; so mot-lan-quan-sat khong duoc goi la "tot hon".
- Khong tu tich hop gi vao code/profile.
