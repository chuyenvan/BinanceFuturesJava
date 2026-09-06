# G4 — RECIPE net015 tai dung + C4 (thang GIA TRI o tang gate)

Ngay 2026-09-06. Pre-reg: `docs/PREREG_C4.md` (commit `4da1486`, viet TRUOC moi run).
Doc kem: `docs/G015_RECIPE.md` (recipe mot trang), `docs/G3_X26_RECOVERY.md` (boi canh).

## 0. RUI RO / DIEU PHAI DOC TRUOC

1. 🔴 **`Funding_Classifier_Final.onnx` dang chay tren duong LIVE KHONG PHAI `net015`.**
   Cham cung 2,134,469 dong OOS 2024Q1: spearman vs `net015` = **0.854** (pearson 0.763,
   mean|d| 0.245) nhung vs `G015_v2` (nhan `maxFav_4h >= 0.06`) = **0.961** (pearson 0.947,
   mean|d| 0.116). Hieu chuan: live `p_mean = 0.2268`, `G015_v2` 0.3411, `net015` **0.4642**.
   => Model live thuoc **ho maxFav**, khong phai ho `net`. Muon shadow chay dung C3 thi
   `symbolPred` live phai la **net015 tai dung**, khong phai file ONNX hien tai. Chi tiet muc 5.
2. 🔴 **`build_map.py` KHUECH DAI sai so 1 ULP thanh 0.37.** Bins tai sinh lech bins goc dung
   `1.192e-07` (1 ULP float32) tren 13.25% dong; sau khi qua `build_map` thi lech **len toi
   0.3715** tren 13.40% dong. Nguyen nhan: pipeline goc dung `sort_values("ts")` (quicksort
   KHONG on dinh) + `rank(method="first")` trong `build_map` pha vo the theo THU TU DONG.
   Day la no ky thuat that, khong phai loi cua model. Muc 4.2.
3. ⚠️ **`C4_maxfav` CHUA CHAY XONG** — `predwf_G015_v2` chi co 10/16 fold; 6 fold con thieu
   dang train tren Kaggle CPU (kernel `chuyendinh/g015v2-maxfav-cpu`). Cau hoi chinh cua C4
   ("thang gia tri co load-bearing o gate khong") **chua co cau tra loi**. Muc 6.
4. ⚠️ **Shadow C3 tren Oracle DA DUNG** (pid 654317 mat, health.log dung o 2026-09-06 15:00Z).
   Job nay KHONG dung no; no da tat truoc khi job bat dau. Can khoi dong lai:
   `cd /home/ubuntu/shadow_c3/app && bin/daemon.sh start`.

## 1. Viec A — bang hyperparam rut tu log + model

Toan bo bang 18 fold + nguon cua tung con so: **`docs/G015_RECIPE.md` muc 2-3**. Tom tat:

| muc | gia tri | rut tu |
|---|---|---|
| nhan | `y = (retEnd_4h > 0.015)`, loc `nBars_4h >= 16` | log + kernel; **kiem doc lap**: `KEEP=48,724,373`, `base=0.1849` — khop tuyet doi |
| WFO | 18 cutoff `20220101..20260401`, `OOS_MONTHS=3`, purge `288 x 15m = 72h`, TZ `+7h` | log |
| feature | 45 = `f0..f39` + 5 OI, `merge_asof(ts, by=symId, backward, tol=2h)` | code |
| XGB | `n_estimators=400, max_depth=5, lr=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=20, spw=(1−pos)/pos, eval_metric=auc, n_jobs=-1, tree_method=hist, seed=42` | model JSON + pipeline |
| device | `cuda` (Kaggle GPU) · xgboost **3.2.0** | log + model JSON |

`scale_pos_weight` doc tu **18/18** model JSON suy nguoc ra `pos` **khop 4 chu so** voi `pos`
trong log — hai nguon doc lap. `max_depth = 5` do tu **cau truc cay** (max 63 node/cay = `2^6−1`),
khong tu tai lieu. Trainer tai dung: **`research/pipeline/g015_net_train.py`**
(`--device cpu|cuda`, `--fold <cutoff|list|all>`, `--save-model`, `--label-mode net|maxfav`).

## 2. Viec A — cong xac minh (train LAI fold 8 tren Kaggle GPU)

