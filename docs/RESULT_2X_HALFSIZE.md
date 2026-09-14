# RESULT_2X_HALFSIZE — 2x so lenh x 1/2 von/lenh (giu hieu qua ~T170, rui ro thap hon)

Pre-reg: `docs/PREREG_2X_HALFSIZE.md` (commit 44b12e4, chot TRUOC khi chay). Nen: DEV mo rong 18 fold
(2021Q3..2025Q4), dataset `wfo_ds_x1_2021`, baseline `X1_GS_T170_2021` (gate1.70/K8/F_BASE0.03, md5 efb793e2, n=1089).
Jar HEAD 46095eb (KHONG doi code Java, KHONG rebuild logic; knob SIM_F_BASE da co san Configs:545).
SIM_END_DATE=20251231, holdout 2026 NGUYEN VEN. KHONG cham 242, KHONG tune, KHONG push.

## 0. Phan quyet (so truoc) — KHONG CONFIG NAO THANG
- **Reproduction PASS**: re-run baseline (jar 46095eb) => printDone md5 **efb793e2** byte-identical (n=1089, b:111070,
  PROFILE_HASH 0d0fa22158b1d8c0). Xac nhan ban va ShadowBookC3 (sau 422b23e) KHONG doi duong sim.
- **Knob-parity PASS**: profile baseline + `SIM_F_BASE=0.03` (mac dinh, keys=21, hash 5deea0b16d288eef) =>
  md5 **efb793e2** byte-identical. Knob SIM_F_BASE o gia tri mac dinh VO HAI.
- **2x lenh: DAT.** n boi so 1.93x (V1) / 2.36x (V2) / 1.95x (V3).
- **1/2 von/lenh: DAT.** size%/leg (margin/equity) ratio vs baseline = 0.55 / 0.51 / 0.51.
- **RUI RO: KHONG dat.** maxDD DEPTH giam (moi V < baseline -11.84%) NHUNG underwater UW **NO GAP ~2.4x**
  (baseline 92 ngay -> 223/222/221) => vi pham rang buoc cung UW<=120 o CA BA V (nam 2025). Da dang hoa lam
  drawdown NONG hon nhung KEO DAI hon nhieu.
- **HIEU QUA: KHONG dat.** CAGR 29.27% -> 21.38 (V1, -7.9pp) / 23.99 (V2, -5.3pp) / 23.60 (V3, -5.7pp) — deu ngoai +-2pp.
- **Chat luong**: V1/V2 0 rate ngoai CI (diem uoc luong deu xau nhung trong CI rong x1.21). V3 2 rate ngoai CI (TSloss+,
  meanP-) DEU XAU (CI V3 hep hon).
=> WIN can DONG THOI (n~2x)+(size~1/2)+(chat luong khong xau ngoai CI)+(maxDD&UW<=baseline)+(CAGR trong 2pp).
   Hai tieu chi (UW) va (CAGR) FAIL o MOI config => **KHONG config nao thang**.

## 1. Nguyen nhan co hoc (vi sao that bai)
- Halve F_BASE => size/leg ~1/2 (dat), 2x count (dat) — NHUNG **gross exposure GIAM** thay vi giu nguyen:
  mMargin 1851 -> ~865 (giam >1/2 tuyet doi, con tren equity thap hon). Concurrency KHONG tang gap doi
  (n_eff khoi-72h co lenh: 96 -> 132/132/115; run dong thoi ~25-31 vs baseline ~25) => tong von trien khai THAP hon
  => CAGR tut 5-8pp.
- Lenh bien them (gate 1.30/1.50 + K12/K16) CHAT LUONG THAP hon: meanP 5.24 -> 3.7-4.3; TSloss% 9.73 -> 12-14.5;
  win% 88.25 -> 84.8-86.7. Nhieu lenh nho chat luong thap => sau moi dinh, equity mai moi lai dinh =>
  **UW keo dai** (92 -> ~222). Baseline it lenh nhung to/tot hon => bat lai dinh nhanh.
- Ket luan: "nhieu bet nho" o day DOI drawdown-depth lay drawdown-duration + return thap. KHONG phai giam rui ro
  theo tieu chi UW da dang ky, va KHONG giu duoc hieu qua.

## 2. Bang chinh (baseline + V1/V2/V3)
| tag | config | n | boi-n | size%/leg | size-ratio | win% | TSloss% | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GATE_REPRO (baseline) | gate1.70/K8/F0.03 | 1089 | 1.00 | 2.785 | 1.00 | 88.25 | 9.73 | 5.244 | 1851 | -11.84 | 92 | 111070 | 29.27 |
| X1_2XH_V1 | gate1.30/K12/F0.015 | 2100 | 1.93 | 1.537 | 0.55 | 84.90 | 14.33 | 3.713 | 884 | -10.48 | 223 | 83685 | 21.38 |
| X1_2XH_V2 | gate1.30/K16/F0.015 | 2573 | 2.36 | 1.412 | 0.51 | 84.80 | 14.46 | 3.838 | 867 | -11.41 | 222 | 92068 | 23.99 |
| X1_2XH_V3 | gate1.50/K16/F0.015 | 2121 | 1.95 | 1.425 | 0.51 | 86.70 | 12.07 | 4.290 | 864 | -10.65 | 221 | 90777 | 23.60 |

