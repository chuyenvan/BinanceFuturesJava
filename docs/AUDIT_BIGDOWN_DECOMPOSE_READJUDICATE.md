# AUDIT_BIGDOWN_DECOMPOSE_READJUDICATE — T170 thang nho ENTRY gioi hay nho leg BIG_DOWN?

> **Day la AUDIT TINH HOP LE cua lua chon DA CO (T170 = incumbent), KHONG phai de xuat co che moi va
> KHONG phai can cu de tune bat ky tham so nao ngay bay gio.** Khong chay backtest moi, khong sua code.
> Chi doc lai 3 `printDone.csv` cua vong re-adjudication goc:
> T100=`X1_C3_FULL_2021` (dc16e4da) · T130=`X1_GS_T130_2021` (68510567) · T170=`X1_GS_T170_2021` (efb793e2).

2026-09-15. Xuat phat tu `DIAG_UW_WINDOW_202503_202510.md`: trong giai doan xau, PnL chu yeu den tu leg
**BIG_DOWN** (bat day) chu khong tu entry qua gate. Cau hoi: so 3 scale co dang tron lan (a) chat luong
entry — thu ma gate scale THUC SU dieu khien — voi (b) so "ve" BIG_DOWN?

## 0. Xac minh phan loai trong CODE (lam truoc khi dem)
- `SimulatorMarketLevelTicker1MStopLoss.createOrder`: `if (!levelChange.equals(BIG_DOWN)) { entryGate(...) }`
  => **chi BIG_DOWN duoc mien HOAN TOAN cong gate.**
- `EntryGate.threshold(thrBase, symbolPred)`: `if (symbolPred == null) return thrBase;` — javadoc ghi ro
  *"nhanh nguong CO SO (symbolPred == null: BIG_DOWN / DCA_LEVEL1 / leg market-signal) **KHONG bi scale**"*.
  `GATE_DYN_SCALE` chi nhan vao nhanh `symbolPred != null`.
=> **Nhom KHONG chiu gate scale = `BIG_DOWN` + `DCA_LEVEL1`.** Nhom chiu gate scale = `PREDICT_SYMBOL_TRADE`.

## 1+2. Phan ra PnL theo nguon leg, theo tung nam (USD, theo nam DONG lenh)
| cfg | nhom | n | pnl | pnl/leg | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| T100 | PREDICT_SYMBOL_TRADE | 2257 | 67,115 | 29.7 | +2,493 | +2,447 | +25,183 | +29,044 | +7,948 |
| T100 | BIG_DOWN | 248 | 11,557 | 46.6 | +754 | +1,157 | +2,174 | +3,479 | +3,992 |
| T100 | DCA_LEVEL1 | 54 | 8,098 | 150.0 | 0 | +3,015 | 0 | −180 | +5,262 |
| **T100** | **TONG** | **2559** | **86,770** | | \multicolumn — **ENTRY 77.3% / khong-qua-gate-scale 22.7%** | | | | |
| T130 | PREDICT_SYMBOL_TRADE | 1301 | 41,518 | 31.9 | +1,731 | +2,919 | +17,823 | +13,125 | +5,920 |
| T130 | BIG_DOWN | 248 | 13,218 | 53.3 | +820 | +1,240 | +2,366 | +5,493 | +3,299 |
| T130 | DCA_LEVEL1 | 31 | 2,881 | 92.9 | 0 | +2,963 | 0 | −174 | +92 |
| **T130** | **TONG** | **1580** | **57,617** | | **ENTRY 72.1% / khong-qua-gate-scale 27.9%** | | | | |
| T170 | PREDICT_SYMBOL_TRADE | 821 | 47,115 | **57.4** | +3,291 | +3,067 | +14,615 | +13,925 | +12,216 |
| T170 | BIG_DOWN | 248 | 16,254 | **65.5** | +982 | +1,358 | +2,022 | +6,172 | +5,720 |
| T170 | DCA_LEVEL1 | 20 | 12,701 | **635.1** | 0 | +3,263 | 0 | 0 | +9,438 |
| **T170** | **TONG** | **1089** | **76,070** | | **ENTRY 61.9% / khong-qua-gate-scale 38.1%** | | | | |

**Doc ngay duoc:** ti trong PnL den tu co che **KHONG chiu gate scale** tang don dieu khi gate that chat:
T100 **22.7%** → T130 **27.9%** → **T170 38.1%**. Tuc **T170 la ban PHU THUOC NHIEU NHAT vao phan ma
gate scale khong dieu khien.** Day la mot canh bao that su cho cach doc "T170 thang vi gate chon gioi hon".

## 3. So "VE" BIG_DOWN — **HOAN TOAN KHONG phu thuoc gate scale** (bac bo gia thuyet (b) o phan DEM)
| cfg | n leg BIG_DOWN | n tick kich hoat | n ngay kich hoat | n coin | concurrency tb | n cum |
|---|---|---|---|---|---|---|
| T100 | **248** | **124** | **54** | 161 | **2.60** | 2505 |
| T130 | **248** | **124** | **54** | 166 | **1.49** | 1549 |
| T170 | **248** | **124** | **54** | 161 | **0.81** | 1069 |

