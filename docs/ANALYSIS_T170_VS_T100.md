# ANALYSIS_T170_VS_T100 — co che vi sao gate scale 1.70 khac gate 1.0 (chi doc, khong sim moi)

Agent phan tich, 2026-09-14. Chi DOC + phan tich; KHONG sim bien the moi, KHONG sua code, KHONG 242/push.
Muc tieu: hieu T170 (SIM_GATE_DYN_SCALE=1.70) LOC BO gi so voi T100 (1.0), loi/hai o dau, co phu thuoc
REGIME khong -> co so cho gate adaptive/rolling hay scale ngang.

Du lieu: `devrun/X1_C3_FULL_2021` (T100, scale 1.0, n=2559) vs `devrun/X1_GS_T170_2021` (T170, scale 1.70,
n=1089). Cung dataset `wfo_ds_x1_2021`, cung profile S1/net015, cua so exit 2021-07..2025-12. Khac DUY NHAT
= SIM_GATE_DYN_SCALE. Regime: `featv2/feat_v2_x1.parquet` (hourly, 627 sym), BTC 7d = `ret_7d - rs_btc_7d`.

**LUU Y BASELINE**: bai nay chay tren cap `_2021` (bat dau 2021-07). Pre-reg/ket qua chinh thuc
(`RESULT_GATESCALE.md`) dung baseline PARITY_R (bat dau 2022-01, n=2266, T170 n=940). Ket luan HUONG khop
nhau; con so TUYET DOI khac vi cua so khac. Xem muc 7 doi chieu.

---

## 0. TL;DR (so truoc)

1. **T170 KHONG "hieu qua hon" theo CAGR** — no THAP hon 2.7pp (T100 31.9% vs T170 29.3% tren cua so _2021;
   RESULT_GATESCALE: d=-3.9pp, CI om 0 => KHONG PASS luat pre-reg). Cai T170 duoc la RUI RO: maxDD -12.9% ->
   -6.3% (giam mot nua), underwater 247 -> 158 ngay, va chat luong lenh (win 84.6->90.3%, collapse 5.98->3.40%).
2. **T170 loc dung lenh bien xau**: 1455 lenh marginal (T100 co, T170 bo) co win 83.6%, collapse 6.74%, meanP
   2.36%, pnl/lenh 23.3 — deu XAU hon ro tap T170 giu (win 90.3%, collapse 3.40%, meanP 5.24%, pnl/lenh 69.9).
3. **Chat luong marginal PHU THUOC REGIME manh** (bang chung so, muc 4): theo xu the BTC 30 ngay, marginal net
   = **+34,606** khi macro UP (65.7/lenh) nhung **-13,787** khi macro CHOP (-35.6/lenh). Dau doi chieu.
4. Vi vay gate regime-adaptive **dang thu** nhung phai pre-reg 1 config khoa + cham OOS (muc 6): thuong tren
   giay hien co la winner's curse.
5. Reconcile GD92 (muc 8): GD92 = chuan hoa TROI MODEL (rolling pct cua predReturn15M), TRUC KHAC voi
   regime-scale = dieu tiet EXPOSURE theo THI TRUONG. GD92 NULL khong du bao regime-scale NULL.

---

## 1. Co che gate (xac nhan tu code)

`EntryGate` (nguon `src/.../tradecore/EntryGate.java`, dong 72-73):
```
float scale = (symbolPred / 0.15) * DYN_MULT;          // DYN_MULT=1.2876
return thrBase * Math.max(DYN_MIN, scale) * GATE_DYN_SCALE;   // thrBase=0.008 DYN_MIN=0.26787
```
=> voi symbolPred>0.0312: dieu kien vao lenh = `predReturn15M >= 0.068672 * symbolPred * GATE_DYN_SCALE`.
- Nguong TANG theo symbolPred (coin diem cao bi doi momentum manh hon), roi NHAN GATE_DYN_SCALE.
- T100: scale=1.0. T170: scale=1.70 => nang bar momentum +70% dong deu tren MOI coin/moi thoi diem.
- Chi nhan vao ket qua dyn_thr; KHONG dung floor/MULT goc; leg DCA_LEVEL1/BIG_DOWN KHONG bi scale.