Cutoff `20240101`, seed 42, cung dataset input. Khoa `(ts,symId)` trung **100.0000%**
(2,140,992 dong).

**Dai luong TAT DINH khop tung con so voi lan chay goc 2026-08-14:**
`n_train = 14,834,006` · `ts_max = 2023-12-28 16:45:00` · `pos = 0.1864` ·
`scale_pos_weight = 4.365823` · `n_oos = 2,140,992 rec = 55,665,792 B`.

| cap | spearman gop | max\|d\| | per-tick tb | **top-8/tick** |
|---|---:|---:|---:|---:|
| **CONG: GPU s42 tai dung vs GOC x26 (GPU)** | **0.985997** | 2.304e-01 | 0.967703 | **0.8296** |
| GPU s43 tai dung vs GOC x26 | 0.984765 | 2.237e-01 | 0.964221 | 0.8271 |
| **NEN NHIEU: GPU s42 vs GPU s43** (cung may, cung code, chi doi seed) | **0.984931** | 2.300e-01 | 0.963999 | **0.8246** |
| tham khao: Oracle CPU s42 vs GOC x26 | 0.986678 | 1.908e-01 | 0.962649 | 0.8246 |
| tham khao: CPU s42 vs GPU s42 (deu tai dung) | 0.984283 | 2.554e-01 | 0.959183 | 0.8115 |

### PHAN QUYET: **PASS**
- `spearman >= 0.98` — **DAT** (0.985997).
- `top-8 >= 0.95` — **KHONG DAT** (0.8296). Nhung **nguong nay khong the dat duoc**: chi doi
  SEED tren cung mot GPU cho **0.8246**. Cong tai dung **cao hon nen nhieu** o **ca hai** do
  (spearman +0.00107, top-8 +0.0050).
- Theo luat `BENCH_DEVICE` muc 7.4 ("hieu ung phai vuot CI multi-seed do trong cung moi truong"),
  ket luan la **PASS**. Nguong `top-8 >= 0.95` mac dung mot loi voi cong `spearman >= 0.999`
  da bi bo o `BENCH_DEVICE` muc 5: no do "co phai dung MOT mo hinh khong" chu khong do
  "moi truong co lech khong" — trong khi mo hinh nay **von ngau nhien** (`subsample=0.8`,
  `colsample_bytree=0.8`). **Khong tune gi sau khi thay so** — nguong da ghi trong
  `PREREG_C4` muc 6 truoc khi chay.
- **CPU vs GPU (tham khao, khong phai cong):** CPU tai dung vs goc = **0.986678 / 0.8246** —
  nam trong cung dai. Tuc lech CPU-vs-GPU o mo hinh 45-feature nay **khong lon hon** lech
  between-seed. Khong duoc dung so nay ghep cap voi cong (BENCH_DEVICE muc 7.3).

## 3. C4_parity — cong hoi quy: **PASS byte-identical**

`c4_build_map.py` (= ban SAO `x1_build_map.py` + env `G015_BINS_DIR`) chay tren bins
`claudedata/predwf_G015x26` -> bins selector **byte-identical 16/16** voi
`predwf_map_s1a2_x1` dang deploy. Dataset WFO ra `binsSha256 = b877623126...` (khop `X1_EXTEND` muc 2).

| do | `C4_parity` | `X1_C3` (neo) |
|---|---|---|
| so lenh | **2,058** | 2,058 |
| `b` cuoi | **98,523** | 98,523 |
| md5 `printDone.csv` | **`d39da2940dfd815f60772f70517750bf`** | `d39da2940dfd815f60772f70517750bf` |

=> Moi truong KHONG troi. Moi so duoi day doc duoc.

## 4. C4_regen — bins TAI SINH thay duoc bins goc o tang sim?

### 4.1 Ket qua
md5 `printDone.csv` = `0b70325ebe3b2f34a3c7742a82050d71` — **KHONG byte-identical**.

