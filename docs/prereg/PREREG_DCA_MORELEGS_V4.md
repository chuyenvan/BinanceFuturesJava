# PREREG_DCA_MORELEGS_V4 — "nhieu lenh hon = on dinh hon": 3 nhanh sweep TACH BIEN (A/B/C)

Pre-reg MOI, COMMIT TRUOC khi chay sweep. KHONG 242, KHONG `git push`, holdout 2026 nguyen ven
(`SIM_END_DATE=20251231`).

## 0. Ly do cua user
Sau V3, user dong y co che dung nhung muon day tiep huong **nhieu lenh hon = on dinh hon**, vi:
(a) it lenh de **overfit** tren DEV dai khong co holdout; (b) nhieu lenh **pha loang rui ro mot coin chet**.
=> V4 tach RIENG ba bien co the lam tang so lenh, moi nhanh doi DUNG MOT thu.

## 1. BUOC 0 — CHAN DOAN (da chay TRUOC khi viet muc 2-4; khong rerun sim, chi doc printDone/sim.out cu)

### 1.1 Khung ngay cua doan underwater dai nhat — **TRUNG KHIT O CA 6 CONFIG THAT BAI**
`research/analysis/uw_window.py` (moi, chi doc `c3_rates.equity`):

| tag | co che | UW | dinh truoc DD | bat dau UW | hoi ve dinh |
|---|---|---|---|---|---|
| **RG_A_T170** (PASS) | baseline | **92** | 2024-04-09 | 2024-04-10 | 2024-07-11 |
| **DS_DCA8** (PASS) | T170 + margin-cut + DCA | **88** | 2024-04-09 | 2024-04-10 | 2024-07-07 |
| X1_2XH_V1 | #52 chia margin deu | 223 | 2025-03-03 | **2025-03-04** | 2025-10-13 |
| X1_2XH_V2 | #52 chia margin deu | 222 | 2025-03-03 | **2025-03-04** | 2025-10-12 |
| X1_2XH_V3 | #52 chia margin deu | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |
| DS_GS100 | V3 noi gate + DCA | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |
| DS_GS120 | V3 noi gate + DCA | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |
| DS_GS140 | V3 noi gate + DCA | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |

