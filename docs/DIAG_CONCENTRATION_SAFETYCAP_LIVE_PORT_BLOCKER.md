# DIAG — PORT 2 guard CONC-CAP sang duong LIVE: **BUOC 0 DUNG LAI, CHUA IMPLEMENT**

> **Trang thai: BLOCKER REPORT.** Theo dung dieu kien dung ma MASTER dat o Buoc 0:
> *"Neu Buoc 0 phat hien live path khac biet du lon khien viec port khong don gian ... DUNG,
> bao cao lai cho toi truoc khi tu thiet ke giai phap thay the."*
>
> **KHONG sua mot dong `.java` nao. KHONG commit code. KHONG tu chon giai phap thay the.**
> Tai lieu nay chi ghi cai da doc duoc va liet ke cac diem MASTER phai quyet.
>
> Nen: code sim da verify parity 6/6 tai commit `5e82983`; ket qua o
> `docs/RESULT_CONCENTRATION_SAFETYCAP.md`.

---

## 0. Ket luan mot dong

**Guard 2 (`CONC_CAP_BD_RATE_*`) port duoc sach se.** **Guard 1 (`CONC_CAP_AGG_DCA_*`) KHONG port
duoc nguyen nghia**: tren live **ca TU SO lan MAU SO cua ti le deu khong co dai luong tuong duong**
— khong phai thieu mot chi tiet, ma la thieu ca hai ve cua phep chia.

---

## 1. Diem chen — **RO RANG**, khong phai cho blocker

Duong live tap trung ve **MOT ham duy nhat**: `DetectEntrySignal2TradeNormal.createOrderBuyRequest`
(dong 740-902), duoc goi tu ca 3 nguon giong het cau truc ben sim:

| nguon leg | call-site live | tuong ung sim |
|---|---|---|
| BIG_DOWN / market-signal | `:289` (`levelChange` tu `getMarketStatus1M`) | `Simulator:336` |
| DCA-grid (nhanh market-level) | `:303` (`MarketLevelChange.DCA_LEVEL1`) | `Simulator:344` |
| DCA-grid (nhanh `isDcaAlt`) | `:324` (`MarketLevelChange.DCA_LEVEL1`) | `Simulator:362` |

Thu tu cong trong `createOrderBuyRequest`:

```
prediction == null            (:746)
EntryGate qua aiRejectFilter  (:765-788)
KILL-SWITCH mat do lenh       (:793-798)   <- live-only, sim khong co
managerBudget / U_MAX         (:824-832)
TIER_3_SHITCOIN chan DCA      (:845-850)
budget *= tierMultiplier      (:853)
gia sizing (price_realtime)   (:861-871)   <- live-only
quantity = Utils.calQuantity  (:872)
--------------------------------------------- DIEM CHEN TUONG DUONG
if (quantity != null && quantity != 0) {    (:880)
    new OrderTargetInfo(...)                (:881)
    addMarginRunning(budget)                (:888)
    rpush REDIS queue / shadowHandleOrder   (:894-896)  <- dat lenh THAT
}
```

=> **Diem chen dung la ngay sau `:880` (dau khoi `if`), truoc `new OrderTargetInfo` o `:881`** —
sau khi `quantity` da tinh, truoc khi order ton tai va truoc khi day vao Redis queue. **Doi xung
chinh xac voi diem chen ben sim.** Day **khong** phai ly do dung.

Khac biet phu can ghi: live co them 2 buoc sim khong co (kill-switch mat do `:793`, sizing theo
`price_realtime` `:861-871`), nhung ca hai deu nam TRUOC diem chen nen khong anh huong.

---

## 2. Guard 2 — `CONC_CAP_BD_RATE_*` — **PORT DUOC**

Guard 2 chi can: (a) diem chen (co — muc 1), (b) mot hang doi timestamp cac leg BIG_DOWN da mo.

Thiet ke cho live (khac sim ve co che, giu nguyen Y NGHIA):

| | sim | live |
|---|---|---|
| Moc thoi gian | `ticker.startTime` (thoi gian sim) | **`System.currentTimeMillis()`** (dong ho that) |
| Reset | `concBdOpenTimes = null` trong `initData()` / `initDataReady()` | **khong co reset** — cua so tu troi: moi lan doc thi `pollFirst()` het cac moc `<= now - 60 phut` |
| Ghi nhan | sau khi `orders.add(order)` | sau khi day order vao Redis queue / `shadowHandleOrder` (`:894-896`), tuc chi dem leg THAT SU da gui di |
| Concurrency | don luong | `createOrderBuyRequest` chay tu `executorService` nhieu luong => hang doi phai la **`ArrayDeque` co `synchronized`** hoac `ConcurrentLinkedDeque` + dem co khoa |

