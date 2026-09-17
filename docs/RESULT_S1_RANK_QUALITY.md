# RESULT — S1 RANKING QUALITY (STANDALONE, CRYPTO DEV)

**Ngay:** 2026-09-17
**Pre-reg:** `docs/PREREG_S1_RANK_QUALITY.md` (commit `da0ea2f`)
**Script:** `research/analysis/s1_rank_quality.py` (+ reuse data-loading cua `trend_rank_ic.py`)
**Trang thai:** DESCRIPTIVE MEASUREMENT — lan DAU do truc tiep chat luong xep hang cua S1.
Chay MOT lan, khong tune. KHONG phai bang chung alpha, KHONG phai buoc tich hop.

---

## 1. Nguon du lieu (da xac minh)

- `/home/ubuntu/java/fsrun/CLOSES_1H.bin` — close 1h per coin (10.322.386 dong, 627 symbol-id,
  2021-01-01 -> 2026-01-01). Map id->ten: `/home/ubuntu/selector_pred_out/symbol_map.csv`.
- S1: `/home/ubuntu/ledger/pred_s1a2x1.parquet` (ts,sym,score; 6.573.909 dong; 620 symbol;
  2021-12-31 -> 2025-12-31, moi ~15 phut). `score = -pred`, `pred = P(win)` (C2B_SPEC:101).
- DEV = 2021-01-01 .. 2025-12-31. 2026 LOAI (seal). Snapshot 1h co dinh, decision `t <=
  2025-12-31 00:00`. Min 10 coin/snapshot.

## 2. QUY UOC DAU (khoa)

`rank_ic = Spearman(-score, fwd_return) = Spearman(pred, ret)`.
**rank_ic > 0 = S1 lam dung viec** (coin S1 cho tot thuc su co forward return cao hon).
Top-K = K coin `-score` cao nhat = K `score` thap nhat (K=8 = `SELECTOR_RANK_TOPK`).

## 3. Bang rank-IC (metric chinh) + CI block-72h

CI = block-72h bootstrap (2000 rep, seed 20260905, inflate x1.21). n = 35.047 snapshot.

| horizon | rankIC mean | CI95 (x1.21) | contains 0 |
|---|---|---|---|
| 1h | **-0.0247** | [-0.0264, -0.0229] | KHONG (am) |
| 4h | **-0.0407** | [-0.0440, -0.0370] | KHONG (am) |
| 24h | **-0.0693** | [-0.0771, -0.0613] | KHONG (am) |

**Ca 3 horizon rank-IC deu AM (nguoc huong "S1 lam dung viec") va CI khong chua 0.**
Do lon rat nho (|IC| <= 0.07) nhung "significance" chi la do mau rat lon (35k snapshot).

## 4. Theo nam (S1 co on dinh khong)

| horizon | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| 1h | -0.0240 | -0.0215 | -0.0265 | -0.0267 |
| 4h | -0.0405 | -0.0347 | -0.0394 | -0.0481 |
| 24h | -0.0691 | -0.0608 | -0.0648 | -0.0828 |

**Am o CA 4 nam, ca 3 horizon.** Khong nam nao duong. **2025 yeu nhat** (am manh nhat),
**2023 bot am nhat** (van am). Dau am ON DINH qua cac nam — day khong phai hieu ung mot nam.

Coverage (n_snap / n_coins / median coins/snapshot): 2022 = 8760/153/134; 2023 = 8760/237/185;
2024 = 8784/371/265; 2025 = 8737/586/461.

## 5. Quintile (chia 5 nhom theo -score)

**QUAN TRONG ve dau:** `-score` CAO = tot (score thap). Q4 = `-score` cao nhat = tot nhat.
Quy uoc bang: Q0 = `-score` THAP nhat = toi nhat, Q4 = `-score` cao nhat = tot nhat.
Forward return trung binh tung nhom (% / horizon):

| horizon | Q0 (worst) | Q1 | Q2 | Q3 | Q4 (best) | spread Q4-Q0 (CI) |
|---|---|---|---|---|---|---|
| 1h | -0.0040 | -0.0015 | -0.0014 | -0.0022 | +0.0030 | +0.0070% [+0.0010%, +0.0129%] |
| 4h | -0.0073 | -0.0051 | -0.0053 | -0.0082 | -0.0023 | +0.0049% [-0.0180%, +0.0265%] |
| 24h | -0.0360 | -0.0293 | -0.0335 | -0.0538 | -0.0319 | +0.0041% [-0.1175%, +0.1213%] |

