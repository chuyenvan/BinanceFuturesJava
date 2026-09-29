# RESULT — VOLTARGET_G2 (vol-target sizing tren nen G2+FLAT3)

Pre-reg: `docs/prereg/PREREG_VOLTARGET_G2.md` (md5 `24369f259e37b81065af2e5020219d0f`, commit `ecae6ef3`, chot TRUOC so) + `PREREG_VOLTARGET_G2_AMEND1.md` (cung commit, TRUOC so).
Sim Kaggle, jar `sim-jar-gdv2` (sha 7368be46..., xac nhan result.json), 0 build, 0 sim Oracle. DEV <= 2025-12-30. Khong dung 242/shadow/2026. Thô: `docs/result/voltarget_g2.json`.
Runner `research/analysis/voltarget_g2_run.py`, cham `research/analysis/voltarget_g2_driver.py` (= trail2_g2_driver, doi arm/parity/k=3 inflate 1.4823).

## 0. Ket luan (rui ro truoc)

1. **B0 parity PASS**: md5 `650c386f0d0dfea334af9d55ca2f21d4`, n 2517, eq 131908 (chay lai qua kernel da va, byte-identical voi `g2flat3-val`).
2. **VT_PORT: KHONG CHAY (BLOCKED)** — xem AMEND1. Loi TASK5 = `TARGET_ANNUAL_VOL=25%` cao hon vol tu nhien cua baseline => vol-target thanh lever-up. Tren B0 (vol tu nhien 13.1%/nam, rolling-20d trung vi 6.6%) target 25% + clamp [0.5,2] => 79% so ngay ket o 2.0 (lever ~2x co dinh). Hang so nay hard-code (`PORTFOLIO_TARGET_ANNUAL_VOL = 0.25f`, khong doc key) => sua can BUILD JAR, task cam build. Chay 25% se lap lai dung loi cu nen KHONG bao nhu 1 arm hop le.
3. **VT_COIN: T1 PASS, Calmar_MTM 1.993 vs B0 1.940 (+0.053), CI khong loai 0 => VERDICT "VT ≈ B0" (khong thang).**
4. VT_COIN **khong tao edge**: cung 2517 lenh, rate chat luong gan nhu y het (win 85.94 vs 85.86, TSloss 13.83 vs 14.30). No la **giam size ~0.72-0.74x**: CAGR x0.742, maxDD x0.722 => Calmar gan nhu khong doi. Mua maxDD -4.9pp bang CAGR -8.86pp (~1.8pp CAGR / 1pp maxDD, dung bang ti le Calmar B0 1.94 — nghia la chi tuong duong cat leverage).

## 1. Bang chinh (3 arm)

| arm | n | equity | CAGR % | maxDD MTM-phut % | UW (ngay) | quy xau nhat ROI % | Calmar_MTM | conc max % | T1 |
|---|---|---|---|---|---|---|---|---|---|
| B0 (G2+FLAT3, OFF) | 2517 | 131 908 | 34.31 | -17.68 | 87 | -0.77 | **1.940** | 4.09 | PASS |
| VT_COIN | 2517 (0%) | 97 047 | 25.45 | -12.77 | 83 | +0.34 | **1.993** | 4.20 | PASS |
| VT_PORT | — | — | — | — | — | — | — | — | BLOCKED (AMEND1) |

T1 chi tiet (nguong §9: maxDD MTM/nam <= 40, UW <= 250, quy xau >= -20, 0 nam am, conc <= 15): ca 2 arm PASS moi tieu chi voi bien rat rong (maxDD nam xau nhat -17.7 / -12.8; 0 nam am).
maxDD MTM-phut theo nam (2021..2025): B0 -11.58 / -17.68 / -4.28 / -10.69 / -15.56 · COIN -9.13 / -12.77 / -3.69 / -7.74 / -10.96 (tot hon moi nam).
ROI nam %: B0 18.53 / 11.11 / 54.14 / 43.35 / 29.51 · COIN 11.38 / 12.17 / 39.11 / 31.50 / 21.32 (COIN thua B0 4/5 nam; hon o 2022 vi tranh coin vol cao bi SL).

## 2. Bootstrap ΔCalmar_MTM (COIN − B0), NREP 2000, seed 20260905, inflate k=3 (1.4823)

| phuong phap | ΔCalmar quan sat | CI95 (inflate) | CI95 raw | chua 0 |
|---|---|---|---|---|
| PRIMARY paired block-72h (K=125 khoi) | +0.053 | [-48.5, +74.7] | [-28.5, +54.7] | CO |
| SENS episode-cluster (K=104) | +0.053 | [-6.37, +15.27] | — | CO |

