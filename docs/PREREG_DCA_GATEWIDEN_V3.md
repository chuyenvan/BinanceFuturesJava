# PREREG_DCA_GATEWIDEN_V3 — NOI GATE + cat nua margin + DCA-signal cuu phan loss tang them

Pre-reg MOI, viet va COMMIT TRUOC khi chay bat cu thu gi. **Day la GIA THUYET KHAC**, khong phai tune tiep
nguong/cooldown cua V1/V2 — huong do DA DONG (docs/RESULT_DCA_SIGNAL_GATE_V2.md muc 11).
KHONG cham 242, KHONG `git push`, holdout 2026 NGUYEN VEN (`SIM_END_DATE=20251231`).

## 0. Vi sao V1/V2 that bai, va V3 sua dung cho nao
V1/V2 giu **nguyen gate T170 hep** (`SIM_GATE_DYN_SCALE=1.70`, ~1089 leg da loc rat ky), roi cat margin cua
**MOI** lenh trong quan the da sach do, de cho mot su kien lo sau **hiem**. Funnel da do (V2 muc 3): chi
**1.9-7.5%** cum tung cham -30/-40/-50%, va chi 0.09-17% cum ban duoc leg-2. Ket qua: ~99% (V2) / ~85% (V1)
von du tru nam khong => CAGR mat 6.5-10.3pp. Nut that = **ti le giai ngan von du tru**, khong phai nguong.

**Y cua user cho V3:** phai **NOI GATE TRUOC** de keo them quan the "marginal trades" that (lenh moi, coin
moi — KHAC han V1/V2 noi "lenh tang" chi la leg-2 cua chinh coin cu), giam margin/lenh de bu rui ro tong,
roi dung DCA-signal-gate de cuu dung phan loss tang them do noi gate:
*"tang dc lenh giam margin de tang su on dinh, loss tang thi dung dca giam xuong"*.

Co so tu chinh du an (`docs/ANALYSIS_T170_VS_T100.md`, commit 8878a96): quan the marginal (T100-only, bi
T170 loai, n=1455) co `symbolPred` TRUNG BINH **CAO HON** (0.233 vs 0.181 cua tap T170 giu) — model THICH
chung hon; chung bi chan vi **nguong momentum**, khong phai vi diem thap. Do la ung vien hop ly de "cuu bang
DCA" thay vi vut di — khac han ve ban chat so voi DCA vao mot lenh ngau nhien dang lo.

## 1. Hai RUI RO da biet — PHAI do va bao cao trung thuc du ket qua the nao
### Rui ro 1 — noi gate lam UW xau di (co bang chung THAT)
`docs/RESULT_REGIME_GATE.md`: noi gate MOT MINH (scale 1.00 luc BTC-30d UP, 1.70 con lai) => **UW no tu 92
len 189 ngay, VI PHAM tran cung 120**, du maxDD lai TOT hon (-9.74 vs -11.84). Lan nay co margin-cut + DCA
di kem nen CO THE khac, nhung **phai do UW rat ky theo tung nam**, va khong duoc ngac nhien neu no van xau.
T100 thuan (scale 1.00) cung FAIL: maxDD -16.13, UW 248.

### Rui ro 2 — quan the marginal PHU THUOC REGIME, va 2025 la nam xau cua no
`ANALYSIS_T170_VS_T100.md` muc 3 + 4b (so that):
- Theo macro BTC-30d: marginal net **+34,606** (+65.7/lenh) khi m_up, nhung **-13,787** (-35.6/lenh) khi
  m_flat/chop. **Doi dau**, khong phai vi dieu chinh.
- Theo nam: marginal 2023 +10,924 / 2024 +21,861 (bull, tot) nhung **2025 = -1,608 (-3.0/lenh)**. Va rieng
  2025, T170 (n=335, +27,375) VUOT CA T100 (n=884, +17,202) du chi bang 1/3 so lenh.
=> Rang buoc cung co `ret nam >= 0` va `ret quy >= -5%` theo **TUNG NAM**. Neu DCA khong cuu noi phan lo cua
marginal o 2025, config se FAIL **dung cho ma T170 von duoc thiet ke de tranh**. **Bat buoc bao cao PnL/UW
theo tung nam va tung quy, KHONG duoc chi bao cao so tong toan cua so.**

