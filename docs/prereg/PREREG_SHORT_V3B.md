# PREREG_SHORT_V3B — STEER OWNER (06:32): CHỌN COIN "MẤT THANH KHOẢN" + GIỮ ĐỦ LÂU

Chốt: **2026-10-01**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này (commit TRƯỚC đo —
`docs/runbooks/AGENT_RUNBOOK.md` luật 2). Bổ sung cho `PREREG_SHORT_V3.md` (`06b8046d`) đã chạy xong.

> **NGUỒN (khai báo bắt buộc):** đây là **STEER của OWNER lúc 06:32**, KHÔNG phải thiết kế tự chọn.
> Nguyên văn: *"Chú ý cái rút ngắn giữ lệnh vì lý thuyết là chọn coin đã vào chu kì mất thanh khoản
> nó sẽ giảm đều"*.

## 0. Hiệu chỉnh so với V3 (điều chỉnh LUẬN ĐIỂM, không sửa số đã đo)

- **Luận điểm chính (owner):** chọn coin **ĐÃ VÀO CHU KÌ MẤT THANH KHOẢN** ⇒ nó **GIẢM ĐỀU** ⇒ phải
  **GIỮ ĐỦ LÂU** để ăn nhịp giảm đều.
- ⇒ **KHÔNG** lấy "rút ngắn thời gian giữ lệnh" làm cách NỀ FUNDING chính (kết quả V3 §1 đã cho thấy
  rút ngắn đều ÂM hơn — nay là **hệ quả phụ**, không phải biện pháp).
- ⇒ **NỀ FUNDING phải bằng CÁCH CHỌN** (coin short **không phải trả / được nhận** funding) + tránh
  mốc 8h **chỉ khi không phá edge**.
- Nếu vẫn thử "giữ ngắn" ⇒ **phải đo RIÊNG "giữ ngắn vs giữ đủ"** và báo **cả hai** (§4).

## 1. Ràng buộc (CỨNG, như V3)

Train CHỈ trên Kaggle · KHÔNG Java/sim trên Oracle · KHÔNG sửa `.java` · KHÔNG push dữ liệu ·
**DEV ≤ 2025-12-31** · output tool nhỏ · commit sớm + push. Vòng này **không train lại** (bins sẵn)
⇒ 0-sim; nếu buộc phải train (mục (c)) thì **DỪNG + báo BLOCKED**.

## 2. (a) FEATURE "ĐANG MẤT THANH KHOẢN" vào BƯỚC CHỌN COIN (khóa)

Nguồn feature: **cùng ma trận 45** đã train (`ds_feat15m` Tool1, cùng 40 cột `f0..f39`). **KHÔNG thêm
dữ liệu mới.** Dùng các cột "thanh khoản teo dần" (đọc tại `t`, **causal**):

| ký hiệu | cột | nghĩa |
|---|---|---|
| `vtrend` | `f27 volumeTrend` | xu hướng volume (≤0 = volume đang GIẢM) |
| `vz` | `f26 volumeZCoin` | volume so với chuẩn coin (≤0 = dưới trung bình) |
| `sqz` | `f31 atrSqueeze` | nén biên độ (≥0 = đang nén) |

**Bộ lọc khóa (causal, đặt TRƯỚC khi biết kết quả):**
- **L1a** = `vtrend ≤ 0` (thanh khoản đang teo).
- **L1b** = `vtrend ≤ 0` **VÀ** `vz ≤ 0` (teo + dưới chuẩn).
- **L1c** = `vtrend ≤ 0` **VÀ** `sqz ≥ 0` (teo + đang nén).
- Tổ hợp với nề funding causal **N1b** (rate kỳ settle kế tiếp ≥ 0) và regime **P2** (như V3).

**KHÔNG** dùng `maxAdv`/`maxFav`/`retEnd` để CHỌN (đó là tương lai — xem §3).

## 3. (b) ĐO "ĐỘ ĐỀU CỦA NHỊP GIẢM" (đường đi) — chỉ ĐO, không CHỌN

