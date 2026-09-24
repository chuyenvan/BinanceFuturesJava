# PREREG_DCA_SIGNAL_GATE_V2 — DCA leg-2 theo TIN HIEU o vung lo SAU (-30/-40/-50%) + cooldown dai

Pre-reg MOI, viet va COMMIT TRUOC khi sua mot dong code nao. KHONG phai tune lai 3 config cua V1:
day la thiet ke khac (nguong khac + mot tham so duoc dua vao dien sweep), do user quyet dinh SAU KHI
doc RESULT V1 nhung TRUOC KHI chay bat cu thu gi cua V2 => hop le, khong phai hau kiem.

KHONG cham 242, KHONG `git push`, holdout 2026 NGUYEN VEN (`SIM_END_DATE=20251231`).

## 0. Vi sao co V2 (trich dan quyet dinh cua user)
V1 (`docs/prereg/PREREG_DCA_SIGNAL_GATE.md` / `docs/result/RESULT_DCA_SIGNAL_GATE.md`, commit 7266bc2 / bd45a50 / fbc9f4f)
da chay X in {-5,-8,-12}% => NULL ca ba. User: **"loss 5 8 12 la qua nho"**, va them y: phai
**"bat sat cai loss hien tai ay ko phai bat all"** — tuc khong ban ngay khi vua cham nguong o mot tick
thoang qua, ma phai qua mot khoang thoi gian toi thieu.

## 1. THAY DOI so voi V1 (chi hai thu)
1. **Nguong lo X**: {-5%, -8%, -12%} -> **{-30%, -40%, -50%}**.
2. **Cooldown toi thieu ke tu luc leg-1 KHOP** tang dan theo do sau nguong. Ghep cap:

| tag | X (`SIM_DCA_SIGNAL_LOSS`) | cooldown (`SIM_DCA_SIGNAL_COOLDOWN_MIN`) |
|---|---|---|
| `DS_DCA30` | -0.30 | 24h = **1440** phut |
| `DS_DCA40` | -0.40 | 36h = **2160** phut |
| `DS_DCA50` | -0.50 | 48h = **2880** phut |

> **GHI RO XUAT XU**: user chi dua VI DU 24h va 48h. Viec ghep cap 30%<->24h, 40%<->36h, 50%<->48h
> (noi suy tuyen tinh cho moc giua) la **gia dinh cua master**, chot TRUOC khi chay, KHONG phai fit sau
> khi thay ket qua. Ba cap nay co dinh; khong doi sau khi doc so.

Moi thu khac GIU NGUYEN V1: base leg = 50% suat von (`SIM_DCA_SIGNAL_BASE_RATIO=0.5`), tran 1 leg-signal
moi cum, do lo tren `firstEntryPrice` (bat bien qua DCA), dieu kien (c) = symbol phai DOC LAP lot top-K
cua tick VA pass `AIRejectFilter.entryGate` (scale 1.70) y het mot lenh moi.

## 2. DINH NGHIA CHINH XAC cua COOLDOWN (chot o day, khong dien giai lai)
Cooldown do tu **thoi diem leg-1 cua cum khop** (`cluster.clusterFirstLegTime`), **KHONG** do tu luc gia
cham nguong X. Dieu kien ban:

```
time - cluster.clusterFirstLegTime >= DCA_SIGNAL_COOLDOWN_MIN * 60_000
AND  ticker.priceClose / cluster.firstEntryPrice - 1 <= DCA_SIGNAL_LOSS
```

Hai ve phai dung **cung mot tick**. Hieu qua thuc te giong y cai user muon ("khong bat cai loss thoang qua"):
mot cu sap nhanh roi bat lai trong vong 24-48h dau doi lenh se KHONG ban duoc leg-2; chi nhung cum da
song du lau MA van con lo sau tai tick do moi duoc.

**Xac nhan ky thuat (doc code truoc khi viet)**: `Configs.DCA_SIGNAL_COOLDOWN_MIN` (int, PHUT) va phep do
tu `clusterFirstLegTime` DA TON TAI tu V1 (commit bd45a50, ham `dcaSignalEligible`). V2 **khong can them
field cau hinh moi cho cooldown** — chi dat gia tri trong profile. Ghi ro de khong ai tuong da doi co che.