**Caveat duy nhat (phai ghi ro cho MASTER):** live chay 24/7 nhung **co restart**. Sau restart hang
doi rong => trong 60 phut dau guard dem thieu (noi long). Vi guard la **safety-net dat nguong cao
hon dinh lich su**, huong sai nay la "bo sot", khong phai "chan nham". Van phai la quyet dinh co y
thuc cua MASTER, khong phai cua toi.

---

## 3. Guard 1 — `CONC_CAP_AGG_DCA_*` — **KHONG PORT DUOC NGUYEN NGHIA**

Cong thuc sim:

```
(tong margin cua MOI leg DCA-grid bac>=1 dang mo, cong dong toan so  +  margin leg sap mo)
-------------------------------------------------------------------------------------------  > 0.45
                                     equity hien tai
```

### 3.1 TU SO — live khong co phan ra theo LEG

Sim giu `symbol2OrdersEntry[symbolId]` = **danh sach TUNG LEG**, moi leg co `marketLevelChange`
rieng, nen cong duoc dung cac leg `DCA_LEVEL1` (bac>=1).

Live **khong co cau truc do**. Vi the live la `BudgetManager.symbol2Pos: Map<String, PositionRisk>`
— **vi the DA GOP tai san giao dich**, mot dong cho mot symbol. `PositionHelper.callMargin(pos)`
(`PositionHelper:32-37`) tra margin cua **ca cum da gop**, khong tach duoc leg dau khoi cac leg DCA.

Muc lech dinh luong (ladder `DCA_GRID_WEIGHTS=1,1,3,8`, tong 13):

| cum dang o bac | margin theo cach SIM (chi leg DCA) | margin theo cach LIVE (ca cum) | **live / sim** |
|---|---|---|---|
| bac 1 | 1/13 | 2/13 | **2.00x** |
| bac 2 | 4/13 | 5/13 | **1.25x** |
| bac 3 | 12/13 | 13/13 | **1.08x** |

=> Dung margin cum gop voi **cung nguong 0.45** thi guard live **chat hon sim tu 1.08x den 2.00x**,
tuy cum dang o bac nao. **Con so 0.45 mat y nghia da verify.**

### 3.2 `symbol2Level` KHONG phai co "dang o trang thai DCA" dung tin

Ung vien thay the duy nhat de biet symbol nao "dang DCA" la
`BudgetManager.symbol2Level: Map<String, MarketLevelChange>`. No **khong dung duoc**:

- `BinanceOrderTradingManager:181` — `symbol2Level.put(order.symbol, order.marketLevel)`: bi **ghi
  de boi level cua lenh MOI NHAT**, khong phai trang thai tich luy cua cum.
- `BinanceOrderTradingManager:326-330` — bi **XOA** khi
  `position.getUpdateTime() >= startTime + 30 * TIME_MINUTE`:
  ```java
  if (position.getUpdateTime() < startTime + 30 * Utils.TIME_MINUTE) {
      BudgetManager.getInstance().symbol2Level.put(symbol, orderInfo.marketLevel);
  } else {
      BudgetManager.getInstance().symbol2Level.remove(symbol);
  }
  ```
  Tuc mot cum da DCA nhung "cu" hon 30 phut se **bien mat** khoi `symbol2Level` — dung loai cum ma
  guard 1 sinh ra de dem.

### 3.3 MAU SO — live **khong co equity hien tai**

| | sim | live (duong THAT) |
|---|---|---|
| Bien dung | `balanceBasic` = `BudgetManagerSimple.equityNow()` khi `FIX_B3` (ca 3 baseline deu `SIM_FIX_B3=true`) | `BudgetManager.balanceBasic` |
| Ban chat | **equity compound, cap nhat lien tuc** | **`public static Float balanceBasic = Configs.capitalStart();`** (`BudgetManager:33`) — **HANG SO, khong bao gio duoc gan lai tren duong that** |

`BudgetManager.updateBudget()` (`:57-69`) co doc `getAccountUMInfo().getWalletBalance()` vao
`balanceCurrent` — nhung chi de **GHI LOG**; dong duy nhat dung no la
`BUDGET_PER_ORDER = balanceBasic / Configs.number_order_budget`, tuc van la **hang so**.
(Chi nhanh shadow `LiveProfileC3` moi co equity that qua `ShadowBookC3.equityNow(pxOpen)` —
`DetectEntrySignal2TradeNormal:820` — nhung do la so GIAY, khong phai tai khoan that.)

=> `margin / equity` tren live se la `margin / von-khoi-diem-co-dinh`, **khac han** `margin / equity`
cua sim. Sau mot giai doan lai/lo dang ke, hai dai luong nay lech theo ti le equity/capitalStart.

### 3.4 Them mot lech nho da phat hien (khong phai blocker nhung phai ghi)