## 2. XAC NHAN THAM SO HOA — **KHONG CAN CODE MOI** (da verify truoc khi viet muc nay)
- `SIM_GATE_DYN_SCALE` -> `Configs` static block -> `EntryGate.GATE_DYN_SCALE` (EntryGate.java:58, dung o
  dong 82: `gateScale = GATE_REGIME_ADAPTIVE ? CURRENT_REGIME_SCALE : GATE_DYN_SCALE`).
  `GATE_REGIME_ADAPTIVE` mac dinh OFF => scale duoc doc THANG tu profile. Khong can flag moi.
- `SIM_DCA_SIGNAL_GATE` / `_LOSS` / `_BASE_RATIO` / `_COOLDOWN_MIN` — da co tu V1 (commit bd45a50), tat ca
  deu doc qua profile. Tie-break voi grid DCA (commit 130ad24) van con nguyen va van chay khi flag ON.
- => V3 **KHONG THEM MOT DONG CODE NAO**. HEAD khi chay = `1063dd1`, jar da build, 137/137 test PASS.
  Neu phai sua code vi bat cu ly do gi, se ghi ro trong RESULT.

**Luu y co che quan trong**: gate scale chi ap cho leg qua `EntryGate` (PREDICT_SYMBOL_TRADE), KHONG ap cho
leg DCA_LEVEL1/BIG_DOWN. Leg-2 cua DCA-signal-gate di qua DUNG `PREDICT_SYMBOL_TRADE` nen **no cung chiu
gate da noi** — dung y do: leg-2 phai vuot dung cai cong ma lenh moi vuot, o cung do rong.

## 3. THIET KE (khoa cung, khong doi sau khi thay so)
Ba thanh phan, CHI thanh phan (a) la bien sweep:

**(a) NOI GATE** — `SIM_GATE_DYN_SCALE` in {1.00, 1.20, 1.40} (noi dan tu T170=1.70 ve phia T100=1.00).
**(b) CAT NUA MARGIN** — `SIM_DCA_SIGNAL_BASE_RATIO=0.5` (y het V1/V2). **CO DINH**, khong sweep lan nay
    (giu mot bien co dinh de khong no so chieu sweep).
**(c) DCA-SIGNAL-GATE = DUNG cau hinh DCA8 cua V1** — `SIM_DCA_SIGNAL_GATE=true`,
    `SIM_DCA_SIGNAL_LOSS=-0.08`, `SIM_DCA_SIGNAL_COOLDOWN_MIN=60` (gia tri GOC cua V1, **KHONG** phai
    1440/2160/2880 cua V2).

> **Vi sao chon DCA8 chu khong phai cau hinh CAGR cao nhat**: trong V1, DCA8 la cau hinh **DUY NHAT** vua
> PASS rang buoc cung moi nam vua co fire-rate chap nhan duoc (17.2% cum ban duoc leg-2 — cao nhat trong
> ca 6 config cua V1+V2). DCA5 co CAGR tuong duong nhung **FAIL** UW 2025 = 164. Chon theo tieu chi AN TOAN
> + fire-rate, da xac nhan DOC LAP voi viec noi gate. Day la lua chon cua master, chot truoc, khong fit.

### Ba config
| tag | `SIM_GATE_DYN_SCALE` | `SIM_DCA_SIGNAL_GATE` | `_LOSS` | `_BASE_RATIO` | `_COOLDOWN_MIN` | profile |
|---|---|---|---|---|---|---|
| `DS_GS100` | **1.00** | true | -0.08 | 0.5 | 60 | `profiles/ds_gs100.properties` |
| `DS_GS120` | **1.20** | true | -0.08 | 0.5 | 60 | `profiles/ds_gs120.properties` |
| `DS_GS140` | **1.40** | true | -0.08 | 0.5 | 60 | `profiles/ds_gs140.properties` |