## 3. VA CHAM VOI GRID DCA CU — quy tac tie-break BAT BUOC
`DcaUtils.shouldDcaGrid` + `DCA_GRID_LEVELS` mac dinh `-0.50,-0.75,-0.90`: **rung dau cua grid catastrophic
la -50%, TRUNG CHINH XAC nguong cua config DCA50**. DCA40 cung co the cham (gia tiep tuc roi tu -40% xuong
-50% trong luc cum van dang mo).

**Luat chot:**
- Moi symbol, moi tick, chi duoc them **TOI DA MOT** leg: signal-gate **HOAC** grid, khong bao gio ca hai.
- Neu ca hai dieu kien dung cung tick => **signal-gate duoc uu tien**, grid bi BO QUA tick do.
- Grid **khong bi mat** — no van con nguyen cho cac rung sau: neu gia tiep tuc giam (hoac don gian la tick
  ke tiep van duoi -50%) thi grid ban binh thuong o tick sau.

**Van de thu tu code (doc code xong moi biet, ghi lai o day):** trong vong tick cua
`SimulatorMarketLevelTicker1MStopLoss`, hai lan goi `DcaProcessor.getDCA(...)` (dong ~280 va ~309) chay
**TRUOC** vong `chosenCands` (dong ~323) noi leg-signal duoc ban. Tuc mac dinh GRID di truoc — nguoc voi
luat tren. Cach sua (toi thieu, khong dao thu tu vong tick):
- Dau moi tick, khi `DCA_SIGNAL_GATE=true`, tinh truoc tap **`dsReserved`** = cac symbol (i) nam trong
  top-K cua tick nay va (ii) thoa dieu kien cau truc (a)(b)(d) cua signal-gate.
- Hai danh sach ung vien grid bi **loc bo** cac symbol trong `dsReserved` => grid khong ban o tick do.
- Sau do vong `chosenCands` chay nhu thuong; neu cong AI tu choi thi symbol do khong duoc leg nao trong
  tick nay, **grid tu ban lai o tick ke tiep** (gia van duoi nguong). Day la dien giai bao thu nhat cua
  "signal uu tien + toi da 1 leg/tick" va la thay doi nho nhat.
- Truong hop "leg market-signal (Best-N / BIG_DOWN) cung tick" KHONG the va cham: nhung leg do chi mo tren
  symbol CHUA chay (`symbolLocked`), ma signal-gate lai doi symbol DANG chay va da qua cooldown >= 24h.

**Ha tang da co tu V1, khong kien truc lai**: field `OrderTargetInfoTest.dcaSignalLeg` + `gridLegCount()`
(leg-signal khong an mat mot rung cua ladder 1,1,3,8) VAN DUNG NGUYEN. Da verify: no du de thuc thi luat
uu tien nay, chi can them tap `dsReserved` + loc hai danh sach grid.

## 4. CANH BAO TRUOC KHI CHAY — hieu suat von nhieu kha nang XAU HON V1
Ghi o day TRUOC khi thay so, de RESULT khong bi doc thanh "biet truoc roi moi noi".

V1 da do: chi **9.7-17%** so cum ban duoc leg-2 => **83-90% vi the song ca doi voi 50% von**. Do la
nguyen nhan chinh lam CAGR mat 6.5-7.4pp (mMargin 1851 -> 916-941).

V2 lam ca hai dieu kien **CHAT HON**: nguong sau hon (-30/-40/-50 thay vi -5/-8/-12) VA cooldown dai hon
(24-48h thay vi 1h). Rat it cum song du lau va lo du sau toi muc do — phan lon bi `LOSER_TIME_STOP_HOURS`
(168h), trailing-hinge hoac hard-SL dong truoc. => **so lan thoa dieu kien gan chac chan THAP HON V1**,
tuc "von dong bang" co the TE HON, khong phai tot hon.

Day **KHONG** phai ly do de tu doi thiet ke. Chay DUNG nhu user yeu cau. Nhung bat buoc phai **DO va BAO
CAO tach bach** (muc 7) de phan biet hai nguyen nhan khac han nhau:
- (A) **hiem khi lo sau toi vay** (nguong qua sau), vs
- (B) **cooldown loc mat co hoi** (cham nguong nhung chua qua cooldown, roi dong lenh truoc khi qua).
Khong duoc gop hai cai thanh mot con so.

## 5. BA CONFIG (khoa cung, chay tuan tu, KHONG doi sau khi thay ket qua)
Profile goc = `profiles/x1_gs_t170.properties` (incumbent T170), chi THEM 4 key.

