# RESULT_GATE_CALIB — hieu chuan gate quanh T170 (1.30 / 2.10): **NULL** (da chay duoc tren Oracle)

Pre-reg: `docs/PREREG_GATE_CALIB.md` (commit `52f6123`, `module`). Baseline T170
`efb793e2468ca3a7318da0f0ad23d4fc` (n=1089, equity 111,070). Vong nay HOAN TAT phan sim/parity ma
ban dau BLOCKED vi bundle Kaggle chua dataset CU + JVM slot bi chiem. Nay chay TRUC TIEP tren Oracle
(noi data `wfo_ds_x1_2021` nam). KHONG push.

## 0. Ket luan mot cau

**NULL cho CA HAI.** scale 1.30 (long hon) va 2.10 (chat hon) deu **0/5 rate CHAT LUONG ngoai CI**
so T170; T130 con FAIL rang buoc cung (UW 221 > 200), T210 qua rang buoc cung nhung khong phan biet
duoc tren rate. T170 (1.70) van la diem toi uu — do doc hien tai DA dung. **Giu T170.**

## 1. Parity — PASS (Oracle, truc tiep)

| do | md5 printDone | n | equity | ket |
|---|---|---|---|---|
| T170 (x1_gs_t170, dataset goc) | `efb793e2468ca3a7318da0f0ad23d4fc` | 1089 | 111,070 | **PASS** |
| T170 (dataset rebuild Sep-20) | `efb793e2468ca3a7318da0f0ad23d4fc` | 1089 | 111,070 | **PASS** |

Jar `target/binance-java-sdk-1.2.4.jar` (md5 `20e4fc40f47d`, HEAD `52f6123`) tai lap byte-identical.

## 2. Bang chinh (equity/CAGR KHONG phai tieu chi)

| tag | scale | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | maxDD% | UW | equity | CAGR% | n_pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **T170** | 1.70 | 1089 | 88.25 | 9.73 | 7.642 | −16.992 | 5.244 | −11.84 | 92 | **111,070** | **29.27** | 841 |
| T130 | 1.30 | 1580 | 85.57 | 13.48 | 7.256 | −18.718 | 3.755 | −18.34 | 221 | 92,616 | 24.15 | 1334 |
| T210 | 2.10 | 808 | 89.73 | 9.28 | 7.530 | −19.204 | 5.048 | −7.60 | 144 | 85,804 | 22.06 | 664 |

`[GATE]`: T130 `scale=1.3 n_cand=17607060 n_pass=1334`; T170 `scale=1.7 n_pass=841`;
T210 `scale=2.1 n_cand=18044936 n_pass=664`. Scale tang => n_pass giam (1334 > 841 > 664) — dung co che.

## 3. CI khoi-72h (2000 rep seed 20260905, inflate = sqrt(2 ln 2) = 1.177, k=2)

Hieu = variant − T170 (toan cua so):

**T130 (n_A=1580 n_B=1089)** — 0 rate CHAT LUONG ngoai CI:
| rate | hieu | CI | ngoaiCI |
|---|---|---|---|
| win% | −2.676 | [−6.607, +1.117] | - |
| TSloss% | +3.747 | [−0.633, +8.142] | - |
| mP\|SM | −0.385 | [−1.979, +1.215] | - |
| mP\|SL | −1.726 | [−6.893, +2.834] | - |
| meanP | −1.489 | [−3.529, +0.559] | - |

**T210 (n_A=808 n_B=1089)** — 0 rate CHAT LUONG ngoai CI:
| rate | hieu | CI | ngoaiCI |
|---|---|---|---|
| win% | +1.482 | [−0.823, +4.072] | - |
| TSloss% | −0.452 | [−3.141, +1.809] | - |
| mP\|SM | −0.112 | [−1.093, +0.903] | - |
| mP\|SL | −2.212 | [−6.384, +2.598] | - |
| meanP | −0.195 | [−1.630, +1.337] | - |

## 4. Rang buoc cung (RISK_APPETITE moi: maxDD<=30%, UW<=200, khong nam am, quy>=-15%)

| tag | nam xau nhat | ket |
|---|---|---|
| T170 | maxDD −11.84, UW 92, khong nam am | **PASS** |
| T130 | maxDD −18.34, **UW 221**, quy −5.6 | **FAIL (UW>200)** |
| T210 | maxDD −7.60, UW 144, khong nam am, quy −3.0 | **PASS** |

(T130 con FAIL o nguong cu: UW 221 > 120; T210 UW 144 chi FAIL o nguong cu 120, qua nguong moi 200.)

## 5. Phan quyet

- **T130 (1.30): NULL** — 0/5 rate ngoai CI + FAIL rang buoc cung (UW 221). Khop `RESULT_DEV2021_READJUDICATE.md` (T130 da chot NULL truoc do; md5 `68510567e9…` trung khop byte-identical => moi truong khong troi).
- **T210 (2.10): NULL** — 0/5 rate ngoai CI; qua rang buoc cung nhung khong phan biet duoc tren rate.
- **T170 (1.70): GIU** — diem toi uu cua do doc (equity 111,070 cao nhat; 1.30 va 2.10 deu thap hon).

Xac nhan "ky vong ghi truoc: NULL" cua pre-reg. Do doc hien tai 1.70 la dung; khong co margin de noi
loi 1.30 hay chat 2.10.

## 6. Artifact + chi phi

| thu | duong |
|---|---|
| run sim | `/home/ubuntu/java/devrun/CALIB_T130/`, `CALIB_T210/` |
| md5 printDone | T130 `68510567e9…` (= RESULT_DEV2021), T210 `1673fa25a8…` |
| rate+CI | `/home/ubuntu/calib_rates.out`, `calib_t210_rates.out` |
| profile | `profiles/x1_gs_t130.properties` (co san), `profiles/x1_gs_t210.properties` (clone t170, scale 2.10) |

Chi phi: 2 sim ~12.7 phut moi (read 75% / sim 24%), tren dataset CU (KHONG rebuild). Kaggle 0.

## 7. Khong lam

Khong push, khong cham 2026/HOLDOUT, khong tune 1.30/2.10, khong doi scale sau khi thay so.
