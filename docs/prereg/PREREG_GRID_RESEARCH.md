# PREREG_GRID_RESEARCH — huong MOI: luoi giao dich (grid) DOC LAP voi x1/C3

Viet va **commit TRUOC** khi chay bat ky do luong nao. Khong sua thiet ke sau khi thay so.
Nguon yeu cau: owner 2026-10-01 *"Co cai GRID TRADING thay co nhieu phuong phap lam va chon coin
thoi diem phu hop — ban nghien cuu them"*.

**Rang buoc cung:** thuan Python **OFFLINE / 0-sim** · **KHONG** chay Java/sim tren Oracle ·
**KHONG** cham production/`242`/ONNX/LIVE · **KHONG** sua `.java` · **KHONG push file du lieu** ·
DEV ≤ **2025-12-31** (KHONG cham 2026 = HOLDOUT) · output tool nho · commit + push.

---

## 0. CAU HOI PHAI TRA LOI (4)

1. Grid co **cua** khong (net sau phi > 0, ngoai CI)?
2. Phu thuoc **maker fee** the nao (taker thi sao)?
3. **Chon coin / chon thoi diem** giup bao nhieu?
4. **GO** hay **NO-GO/NULL**?

## 1. GIA DINH PHI — noi RO, day la diem chet cua grid

| muc | %/chan | %/vong | nguon |
|---|---|---|---|
| **maker** | 0,0200 | **0,0400** | Binance USDT-M VIP0 maker (`exec_maker_t170.py:FEE["C"]`) |
| **taker (do)** | 0,0491 | **0,0982** | `RESULT_COST_TRUTH` §3 (fee do tren 991 chan that) |
| **taker + spread** | 0,0560 | **0,1120** | `RESULT_COST_TRUTH` §3 (`base`) |
| **stress** | 0,0750 | **0,1500** | `RESULT_COST_TRUTH` §3 (`p90`) |
| **legacy sim** | 0,4000 | **0,8000** | `Configs.java` (KHONG dung lam chi phi thuc) |

⚠️ **Maker fill la gia dinh MANH**: model cho lenh limit khop TAI dung gia muc luoi khi
`low ≤ p ≤ high` cua nen 1 phut. Thuc te con **hang doi (queue) + adverse selection** — do luong
maker that KHONG co trong du lieu nay (991 chan do duoc deu la TAKER, `RESULT_COST_TRUTH` §5.1).
⇒ **maker = CAN TREN lac quan**, **taker = CAN DUOI bao thu**. Ket luan phai dung CA HAI.

## 2. DU LIEU (1m that, ngoai repo, KHONG push)

- Nguon: **Binance public data** `data.binance.vision`, `futures/um/monthly/klines/<SYM>/1m/<SYM>-1m-YYYY-MM.zip`.
  (Ly do: `raw/<sym>.f32` cu — nguon cua `RESULT_RANGE4H_TOPK` — da bi xoa khoi Oracle; KHONG
  cham `holdout_study/raw` va `wt_crashpen/_wfotmp/holdout/raw` = **HOLDOUT 2026, cam**.)
- **6 coin**: `BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT DOGEUSDT` (trai tu vol thap -> cao, thanh khoan cao, lich su dai).
- **6 cua so thang** (DEV, phu 4 nam): `2022-05`, `2022-11`, `2023-06`, `2024-03`, `2024-11`, `2025-06`.
- Tong: 36 file thang; ghi lai **sha256 tung file** vao JSON ket qua. Trung gian luu `/tmp/grid_research/`.

## 3. THIET KE GRID DO — khoa truoc

**Grid trung tinh (neutral), bounded, bat dau 50% deployed** — dinh nghia chinh xac:

- Neo `p0` = gia **close nen 1m dau tien** cua cua so. `N` muc: `p_i = p0·(1 + (i − N/2)·g)`, `i=0..N`.
- Buoc luoi `g`; dai `±(N/2)·g`. Ngoai dai: **KHONG giao dich them** (luoi co bien — tai hien rui ro ket hang).
- Don vi `δ = B/(N·p0)` coin (B = von). Bat dau `q0 = (N/2)·δ` (long 50%).
- Moi nen 1m `[lo, hi]`: dem so muc bi **cat xuong** (mua tai `p_i`) va **cat len** (ban tai `p_i`);
  gia khop = **dung gia muc** (gia dinh limit). Toi da 1 lan/muc/nen.