**KHONG don dieu** o ca 3 horizon: duong return khong tang dan tu Q0 -> Q4. Chi co Q4 (nhom
"tot nhat") nho ra khoi da am o 1h, nhung Q1/Q2/Q3 nhieu loan va o 24h Q3 la nhom am nhat.
Spread Q4-Q0: duong nhung nho, chi o 1h CI nam ngoai 0 (0.7 bps/gio), o 4h/24h CI CHUA 0.

## 6. Metric QUYET DINH — top-8 (K=8) vs universe average

`diff = mean(ret top-8 theo S1) - mean(ret toan universe cung snapshot)`. CI block-72h.

| horizon | top-8 diff | CI95 | contains 0 |
|---|---|---|---|
| 1h | +0.0066% | [-0.0064%, +0.0194%] | CO |
| 4h | +0.0245% | [-0.0255%, +0.0750%] | CO |
| 24h | +0.1004% | [-0.1692%, +0.3698%] | CO |

**"Chon top-8 co loi hon trung binh khong?" => KHONG co bang chung.** Diff duong nho nhung
CI chua 0 o ca 3 horizon (luat chon top-K cua he thong khong tao edge thong ke y nghia).

## 7. Doi chung (tai su dung bang muc 3 cua RESULT_TREND_RANK_IC.md, cung moc n=35047)

| horizon | trend | mom | vol | S1 |
|---|---|---|---|---|
| 1h | -0.0219 | -0.0208 | -0.0320 | -0.0247 |
| 4h | -0.0286 | -0.0308 | -0.0505 | -0.0407 |
| 24h | -0.0367 | -0.0446 | -0.0876 | -0.0693 |

S1 **manh hon trend va mom**, nhung **yeu hon vol** (vol am manh nhat = low-vol de-risking).
S1 cung huong am voi toan bo tap trend/vol — cung mot hieu ung reversal.

## 8. KET LUAN (theo tieu chi pre-reg)

**S1 KHONG co nang luc xep hang coin theo forward return (1h/4h/24h).**

Theo tieu chi da chot (can ca 3): (1) `rank_ic > 0` o >=2/3 horizon => **TRUOT** (ca 3 am);
(2) CI khong chua 0 => CI co nam ngoai 0 nhung **sai huong (am)**; (3) quintile don dieu =>
**TRUOT** (khong don dieu; spread chi 1h ngoai 0 va nho). => **KHONG dat.**

**S1 yeu o dau (cu the):**
- **Huong nguoc**: S1 cang "tu tin" (score thap / pred cao) thi forward return **cang THAP**
  (reversal). IC am o ca 3 horizon, **cang am khi horizon cang dai** (1h -0.025 -> 24h -0.069).
- **Theo nam**: am deu 2022-2025, **2025 am nhat** (-0.083 o 24h). Khong nam nao duong.
- **Luat chon top-8**: khong tao edge (diff CI chua 0 o ca 3 horizon).

**Ghi chu khong bien ho:** dau am + do lon nho + top-8 khong edge => S1 nhu dang dung (ranking
theo `pred`) **khong** la nguon alpha forward-return o cac horizon nay. Day la descriptive
measurement, khong phai lenh tich hop/tune.

## 9. Gioi han

1. **Snapshot 1h KHONG phai moc ra quyet dinh that cua sim** — sim chay ticker 1m va chon
   top-K o tan so khac (15m). Day chi la proxy do ranking bang muc snapshot co dinh de so
   sanh duoc voi bai truoc.
2. **Target lech**: S1 duoc huan luyen (XGBRanker `rank:ndcg`) de xep hang theo `g1lite` =
   outcome **72h** (trailing maxFav_72h / retEnd_72h), KHONG phai forward return 1h/4h/24h
   dang do o day. IC am o horizon ngan khong phan anh "S1 sai mut muc tieu 72h"; no chi
   noi rang ranking cua S1 **khong align** voi forward return ngan han (nguoc lai: reversal).
3. **Coverage theo nam khong deu**: 2022 chi 153 coin (median 134/snapshot) -> 2025 moi 586
   coin. Con so 2022-2023 it coin hon, CI ro hon.
4. **S1 chi co 2022-2025** (parquet bat dau 2021-12-31) — khong co 2021, khong co 2026 (seal).
5. **Do lon IC rat nho** (<= 0.07): "significance" chi do n=35k snapshot; ve kinh te gan nhu
   chac chan khong con gi sau phi/slippage. KHONG duoc doc CI-khong-chua-0 thanh "co edge".