**Gate la STATEFUL, khong phai loc thuan**: T170 KHONG phai tap con cua T100. Trung khop chinh xac
(sym+start) chi 355/1089; trung sym+ngay 775/842. Chan bot entry => giai phong von/slot => stream lenh
KHAC va gio vao lech phut. Vi vay "marginal" duoi day dinh nghia theo **sym+ngay** (lenh T100 tren mot
coin-ngay ma T170 KHONG dong vao), n=1455 — la XAP XI, khong phai hieu so tap sach.

---

## 2. (a) Marginal vs Kept — marginal XAU hon ro

| tap | n | win% | TSloss% | collapse% | meanP% | pnl/lenh | mean symbolPred | hold(h) |
|---|---|---|---|---|---|---|---|---|
| marginal (T100 bo boi T170) | 1455 | 83.6 | 16.4 | 6.74 | 2.36 | 23.3 | 0.233 | 43.9 |
| shared (ca 2 giu, sym+ngay) | 1104 | 86.1 | 13.9 | 4.98 | 4.25 | 47.9 | 0.206 | 36.8 |
| **T170-all** | 1089 | **90.3** | **9.7** | **3.40** | **5.24** | **69.9** | 0.181 | 28.7 |
| T100-all | 2559 | 84.6 | 15.4 | 5.98 | 3.17 | 33.9 | 0.223 | 40.8 |

collapse% = STOP_LOSS_DONE & profit<=-20. Chi co 2 status: STOP_MARKET_DONE (thang/chot) va STOP_LOSS_DONE.

Doc: marginal thua kept tren MOI truc — win -6.7pp, collapse gan **2 lan** (6.74 vs 3.40), meanP < mot nua,
pnl/lenh chi 1/3, holdtime dai hon (43.9 vs 28.7h = lenh lom nam lai an time-stop 168h).
**Nghich ly quan trong**: marginal co symbolPred CAO hon (0.233 vs 0.181) nhung ket qua XAU hon. Dung voi co
che: nguong dyn TANG theo score, nen lenh score-cao-momentum-yeu la lenh model TU TIN QUA MUC; scale 1.70 loc
dung nhom nay. T170 khong bo lenh diem thap — no bo lenh diem cao ma momentum khong xac nhan.

marginal VAN net duong tuyet doi (+33,834; 23.3/lenh) => bo chung lam GIAM tong pnl (do la ly do T170 -CAGR).
Cau hoi: duong deu hay doi dau theo regime?

---

## 3. (b) Theo nam — marginal duong o bull, AM o stress

| nam | marg n | marg pnl | marg pnl/lenh | marg win% | marg meanP | T100 pnl | T170 pnl |
|---|---|---|---|---|---|---|---|
| 2021 | 147 | +185 | 1.3 | 74.8 | 0.76 | 3,248 | 4,273 |
| 2022 | 218 | +2,472 | 11.3 | 84.4 | 2.39 | 6,619 | 7,688 |
| 2023 | 178 | +10,924 | 61.4 | 88.8 | 4.41 | 27,014 | 16,331 |
| 2024 | 378 | +21,861 | 57.8 | 85.7 | 4.12 | 32,687 | 20,403 |
| 2025 | 534 | **-1,608** | **-3.0** | 82.4 | 0.86 | 17,202 | **27,375** |

- 2023-24 (bull): marginal cong **+32,785** — day la CAGR ma T170 bo lai.
- 2025 (stress/chop): marginal **AM** (-1,608). Va o 2025 T170 (n=335, +27,375) VUOT T100 (n=884, +17,202)
  du bang 1/3 so lenh — o nam xau, cat marginal khong chi giam DD ma con TANG tong lai.
Day la bang chung truc tiep cho regime-dependence o tang nam.

---

## 4. (c) Theo REGIME — xu the BTC 30 ngay la tin hieu tach sach nhat

Regime gan tai ENTRY (floor gio), tu featv2. Thu 3 truc:

