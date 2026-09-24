# RESULT_D3D4_FILTER_SIM — chay sim filter D3/D4 (pump-dump) doi chieu baseline T170

**Verdict: NULL — ca 3 bien the KHONG cai thien chat luong; giu nguyen T170 (parity).**

Chay dung `docs/prereg/PREREG_D3D4_FILTER_SIM.md` (commit `2c8a7a8`). Filter pump-dump POST-HOC (D3
`oi_px_div`, D4 `stall`) ap cho LENH MOI (selector Best-N + BIG_DOWN), bo qua neu feature > p90.
Ca 3 bien the (FILT_D3 / FILT_D4 / FILT_D3D4) deu **KHONG dat >= 2 rate chat luong ngoai CI**. D4
co meanP ngoai CI (1 rate) nhung chua du nguong; D3/D3D4 giau ky thuc ra HƠI XAU (TSloss% tang,
meanP giam) du chua ngoai CI. KHONG push. DEV 2021-07..2025-12 (`wfo_ds_x1_2021`).

- Pre-reg: `docs/prereg/PREREG_D3D4_FILTER_SIM.md` (commit `2c8a7a8`).
- Baseline parity md5 `efb793e2468ca3a7318da0f0ad23d4fc`.

## 0. KHA THI (Buoc 1 — tom tat)

| feature | nguon in-sim | ket luan |
|---|---|---|
| D4 `stall = ret_6h - ret_15m` | HistoryManager (ring 1m) | KHA THI in-sim, KHONG can bang tra cuu |
| D3 `ret_24h` | HistoryManager (ring 1m) | KHA THI in-sim |
| D3 `oiDelta24h` | bang tra cuu `filter_oi_lookup.bin` (OI 5m, 111.5M record) | KHA THI (binary-search floorEntry) |

- D4 KHONG can nguon 15m ngoai (dung 1m-close cua HistoryManager, trung quy uoc screen).
- p90 DEV (920 leg entry moi): D3 = 0.31944, D4 = 0.11277 (co dinh, KHONG toi uu).

## 1. Cong parity (bat buoc)

Flag `SIM_FILTER_D3D4=off` (profile `x1_gs_t170` KHONG khai key) => `printDone.csv` **byte-identical**
`efb793e2468ca3a7318da0f0ad23d4fc` (1090 dong, 1089 trade). PASS.

## 2. Co che — so lenh bi loc (binding)

| tag | mode | candidate bi loc (skipped) | n lenh cuoi | n leg-1 (entry moi) | n DCA | net giam (vs parity) |
|---|---|---|---|---|---|---|
| PARITY | off | — | 1089 | 1069 | 20 | — |
| FILT_D3 | d3 | 4942 | 980 | 962 | 18 | **-109** |
| FILT_D4 | d4 | 597 | 1035 | 1015 | 20 | **-54** |
| FILT_D3D4 | both | 5476 | 930 | 912 | 18 | **-159** |

- **Filter giam BINDING thap**: D3 loc 4942 candidate nhung net chi -109 lenh (45x). Ly do: selector
  top-8 moi tick sinh nhieu candidate, da so bi chan boi budget/breaker KHOI lenh; filter bo qua
  candidate bi chan san => khong giam lenh THAT. Dong thoi khi bo qua 1 candidate, budget chuyen sang
  candidate rank ke tiep (thay the) => thanh phan coin doi nhung SO LENH it doi.
- DCA giam 20->18 o D3/D3D4 la HE QUA GIAN TIEP (leg-1 bi loc => cum do khong bao gio co DCA),
  KHONG phai filter truc tiep len DCA (dung thiet ke: KHONG ap DCA).

## 3. PRIMARY — 5 rate chat luong TOAN BO leg (so sanh tung bien the vs parity)

CI block 72h x1.21, 2000 rep, seed 20260905. "Tot" = win% & meanP tang, TSloss% giam.

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---|---|---|---|---|---|
| PARITY | 1089 | 88.25 | 9.73 | 7.642 | -16.992 | 5.244 |
| FILT_D3 | 980 | 88.06 | 10.71 | 7.591 | -17.118 | 4.944 |
| FILT_D4 | 1035 | 88.60 | 9.57 | 7.788 | -16.397 | 5.475 |
| FILT_D3D4 | 930 | 88.28 | 10.54 | 7.713 | -16.525 | 5.158 |

Hieu (parity - variant) + CI (ngoai CI neu CI khong chua 0):

| bien the | win | tsloss | mp_sm | mp_sl | meanP | so rate ngoai CI |
|---|---|---|---|---|---|---|
| FILT_D3 | +0.185 CI[-0.278,+0.757] | -0.981 CI[-2.360,+0.149] | +0.050 | +0.126 | +0.300 CI[-0.191,+0.797] | **0** |
| FILT_D4 | -0.353 CI[-0.967,+0.287] | +0.168 CI[-0.419,+0.862] | -0.146 CI[-0.338,+0.020] | -0.595 | **-0.231 CI[-0.450,-0.026] CO** | **1** |
| FILT_D3D4 | -0.033 CI[-0.830,+0.800] | -0.804 CI[-2.526,+0.751] | -0.071 | -0.467 | +0.085 CI[-0.465,+0.629] | **0** |

- **FILT_D3**: 0/5 rate ngoai CI. Huong thuc te HOI XAU: TSloss% tang (9.73 -> 10.71), meanP giam
  (5.244 -> 4.944), win% giam nhe. => loc oi_px_div > p90 KHONG lo duoc SUP ma cat vao loi nhe.