- **Tran ton kho**: `q ∈ [0, N/2·δ]` (KHONG ban khoong, KHONG martingale/no them ngoai luoi).
- Phi tru **theo tung lan khop**: `fee_rate · δ · p_khop`.
- PnL cuoi = `cash + q·p_end`, `net% = PnL/B − 1` (tru phi tich luy).

**3 cau hinh luoi (doi xung, khoa truoc):**

| id | dai | buoc `g` | N | y |
|---|---|---|---|---|
| **G1** | ±10% | 1,0% | 20 | chuan |
| **G2** | ±10% | 0,5% | 40 | day (nhieu khop) |
| **G3** | ±30% | 1,5% | 40 | rong (coin bien dong) |

**2 muc phi chay song song**: `maker 0,040%/vong` (chinh) + `taker 0,0982%/vong` (bao thu).

**Funding (do nhay, KHONG tinh vao ket qua chinh):** `0` (spot-like) va `0,03%/ngay × |notional ton kho|`
(futures long tra funding mac dinh 0,01%×3/ngay). Bao rieng.

## 4. CHI SO DO

- **Ket qua**: `net%` theo (coin × cua so × luoi × phi); so lan khop; **ton kho max (% von)**;
  **maxDD MTM 1m**; tach **realized (chu ky hoan tat) vs unrealized (ton kho cuoi)**.
- **Chon COIN/THOI DIEM (do tu 1m)** — tinh TREN CUA SO, KHONG look-ahead:
  - `vol_ann` (bien dong 1m annualized), `ADR%` (bien do ngay trung binh),
  - `ER` = |ln(p_end/p0)| / Σ|ln(p_t/p_{t-1})| (efficiency ratio; thap = di ngang),
  - `VR(60)` = Var(r_60)/(60·Var(r_1)) (<1 = mean-revert, >1 = trend),
  - `|ret|` tong cua so, `%time in band`, `fund_mean` (neu fetch duoc).
- **CI**: bootstrap **block-72h** (dung lai chuan repo: 2000 rep, seed 20260905, `inflate(k)=sqrt(2 ln k)`).

## 5. LUAT KET LUAN (chot TRUOC)

- **(C1) CO CUA** ⇔ `mean(net)` (maker) **> 0** voi **CI72h ngoai 0 phia duong**, VA
  **≥ 3/4 nam** mean dương. Khong dat ⇒ **khong co cua**.
- **(C2) PHU THUOC MAKER** ⇔ dau `net` **doi** giua maker va taker (maker > 0 ≥ taker), hoac
  `|net_taker − net_maker|` ≥ spacing/2. Neu vay ⇒ ket luan **"song nho maker"** + ghi ro rui ro
  adverse selection chua mo hinh hoa.
- **(C3) CHON COIN/THOI DIEM CO GIA TRI** ⇔ `corr(ER, net) < 0` (net cao khi ER thap) **va**
  `corr(|ret|, net) < 0`, **ca hai co CI ngoai 0**; VA chia **tercile ER** cho thay nhom ER thap
  nhat co mean net > 0 (maker).
- **(C4) KET LUAN DUT KHOAT**:
  - **GO** ⇔ **(C1) dat** (o muc maker) **VA** tong net duong o **ca maker va taker** ⇒ kem ke hoach
    (neu (C2) dat thi ke hoach PHAI co buoc do maker-fill that).
  - **NO-GO/NULL** ⇔ con lai. Ghi ro **dan so** nao phu dinh (C1..C3) va **con thieu gi**
    (du lieu orderbook/queue de do maker-fill that; funding; chi phi vay).

## 6. PHAM VI / KHONG DUOC LAM

- Khong tune tham so luoi tren ket qua (3 cau hinh khoa truoc). Khong them coin/cua so sau khi xem so.
- Khong dung PnL/equity de thay luat (C1..C4). Khong dung `legacy 0,8%/vong` lam chi phi chinh.
- Khong ket luan ve live/forward; day la **MO TA qua khu DEV**.