**248 leg / 124 tick / 54 ngay — GIONG HET NHAU o ca ba**, trong khi concurrency chenh **3.2 lan**
(2.60 vs 0.81). Ly do co che: BIG_DOWN do `MarketBigChangeDetector` kich hoat theo **GIA THI TRUONG**,
so leg moi lan = `NUMBER_ENTRY_EACH_SIGNAL` co dinh; `symbolLocked` chi doi **coin nao** duoc chon
(161/166/161 coin khac nhau), **khong doi SO LUONG**.
=> **Gate rong hon KHONG tao ra nhieu "ve" BIG_DOWN hon. Gia thuyet (b) SAI o truc so luong.**

**NHUNG (b) DUNG o truc GIA TRI moi ve:** pnl/leg BIG_DOWN tang don dieu theo do chat cua gate —
**46.6 → 53.3 → 65.5** (T170 rut duoc **+41%** PnL tu **cung 248 leg, cung 124 tick, cung 54 ngay**).
Co che: gate chat => concurrency thap => `marginRunning/equity` thap => `managerBudget` throttle
`1 − u/U_MAX` cao hon => **moi leg BIG_DOWN duoc cap von lon hon**.
**Day la he qua NHAN QUA cua gate chat, khong phai an may.** Phai ghi cong cho T170 o diem nay —
nhung cung phai ghi ro: **do la loi ich GIAN TIEP qua co che sizing, khong phai "chon entry gioi hon".**

## 4. CHI XET ENTRY THUONG — T170 co con thang khong?
### 4a. Rate muc leg (phep do TIN CAY, khong can dung lai equity path)
| cfg | n | win% | TSloss% | meanP | mMargin | pnl/leg |
|---|---|---|---|---|---|---|
| T100 | 2257 | 84.54 | 15.02 | 2.562 | 2030 | 29.7 |
| T130 | 1301 | 85.47 | 13.84 | 3.087 | 1833 | 31.9 |
| **T170** | **821** | **88.31** | **10.11** | **4.221** | 1891 | **57.4** |

(doi chieu, TOAN BO leg nhu vong goc: T100 84.33/15.36/3.173 · T130 85.57/13.48/3.755 · T170 88.25/9.73/5.244)

**Diem uoc luong: T170 tot hon T100 tren CA BA rate ngay ca khi bo BIG_DOWN** (win +3.77pp,
TSloss −4.91pp, meanP +1.66), va **pnl/leg gap 1.93 lan**. => Gate that CHAT THAT SU cai thien chat
luong tung lenh. Phan "huong" cua ket luan goc DUNG VUNG.

### 4b. CI block-72h tren ENTRY-ONLY (may bootstrap y het vong goc; hieu = variant − T100)
| he so | T170 − T100 | T130 − T100 |
|---|---|---|
| **1.177 (k=2, he so DUNG)** | **1 rate TOT** — tsloss −4.910 [−9.265, −0.278] | **0 rate** |
| 1.210 (he so da dung) | **1 rate TOT** — tsloss −4.910 [−9.389, −0.154] | **0 rate** |

Chi tiet T170 − T100 (CI 1.21): win **+3.770 [−0.946, +8.414]** (trong CI) · tsloss **−4.910
[−9.389, −0.154]** (NGOAI, tot) · meanP **+1.660 [−0.290, +3.852]** (trong CI).

**So sanh truc tiep voi vong goc (TOAN BO leg):** T170 co **2** rate ngoai CI o 1.21 (tsloss −5.624,
meanP +2.071) va **3** rate o 1.177. Tren **ENTRY-ONLY chi con 1** (tsloss) — `meanP` tut tu
+2.071[+0.067,+3.983] (ngoai CI) xuong +1.660[−0.290,+3.852] (**vao trong CI**).

=> **PHAN QUYET muc 4: neu CHI xet entry qua gate, T170 KHONG con dat nguong thang (1 rate < 2).**
T130 van 0 rate => NULL, khong doi.

## 5. GIOI HAN PHUONG PHAP — phai doc truoc khi trich dan muc 4
1. **Day la PHAN RA (attribution), KHONG phai PHAN THUC (counterfactual).** Bo PnL cua leg BIG_DOWN ra
   **khong** mo phong duoc mot the gioi khong co BIG_DOWN: neu khong co no, von khong bi chiem, throttle
   khac, sizing cac leg entry sau do khac, va dong lenh se khac han. Con so muc 4 tra loi cau
   *"phan nao cua ket qua DA CO den tu dau"*, **khong** tra loi *"T170 se ra sao neu tat BIG_DOWN"*.
