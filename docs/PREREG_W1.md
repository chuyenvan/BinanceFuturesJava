# PREREG_W1 — quet cac truc CHUA TUNG SWEEP tren nen C2b

Commit TRUOC khi chay. Khong sua sau khi thay so. Null co tinh thong tin.
Ngay: 2026-09-05. Nhanh `module`. Nen: `C2b` (`profiles/c2b_min.properties`,
PROFILE_HASH=a2f859b2463108fe, b:60390, 970 lenh, maxDD -13.12%, underwater 93 ngay,
md5 printDone `8f7afdfb27b15f5b6d4c886700def93c`).

## 0. Pham vi va rui ro NEU TRUOC

- Day la **quet KHAM PHA**, khong phai xac nhan. **Khong de cu ung vien baseline moi**
  tu batch nay, du o nao dep. Ung vien phai qua mot pre-reg xac nhan rieng sau.
- `sd(dCAGR)` exit params = **2.57pp**. Batch nay N=16 (15 o quet + 1 parity)
  => `E[max nhieu]` = 2.57*sqrt(2 ln 16) = **6.05pp**. (De bai neu N=18 => 6.1pp;
  luoi liet ke ra dung 15 o, nen dung 16.) **CAM chon o co equity cao nhat.**
- Equity bao cao o muc rieng, dan nhan "khong phai tieu chi".
- **Confound da biet cua truc F (`DCA_GRID_WEIGHTS`)**: tong trong so giu = 1.0 nen
  `ladder` khong doi, nhung trong so leg 0 giam (1.0 -> 0.5 -> 0.4) => **size lenh dau
  giam 50%/60%** dong thoi voi viec bat them leg DCA. Vay truc F **tron 2 thay doi**:
  (i) bat co che DCA, (ii) ha sizing lenh dau. Theo RUNBOOK muc 4, sizing KHONG do duoc
  tren DEV. => du F co ra so dep, **khong duoc doc la "DCA co tac dung"**; chi duoc ket
  luan "co/khong co tin hieu tren cap (DCA on + size dau giam)". Ghi truoc de khong
  dien giai nham sau.
- Chi 1 realization DEV; maxDD/underwater la thong ke `n_eff` nho, do lai chinh no
  bang cach chon max se lech duong. Chung chi dung lam **rang buoc loai**, khong lam diem.

## 1. Xac nhan key khong tro (da lam TRUOC khi chay)

`grep -rn` trong `src/main` + `DumpConfig` voi tung profile thu. Ket qua:
ca 8 key deu doc qua `Cfg.get` va deu doi gia tri hieu dung trong `DumpConfig`.
**Khong loai key nao khoi grid.**

| key | doc o | bang chung DumpConfig |
|---|---|---|
| `SIM_TS_MAX_GAP` | `Configs.java:468` -> `TS_MAX_GAP`, dung o `TradeUtils.java:31` | `TS_MAX_GAP` + `derived...cap_strong` doi |
| `SIM_TS_MAX_GAP_WEAK` | `Configs.java:469` -> `TS_MAX_GAP_WEAK`, `TradeUtils.java:30` | `cap_weak` + `sl_at_arm WEAK` doi |
| `SIM_TS_PNOPUMP_WEAK_THR` | `Configs.java:465` -> `TS_PNOPUMP_WEAK_THR_OVR`, doc qua accessor `Configs.java:390` | `TS_PNOPUMP_WEAK_THR_OVR` + nguong STRONG/WEAK doi |
| `SIM_MIN_MOMENTUM_15M` | `Configs.java:457` | `MIN_MOMENTUM_15M` + `derived.gate_thr@*` doi |
| `SIM_PREDICT_SYMBOL_RATE_MAX` | `Configs.java:472` | `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` + `derived.candidate_score_max` doi |
| `DCA_GRID_WEIGHTS` | `Configs.java:189`, dung `DcaUtils.gridLegWeightRatio` | mang hieu dung doi, `CONFIG_HASH` doi |
| `DCA_GRID_SCALE` | `Configs.java:254` | doi |
| `SIM_RATE_PROFIT_STOP_MARKET` | `Configs.java:473` | `RATE_PROFIT_STOP_MARKET` + `derived.arm_roi` doi |

