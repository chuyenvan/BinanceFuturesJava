# PREREG_POSTPUMP_MEASURE — do tin hieu "post-pump" tren TOAN BO lenh (n=1089)

> **Pre-registration (chot thiet ke TRUOC khi chay).** Tai lieu MO TA (descriptive): chi doc
> du lieu da co, **KHONG chay sim, KHONG sua `.java`, KHONG push**. Khong chon nguong "tot nhat"
> sau khi nhin ket qua. Tat ca tieu chi duoi day duoc chot truoc khi chay script.

Noi tiep `docs/DIAG_ALT_IDIOSYNCRATIC_RISK.md` (commit `d02c7aa`): trong cua so UW dai nhat,
8 lenh sup co momentum 30d +57% vs doi chung -3.7% (n=8 qua nho). Cau hoi o day: tin hieu do
co that tren **toan bo 49 lenh sup** khong, va neu loc no se giet bao nhieu lenh LAI.

Nguon du lieu (dung san, khong tim lai):
- `printDone.csv` T170 `/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv`
  (n=1089, md5 `efb793e2468ca3a7318da0f0ad23d4fc`). Cot `profit` = % return/leg, `pnl` = USDT,
  `symbolPred` = score selector (1 - P(win)), `start` = entry (GMT+7, `%Y%m%d %H:%M`).
- `CLOSES_1H.bin` `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (BE `[ts>i8, sym>i2, c>f4]`, ts ms UTC,
  10.3M records, 627 symId, 2021-01-01 -> 2026-01-01).
- Map `selector_pred_out/symbol_map.csv` (`sym+"USDT"` -> `symId`; BTCUSDT = 1).

2026-09-17.

---

## 1. Nhom (dinh nghia GIU NGUYEN de so sanh duoc)

| nhom | dinh nghia | n |
|---|---|---|
| `SUP` | `profit <= -20` (dinh nghia cu trong DIAG) | **49** |
| `DOI_CHUNG` | phan con lai | **1040** |
| tong | | **1089** |

Ghi n thuc te khi chay (phai bang 49/1040/1089).

## 2. Feature

**Feature chinh (primary): `mom30d`** — return 30 ngay truoc do cua CHINH coin do, **causal**
(chi dung gia dong cua cho tinh den thoi diem vao lenh, khong dung gi sau entry):

```
mom30d (%) = ( close_entry / close_30d_ago - 1 ) * 100
  close_entry    = close 1h CUOI CUNG co ts <= entry_ts_ms
  close_30d_ago  = close 1h CUOI CUNG co ts <= entry_ts_ms - 720*3600*1000   (30 ngay = 720h)
  entry_ts_ms    = pd.to_datetime(start, "%Y%m%d %H:%M").tz_localize("Asia/Ho_Chi_Minh")
                   -> int64 (ns UTC) // 1e6