2. **Duong equity tong hop lai KHONG dung de cham hard-constraint.** Toi co thu (CAP0=35,000 +
   cumsum(pnl) theo ngay dong lenh) va **cong kiem soat cua chinh phuong phap da FAIL**:
   | cfg | nguon | maxDD% | UW |
   |---|---|---|---|
   | T170 | equity THAT (sim.out, co unrealized) | **−11.84** | **92** |
   | T170 | tong hop ALL-leg (phuong phap nay) | −6.18 | **158** |
   | T170 | tong hop ENTRY-ONLY | −8.48 | 159 |
   Ban tong hop ALL-leg le ra phai tai lap duoc ban that, nhung no ra maxDD **nhe hon** va UW **nang hon
   1.7 lan** — vi no chi ghi nhan PnL **luc DONG lenh** va bo qua **unrealized mark-to-market**, ma
   unrealized moi la thu tao ra DD/UW that. Ket qua: **ca T170 ALL-leg cung "FAIL" UW 158>120 du ban
   THAT PASS o 92.** => **Moi con so hard-constraint tren duong tong hop deu VO NGHIA; toi khong bao cao
   chung nhu mot phan quyet.** (So tho van luu trong `research/analysis/bigdown_decompose.py` de tai lap.)
3. Phan **TIN CAY** la muc 4a/4b: rate muc leg va CI bootstrap **khong can** duong equity, nen khong bi
   loi tren. Do la co so duy nhat toi dung de ket luan.

## 6. PHAN QUYET — noi thang
**1) So "ve" BIG_DOWN KHONG phu thuoc gate scale.** 248 leg / 124 tick / 54 ngay, **giong het nhau**
o ca T100/T130/T170 du concurrency chenh 3.2 lan. Gia thuyet "gate rong => nhieu co hoi BIG_DOWN hon"
**SAI**. T170 **khong** duoc nhieu ve hon.

**2) Nhung T170 rut duoc NHIEU TIEN HON tu cung so ve** (46.6 → 53.3 → **65.5** USD/leg, +41% so T100),
vi gate chat => it lenh dong thoi => con nhieu von => moi leg BIG_DOWN duoc cap budget lon hon.
Day la **he qua nhan qua cua gate**, khong phai may rui — nhung no la loi ich qua **co che SIZING**,
khong phai qua **chat luong chon entry**.

**3) T170 CO THAT SU chon entry tot hon** — tren entry-only, no hon T100 o ca ba rate ve diem uoc luong
(win +3.77pp, TSloss −4.91pp, meanP +1.66) va **pnl/leg gap 1.93 lan**. Huong cua ket luan goc dung.

**4) NHUNG ve MUC DO TIN CAY THONG KE thi KHONG con du:** tren entry-only, T170 chi con **1** rate ngoai
CI huong tot (TSloss%), duoi nguong **>=2** cua chinh du an. `meanP` — mot trong hai rate da dung de
tuyen bo T170 thang o vong goc — **roi vao trong CI** khi bo BIG_DOWN/DCA ra.

**=> Ket luan trung thuc: phan quyet "T170 thang" o vong goc KHONG BEN VUNG hoan toan khi tach rieng
phan ma gate scale that su dieu khien.** No dung o *huong* (entry cua T170 tot hon that), nhung *do manh
thong ke* dat nguong thang la nho mot phan vao cac leg **BIG_DOWN + DCA_LEVEL1** — vốn **khong di qua
gate** va **khong bi gate scale**, tuc **khong phai thu ma tham so dang duoc chon (`GATE_DYN_SCALE`)
kiem soat**. Ti trong phan do o T170 la **38.1%** PnL, cao nhat trong ba ban.

**Dieu nay KHONG tu dong lat do T170:**
- T130 van NULL o moi cach cat (0 rate entry-only) — khong co ung vien nao tot hon noi len.
- T100 co nhieu PnL entry hon (67,115 vs 47,115) nhung **chi vi nhieu lenh hon 2.7 lan**; chat luong moi
  lenh kem hon han, va T100 **tu FAIL rang buoc cung** o ban THAT (2024 UW=121, 2025 UW=227).
- Phep thu hard-constraint tren entry-only **khong thuc hien duoc** (muc 5.2) nen **khong co bang chung
  nao noi T100/T130 tot hon T170 ve rui ro** khi bo BIG_DOWN.
=> Trang thai dung: **T170 van la lua chon hop ly nhat trong ba, nhung co so thong ke cua no yeu hon
ban goc da ghi.** Quyet dinh giu/doi incumbent thuoc ve master va user — audit nay khong quyet dinh.

## 7. VIEC NAY KHONG CHO PHEP LAM GI
- **KHONG** duoc dung so o day de tune `GATE_DYN_SCALE`, nguong BIG_DOWN, `NUMBER_ENTRY_EACH_SIGNAL`,
  hay ti trong DCA — do se la fit truc tiep len chinh cua so DEV da nhin.
- Neu muon biet THAT SU "T170 con thang khong khi khong co BIG_DOWN", phai **chay sim voi BIG_DOWN tat**
  (vd `WFO_DISABLE_DCA` / co rieng), co **pre-reg RIENG** — phan ra tren giay **khong thay the duoc**.
- KHONG deploy, KHONG 242, KHONG `git push`, holdout 2026 nguyen ven.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
