# T1_LABEL3 — doi NHAN selector: 4h "maxfav6" LAM XAU DI, 72h khong phan biet duoc

Tuan `docs/prereg/PREREG_T1.md` @ **26a45ee** (commit TRUOC khi train). CHI DEV 2022-01..2024-06.
Script: `research/analysis/t1_label3.py` (train + rank-IC + bootstrap),
`research/pipeline/build_map.py` (bins), `research/analysis/w1_rates.py` +
`research/analysis/t1_rates_ci.py` (rate + CI). Log: `/home/ubuntu/cov/T1_*.out`.
Train CPU (GPU cam). Sim Oracle CPU. **Khong VAL, khong push, khong ghi de artifact nao.**

## 0. 🔴 RUI RO / BAY MOI PHAT HIEN — doc truoc so

**Bay #13 (moi) — bins KHONG di qua duong Kaggle.** `WFO_FUNDING_PRED_DIR` duoc TIEU THU o
`ExportWfoDataset` (sinh `funding.bin`), **khong** o luc sim. Kernel Kaggle chi chay sim tren
dataset **DA BUILD** (`OFFLINE BIN: doc market/pred/funding tu WfoDataset tai .../sim-c2b-bundle`)
=> doi bins tren Kaggle **khong co tac dung**. Do thuc trong job nay: 3 chan bins moi day len
Kaggle deu ra `equity 60395 / 970 lenh / md5 printDone 910f1aa6…` — **y het parity**.
Ba run do **VO HIEU** va da bi bo; 3 chan duoc chay LAI tren Oracle (noi build dataset).
Muon chay bien the bins tren Kaggle thi phai upload **dataset da build rieng cho tung chan**
(`funding.bin` 1.7GB moi chan), khong phai upload bins.
=> `docs/runbooks/KAGGLE_SIM.md` da duoc bo sung muc canh bao nay.

**Bay #14 — mount Kaggle KHONG phang o cap `/kaggle/input`.** Dataset nam duoi
`/kaggle/input/datasets/<user>/<slug>/`, khong phai `/kaggle/input/<slug>/`.

## 1. CONG REPRO — PASS

| do | tri | nguong |
|---|---|---|
| `spearman(harness L_g1, ledger/pred_s1a2.parquet.score)` | **1.000000** | >= 0.9999 |
| so dong doi chieu | **774,270** | — |
| pool goc | 1,220,490 dong / 8,642 tick | — |
| pool ghep cap (them `maxFav_4h`) | **1,220,490 dong / 8,642 tick — mat 0 dong** | ghep cap sach |

`pred_t1_g1.parquet` ra dung **7,401,294 byte** = kich thuoc `pred_s1a2.parquet`.
Harness trung thuc => moi so duoi noi ve dung cong thuc dang chay.

## 2. BON CHAN

| ma | relevance | ti le nhan duong |
|---|---|---|
| `L_g1` | `rel5` ngu phan vi cua `g1lite - median_tick` (= S1 dang chay) | rel5 can bang 5x~244k |
| `L_f4` | **`1{maxFav_4h >= 0.06}`** ("maxfav6" 4h, cau hoi cua user) | **14.14%** |
| `L_f4q` | `rel5` cua `maxFav_4h` (= `L4_maxfav` cua `LABELH`) | rel5 |
| `L_f72` | **`1{maxFav_72h >= 0.06}`** | **65.71%** |

⚠️ `LABELH` dung ban **ngu phan vi**, user hoi ban **nhi phan**. Chay ca hai (§0 pre-reg).

## 3. rank-IC / edge5 OOS (n = 4,595 tick, min 10 dong/tick)

Diem uoc luong (rank-IC = trung binh theo tick cua `spearman(pred, outcome)`):

