# AUDIT_GATEDYN_GD92 — ro soat doc lap claim "GD92 THANG" (OpenClaw, 09/09/2026)

Nguoi ro soat: agent AUDIT+REPLICATE, 11/09/2026. Doi tuong: 3 commit `272d8f1` / `1c1ecca` /
`41d5d76` tren branch `module`, doc `docs/RESULT_GATEDYN.md` + `docs/RESULT_GATEDYN2.md`.
Pham vi: doc lai toan bo bang chung, chay LAI GD92 tu dau tren dataset build lai, va cham lai
bang chinh khung pre-reg cua du an (`docs/PREREG_CI.md`, `docs/PREREG_X1.md`, `docs/PREREG_B4.md`).

---

## 1. PHAN QUYET

**KHONG PHAN BIET DUOC (nhieu)** o tang hieu qua, **cong them VI PHAM PHUONG PHAP** rieng cho dot
GATEDYN2. Cu the: cac run cua OpenClaw **tai lap byte-identical** (khong co bia so, khong co loi
scope, khong cham holdout) va muc tieu PRIMARY ma user dat ra — phan bo lenh deu hon giua cac quy —
**that su dat** (CV quy 0.712 -> 0.518). Nhung tu "THANG" trong commit `272d8f1` ham y GD92 **tot
hon** gate cung, va bang chung cho ve "tot hon" khong dung vung: (a) chenh lech hieu qua
`d = CAGR(GD92) - CAGR(PARITY_R) = +4.98pp` co `CI95 [-4.47, +16.09]` **chua so 0**, va cach
nguong hieu chinh boi k=9 bien the (`2.0963*sd_boot = 10.90pp`) hon **2.2 lan** — dung y nhu
`PREREG_B4` muc 0.1 da du bao truoc cho moi thay doi kieu "num gate"; (b) bang chung quyet dinh
duy nhat tach GD92 khoi cac bien the khac la **UW (underwater days)**, ma `PREREG_CI` muc 2.5 ghi
ro **KHONG duoc bootstrap** va chi la "so quan sat duoc mot lan" — GD92 dat 116 so voi nguong 120,
du **4 ngay**, trong khi hai lang gieng gan nhat cung pct lai la 153 va 183; (c) dot GATEDYN2 mo 6
bien the **quanh diem thang** bang cach doi phan vi va noi cua so, dung thu tu ma
`docs/B4_RESULT.md` dong 179-180 cam ten: *"KHONG mo them bien the tren cung khong gian (noi cua
so, doi phan vi, doi tan so cap nhat...). Them bien the = chon tren nhieu = leak L2."* Ket qua
"6/6 FAIL" cua dot do **khong** xac nhan GD92 on dinh nhu doc ket luan — no la dau hieu nguoc lai:
be mat tham so **gap ghenh** o dung thang do cua luoi, tuc diem uoc luong khong dang tin.

De khong bi doc qua tay: bai nay **khong** chung minh GD92 xau hon gate cung. No chung minh du
lieu DEV 48 thang **khong du suc phan biet** hai cau hinh o tang hieu qua, nen chot GD92 vao
production se la quyet dinh dua tren do deu (co that) cong voi mot phan thuong hieu qua **chua
duoc chung minh**.

---

## 2. AUDIT A1-A6

### A1. Pre-reg co truoc run dau tien khong? — CO, ca hai dot

| moc | thoi diem | bang chung |
|---|---|---|
| commit `3cdccd0` PREREG_GATEDYN | 2026-09-09 10:06:16 | `git log --format='%h %ci %s'` |
| sim PARITY_R bat dau | 2026-09-09 10:07:55 | dong 2 `X1_C3_FULL_PARITY_R/logs/sim.out` |
| GD88 xong / GD92 chay 10:37:08 / GD96 xong | 10:34:41 / 10:50:14 / 11:03:43 | mtime `printDone.csv` |
| commit `272d8f1` RESULT_GATEDYN | 2026-09-09 11:16:37 | git log |
| commit `1c1ecca` PREREG_GATEDYN2 | 2026-09-09 12:22:14 | git log |
| 6 run grid | 12:37:03 .. 14:41:23 | mtime `printDone.csv` |
| commit `41d5d76` RESULT_GATEDYN2 | 2026-09-09 15:16:35 | git log |

