# PREREG_HEDGE_OVERLAY_A — Phuong an A: OVERLAY hedge BTC (counterfactual)

Ngay: 2026-09-20. Branch `module`. Tac gia: agent executor (MASTER thiet ke, Uni so huu).
Trang thai: **PRE-REGISTRATION — chot TRUOC khi tinh bat ky so nao cua gia thuyet.**

Tien de: `docs/design/DESIGN_HEDGED_BOOK.md` (commit `8a081ae`) da RECON xong TASK 2 va DUNG o
cong thiet ke: core Java KHONG mo duoc SELL doc lap (`createOrderSELL` go tu `5f40a90`),
khong co co che portfolio-level leg, va mot hedged book "dung nghia" bat buoc cham
`BudgetManagerSimple.equityNow()` + `marginRunning` => se DOI luon tap lenh long duoc chon
=> confound ngay o bien do chinh. MASTER da chot chay **Phuong an A (OVERLAY)** truoc.

## 0. Ky luat cua vong nay

- **KHONG sua bat ky file `.java` nao. KHONG chay sim Java.** Toan bo lam bang Python tren
  du lieu da co (`printDone.csv` + `sim.out` cua T170 + BTC 1h + funding BTCUSDT).
- Sach long giu **NGUYEN VEN byte-identical** voi T170 (`md5 efb793e2` thoa hien nhien vi
  khong co gi duoc chay lai). Hedge la mot lop PHU TINH, khong phan hoi vao sizing/admission.
- Neu trong luc code phat hien loi thiet ke va phai sua, phai ghi ro trong RESULT la da sua
  **truoc** hay **sau** khi thay ket qua cuoi.

## 1. Gia thuyet co the bac bo

`docs/notes/power_wall.md` xac dinh duong power duy nhat con song la **tang so cuoc doc lap**.
`docs/result/NBETS_RESULT.md` muc 4.2 do ICC (mot chieu, ANOVA, cohort = ngay vao lenh) = **+0.2468**
tren C2b, on dinh 0.16-0.27 tren 11 run => tran `1/ICC` ~ 4 cuoc doc lap/ngay.

**H1 (co the bac bo):** Phan lon tuong quan trong-ngay giua cac lenh long la do **market beta
chung** (moi lenh long cung chiu beta BTC). Neu vay, tru di mot overlay short BTC theo beta
rolling se lam **ICC giam dang ke** va **beta cua so giam ve ~0**, trong khi khong doi sach long.

**H0 (NULL):** Tuong quan trong-ngay KHONG chu yeu den tu market beta (ma den tu co che chung
khac: cung gate, cung sizing, cung regime thanh khoan/altseason, cung dang pump-lottery) =>
hedge beta KHONG lam ICC giam dang ke.

H1 co the bac bo bang so: neu ICC sau hedge khong giam (hoac giam < 15% tuong doi) thi H1 sai.

**Du bao truoc (de sau khong "giai thich xuoi" theo ket qua):** TASK1 da do %beta FULL cua T170
chi **3.9%** tong loi nhuan log va R2 chi 3-9% => phan phuong sai ngay giai thich duoc boi BTC
la NHO. Do do agent **du bao H1 nhieu kha nang SAI** (ICC giam it). Ghi truoc de RESULT khong
bi doc nguoc.

## 2. Nguon du lieu (chinh xac, chi doc)

