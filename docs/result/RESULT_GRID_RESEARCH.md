# RESULT_GRID_RESEARCH — kha thi LUOI GIAO DICH (grid) tren 1m: **NO-GO/NULL**

Ngay: 2026-10-01. Pre-reg: **`docs/prereg/PREREG_GRID_RESEARCH.md`** (**commit `3d97009d`**, chot TRUOC,
sau do **khong sua thiet ke**). Plan/tong hop phuong phap: `docs/plan/RESEARCH_GRID_TRADING.md`.
Script: `research/grid/grid_fetch.py` + `research/grid/grid_backtest.py`. JSON: `docs/result/GRID_RESEARCH.json`.

**Tuan thu:** thuan Python **OFFLINE / 0-sim** · **0 train** · khong chay Java/sim tren Oracle ·
khong cham production/`242`/ONNX/LIVE · khong sua `.java` · **khong push du lieu** (kline tai ve `/tmp/grid_research/`)
· DEV ≤ **2025-12-31** (khong cham 2026 = HOLDOUT) · output tool nho · commit + push.

---

## 0. KET LUAN (mot dong)

> **NO-GO/NULL.** Luoi trung tinh **hai duoc chu ky** (realized **+2,31 %/thang**) nhung **bi ton kho trong
> trend an het** (MTM cuoi **−3,93 %/thang**) ⇒ gross **−1,63 %/thang** (CI72h×1,18 **chua 0**: [−5,57; +3,72]).
> Sau phi: **maker −1,86 %** · **taker −2,20 %**/thang. **Phi KHONG phai diem chet** (chênh maker↔taker chi
> **0,34 pp/thang**, khong lat dau); **diem chet la RUI RO TON KHO trong trend** (2022-05: **−20,1 %/thang**,
> 0/18 run duong; 2024: **+9,8 %**, 36/36 duong). `corr(net, ER) = −0,14` va tercile ER thap **+3,96 %**
> la tin hieu YEU/khong qua CI ⇒ luat **(C1)/(C3) KHONG dat**.

## 1. Do luong (doc lap, tai hien duoc)

| muc | gia tri |
|---|---|
| Du lieu | `data.binance.vision` futures-UM monthly klines **1m**, **6 coin** × **6 thang** DEV = **36 file**, sha256 trong JSON |
| Coin | BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT DOGEUSDT |
| Cua so | 2022-05, 2022-11, 2023-06, 2024-03, 2024-11, 2025-06 |
| Luoi (khoa truoc) | **G1** ±10%/buoc 1,0% · **G2** ±10%/0,5% · **G3** ±30%/1,5% (neutral, bounded, 50% deployed, tran ton kho = N muc) |
| So run | 108 (36 × 3 luoi); moi run ~43k nen 1m; sim 0,17 s/run |
| Phi | maker **0,040 %/vong** · taker do **0,0982 %** · taker+spread 0,112 % · stress 0,150 % |

**Kiem chung mo hinh (bat buoc, lam TRUOC khi doc so):** duong gia tong hop — **UP tuyen tinh +10 % ⇒ +2,75 %**
(dung ky vong ly thuyet `g·(N/2)(N/2+1)/2/N`), **DOWN −10 % ⇒ −7,25 %** (dung), **sin 30 vong ±5 % ⇒ +15,0 %**
(= 30 × 0,5 %). Mo hinh dung, khong con loi "fill ma" (nen dau da sua: floor→ceil, va bo neu muc `cur`).

## 2. KET QUA CHINH — (C1) CO CUA KHONG?

| chi so | gia tri |
|---|---|
| **GROSS mean** | **−1,626 %/thang**, median **+3,061 %**, **63/108** duong |
| CI72h (2000 rep, seed 20260905, ×1,177, ×30) | **[−5,57 %; +3,72 %] → CHUA 0** |
| realized (chu ky hoan tat) | **+2,307 %/thang** (duong o MOI cau hinh) |
| MTM ton kho cuoi | **−3,933 %/thang** |
| turnover | TB **11,7 ×B/thang** (G1 10,3 · G2 19,3 · G3 5,6) |
| maxDD MTM 1m | TB **−18,3 %** |
| ket hang (`q_end ≥ 99 %`) | **26/108** run |

**Sau phi (%/thang):**

| phi | mean | median | duong |
|---|---|---|---|
| maker 0,040 | **−1,860** | +2,741 | 63/108 |
| taker do 0,0982 | **−2,201** | +2,652 | 63/108 |
| taker+spread 0,112 | −2,282 | +2,612 | 63/108 |
| stress 0,150 | −2,505 | +2,417 | 63/108 |

**Theo nam (maker):** 2022 **−15,67 %** (4/36) · 2023 **−1,51 %** (8/18) · 2024 **+9,78 %** (36/36) · 2025 **+2,14 %** (15/18).
⇒ **khong dat "≥ 3/4 nam duong"**.

**(C1) CO CUA: KHONG DAT** — CI chua 0, mean am, 2/4 nam am.

## 3. (C2) PHU THUOC MAKER FEE?

- maker −1,860 vs taker_do −2,201 ⇒ chênh **0,34 pp/thang**, **KHONG lat dau**, < spacing/2 (0,5 pp) cho G1/G3.
- Ly do co hoc: turnover chi **11,7 ×B/thang** ⇒ `phi maker 0,23 %/thang` vs `phi taker 0,58 %/thang`
  — **nho so voi bien do MTM ±10 %**. Voi luoi RONG (G1/G3) **phi khong quyet dinh**.
- ⚠️ Nguoc lai voi truc giac "grid song nho maker": dung la vay **chi khi luoi DAY** (buoc ≲ 0,3 % ⇒ turnover
  ~40–80 ×B ⇒ taker 2–4 %/thang). **KHONG do** (pre-reg khoa 3 cau hinh, khong tune sau khi xem so).
