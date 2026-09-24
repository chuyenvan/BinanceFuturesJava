# RESULT_GATESCALE — do doc gate dyn scale (0.80 / 1.30 / 1.70) tren 48 thang

Pre-reg: `docs/prereg/PREREG_GATESCALE.md` (commit 1985a81, chot 2026-09-12 TRUOC khi cai code/chay). Code+parity: commit 71a713f (branch `module`).
Baseline canonical: `devrun/X1_C3_FULL_PARITY_R` (equity 111,428, n=2,266, md5 ca file 2478e90d...). Cua so 2022-01..2025-12 (1460 ngay MTM),
dataset `wfo_ds_x1`, bins `predwf_map_s1a2_x1` (KHONG rebuild), TICKER_SOURCE=file. `scale=1.0` = baseline (KHONG chay lai).
**Ky vong ghi truoc: NULL** (khong phan biet duoc; hoac cac diem chat lam giam so lenh -> UW/variance xau).

## 1. Cong nghiem thu (byte-identical)
- jar moi + `profiles/x1_c3_full.properties` (KHONG khai `SIM_GATE_DYN_SCALE`) => `devrun/X1_GS_OFF`.
- `printDone.csv`: 2267 dong (2266 lenh); md5 = `2478e90d4e6147bf4cc64f75967ef47d` = X1_C3_FULL_PARITY_R => **BYTE-IDENTICAL** (`cmp` bo header rc=0).
- `[GATE]` log: `scale=1.0 base=0.008 n_cand=15162720 n_pass=2056` => **0 dong `[GATE]` co scale != 1.0**.
- `tools/check_cfg_gateway.sh`: OK. => cong nghiem thu **PASS**, duoc phep chay 3 bien the.

## 2. Bang 3 bien the
d CAGR = paired block-bootstrap equity ngay MTM (block 21, 2000 rep, seed 20260903, k=3 => nguong = 1.4823*sd_boot). maxDD/UW = quan sat toan cua so.

| tag | scale | n | equity | CAGR% | d CAGR (pp) | CI95 d | sd_boot | nguong 1.48*sd | vuot? (i) |
|---|---|---|---|---|---|---|---|---|---|
| X1_C3_FULL_PARITY_R | 1.00 | 2266 | 111428 | +33.58 | — | — | — | — | baseline |
| X1_GS_L80 | 0.80 | 3462 | 74151 | +20.65 | -12.931 | [-25.24, -0.96] | 6.109 | 9.055 | KHONG (d am RO, CI tren<0) |
| X1_GS_T130 | 1.30 | 1386 | 86322 | +25.32 | -8.259 | [-19.41, +1.72] | 5.389 | 7.989 | KHONG |
| X1_GS_T170 | 1.70 | 940 | 98988 | +29.68 | -3.895 | [-18.06, +8.93] | 7.044 | 10.442 | KHONG (CI om 0) |

Do ben block (L=10/21/42) giu dau am/khong-vuot cho ca 3. 5 rate (x1_rates.py, CI khoi-72h x1.21), hieu so voi baseline toan cua so:
- **L80**: win% -2.97 (ngoaiCI), TSloss% +2.89 (ngoaiCI), meanP -0.92 (ngoaiCI), mMargin -386 => 3 rate chat luong ngoai CI, DEU XAU hon.
- **T130**: win% +0.96, TSloss% -1.69, meanP +0.51, mMargin -135 => 0 rate ngoai CI.
- **T170**: win% +2.87, TSloss% -4.85 (ngoaiCI), meanP +2.07 (ngoaiCI), mMargin -171 => 2 rate ngoai CI, deu TOT hon (loc gay hon).