- **FILT_D4**: 1/5 rate ngoai CI (meanP +0.231, huong TOT). win% tang nhe, TSloss% giam nhe nhung
  chua ngoai CI. => tin hieu stall co xu huong tot nhung YEU, 1 rate < nguong >=2.
- **FILT_D3D4**: 0/5 ngoai CI. Ket hop hai filter lam TSloss% tang (9.73 -> 10.54), trung hoa loi
  cua D4. => khong tang gia tri so voi D4 don le.

=> Khong bien the nao dat PRIMARY (>=2/5 rate ngoai CI cung huong tot). NULL.

## 4. Tap trung (chan cung #2)

`max % equity 1 coin` = 9.77% (parity) / 7.81% (D3) / 9.76% (D4) / 7.99% (D3D4). Deu <= 15%,
KHONG tang. PASS.

## 5. Rang buoc cung tu equity THAT (`sim.out`) theo nam (chan cung #3)

Nguong MOI (docs/runbooks/RISK_APPETITE.md): maxDD <= 30%/nam, UW <= 200 ngay, khong nam am, quy >= -15%.

| tag | maxDD nam xau nhat | UW dai nhat | nam am | quy xau nhat | ket luan |
|---|---|---|---|---|---|
| PARITY | -11.84 (2022) | 92 (2024) | khong | -0.9% | PASS |
| FILT_D3 | -8.86 (2022) | **128 (2025)** | khong | -2.8% | PASS |
| FILT_D4 | -11.84 (2022) | 92 (2024) | khong | -0.9% | PASS |
| FILT_D3D4 | -8.88 (2022) | **128 (2025)** | khong | -2.8% | PASS |

- Ca 4 deu PASS nguong MOI. Nhung D3/D3D4 lam **UW dai hon** (92 -> 128 ngay) va return 2024-2025
  thap hon (D3: 28.4/25.6 vs parity 32.1/32.7) — loc bo lenh lam portfolio it "quay lai dinh" hon.
- maxDD nam CAI THIEN nhe o D3/D3D4 (-8.9 vs -11.8) chi vi it lenh hon (it rui ro it loi), KHONG
  phai chat luong tot hon.

## 6. Equity / PnL / CAC chi so (bao cao rieng — KHONG dung de chon)

| tag | n | equity cuoi | CAGR% | maxDD% | PnL tong (USD) |
|---|---|---|---|---|---|
| PARITY | 1089 | 111070 | 29.27 | -11.84 | +76070 |
| FILT_D3 | 980 | 100299 | 26.37 | -8.86 | +65300 |
| FILT_D4 | 1035 | 114476 | 30.14 | -11.84 | +79477 |
| FILT_D3D4 | 930 | 102028 | 26.85 | -8.88 | +67029 |

- FILT_D4 co equity/CAGR cao nhat (114476 / 30.14%) nhung day la do n=1035 (it hon parity) ma
  meanP cao hon chut — KHONG phai bang chung (1 rate ngoai CI). Equity KHONG phai tieu chi.
- FILT_D3 va FILT_D3D4 co equity THAP hon parity (100299 / 102028 vs 111070) => loc qua tay cat
  vao lenh LAI.

## 7. KET LUAN

- **Ca 3 bien the deu NULL** theo nguong bang chung (>=2 rate chat luong ngoai CI). Filter pump-dump
  D3/D4 (post-hoc, rho ~0.56-0.58 o screen mo ta) **KHONG tai lap duoc thanh cai thien chat luong**
  khi ap dung nhu filter lenh moi trong sim that tren T170.
- **FILT_D4 (stall) huong tot nhat** (meanP +0.23 ngoai CI, win% tang, TSloss% giam) nhung 1/5 rate,
  chua du nguong; D3 va D3D4 giau ky HOI XAU (TSloss% tang). => tin hieu "mat da" (stall) co mot
  chut gia tri, "OI phan ky" (oi_px_div) KHONG.
- **Co che binding thap**: filter bo qua nhieu candidate (4942 D3) nhung net chi -109 lenh vi da so
  candidate bi chan boi budget/breaker san + candidate bi loc duoc thay the boi rank ke tiep.
- **CANH BAO POST-HOC (phai ghi)**: day la luat chon SAU khi da nhin DEV. Multiplicity 11 detector
  tich luy. Ket qua duong tren DEV chi la UNG VIEN, KHONG ap dung; can holdout 2026 de xac nhan.
  O day ca 3 deu NULL nen khong co gi de theo tiep.

## 8. Gioi han

- D3 `oiDelta24h` doc tu bang tra cuu 5m (khong phai OI raw); OI file KHONG chua OI 1h/4h.
- D4 dung 1m-close HistoryManager (ring 2048 bar ~34h); coin co gap > 30m => feature NaN => KHONG
  filter (giu lenh). Thanh phan gom 1m -> 1h co the lech ULP so screen, khong anh huong ket luan.
- p90 tinh tren 920 leg DEV entry moi (2022-2025); sim chay 2021-07..2025-12 nen 2021 H2 cung bi
  filter bang cung nguong.
- `skipped` dem moi lan createOrder candidate bi loc (ke ca candidate se bi budget chan), KHONG phai
  so lenh THAT bi giam; dung "net giam" o muc 2 de do binding.

Co-Authored-By: Claude (subagent) — pre-reg truoc, khong push.
