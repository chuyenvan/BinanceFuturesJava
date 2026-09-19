# RESULT_GATE_H72 — Huong B (gate 4h -> 72h): **KHONG CHAY** — cau hoi da dong

Pre-reg: `docs/PREREG_GATE_H72.md` (commit cung dot nay, `module`, nen `2e3bef8`).
Baseline: **T170** `devrun/X1_GS_T170_2021` md5 `efb793e2468ca3a7318da0f0ad23d4fc` (1089 lenh).
**Vong nay KHONG train, KHONG sinh bins, KHONG sim. Khong push.**

---

## 0. Ket luan mot cau

**KHONG CHAY vi trung lap: nhan `retEnd_72h > 0.015` da duoc pre-register (`f0b088b`) va da
chay xong ca bins lan sim 48 thang; ket qua la XAU HON RO RET, khong phai NULL.** Va o kien truc
dang chay, Hướng B **khong co kenh tac dong** (muc 3).

## 1. 🟢 Bang chung da co (khong chay lai) — nhan/horizon cua gate

### 1.1 Proxy (offline, phut) — `g5_proxy.py`, `docs/G5_VALUE_LABELS.md` §3.1

| ung vien | base rate | rank-IC vs `g1lite` | hieu so vs `net015_4h` (CI khoi-72h x1.21, 419 khoi) | edge5 | `pass` RAW vs parity |
|---|---:|---:|---:|---:|---:|
| `net015_4h` (= x26 dang deploy) | 0.1849 | **+0.14412** | moc | +0.17205 | 103,840 (x1.00) |
| `net015_72h` (= **Hướng B**) | **0.3932** | **−0.01277** | **−0.15689 [−0.17792, −0.13586]** — ngoai CI | +0.00782 | 83,193 (**x0.80**) |

=> Model 72h **gan nhu khong xep hang duoc gi trong tick** (rank-IC ~ 0), kem `net015_4h`
**ngoai CI va cung huong XAU**. Phan phoi `p` hep hon (sd 0.1175 vs 0.1301) => admission RAW
giam 20% (khong phai tang nhu du doan "base rate cao" — xem `G5_VALUE_LABELS` §3.4).

### 1.2 Sim 48 thang (2022-01-01..2025-12-31, `TICKER_SOURCE=file`) — arm `G5_net015_72h`

Doi chung = `G5_parity_S1` (= `X1_C3`, md5 `d39da294…`, byte-identical, 2058 lenh).
Artifact: `/home/ubuntu/java/devrun/G5_net015_72h/storage/printDone.csv`, md5
`a020ba74b38323250a0e65d3ee0ad689`, 2815 lenh. Nguon so: `/home/ubuntu/g5/rates.out`.

| rate | T170/parity (48m) | `net015_72h` | hieu | CI95 (khoi-72h x1.21) | ngoai CI |
|---|---:|---:|---:|---|---:|
| n | 2058 | 2815 | +757 | [+477, +1060] | CO |
| win% | 85.33 | **76.02** | **−9.30** | [−13.49, −5.48] | **CO (XAU)** |
| TSloss% | 14.87 | **27.00** | **+12.13** | [+8.23, +16.34] | **CO (XAU)** |
| mean(P\|SL) | −21.848 | −11.450 | +10.40 | [+7.25, +13.65] | **CO (TOT hon 1 chieu)** |
| mean(margin) | 1918 | 723 | −1195 | [−1351, −1034] | **CO (XAU)** |
| mean(P\|SM) | 7.178 | 6.816 | −0.36 | [−0.80, +0.10] | khong |
| mean(P) | 2.863 | 1.884 | −0.98 | [−2.18, +0.19] | khong |

=> **4/5 rate CHAT LUONG ngoai CI, huong tong the XAU** (mP|SL tot hon la he qua co khi
`win%` tut: it lenh thang hon thi lenh thua nguoc lai nhe hon). Equity 39,181 vs 98,523
(**CAGR 2.87% vs 29.58%**), maxDD 48t −28.04% vs −13.31%. Equity **khong** phai tieu chi —
nhung khong can no de ket luan.

### 1.3 Rang buoc cung — ke ca theo nguong MOI cua `RISK_APPETITE`

| nam | maxDD% (<=30) | UW (<=200) | ret_nam% (khong am) | quy_min% (>=-15) | PASS |
|---|---:|---:|---:|---:|:---:|
| 2022 | −20.21 | **359** | **−12.01** | −6.39 | **FAIL** |
| 2023 | −6.49 | **284** | +42.41 | +1.24 | PASS |
| 2024 | −15.72 | **343** | +19.72 | −11.15 | **FAIL** |
| 2025 | −27.30 | **357** | **−25.34** | **−16.72** | **FAIL** |