### 4a. Tuc thoi 7d BTC / 30d vol — tach YEU (marginal duong o gan het bucket)
| BTC7d bucket | marg pnl | pnl/lenh | coll% | | vol bucket | marg pnl | pnl/lenh | coll% |
|---|---|---|---|---|---|---|---|---|
| bear (<-2.0%) | +26,684 | 31.0 | 6.7 | | calm | +7,434 | 33.2 | 3.1 |
| side | +2,944 | 11.7 | 5.6 | | mid | +8,706 | 18.8 | 8.6 |
| bull (>+2.7%) | +4,206 | 12.3 | 7.6 | | stress | +17,695 | 23.1 | 6.6 |

Tuc thoi khong doi dau => tin hieu ngan han khong bat duoc "momentum co follow-through khong".

### 4b. MACRO xu the BTC 30 ngay (rolling 720h cua BTC7d) — DOI DAU RO
| macro bucket | marg n | marg pnl | pnl/lenh | win% | coll% | meanP |
|---|---|---|---|---|---|---|
| m_down (xu the giam) | 541 | +13,015 | 24.1 | 84.5 | 8.9 | 1.75 |
| **m_flat (chop)** | 387 | **-13,787** | **-35.6** | 79.8 | 8.0 | 0.84 |
| **m_up (xu the tang)** | 527 | **+34,606** | **+65.7** | 85.4 | 3.6 | 4.10 |

Dau pnl/lenh DOI CHIEU: -35.6 (chop) -> +65.7 (uptrend). Kinh te ro: momentum chet trong chop, song
theo song trong uptrend. Day la CO SO tin cay cho gate adaptive (bien do lon, khong phai vi dieu chinh nhieu).

### 4c. (d) T100 vs T170 tong theo macro — T170 lai o dau, mat o dau
| macro | T100 n | T100 pnl | T170 n | T170 pnl |
|---|---|---|---|---|
| m_down | 877 | +18,205 | 337 | +14,891 |
| **m_flat (chop)** | 646 | **-7,543** | 255 | **+16,847** |
| m_up | 1036 | +76,108 | 497 | +44,332 |

- Chop: T100 LO -7,543; T170 LAI +16,847 — swing **+24,390**. Toan bo uu the DD/UW cua T170 den tu day.
- Uptrend: T170 bo lai ~**31,776** pnl (44,332 vs 76,108) — toan bo chi phi CAGR den tu day.
=> Ket luan co che: T170 = danh doi loi nhuan uptrend LAY an toan trong chop. Neu tach duoc 2 regime,
   ta co the giu ca hai (in-sample upper bound lon).

---

## 5. Duong equity — tai lap DD/UW/CAGR (tu log b: hang ngay)

| | equity cuoi | CAGR% | maxDD% | maxDD$ | maxUW ngay |
|---|---|---|---|---|---|
| T100 | 121,770 | 31.94 | -12.89 | -17,393 | 247 |
| T170 | 111,070 | 29.27 | -6.30 | -5,947 | 158 |

Chenh CAGR -2.67pp; maxDD giam mot nua; UW 247->158. (Master ghi "UW 92 vs 248": T100=247 khop ~248;
T170 tong-cua-so=158 — chenh voi 92 la do dinh nghia UW khac, xem muc 9.)

**Rang buoc cung theo nam** (maxDD<=15, UW<=120, nam>=0, quy>=-5), cua so _2021:
| nam | T100 maxDD/UW/ret | T100 | T170 maxDD/UW/ret | T170 |
|---|---|---|---|---|
| 2022 | -9.7 / 101 / +17.3 | pass | -3.3 / 95 / +19.6 | pass |
| 2023 | -2.5 / 27 / +61.0 | pass | -1.9 / 64 / +35.4 | pass |
| 2024 | -8.9 / **121** / +44.8 | **FAIL UW** | -6.3 / 111 / +31.6 | pass |
| 2025 | -12.9 / **220** / +16.5 | **FAIL UW** | -5.1 / **158** / +32.7 | FAIL UW (158<<220) |

T170 cuu 2024 (qua UW) va giam manh 2025 (158 vs 220), du 2025 van >120. Do la gia tri thuc cua T170.

---

## 6. HUONG TIEP: gate regime-adaptive — co dang thu khong + thiet ke

