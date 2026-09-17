# PRE-REG — S1 RANKING QUALITY (STANDALONE, CRYPTO DEV)

**Ngay viet (pre-reg truoc khi chay):** 2026-09-17
**Trang thai:** KHOA — chay dung MOT lan, KHONG sua thiet ke sau khi thay ket qua.
**Muc dich:** lan DAU tien do TRUC TIEP chat luong xep hang cua S1 (`pred_s1a2x1`) tren
crypto DEV. Cau hoi: **"S1 xep hang coin tot den dau, manh o dau, yeu o dau?"** Tra loi
bang SO (co CI). Day la **descriptive measurement**, KHONG phai chung minh alpha; khong
phai dau hieu nao de tich hop hay tune.

**Tai su dung DUNG phuong phap do cua `docs/PREREG_TREND_RANK_IC.md` (commit `e26e3c3`)
+ `docs/RESULT_TREND_RANK_IC.md` (commit `8591f47`)** de so sanh duoc. Khong tu nghi ra
phuong phap moi.

---

## 0. Nguon du lieu per-coin (da xac minh, khong suy dien)

- `/home/ubuntu/java/fsrun/CLOSES_1H.bin` — binary big-endian `[ts>i8, sym>i2, c>f4]`
  (ts = Binance open_time ms; c = close tai close_time = ts+1h). 10.322.386 dong,
  627 symbol-id, 2021-01-01 -> 2026-01-01 (UTC).
- Map id->ten: `/home/ubuntu/selector_pred_out/symbol_map.csv`.
- **S1 score:** `/home/ubuntu/ledger/pred_s1a2x1.parquet` (cot `ts,sym,score`; float32;
  6.573.909 dong; 620 symbol; ts 2021-12-31 17:30 -> 2025-12-31 16:45 UTC, moi ~15 phut).
- **DEV = 2021-01-01 .. 2025-12-31 (UTC).** Nam 2026 (590 dong seal) LOAI. Snapshot quyet
  dinh chi lay den `t <= 2025-12-31 00:00` de forward return 24h van nam trong 2025.

## 1. QUY UOC DAU (bat buoc, khoa de khong doc sai dau nhu lan truoc)

- S1 score = `-pred`, voi `pred = P(win)` (xem `docs/C2B_SPEC.md:101`: `score = -pred`).
  => **score THAP = tot** (score = -P(win), nen score thap <=> P(win) cao).
- He thong chon top-K bang cach sort `symbol2Pred` TANG dan theo score roi lay K phan tu
  dau = **K coin score THAP nhat** (`Configs.java:358-363`, `SELECTOR_RANK_TOPK=8`).
- **Dinh nghia metric chinh:** `rank_ic = Spearman(-score, fwd_return)`.
  Vi `-score = pred = P(win)`, **rank_ic > 0 = S1 lam dung viec** (coin S1 cho la tot
  thuc su co forward return cao hon). Ghi ro de KHONG doc nham dau am/duong.

## 2. Horizon + sample (chot truoc)

- **Horizon:** h in {**1h, 4h, 24h**} (clock time), `ret_fwd_h(t) = c(t+h)/c(t) - 1`.
- **Sample:** snapshot **1h co dinh** (luoi UTC gio chan), KHONG resample (dung bar 1h goc).
  Tai moi snapshot `t`, cross-section = cac coin co S1 score (forward-fill toi `t`) khong
  NaN **va** co forward return hop le.
- **So coin toi thieu moi snapshot = 10** (chot truoc, giong bai truoc).
- Ghi ro **so moc / so coin / coverage theo nam** trong RESULT.

## 3. Metric (chot truoc)

- **(a) rank_ic trung binh + CI block-72h**: bootstrap block 72 snapshot lien tiep (72h),
  resample co hoan lai (2000 rep, seed `20260905`), percentile 2.5/97.5, **inflate x1.21**
  quanh mean quan sat (y het `c3_rates.py` / bai truoc).
- **(b) theo nam**: tinh rank_ic rieng cho 2022 / 2023 / 2024 / 2025 (+ CI block-72h rieng
  tung nam). Cau hoi: S1 co on dinh theo nam khong.
- **(c) quintile**: moi snapshot, chia coin thanh 5 nhom theo `-score` (Q1 = `-score` thap
  nhat = tot nhat, Q5 = cao nhat = tot nhat). Bao cao forward return trung binh moi nhom
  (trung binh qua snapshot) va **spread Q5 - Q1** (per-snapshot) + CI block-72h. Don dieu
  tang Q1->Q5 = S1 xep hang dung.

## 4. Metric QUYET DINH (quan trong hon IC): top-K vs universe

- Mo phong **luat chon thuc te**: moi snapshot lay **top-K theo S1 (K=8 =
  `SELECTOR_RANK_TOPK`)** = 8 coin `-score` cao nhat (score thap nhat).
- `diff_snap(t) = mean(ret_fwd_h cua top-8) - mean(ret_fwd_h toan universe cung snapshot)`.
- Bao cao `mean(diff)` + **CI block-72h** (cung bootstrap). Day moi la cau hoi "chon top
  co loi hon trung binh khong".

## 5. Doi chung (chot truoc)

- (i) **universe average**: mean forward return toan universe (chinh la baseline cua diff).
- (ii) **trend/mom/vol da do truoc**: tai su dung bang muc 3 cua `docs/RESULT_TREND_RANK_IC.md`
  (cung moc, n=35047): S1 rankIC = -0.0247 (1h) / -0.0407 (4h) / -0.0693 (24h) theo quy
  uoc "cao=tot" (nghia la `Spearman(-score, ret)`), trend/mom/vol cung bang do. KHONG do lai.

## 6. Tieu chi ket luan (chot truoc)

- S1 duoc coi la **co nang luc xep hang** neu **ca 3 dieu**:
  1. `rank_ic > 0` (dau duong, dung huong) o **it nhat 2/3 horizon**, va
  2. **CI block-72h khong chua 0** o cac horizon do, va
  3. **quintile don dieu (hoac gan don dieu)**: Q5 - Q1 > 0 va CI khong chua 0 o it nhat
     2/3 horizon.
- **Neu khong dat** => ghi ro la khong dat, va chi ro S1 **yeu o dau** (theo nam / theo
  horizon / dau hieu reversal). KHONG bien ho thanh "van co tin hieu".

## 7. Cai KHONG lam

- KHONG sua `.java`. KHONG chay sim T170. KHONG tune bat cu tham so nao. KHONG dung data
  2026 (seal). KHONG push.
- Script chi dung module `logging` (KHONG `print()`), ghi JSON/CSV.
