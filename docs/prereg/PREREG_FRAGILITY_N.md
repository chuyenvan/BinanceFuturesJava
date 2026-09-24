# PREREG_FRAGILITY_N — do do venh (`fragility`) theo n va kiem gia thuyet "danh 1x nen khong chay duoc tk"

Chot **TRUOC khi do** — 2026-09-24. Moi phep do trong `docs/result/RESULT_FRAGILITY_N.md` phai nam
trong danh sach duoi day; phat sinh ngoai danh sach thi ghi ro la **kham pha (exploratory)**,
khong duoc dung lam ket luan.

## 0. Cau hoi cua owner (nguyen van, nguyen van)

1. *"can tang nhieu lenh, giam ti le lai cung ok, nhung toi nghi no GIAM RUI RO: cung 1 PNL ma tap
   lenh nho thi chi it lenh khac voi binh thuong khac test la ket qua rat venh; con so luong lenh
   lon thi cac khac biet o mot vai lenh o backtest so voi live se ko anh huong lon"*
2. *"toi san sang voi maxDD co the len 30 hay 40% deu ok — no chi la so lo TAM THOI, ko chay duoc
   tk vi danh 1x"*

⇒ Phai tach: (i) nhieu NGau NHIEN, (ii) RUI RO, (iii) lech HE THONG, (iv) gia thuyet **1x**.

## 1. Rang buoc (BAT BUOC)

- **KHONG chay sim moi**, KHONG Java, KHONG Claude Code. **Thuan Python offline** tren artifact DA CO.
- **DEV only** (2021-07-01 .. 2025-12-30). **Khong doc dung 2026**. Khong dung `_SEALED_2026_*`.
- Ket qua trung gian: `/home/ubuntu/fragility/`. Script: `research/analysis/fragility_n.py`.
- Khong push.

## 2. Du lieu (chi doc)

| nhan | thu muc | n leg |
|---|---|---|
| **T170** | `/home/ubuntu/kaggle_sim/out/t170-x1-2021/` | 1,089 |
| **T100** | `/home/ubuntu/kaggle_sim/out/hn-t100/` | 2,559 |
| **GD92** | `/home/ubuntu/kaggle_sim/out/hn-g92/` | 2,632 |
| bien the | `/home/ubuntu/kaggle_sim/out/{tl-l1,tl-l2,tl-l3,pc-close,tc-cap,hn-g-hi,hn-g-la,hn-g-cp,hn-t-hi,hn-t-la,hn-t-cp}/` | 1,039..2,640 |
| TH (Oracle, tham chieu) | `/home/ubuntu/java/devrun/{X1_TH_GAP05_2021,X1_TH_GAP12_2021,X1_TH_WEAK17_2021}/` | — |

Moi run phai co `storage/printDone.csv` **va** `logs/sim.out` (hoac `sim.out.gz`). Thieu mot trong
hai ⇒ **ghi ro "KHONG DO DUOC", KHONG bia so**.

`printDone.csv` khong phai CSV chuan: field thu 8 la `'<yyyy-mm-dd HH:MM:SS>`. Cach doc da chot:
bo ky tu `'` roi `split(',')`; 25 cot; chi so (0-based) dung:
`sym=0, side=1, entry=2, profit=4, status=5, start=6, end=8, quantity=13, margin=14, pnl=15`.

## 3. VIEC A — kiem gia thuyet 1x (dinh nghia chot TRUOC)

- **A1 leverage**: `lv = margin / (quantity * entry)`. `1x isolated` ⇔ `lv = 1` cho **moi** leg
  (dung sai 1e-6). Bao: so leg `lv=1` / tong, `min/max lv`, va so leg `lv > 1.05`.
- **A2 max concurrent margin** (quet su kien `start`/`end` tren moc PHUT): `S(t) = Σ margin` cua cac
  leg co `start ≤ t ≤ end`. Tai cung 1 moc phut co ca `start` lan `end`, bao **HAI bien**:
  `peak_starts_first` (xu ly het start roi moi end — CAN TREN) va `peak_ends_first` (CAN DUOI).
  Cung bao `t_peak`.
- **A3 equity tai `t_peak`**: `E(t)` = gia tri cuoi cung cua chuoi equity NGAY trong `sim.out`
  tai ngay `≤ t_peak`, voi `equity = b + unP` (`RX` cua `c3_rates.py`). Bao `peak/35000` (von goc)
  va `peak/E(t_peak)`.
- **A4 max margin/equity theo thoi gian**: `R = max_t S(t)/E(t)`; **va** kiem cheo bang chuoi NGAY
  cua `sim.out`: `max` (`date2MarginMax`) / `(b+unP)` cung ngay.
- **A5 pha gia thuyet**: neu `R > 1.0` (bat ky moc nao co exposure > equity) ⇒ **BAO DO: gia thuyet
  1x bi pha** (khong the chay tk). Nguoc lai: `R < 1` tren MOI moc ⇒ **khong the chay tk**.
- **A6 `lo TAM THOI` vs `MAT THAT`**:
  - (a) `mat that` do **delist khi dang giu**: `printDone` **khong** co truong nguyen nhan delist
    (`status` chi co `STOP_MARKET_DONE` / `STOP_LOSS_DONE`), va **khong** co dataset lifecycle
    phu 2021-2025 trong may. ⇒ Do bang **proxy da chot truoc**: leg co `pnl/margin ≤ -0.90`
    (mat ≥ 90% margin da trien khai — dau vet duy nhat quan sat duoc cua "vi the ve 0"). Bao:
    so leg, `Σpnl`, `%` cua tong pnl. Neu proxy = 0 ⇒ ghi ro "**khong co dau vet mat-that
    quan sat duoc trong mau**", KHONG duoc ket luan "khong the xay ra".
  - (b) **tran mat-that 1 coin** = `max` tren moi coin cua `max_t (margin coin/tai t) / E(t)` × 100.
    Day la **can tren** cua thiet hai neu coin do ve 0 ngay tai dinh diem (1x ⇒ mat = margin).