| tieu chi (thien vi) | `L_g1` | `L_f4` | `L_f4q` | `L_f72` |
|---|---|---|---|---|
| rank-IC vs `g1lite` (**thien vi `L_g1`**) | +0.17230 | +0.16694 | **+0.18002** | +0.17269 |
| rank-IC vs `maxFav_4h` (**thien vi `L_f4`,`L_f4q`**) | +0.25036 | +0.28071 | **+0.30375** | +0.24523 |
| rank-IC vs `maxFav_72h` (**thien vi `L_f72`**) | +0.24578 | +0.24754 | **+0.27319** | +0.24890 |
| edge5 vs `g1lite` (thuoc do goc `s1_rank.py`) | +0.06804 | **+0.07957** | +0.07433 | +0.06554 |

Hieu vs `L_g1`, block-bootstrap **ghep cap** 2000 rep seed 20260905, CI = `d +- 1.96*f*sd`, `f=1.21`:

| tieu chi | chan | d | CI 72h | loai tru 0 (72h/24h/168h) |
|---|---|---|---|---|
| IC vs `g1lite` | `L_f4` | -0.00536 | [-0.02644,+0.01571] | khong / khong / khong |
| IC vs `g1lite` | `L_f4q` | +0.00772 | [-0.01214,+0.02758] | khong / khong / khong |
| IC vs `g1lite` | `L_f72` | +0.00039 | [-0.01653,+0.01731] | khong / khong / khong |
| IC vs `maxFav_4h` | `L_f4` | **+0.03035** | [+0.01794,+0.04275] | **CO / CO / CO** |
| IC vs `maxFav_4h` | `L_f4q` | **+0.05339** | [+0.04108,+0.06570] | **CO / CO / CO** |
| IC vs `maxFav_4h` | `L_f72` | -0.00514 | [-0.02179,+0.01151] | khong / khong / khong |
| IC vs `maxFav_72h` | `L_f4` | +0.00176 | [-0.01963,+0.02314] | khong / khong / khong |
| IC vs `maxFav_72h` | `L_f4q` | **+0.02741** | [+0.00706,+0.04776] | **CO / CO / CO** |
| IC vs `maxFav_72h` | `L_f72` | +0.00312 | [-0.01552,+0.02176] | khong / khong / khong |
| edge5 vs `g1lite` | `L_f4` | +0.01153 | [-0.00627,+0.02933] | khong / khong / khong |
| edge5 vs `g1lite` | `L_f4q` | +0.00629 | [-0.01291,+0.02548] | khong / khong / khong |
| edge5 vs `g1lite` | `L_f72` | -0.00250 | [-0.01009,+0.00510] | khong / khong / khong |

Ba dieu phai ghi kem:
1. **Khong chan nao phan biet duoc tren tieu chi trung lap** (`g1lite` / edge5) — CI chua 0 het.
   Cac o "CO" deu la chan **thang tren chinh outcome ma no train**, dung nhu canh bao thien vi
   cua `PREREG_LABELH §3` => **khong duoc dung lam bang chung "nhan tot hon"**.
2. **`L_f72` KHONG thang tren chinh outcome cua no** (`maxFav_72h`: d=+0.00312, CI chua 0).
   Nhan nhi phan o nguong 0.06 co **65.7% duong** — gan nhu khong phan tang.
3. 🔴 **rank-IC selector la proxy YEU cho rate giao dich**: `L_f4` khong phan biet duoc o
   MOI tieu chi rank-IC, nhung o sim thi **khac that** (§5). Cai nay bac lai gia dinh ngam
   cua `LABELH` rang dung o rank-IC la du de ket luan.

## 4. PARITY

| duong | equity | lenh | md5 `printDone.csv` | neo |
|---|---|---|---|---|
| `T1_g1o` Oracle + aerospike | **60390** | **970** (`done:147/970/970`) | `8f7afdfb27b15f5b6d4c886700def93c` | = `C2b` — **byte-identical** (`cmp` PASS) |
| `t1-g1` Kaggle + file | **60395** | **970** | `910f1aa6f76b5e6797d97a31a7ea5f5a` | = neo `KAGGLE_SIM §1` |

