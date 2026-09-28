# RESULT PASS 1 — DIFF 33 FEATURE: LIVE (feat_dump) vs EXPORT DEV

Pre-reg chot TRUOC: `docs/prereg/PREREG_FEAT_DIFF_PASS1.md` (`f56f8a5`). Tool: `research/analysis/feat_diff_pass1_ext.py`
(mo rong `feat_diff_live_vs_dev.py`, van dung `V3FULL`/`QS`). **Chi DOC** tren Oracle + 242. **Khong** Java/sim/WFO —
chi Python nhe local (pandas + onnxruntime). 2026 **chi chan doan**.

**KET LUAN MOT CAU:** **PASS 1 KHONG ket luan cung** — mau live qua nho (46 dong / 1 cua so 42 phut, 2026-09-28)
va **0 cap khop `(ts,symbol)`** voi export DEV (DEV ket thuc 2026-06-01) ⇒ khong the so cap. Tuy nhien:
**instrument duoc xac nhan DUNG tuyet doi** (`p15_out` == `fold_20(live 33 feat)` chinh xac 4,5e-9; 4 feature thoi
gian khop ham) ⇒ loi (neu co) **khong o buoc dump/ghi**, ma o **gia tri feature**. **Chua tim thay feature nao bi
CUT co cau truc** (khong NaN, khong hang so bat thuong, khong clip trong code). Nghi pham manh nhat (chi de nghi):
`volatilityTermStructure` (live ~1,93 vs DEV ~0,93, > DEV p95) va cap `fundingRate*` (duoi bi nen).

---

## 1. DU LIEU THU THAP (so dong thuc)

| host | file | so dong (sau loc BTCUSDT) | symbol | ts (local +07) |
|---|---|---|---|---|
| shadow Oracle | `feat_dump_20260928_084006.csv.gz` | **10** | BTCUSDT | 2026-09-28 08:40:06 → 09:20:06 |
| 242 | `feat_dump_20260928_084506.csv.gz` | **36** | BTCUSDT | 2026-09-28 08:45:06 → 09:22:06 |
| **gop** | | **46** | BTCUSDT | **08:40:06 → 09:22:06 (~42 phut)** |

- **Co du mau khong? KHONG.** 46 dong < 200 ⇒ theo pre-reg §4.3: **"chua du", khong ket luan cung**.
- **0 cap khop `(ts,symbol)`** voi DEV (DEV export ts 2021-01-01 → **2026-06-01**; live 2026-09-28 ⇒ khong giao).
  ⇒ theo pre-reg §4.2: ket qua la **PASS 1 / chi de nghi**.
- Nhip ghi khac nhau: shadow ~1 dong / 4,4 phut; 242 ~1 dong / 1,03 phut (cung BTCUSDT) ⇒ **cau hoi mo** (khac
  build/call-site? xem §6).

## 2. KIEM INSTRUMENT — **DAT (khong the do loi o buoc dump)**

| kiem | ket qua | y nghia |
|---|---|---|
| `p15_out` vs phan bo live da do (`RESULT_P15_SOURCE.md` §3.1) | raw p50 **0,010041** → ×100 = **1,004 %**; known live p50 0,910 % / max 2,300 % | don vi dump = **phan so** (frac); p50 khop |
| `p15_out` == `fold_20`(live 33 feat) bang onnxruntime | **max abs diff = 4,5e-9 pp**, corr = **1,0000000**, model p50 1,004 % / max 1,152 % | **dump ghi DUNG gia tri model xuat** ⇒ khong phai loi ghi |
| 4 feature thoi gian (`hourOfDay/dayOfWeek/weekOfMonth/monthOfYear`) vs ham xac dinh tu `ts` (calibrate tu DEV) | match = **1,0 / 1,0 / 1,0 / 1,0** | tz +07 + `Calendar.DAY_OF_WEEK` (Sun=1) + `WEEK_OF_MONTH` (Sun-start) **khop DEV** |
| cong thuc feature dan xuat (kiem tren DEV 300k dong) | `volatilityTermStructure == volatility1H/volatility24H` (corr 1,00000); `momentumAcceleration == momentum5M-momentum15M` (corr 1,00000) | **cung cong thuc** DEV ↔ live |
| `grep` clamp/cap trong `ComprehensiveMarketFeatureExtractor.java` | **khong** co `Math.min/max/clamp` tren momentum/volatility | khong co clip co y |