```

- `mom30d = NaN` neu khong co close nao <= entry - 720h (coin niem yet < 30 ngay truoc entry);
  cac lenh nay bi **loai khoi** moi tinh toan mom30d (ghi ro n_NaN).
- Cao = "vua pump manh 30 ngay truoc entry".

**Feature phu (de kiem lai ket luan cu, ghi ro la PHU, KHONG dung cho tieu chi quyet dinh):**

- `vol30d` (%) = std cua **simple return 1h** (close[i]/close[i-1]-1) tren cac close trong cua so
  `[entry-720h, entry]`, nhan 100. NaN neu < 2 close trong cua so.
- `drawdown30d` (%) = `(close_entry / max(close trong [entry-720h, entry]) - 1) * 100`
  (am = dang duoi dinh 30 ngay).
- `symbolPred` luc vao (lay truc tiep cot `symbolPred`).
- `tuoi niem yet` (ngay) = `(entry_ts_ms - first_ts[symId]) / 86400 / 1000`,
  `first_ts` = ts nho nhat cua symId trong CLOSES_1H.bin.

## 3. Kiem dinh

### (a) So sanh phan bo mom30d giua SUP vs DOI_CHUNG

- Bao cao **mean** va **median** mom30d cua moi nhom + hieu `d = SUP - DOI_CHUNG` (mean va median).
- **Bootstrap CI block-72h** cho **hieu MEAN** (primary), 2000 rep, seed `20260905`, nhan
  `x1.21` (inflate quanh tam, y het `research/analysis/c3_rates.py::ci_pair`):
  - block = `((ts - t0) / 72h)` (t0 = min ts), resample blocks co hoan lai (so block = so block
    unique chua lenh co mom30d hop le), dung CHUNG luoi block cho ca 2 nhom; moi rep lay cac lenh
    roi vao block duoc rut, split SUP vs DOI_CHUNG trong resample, tinh hieu mean mom30d.
  - CI = percentile 2.5/97.5; sau do inflate: `lo = c - (c-lo)*1.21`, `hi = c + (hi-c)*1.21`
    (c = tam). Bao cao ca CI truoc va sau inflate.
- **Tieu chi (a)**: CI (sau inflate) cua hieu mean mom30d **KHONG chua 0**.

### (b) Bucket theo mom30d (decile)

- Chia cac lenh co mom30d hop le thanh **10 decile** theo mom30d tang dan (qcut, rank method
  "first", neu trung value thi khong ep but coi nhu bucket theo rank).
- Moi decile bao cao: `n`, `n_SUP`, `ti_le_SUP (%)`, `PnL trung binh (USDT)`, `profit trung binh (%)`,
  `tong PnL (USDT)`.
- **Tieu chi (b) — don dieu**: ti le SUP **tang don dieu** theo bucket momentum, dinh nghia =
  Spearman rho(bucket_order 1..10, ti_le_SUP) **>= +0.7** VA `ti_le_SUP(D10) > ti_le_SUP(D1)`.

### (c) Theo nam 2021-2025

Moi nam bao cao: `n`, `n_SUP`, `ti_le_SUP`, `mean mom30d (SUP)`, `mean mom30d (DOI_CHUNG)`.
Mo ta, khong co tieu chi quyet dinh.

## 4. Danh doi (bat buoc) — what-if, KHONG re-run

Voi moi nguong trong `{p75, p90, p95}` cua phan bo mom30d (tinh tren lenh mom30d hop le),
dinh nghia `removed = { lenh co mom30d > nguong }`, bao cao bang:

| cot | y nghia |
|---|---|
| `n_removed` | so lenh bi loc |
| `n_SUP_removed` / `USD_lo_tranh` | so lenh SUP bi loc; `USD_lo_tranh = -sum(pnl cua SUP removed)` (>0) |
| `n_win_removed` / `USD_lai_mat` | so lenh LAI (pnl > 0) bi loc; `USD_lai_mat = sum(pnl cua win removed)` (>0) |
| `n_otherloss_removed` | so lenh lo nhe (profit<0 va >-20) bi loc (tham khao) |
| `PnL_rong_thay_doi` | `= -sum(pnl cua TAT CA removed)` = lo tranh - lai mat |

- Chi tinh tren PnL **DA XAY RA** (what-if), **KHONG re-run sim** (ghi ro trong ket qua).
- **Khong duoc chon "nguong tot nhat"** — bao cao toan bo 3 dong, khong khuyen nghi nguong.

## 5. Gioi han phai ghi (trong result)

- Lenh la **conditional** (chi gom lenh da duoc he THUC SU vao lenh); khong suy ra gi ve coin bi loai.
- What-if **khong tinh duoc** tac dong danh muc / co hoi bi mat / giai phong margin / tuong quan vi the.
- n_SUP = 49 (nho); decile voi ~5 SUP/decile la nhieu.
- **Khong co CI** cho bang danh doi (what-if).

## 6. Tieu chi ket luan (chot truoc)

- Tin hieu duoc coi la **DANG THEO** neu **CA (a) VA (b)** dat:
  - (a) CI (sau inflate) cua hieu mean mom30d (SUP - DOI_CHUNG) **khong chua 0**;
  - (b) ti le SUP **don dieu tang** theo bucket momentum (Spearman >= 0.7 VA D10 > D1).
- Neu khong dat => ghi **NULL** va **DUNG**.
- Neu dat => **KHONG tu dong de xuat ap dung** — chi de xuat **buoc pre-reg test trong sim**
  (muc dich: xac nhan signal co cai thien PnL tren holdout), va **noi ro nguong se duoc chon post-hoc**
  cho buoc do.

## 7. Thuc thi

- Script moi `research/analysis/postpump_measure.py` (Python, dung `logging`, KHONG `print`),
  chay background/setsid + poll. Ghi JSON + CSV vao `research/analysis/out/`.
- Ket qua ghi `docs/RESULT_POSTPUMP_MEASURE.md` (bang a/b/c/d + ket luan + gioi han).
- Commit pre-reg + script + result. **KHONG push.**