Jar `target/binance-java-sdk-1.2.4.jar` md5 `e46f9dfe8621` (build lai, KHAC md5 `99d96825428f`
cua ban 2026-09-03) van cho **byte-identity** voi `C2b`. `binsSha256` parity
`0f8721558fbd87ef…`, `md5_funding` `7b9ba20f7a5b49ec…` — trung `BINS_MANIFEST §2c`.
**PARITY PASS o ca hai duong.**

Bins moi (`build_map.py`, nguon gia tri = G015x26, gate giu nguyen multiset P(win)/tick):

| chan | bins | doi | `binsSha256` | `md5_funding` dataset |
|---|---|---|---|---|
| `L_f4` | `/home/ubuntu/predwf_t1_f4` | 765,102/15,536,189 (**4.9%**) | `06c4ee50cc6f66b9…` | `5051b1af413249a1…` |
| `L_f4q` | `/home/ubuntu/predwf_t1_f4q` | 763,943 (**4.9%**) | `05f73199d114fed6…` | `04f2266865d6b0d4…` |
| `L_f72` | `/home/ubuntu/predwf_t1_f72` | 765,391 (**4.9%**) | `550093a5e4442fcf…` | `baaaf06461723262…` |

Ti le `doi` 4.9% trung y ban `predwf_map_s1a2` => build_map chay dung.

## 5. RATE — TIEU CHI PRIMARY (`w1_rates.py`, 4 run Oracle, cung jar, cung dataset-recipe)

| tag | n | win% | TSloss% | mean(P\|SM) | mean(P\|SL) | meanP | mMargin |
|---|---|---|---|---|---|---|---|
| **`T1_g1o`** (`L_g1` = C2b) | 970 | **85.26** | **15.15** | 7.476 | -18.896 | 3.479 | 971 |
| `T1_f4` (`L_f4`) | 1046 | 82.79 | 17.69 | 7.449 | -18.826 | 2.802 | 914 |
| `T1_f4q` (`L_f4q`) | 979 | 83.55 | 17.06 | 7.486 | -19.796 | 2.832 | 959 |
| `T1_f72` (`L_f72`) | 980 | 84.49 | 16.53 | 7.556 | -18.354 | 3.273 | 952 |

Hieu vs `T1_g1o`, block-bootstrap **72h ghep cap theo KHOI THOI GIAN** (4 chan chon COIN khac
nhau nen khong ghep cap tung lenh duoc), 2000 rep, seed 20260905, CI `d +- 1.96*f*sd`, `f=1.21`:

| chan | rate | d | CI 72h | loai tru 0 (72h/24h/168h) |
|---|---|---|---|---|
| `T1_f4` | `TSloss%` | **+2.5318** | [+0.2685,+4.7951] | **CO / CO / CO** |
| `T1_f4` | `win%` | **-2.4661** | [-4.7874,-0.1449] | **CO / CO** / khong |
| `T1_f4` | `mean(P\|SM)` | -0.0266 | [-0.2310,+0.1778] | khong / khong / khong |
| `T1_f4` | `mean(P\|SL)` | +0.0699 | [-1.8929,+2.0328] | khong / khong / khong |
| `T1_f4q` | `TSloss%` | +1.9036 | [-0.2540,+4.0611] | khong / khong / khong |
| `T1_f4q` | `win%` | -1.7031 | [-3.6959,+0.2898] | khong / khong / khong |
| `T1_f4q` | `mean(P\|SM)` | +0.0099 | [-0.1547,+0.1745] | khong / khong / khong |
| `T1_f4q` | `mean(P\|SL)` | -0.8996 | [-2.4175,+0.6183] | khong / khong / khong |
| `T1_f72` | `TSloss%` | +1.3760 | [-0.5235,+3.2755] | khong / khong / khong |
| `T1_f72` | `win%` | -0.7679 | [-2.6269,+1.0910] | khong / khong / khong |
| `T1_f72` | `mean(P\|SM)` | +0.0804 | [-0.1251,+0.2860] | khong / khong / khong |
| `T1_f72` | `mean(P\|SL)` | +0.5420 | [-1.6872,+2.7711] | khong / khong / khong |