⇒ Bang chung **BAC BO** gia thuyet "loi o buoc dump/pipeline feature thoi gian/cong thuc co ban".

## 3. BANG NGHI PHAM (FALLBACK so PHAN BO — chi de nghi, mau nho)

So live (46 dong, 1 cua so tinh lang) voi **DEV w20** (2025-10→2026-06, n=349.501). `shift_sd=|Δmean|/std_dev`,
`tail_ratio=max_live/p99_dev`.

| # | feature | live (p50 / max) | DEV w20 (p50 / p99) | shift_sd | tail_ratio | doc |
|---|---|---|---|---|---|---|
| 1 | **volatilityTermStructure** | **1,969 / 2,130** | 0,822 / 2,464 | **2,29** | 0,86 | live > DEV p95 (**1,77**), ~ DEV p97 (1,97); chi ~3,0 % dong DEV ≥ live |
| 2 | **fundingRateAvg24H** | 6e-6 / 6e-6 | -1,3e-4 / 8,9e-5 | 1,42 | **0,071** | duoi nen manh (nhung funding von ~const trong 8h) |
| 3 | **fundingRateRaw** | -1,5e-5 (std=0) | -1,3e-4 / 9,0e-5 | 1,06 | 0,17 | **hang so** trong cua so |
| 4 | momentum1H | -0,0054 / -0,0026 | 1,8e-5 / 0,0138 | 1,13 | -0,19 | live am (thi truong vua giam) |
| 5 | volatility24H | 3,47e-4 / 3,52e-4 | 5,84e-4 / 1,52e-3 | 1,04 | 0,23 | live thap + gan nhu phang |