**FAIL 3/4 nam ngay ca khi da noi nguong** (UW 200, maxDD 30, quy −15). T170 PASS ca 4 nam
(`RESULT_GATESCALE` §3: −11.84/72, −2.73/63, −6.60/92, −4.23/52). Tap trung 1 coin: **khong do**
trong `rates.out` — ghi la thieu, khong suy dien.

### 1.4 Cong doc lap o tang offline: G1 — `docs/G1_HORIZON.md` (commit `3b13de6`)

G1 (`PREREG_G1` `f931265`, `PREREG_G1_SIM` `6519c22`) hoi **dung cau hoi horizon o tang gia tri
gate**, ho nhan `maxFav` (khac `net`): `G72` (`maxFav_72h >= 0.07`) vs `G4_repro` (`maxFav_4h >= 0.06`),
n = 15,442,092, 304 khoi, 2000 rep, seed 20260906:

- AUC **0.6259 vs 0.6558**, hieu **−0.0299**, CI95 **[−0.0459, −0.0145]** nam tron duoi 0.
- `P(d>0) = 0.0000`, dau nhat quan ca 3 nam, `gate_pass = False` => **0/2 sim duoc cap phep**.

=> Hai ho nhan (net va maxFav), hai tang (proxy + sim; offline + sim) deu noi cung mot chieu:
**doi gate sang 72h lam gate KEM DI**.

## 2. Doi chieu T170 — gioi han phai khai ro

Arm G5 chay o `x1_c3.properties` (gate scale **1.0**, 48 thang, 2058 lenh parity); T170 la cung
bins do voi scale **1.70** (1089 lenh). Nen con so o §1.2 la **vs `X1_C3`**, khong phai vs T170.
Do la **diem chua do duy nhat** cua vong nay — va no khong lam thay doi ket luan, vi:
deficit nam o `win%`/`TSloss%` (chat luong coin duoc chon), khong phai o do chat cua gate.

## 3. 🔴 Co che: o kien truc dang chay, Hướng B KHONG co kenh tac dong

`c4_build_map.py` (duong tao `predwf_map_s1a2_x1` ma T170 dang tro vao) trong moi tick:
lay `p` cua gate lam **DUNG MOT LAN** theo thu hang cua S1 —
`sub["r_score"] = rank(score S1)`, `sub["p_new"] = p_sorted[theo r_score]`.
Nghia la: **thu tu trong tick do S1 quyet dinh; gate chi con lai MULTISET `p` cua tick.**

=> Doi horizon cua gate **khong** doi duoc "tin hieu gate xep hang coin" (thu tu do da bi bo).
No chi doi **hieu chuan/threshold** cua `symbolPred` (do duoc: `pass` RAW x0.80, tuc gate chat
hon ~20%). Tuc:
- Gia thuyet H_B ("gate va selector cung horizon => tin hieu nhat quan hon") **khong co kenh de
  tac dong** trong kien truc hien tai. Muon do that su thi phai dung THU TU cua gate — do la
  Hướng A/E/F, khong phai B.
- Cai con lai cua B la mot phep **HIEU CHUAN/DO CHAT**, da co khung do rieng (`RESULT_GATESCALE`:
  L80/T130/T170) va da biet hieu chuan la kenh load-bearing (C4, `PREREG_G5` §0).

**Ket luan**: B vua da bi bac bo o tang nhan, vua **sai dac ta** o tang thiet ke. Chay no se tao
mot con so mang ten "horizon" nhung thuc chat do "do chat gate" — de gay hieu nham trong ho so.

## 4. Chan van hanh (khong tu xu ly)

`AGENT_RUNBOOK` bay #4: 1 slot JVM, `pgrep java` phai rong. Luc kiem: `pid 1198675`
`BinanceOrderTradingManager` (start 2026-09-20 00:12). Dung tien trinh song la ngoai pham vi job.

## 5. Cai gi se doi ket luan

1. Owner muon con so **T170** cu the (khong phai `X1_C3`) => can 1 slot JVM rong; khi do phai
   doi ten thanh "H72_CAL" va cham bang tieu chi hieu chuan, khong duoc goi la kiem horizon.
2. Owner muon kiem **that** gia thuyet horizon => phai la mot huong dung THU TU cua gate
   (A/E/F trong `DESIGN_GATE_TARGET_ALIGNMENT` muc 5).
3. Co bien the 72h moi khac han (`retEnd_72h` o nguong khac, ho nhan khac, thiet ke khac
   `g5_pool_train.py`) => pre-reg moi, k=1.

## 6. Khong lam

Khong push, khong cham 2026/`HOLDOUT_UNSEAL`, khong train lai, khong sua
`research/pipeline/g015_net_train.py` (artifact ghim sha), khong dung tien trinh dang chay.
