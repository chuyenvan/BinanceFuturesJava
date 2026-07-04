# TASK-126: Lọc ghost symbol quote-USDC (bug normalize dán USDT) — STUB

- **status:** todo (nguồn: TASK-125 validation WARN #1)
- Bug: logic `endsWith("USDT") ? s : s+"USDT"` dán nhầm hậu tố vào cặp quote-USDC →
  `1000PEPEUSDCUSDT, PENGUUSDCUSDT, WLDUSDCUSDT, WLFIUSDCUSDT` lọt pool funding (4/669 symbol, tác động nhỏ).
- Việc: tìm điểm normalize; loại cặp quote-USDC khỏi universe USDT-perp (hoặc Uni xác nhận cố ý);
  re-export funding bin ở vòng dataset kế (không re-run 3 vế hiện tại vì tác động 4/669 không đổi kết luận).
## Kết quả
<.>