- **A7 chuan rui ro**: `maxDD ≤ 40%/nam` (owner noi 2026-09-24). Ghi ro `maxDD` **KHONG** phai rao
  dang chan (T170/T100/GD92 deu duoi tran CU 30%).

## 4. VIEC B — do venh nho-n vs lon-n (moi run)

- **B1** `n`, `meanP = mean(pnl)`, `SD`, `SE`:
  - `SE_naive = SD/sqrt(n)`;
  - `SE_boot` = **bootstrap block-72h** tren leg: `blk = floor((start − 2021-07-01)/72h)`, resample
    `n_blk` block co hoan lai, tinh `mean(pnl)` moi rep; `2000` rep, `seed 20260905`
    (dung `BLOCK_H/NREP/SEED` cua `research/analysis/c3_rates.py`).
  - **`relSE = SE_boot/meanP`** (va `relSE_naive`). Kiem scaling `1/sqrt(n)`: bao
    `relSE × sqrt(n)` — neu ~hang so ⇒ dung scaling.
- **B2** **MDE95** tren `pnl/leg` = `1.96 × SE_boot` (USDT/leg). Bao ca `MDE/meanP` (%).
- **B3** **Drop-top-K** (bo theo `pnl`): K = **1**, **5**, `ceil(0.01n)`, `ceil(0.05n)`;
  ban doi xung: bo **best** va bo **worst**.
  Chi tieu: `ΔPnL% = (Σpnl_moi − Σpnl_cu)/Σpnl_cu × 100`;
  `ΔmaxDD` (pp) va `ΔUW` (ngay) tren **duong equity proxy** = cumulative `Σpnl` theo `end`,
  resample NGAY (lay gia tri cuoi ngay). `maxDD_hat`/`UW_hat` la **proxy** (khong co mark-to-market
  tung phut); bao kem gia tri THAT tu `sim.out` (`maxDD`/`UW` toan ky) de lo doc bias.
- **B4** **Tap trung PnL**: `share_q = Σpnl(top q% leg theo pnl) / Σpnl` × 100 voi q = 1, 5, 10.
- **B5** **Do venh theo nam**: `ret%` tung nam tu **duong equity THAT** (`sim.out`, `b+unP`,
  `year_end/year_start − 1`); bao `SD` va `range = max − min` tren cac nam 2021(1 nua)..2025.
- **B6** **N_eff**:
  - (a) *overlap*: voi moi `sym`, gom leg co khoang `[start,end]` **giao nhau hoac cham nhau**
    (union-find) ⇒ `N_eff_a` = tong so cum tren moi sym; ty le `N_eff_a/n`.
  - (b) *tuan lich* (ISO week): `N_eff_b` = so tuan ISO co leg; ty le `N_eff_b/n`.
  - (c) tham chieu: so ngay co leg.
- **B7** **Tap trung 1 coin** `%` = `max` tren `(sym,end)` cua `Σmargin / E(ngay)` × 100
  (cong thuc `conc_max` cua `gd92xexit_score.py`, tai dung de so sanh duoc voi `RISK_APPETITE.md`).

## 5. Cau tra loi cu the bat buoc

- **(a)** Bo **1%** va **2%** so lenh, theo **3 kieu chon**:
  1. `best` (pnl cao nhat), 2. `worst` (pnl thap nhat), 3. `random` (**2000** lan, seed **20260905**).
  Bao `Δtong PnL%`. Kieu `random` bao `mean [p5, p95]`.
- **(b)** Neu **1 coin ve 0** thi mat bao nhieu `% equity`: = A6(b), bao per run (T170/T100/GD92),
  kem ten coin + thoi diem; va top-5 coin.

## 6. Tien dinh (chot TRUOC, de chong dien giai sau)

- **P1**: `SE ~ 1/sqrt(n)` ⇒ `relSE(T100)/relSE(T170) ≈ sqrt(1089/2559) = 0.652`;
  `relSE(GD92)/relSE(T170) ≈ sqrt(1089/2632) = 0.643`.
- **P2**: `ΔPnL%` khi bo `top-1%` `[best]` se **GIAM** tu T170 → T100 → GD92 (n lon hon ⇒ mot vai
  leg it anh huong hon). Neu nguoc lai ⇒ luan diem owner **dung** o cho nay.
- **P3**: `N_eff/n` < 0.5 o **moi** run (leg chong lan nhau manh) ⇒ `n` la con so **danh nghia**,
  canh bao "n lon" khong dong nghia "nhieu bet doc lap".
- **P4**: `R = max S(t)/E(t) < 1` o ca 3 run (danh 1x, exposure << equity).
- **P5**: A6(a) proxy mat-that = **0 leg** (khong co leg `pnl/margin ≤ -0.90`) ⇒ "lo tam thoi" dung
  trong mau; nhung A6(b) > 0 ⇒ kenh mat-that **ton tai** qua tap trung 1 coin.

## 7. Luan diem owner — chot cach phan xu TRUOC

- DUNG neu: `relSE` giam theo `1/sqrt(n)` **VA** rui ro (maxDD/UW/venh nam) khong tang theo n.
- SAI/THIEU neu: `ΔPnL%` khi bo top-1%/5% **khong** giam theo n, hoac `N_eff/n` giam manh theo n,
  hoac ton tai kenh `mat that` (A6) khong phu thuoc n.
- **TUYET DOI KHONG** dung ket qua nay de tich hop/go bien the — chi la phep do.
