# E3_HOLDOUT_2026_PREP — kiểm niêm phong + kiểm kê đầu vào 2026 + kế hoạch build

Ngày: 2026-09-29 (TASK E3, CHUẨN BỊ holdout 2026 — KHÔNG chạy sim 2026, KHÔNG nhìn kết quả 2026).
Nháp pre-reg: `docs/prereg/PREREG_HOLDOUT_2026_DRAFT.md` (chưa final, chờ owner duyệt).
Kế thừa: `docs/plan/H1_HOLDOUT_PREP.md` + `docs/prereg/PREREG_H1.md` (lần chuẩn bị trước cho baseline cũ C3).

---

## 0. TÓM TẮT (rủi ro trước)

| # | việc | trạng thái |
|---|---|---|
| 1 | Kiểm niêm phong (artifact kết quả sim 2026) | ✅ in-scope SẠCH; ⚠️ phát hiện artifact stale ngoài scope có data 2026 (§1) |
| 2 | Đầu vào 2026 (ticker/OI/gate p15/bins selector) | ✅ ticker+OI+gate p15 tới 2026-07-01; 🔴 bins selector 2026 THIẾU — blocker (§2) |
| 3 | Nháp pre-reg R4 (chính) + G2 (phụ) | ✅ `PREREG_HOLDOUT_2026_DRAFT.md` |

---

## 1. KIỂM NIÊM PHONG — kết quả

### 1.1 In-scope (repo / `~/kaggle_sim/out` / Kaggle outputs): **KHÔNG có kết quả sim 2026**

- `~/kaggle_sim/out/*` (172 run) và `~/java/devrun/*` (360 run): mọi `printDone.csv` có `max(start,end)` **≤ 20251231**;
  mọi `logs/sim.out` có `days=1644` (= cửa sổ DEV 2021-07-01..2025-12-31). Không run nào vượt qua 2025-12-31.
- Kaggle kernels (`mine`): chỉ 20 kernel, toàn `sim-{gdv2,gd92,...}` = run DEV; không có kernel holdout/2026.
- repo git-tracked: không có `printDone`/`sim.out`; branch `holdout-archive` + `_wfotmp/holdout/` là **TradFi
  trend-following out-of-universe** (S&P/Nasdaq/forex/hàng hóa, data tới 2026-08-27) — **KHÔNG phải crypto 2026 holdout**.

### 1.2 ⚠️ Artifact STALE có data 2026 (ngoài 3 vị trí trên, thời kỳ TRƯỚC reset 2026-09-05)

Các file này sinh khi 2026 còn là VAL (trước khi X1_EXTEND chốt DEV ≤ 2025-12-31 và seal 2026). **Không phải** run
của chiến lược hiện tại (R4/G2/B*) trên holdout; chỉ liệt kê tên/ngày (KHÔNG đọc nội dung kết quả):

| thư mục | class sim | data tới | mtime | ghi chú |
|---|---|---|---|---|
| `~/java/fsrun/{storage,runs/*}` | `SimulatorForcedSeller` (harness forward-search, 1H) | 2026-08-13 | 2026-08-31..09-13 | label/selector sweep, khác chiến lược sim |
| `~/java/simulator/storage` | main sim dir (old) | 2026-05-02 | 2026-08-19 | cửa sổ cũ `days=1977` (2021-01..2026-06) |
| `~/runs/{A,B,C,VERIFY}_*/simulator` | preflight (maxFav3/RET2WF) | 2026-06-01 | 2026-07-12/13 | thí nghiệm label cũ |
| `~/team_{fail,entry,success}/simulator` | team harness | 2026-02-06/09 | (trước 09-01) | |
| `~/claudedata/.run/run226_cwd/storage` | WFO worker cwd | 2026-01-01 | 2026-07-15 | mep đúng seal |

**Đánh giá [ĐO]:** đây là tàn dư lịch sử của thời "2026 = VAL", không phải rò rỉ mới của holdout hiện hành. Nhưng
báo để owner biết "2026 đã từng được nhìn" ở tầng gate/selector trước khi seal (§0 rủi ro trong pre-reg draft).

---