**Co dang thu: CO, nhung voi ky luat pre-reg cao** — vi marginal DOI DAU theo regime (bien do lon,
-35.6 vs +65.7/lenh, story kinh te ro), khac han cac hieu ung 3pp nam trong nhieu ma CI_REAUDIT/AUDIT_GATEDYN
da bac. Upper bound in-sample = giu ~+31.8k uptrend ma T170 dang bo, DONG THOI giu swing +24.4k trong chop.
Effect nay LON hon san nhieu (sd_boot 5-7pp), nen dang mot lan cham OOS — khac GD92 (effect trong nhieu).

**Thiet ke chot cung (de xuat, chua chay):**
- 2 trang thai, KHOA truoc: `scale = 1.00` khi macro UP, `scale = 1.70` khi KHONG-UP (flat/down).
- Chi 1 nguong regime, dinh a priori — KHONG quet. Uu tien tin hieu da co san, nhan qua, tinh live duoc.

**Tin hieu regime (da co, khong can build moi):**
1. **BTC 30d trend**: dau return BTC 30 ngay (hoac rolling-mean BTC7d). Sach, nhan qua, live re; tach dep nhat.
2. **ValidateBrakeDynamic** da tag regime UP/DOWN/SIDE trong-sim (UP=0/DOWN=1/SIDE=2) va da co khung do
   "phanh cuu duoc bao nhieu, tach theo regime" — nha co san cho scale-theo-regime (UP => 1.0, con lai => 1.70).
3. Breadth (% coin duong 7d) / n_potential_losers dung duoc nhung nhieu hon; uu tien (1) hoac (2).

**Pre-reg goi y (khuon PREREG_GATESCALE + B4):**
- 1 config DUY NHAT da chot (vd macro=BTC30d>0 -> 1.0 else 1.70). KHONG mo bien the nguong.
- Ky vong ghi truoc: HOAC regime-scale > T170 ca CAGR lan giu DD (thang that), HOAC NULL.
- Luat quyet dinh: d CAGR vs PARITY_R > 1.4823*sd_boot (hieu chinh boi k=so bien the) VA qua rang buoc cung
  tung nam. UW/maxDD la QUAN SAT 1 lan, khong bien thanh CI (PREREG_CI 2.5).
- **Bat buoc OOS/holdout**: split m_up/m_flat la in-sample tren DEV, nguong regime do agent chon hau kiem
  (tercile) — chua pre-reg. Chi holdout 2026 (dang seal) moi bac duoc winner's curse.

**Goc scale-ngang**: m_up collapse thap (3.6%)+pnl/lenh cao => o uptrend co the NOI slot (TOPK>8) an toan;
chop/down thi KHONG. Cung adaptive-theo-regime nhung them 1 chieu tham so -> rui ro leak cao hon, de sau.
**Neu khong muon them knob**: giu T170 nhu SLEEVE rui-ro-thap ben canh T100 sleeve CAGR-cao; blend 2 sleeve
la trung diem ma KHONG can regime-signal moi.

---

## 7. Doi chieu ket qua chinh thuc (RESULT_GATESCALE.md, cua so PARITY_R 2022-2025)

| tag | scale | n | equity | CAGR% | d CAGR | CI95 d | vuot (i)? |
|---|---|---|---|---|---|---|---|
| PARITY_R | 1.00 | 2266 | 111,428 | +33.58 | — | — | baseline |
| T130 | 1.30 | 1386 | 86,322 | +25.32 | -8.26 | [-19.41,+1.72] | KHONG |
| **T170** | 1.70 | 940 | 98,988 | +29.68 | **-3.90** | [-18.06,+8.93] | **KHONG (CI om 0)** |
| L80 | 0.80 | 3462 | 74,151 | +20.65 | -12.93 | [-25.24,-0.96] | KHONG (am ro) |

