# PREREG_D3D4_FILTER_SIM — chot thiet ke sim filter D3/D4 (pump-dump) doi chieu baseline T170

> **Pre-reg TRUOC khi chay.** Thuc hien sau `docs/RESULT_PUMPDUMP_OHLCV.md` (commit `8a4e5f0`).
> **KHONG push.** 2026-09-17.

## 0. BOI CANH + CANH BAO POST-HOC (doc truoc)

`RESULT_PUMPDUMP_OHLCV` (descriptive, chi doc du lieu, KHONG chay sim) do 4 detector "pump xong
chuan bi dump" bang OHLCV 1m + OI 5m tren 49 lenh SUP. Ket qua: **ca 4 deu NULL** theo tieu chi
chot truoc (monotone rho>=0.7 VA CI hieu mean khong chua 0 VA PnL rong >= 0). Trong do:

- **D3 `oi_px_div`** = `oiDelta24h(entry) - (close(t)/close(t-24h) - 1)` → rho +0.578, PnL rong
  what-if DUONG (+10.8k/+3.4k/+5.1k o p75/p90/p95) nhung **CI chua 0** (n_SUP=49 nho).
- **D4 `stall`** = `ret_6h - ret_15m` → rho +0.557, PnL rong DUONG (+12.4k/+4.0k/+3.9k) nhung
  **CI chua 0**.

User yeu cau: *"Co chay de doi chieu baseline"*. Nghia la chay sim THAT de xem hai tin hieu nay
(dung huong nhung yeu o muc mo ta) co that su lam tang chat luong khi ap dung nhu MOT FILTER
lenh moi hay khong.

**CANH BAO (phai ghi ro, khong duoc bo):** day la **luat chon POST-HOC** — hai feature D3/D4 duoc
chon SAU khi da nhin ket qua DEV. Tong detector da thu tich luy = **11** (6 close-based + 4
OHLCV/OI + bai nay). ⇒ **multiplicity rat cao**. Ket qua duong tren DEV chi la **UNG VIEN**,
**KHONG duoc ap dung**; phai xac nhan o forward/holdout 2026. Neu am/khong khac biet ⇒ **NULL**.

## 1. KHA THI TINH FEATURE O QUY MO TOAN UNIVERSE (Buoc 1)

Filter phai tinh duoc feature tai **MOI moc vao lenh, cho MOI coin** (khong chi 249 lenh). Kha thi:

| feature | thanh phan | nguon in-sim | ket luan |
|---|---|---|---|
| D4 `stall = ret_6h - ret_15m` | close 1m | **HistoryManager** (ring 1m, RING_SIZE=2048 ≈ 34h) — da co san trong sim, KHONG can bang tra cuu | **KHA THI in-sim** |
| D3 `ret_24h` | close 1m | **HistoryManager** (ring 1m) | **KHA THI in-sim** |
| D3 `oiDelta24h` | OI file 5m | KHONG co trong sim → bang tra cuu `filter_oi_lookup.bin` (111.5M record DEV, keyed symId + ts 5m-index, sort ascending, binary-search floorEntry) | **KHA THI (bang tra cuu)** |

- **D4 KHONG can nguon 15m ngoai**: ret_15m = close(t)/close(t-15m) tinh tu ring 1m cua
  HistoryManager (chinh xac, cung quy uoc 1m-close nhu screen). KHONG dung CLOSES_1H.bin (thieu 15m).
- **D3 can bang tra cuu** cho rieng `oiDelta24h` (OI file khong co trong sim). Bang tra cuu sinh
  offline tu `oi_percoin_full.bin` (5m), cot `oiDelta24h` (field 0), cua so DEV (2021-08-01 →
  2026-01-01), 629 symbol, 111,521,331 record (sau bo NaN 281k → giu NaN de "khong tinh duoc").

### Quy uoc tinh feature (TRUNG screen de p90 khop)

Ky hieu `close(t)` = close bar 1m co `startTime <= t`. Tai moc vao lenh (bar co `startTime = T`,
entry price = close(T)):