## 3. CI khoi-72h x1.21 (variant - baseline, TOAN CUA SO). Rate chat luong = win/TSloss/meanP
| config | win% (CI) | TSloss% (CI) | meanP (CI) | #rate CL ngoai CI |
|---|---|---|---|---|
| V1 | -3.34 [-7.61,+0.36] | +4.60 [-0.14,+9.39] | -1.53 [-3.48,+0.43] | 0 |
| V2 | -3.44 [-7.92,+0.40] | +4.72 [-0.11,+9.63] | -1.41 [-3.39,+0.60] | 0 |
| V3 | -1.54 [-3.65,+0.38] | **+2.34 [+0.41,+4.31]** | **-0.95 [-1.57,-0.25]** | 2 (deu xau) |
n & mMargin (bien kiem soat) ngoai CI o ca 3 (n tang, mMargin giam ~1/2) — dung ky vong.
V3 CI hep hon (block variance thap hon) nen 2 rate xau lo ra ngoai CI; V1/V2 CI rong nen diem xau van trong CI.

## 4. Rang buoc cung tung nam (maxDD<=15%, UW<=120, nam>=0, quy>=-5%)
| tag | verdict | chi tiet |
|---|---|---|
| baseline | **PASS 5 nam** | maxDD max -11.84, UW max 92 |
| V1 | **FAIL** | 2025 UW=223 (maxDD -6.58) |
| V2 | **FAIL** | 2025 UW=222 (maxDD -6.98) |
| V3 | **FAIL** | 2025 UW=221 (maxDD -4.33) |
maxDD ca nam deu <= baseline (nong hon) nhung UW 2025 vuot tran ~1.85x o ca ba => rui ro (theo UW) XAU hon.

## 5. Verdict theo luat WIN (can DONG THOI ca 5)
| tieu chi | V1 | V2 | V3 |
|---|---|---|---|
| (1) n 1.8-2.2x | PASS 1.93 | FAIL 2.36 | PASS 1.95 |
| (2) size ~1/2 | PASS 0.55 | PASS 0.51 | PASS 0.51 |
| (3) chat luong khong xau ngoai CI | PASS (0 out) | PASS (0 out) | FAIL (2 out, xau) |
| (4) maxDD & UW <= baseline | FAIL (UW 223) | FAIL (UW 222) | FAIL (UW 221) |
| (5) CAGR trong +-2pp | FAIL (-7.9pp) | FAIL (-5.3pp) | FAIL (-5.7pp) |
=> **KHONG config nao THANG.** Fail chung: (4) UW no ~2.4x, (5) CAGR tut 5-8pp.

## 6. Config gan nhat + trade-off
- **V1** dat NHIEU gate nhat (n~2x, size~1/2, chat luong-trong-CI, maxDD tot nhat -10.48) nhung CAGR te nhat (-7.9pp).
- **V3** can bang tot nhat ve diem: meanP cao nhat (4.29), TSloss thap nhat (12.07), maxDD -10.65, UW thap nhat (221),
  n 1.95x — NHUNG CI hep phoi bay 2 rate chat luong xau, va van fail UW + CAGR.
- **V2** CAGR cao nhat trong 3 (23.99) nhung n vuot (2.36x), chat luong/maxDD te nhat.
Neu buoc phai chon 1 "gan muc tieu (rui ro thap + giu hieu qua)" nhat: **KHONG cai nao dung dat**; can nhat la V3
(rui ro-depth tot, return-quality tot nhat) nhung UW va CAGR van truot. Khong de xuat ap dung.

## 7. Sai lech / ghi chu
- Config CO DINH theo pre-reg (khong tune ep 2x). Reproduction + knob-parity PASS TRUOC khi chay V.
- Knob dung SIM_F_BASE (da co san, Configs:545) thay vi them SIM_SIZE_SCALE — theo pre-reg (uu tien F_BASE neu co).
  Luu y: SIM_F_BASE ap TRUOC throttle nen 1/2 F_BASE khong phai scale tuyet doi (equity path) — no giam gross that
  su + tuong tac throttle; day la ly do gross tut va CAGR giam (khong phai chi co ti le).
- KHONG cham 242 (offline bin, TICKER_SOURCE=file). KHONG git push. Holdout 2026 nguyen (SIM_END_DATE=20251231).
- Devrun: X1_2XH_V1/V2/V3, GATE_REPRO, GATE_FB03 tai /home/ubuntu/java/devrun. Score raw: /home/ubuntu/java/score_2xh.out.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