**KET LUAN: day la mot CORRELATED SYSTEMIC EVENT, KHONG phai statistical artifact cua tung co che.**
Sau config that bai — hai ho co che KHAC HAN nhau (#52 chia deu margin cho coin moi; V3 noi gate + DCA) —
deu vao underwater **dung ngay 2025-03-04** (dinh 2025-03-03) va hoi ve dinh trong khoang
**2025-10-11..13**. Trung den TUNG NGAY, khong the la ngau nhien.
Hai config PASS (T170, DCA8) co doan UW dai nhat o **cua so hoan toan khac** (2024-04-10 -> 2024-07).

### 1.2 Chuyen gi xay ra trong khung do (2025-03-04 .. 2025-10-11)
| tag | n_leg dong trong khung | PnL thuc hien | win% | equity dau -> cuoi |
|---|---|---|---|---|
| RG_A_T170 | 61 | **+1,419** | 81.97 | 94,736 -> 102,303 |
| DS_GS100 | 313 | **-3,399** | 76.68 | 96,658 -> 100,780 |
| DS_GS120 | 198 | **-3,213** | 74.24 | 78,964 -> 81,950 |
| DS_GS140 | 136 | **-1,937** | 73.53 | 75,546 -> 79,858 |
| X1_2XH_V3 | 142 | **-2,653** | 73.94 | 83,569 -> 85,662 |

=> Trong dung cua so do, quan the **hep** (T170) LAI, quan the **rong** (moi bien the "nhieu lenh") LO.
Khop chinh xac voi `ANALYSIS_T170_VS_T100` muc 4b: marginal net **-13,787** khi macro chop.
**Do la ngu canh ma sweep V4 phai vuot qua — ghi o day TRUOC khi chay.**

### 1.3 Chi tiet GS100 (moc tham chieu cho nhanh B va C, vi ca hai lay GS100 lam NEN)
Concurrency (so CUM mo dong thoi, lay mau theo gio) + holding time:
| tag | n_cum | conc_tb | conc_p50 | conc_p95 | conc_max | hold_p50(h) | hold_p90(h) | hold_tb(h) |
|---|---|---|---|---|---|---|---|---|
| **DS_GS100** | 2604 | **2.43** | 0 | 12 | 32 | 10.2 | 168.0 | 36.5 |
| RG_A_T170 | 1069 | 0.81 | 0 | 5 | 27 | 4.8 | 154.6 | 28.8 |

**Quan sat quan trong**: conc_p50 = **0** o CA HAI — danh muc rong hon nua so gio. GS100 chi nang
concurrency trung binh tu 0.81 len 2.43. Tuc "nhieu lenh hon" hien nay **khong** lam day danh muc lien
tuc; no chi lam day HON trong nhung dot co tin hieu. hold_p90 = 168h = dung `LOSER_TIME_STOP_HOURS`.

Rate theo nam (muc LEG):
| tag | nam | n | win% | TSloss% | meanP | mMargin | pnl |
|---|---|---|---|---|---|---|---|
| GS100 | 2021 | 342 | 80.99 | 17.84 | 2.762 | 526 | 2,601 |
| GS100 | 2022 | 495 | 78.99 | 16.57 | 2.369 | 548 | 6,203 |
| GS100 | 2023 | 319 | 88.71 | 12.85 | 6.117 | 967 | 16,099 |
| GS100 | 2024 | 775 | 85.55 | 12.26 | 4.697 | 1,057 | 25,884 |
| GS100 | 2025 | 1084 | 80.54 | 12.27 | 2.900 | 1,525 | 36,082 |
| T170 | 2021 | 149 | 92.62 | 7.38 | 4.368 | 973 | 4,273 |
| T170 | 2022 | 198 | 83.84 | 11.11 | 3.861 | 1,171 | 7,688 |
| T170 | 2023 | 126 | 88.10 | 15.87 | 8.074 | 1,993 | 16,331 |
| T170 | 2024 | 281 | 90.04 | 10.68 | 4.769 | 2,112 | 20,403 |
| T170 | 2025 | 335 | 87.46 | 6.87 | 5.784 | 2,372 | 27,375 |

maxDD / UW / return theo nam:
| tag | nam | maxDD% | UW | ret_nam% | equity cuoi nam |
|---|---|---|---|---|---|
| GS100 | 2021 | -4.33 | 47 | 7.43 | 37,601 |
| GS100 | 2022 | -10.83 | 64 | 16.50 | 43,804 |
| GS100 | 2023 | -1.52 | 57 | 36.85 | 59,944 |
| GS100 | 2024 | -7.91 | 88 | 43.15 | 85,787 |
| GS100 | 2025 | -6.27 | **221** | 42.06 | 121,869 |
| T170 | 2021 | -2.46 | 37 | 12.21 | 39,272 |
| T170 | 2022 | -11.84 | 72 | 19.58 | 46,960 |
| T170 | 2023 | -2.73 | 63 | 34.96 | 63,378 |
| T170 | 2024 | -6.60 | 92 | 32.14 | 83,695 |
| T170 | 2025 | -4.23 | 52 | 32.71 | 111,070 |

## 2. XAC NHAN THAM SO HOA — **KHONG CAN CODE MOI** (verify truoc khi viet muc 3)
- `SIM_GATE_DYN_SCALE` -> `EntryGate.GATE_DYN_SCALE` (nhanh A) — da dung o V3.
- `SELECTOR_RANK_TOPK` -> `Configs.SELECTOR_RANK_TOPK` (nhanh B) — da dung o `docs/result/RESULT_K_DENSITY.md`
  (profiles `x1_gs_t170_k12/k16.properties`, moi file chi doi DUNG 1 dong).
- `SIM_DCA_SIGNAL_LOSS` (nhanh C) + `_GATE` / `_BASE_RATIO` / `_COOLDOWN_MIN` — da co tu V1.
=> V4 **KHONG THEM MOT DONG CODE NAO**. Chay tren build HEAD `060e8a5` (= jar cua V2/V3, 137/137 test PASS).

## 3. BA NHANH SWEEP — TACH RIENG TUNG BIEN, KHONG TRON
Moi config so voi **HAI** moc: **T170 GOC** (scale 1.70, khong margin-cut, khong DCA) **VA** **GS100**
(scale 1.00 + margin-cut 50% + DCA8 — moc "da noi gate").

### Nhanh A — ha tiep gate scale (tiep V3, them diem thap hon 1.00)
Machinery Y HET GS100/120/140: margin-cut 50% + DCA8 (X=-8%, cooldown 60p, K=8). CHI doi scale.
| tag | `SIM_GATE_DYN_SCALE` |
|---|---|
| `DS_GS085` | 0.85 |
| `DS_GS070` | 0.70 |
| `DS_GS055` | 0.55 |

### Nhanh B — tang mat do top-K, tren NEN GS100 (khong phai T170 goc)
Moi config = **GS100 + doi DUNG `SELECTOR_RANK_TOPK`**. K=16 KHONG chay lai (K_DENSITY da do: K16 tren
T170 lam UW=164). Giu scale=1.00 + margin-cut 50% + DCA8.
| tag | `SELECTOR_RANK_TOPK` |
|---|---|
| `DS_K10_GS100` | 10 |
| `DS_K12_GS100` | 12 |

### Nhanh C — DCA nguong sau hon, tren NEN GS100 (khong phai nen T170 hep nhu V2)
Moi config = **GS100 + doi DUNG `SIM_DCA_SIGNAL_LOSS`**. **Cooldown giu 60 phut** (gia tri V1 goc) —
CO TINH tach bien: V2 doi CA nguong LAN cooldown nen khong tach duoc hai anh huong. Giu scale=1.00 +
margin-cut 50% + K=8.
| tag | `SIM_DCA_SIGNAL_LOSS` |
|---|---|
| `DS_DCA20_GS100` | -0.20 |
| `DS_DCA25_GS100` | -0.25 |
| `DS_DCA30_GS100` | -0.30 |

> **Vi sao nhanh C dang thu lai du V2 da NULL**: V2 chay nguong sau tren nen **T170 hep**, noi chi
> **1.9-7.5%** cum tung cham nguong (muc 3 RESULT V2). Quan the **GS100 khac han**: gap 2.4x so cum,
> holding p50 gap doi (10.2h vs 4.8h), conc_tb gap 3x. Fire-rate o nguong sau **co the khac han**.
> Day la ly do co CAN CU, khong phai tune lai bien da bi loai.

**Tong: 8 config.** KHONG co config nao khac. KHONG them bien the sau khi thay so.

## 4. Dataset + cham diem (Y HET moi lan truoc)
- `/home/ubuntu/wfo_ds_x1_2021`, `configs/sim_dev_file_2021.properties`, `SIM_END_DATE=20251231`,
  harness `/home/ubuntu/k_runarm.sh <TAG> <PROFILE>`.
- **CONG PARITY BAT BUOC**: `DS_PARITY_V4` voi `ds_v3_parity.properties` (scale 1.70, 4 key DCA khai bao
  nhung `GATE=false`) phai ra md5 `efb793e2468ca3a7318da0f0ad23d4fc` (n=1089). FAIL => dung.
- `research/analysis/x1_rates.py`: khoi 72h, block-paired, NREP=2000, SEED=20260905, CI x1.21.
  `python3 x1_rates.py <TAG> RG_A_T170` => hieu (T170 - config).
- **Rang buoc cung theo TUNG NAM**: maxDD <= 15%, UW <= 120 ngay, ret nam >= 0, ret quy >= -5%.
- **THANG** = (>= 2 rate CHAT LUONG trong {win%, TSloss%, meanP} ngoai CI theo huong TOT) **VA**
  (rang buoc cung PASS **TAT CA** cac nam). Moi truong hop khac => **NULL**. Cham RIENG tung config,
  KHONG gop nhanh.

## 5. CAU HOI COT LOI cua round nay (chot truoc)
**Co nhanh nao THOAT khoi cua so underwater 2025-03-04 .. 2025-10-11 (UW 221) khong?**
Voi MOI config phai bao cao: UW tong, UW theo tung nam, va **khung ngay cua doan UW dai nhat**
(dung `uw_window.py`) de doi chieu truc tiep voi bang muc 1.1. Neu mot config co UW <= 120 thi phai
neu bat va giai thich no KHAC gi cac config truoc khien no thoat duoc.

## 6. KY VONG GHI TRUOC (de khong bao chua sau)
Tu muc 1.2: trong dung cua so 2025-03-04..10-11, moi quan the RONG deu LO (-1,937 den -3,399) trong khi
T170 hep LAI (+1,419). Nhanh A **noi gate them nua** => quan the rong hon nua => **ky vong UW xau di hoac
giu nguyen 221, kha nang thoat thap**. Nhanh B (tang K) cung lam rong pool ung vien => tuong tu.
Nhanh C (nguong DCA sau hon) KHONG doi quan the entry, chi doi cach giai ngan von du tru => **kha nang
cao khong dong toi UW**, va theo V2 thi nguong sau lam fire-rate giam.
Ghi ky vong nay TRUOC de: (a) neu dung thi khong ai phai "giai thich lai"; (b) neu SAI thi do la phat hien
that su dang chu y. **KHONG phai ly do de bo bot config — chay du ca 8 nhu user yeu cau.**

## 7. CAM KET
- Tham so muc 3 DA KHOA truoc khi chay. KHONG tune sau khi thay ket qua. KHONG them config.
- Cong parity PASS truoc khi chay bat ky config nao.
- KHONG deploy 242, KHONG `git push`, chi commit LOCAL tren branch `module`. Holdout 2026 KHONG mo.