| Thu | Duong dan | Ghi chu |
|---|---|---|
| Sach lenh T170 | `/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv` | 1089 lenh. Cot `margin` = **NOTIONAL** (= quantity x entry, da verify o TASK1 + `MaeDistributionProbe.java`). `start`/`end` la gio **GMT+7 naive**. |
| Equity ngay T170 | `.../X1_GS_T170_2021/logs/sim.out` | Tai su dung `research/analysis/c3_rates.py::equity()` (regex `Update YYYYMMDD ... b:<B> ... unP:<U>`, equity = B+U, ban ghi cuoi moi ngay, lich GMT+7). |
| Gia BTC 1h | `/home/ubuntu/java/fsrun/CLOSES_1H.bin` | Tai su dung `research/analysis/trend_rank_ic.py::load_closes()`; `symId=1`; `ctime = open_time + 1h` (causal); loader **da loc `ts < 2026-01-01 UTC`** => HOLDOUT 2026 khong bi cham. |
| Funding BTCUSDT | Aerospike **local** `127.0.0.1:3222`, ns=`test`, set=`funding_data`, key=`BTCUSDT`, bin `f_data` (Snappy(JSON ts->rate)) | **Dung nguon THAT ma engine doc** (`DataManagerAerospikeFloatSim.getAllFundingMap()` doc chinh set/bin nay). **KHONG** dung `label_15m/funding_label_*.pb` hay `claudedata/funding_lf.bin` (do la label dataset ML, khong phai funding rate). Dump 1 lan ra `/home/ubuntu/hedge_a/funding_btcusdt.csv`, khong ghi nguoc vao Aerospike. |

Cua so phan tich: **2021-07-01 .. 2025-12-31** (dung cua so cua TASK1, `beta_decomp_t170.py`).
HOLDOUT 2026 **khong** duoc cham o bat ky buoc nao.

## 3. Beta rolling CAUSAL (khong lookahead)

Dieu chinh `beta_decomp_t170.py` tu FULL-period sang rolling. Dinh nghia:

- Chuoi ngay (lich GMT+7, dong he quy chieu voi `sim.out`):
  - `dPnL(d)` = `equity(d) - equity(d-1)` (loi nhuan USDT trong ngay `d` cua sach long).
  - `Nopen(d)` = **trung binh so hoc cua tong notional long dang mo** tren 24 moc gio cua ngay `d`
    (Sum notional cac lenh co `start <= t < end`).
  - `y(d) = dPnL(d) / Nopen(d)` (loi nhuan tren MOT DON VI notional long) — chi dinh nghia khi
    `Nopen(d) > 0`.
  - `x(d) = log(BTC_close(d) / BTC_close(d-1))`, gia BTC 1h gan nhat <= 00:00 UTC cua ngay `d`
    (dung quy uoc ghep gio da kiem o TASK1: delta_h = 0.0).
- `beta_roll(D)` = he so goc OLS cua `y` tren `x` uoc luong tren **N = 60 ngay lich gan nhat
  KET THUC o ngay D-1** (tuc chi dung `d <= D-1`, khong bao gio dung ngay D hay tuong lai).
  Yeu cau toi thieu **20 quan sat hop le** (`Nopen > 0` va `x` huu han) trong cua so; neu khong
  du, `beta_roll(D) = 0` (KHONG hedge) — quy tac nay chot truoc, khong doi sau.
- Trong mot ngay D, `beta_roll` GIU NGUYEN cho ca 24 moc rebalance (beta cap nhat 1 lan/ngay,
  hedge notional cap nhat 1 lan/gio theo `Nopen(t)` thuc te).

**Vi sao N = 60 ngay (chot 1 gia tri duy nhat, KHONG do nhieu N roi chon cai dep):**
(i) T170 la sach THUA — phan lon gio khong co vi the nao mo (NBETS do C2b: 62.5% so gio trong),
nen mot cua so 30 ngay chi cho ~15-20 quan sat hop le => SE(beta) qua lon;
(ii) TASK1 do R2 cua hoi quy beta ngay chi **3-9%** => beta von da rat nhieu, can n lon;
(iii) 60 ngay la can tren cua khoang MASTER cho phep (30-60), va van du ngan de bat duoc thay doi
regime trong nam. **Khong chay bat ky N nao khac.**

## 4. Tan suat rebalance va hedge notional

- Rebalance **moi 1 gio**, tren dung luoi `ctime` cua `CLOSES_1H.bin` (khop tan suat du lieu).
- Tai moc `t`: `hedge_notional(t) = beta_roll(ngay cua t) x Sum notional_long dang mo tai t`
  (vi the **SHORT** BTC co notional bang so do). `Sum notional` tinh tu `printDone.csv` voi quy
  uoc lenh mo tren `[start, end)` (gio GMT+7 quy ve UTC bang `-7h`).