## 2. ĐẦU VÀO 2026 — kiểm kê (mép cứng: 2026-07-01 00:00 GMT+7)

| đầu vào | phục vụ | mep | trạng thái |
|---|---|---|---|
| ticker 1m `kaggle_data_hpo/ticker_*.bin.gz` (2008 file) | giá vào/ra | 2026-07-01 | ✅ |
| OI `oi_percoin_20210101_to_20260701.bin.gz` (3,2 GB) | feature selector | 2026-07-01 | ✅ |
| gate `p15` `claudedata/wfo_gate_pred_2026_H1.csv` (260 183 dòng, sha256 `4cc62c14…`) | gate entry | 2026-07-01 | ✅ (đã sinh, P1 PASS; chưa nạp Aerospike) |
| **bins selector S1+net015** `predict_wf_20260101/20260401.bin` | `funding.bin` (thứ tự S1 + P(win) net015) | CHỈ tới 20251001 | 🔴 **THIẾU** |

### 2.1 Blocker (kế thừa `H1_HOLDOUT_PREP.md` §3/§5 — chưa gỡ)

1. 🔴 **`CLOSES_1H.bin` không có generator** (mọi file trên đĩa/git là READER) ⇒ không mở rộng `feat_v2`/`cand_dev`
   sang 2026 ⇒ không train S1 2026 ⇒ không có bins. Hai đường đi (user chọn): (a) Vision kline 1h; (b) gộp `kline_1m_opt` lên 1h.
2. 🔴 **Nguồn net015 `predwf_G015x26` không tái lập được** (fold 2026 đã xóa). Train mới = họ `G015_v2`, hiệu chuẩn KHÁC
   ⇒ bản lề `symbolPred <= 0.29` (ngưỡng TUYỆT ĐỐI) đổi nghĩa ⇒ `%STRONG` 2026 đổi vì lý do không liên quan 2026.
   Phải đo hiệu chuẩn (chỉ DEV) TRƯỚC.

### 2.2 Kế hoạch build (sau khi owner chốt 2 blocker) — DEV-train < mốc dự báo, không leak

1. Dựng `CLOSES_1H` 2026 + P2 byte-identical đoạn 2025-12.
2. `x1_ledger.py build` — `X1_CUTS` thêm `20260101 20260401`, `X1_LBGLOB='202[1-6]'` (bẫy glob).
3. `g72_train.py` (net015) train cutoff `< mốc`, predict OOS — đo hiệu chuẩn vs `G015x26/20251001` trước.
4. `x1_s1_rank.py` (S1) train cutoff `< mốc`, predict OOS.
5. `c4_build_map.py` → `predict_wf_20260101/20260401.bin`.
6. Kiểm leak: train max < dự báo min từng fold; OI `create_time` < mốc dự báo (`docs/ops/OI_FIX_LOG.md`).
7. P3/P4/P5 (pre-reg §3); P5 FAIL ⇒ DỪNG.

Chạy trên Kaggle hoặc Oracle theo luật (1 job nặng, ≤ 6 GB Python, `nice -n 10`). **KHÔNG chạy sim trên 2026,
KHÔNG tính PnL/metric 2026.**

### 2.3 Thời gian build (ước lượng [SUY LUẬN])

net015 45-feature 16-fold ~30 phút GPU / lâu hơn CPU; S1 + ledger/featv2 là bước nặng nhất (merge OI 138M rec ~23 GB RAM,
OOM trên Oracle ⇒ Kaggle 30 GB). Tổng toàn tuyến (sau khi có generator CLOSES_1H) ước **vài giờ** chạy nền, chưa kể
thời gian chốt 2 blocker. **Không khả thi trong một lượt cho tới khi owner chốt §2.1.**

---

## 3. VIỆC TREO (cần owner)

1. Chốt đường `CLOSES_1H` (a)/(b) — §2.1.1.
2. Chốt nguồn bins net015 (G015_v2 mới vs G015x26) sau phép đo hiệu chuẩn — §2.1.2.
3. Duyệt nháp pre-reg → chốt thành `PREREG_HOLDOUT_2026.md` (final).
4. (Chỉ sau khi 1–3 xong) mở seal `HOLDOUT_UNSEAL` một lần duy nhất.