Xac nhan **chua tung sweep tren nen C2b**: `grep '^KEY' profiles/*.properties` cho thay
`SIM_TS_MAX_GAP` / `SIM_TS_MAX_GAP_WEAK` / `SIM_TS_PNOPUMP_WEAK_THR` /
`SIM_PREDICT_SYMBOL_RATE_MAX` **khong xuat hien trong bat ky profile nao**;
`SIM_MIN_MOMENTUM_15M` chi tung nhan 0.008 / 0.006 / 0.014052 (khong co huong SIET
0.010-0.012 tren nen C2b); `DCA_GRID_WEIGHTS` = `1,0,0,0` o **tat ca 24 profile**
(DCA tat hoan toan trong ca ho C2b).

## 2. Co hoc da biet cua truc A/B/C (viet truoc de doc ket qua khong bi bat ngo)

Trailing: `giveback = min(peak*TS_GIVEBACK_RATIO, cap)`, `TS_GIVEBACK_RATIO=0.5`, arm = 7%.
`cap = TS_MAX_GAP_WEAK` neu `symbolPred > TS_PNOPUMP_WEAK_THR`, nguoc lai `TS_MAX_GAP`.
=> cap chi RANG BUOC khi `peak > 2*cap`.

- Truc A (STRONG, cap 0.08 -> 0.05/0.12/0.16): cap rang buoc tu peak > 0.10 / 0.24 / 0.32.
  **Du bao truoc: A=0.16 gan nhu tro** (rat it lenh dat peak > 32%); A=0.12 tac dong nho;
  chi A=0.05 co the doi nhieu lenh. Neu A=0.12/0.16 ra gan y het parity thi do la
  **co hoc**, khong phai bang chung "truc khong co tac dung".
- Truc B (WEAK, cap 0.03 -> 0.015/0.05/0.08): 0.03 rang buoc tu peak > 0.06 < arm 0.07
  => **luon rang buoc** o baseline. 0.015 that chat them; 0.05 va 0.08 lam nhanh WEAK
  **trung voi STRONG tai arm** (`sl_at_arm` ca hai = 0.035).
- Truc C (ban le 0.29 -> 0.05/0.60): 88.55% hang admit co score < 0.30 => baseline
  ~88.6% lenh di nhanh STRONG (cap 8%). C=0.05 lat gan het sang WEAK (cap 3%, that);
  C=0.60 dua gan het/toan bo sang STRONG. **C la don bay manh nhat cua ba truc.**

## 3. Grid — one-at-a-time quanh baseline, tat ca qua PROFILE COPY

Cam dat env tien to `SIM_`/`DCA_` khi da co `TRADING_PROFILE` (bay 2).
Moi profile = ban sao `c2b_min.properties` sua/them dung 1 dong (truc G: 2 dong).

| tag | profile | thay doi | baseline |
|---|---|---|---|
| `W1_parity` | `c2b_min.properties` | khong doi | — |
| `W1_A05` `W1_A12` `W1_A16` | `w1_a{05,12,16}` | `SIM_TS_MAX_GAP` = 0.05 / 0.12 / 0.16 | 0.08 |
| `W1_B015` `W1_B05` `W1_B08` | `w1_b{015,05,08}` | `SIM_TS_MAX_GAP_WEAK` = 0.015 / 0.05 / 0.08 | 0.03 |
| `W1_C005` `W1_C060` | `w1_c{005,060}` | `SIM_TS_PNOPUMP_WEAK_THR` = 0.05 / 0.60 | 0.29 |
| `W1_D010` `W1_D012` | `w1_d{010,012}` | `SIM_MIN_MOMENTUM_15M` = 0.010 / 0.012 | 0.008 |
| `W1_E010` `W1_E012` | `w1_e{010,012}` | `SIM_PREDICT_SYMBOL_RATE_MAX` = 0.10 / 0.12 | 0.15 |
| `W1_F55` `W1_F433` | `w1_f{55,433}` | `DCA_GRID_WEIGHTS` = `0.5,0.5,0,0` / `0.4,0.3,0.3,0` | `1,0,0,0` |
| `W1_G_A8S175` | `w1_g_a8s175` | `SIM_RATE_PROFIT_STOP_MARKET`=0.08 + `DCA_GRID_SCALE`=1.75 | 0.07 / 1.5 |