| do | `C4_parity` | `C4_regen` | hieu | CI khoi-72h x1.21 | ngoai CI |
|---|---:|---:|---:|---|:---:|
| n | 2,058 | 2,058 | 0 | [0, 0] | - |
| win% | 85.33 | 85.33 | 0.0000 | [0, 0] | - |
| TSloss% | 14.87 | 14.87 | 0.0000 | [0, 0] | - |
| mP\|SM | 7.178 | 7.187 | +0.0086 | [−0.0029, +0.0308] | - |
| mP\|SL | −21.848 | −21.848 | 0.0000 | [0, 0] | - |
| meanP | 2.863 | 2.870 | +0.0073 | [−0.0025, +0.0261] | - |
| **mMargin** | 1,918 | 1,921 | **+3.43** | [+2.49, +4.42] | **CO** |

**Theo nam:** 2022 va 2023 **giong het tuyet doi** (0/5 ngoai CI, moi hieu = 0.0000);
2024 **0/5**; 2025 **1/5** (`mMargin` +8.63 [+7.77, +9.61]).

**Admission:** trung khoa `(sym,start)` = **2,056/2,058 = 99.90%**. `symbolPred` p10/50/90
**giong het** `0.1424 / 0.2173 / 0.3223` o ca hai arm; %STRONG **83.8** o ca hai.
**Rang buoc cung:** ca hai arm PASS moi nam (maxDD −13.31/−2.63/−11.12/−12.17; khong nam am;
quy xau nhat −4.75). Equity (khong phai tieu chi): 98,523 vs **98,867** (+0.35%), CAGR 29.58 vs 29.69.