- **Khong co deadband, khong co nguong rebalance** (rebalance dung muc tieu moi gio). Ly do: deadband
  la mot bac tu do co the dieu chinh sau khi thay so; bo no => khong con cho dredging, doi lai
  phai tra phi giao dich day du (muc 6).
- Neu `beta_roll < 0` thi `hedge_notional < 0` (tuc LONG BTC). Cho phep, khong chan — chan se la
  mot lua chon tuy y them.

## 5. PnL hedge moi khoang `[t, t+1h)` — DAU DUNG THEO BINANCE THAT

`hedge_pnl(t) = price_pnl(t) + funding_pnl(t) - cost(t)`

1. **Price PnL (SHORT):** `price_pnl(t) = -hedge_notional(t) x (P(t+1h)/P(t) - 1)`
   (short lai khi BTC giam). Dung **simple return**, khong log, vi PnL USDT cua mot vi the
   notional co dinh trong mot buoc la tuyen tinh theo simple return.
2. **Funding PnL (SHORT) — dau XAC DINH LAI DOC LAP, KHONG ke thua bug:**
   Quy uoc Binance THAT: khi `funding_rate > 0` thi **LONG TRA, SHORT NHAN**; khi `rate < 0` thi
   nguoc lai. Vay voi vi the SHORT: `funding_pnl = + hedge_notional x rate` (DUONG khi rate > 0).
   🔴 Day la **NGUOC DAU** voi `OrderTargetInfoTest.computeFundingOnClose()` cho `side == SELL`
   (code do mo hinh short TRA khi rate duong — bug da biet, tu danh dau `REVIEW-POINT`).
   Overlay nay viet doc lap va **khong** goi code Java do.
   **Moc ap dung:** funding Binance thanh toan **roi rac** tai 00:00 / 08:00 / 16:00 UTC (lay dung
   timestamp settlement co trong dump Aerospike). Neu timestamp settlement `s` roi vao `[t, t+1h)`
   thi cong `hedge_notional(t) x rate(s)`.
   *Ghi chu minh bach:* de bai MASTER goi y dang PRORATA `rate x (gio/8h)`. Overlay dung dang
   **roi rac tai settlement** vi do la co che THAT cua Binance (vi the tai dung thoi diem settlement
   moi bi tinh); hai cach cho tong bang nhau khi notional khong doi, chi khac o bien rebalance.
   Lua chon nay chot **truoc** khi tinh, khong phai sau.
3. **Chi phi giao dich:** muc 6.

## 6. Chi phi giao dich cua chan hedge BTC (khong bo qua)

`cost(t) = (taker_fee + slippage) x |hedge_notional(t) - hedge_notional(t-1h)|`
voi `taker_fee = 0.05%` (dong muc sim dang tinh cho chan long) va `slippage = 1bp`
=> he so **0.0006** tren notional QUAY VONG. Moc mo dau va dong cuoi ky cung tinh phi.
Day la mot gia dinh BAO THU HON so voi bo qua cost (de bai cho phep tu quyet); BTCUSDT that su
co taker 0.04% va spread mong hon 1bp, nen 0.0006 la can TREN cua chi phi that.

## 7. Phan bo hedge PnL/chi phi ve tung lenh long — **DA KHOA SAN, KHONG DOI**

Voi moi khoang rebalance `[t, t+1h)`, goi `w_j = notional_j x thoi_luong_chong_lan_j` cho moi
lenh long `j` dang mo trong khoang do. Phan cua lenh `i`:

```
share_i(t) = hedge_pnl(t) x  w_i / Sum_j w_j          (neu Sum_j w_j > 0)
```

`hedge_pnl_i = Sum_t share_i(t)`; `roi_hedged_i = (pnl_i + hedge_pnl_i) / margin_i`
(`margin` = notional, dung dinh nghia ROI cua `nbets_step3_crosssec.py`).
Neu `Sum_j w_j = 0` (khong lenh nao mo) thi `hedge_notional = 0` nen `hedge_pnl = 0`: khong co gi
de phan bo. Tong kiem tra bat buoc: `Sum_i hedge_pnl_i == Sum_t hedge_pnl(t)` (sai so < 1e-6).

