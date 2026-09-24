# RESULT_GATE_TOPK_LABEL_SIM — Huong A: gate top-K outcome = **XAU HON** (sim, 18-fold)

Pre-reg: `docs/prereg/PREREG_GATE_TOPK_LABEL.md` (`70e8d8f`). Baseline = **T170**
(`profiles/x1_gs_t170.properties`, dataset `wfo_ds_x1_2021`, 18-fold 2021-07..2025-12, md5
`efb793e2468ca3a7318da0f0ad23d4fc`, n=1089, equity 111,070). Vong nay HOAN TAT phan sim/parity ma
vong offline truoc (`RESULT_GATE_TOPK_LABEL.md`) bi BLOCKED do JVM slot bi chiem. KHONG push.

## 0. Ket luan mot cau

**XAU HON — RO RET, LOAI.** Gate A (train label = ket cuc that top-K S1, `y=(g1lite>0)`) lam gate
**LONG HON ~2x** (n_pass 1442 vs 841) vi p cua no cao hon hieu chuan (mean 0.67 vs 0.45) => 4/5 rate
CHAT LUONG ngoai CI **deu theo huong XAU** + **FAIL rang buoc cung** (nam 2025 am -10.35%, UW 418 ngay,
maxDD -20.81%). Equity **54,077 vs 111,070** (−51%), CAGR 10.15% vs 29.27%. Giu T170.

## 1. PARITY — PASS (2x byte-identical)

| duong | dataset | md5 printDone | ket |
|---|---|---|---|
| T170 tren dataset GOC (Sep 12) | wfo_ds_x1_2021 | `efb793e2468ca3a7318da0f0ad23d4fc` | **PASS** |
| T170 tren dataset REBUILD (Sep 20) | wfo_ds_x1_2021_B | `efb793e2468ca3a7318da0f0ad23d4fc` | **PASS** |

Jar `target/binance-java-sdk-1.2.4.jar` (md5 `20e4fc40f47d`, HEAD `52f6123`) tai lap byte-identical.
Luu y: market.bin rebuild lech 57 byte vs goc (backfill ~14 float o vung da bi HOLDOUT SEAL / ngoai
cua so giao dich) — **vo hai** (ca 2 duong deu ra `efb793e2`). funding.bin determinism (md5 trung).

## 2. Mo rong 16-fold (dinh chinh pre-reg §4, ghi ro)

Pre-reg §4 ghi "10 cut 2022-2024" nhung §5.2 lai doi chieu **T170** = 18-fold. De khop baseline that,
gate A duoc **train lai tren 16 cut** (2022-01..2025-12, = `predwf_G015x26` 16 fold + `CUTS16` cua
`run_x1.sh`); KHONG doi design (45 feat, purge 72h, OOS 3 thang, XGB giu nguyen). **Fold 2021 (2 cut
20210701/20211001) khong the train** (khong co data train truoc 2021-07) => **fallback gate CU**
(copy 2 bin 2021 tu `predwf_map_s1a2_x1_2021`). Da them `--cuts 16` vao `gate_topk_train.py` (mac dinh
van 10 = pre-reg goc).

Offline AUC OOS (top-K, WFO sach) 16-fold — **KHONG tot hon**:
- TONG: **0.5876 vs 0.5908** (gate A thua nhe −0.003).
- Theo nam: 2022 **+0.076**, 2023 **+0.033**, 2024 +0.002, 2025 **−0.015**.
- Khop offline 10-fold truoc do (2022-2023 tot hon, 2024+ kem hon). Nen khong co "cai tien dong nhat".

## 3. Sim — bang chinh (equity/CAGR KHONG phai tieu chi)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **T170** (baseline) | 1089 | 88.25 | 9.73 | 7.642 | −16.992 | 5.244 | 1851 | −11.84 | 92 | 111,070 | 29.27 |
| **GATEA_TOPX16** | 1112 | 84.98 | 13.85 | 6.837 | −23.940 | 2.575 | 1428 | −20.81 | 418 | **54,077** | **10.15** |

`[GATE]` gate A: `scale=1.7 base=0.008 n_cand=3629963 n_pass=1442` vs baseline
`n_cand=17925650 n_pass=841`. Gate A admission **+71%** (1442 vs 841) tren tap candidate nho hon
(top-K/tick) => lenh them nhung CHAT KEM.