Từ `.pb` (cùng file, thêm cột `maxAdv_72h`), định nghĩa (khóa):
- `ratio = retEnd_72h / maxAdv_72h` ∈ [0,1] — gần 1 ⇒ giá đi xuống **đều**, giữ được gần đáy sâu nhất.
- `hoi = maxFav_72h` — độ hồi ngược tệ nhất trong cửa sổ (nhỏ ⇒ giảm êm).

**Báo cáo:** phân bố `ratio`, `hoi` (mean/median/p25/p75) cho từng cấu hình chọn.
**Kiểm định luận điểm owner (nhãn LOOKAHEAD — chỉ là CHẨN ĐOÁN, KHÔNG tính GO):** net của subset
`ratio ≥ 0,5` và `hoi ≤ 3 %` — nếu subset "giảm đều" có net > 0 thì luận điểm owner ĐÚNG về mặt
cơ chế, nhưng vẫn cần model **dự báo** được "giảm đều" tại `t` (chưa có ⇒ ghi vào "còn thiếu").

## 4. CÁCH NỀ FUNDING ĐƯỢC PHÉP (khóa) + "GIỮ NGẮN vs GIỮ ĐỦ"

- Nề funding **chính** = **LỌC THEO CÁCH CHỌN**: N1b (dấu funding kỳ settle kế tiếp, causal) × L1a/b/c.
- **Giữ đủ** `T = 72h` là **chính**. Bảng phụ **bắt buộc**: `T ∈ {4, 12, 24, 72}h` × {baseline, L1×N1b}
  để trả lời "rút ngắn có PHÁ EDGE không" — báo **cả hai**.
- N2b (tránh mốc settle bằng giờ vào lệnh) giữ nguyên như V3 (phụ).

## 5. Chỉ số + CI (khóa — như V3)

net TRƯỚC/SAU funding (funding **chính xác từng lệnh**), **winrate**, cut-rate, theo năm 2022–2025,
CI block-72h `NREP=2000 SEED=20260905` ×1,21, mean-seed 3 seed {42,7,13}, K=8, cắt `C ∈ {+20,+30,+50}%`.

## 6. LUẬT KẾT LUẬN (khóa — GIỮ NGUYÊN V3 §6)

**GO** chỉ khi ∃ cấu hình **tradeable** (không lookahead): **A** net sau funding > 0 **ngoài CI**
(raw & ×1,21) · **B** ≥3/4 năm dương · **C** winrate ≥ 55 % **và** ≥ baseline +5 điểm %.
Ngược lại **NO-GO/NULL**. `maxAdv/maxFav`-based chỉ là **chẩn đoán**, không tính GO.

## 7. VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Rút ngắn giữ lệnh làm cách nề funding CHÍNH | ⛔ BỎ | **STEER owner 06:32** (phá luận điểm "giảm đều"); chỉ để bảng đối chiếu §4 |
| 2 | Dùng `maxAdv/maxFav/retEnd` để CHỌN | ⛔ BỎ | tương lai ⇒ lookahead |
| 3 | (c) path-aware label + "mất thanh khoản" **train lại** | ⛔ BLOCKED | bins `pa` bị kernel xoá; train lại cần GPU Kaggle ⇒ vòng sau |
| 4 | Thêm dữ liệu mới / push dữ liệu | ⛔ BỎ | §1 |
| 5 | Feature OI (`oi_delta24h`) ghép local | ⛔ BỎ (vòng này) | ghép `merge_asof` 4 năm local nặng/thời gian; để vòng sau |

## 8. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_V3B.md` | file này (commit TRƯỚC đo) |
| `research/analysis/short_v3b_score.py` | chấm 0-sim: L1a/b/c × N1b × T + chẩn đoán `ratio`/`hoi` |
| `docs/result/RESULT_SHORT_V3B.md` (+`.json`) | kết quả + xác nhận/phủ định luận điểm owner |
