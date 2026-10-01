# PREREG_SHORT_V3C — SỬA NGƯỠNG LỌC "MẤT THANH KHOẢN" (theo ĐỊNH NGHĨA JAVA)

Chốt: **2026-10-01**, commit TRƯỚC khi chạy phép đo của V3C (`AGENT_RUNBOOK` luật 2).
Bổ sung `PREREG_SHORT_V3B.md` (`bc531673`) — **STEER owner 06:32**.

## 0. Vì sao có V3C (V3B L1 = VOID vì SAI DẤU, không do kết quả)

`PREREG_SHORT_V3B §2` khoá L1a `vtrend ≤ 0`, L1c `sqz ≥ 0`. Kiểm tra **định nghĩa trong code Java**
(nhánh STEER yêu cầu "đun số liệu có sẵn" ⇒ phải đọc đúng ngữ nghĩa cột TRƯỚC khi cắt ngưỡng):

- `FundingDataCollectionManager.java:433` → **`volumeTrend = avgVol_5 / avgVol_60`** ⇒ là **TỈ SỐ ~1.0**
  (>0 luôn khi có dữ liệu; NaN nếu thiếu) ⇒ `≤ 0` **không bao giờ đúng** ⇒ L1a/L1b/L1c(V3B) chọn **0 dòng**.
- `FundingDataCollectionManager.java:458` → **`atrSqueeze = atr_5 / atr_60`** ⇒ cũng là **TỈ SỐ ~1.0**
  ⇒ `sqz ≥ 0` **luôn đúng** ⇒ vô nghĩa.
- `volumeZCoin` (`getVolumeZScore(symbol,20)`) = **z-score 20 nến** ⇒ "dưới chuẩn" = **`vz < 0`**.

⇒ Ngưỡng V3B sai **do hiểu nhầm ngữ nghĩa**, KHÔNG do nhìn kết quả (chưa chạy V3B). V3C **sửa ngưỡng
theo ĐỊNH NGHĨA**, không sửa theo số. Kết quả L1(V3B) sẽ được báo là **VOID (kept≈0)** để minh bạch.

## 1. Ngưỡng LỌC đã sửa (khóa TRƯỚC khi đo)

| # | điều kiện (causal, đọc tại `t`) | nghĩa |
|---|---|---|
| **L1a′** | `vtrend < 1,0` | volume ngắn hạn < dài hạn ⇒ **thanh khoản đang teo** |
| **L1b′** | `vtrend < 1,0` **VÀ** `vz < 0` | teo **VÀ** volume dưới chuẩn 20 nến |
| **L1c′** | `vtrend < 1,0` **VÀ** `sqz < 1,0` | teo **VÀ** biên độ đang **nén** |

- Ngưỡng = **giá trị TRUNG TÍNH của định nghĩa** (1,0 cho tỉ số; 0 cho z-score) — KHÔNG tune.
- Tổ hợp với **N1b** (rate kỳ settle kế tiếp ≥ 0 — causal) làm cách **NỀ FUNDING BẰNG CÁCH CHỌN**.
- **Giữ đủ `T = 72h` là CHÍNH**; bảng đối chiếu `T ∈ {4, 24}h` bắt buộc (kiểm tra có phá edge không).

## 2. Giữ nguyên mọi thứ khác của V3/V3B

Chỉ số + CI (block-72h, NREP2000, SEED20260905, ×1,21), chi phí 0,112 %, 3 seed {42,7,13}, K=8,
cắt `C ∈ {+20,+30,+50}%`, funding **chính xác từng lệnh**, chẩn đoán `ratio`/`hoi` (lookahead, không
tính GO), và **LUẬT GO A/B/C** như `PREREG_SHORT_V3.md §6`.

## 3. Việc BỎ (ghi trước)

| # | việc | lý do |
|---|---|---|
| 1 | Tune ngưỡng L1 theo kết quả | cấm; ngưỡng lấy từ định nghĩa |
| 2 | Feature OI (`oi_delta24h`) | ghép local nặng; vòng sau |
| 3 | path-aware + mất thanh khoản (train lại) | bins `pa` mất ⇒ vòng sau (Kaggle) |