Co PREREG cho **ca dot 1** (`PREREG_GATEDYN.md`, khong chi co PREREG_GATEDYN2). Thu tu
pre-reg -> run -> result **dung** o ca hai dot, khoang cach dot 1 la 1 phut 39 giay truoc khi JVM
dau tien khoi dong. **Khong co vi pham thu tu commit.** Day la diem manh cua bai, ghi nhan.

### A2. Baseline va GF27

- `X1_C3_FULL_PARITY_R` md5 `printDone.csv` = `2478e90d4e61…` (ca header) va
  `e13bc39e625b8d2ceebb7b9194f7f4f0` (bo header) — **trung tuyet doi** voi ca
  `X1_C3_FULL` (run canonical 05/09) lan `X1_C3_FULL_PARITY` (07/09). n = 2,266, equity 111,428,
  dung con so canonical trong `docs/RESULT_5MGRID.md` / `K12_RESULT.md`. **Baseline hop le, khong
  co troi nen.**
- `GF27` **khong** phai bien the gate rolling. Profile cua no la chinh `x1_c3_full.properties`
  (`PROFILE_HASH=135750e04d67c263`, giong het PARITY_R); khac biet nam o **dataset**:
  `wfo_ds_x1_gf27` voi `pred=2499840` so voi `wfo_ds_x1_gd` `pred=2500260` — tuc mot **model gate
  27-feature** khac duoc export vao tap pred. Day la nhanh GATEFEAT (`55acc46`), da **NULL** o tang
  sim. Khong anh huong ket luan GD92, nhung can noi ro: GF27 **khong** phai doi chung cua GATEDYN.

### A3. Tieu chi quyet dinh — chot truoc, nhung trong so dat sai cho

Nhung gi **dung**:
- `PREREG_GATEDYN` muc 4 chot PRIMARY (CV quy giam >= 20% + min-quy khong tut qua 20%), rang buoc
  rate theo khung K12/GATEFEAT, rang buoc cung maxDD/nam-am/quy. Tat ca **truoc** khi chay.
- `UW <= 120` **khong** phai tieu chi bia them sau khi thay so: hang `HARD_DD, HARD_UW, HARD_Q =
  15.0, 120, -5.0` da co trong `research/analysis/x1_rates.py` tu commit `e710f72`
  (2026-09-05 20:53), tuc **truoc GATEDYN 4 ngay**, va `docs/PREREG_X1.md` dong 176 ghi
  `underwater <= 120 ngay`. Nghi van "post-hoc dat nguong 120 vi GD92 duoc 116" da duoc kiem va
  **bac bo**.

Nhung gi **khong dung**:
- Muc 4 cua `PREREG_GATEDYN` liet ke rang buoc cung la maxDD / nam am / quy, **khong ten UW**. The
  nhung trong `RESULT_GATEDYN` muc 4, UW lai la **tieu chi duy nhat** loai baseline (PARITY_R
  "FAIL (UW>120)") va loai GD96. Metric quyet dinh cuoi cung khong phai metric duoc nhan manh
  trong pre-reg cua chinh dot do.