Luat pre-reg PASS = (i) d CAGR > 1.4823*sd_boot VA (ii) qua rang buoc cung. **KHONG bien the nao PASS (i)**
=> verdict chinh thuc = "khong phan biet duoc o tang CAGR / giu incumbent". Ky vong ghi truoc NULL DA UNG.
NHUNG: T170 la bien the DUY NHAT co 2 rate chat luong NGOAI CI deu TOT (TSloss% -4.85, meanP +2.07) va cai
thien rang buoc cung tung nam manh nhat. => "T170 hieu qua hon" chi dung theo nghia RUI RO/CHAT LUONG, KHONG
theo CAGR. Bai _2021 nay khop huong do (T170: -CAGR, +chat luong, +an toan).

---

## 8. Reconcile GD92 (rolling percentile) — vi sao regime-scale KHAC

- **GD92 = GateRollingThreshold** (`ai_ml/onnx/entry/GateRollingThreshold.java`): nguong MOM15 co so = phan vi
  p (0.92-0.95) cua **predReturn15M cua CHINH MODEL** trong cua so rolling 90 ngay. Muc dich: chuan hoa TROI
  MODEL (mean predReturn15M troi 0.0036->0.0091 giua cac quy). Giu TY LE gate mo ON DINH => EXPOSURE-NEUTRAL,
  khong cat tong lenh, khong nhin THI TRUONG. Audit (AUDIT_GATEDYN_GD92): d CAGR +4.98pp nhung CI [-4.47,+16.09]
  om 0, nguong hieu chinh 2.2 lan effect; "thang" duy nhat (UW 116 vs 120) la diem lot khe (lang gieng 153/183)
  = dinh nhieu => NULL o tang hieu qua.
- **SIM_GATE_DYN_SCALE (T170)** = nhan HANG SO 1.70 vao dyn_thr => nang bar dong deu, cat ~57% lenh,
  EXPOSURE-REDUCING. Cung khong phan biet duoc o CAGR (d -3.9pp) nhung cai thien chat luong + rui ro.
- **Regime-adaptive scale** = nhan he so theo TRANG THAI THI TRUONG (BTC30d / UP-DOWN-SIDE) — TRUC THU BA,
  truc giao voi ca hai: khong phai chuan-hoa-model (GD92), khong phai hang-so (T170). **GD92 NULL KHONG du bao
  regime-scale NULL** vi tac dong len truc khac. Ly do regime-scale co the thang o cho ca hai kia hoa: pnl
  marginal DOI DAU theo regime (-13.8k chop vs +34.6k up) — hang so phai chon 1 thoa hiep, GD92 khong nham
  regime; regime-scale co the duong o CA hai. Nhung ky luat OOS/pre-reg van bat buoc (cung ly do da ha GD92):
  DEV 48 thang khong phan biet effect nho, va nguong regime o day la hau kiem.

---

## 9. Blocker / lech / gia dinh

1. **Non-nested**: T170 khong ⊂ T100 (gate stateful). "marginal" theo sym+ngay (n=1455) la XAP XI, khong phai
   hieu so tap. Trung chinh xac chi 355/1089.
2. **Window mismatch**: bai dung cap _2021 (start 2021-07); chinh thuc dung PARITY_R (start 2022-01). Con so
   tuyet doi khac; huong khop. maxUW T170 = 158 (_2021) vs 92 (master ghi) — kha nang dinh nghia UW khac
   (nguong %, hay tren PARITY_R). Can master xac nhan dinh nghia UW de khop chinh xac.
3. **Regime bucket hau kiem**: tercile BTC30d/vol do agent chon sau khi thay du lieu — DESCRIPTIVE, chua pre-reg.
4. **symbolPred null**: 302/2559 lenh T100 co symbolPred null (fallback gate cung). Khong loai; anh huong nho.
5. Chua cham 242/holdout/live-parity. Chi doc printDone + log + featv2.

## 10. Lenh tai lap
```
# regime hourly tu featv2 -> /home/ubuntu/scratch_regime.parquet:
#   btc7=median(ret_7d-rs_btc_7d), breadth=mean(ret_7d>0), mvol=median(vol_30d) group by ts
# macro=rolling(720h).mean(btc7); bucket tercile. marginal = T100 sym+ngay khong co trong T170.
# equity/DD tu regex 'Update (\d{8}) .* b:(\d+)' trong logs/sim.out.
```
Artifact tam (khong commit): `/home/ubuntu/scratch_regime.parquet`.