## 3. Theo nam — rang buoc cung (maxDD<=15%, UW<=120, nam>=0, quy>=-5%) [x1_rates.py, cummax trong nam]
| tag | nam | maxDD% | UW | ret_nam% | quy_min% | PASS |
|---|---|---|---|---|---|---|
| PARITY_R | 2022 | -12.46 | 64 | +17.30 | +0.63 | PASS |
| PARITY_R | 2023 | -2.51 | 45 | +60.43 | +7.80 | PASS |
| PARITY_R | 2024 | -11.36 | 121 | +45.36 | -4.64 | **FAIL** |
| PARITY_R | 2025 | -10.60 | 227 | +16.45 | -2.47 | **FAIL** |
| L80 | 2022 | -18.12 | 77 | +14.09 | -1.74 | **FAIL** |
| L80 | 2023 | -4.70 | 63 | +67.06 | +11.21 | PASS |
| L80 | 2024 | -15.54 | 248 | +30.86 | -8.48 | **FAIL** |
| L80 | 2025 | -28.83 | 302 | -15.29 | -14.19 | **FAIL** |
| T130 | 2022 | -13.14 | 78 | +18.97 | +2.10 | PASS |
| T130 | 2023 | -2.51 | 42 | +44.69 | +2.74 | PASS |
| T130 | 2024 | -9.70 | 141 | +28.95 | -5.63 | **FAIL** |
| T130 | 2025 | -18.34 | 221 | +11.17 | -1.29 | **FAIL** |
| T170 | 2022 | -11.84 | 72 | +19.58 | +2.90 | PASS |
| T170 | 2023 | -2.73 | 63 | +34.96 | -0.37 | PASS |
| T170 | 2024 | -6.60 | 92 | +32.14 | -0.92 | PASS |
| T170 | 2025 | -4.23 | 52 | +32.70 | +1.27 | PASS |

Ghi chu: baseline TU vi pham muc TUYET DOI (2025 UW=227; 2024/2025 quy). Rang buoc (ii) doc TUONG DOI theo baseline (khuon B4):
"qua (ii)" <=> KHONG them vi pham nang hon incumbent. **L80** them nam AM 2025 (-15.29%) + maxDD -28.83 / UW 302 => VI PHAM nang hon.
**T130** them maxDD 2025 -18.34 (vs -10.60; > 15 tuyet doi) => them vi pham. **T170** CA 4 NAM PASS tuyet doi (maxDD max -11.84, UW max 92,
quy min -0.92) => rui ro TOT hon baseline.

## 4. Co che
| tag | scale | entries/ngay | n_pass gate (PST) | mMargin | open_max | open_p90 | collapse-day (tong 4 nam) |
|---|---|---|---|---|---|---|---|
| OFF | 1.00 | 1.55 | 2056 | 1945 | 30 | ~11 | 25 |
| L80 | 0.80 | 2.37 | 4563 (+122%) | 1559 | 37 | ~18 | 54 |
| T130 | 1.30 | 0.95 | 1172 (-43%) | 1810 | 27 | ~6 | 16 |
| T170 | 1.70 | 0.64 | 724 (-65%) | 1774 | 27 | ~3 | 7 |

- So lenh/nam & `n_pass` di DON DIEU dung chieu voi scale (scale thap = LONG = nhieu lenh) => co che dung, do do khong degenerate.
- **% chan tu `[GATE]` n_cand la tren MOI danh gia cong (n_cand ~15M/48 thang), KHONG phai "slot top-8"**: ca 4 ~99.99%,
  nen menh de §4(c) ">99% top-8" **KHONG ap dung** (mau so khac). Tin hieu co che thuc = `n_pass` (gate PASS cho PREDICT_SYMBOL_TRADE) di don dieu.
- L80: book mo lon nhat (open_p90 ~18), collapse-day GAP DOI baseline (54 vs 25). T170: book nho nhat (open_p90 ~3), collapse-day GIAM ~3.5 lan (7 vs 25).
- entries/ngay tren 1460 ngay MTM.

## 5. PHAN QUYET
Chot theo §4: bien the **PASS** <=> (i) `d CAGR > 1.4823*sd_boot` (paired, block 21, toan cua so) VA (ii) qua het rang buoc cung tung nam.