Truc G khong phai truc quet: `N4_a8s175` da tung ra 61,148 nhung **chua tung do
maxDD/quy/underwater**. Chay lai tren jar + dataset hien tai de do cho du va de so sanh
duoc voi phan con lai cua batch (ban cu chay 2026-09-03, khac jar).

1 dataset dung chung: `/home/ubuntu/wfo_ds_clean` (da co san, 1.8G — khong build lai,
dia con 16G). `SIM_END_DATE=20240630`, DEV 2022-01-01..2024-06-30. **Khong chay VAL.**

## 4. Do cai gi — RATE la tieu chi, equity thi khong

Voi moi truc, bao theo tung muc:
- `TSloss%` = n(`STOP_LOSS_DONE`) / n tong (day la **time-stop 168h**, khong phai SL)
- `win%` = n(profit > 0) / n tong
- `mean(profit | STOP_MARKET_DONE)` va `mean(profit | STOP_LOSS_DONE)`
- so lenh `n`, `mean(margin)`
- maxDD, underwater (ngay), return tung quy (10 quy DEV)

## 5. Quy tac quyet dinh — CHOT TRUOC KHI THAY SO

**Phan quyet dua tren CAU TRUC DON DIEU doc truc, khong phai o don le.**

Mot truc duoc coi la **CO TIN HIEU** khi va chi khi:
1. co it nhat **mot rate** don dieu qua **toan bo** cac muc cua truc do
   (ke ca muc baseline nam dung vi tri cua no tren truc), VA
2. co it nhat mot muc thoa **toan bo** rang buoc cung.

Truc khong co rate nao don dieu => **ghi null, dong truc**.
Don dieu = khong doi dau chenh lech giua cac muc lien tiep khi sap theo gia tri param
(bang nhau tuyet doi tinh la khong vi pham chi khi < 0.5% tuong doi; ghi ro neu xay ra).

**Rang buoc CUNG (vi pham la loai, bat ke moi thu khac):**
- maxDD <= 15%
- underwater <= 120 ngay
- khong nam am
- khong quy < -5%
- so lenh >= 600

## 6. Ket qua co the co, va ta se ket luan gi

- Truc co rate don dieu + it nhat 1 muc pass rang buoc => ghi "CO TIN HIEU", mo the
  cho mot pre-reg xac nhan rieng. **Khong de cu baseline moi o day.**
- Truc khong don dieu => null.
- Truc don dieu nhung **khong muc nao** pass rang buoc cung => ghi "don dieu nhung
  loai boi rang buoc", cung la null cho muc dich ung dung.
- Parity `W1_parity` md5 != `8f7afdfb27b15f5b6d4c886700def93c` => **DUNG CA BATCH**,
  khong bao so nao.

## 7. Ky thuat

`rc=1` khong phai fail (bay 1). Tieu chi hoan tat: log co `done:` + `b:` va
`storage/printDone.csv` co dong. 1 slot JVM, chay tuan tu, `pgrep java` rong truoc khi
bat dau. `df -h /` truoc khi chay. Khong `rm -rf` dataset dung chung (`wfo_ds_clean` la
tai san co san cua repo, khong phai dataset batch nay tao ra).
