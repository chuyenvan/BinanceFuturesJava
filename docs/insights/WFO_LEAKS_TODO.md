# WFO — các LEAK/rủi ro toàn vẹn đã phát hiện (NOTE để xử lý sau, KHÔNG quên)

> Ghi lại 2026-06-28 khi rà luồng dữ liệu WFO. Đây là các điểm rủi ro tính-toàn-vẹn/leak phát hiện
> trong lúc xây framework. CHƯA xử lý — note để cải tiến sau (Uni đồng ý làm v1 trước, sai lệch cùng sửa).

## ⚠️ L0 — RANH GIỚI DATASET theo LOẠI WFO (Uni chỉ ra 2026-06-28, QUAN TRỌNG NHẤT)
**Uni hỏi: "sao lại export pred? WFO phải dùng pred MỚI chứ".** Đúng — phơi bày khái niệm sai trong v1:
`WfoDataset` (3 khối: market + `ai_pred_market_full_basket_v2` + funding) KHÔNG phải dataset CHUNG cho mọi WFO.

- **Strategy WFO (loại 1):** model market ĐỨNG YÊN, chỉ vặn 18 gene. → pred (`ai_pred_market_full_basket_v2`)
  là INPUT BẤT BIẾN hợp lệ → đưa vào file offline ĐÚNG. (dataset hiện tại đúng CHO loại 1.)
- **Model WFO (loại 2):** mỗi fold TRAIN model mới → PREDICT mới trên OOS. → pred là OUTPUT sinh trong fold,
  TUYỆT ĐỐI KHÔNG đọc từ set cũ. Dùng pred cũ = mất sạch ý nghĩa walk-forward (đo lại chính model cũ).
  → dataset offline cho loại 2 phải là **features + label** (input để train), KHÔNG phải pred.

**Hệ quả sửa thiết kế:** `WfoDataset` hiện tại = "StrategyWfoDataset" (riêng loại 1). Mỗi loại WFO có dataset
offline RIÊNG (khác khối dữ liệu). Đổi tên/ghi rõ ngữ nghĩa để không ai hiểu nhầm pred này dùng cho model WFO.
KHÔNG để 1 class WfoDataset gánh cả 2 nghĩa. [đã đổi tên trong v1 — xem WFO_FRAMEWORK_DESIGN mục 1.]


## L1 — Label leakage quanh cutoff (embargo) — TINH VI, ưu tiên cao
- WFOGateRunner: train `df.timestamp < cutoff`. Nhưng LABEL = `basketMaxGain` nhìn 15m TƯƠNG LAI.
- → phút cuối train (sát cutoff) có label nhìn sang [cutoff, cutoff+15m) = vùng OOS → LEAK nhẹ.
- Chuẩn quant: **purge/embargo** vùng đệm = độ dài label-horizon quanh cutoff (bỏ các sample train có
  label-window chạm OOS). Ở đây embargo ≈ 15 phút (horizon label).
- Tác động: nhỏ (chỉ vài sample sát biên) nhưng đúng nguyên tắc Uni "lệch input → cả mớ sau vô nghĩa".
- FIX đề xuất: trong train_gate_fold, lọc `timestamp < cutoff - LABEL_HORIZON_MS`.

## L2 — Feature order drift (copy tay V3FULL 2 nơi)
- Thứ tự 33 feature V3FULL khóa cứng ở `OnnxInferenceManager.extractFeaturesV3Full` (Java) VÀ copy tay
  trong `train_gate_fold.py` (Python). Sửa 1 nơi quên nơi kia → model học sai map feature.
- FIX đề xuất: SINH thứ tự feature từ 1 nguồn (Java in ra file `feature_order.json`), Python đọc file đó.

## L3 — Snapshot nguồn lệch giữa máy/lần (data drift)
- Replay feature từ market_data; nếu Oracle replay bản hôm nay, Kaggle bản copy cũ → feature khác.
- Đã từng dính: "stale Kaggle ff/OI source mismatch" (2h hang).
- FIX (ĐÃ đưa vào v1): manifest md5 + version cho mọi dataset offline; mọi node fail-fast nếu md5 lệch.

## L4 — Provenance pred set ghép (predRisk4H từ set cũ)
- WFOGateRunner giữ predRisk4H từ `ai_pred_market_full_basket_v2` (set cũ), chỉ thay predReturn15M.
- Đúng cho thí nghiệm isolate biến, NHƯNG pred set OOS ghép từ {15M mới + risk4H cũ} → phải GHI RÕ
  provenance trong manifest pred set, tránh sau này hiểu nhầm là pred mới hoàn toàn.
- FIX (ĐÃ đưa vào v1): manifest pred set ghi rõ nguồn từng cột.

## L5 — featChecksum chỉ in, chưa CHẶN
- WFOGateRunner in featChecksum để so 2 lần chạy thủ công. Chưa tự động chặn nếu lệch.
- FIX đề xuất: ghi featChecksum vào manifest; lần chạy sau so tự động, lệch → fail-fast.