Moi profile = `profiles/x1_gs_t170.properties` doi DUNG mot dong `SIM_GATE_DYN_SCALE` + them 4 key DCA.
KHONG co config nao khac. KHONG them bien the sau khi thay so.

### BASELINE so sanh = **T170 GOC**
`RG_A_T170`: scale 1.70, **KHONG** margin-cut, **KHONG** DCA. md5 `efb793e2468ca3a7318da0f0ad23d4fc`,
n=1089, equity 111,070, CAGR 29.27, maxDD -11.84, UW 92, win% 88.25, TSloss% 9.73, meanP 5.244.
**KHONG** so voi "T170+DCA8" (`DS_DCA8`) — do la ban cua V1, chi dung de doi chieu phu.
Tham chieu phu: T100 (`RG_A_T100`) n=2559, equity 121,770, CAGR 31.94, maxDD -16.13, UW 248 (**FAIL** hard).

## 4. CONG PARITY — BAT BUOC PASS TRUOC KHI CHAY BAT KY CONFIG ON NAO
| cong | tag | profile | ky vong |
|---|---|---|---|
| scale 1.70 + DCA flag OFF | `DS_PARITY_V3` | `ds_v3_parity.properties` = T170 + **4 key DCA khai bao day du nhung `GATE=false`** | md5 `efb793e2...` (n=1089) |

Cong nay MANH hon viec chay lai profile T170 tran: no chung minh bon key DCA co mat trong profile nhung
**vo hai khi flag OFF** (khong key nao am tham doi sizing/dem leg). FAIL => dung, khong bao cao ket qua ON.

## 5. Dataset + cham diem (Y HET moi lan truoc — khong doi mot chu)
- Dataset `/home/ubuntu/wfo_ds_x1_2021`, config `configs/sim_dev_file_2021.properties`,
  `SIM_END_DATE=20251231`, harness `/home/ubuntu/k_runarm.sh <TAG> <PROFILE>`.
- `research/analysis/x1_rates.py` (may bootstrap `c3_rates.py`): khoi 72h, block-paired, NREP=2000,
  SEED=20260905, CI x1.21. `python3 x1_rates.py <DS_X> RG_A_T170` => in hieu (T170 - config).
- **Rang buoc cung theo TUNG NAM**: maxDD <= 15%, UW <= 120 ngay, ret nam >= 0, ret quy >= -5%.
- **THANG** = (>= 2 rate CHAT LUONG trong {win%, TSloss%, meanP} ngoai CI theo huong TOT CHO CONFIG)
  **VA** (rang buoc cung PASS **TAT CA** cac nam). Moi truong hop khac => **NULL**. Khong dien giai mem.

## 6. BAO CAO BAT BUOC trong RESULT_DCA_GATEWIDEN_V3.md
1. Bang chuan vs **T170 goc** (n, win%, TSloss%, meanP, mMargin, maxDD%, UW, equity, CAGR%).
2. **UW theo TUNG NAM cho TUNG config** (rui ro 1) — khong duoc chi bao UW tong.
3. **PnL/return theo TUNG NAM va TUNG QUY** (rui ro 2), **noi bat rieng 2025**.
4. **% so lenh tang** — va phai tach: bao nhieu la **CUM moi** (coin moi, do noi gate) vs bao nhieu la
   **leg-2** (cung coin, do DCA). Day la diem KHAC ban chat so voi V1/V2 va phai chung minh bang so.
5. Phieu loc DCA: % cum ban duoc leg-2, PnL cua leg-signal, so cum duoc "cuu".
6. CI day du + verdict THANG/NULL theo dung win rule.

## 7. CAM KET
- Tham so muc 3 DA KHOA truoc khi chay. KHONG tune sau khi thay ket qua. KHONG them config.
- KHONG deploy 242. KHONG `git push`. Chi commit LOCAL tren branch `module`.
- Holdout 2026 KHONG mo. Neu can sua code ngoai du kien => ghi ro trong RESULT.
- Neu ket qua NULL thi bao NULL; neu UW/2025 xau thi bao dung nhu the — hai rui ro o muc 1 duoc ghi TRUOC
  khi chay chinh la de khong ai phai to hong hay bao chua sau do.
