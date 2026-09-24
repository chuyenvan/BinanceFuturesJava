# PREREG_TRAIL_CAP_1030 — Nang TRAN giveback cua trailing tu 3%/8% len **10%/30%** (SIM THAT, T170, DEV)

Viet **TRUOC** khi do (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Tien le: `docs/result/RESULT_TRAIL_HINGE.md` (cap phang 0.05/0.12 = NULL), `docs/result/RESULT_TRAIL_LADDER.md`
(bac thang L1/L2/L3 = NULL), `docs/result/RESULT_PEAK_CLOSE.md` (dinh CLOSE = NO-GO),
`docs/result/RESULT_CLOSE_BIGGAP.md` (harness offline, cap 0.20/0.35 **voi dinh CLOSE** = NULL).
Day la **vong thu 6 tren truc exit** va la vong **dau tien doi TRUC TIEP 2 moc tran `maxGap`**
(3%/8% -> 10%/30%) — cac vong truoc doi *hinh dang ham gap* hoac *nguon dinh*, **chua vong nao
chay cap 0.10/0.30 tren sim that**.

**Yeu cau cua owner (nguyen van):** *"khong chap nhan viec tran giveback bi chan o 3% (lenh yeu) /
8% (lenh manh) => lenh 2x/3x chi cach dinh 3-8 diem la bi cat. Doi 3 -> 10 va 8 -> 30."*

---

## 0. Cau hoi

Co che exit hien tai (T170, incumbent): arm `+7%`; `gap = min(peak x TS_GIVEBACK_RATIO(0.5), maxGap)`;
`rate (SL) = peak - gap`; ratchet lien tuc (step lam tron `0.005`); bat bien **SL luon > entry**;
loser time-stop `168h`; peak = **HIGH nen 1m** (`TS_PEAK_MODE=high`, giu nguyen).
`maxGap` co 2 muc theo `pNoPump` (= `symbolPred`, do `FIX_B1` chep sang cum):
**yeu** `TS_MAX_GAP_WEAK = 0.03` khi `pNoPump > TS_PNOPUMP_WEAK_THR (0.29)`, nguoc lai **manh**
`TS_MAX_GAP = 0.08`.

> **Cau hoi:** nang 2 moc tran tu **3%/8% len 10%/30%** (giu nguyen ratio 0.5, peak HIGH, arm +7%)
> — tuc cho phep lenh giveback xa dinh hon (**nuoi lenh lau hon**) — **co lam ket qua TOT HON co y
> nghia** khong, xet tren **5 rate chat luong + CI block-72h**, dong thoi **khong vi pham rang buoc
> cung** va **khong lam rate nao XAU di co y nghia**?

---

## 1. BUOC 0 — DINH NGHIA CHINH XAC (doc code, KHONG tu dien giai)

Doc `src/main/java/com/binance/chuyennd/tradecore/Configs.java`,
`.../tradecore/TradeUtils.java` (`calRateLossDynamicBuyPNoPump`, `trailFromCap`),
`.../research/OrderTargetInfoTest.java` (`trailRate` :374-394), `.../tradecore/DumpConfig.java` :70-84.
**CHINH XAC 5 tham so (ten that trong code):**

| # | vai tro | ten trong code | gia tri dang chay | key ghi de (override) |
|---|---|---|---|---|
| (a) | tran `maxGap` **MANH** | `Configs.TS_MAX_GAP` (Configs.java:140) | `0.08f` | `SIM_TS_MAX_GAP` (Configs.java:801) |
| (b) | tran `maxGap` **YEU** | `Configs.TS_MAX_GAP_WEAK` (:141) | `0.03f` | `SIM_TS_MAX_GAP_WEAK` (:802) |
| (c) | nguong phan biet yeu/manh | `Configs.TS_PNOPUMP_WEAK_THR` (:443) | `0.29f` | `SIM_TS_PNOPUMP_WEAK_THR` / profile `TS_PNOPUMP_WEAK_THR` |
| (d) | ty le giveback | `Configs.TS_GIVEBACK_RATIO` (:173) | `0.5f` | profile `TS_GIVEBACK_RATIO` |
| (e) | nguong ARM | `Configs.RATE_PROFIT_STOP_MARKET` (:169) | T170 profile: `SIM_RATE_PROFIT_STOP_MARKET=0.07` | `SIM_RATE_PROFIT_STOP_MARKET` |

Chieu phan nhanh (TradeUtils.java:41-44): `maxGap = (pNoPump != null && pNoPump > pNoPumpWeakThres)
? TS_MAX_GAP_WEAK : TS_MAX_GAP` — **`>` (khong phai `>=`)**; `pNoPump == null` (khong co selector)
=> coi nhu **YEU** (bao thu). `TS_GIVEBACK_RATIO` la **HANG SO theo profile** (khong doc env truc tiep
o call-site), gia tri 0.5 trong T170 (`profiles/x1_gs_t170.properties`).

**THAY DOI DUY NHAT cua chan nay — dung 2 cap, khong gi khac:**
`TS_MAX_GAP_WEAK 0.03 -> 0.10` va `TS_MAX_GAP 0.08 -> 0.30`. Giu nguyen: ratio 0.5, `TS_PNOPUMP_WEAK_THR`
0.29, peak HIGH, arm 0.07, step 0.005, ratchet guard, 168h, funding/sizing/entry/gate/DCA.
**Bat bien "SL > entry" van giu**: `gap = min(peak x 0.5, cap) <= peak x 0.5` (voi moi `cap`, ke ca
0.30) => `rate = peak - gap >= peak/2 > 0` (arm chi xay ra khi peak >= +7%).

### 1.1 Pham vi anh huong — DO TRUOC tren trace cua chan parity cu (`pc-part`, 1089 leg)

`gap = min(peak/2, cap)`; **cap bind khi `peak > 2 x cap`**. Do tren `trailTrace.csv` (mau so chung):

| nhom | nang (peak/2 > cap cu?) | n | peak TB | rate TB (cu) |
|---|---|---|---|---|
| WEAK, peak <= 6% | khong | 25 | 3,5% | −17,2% |
| WEAK, 6–10% | **co** | 151 | 8,1% | 3,9% |
| WEAK, 10–20% | **co** | 129 | 12,6% | 8,0% |
| WEAK, > 20% | **co** (bind ca cap moi) | 40 | 122,4% | 41,8% |
| STRONG, peak <= 16% | khong | 621 | – | – |
| STRONG, 16–30% | **co** | 99 | 21,4% | 13,3% |
| STRONG, 30–60% | **co** | 23 | 37,3% | 29,2% |
| STRONG, > 60% | **co** (bind ca cap moi) | 1 | 72,2% | 61,7% |

=> **443/1089 leg (40,7%)** co cap cu dang bind => tap chiu anh huong THAT; tong `SumPnL` cua rieng
nhom nay = **84 459 USDT** (tong toan chan 76 070 → phan con lai −8 389). Cap **moi** chi con bind
**41 leg (3,8%)**. => Doi cap la **NOI trailing tren 40,7% so leg**, khong phai doi nho.

### 1.2 Ky vong ghi TRUOC (de khong dien giai sau)

- SL bi dat **THAP hon** voi moi leg bi anh huong (gap lớn hơn) => **lenh song lau hon / thoat xa dinh hon**.
- **Capture ratio (profit/peak) se GIAM ve co hoc** o nhom bi anh huong (thoat cach dinh xa hon)
  => capture giam **KHONG** tu dong la xau (phai doc kem `SumPnL`/`meanP`). Day la **rui ro dien giai
  nguoc** da ghi truoc.
- Chieu TOT ky vong: `SumPnL`/`meanP`/`mP|SM` tang (nuoi lenh), `TSloss%` co the tang (giu lau hon
  => nhieu co hoi bi quay dau). Chieu XAU ky vong: **mat luot vao** (giu lau hon chiem slot) — dung
  bay da do duoc o `RESULT_PEAK_CLOSE` (F3 mat 50 leg) va o harness `RESULT_CLOSE_BIGGAP` (bias
  "+20,6% harness" khong chuyen duoc sang sim that).

---

## 2. BUOC 1 — Code + profile (KHONG sua code)

Ca 2 tham so **da doc duoc qua override profile** (`Configs.java:801-802`, mo 2026-09-03 chinh vi muc
dich nay, comment ngay tren: *"gap trailing: TRUOC DAY hardcode-only (0.08/0.03) => profile khong dieu
khien duoc. Mo override de tim kiem toan cuc. Default (khong khai bao) = gia tri cu => byte-identical"*).
=> **KHONG sua code, KHONG build lai jar, KHONG doi jar**.

- Profile moi `profiles/x1_gs_t170_cap1030.properties` = **ban sao nguyen** `profiles/x1_gs_t170.properties`
  + dung 2 dong `SIM_TS_MAX_GAP=0.30` va `SIM_TS_MAX_GAP_WEAK=0.10` (khac 2 key duy nhat).
- Chan parity chay **profile `x1_gs_t170` nguyen ban** (khong override cap).
- `tools/check_cfg_gateway.sh` phai OK (khong doi code => chi de xac nhan).

## 3. BUOC 2 — CONG PARITY (bat buoc, chot TRUOC)

`printDone.csv` cua chan parity (`x1_gs_t170`, chi `SIM_TRAIL_TRACE=1` — do-luong-only, KHONG doi
printDone) phai **byte-identical** `md5 = efb793e2468ca3a7318da0f0ad23d4fc` (**n=1089 leg**,
equity cuoi **111 070**, cua so `20210701..20251231`, `symbol_mapper=863`).
Chan nay chay lai tu dau trong round (khong tai su dung output cu) tren **dung jar** se dung cho chan
variant: `sha256 = 70066fca33d347c3b6212dfd613f3a6694ca3684e7aece188790b183dfba24ff`
(= `target/binance-java-sdk-1.2.4.jar` hien tai; khong commit nao doi `src/` tu `dca07ce`).
**Bat ky khac => DUNG, bao RO, khong doc ket qua chan variant.**

## 4. BUOC 3 — Chan variant + cham diem (chot TRUOC)

**Chan:** 1 kernel Kaggle, profile `x1_gs_t170_cap1030`, `SIM_TRAIL_TRACE=1`, `SIM_END_DATE=20251231`,
bundle `sim-x1-2021-bundle`, jar dataset `sim-jar-cap1030` (jar hien tai, sha256 `70066fca…`),
`TICKER_SOURCE=file`. DEV only (**2021-07-01..2025-12-31**), **khong 2026**. Chi phi Kaggle: 0
(CPU kernel khong tinh quota); ghi lai wall-clock.

### 4.1 Tieu chi (chot TRUOC)
- **5 rate chat luong** (theo LEG, toan bo tap): `win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP` —
  so **cap-0.10/0.30 vs parity (T170 goc)** tren cung cua so.
- **CI block-72h, 2000 rep, seed `20260905`, anchor `2021-07-01`** cho hieu tung rate, o **HAI do rong**:
  `x1.21` (legacy, muc brief yeu cau) va `inflate(k=1) = 1.0` (chuan hoa `sqrt(2 ln k)`,
  `docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md`; round nay **1 ung vien** vs baseline => `k=1`).
  **"Ngoai CI" chi tinh khi ngoai o CA HAI do rong.** HUONG: `win%`/`mP|SM`/`mP|SL`/`meanP` tang = TOT;
  `TSloss%` giam = TOT.
- **Rang buoc cung** (`docs/runbooks/RISK_APPETITE.md`): `maxDD`/nam `<= 30%`; `UW <= 200` ngay; **khong nam am**;
  quy xau nhat `>= −15%`; **tap trung 1 cum <= 15% equity**. Do tu `sim.out` + `printDone.csv`.
- **Capture ratio** (BAT BUOC bao) cho nhom dinh **>= 20% / >= 50% / >= 100%** (theo LEG, tu
  `trailTrace.csv`; `peak` = `maePeak` = dinh HIGH GIA THAT tu leg dau — **cung mau so cho ca 2 chan**):
  so lenh `n`, **% bi cat som** (phan bo exit reason `STOP_MARKET_DONE`/`STOP_LOSS_DONE`),
  `capture = ratePct/peakPct` (trung vi + trung binh + `mean(rate)/mean(peak)`), `SumPnL`.
  So **parity vs cap-0.10/0.30**.
- **n, turnover/thoi gian giu, va PnL/equity** bao **RIENG** (equity cuoi, CAGR, SumPnL, meanP) —
  **KHONG** dung de chon.
- **TRAIN/TEST** neu tach duoc: TRAIN `2022-01-01..2023-12-31`, TEST `2024-01-01..2025-12-31`.

### 4.2 Ket luan (chot TRUOC)
- **GO (ung vien, KHONG tich hop)** chi khi **DONG THOI**: (a) `>= 2` rate chat luong **ngoai CI cung
  huong TOT** (o CA HAI do rong), (b) **0** rate **XAU ngoai CI**, (c) **het** rang buoc cung.
- **Neu rate KHONG doi nhung capture tang** => ghi ro **"CHUA DU KET LUAN"** + bao so capture.
  *(O day ky vong nguoc lai: capture **giam** co hoc — neu capture giam ma `SumPnL` khong tang thi
  ket luan la **NULL co giai thich**; neu capture giam ma `SumPnL`/`meanP` **tang ngoai CI** thi ghi
  ro la "doi cho doi lay" va van khong duoc tuyen bo GO neu thieu 2 rate ngoai CI.)*
- **Keo dai/lam lai ket luan**: neu **hon** => de xuat buoc tiep (KHONG tu tich hop san xuat, khong
  de xuat them slot ngay). Neu **khong** => **NULL** + noi ro **co nen thu cap nao nua khong** (kem
  ly do; day la vong thu 6 tren truc exit, nen phai noi ro da can kiet chua).
- Ket qua duong (neu co) van la **UNG VIEN** — can **forward** xac nhan.

## 5. Gioi han (ghi TRUOC, khong phai loi chinh minh sau)
1. Kaggle sim luon `TICKER_SOURCE=file` (neo lech 1 lenh/970 vs aerospike — KHONG anh huong so **giua
   2 chan** vi ca hai deu `file`, cung bundle, cung cua so).
2. **1 chan = 1 diem do**; khong quet them cap nao khac trong round nay (do la ly do ton tai cua cau
   "co nen thu cap nao nua khong" o §4.2). Khong fit tham so.
3. `maePeak` (mau so capture) **khong doi** theo cap (HIGH, do-luong-only) => capture la "phan dinh
   HIGH GIA THAT giu duoc"; nhung cap moi **co hoc** lam SL thap hon => capture giam la **he qua
   thiet ke**, khong phai bang chung xau.
4. Nhom `peak >= 100%` chi **21 leg** (tat ca WEAK) o parity => **n nho**, moi so nhom la thong tin
   tham khao, khong du de ket luan rieng.
5. Harness offline (`RESULT_CLOSE_BIGGAP`) **khong thay the duoc** chan nay: (i) no do **dinh CLOSE**
   (da bi sim that bac bo o `RESULT_PEAK_CLOSE`: +20,6% harness -> −0,23% sim), (ii) no **khong dinh
   gia duoc phan "mat luot vao" khi giu lau** (F3: harness +20,6% vs sim −0,23%) — dung ly do bat buoc
   phai chay **sim that**.