⇒ luat §9: VT thang ⇔ T1 va Calmar > B0 va CI khong chua 0. COIN dat 2/3 (T1, Calmar diem cao hon) nhung CI chua 0 ⇒ **"VT ≈ B0"**. Ket luan khong phu thuoc k (CI raw da chua 0).
ΔCAGR block72 CI inflate [-158, -33.8] (khong chua 0): **CAGR thap hon co y nghia**, ΔΣPnL trung binh -34.8k USDT. Sacrifice: CAGR -8.86pp (-26%), equity -34.9k (-26%).
Cach doc: CI block-72h cua ti so Calmar rat rong (±50) vi Calmar tren ledger resample khong on dinh (nhu vong TRAIL2); khong the dung no de "chung minh" khong co loi ich — chi noi khong co bang chung loi ich.

## 3. Bang quy (ROI % / maxDD ngay % / UW ngay) — qstat_r4.py

| quy | B0 ROI | B0 DD | B0 UW | COIN ROI | COIN DD | COIN UW |
|---|---|---|---|---|---|---|
| 2021Q3 | 13.91 | -5.27 | 17 | 9.15 | -4.39 | 19 |
| 2021Q4 | 4.06 | -3.05 | 27 | 2.05 | -2.58 | 27 |
| 2022Q1 | 4.43 | -2.16 | 33 | 3.38 | -1.89 | 33 |
| 2022Q2 | **-0.77** | -10.02 | 56 | 0.64 | -6.38 | 39 |
| 2022Q3 | 6.76 | -0.12 | 19 | 6.15 | -0.13 | 19 |
| 2022Q4 | 0.43 | -9.37 | 10 | 1.56 | -6.55 | 2 |
| 2023Q1 | 8.39 | -2.12 | 20 | 6.19 | -1.30 | 18 |
| 2023Q2 | 13.42 | -2.00 | 45 | 9.04 | -1.94 | 61 |
| 2023Q3 | 10.69 | -0.68 | 24 | 9.73 | -0.60 | 24 |
| 2023Q4 | 13.28 | -2.24 | 16 | 9.49 | -2.02 | 16 |
| 2024Q1 | 14.72 | -1.48 | 34 | 9.65 | -1.00 | 34 |
| 2024Q2 | 1.33 | -5.39 | 80 | 2.16 | -3.52 | 58 |
| 2024Q3 | 7.05 | -1.01 | 26 | 5.96 | -1.11 | 26 |
| 2024Q4 | 15.21 | -0.22 | 17 | 10.80 | -0.21 | 17 |
| 2025Q1 | 13.53 | -1.87 | 28 | 8.58 | -1.19 | 28 |
| 2025Q2 | 2.49 | -0.57 | 15 | 1.32 | -0.45 | 15 |
| 2025Q3 | **-0.24** | -1.30 | 40 | 0.34 | -0.66 | 23 |
| 2025Q4 | 11.56 | -1.54 | 52 | 9.90 | -0.83 | 52 |

B0 co 2 quy am (2022Q2, 2025Q3), COIN 0 quy am; maxDD ngay toan cua so: B0 -10.02 (UW 86) vs COIN -6.55 (UW 82). Nguon: `vt_qstat_*.txt`.

## 4. Phan bo ROI (roidist.py, profit % theo lenh, PnL USDT k)

| bucket | B0 n / PnL / %PnL | COIN n / PnL / %PnL |
|---|---|---|
| <0 (lo) | 356 / -65.8 / -67.9% | 354 / -38.1 / -61.3% |
| 0-3% | 45 / 0.6 / 0.6% | 48 / 0.4 / 0.7% |
| 3-5% | 660 / 30.2 / 31.2% | 657 / 18.0 / 29.0% |
| 5-7% | 656 / 39.2 / 40.5% | 665 / 24.1 / 38.8% |
| 7-10% | 456 / 37.3 / 38.5% | 450 / 23.0 / 37.0% |
| 10-15% | 246 / 29.4 / 30.3% | 246 / 17.9 / 28.9% |
| 15-25% | 57 / 9.7 / 10.0% | 55 / 6.1 / 9.8% |
| 25-50% | 14 / 3.6 / 3.7% | 16 / 3.4 / 5.5% |
| 50-100% | 23 / 8.3 / 8.6% | 22 / 4.8 / 7.8% |
| 100%+ | 4 / 4.3 / 4.5% | 4 / 2.4 / 3.8% |
| TOTAL | 2517 / 96.9 / 100% | 2517 / 62.0 / 100% |