## 8. Metric se bao cao — KHOA TRUOC, KHONG THEM BOT SAU KHI THAY KET QUA

(a) **Beta / alpha tang ngay**: chay dung phuong phap `beta_decomp_t170.py`
    (`ols_hac`, HAC maxlags=5, `r_s = log(equity_d/equity_{d-1})`, `r_b = log BTC`) tren
    chuoi `equity_hedged(d) = equity_T170(d) + cumsum(hedge_pnl den het ngay d)`.
    Bao: `beta`, `t_alpha`, `r2`, `pct_beta_of_total`. So voi T170 goc (**%beta FULL = 3.9%,
    |t(alpha)| = 4.372**).

(b) **ICC + n_eff**: dung **dung** `icc_anova()` cua `research/analysis/nbets_step3_crosssec.py`
    (ANOVA mot chieu, `x_i = pnl_i/margin_i`, cohort = ngay vao lenh `t0.dt.floor("1D")`,
    `n_eff(k) = k/(1+(k-1)*ICC)`, ICC am bi kep ve 0). KHONG tu viet cong thuc ICC khac.
    🔴 **Luu y quan trong da phat hien truoc khi chay:** con so **0.247 trong de bai la cua C2b**,
    KHONG phai cua T170 (`NBETS_RESULT.md` muc 4.2 chi do 11 run cu). Vi vay bao cao se tinh
    **ICC cua chinh sach T170 GOC** bang cung ham do lam baseline so sanh (apples-to-apples),
    va van in kem 0.2468 cua C2b lam moc lich su.

(c) **CAGR / maxDD / UW**: dung dung dinh nghia `c3_rates.py`:
    `CAGR = ((e_end/e_start)^(365.25/days) - 1) x 100`; `maxDD = min(e/cummax(e) - 1) x 100`;
    `UW` = so ngay duoi nuoc lien tiep dai nhat. So voi T170 goc (**equity 111.070, CAGR 29.27,
    maxDD -11.84, UW 92**). Bao them rang buoc cung theo nam (maxDD<=15, UW<=120, nam khong am,
    quy >= -5) nhu `x1_rates.py::hard_by_year`.

(d) **So cuoc doc lap hieu dung/ngay**: `k_bar` = trung binh so vi the giu dong thoi tren luoi
    60 phut **khi >= 1 vi the** (dung cach dem cua `nbets_step3_crosssec.py` muc 5.1, ap cho cua
    so T170), `n_eff(k_bar) = k_bar/(1+(k_bar-1)*ICC)`, va tran `1/ICC`. Bao ca truoc va sau hedge.
    (`k_bar` KHONG doi vi sach long khong doi; chi `ICC` doi.)

Khong bao cao metric nao khac o phan phan quyet. (Duoc phep in them so mo ta — vd quy mo hedge
notional, tong funding thu/chi, tong cost — nhung chung KHONG tham gia tieu chi muc 9.)

## 9. Tieu chi dien giai — KHOA TRUOC KHI TINH

Goi `ICC_0` = ICC cua sach T170 goc (tinh o muc 8b), `ICC_h` = ICC sau hedge;
`beta_0`, `beta_h` = he so beta tang ngay (muc 8a).

**TIN HIEU DUONG (du manh de CAN NHAC Phuong an B)** — phai dat **DONG THOI ca 4**:
1. `ICC_h <= 0.70 x ICC_0` (giam >= 30% tuong doi) **VA** `ICC_h < 0.15` tuyet doi;
2. `|beta_h| <= 0.30 x |beta_0|` (co che dung: beta that su bi trung hoa);
3. `maxDD_h >= 1.25 x maxDD_0` (theo dau am: khong xau di qua 25% tuong doi,
   tuc `maxDD_h >= -14.80%`) **VA** `CAGR_h > 0`;