- ⚠️ Mo hinh gia dinh **maker khop TAI dung gia muc** khi `low ≤ p ≤ high` — **KHONG mo hinh hoa hang doi +
  adverse selection**; maker la **can TREN lac quan**. Taker la can duoi.

**(C2): khong lat dau ⇒ grid o day KHONG "song nho maker"**, nhung day la do luoi rong, khong phai ket luan chung.

## 4. (C3) CHON COIN / CHON THOI DIEM GIUP BAO NHIEU?

**corr(net_maker, ·):** `ER −0,14` · `|ret| +0,07` · `VR60 +0,20` · `ADR −0,32` · `realized +0,69` · `inband +0,30`.

**Tercile (maker):**

| nhom | ER | ADR | VR60 |
|---|---|---|---|
| thap | **+3,96 %** | **+1,04 %** | −4,24 % |
| giua | −5,25 % | +0,22 % | −3,30 % |
| cao | −4,28 % | **−6,84 %** | +1,96 % |

**Theo cua so (maker):** 2022-05 **−20,06 %** (0/18) · 2022-11 −11,28 % (4/18) · 2023-06 −1,51 % (8/18) ·
2024-03 **+12,24 %** (18/18) · 2024-11 +7,31 % (18/18) · 2025-06 +2,14 % (15/18).

**Theo coin (maker, G1/G2/G3):** BTC −0,08/−0,22/**+2,42** · ETH −1,49/−1,70/+0,09 · BNB −0,41/−1,12/+1,07 ·
XRP **+1,27/+0,69/+1,21** · DOGE −3,43/−3,63/+0,82 · SOL **−10,71/−10,55/−7,70**.

- **Chon THOI DIEM: CO tin hieu nhung KHONG qua CI.** `corr(inband, net) = +0,30` (o trong dai ⇒ tot hon),
  tercile ER thap nhat **+3,96 %** (duong) — dung huong gia thuyet "range-bound", nhung **corr(ER,net) chi −0,14**.
- **Chon COIN: ro hon.** `corr(ADR, net) = −0,32`: coin/ky **bien dong thap** tot hon (ADR tercile thap +1,04 %
  vs cao −6,84 %). Nhung **khong du de lat tong**: ngay trong nhom tot nhat van co run am (SOL keo xuong −9,7 %).
- Luat (C3) doi hoi **CA** `corr(ER,net)<0` **VA** `corr(|ret|,net)<0` ngoai CI. `corr(|ret|,net)=+0,07` ⇒
  **KHONG DAT**. Tin hieu thoi diem **khong du tin cay** (n=108, day la so mo ta, khong phai forward).

## 5. RUI RO TRONG TREND — chan duoc khong?

- **Tran ton kho** (bounded grid) da chan lo VO HAN: 26/108 run ket hang o day dai — nhung van **lo MTM −10…−20 %**.
- **Co che that bai giong het bai hoc `RESULT_FLATGRID`/`RESULT_5MGRID`**: luoi **khong cuu duoc cu trend manh**;
  `DCA_GRID_WEIGHTS=1,1,3,8` trong he cu **thang** vi bac sau cuu cum (FTT 11/2022), nhung do la **martingale-ish
  + tang tap trung** — khong phai grid neutral.
- **Khong co trend filter trong test nay** (pre-reg khong dat). Tien de do tiep: tat luoi khi `ER`/MA = trend.

## 6. TRA LOI 4 CAU HOI

1. **Grid co cua khong (net > 0 ngoai CI)?** **KHONG.** Gross −1,63 %/thang, CI chua 0; sau phi am ca maker
   va taker. *Chu ky hoan tat* thi duong (+2,31 %) nhung *ton kho* am (−3,93 %) nuot het.
2. **Phu thuoc maker fee the nao?** **Yeu** (0,34 pp/thang, khong lat dau) **voi luoi rong**. Chi voi luoi day
   (chua do) phi moi thanh diem chet. Maker-fill **chua duoc kiem chung** (khong co orderbook/queue).
3. **Chon coin/thoi diem giup bao nhieu?** **Mot phan, khong du.** Huong dung (ER thap / ADR thap / o trong
   dai ⇒ tot hon; 2022 crash ⇒ −20 %), nhung `corr(|ret|,net)` **sai dau** ⇒ luat (C3) **FAIL**.
4. **GO hay NO-GO?** **NO-GO/NULL.** Dung luat khoa: (C1) FAIL, (C3) FAIL. Khong de xuat tich hop.

## 7. THIEU GI (de mo lai sau, neu owner muon)

- **Orderbook/queue** de do **maker-fill that** (adverse selection) — hien tai la gia dinh lac quan.
- **Funding** (futures): chua tinh vao ket qua chinh; long perpetual trong dai tra funding ~0,03 %/ngay ⇒
  lam ket qua **xau hon** (khong the tot hon). `RESULT_COST_TRUTH` §4-5.
- **Trend filter + luoi day** (turnover cao) — vong moi, phai pre-reg rieng.
- Cua so 1 thang × 6 nam thay vi lien tuc: **chua do chuoi dai** (thoi gian ket hang lien tuc).

## 8. KET LUAN

**Grid trung tinh la "ban bien dong" (short vol/range)**: an chu ky, tra bang ton kho. Tren 6 coin × 6 cua so
DEV, **net khong phan biet duoc voi 0 va am sau phi**; rui ro tap trung o **trend/crash** (2022-05 −20 %/thang),
khong o **phi**. **NO-GO** — khong tich hop, khong tieu holdout 2026, khong doi incumbent.