## 4. CI khoi-72h (bootstrap 2000 rep seed 20260905, inflate = sqrt(2 ln k), k=1 => 1.0)

Hieu = GATEA_TOPX16 − T170 (toan cua so 2021-07..2025-12, n_A=1112 n_B=1089):

| rate | hieu | CI | ngoai CI |
|---|---|---|---|
| win% | **−3.264** | [−6.171, −0.672] | **YES (XAU)** |
| TSloss% | **+4.115** | [+0.857, +7.393] | **YES (XAU)** |
| mP\|SM | −0.804 | [−1.993, +0.365] | - |
| mP\|SL | **−6.948** | [−11.485, −3.370] | **YES (XAU)** |
| meanP | **−2.669** | [−4.007, −1.352] | **YES (XAU)** |

=> **4/5 rate CHAT LUONG ngoai CI, DEU THEO HUONG XAU.** (He so cu x1.21 khong doi ket luan: ca 4 rate
van ngoai CI.)

## 5. Rang buoc cung (RISK_APPETITE moi: maxDD<=30%, UW<=200, khong nam am, quy>=-15%)

| tag | nam | maxDD% | UW | ret_nam% | quy_min% | ket (nguong MOI) |
|---|---|---|---|---|---|---|
| T170 | 2021..2025 | max −11.84 | max 92 | deu >0 | min −0.92 | **PASS** |
| GATEA | 2022 | −19.49 | **238** | +1.89 | −10.99 | **FAIL (UW>200)** |
| GATEA | 2023 | −1.52 | 82 | +14.30 | +1.20 | PASS |
| GATEA | 2024 | −2.82 | 55 | +31.88 | +1.37 | PASS |
| GATEA | 2025 | −20.81 | **329** | **−10.35** | −11.14 | **FAIL (UW>200 + nam am)** |

=> **FAIL tuyet doi**: nam 2025 **am** (−10.35%) — vi pham "khong nam am" (GIU CUNG) + UW 329 > 200.
Tap trung 1 coin: chua do o day (khong can — da FAIL rang buoc truoc).

## 6. Co che vi sao XAU

Gate A duoc train tren top-K outcome (base rate **0.80**) => `p0` mean **0.67** (vs gate CU net015 mean
**0.45**). Trong `map_s1a2`, thu tu gate bi bo, chi multiset `p` con lai; `symbolPred = 1 − p` => gate A
`symbolPred ≈ 0.33` thap hon gate CU ≈ 0.55 => `dyn_thr` gate A ≈ **0.038** vs gate CU ≈ **0.064**
(LONG hon ~2x). Ket qua: gate A mo qua rong, nhan them lenh ke ca nhung coin top-K co ket cuc that xau.
Day chinh la rui ro "calibration lech" da ghi o `RESULT_GATE_TOPK_LABEL.md` §2.3 — nay DA DO DUOC, va
no la thuc, khong phai lo ly thuyet.

## 7. Artifact + chi phi

| thu | duong |
|---|---|
| bins gate A 16-fold | `/home/ubuntu/gate_topk_x16/` (16 file) + summary.json |
| map gate A 18-fold | `/home/ubuntu/predwf_gatetopk_x16/` (16 gate A + 2 gate CU 2021) |
| profile build | `profiles/x1_gatetopk_2021build.properties` |
| dataset A | `/home/ubuntu/wfo_ds_x1_2021_A` (funding.bin 268MB, top-K) |
| run sim | `/home/ubuntu/java/devrun/GATEA_TOPX16/` |
| rate+CI | `/home/ubuntu/gatea_rates.out` |
| script | `research/pipeline/g5/gate_topk_train.py` (them `--cuts 16`) |

Chi phi: train 16-fold ~2.7 phut CPU; build dataset ~2 phut; sim ~12.6 phut (read 75% / sim 24%);
cham diem bootstrap ~3 phut. Kaggle 0.

## 8. Khong lam

Khong push, khong cham 2026/HOLDOUT, khong sua `g015_net_train.py`, khong bat lai shadow-c3, khong
train 2026. Bins 2021 fallback gate CU (khong train gate A 2021 vi khong co data train).