### 4.2 Phan quyet — **KHONG DAT cong da ghi truoc, nhung ly do la mMargin**
`PREREG_C4` muc 4 doi: byte-identical **hoac** (0/5 rate chat luong ngoai CI **va** trung khoa
>= 99%). Do duoc: **1/5** ngoai CI, va do la **`mMargin`** — dung cai kenh ma
`AGENT_RUNBOOK` muc 4 da chi ra la **kenh THANG DO cua sizing compound** (B3: "hieu bang 0 tuyet
doi o moi rate muc lenh, chi `mean(margin)` doi"). Do lon: **+0.18%** tren nen 1,918.
Moi rate CHAT LUONG THAT SU (`win%`, `TSloss%`, `mP|SM`, `mP|SL`) **bang 0 tuyet doi hoac trong CI**.

**Doc dung:** bins tai sinh **thay duoc** bins goc ve mat hanh vi giao dich (99.90% cung lenh,
0 khac biet ve chat luong), **nhung khong the thay o cho nao doi byte-identity**. Toi
**khong sua cong sau khi thay so**; ghi lai la **1/5 — FAIL theo van ban, PASS theo noi dung**,
va de user quyet.

### 4.3 Nguyen nhan goc — `build_map.py` khuech dai sai so, va no la NO KY THUAT
| tang | max\|d\| | % dong lech |
|---|---:|---:|
| bins GIA TRI (`predwf_G015x26` vs `g3x26/regen`) | **1.1921e-07** (= 1 ULP float32) | 13.25% |
| bins SELECTOR sau `build_map` (`c4_parity` vs `c4_regen`) | **3.7154e-01** | 13.40% |

Tap khoa `(ts,symId)` trung **100%** o ca hai tang; chi THU TU DONG trong cung mot `ts` khac.
`build_map.py` dung `groupby("ts").rank(method="first")` — pha the theo **thu tu dong** — nen
mot hoan vi trong tick di thang vao gia tri `symbolPred` cua tung coin. Cong voi
`sort_values("ts")` (quicksort **khong on dinh**) cua pipeline goc, ket qua la:
**khong ai tai lap byte duoc bins selector, ke ca khi tai lap bins gia tri toi 1 ULP.**
Sua goc = them `kind="stable"` + sort phu theo `symId` o CA hai cho — nhung lam vay se **doi
bins deploy hien tai** => phai co pre-reg rieng. **Khong dong vao trong dot nay.**

## 5. ONNX duong LIVE co phai net015 khong? — **KHONG**

Cham `Funding_Classifier_Final.onnx` (sha256 `dce8b6a692f672c2a2a42c57ca2d9ab9c412de1d1a48724e25930dcd20a52c24`,
`TreeEnsembleClassifier`, 400 cay, 45 feature, `post_transform=LOGISTIC`, OnnxMLTools 1.16.0)
tren **2,134,469 dong OOS 2024Q1 that**, roi ghep khoa `(ts,symId)`:

| doi chieu | spearman | pearson | max\|d\| | mean\|d\| | p_mean cua bins |
|---|---:|---:|---:|---:|---:|
| ONNX live vs **`x26` net015** (`retEnd_4h > 0.015`) | **0.854131** | 0.763248 | 0.7555 | 0.2445 | 0.46424 |
| ONNX live vs **`G015_v2`** (`maxFav_4h >= 0.06`) | **0.961382** | 0.947293 | 0.8074 | 0.1161 | 0.34105 |

ONNX live: `mean = 0.22675`, `std = 0.17357`, `p10/50/90 = 0.0525 / 0.1762 / 0.4819`.
Quet them ca 18 model `net015` tren mau 300k: spearman cao nhat = **0.9008** (fold 17), va no
**tang don dieu theo fold** — dau hieu cua mot model train tren lich su dai hon, **nhan khac**.

**Ket luan:** model gia tri tren duong live thuoc **ho `maxFav`**, KHONG phai `net015`.
Chenh hieu chuan 0.2268 vs 0.4642 la **hai lan** — day chinh la cai `AGENT_RUNBOOK` muc 0.8(a)
canh bao ("chay shadow bang selector live roi dan nhan C3 = so lieu VO GIA TRI").

### He qua cho shadow
- `L1_SHADOW_C3` muc 4 da chung minh **GIA TRI cua `symbolPred` khong load-bearing o tang
  TRAILING** (thay bang hang so o ca hai cuc -> 0/5 rate ngoai CI). Nen ONNX live sai ho
  **khong lam hong** phan trailing.
- 🔴 Nhung tang **GATE** (`dyn_thr` tang don dieu theo `score`) thi **chua do** — do dung la
  cau hoi cua `C4_maxfav`, va no **chua chay xong**. **Chua duoc ket luan** shadow dung ONNX
  live la an toan cho phan admission.
- Duong di dung neu muon shadow = C3 that: xuat ONNX tu **model `net015` fold cuoi**
  (`/home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx`, sha256 `7921ceaf24...`, cong ONNX-vs-JSON
  `spearman = 1.0`, `max|d| = 4.6e-07` — `G3_X26_RECOVERY` muc 7) va thay file live.
  **Khong lam trong dot nay** — deploy nam ngoai pham vi.

## 6. C4_maxfav — CHUA XONG (bao cao trung thuc)

`predwf_G015_v2` chi co **10/16** fold (`20220101..20240401`, mep `TS_HI = 2024-07-01` hardcode
trong `g72_train.py`). Sau khi do chi phi: duong 45-cot-pandas cua `g72_train.py` **OOM-kill im
lang** tren Oracle o cac fold >= 2025 (`G3_X26_RECOVERY` muc 6.2), va Oracle chi co 1 slot JVM
dung chung voi sim. Da chuyen sang: kernel Kaggle CPU `chuyendinh/g015v2-maxfav-cpu`
(BENCH_DEVICE muc 7.1: **Kaggle CPU == Oracle CPU byte-for-byte**), sinh
**fold 0** (cong doi chieu byte voi `predwf_G015_v2/predict_wf_20220101.bin`,
sha256 `aed0732c09e87a068622a78a51d8dd7a02ceb2c547d422cc430a996ab1cdc485`) + **fold 10..15**.
Trang thai luc viet: **RUNNING**.

**Sai lech so voi pre-reg, khai bao TRUOC khi thay bat ky so nao cua arm nay:** pre-reg muc 1 ghi
"train them bang `g72_train.py` CPU byte-identical". Thuc te dung `g015_net_train.py
--label-mode maxfav --thr 0.06` (cung nhan, cung hyperparam, duong build memory-light) **vi
`g72_train.py` khong chay noi cac fold 2025 tren Oracle**. Cong thay the: fold 0 phai ra
**byte-identical** bins cu. Neu cong do FAIL thi **bo arm nay**, khong bao so.

Khi arm chay xong: `c4_build_map.py` -> `predwf_map_c4_maxfav` -> `run_c4_sim.sh C4_maxfav`
-> `c4_rates.py C4_parity C4_regen C4_maxfav`. Du doan da ghi truoc: `PREREG_C4` muc 5.

### 6.1 SAI LECH PHAM VI — khai bao TRUOC khi thay bat ky so nao cua arm nay

Kernel 48 thang chay lau hon ngan sach cua dot nay. De **van tra loi duoc cau hoi chinh**,
chay them mot arm **CUA SO 30 THANG** (`2022-01-01 .. 2024-06-30`) dung **10 fold DA CO SAN**
cua `predwf_G015_v2` — **khong train them dong nao**:

- `C4_maxfav30` = bins `predwf_G015_v2` (10 fold `20220101..20240401`), `SIM_END_DATE=20240630`.
- Nen so sanh = **`C4_parity` cat toi `end < 2024-06-30`**. Phep cat nay DA duoc xac nhan
  hop le: `X1_EXTEND` muc 3 do rang `X1_C3` cat toi 2024-06-30 ra **dung 961 dong IDENTICAL**
  `C3_BASE`, tuc "chay 48 thang roi cat" == "chay 30 thang".
- **Tieu chi giu nguyen** `PREREG_C4` muc 3-4: >= 2 rate CHAT LUONG cung huong, ngoai CI khoi-72h
  x1.21 => KHAC parity. `n` va `mean(margin)` mot minh khong tinh.
- **Diem yeu phai ghi:** cua so 30 thang co `n_eff` **89 khoi 72h** (so voi 167 cua 48 thang,
  `X1_EXTEND` muc 9) => CI rong hon ~1.37 lan. Mot ket qua NULL o day **khong** manh bang null
  o 48 thang. Neu ra null thi phai ghi la "chua do du power", khong phai "khong co hieu ung".
- Arm 48 thang van chay tiep; khi xong se bao sung, **khong thay the** ket qua 30 thang.

Du doan cho 30 thang (ghi truoc): giong `PREREG_C4` muc 5.2 diem 3-4 — `n` tang >= 15%,
1-2 rate chat luong ngoai CI, `%STRONG` tang len > 95%.

## 7. Artifact + lenh tai lap

| thu | duong dan |
|---|---|
| trainer tai dung | `research/pipeline/g015_net_train.py` (sha256 `05298cba5578...`) |
| recipe | `docs/G015_RECIPE.md` |
| build map tham so hoa | `research/pipeline/x1/c4_build_map.py` (env `G015_BINS_DIR`) |
| runner sim | `research/pipeline/x1/run_c4_sim.sh <TAG> <profile> <bins>` |
| cham diem | `research/analysis/c4_rates.py C4_parity C4_regen [C4_maxfav]` |
| profile | `profiles/c4_{parity,regen,maxfav}.properties` (chi khac `WFO_FUNDING_PRED_DIR`) |
| bins selector | `/home/ubuntu/predwf_map_c4_parity` (= `predwf_map_s1a2_x1` byte-identical), `/home/ubuntu/predwf_map_c4_regen` |
| run sim | `/home/ubuntu/java/devrun/{C4_parity,C4_regen}` · log `/home/ubuntu/c4log/` |
| cong Viec A | `/home/ubuntu/g4/{gpu_f8,gpu_f8_s43,cpu_f8}` · `gate2.py`, `gate_cmp.py` |
| ONNX check | `/home/ubuntu/g4/onnx_full.py`, log `onnx_full.log` |
| kernel Kaggle | `chuyendinh/g015-net015-retrain-f8-gpu`, `...-f8-s43-gpu`, `g015v2-maxfav-cpu` |

⚠️ `UW` trong `c4_rates.py` = **so ngay duoi `cummax`** trong nam, KHONG phai chuoi lien tiep
dai nhat nhu `X1_EXTEND` muc 7 (302). Hai dinh nghia khac nhau — dung so sanh cheo.

## 8. No ky thuat moi

1. 🔴 `build_map.py` + `sort_values("ts")` khong on dinh => **bins selector khong tai lap byte
   duoc**, ke ca khi bins gia tri tai lap toi 1 ULP (muc 4.3). Sua = pre-reg rieng.
2. 🔴 ONNX live khong phai `net015` (muc 5) — anh huong moi ket luan shadow ve **admission**.
3. ⚠️ `g72_train.py` khong mo rong duoc qua 2024-06 tren Oracle (OOM) — dung
   `g015_net_train.py --label-mode maxfav` thay the, va phai giu cong byte fold 0.
4. ⚠️ Shadow C3 Oracle dang TAT.