- **X1_GS_L80 (0.80): FAIL.** (i) d CAGR -12.9pp, khong vuot, CI tren = -0.96 < 0 => **d CAGR am RO**. (ii) them nam am 2025 (-15.29%) +
  maxDD/UW/quy xau hon baseline. 3/5 rate chat luong ngoai CI deu xau. => **"gate LONG hon THUA"** (dung ky vong: ve phia flat-gate da biet la xau).
- **X1_GS_T130 (1.30): FAIL.** (i) d CAGR -8.3pp, khong vuot (CI [-19.4, +1.7]). (ii) them vi pham maxDD 2025 (-18.34). => chat 30% KHONG cai thien, xau di ve DD.
- **X1_GS_T170 (1.70): KHONG PASS (khong phan biet duoc).** (i) d CAGR -3.9pp, khong vuot, CI [-18.1, +8.9] **OM 0** => khong phan biet CAGR voi incumbent.
  (ii) qua HET rang buoc cung ca 4 nam (rui ro TOT hon: UW 92 vs 227, maxDD -11.84, moi nam duong). Nhung PASS doi CA (i) VA (ii) => T170 **KHONG PASS**.

**Cach doc (khuon B4 muc 7): 0/3 PASS** => nhanh **(b)**: "khong phan biet duoc / do doc gate incumbent la HOP LY" — **DONG, GIU gate hien tai**
(`SIM_MIN_MOMENTUM_15M=0.008`, `EntryGate` nguyen ban, scale=1.0 giu production). KHONG de xuat forward (nhanh (a) can >=1 PASS). Ket qua **khop ky vong ghi truoc = NULL**.
Khong doc cach khac, khong them hau kiem, khong doi nguong 1.4823, khong doi scale sau khi thay so.

Ghi chu doc them (KHONG phai phan quyet): T170 danh doi ~3.9pp CAGR (KHONG co y nghia thong ke) lay rui ro tot hon ro rang — nhung theo pre-reg,
d CAGR la metric quyet dinh va khong phan biet duoc voi 0 => giu incumbent. Neu sau nay muon theo duoi huong "gate chat de giam DD" thi la job MOI, pre-reg rieng.

## 6. Khong lam
Khong mo lai rolling/5m-grid; khong doi bins/exit/selector/trailing; khong cham 242 / holdout 2026 / shadow_c3 / SHADOW_NO_PUSH;
khong deploy; khong git push; khong tune scale sau khi thay so; khong xoa devrun cua nguoi khac; khong doi 0.80/1.30/1.70.

## 7. Tai lap
- Code+parity: commit 71a713f (branch `module`). Key `SIM_GATE_DYN_SCALE` -> `EntryGate.GATE_DYN_SCALE` (doc 1 lan luc Configs nap; khong khai/<=0 => 1.0f;
  chi nhan vao nhanh dyn `symbolPred!=null`; x*1.0f IEEE-exact => byte-identical).
- Build: `/home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -DskipTests -o package` => `target/binance-java-sdk-1.2.4.jar`. `check_cfg_gateway.sh` OK.
- Run (runx trong research/pipeline/x1/run_x1_sim.sh): `WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1 WFO_SMART_CACHE=1 SIM_END_DATE=20251231`
  `EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=<prof> java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp <jar>`
  `com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss`. Profiles: `profiles/x1_gs_l80|t130|t170.properties` (moi key khac y x1_c3_full).
- Devrun: `X1_GS_OFF` (parity), `X1_GS_L80`, `X1_GS_T130`, `X1_GS_T170`.
- Cham: `python3 research/analysis/x1_rates.py X1_C3_FULL_PARITY_R <tag>`; `python3 research/analysis/ci_gatescale.py X1_GS_L80 X1_GS_T130 X1_GS_T170`
  (=> /home/ubuntu/x1log/ci_gatescale.out).
- md5 printDone: OFF `2478e90d`(=baseline), L80 `0c436d82`, T130 `186a0567`, T170 `495954e1`.