- **NaN-rate: 0,0 %** cho ca 33 feature (46/46 dong huu han) ⇒ **KHONG nghi H_src "thieu du lieu"**.
- **Hang so live**: chi `weekOfMonth/dayOfWeek/monthOfYear` (ban chat nham thoi gian — binh thuong trong 42') +
  `fundingRateRaw` (funding cap nhat 8h — binh thuong).
- 17 feature co `tail_ratio<0.5`, nhung **deu la artifact cua cua so tinh lang 42'** (momentum ~0, vol thap), khong
  phai bang chung bi kep.

### 3b. EXPLORATORY (khong pre-reg) — so voi DEV o **cung dai p15**

Vi `p15_out == fold_20(feat)`, so live voi **DEV rows cho cung p15 ≈ 1,00 %** (n_band=179.512):

| feature | live_mean | dev_band_mean | shift_sd_band |
|---|---|---|---|
| **volatilityTermStructure** | **1,929** | 0,962 | **2,18** |
| basketMomentum1H | -0,0097 | 0,0003 | 1,52 |
| weekOfMonth (artifact lich) | 5 | 3,04 | 1,47 |
| fundingRateAvg24H | 5e-6 | -1,2e-4 | 1,44 |
| momentum1H | -0,0057 | 0,0002 | 1,17 |

⇒ Ngay ca khi model xuat cung muc p15 (~1 %), vector live **lech khoi da tap DEV** ro nhat o
`volatilityTermStructure` (off-manifold 2,2 SD). Day la dau hieu **manh nhat, nhung chua du de ket luan**.

## 4. CO KHOP GIA THUYET "p15 CUT DUOI" KHONG?

**CHUA khang dinh.** Ly do dinh luong:

- DEV w20 (n=349.501): p50 0,891 % / p99 1,439 % / max **119,5 %**; so dong **≥ 2,947 % = 239 (0,0684 %)**.
- Live 46 dong ⇒ **ky vong** so dong ≥2,947 % = 46 × 0,000684 = **0,03** ⇒ **quan sat 0 la BINH THUONG**
  o cadence nay. (Voi 8.986 dong nhu `RESULT_P15_SOURCE` thi ky vong ~6,1 — do moi la bat thuong, va can mau lon.)
- Feature **dan dat duoi** p15 (DEV w20, so voi trung binh): `momentumAcceleration` **+17 SD**, `momentum15M` -16,9,
  `momentum1M` -12,5, `volatility1H` +9,5, `volatility15M` +7,7, `volatility24H` +4,8 ⇒ duoi p15 **do nhom
  momentum/volatility**. Live trong cua so nay co cac feature do **nam trong vung tinh lang** (vi du `volatility1H`
  live 0,00067 < tail_p5 0,00131) ⇒ **chua he co su kien** de kiem.
- **Ket luan theo pre-reg §4.5**: chua feature nao co `tail_ratio<0.5` kem **co che** ⇒ **H_cut chua duoc ung ho**;
  van **khong loai** (ii) model/store goc.

## 5. BUOC TIEP (cu the)

1. **Can them du lieu:** toi thieu **≥ 200 dong**, that te can **≥ 2.000–5.000 dong trai ≥ 1 dot bien dong manh**
   (va ly tuong vai ngay/tuan) tren **ca 2 host**. O nhip hien tai: 242 ~1 dong/phut ⇒ ~33 h cho 2.000 dong;
   shadow cham 4× ⇒ **cung can hieu vi sao shadow ghi cham** truoc khi lay mau dai.
2. **Can cua so DEV phu 2026-09:** export DEV dung `<= 2026-06-01` ⇒ 0 cap khop. Can **store/export 2026-08→09**
   de bat buoc dung **PRIMARY (cap `(ts,symbol)`)** + rank-corr (pre-reg §2.1).
3. **Gia thuyet can kiem tiep (uu tien):**
   - **(H1) `volatility24H` bi thieu lich su tren duong live** (Aerospike/HistoryManager chua du 24h tick) ⇒
     `volatilityTermStructure = vol1H/vol24H` bi **phong dai ~2×** (live 1,93 vs DEV 0,93). Kiem: do do dai
     cua so tick thuc te cho vol1/15/60/1440 o duong live.
   - **(H2) nguon `fundingRate*` (Aerospike) tra ve gia tri "phang"/thieu bien do** (tail_ratio 0,07–0,17).
   - **(H3) duoi p15 bi kep** o nhom `momentum{1M,15M,Acceleration}` + `volatility*` — chi kiem duoc **sau khi**
     capture duoc 1 dot bien dong.
4. **Khong deploy, khong hieu chuan lai** truoc khi nguon khop (theo `RESULT_P15_SOURCE.md` §4.4).

## 6. MUC BO / LY DO (khai RO)

- **Bo:** so cap `(ts,symbol)` + rank-corr — **khong the** vi 0 cap khop (DEV ket thuc 2026-06-01). Ghi ro la
  **han che du lieu**, khong phai lua chon.
- **Bo:** ket luan cung ve feature cut — **mau 46 dong < 200** (pre-reg §4.3).
- **Bo:** so `shift_sd` theo cua so day du — bi **nhieu boi che do thi truong** (cua so tinh lang 42' vs 8 thang):
  chi dung de **xep hang nghi pham**, khong dung ket luan.
- **Them (khong pre-reg):** muc 3b "cung dai p15" (EXPLORATORY) — dua vao de tang do phan giai; **khong** dung
  lam bang chung cung.
- **Bo:** khong chay Java/sim/WFO, khong restart/kill host, khong doc key; khong commit `*.csv.gz`/parquet.
- File tam `/tmp/featdiff` da don sau khi dung.

## 7. BANG CHUNG THO (tai lap, output nho)

```bash
# lay mau (chi doc)
scp -P 2222 -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242:/home/chuyennd/java/v_t_m/feat_dump/feat_dump_20260928_084506.csv.gz /tmp/featdiff/live_242/
cp /home/ubuntu/shadow_c3/app/feat_dump/feat_dump_20260928_084006.csv.gz /tmp/featdiff/live_oracle/
python3 research/analysis/feat_diff_pass1_ext.py --out-json /tmp/featdiff/pass1.json
```
**So nguon JSON:** `docs/result/RESULT_FEAT_DIFF_PASS1.json`.