## 6. RANG BUOC CUNG (§7 pre-reg: maxDD <= 15%, UW <= 120 ngay, khong nam am, khong quy < -5%)

| tag | maxDD% | UW (ngay) | nam am | quy thap nhat | ket |
|---|---|---|---|---|---|
| `T1_g1o` | -13.12 | 93 | khong | -3.7 (2022Q4) | **PASS** |
| `T1_f4` | **-16.47** | **161** | khong | -5.0 | **FAIL** (maxDD, UW) |
| `T1_f4q` | **-15.02** | **187** | khong | **-6.0** (2022Q4) | **FAIL** (maxDD, UW, quy) |
| `T1_f72` | **-15.12** | 95 | khong | -4.1 | **FAIL** (maxDD) |

**Ca 3 chan doi nhan deu vi pham rang buoc cung.** Theo §7: LOAI, khong xet tiep.

## 7. PHAN QUYET

- **`L_f4` (= "maxfav6" 4h nhi phan, cau hoi chinh cua user): KHAC C2b va KHAC theo huong XAU HON.**
  Dat dung quy tac §8 o khoi 72h (khoi chinh) va 24h: **2/4 rate PRIMARY ngoai CI, cung huong xau**
  (`TSloss%` +2.53pp, `win%` -2.47pp). O khoi 168h chi con 1/4 (`win%` cham bien tren +0.03),
  tuc **do ben khong tuyet doi** — phai ghi. Ngoai ra **FAIL rang buoc cung** (maxDD -16.47%, UW 161 ngay).
- **`L_f4q` (ngu phan vi 4h, ban cua `LABELH`): KHONG PHAN BIET DUOC tren rate** (0/4 ngoai CI o
  ca 3 do dai khoi) — **nhung LOAI vi FAIL rang buoc cung** (maxDD -15.02%, UW 187 ngay, quy -6.0%).
- **`L_f72` (= "maxfav6" 72h nhi phan): KHONG PHAN BIET DUOC tren rate** (0/4 ngoai CI) —
  **LOAI vi FAIL rang buoc cung** (maxDD -15.12%).

**Mot cau: khong chan nao thay the duoc C2b — `L_f4` do duoc la XAU HON, `L_f4q` va `L_f72`
khong phan biet duoc tren rate nhung ca ba deu vi pham rang buoc cung, nen nhan `maxFav>=0.06`
(ca 4h lan 72h) KHONG phai truc dang theo duoi o tang selector.**

## 8. EQUITY — **KHONG PHAI TIEU CHI** (`E[max nhieu]` CAGR voi N=4 = **4.3pp**)

| tag | equity cuoi | CAGR | d CAGR vs C2b |
|---|---|---|---|
| `T1_g1o` | 60,390 | 24.43% | — |
| `T1_f4` | 54,497 | 19.41% | **-5.02pp** |
| `T1_f4q` | 54,628 | 19.53% | **-4.90pp** |
| `T1_f72` | 58,527 | 22.87% | -1.56pp |

Ca ba deu AM, hai chan 4h vuot nguong nhieu 4.3pp mot chut, `L_f72` **nam trong** nhieu.
Muc nay khong tham gia phan quyet §7 — de day de doc, khong de ket luan.

## 9. SO VOI `LABELH_RESULT` — khop mot nua, va cho khac la cho quan trong