`BinanceOrderTradingManager:416-418`:
```java
if (PositionHelper.calRateLoss(position) < 6 * Configs.RATE_PROFIT_STOP_MARKET) {
    marginTotal += margin;
}
```
`PositionHelper.calRateLoss` (`:44-53`) = `markPrice/entryPrice - 1` cho long => **DUONG khi lai**.
Nen `marginRunning` cua live **loai cac vi the dang lai manh** (> `6 x RATE_PROFIT_STOP_MARKET`).
Sim thi `marginRunning` la tong THUAN moi leg. Neu MASTER chon dung `marginRunning` o bat ky ve nao
cua guard 1, phai biet no khong phai tong so that.

---

## 4. Bang tong ket "co / khong" cho Buoc 0 muc 2

| thu guard can | live co san? | o dau |
|---|---|---|
| Diem chen sau `quantity`, truoc khi dat lenh | **CO** | `DetectEntrySignal2TradeNormal:880` |
| Danh sach vi the dang mo + margin tung cai | **CO** | `BudgetManager.symbol2Pos`, `symbol2Margin` (rebuild moi vong `updatePositionInfo`) |
| Phan ra margin **theo LEG** (tach leg DCA bac>=1) | **KHONG** | vi the da gop o san; khong cau truc nao giu leg |
| Co "symbol dang o bac DCA>=1" dung tin | **KHONG** | `symbol2Level` bi ghi de + bi xoa sau 30 phut (`BinanceOrderTradingManager:326-330`) |
| **Equity hien tai** | **KHONG** (duong that) | `balanceBasic` la hang so `capitalStart()` |
| Tong margin toan so | **CO, nhung khac dinh nghia sim** | `marginRunning` loai vi the lai manh (`:416-418`) |
| Rolling window BIG_DOWN 60 phut | **KHONG — phai tu track** | (thiet ke da co o muc 2, port duoc) |

---

## 5. CAC DIEM MASTER PHAI QUYET (tai lieu nay **KHONG** tu chon)

Guard 1 chi port duoc sau khi MASTER chot **ca ba** cau duoi. Moi lua chon deu **doi y nghia cua
nguong 0.45**, nen theo ky luat cua du an, chung can mot **pre-reg rieng**:

1. **TU SO** — dem cai gi tren live?
   (i) tu track margin DCA cong don theo symbol trong bo nho tien trinh (dung nghia sim, nhung
   **mat het khi restart**); hay (ii) dung margin **ca cum gop** cua cac symbol dang o trang thai
   DCA (co san, nhung **to hon sim 1.08x-2.00x** — muc 3.1); hay (iii) mot dinh nghia khac.
2. **CO "DANG DCA"** — neu chon (ii), lay o dau, khi `symbol2Level` khong dung tin (muc 3.2)?
3. **MAU SO** — dung gi lam equity khi duong that khong co equity hien tai (muc 3.3)? Giu
   `capitalStart()` (doi nghia cua 0.45), hay bo sung mot nguon equity that cho live (la mot thay
   doi **ngoai pham vi** "port guard", cham vao sizing cua ca he)?

**Ghi chu quan trong:** cau 3 dac biet nang — them "equity that" vao `BudgetManager.balanceBasic`
se **doi `BUDGET_PER_ORDER`**, tuc **doi size cua MOI lenh live**. Do **khong** con la lap safety-net
nua ma la doi co che sizing cua he thong dang chay tien that. Toi **khong** dong vao no.

---

## 6. De xuat pham vi kha thi ngay (de MASTER can nhac, **chua lam**)

Tach lam hai:

- **Guard 2** (`CONC_CAP_BD_RATE_*`): port duoc ngay theo thiet ke muc 2, default OFF, rui ro thap
  (chi them mot hang doi timestamp + mot khoi `if` truoc khi dat lenh).
- **Guard 1** (`CONC_CAP_AGG_DCA_*`): **treo lai**, cho pre-reg rieng tra loi 3 cau o muc 5.

Toi **chua** lam ca hai, dung cho MASTER quyet.

---

## 7. Xac nhan trang thai flag

4 flag (`CONC_CAP_AGG_DCA_ENABLED=false`, `CONC_CAP_AGG_DCA_PCT=0.45`,
`CONC_CAP_BD_RATE_ENABLED=false`, `CONC_CAP_BD_PER_HOUR=75`) hien **chi ton tai o duong SIM**
(commit `5e82983`). Tren duong LIVE **chua co dong code nao doc chung** — tuc live **hoan toan
khong bi anh huong** boi bat ky thu gi trong round nay. Khong co gi can bat/tat tren live luc nay.

---

## 8. File da doc

`DetectEntrySignal2TradeNormal.java` (1027 dong), `BudgetManager.java`, `BinanceOrderTradingManager.java`
(vung 170-195 / 310-340 / 400-450), `PositionHelper.java`, `DcaProcessor.java`
(`getDCAProduction`), `MarketBigChangeDetector.java`, `Configs.java`,
`SimulatorMarketLevelTicker1MStopLoss.java` (de doi chieu).