Phan bo lenh gan nhu y het (n, quantile win: p50 6.0, p95 14.6 vs 14.5); top-1% lenh chiem 14.6% vs 13.6% PnL. Lo giam manh hon lai (-65.8k → -38.1k, ×0.58) so voi lai (×0.62) — COIN cat lo hoi hieu qua hon cat lai (giam size coin vol cao cung la coin hay dinh SL), nhung chenh nho.

## 5. Rui ro / gioi han

1. **COIN ≈ cat leverage.** Ty le CAGR/maxDD giu nguyen; khong co bang chung day la "vol-target thong minh" hon viec giam `SIM_F_BASE` ~26%. Doan can control arm F_BASE×0.74 (KHONG co trong pre-reg, ngoai pham vi; neu MASTER muon phai pre-reg moi). AGENT_RUNBOOK §4: sizing la nut risk preference cua owner.
2. Calmar +0.053 (+2.7%) nam trong nhieu (2 CI deu chua 0). Khong duoc trinh bay nhu cai thien.
3. n khong doi (2517 = B0, |Δn| 0% << 10%): budget throttle khong cham o F_BASE 0.015, nen VT khong doi tap lenh — cach ly sach.
4. VT_PORT chua duoc test => KHONG ket luan gi ve PORTFOLIO mode tren G2. Bang chung gian tiep duy nhat (chi tren B0, khong phai so arm): target 25% la lever-up (AMEND1 §2). Rolling-20d sigma cua chien luoc "bursty" cuc phan mem (p10≈0, trung vi 6.6% vs toan cua so 13.1%) → ngay ca target thap van bi kep 2.0 nhieu ngay; thiet ke PORTFOLIO co the can xem lai cong thuc sigma (ngoai pham vi luot nay).
5. k=3 inflate giu nguyen theo pre-reg du chi 2 arm (bao thu; k=2 → 1.177 khong doi ket luan).
6. Ha tang: COIN doc `CLOSES_1H.bin` + `symbol_map.csv` o duong dan cung `/home/ubuntu/...` khong co trong bundle Kaggle => dataset phu `chuyendinh/sim-vt-data` (sha256 CLOSES_1H.bin `24fd3e93f90a8f9aecb6866ce30e9bd9c8890d34b327ed048772f0df2b4d94b5`, symbol_map.csv `41ee8f1b96b8a01cd3425242fa7bcccbf015c27f9c8fd348604f20ff1bdedd7b`; copy tu Oracle, cung file TASK5) + kernel va trong bo nho (them symlink truoc khi chay java, khong sua `tools/kaggle_sim.py`). Log kernel COIN: `[VOL_TARGET] loaded 10322386 rows -> 627 symbol arrays` (khop TASK5: 627 coin). B0 chay qua cung kernel byte-identical voi lan chay cu ⇒ ban va khong doi hanh vi khi OFF.
7. So voi TASK5: khong so sanh truc tiep (TASK5 nen T170/F_BASE 0.03; o do COIN cung ≈ Calmar 2.469→2.494, CAGR 29.3→20.3 — cung hinh mau "cat leverage, Calmar phang").

## 6. Viec treo

- VT_PORT: can (a) MASTER cho phep sua Java + build jar (them key `SIZE_VOL_TARGET_ANNUAL_VOL`, mac dinh 0.25 giu byte-identical), (b) chot target THEO QUY TAC truoc so (AMEND1 §3 de xuat), (c) dong goi dataset jar moi + chay lai parity B0 650c386f.
- Control F_BASE×0.74 (tuy chon) de tach "vol-target" khoi "cat size".

## 7. File / job

- Kaggle kernels: `chuyendinh/sim-vt-g2-b0`, `chuyendinh/sim-vt-g2-coin` (COMPLETE, khong con job chay). Output: `~/kaggle_sim/out/vt-g2-b0`, `~/kaggle_sim/out/vt-g2-coin` (md5 printDone: `650c386f0d0dfea334af9d55ca2f21d4` / `137c886a6c5dcc943212dbd4e5028371`).
- Cham: `research/analysis/voltarget_g2_driver.py` (MTM cache `/tmp/voltarget_g2_mtm.json`), do vol baseline `research/analysis/voltarget_g2_natvol.py`.