- `now = close(T - 1m)`  (bar dong ngay truoc moc vao; trung `ce = c[N-1]` cua extractor screen)
- `ret_15m = now / close(T - 15m) - 1`
- `ret_6h  = now / close(T - 6h)  - 1`
- `ret_24h = now / close(T - 24h) - 1`
- `stall = ret_6h - ret_15m`
- `oi_px_div = oiDelta24h(T) - ret_24h`, voi `oiDelta24h(T)` = snapshot OI 5m gan nhat `ts <= T`
  (floorEntry).

Thieu thanh phan (history < 24h / gap > 30m / OI NaN) ⇒ feature **NaN** ⇒ **KHONG filter** (giu lenh).

## 2. THIET KE FILTER (chot truoc, KHONG toi uu nguong)

- **Nguon filter**: 1 nguon CO DINH = **phan vi p90 cua feature tinh tren DEV** (toan bo 920 leg
  entry moi DEV: PREDICT_SYMBOL_TRADE + BIG_DOWN, 2022-2025). KHONG toi uu nguong.

  | detector | feature | p90 (DEV) |
  |---|---|---|
  | D3 | `oi_px_div` | **0.319439835** |
  | D4 | `stall` | **0.112770706** |

- **Luat**: **bo qua lenh moi neu `feature > p90`** (feature cao = de sup). NaN ⇒ giu lenh.
- **Pham vi ap dung**: **moi lenh entry moi** = `PREDICT_SYMBOL_TRADE` (selector Best-N) va
  `BIG_DOWN`. **KHONG ap cho DCA** (DCA_LEVEL1 va leg dcaSignal) — DCA la cuu vi the da vao.
- **3 bien the (k=3)**: `FILT_D3` (chi D3) · `FILT_D4` (chi D4) · `FILT_D3D4` (ca hai: bo qua neu
  **bat ky** feature nao > p90 cua no). Doi chung: parity T170 (`SIM_FILTER_D3D4=off`).

## 3. CODE + PARITY

- Flag moi **default OFF**: `SIM_FILTER_D3D4=off|d3|d4|both`. Doc qua `Cfg.getOr` (profile key).
- Bang tra cuu OI doc bang **binary-search floorEntry** (tien le `RegimeSchedule`), file
  `/home/ubuntu/java/filter_oi_lookup.bin`.
- **CONG PARITY**: OFF ⇒ `printDone.csv` **byte-identical** `efb793e2468ca3a7318da0f0ad23d4fc`
  (bo header `8d03d4e18c15cc825731fc25f7362bb8`), 1089 lenh. Khac ⇒ DUNG + bao.
- KHONG sua feature extractor / MarketBigChangeDetector / gene HPO.

## 4. CHAY + CHAM

- Chay tuan tu tren `/home/ubuntu/wfo_ds_x1_2021`, `TICKER_SOURCE=file`, `SIM_END_DATE=20251231`,
  profile clone `x1_gs_t170` + key moi. Artifact `/home/ubuntu/java/devrun/`.
- **Cham**: 5 rate chat luong toan bo leg (`win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP`) vs parity
  + CI (bootstrap block-72h x1.21, 2000 rep, seed 20260905). **Kiem tra co che** (dem so lenh bi
  loc, co binding khong). Rang buoc cung: bar moi tu equity THAT `sim.out`; tap trung 1 coin; so leg;
  PnL/chi so bao cao rieng (KHONG dung de chon).
- Nguong BANG CHUNG: >= 2 rate ngoai CI cung huong tot. Nguong RUI RO: `docs/RISK_APPETITE.md`.

## 5. KY LUAT (da nhin ket qua truoc khi chay)

- Post-hoc, multiplicity 11. Ket qua duong tren DEV = ung vien, KHONG ap dung, can holdout 2026.
- Am/khong khac biet ⇒ NULL.

Co-Authored-By: Claude (subagent) — pre-reg truoc, khong push.