4. `n_eff(k_bar)` tang >= **20%** so voi truoc hedge.

**NULL (khong dang dau tu Phuong an B)** neu: `ICC_h > 0.85 x ICC_0` (giam < 15% tuong doi)
**HOAC** `maxDD_h < 1.50 x maxDD_0` (xau di hon 50%, tuc thung hon -17.76%).

**KHONG KET LUAN DUOC (HON HOP)**: moi truong hop con lai. Khi do bao ro so va **KHONG** khuyen
nghi B (mac dinh la khong lam B khi khong co tin hieu duong ro rang).

Ly do chon nguong: (1) 30% giam ICC la muc toi thieu de doi dau bai power — `n_eff` ti le
`1/(1+(k-1)ICC)`, giam ICC 30% tu 0.25 ve 0.175 chi mua duoc he so `sd` ~1.1, con duoi muc do
la nhieu do luong; nguong tuyet doi 0.15 dam bao khong chi la "giam tren giay" tu mot `ICC_0`
von da thap. (2) Nguong beta la **kiem tra co che**: neu ICC giam ma beta khong giam thi khong
phai nho hedge. (3) Nguong maxDD la rang buoc khau vi rui ro cua Uni — hedge lam CAGR giam la
CHAP NHAN DUOC (da du bao o `DESIGN_HEDGED_BOOK.md` muc 6.4: short BTC 2023-2025 cat CAGR), nhung
lam rui ro XAU DI thi khong. (4) 20% `n_eff` la he qua so hoc cua (1), de lam kiem tra cheo.

## 10. Gioi han PHAI neu trong RESULT

1. **Day la COUNTERFACTUAL, khong phai he chay duoc live.** Hedge PnL **khong** phan hoi vao
   `equityNow()` nen **khong** doi sizing, va hedge notional **khong** an `marginRunning` nen
   **khong** doi admission (`throttle`). Neu chay that (Phuong an B), tap lenh long SE khac.
2. Hedge dung **mot** proxy thi truong duy nhat (BTC). Beta thuc cua mot sach altcoin con co
   thanh phan "alt-beta"/thanh khoan ma BTC khong bat duoc (TASK1 da ghi gioi han nay).
3. Vi the hedge gia dinh khop **dung gia close 1h**, khong mo hinh gap/thanh khoan trong gio,
   khong mo hinh funding cua chinh chan hedge bi thay doi boi kich thuoc lenh.
4. Chi phi 0.0006/quay vong la uoc tinh; khong mo hinh impact theo kich thuoc.
5. Khong mo hinh margin/thanh ly cua chan hedge (gia dinh von vo han cho chan short).
6. `equity` ngay lay tu `sim.out` la **snapshot cuoi ngay**, nen `dPnL(d)` chua dung chinh xac
   thoi diem intraday; beta rolling vi vay la beta **tan suat ngay**, khong phai tan suat gio.

## 11. Minh bach — nhung gi DA lam truoc khi commit pre-reg nay

- Doc code/tai lieu (`DESIGN_HEDGED_BOOK.md`, `beta_decomp_t170.py`, `nbets_step3_crosssec.py`,
  `c3_rates.py`, `x1_rates.py`, `FundingFeeManager.java`, `DataManagerAerospikeFloatSim.java`).
- **Da dump funding BTCUSDT tu Aerospike va in thong ke MO TA cua rieng chuoi funding**
  (so ban ghi, khoang thoi gian, mean/median/min/max, %rate duong, khoang cach settlement).
  Muc dich: xac minh nguon du lieu ton tai va dung dinh dang de viet duoc muc 2 cho chinh xac.
  **Khong** tinh bat ky metric nao cua gia thuyet (beta/ICC/CAGR/maxDD/n_eff) truoc pre-reg nay.
- Da xac dinh `funding_data` nam o namespace `test` (KHONG phai `ticker` nhu `config.properties`
  ghi cho box khac) tren Aerospike **local cua Oracle** (`127.0.0.1:3222`, container
  `aerospike-wfo`). **Khong** ket noi toi 242 (tien that) hay 226.
