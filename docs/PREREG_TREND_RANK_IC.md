# PRE-REG — TREND/VOL RANK-IC SCREENING (STANDALONE, CRYPTO)

**Ngay viet (pre-reg truoc khi chay):** 2026-09-17
**Trang thai:** KHOA — chay dung MOT lan, KHONG sua thiet ke sau khi thay ket qua.
**Muc dich:** tra loi cau hoi Stage-1 cua `docs/HOLDOUT_TO_T170_PLAN.md`: tap dac
trung trend/vol (tinh than holdout) co **xep hang duoc coin theo forward return**
khong, tren du lieu CRYPTO (DEV). Day la **descriptive screening**, KHONG phai chung
minh alpha; IC nho van co the vo dung sau phi/exit.

---

## 0. Nguon du lieu per-coin (da xac minh, khong suy dien)

- **File:** `/home/ubuntu/java/fsrun/CLOSES_1H.bin`
  - Dinh dang: binary big-endian, `np.dtype([("ts",">i8"),("sym",">i2"),("c",">f4")])`
    (timestamp ms, symbol-id int16, close float32). Giong cach doc trong
    `research/analysis/graveyard.py`, `dyn_collapse_probe.py`.
  - `ts` = Binance kline **open_time** (UTC). `c` = close gia tai **close_time = ts + 1h**.
  - **Pham vi:** `ts` tu 2021-01-01 00:00 den 2026-01-01 00:00 (UTC).
  - **So symbol:** 627 symbol-id (1..789, lo thung thuong), 10.322.386 dong.
  - **Map symbol-id -> ten:** `/home/ubuntu/selector_pred_out/symbol_map.csv`
    (782 dong, `symId,symbol`).
- **Doi chung S1 (bat buoc):** `/home/ubuntu/ledger/pred_s1a2x1.parquet`
  (cot `ts,sym,score`; score thap = tot; ts moi ~15 phut; pham vi
  2021-12-31 -> 2025-12-31, 620 symbol). La S1 selector "hien tai" phu het DEV.

## 1. Cua so DEV (chot truoc)

- **DEV = 2021-01-01 -> 2025-12-31 (UTC).** Nam 2026 (590 dong, holdout seal) bi LOAI.
- Loai toan bo dong co `open_time >= 2026-01-01 00:00`.
- Snapshot quyet dinh chi lay den `t <= 2025-12-31 00:00` de forward return 24h van
  nam trong 2025 (khong chay vao 2026).

## 2. Tan suat resample + snapshot (chot truoc)

- **KHONG resample.** Dung bar 1h goc (native). SMA 50/100/200 tinh tren bar 1h
  = 2/4/8 ngay (dung tinh than plan doc: "SMA 50/100/200 nhung tinh tren bar 1h").
- Snapshot **co dinh moi 1 gio** (luoi UTC gio chan). Mo hom: cac bar close_time <= t.

## 3. Feature (per coin, tai t, chi dung du lieu <= t)

Quy uoc causal (chot): bar co `open_time = ot` co `close` chi duoc biet tai
`close_time = ot + 1h`. Ta doi: xay chuoi close theo `close_time = ot + H` (H=1h).
Feature tai snapshot `t` chi dung cac close co `close_time <= t`.

- **trend** = `sig = ( I[c>SMA50] + I[c>SMA100] + I[c>SMA200] ) / 3`
  - SMA theo **bar** (positional rolling), `min_periods = do dai cua so` (khong tinh
    thieu) — y het holdout. Warmup 200 bar. Gia tri {0, 1/3, 2/3, 1}.
- **mom** = trailing return 168h = `c[t] / c[t-168bar] - 1` (positional; 168 bar truoc).
- **vol** = std cua 1h return (pct_change) trong 168 bar gan nhat (positional,
  `min_periods=168`). Don vi goc (khong annualize; rank-IC bat bien theo scale).

## 4. Target (forward return, chi dung du lieu > t)

`ret_fwd_h(t) = c(t+h) / c(t) - 1`, h in {**1h, 4h, 24h**} (clock time).
`c(t)` = close co close_time <= t (bar dong dung tai t). `c(t+h)` = close co
close_time <= t+h. Neu thieu close tai t hoac t+h -> loai (coin,t,h) khoi cross-section.

## 5. Mau + do luong

- Tai moi snapshot `t`, cross-section = cac coin co du ca 3 feature (trend/mom/vol)
  khong NaN **va** co forward return hop le.
- **So coin toi thieu moi snapshot de tinh rank-IC = 10.** (chot truoc)
- **Metric chinh:** Spearman rank-IC cross-section tai moi snapshot
  (`spearman(feature, ret_fwd_h)`), roi **trung binh qua cac snapshot**.
- **Metric phu (bao ca neu de):** Pearson IC (he so tuong quan thuong) cung cach tinh.

## 6. CI bootstrap block-72h (theo chuan repo)

- Block = 72 snapshot lien tiep (72h). Resample block co hoan lai (2000 rep,
  seed `20260905`), tinh lai mean rank-IC moi rep, lay percentile 2.5/97.5,
  **inflate x1.21** quanh mean quan sat (y het `c3_rates.py`).

## 7. Doi chung S1 (bat buoc, cung moc + cung target)

- S1 score `pred_s1a2x1` forward-fill den luoi 1h: tai snapshot t lay score moi nhat
  co `ts <= t` (causal). Doi dau score (`-score`) de "cao = tot".
- Tinh rank-IC cua `-score` vs cung forward return, cung snapshot, cung CI block-72h.
- **Ket luan "khong them gia tri" neu trend khong hon duoc S1** (so sanh |mean rank-IC|).

## 8. Tieu chi quyet dinh (chot truoc)

- Voi moi feature (trend/mom/vol) x moi horizon (1h/4h/24h):
  - **Neu CI block-72h cua rank-IC CHUA 0** => KHONG co tin hieu o o do.
- **Neu TAT CA cac o deu chua 0** => **DUNG huong nay, ghi `NULL`, khong tich hop,
  khong ton sim nao.**
- Neu co o nao CI nam NGOAI 0 => bao cao, va chi **de xuat** Stage-2 (pre-reg tich hop
  + sim) — **KHONG tu tien tich hop**.
- Gioi han: day la descriptive screening; ket qua chi la goi y, khong phai bang chung alpha.

## 9. Cai KHONG lam

- KHONG sua `.java`. KHONG chay sim T170. KHONG tune tham so sau khi thay ket qua.
- KHONG dung data 2026 (seal). KHONG push.
- Script chi dung module `logging` (khong `print()`), ghi JSON/CSV.