| | `LABELH` (2026-09-04) | T1 (job nay) |
|---|---|---|
| dinh nghia nhan 4h | **ngu phan vi** `maxFav_4h` | ca **nhi phan >= 0.06** VA ngu phan vi |
| tieu chi | rank-IC vs `g1_replay` / `pathq_72h` / ROI that (n=84) | rank-IC vs `g1lite`/`maxFav_4h`/`maxFav_72h` + edge5 **+ RATE tu sim** |
| co chay sim? | **KHONG** (dung o rank-IC) | **CO** — 4 run, bins + java |
| ket luan 4h ngu phan vi | khong phan biet duoc | **khop**: rank-IC khong phan biet duoc (d=+0.00772 vs `g1lite`, CI chua 0) va rate cung khong (0/4) |

**Cho KHAC — va la dong gop chinh cua job nay:** `LABELH` ket thuc o "null, khong phan biet duoc"
va **suy ra** khong can lam tiep. Do la sai o mot diem cu the: `L_f4q` **khong phan biet duoc tren
rate** nhung lai **vi pham rang buoc cung** (maxDD -13.12 -> -15.02, underwater 93 -> **187 ngay**,
quy 2022Q4 -3.7% -> **-6.0%**) va equity 60,390 -> 54,628. Tuc **"null o rank-IC" khong dong nghia
"vo hai"** — hai chan 4h deu doi duong equity du diem uoc luong rank-IC gan nhau.
Dau `d` cua `L_f4q` cung doi (`LABELH`: -0.01104 vs `g1_replay`; T1: +0.00772 vs `g1lite`) — hai
outcome khac nhau, khong mau thuan, nhung **cho thay dau cua rank-IC selector khong on dinh giua
cac outcome cung ho 72h**. Do la mot ly do nua de khong dung rank-IC lam tieu chi cuoi.

`LABELH §4.3` ghi "cau hoi goc (nhan **168h**) van nguyen" — **job nay cung KHONG kiem no**.
T1 chi kiem 4h va 72h. Muon kiem 168h phai sinh nhan tu `CLOSES_1H.bin` voi `NH=168`.

## 10. Job nay KHONG lam

Khong cham VALIDATION/HOLDOUT. Khong rebuild OI. Khong ghi de `predwf_map_s1a2/`,
`ledger/pred_s1a2.parquet`, `featv2/feat_v2.parquet`, `claudedata/predwf_G015x26/`,
`sim-c2b-bundle`. Khong dung GPU. Khong push. Ba dataset Kaggle `bins-t1-*` da tao van con
tren tai khoan nhung **vo dung cho duong Kaggle hien tai** (§0 bay #13) — giu lam bang chung,
khong dung lai.

## 11. Artifact

| thu | duong |
|---|---|
| pred 4 chan | `/home/ubuntu/ledger/pred_t1_{g1,f4,f4q,f72}.parquet` |
| bins 3 chan | `/home/ubuntu/predwf_t1_{f4,f4q,f72}/` (386MB moi) |
| profile 3 chan | `profiles/t1_{f4,f4q,f72}.properties` (copy `c2b_min`, doi 1 dong) |
| run sim | `/home/ubuntu/java/devrun/T1_{g1o,f4,f4q,f72}/` |
| log train | `/home/ubuntu/cov/T1_LABEL3.out`, per-tick IC: `/home/ubuntu/cov/T1_ic_*.csv` |
| log rate CI | `/home/ubuntu/cov/T1_RATES_CI.out` |
| run Kaggle VO HIEU | `/home/ubuntu/kaggle_sim/out/t1-{g1,f4,f4q,f72}/` |

## ERRATA (2026-09-25) — `p_mean` **KHÔNG** phải calibration của chân

`p_mean` gần trùng giữa các chân T1 **không** phải calibration: `build_map.py` **giữ nguyên multiset
`P(win)` trong từng tick** (đúng `PREREG_T1.md` §3.2) nên tổng/mean chỉ khác do **nhiễu thứ tự cộng
float32**. Các chân được so bằng **THỨ HẠNG qua cùng một gate**, không phải so mức.
Chi tiết: `docs/diag/DIAG_BINS_P_OVERWRITE.md` (`927bb44`).