- **UW va maxDD la so quan sat mot lan, khong co CI** (`PREREG_CI` muc 2.5 noi thang: *"Moi phat
  bieu ve maxDD ... la so quan sat duoc mot lan, khong co CI. Ghi ro nhu vay, khong bien no thanh
  CI gia. Tuong tu: underwater-days"*). OpenClaw **da dung dung no lam bang chung quyet dinh
  chinh**. Do la cho vuot bang chung nang nhat cua bai.
- "0 rate xau ngoai CI" la **khong bac bo**, khong phai **bang chung khong co hai**. Do rong CI
  cua `win%` la `[-2.07, +0.87]` (~3pp): mot suy giam that 1.5pp se **khong** bi phat hien. Dung
  no de ket luan "khong hy sinh chat luong" la doc nguoc chieu cong suat kiem dinh.
- Rate "TOT" duy nhat duoc neu — `mP|SL +2.544 CI [+0.051, +5.363]` — co can duoi **0.051**, tuc
  sat 0. Voi 5 rate x 5 cua so x 9 bien the = ~225 lan kiem CI **khong hieu chinh boi**, mot ket
  qua sat bien nhu vay la ung vien hang dau cua duong tinh gia.

### A4. Da so sanh va cau hoi "khong gian moi hay lach lenh dong B4"

**Khong co hieu chinh boi nao duoc ap dung** trong ca hai doc ket qua. `PREREG_B4` muc 3 (cung du
an, cung co che) da tung dung `sqrt(2 ln 3) = 1.4823` cho 3 bien the — nen khung nay san co va
**da bi bo qua** khi so 9 bien the.

Lap luan **ung ho** OpenClaw: (i) nen khac that — C3_FULL 48 thang, engine da sua B1/B2/B3, so
voi C2b 30 thang engine con bug; (ii) muc tieu PRIMARY khac that — do deu phan bo lenh theo quy,
khong phai equity, va la **yeu cau truc tiep cua user** ngay 09/09 10:02; (iii) co pre-reg rieng,
quota dong, va `RESULT_GATEDYN` muc 6.2 con tu ghi "pre-reg moi, KHONG tune tren pre-reg nay".
Theo cach doc nay, dot 1 la mot bai hop le, khong phai lach lenh.

Lap luan **phan bac**: (i) dieu khoan dong cua B4 khoa **khong gian tham so**, khong khoa tap du
lieu — `B4_RESULT` 179 ke ten dung ba thao tac "noi cua so, doi phan vi, doi tan so cap nhat", va
GATEDYN2 lam dung hai thao tac dau; doi nen chi tao **mau moi**, khong tao khong gian moi;
(ii) canh bao cong suat cua `PREREG_B4` muc 0.1 (`sd` thay doi kieu gate = 6.34pp, can ~87 nam de
phat hien cai thien 3pp) **van con hieu luc** tren C3_FULL — do lai o day cho `sd_boot = 5.20pp`
tren 4 nam, cung bac do lon; (iii) dot 2 lay tam luoi **tu ket qua dot 1**, nen du co pre-reg
rieng no van la chon-tren-nhieu: pre-reg khong tay trang duoc mot thiet ke da bi ket qua truoc do
dieu huong.

**Ket luan A4:** dot 1 (GATEDYN) **chap nhan duoc** ve thu tuc — nen moi + muc tieu moi + quota
dong, khong phai lach lenh. Dot 2 (GATEDYN2) **vi pham** `B4_RESULT` 179-180: no la grid quanh
winner tren dung khong gian da bi dong, va nam ngoai bat ky bien minh "muc tieu moi" nao.

Them mot diem quan trong hon ca vi pham thu tuc: **ket qua dot 2 bi doc nguoc**. `RESULT_GATEDYN2`
muc 3 ket luan "grid xac nhan vung on dinh" va goi 0.92/90 la "diem ngot". Nhung so lieu cua chinh
doc do cho thay, giu nguyen pct=0.92 va chi doi cua so: UW = 183 (W=60) -> **116** (W=90) -> 153
(W=120); con doi pct o W co dinh thi UW nhay 221 / 116 / 185. Mot toi uu **that** phai co lang
gieng gan bang no. Tai day, diem duy nhat qua cua la diem duy nhat **lot khe**: 6/6 lang gieng
FAIL. Do la chu ky cua mot **dinh nhieu**, khong phai mot vung on dinh. Ba metric con dat dinh o
**ba diem khac nhau** — CV thap nhat o G90W60 (0.469), equity cao nhat o G92W60 (130,175), UW thap
nhat o GD92 (116) — them mot dau hieu be mat do la nhieu.

### A5. Scope, bins, code — SACH

| kiem tra | ket qua |
|---|---|
| `SIM_END_DATE` | `20251231` o ca PARITY_R, GD88/92/96, grid — log: `SIM_END_DATE override: chay toi 20251231` |
| cham holdout 2026 | **KHONG**. Nam dong lenh trong `printDone.csv` chi co `[2022 2023 2024 2025]` |
| bins | `/home/ubuntu/predwf_map_s1a2_x1`, 16 fold, `binsSha256=b87762312620f31769a8ef0160ec8132a5482c8f235d86e3364b59cce022a862`, md5 fold `20251001` = `5ebae9298eb67bb4f12784b091148af7`. **Khong rebuild.** |
| `GateRollingThreshold.java` | `git diff 4d3fe62 HEAD` tren file nay = **rong**. Khong sua mot chu. |
| code Java khac | `AIRejectFilter.java` co `+13` dong: ham `dynThreshold()` moi, **READ-ONLY** (dung cho TICKLOG, khong goi trong duong quyet dinh). Khong anh huong. |
| `nBeforeFirst` | **0** — khong co WARN "truy van truoc moc dau tien". Moc gio dau `1624989600000` = 2021-06-30, **truoc** 2022-01-01, nen vung khoi dong khong roi vao DEV (giong `B4_RESULT` dong 48-50). |
| khac biet duy nhat vs baseline | 2 key profile: `SIM_GATE_ROLLING_PCT=0.92`, `SIM_GATE_ROLLING_DAYS=90` (`diff x1_c3_full.properties x1_gd92.properties` chi ra dung 2 dong them) |

### A6. Cham lai bang `x1_rates.py` — TAI LAP 100%

Chay lai `python3 research/analysis/x1_rates.py X1_C3_FULL_PARITY_R X1_C3_FULL_GD92`. **Moi con so
trong `RESULT_GATEDYN` muc 1, 3, 4 deu tai lap dung den chu so cuoi.** Khong co so nao khong tai
lap duoc.

| metric | PARITY_R | GD92 | doc cua OpenClaw |
|---|---|---|---|
| n | 2,266 | 2,355 | khop |
| win% | 84.69 | 84.12 | khop |
| TSloss% | 14.96 | 15.67 | khop |
| mP\|SM | 7.333 | 7.324 | khop |
| mP\|SL | -19.570 | -17.026 | khop |
| meanP | 3.308 | 3.509 | khop |
| maxDD% | -12.46 | -13.21 | khop |
| UW | 227 | 116 | khop |
| equity | 111,428 | 128,979 | khop |
| CV quy | 0.712 | 0.518 | khop (`gd_evenness.py`) |

CI toan cua so: `mP|SL +2.544 [+0.051, +5.363]` YES (TOT), 0 rate XAU — **khop**. Theo nam: 2022
0 xau, 2023 0 xau, 2024 0 xau, 2025 0 xau + 2 tot (`TSloss% -3.220`, `meanP +1.455`) — **khop**.

Mot chi tiet doc chua noi ro, dang luu y: bang rang buoc cung **theo nam** cho thay PARITY_R FAIL
o **2024 voi UW = 121** — hon nguong dung **1 ngay**. Ket luan "gate cung FAIL" do vay treo tren
mot ngay lich o 2024 cong voi 2025 (227).

---

## 3. REPLICATE B7-B9

### B7. Dieu kien truoc khi chay
`pgrep java` = rong; disk free 32G (>= 12G). Dataset `wfo_ds_x1` **da bi xoa** (OpenClaw don theo
dung pre-reg muc 5) nen phai build lai: `ExportWfoDataset` voi
`TRADING_PROFILE=profiles/x1_c3.properties`, `WFO_SET_PRED=ai_pred_market_gate_wfo`,
`WFO_SEL_HORIZON_IDX=0` -> `/home/ubuntu/wfo_ds_x1` (4.0G, `foldCount=16`,
`leakFreeFrom=2022-01-01`). Jar `target/binance-java-sdk-1.2.4.jar` **khong** build lai (mtime
07/09, cu hon cac run 09/09 => cung jar OpenClaw dung).

### B8. Chay lai GD92 — BYTE-IDENTICAL

Dir moi `X1_C3_FULL_GD92_R` (khong ghi de dir cua OpenClaw), cung env `runx` trong
`research/pipeline/x1/run_x1_sim.sh`.

| | OpenClaw `X1_C3_FULL_GD92` | Audit `X1_C3_FULL_GD92_R` |
|---|---|---|
| md5 `printDone.csv` (ca header) | `eb607396fadb…` | `eb607396fadb…` |
| md5 bo header | `c18314d661c9aa6135761ad68dc16cec` | `c18314d661c9aa6135761ad68dc16cec` |
| n | 2,355 | 2,355 |
| bang `[GATE-ROLL]` | `39510 moc gio, moc dau 1624989600000, min=0.00456 max=0.01265` | **giong het** |

**Tai lap duoc tuyet doi**, ke ca tren dataset build lai tu dau o ngay khac. Khong co nondeterminism,
khong co lech bins. Day la diem cong ro rang cho cong viec cua OpenClaw va can duoc ghi nhan tach
bach voi phan phe binh phuong phap.

### B9. Paired block-bootstrap tren equity NGAY (b+unP)

Cong cu moi: `research/analysis/ci_gatedyn.py` (khuon `ci_b4.py`; `logging`, khong `print`).
Block 21 ngay (kiem them 10 va 42), 2000 rep, seed 20260903, 1460 ngay = 4.0000 nam.
Hieu chinh boi **k = 9** bien the rolling gate da chay (GD88/92/96 + 6 run grid):
`sqrt(2 ln 9) = 2.0963`.

**Toan cua so 48 thang** — `d = CAGR(GD92) - CAGR(PARITY_R)`:

| d (pp) | sd_boot | CI95 (block 21) | P(d>0) | nguong 2.0963*sd | phan quyet |
|---|---|---|---|---|---|
| **+4.975** | 5.201 | **[-4.469, +16.087]** | 0.837 | 10.902 | **KHONG DAT** |

CI **chua so 0** => theo `PREREG_CI` muc 4 phan loai la **KHONG PHAN BIET DUOC**, truoc ca khi noi
den hieu chinh boi. Voi hieu chinh boi, d con thieu hon mot nua nguong.

Do ben theo do dai block (ket luan khong phu thuoc L):

| L | CI95 | sd |
|---|---|---|
| 10 | [-4.029, +14.844] | 4.878 |
| **21** | **[-4.469, +16.087]** | **5.201** |
| 42 | [-3.765, +16.388] | 5.085 |

**Theo tung nam** (bootstrap trong nam, block 21):

| nam | d (pp) | sd_boot | CI95 | P(d>0) | nguong | phan quyet |
|---|---|---|---|---|---|---|
| 2022 | **-10.060** | 5.265 | [-20.971, -1.100] | 0.015 | 11.037 | KHONG DAT |
| 2023 | +13.690 | 13.265 | [-6.599, +43.500] | 0.888 | 27.806 | KHONG DAT |
| 2024 | -0.973 | 6.444 | [-12.015, +13.149] | 0.453 | 13.508 | KHONG DAT |
| 2025 | +20.382 | 13.402 | [-2.271, +50.554] | 0.954 | 28.094 | KHONG DAT |

Doc bang nay: dau cua `d` **doi chieu** giua cac nam (2022 am, 2023 duong, 2024 ~0, 2025 duong),
va nam duy nhat co CI khong chua 0 la **2022, ve phia XAU** (-10.06pp, GD92 kem hon gate cung).
`sd_boot` theo nam len toi 13.4pp. Day la chan dung cua mot hieu ung **khong on dinh theo che do
thi truong**, khong phai mot cai thien ben vung.

**Rang buoc cung theo nam** (so quan sat, khong bootstrap — `x1_rates.py`):

| tag | nam | maxDD% | UW | ret_nam% | quy_min% | PASS |
|---|---|---|---|---|---|---|
| PARITY_R | 2022 | -12.46 | 64 | +17.30 | +0.63 | PASS |
| PARITY_R | 2023 | -2.51 | 45 | +60.43 | +7.80 | PASS |
| PARITY_R | 2024 | -11.36 | **121** | +45.36 | -4.64 | **FAIL** (UW hon nguong 1 ngay) |
| PARITY_R | 2025 | -10.60 | **227** | +16.45 | -2.47 | **FAIL** |
| GD92_R | 2022 | **-13.21** | 69 | **+7.24** | **-3.81** | PASS |
| GD92_R | 2023 | -5.24 | 63 | +74.12 | +13.33 | PASS |
| GD92_R | 2024 | -11.36 | 114 | +43.91 | -4.58 | PASS |
| GD92_R | 2025 | -6.11 | 116 | +36.76 | +1.72 | PASS |

So **tuong doi** so voi control (phan doc cha thieu trong doc cua OpenClaw): GD92 **xau hon**
PARITY_R o 2022 tren ca ba truc — maxDD -13.21 vs -12.46, ret nam +7.24 vs +17.30, quy min -3.81
vs +0.63; **tot hon** ro o 2025 (UW 116 vs 227, maxDD -6.11 vs -10.60). Tuc GD92 khong "tot hon o
moi noi", no **doi rui ro tu 2025 sang 2022**.

---

## 4. RUI RO NEU ADOPT GD92 VAO PRODUCTION

1. **Phan thuong hieu qua chua duoc chung minh.** `+4.98pp` CAGR voi `CI95 [-4.47, +16.09]`: gia
   tri that hoan toan co the la am. Chot GD92 vi tuong se duoc them ~5pp/nam la ky vong khong co
   co so thong ke.
2. **Bang chung quyet dinh la mot so khong co CI, o sat bien.** UW 116 so voi nguong 120 (du 4
   ngay), trong khi cung mot co che voi W=60/W=120 cho 183/153. Neu sai so lay mau day UW len qua
   120, GD92 mat toan bo ly do duoc chon. Khong co gi trong du lieu hien co dam bao dieu do khong
   xay ra tren du lieu moi.
3. **Rui ro doi che do (2022).** GD92 kem hon gate cung 10.06pp CAGR o 2022 — nam gau, va la nam
   duy nhat co CI khong chua 0. Mot che do gau moi la kich ban GD92 **da the hien la xau hon** tren
   du lieu da co.
4. **Doi baseline C3_FULL keo theo cong hoi quy.** GD92 lam thay doi n (2,266 -> 2,355) va toan bo
   duong equity; moi ket luan truoc day neo vao `X1_C3_FULL_PARITY` (md5 `2478e90d…`) se phai chay
   lai de doi chieu. Chi phi nay chi dang tra neu hieu ung la that.
5. **Chua he kiem tren VALIDATION/HOLDOUT.** Toan bo bang chung nam tren DEV 2022-2025. Holdout
   2026 con nguyen seal. Mot cau hinh chon bang cach quet 9 bien the tren DEV la ung vien dien
   hinh cua winner's curse khi ra du lieu moi.
6. **Rui ro thuc thi live.** Nguong truot doi moi gio; `GateRollingThreshold` chay tot trong sim
   offline nhung duong live phai co cung cua so `[t-W, t)` va cung nguon `predReturn15M`. Chua co
   bai nao kiem parity live cho co che nay.

**Khuyen nghi:** khong chot GD92 vao production dua tren bang chung hien tai. Neu van muon giu
huong "gate dong theo phan vi" (muc tieu do deu la that va la yeu cau cua user), thi tach bach hai
viec: (a) cong nhan do deu la dat duoc, (b) **khong** tuyen bo cai thien hieu qua. Muon nang (b)
len thanh ket luan thi can du lieu ngoai mau — VALIDATION hoac holdout — voi pre-reg rieng, mot
cau hinh duy nhat da chot (0.92/90), khong quet them.

---

## 5. NHUNG GI BAI NAY **KHONG** LAM / KHONG KET LUAN

- **Khong** chay lai GD88, GD96 va 6 run grid. Ket luan ve chung dua tren doc `printDone.csv` va
  doc cua OpenClaw, khong phai replicate doc lap.
- **Khong** ket luan GD92 **xau hon** gate cung toan cuc. Bai nay ket luan **khong phan biet duoc**
  o tang hieu qua; rieng 2022 co dau hieu xau hon nhung cung chua qua nguong hieu chinh boi.
- **Khong** phu nhan PRIMARY: CV quy 0.712 -> 0.518 la that, tai lap duoc, va la dieu user yeu cau.
  Bai nay chi khong dong y voi buoc nhay tu "dat do deu" sang "THANG".
- **Khong** danh gia chat luong gate o tang IC/OOS, khong dung `gd_quarterly.py` (file nay dang
  untracked tren Oracle, khong phai artifact da commit).
- **Khong** cham VALIDATION, **khong** mo holdout 2026, khong cham 242, khong cham
  `SHADOW_NO_PUSH`, khong sua `/home/ubuntu/predwf_map_s1a2_x1`, khong sua code Java, khong
  `git push`, khong xoa dir devrun cua OpenClaw.
- **Khong** kiem tra duong live cua `GateRollingThreshold` (chua co harness).
- Luu y ky thuat: `ci_gatedyn.py` cho CAGR 33.58/38.55 so voi `x1_rates.py` 33.63/38.61 — lech
  ~0.06pp do khac quy uoc dem ngay cuoi chuoi equity. Khong anh huong ket luan (`d` = 4.975 o ca
  hai cach).

---

## 6. LENH TAI LAP

```bash
# 0. Tren Oracle, repo /home/ubuntu/src/BinanceFuturesJava, branch module
pgrep -a java            # phai rong
df -BG --output=avail /  # >= 12G

# 1. Build lai dataset (4.0G, ~2 phut) — da GIU lai tai /home/ubuntu/wfo_ds_x1
R=/home/ubuntu/src/BinanceFuturesJava; SHA=$(git -C $R rev-parse --short HEAD)
cd /home/ubuntu/java/devrun && cp -f $R/configs/sim_dev_file.properties config.properties
env TRADING_PROFILE=$R/profiles/x1_c3.properties WFO_SET_PRED=ai_pred_market_gate_wfo \
    WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$SHA \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $R/target/binance-java-sdk-1.2.4.jar \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset /home/ubuntu/wfo_ds_x1

# 2. Chay lai GD92 (~13 phut)
D=/home/ubuntu/java/devrun/X1_C3_FULL_GD92_R; mkdir -p $D/storage $D/logs; cd $D
cp -f $R/configs/sim_dev_file.properties config.properties; rm -f storage/*
ln -sfn /home/ubuntu/java/simulator/kaggle_data_hpo kaggle_data_hpo
env WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1 WFO_SMART_CACHE=1 SIM_END_DATE=20251231 \
    EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json \
    TRADING_PROFILE=$R/profiles/x1_gd92.properties \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $R/target/binance-java-sdk-1.2.4.jar \
    com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1

# 3. Cong parity: phai ra c18314d661c9aa6135761ad68dc16cec
tail -n +2 $D/storage/printDone.csv | md5sum

# 4. Cham
cd $R
python3 research/analysis/x1_rates.py    X1_C3_FULL_PARITY_R X1_C3_FULL_GD92_R
python3 research/analysis/gd_evenness.py X1_C3_FULL_PARITY_R X1_C3_FULL_GD92_R
python3 research/analysis/ci_gatedyn.py  X1_C3_FULL_GD92_R            # -> /home/ubuntu/x1log/ci_gatedyn.out
```

Artifact do bai audit nay tao tren Oracle: `research/analysis/ci_gatedyn.py` (commit),
`/home/ubuntu/java/devrun/X1_C3_FULL_GD92_R/` (giu), `/home/ubuntu/wfo_ds_x1` (4.0G, **GIU** —
dataset canonical cua khung X1, khong phai dataset tam), log
`/home/ubuntu/x1log/{aud_build,aud_rates_gd92,aud_rates_gd92R,ci_gatedyn,aud_ci_R}.out`.
Khong xoa, khong sua bat ky dir nao cua OpenClaw.