| tag | profile | `SIM_DCA_SIGNAL_LOSS` | `SIM_DCA_SIGNAL_COOLDOWN_MIN` |
|---|---|---|---|
| `DS_DCA30` | `profiles/ds_dca30.properties` | -0.30 | 1440 |
| `DS_DCA40` | `profiles/ds_dca40.properties` | -0.40 | 2160 |
| `DS_DCA50` | `profiles/ds_dca50.properties` | -0.50 | 2880 |

Hai key con lai giong nhau ca ba: `SIM_DCA_SIGNAL_GATE=true`, `SIM_DCA_SIGNAL_BASE_RATIO=0.5`.
KHONG co config nao khac. KHONG them bien the sau khi thay so.

## 6. Dataset + harness + cham diem (Y HET V1 va cac bai truoc — khong doi mot chu)
- Dataset `/home/ubuntu/wfo_ds_x1_2021`, config `configs/sim_dev_file_2021.properties`,
  `SIM_END_DATE=20251231`, harness `/home/ubuntu/k_runarm.sh <TAG> <PROFILE>`.
- Baseline = **T170** (`RG_A_T170`): md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089, equity 111,070,
  CAGR 29.27, maxDD -11.84, UW 92, win% 88.25, TSloss% 9.73, meanP 5.244.
- **CONG PARITY BAT BUOC**: chay `DS_PARITY_T170_V2` voi profile T170 GOC (flag OFF) tren build MOI;
  phai ra **dung** md5 `efb793e2...` (n=1089). FAIL => dung, sua code, KHONG duoc bao cao ket qua ON.
- Build `mvn -o package` + **toan bo test suite** (134 test hien co + test moi cho cooldown/tie-break)
  phai PASS het. Khong xoa/sua test cu de ne fail.
- Cham diem: `research/analysis/x1_rates.py` (may bootstrap cua `c3_rates.py`): khoi 72h, block-paired,
  NREP=2000, SEED=20260905, CI x1.21 (muc noi rong da bao k=3 multiplicity, theo PREREG_2X_HALFSIZE muc 5).
  Lenh: `python3 x1_rates.py <DS_X> RG_A_T170` => in hieu (T170 - config).
- **Rang buoc cung theo tung nam**: maxDD <= 15%, UW <= 120 ngay, return nam >= 0, return quy >= -5%.
- **THANG** = (>= 2 rate CHAT LUONG trong {win%, TSloss%, meanP} ngoai CI theo huong TOT CHO CONFIG)
  **VA** (rang buoc cung PASS tat ca cac nam). Moi truong hop khac => **NULL**. Khong dien giai mem.

## 7. BAO CAO BAT BUOC trong RESULT_DCA_SIGNAL_GATE_V2.md
Ngoai bang chuan + CI + hard-constraint theo nam, va ba cau hoi cua V1 (so lenh; ti le lo RAW muc LEG;
ti le lo HIEU DUNG muc VI THE), PHAI them **phieu loc 3 tang**, tach rieng tung config:

| tang | dinh nghia | tra loi cau hoi |
|---|---|---|
| T1 | % cum **tung cham nguong X** bat ky luc nao trong doi (BO QUA cooldown, bo qua top-K, bo qua gate) | nguong co qua sau khong? |
| T2 | % cum tung cham X **tai mot tick da qua cooldown** | cooldown loc mat bao nhieu? |
| T3 | % cum **thuc su ban duoc leg-2** (them dieu kien top-K + EntryGate + budget) | tin hieu/von loc mat bao nhieu? |

T1 va T2 do bang log rieng trong sim (chi bat khi `DCA_SIGNAL_GATE=true` => parity khong doi), T3 doc tu
`printDone.csv` (leg>0 va level=PREDICT_SYMBOL_TRADE). Phai in ca ba, **khong duoc gop**.

Them: **so lan tie-break thuc su xay ra** (symbol bi giu lai khoi grid trong cung tick vi signal-gate uu
tien). Neu = 0 thi noi ro la 0 (luat van dung, chi la khong kich hoat trong du lieu nay).

## 8. CAM KET
- Tham so muc 1 + 5 DA KHOA truoc khi sua code. Khong tune sau ket qua. Khong them config.
- Cong parity OFF byte-identical PASS TRUOC khi chay bat ky config ON nao.
- KHONG deploy 242. KHONG `git push`. Chi commit LOCAL tren branch `module`.
- Holdout 2026 KHONG mo. Neu khong tim thay diem sua nhu mo ta => dung va bao cao, khong tu che duong vong.
