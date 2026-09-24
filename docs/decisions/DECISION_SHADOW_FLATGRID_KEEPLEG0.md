# DECISION — Chuyển shadow production sang FLATGRID KEEPLEG0 (2026-09-19)

## Quyết định
Ngày **2026-09-19**, user **CHỐT** chuyển cấu hình chạy của **shadow C3 production** (paper,
`SHADOW_NO_PUSH=true`) từ **T170 gốc** sang biến thể **FLATGRID KEEPLEG0**:

| DCA param | T170 (trước) | KEEPLEG0 (sau) |
|---|---|---|
| `DCA_GRID_WEIGHTS` | 1,1,3,8 | **1,1,1,1** |
| `DCA_GRID_SCALE` | 19.5 | **6.0** |

Mọi tham số khác của T170 **GIỮ NGUYÊN**: `SIM_GATE_DYN_SCALE=1.70`, `SELECTOR_ONLY_ENTRY=0`,
`DCA_GRID_ENABLED=true`, `SIM_LOSER_TIME_STOP_HOURS=168`, `SHADOW_NO_PUSH=true`,
`LIVE_PROFILE=c3_shadow`, `PAPER_EQUITY=35000`, `CAPITAL_START=35000`.

Nguồn sự thật cho KEEPLEG0: **`profiles/t170_flat_keepleg0.properties`**. `diff` với
`profiles/x1_gs_t170.properties` xác nhận đúng **2 dòng** khác nhau (WEIGHTS + SCALE), không đổi
LEVELS/LEGS/FIX_B*/gate/bất kỳ key nào khác. Chi tiết cơ học + số liệu:
`docs/result/RESULT_FLATGRID.md`, `docs/prereg/PREREG_FLATGRID.md`.

## ĐÂY LÀ QUYẾT ĐỊNH KHẨU VỊ RỦI RO CÓ Ý THỨC — KHÔNG PHẢI LỖI BỎ SÓT RÀNG BUỘC
Nghiên cứu FLATGRID (`docs/result/RESULT_FLATGRID.md` mục 6) ra verdict: **KEEPLEG0 KHÔNG đạt luật
thắng** (0/2 rate ngoài CI hướng tốt) và **FAIL ràng buộc cứng UW toàn kỳ (147 > 120 ngày)**.
Theo luật incumbent, T170 lẽ ra **giữ nguyên**.

User quyết định **vẫn chuyển** shadow sang KEEPLEG0. Điều này **CỐ Ý NỚI hard-constraint
underwater (UW) từ 120 lên >= 147 ngày** (đo toàn kỳ) để đổi lấy việc **hạ trần tập trung rủi
ro 1 coin**. Đây là lựa chọn khẩu vị rủi ro, ghi nhận rõ ràng ở đây để **không bị hiểu nhầm là
quên/bỏ sót ràng buộc UW** trong các review sau.

## Đánh đổi (số liệu từ docs/result/RESULT_FLATGRID.md mục 6, backtest toàn kỳ)
| Chỉ số | T170 | KEEPLEG0 | Ghi chú |
|---|---|---|---|
| CAGR | 29.27% | **27.14%** | **-2.13 pp** (giá phải trả) |
| Equity cuối | 111,070 | 103,083 | -7.19% |
| UW toàn kỳ | 92 ngày | **147 ngày** | +55 ngày; **vượt cap 120** (đây là ràng buộc được nới) |
| maxDD toàn kỳ | -11.84% | -11.21% | **tốt hơn** (giá không nằm ở độ sâu DD mà ở thời gian dưới nước) |
| Chất lượng lệnh | — | không đổi | 0/3 rate khác biệt ngoài CI |
| **Trần tập trung 1 coin (lý thuyết)** | 58.5% | **18.0%** | **cái đổi lấy** — giảm 3.25 lần |
| Max % equity 1 coin (đo thực) | 8.71% | 6.98% | |
| Rủi ro entry đầu (margin bậc 0) | 4.544% | 4.549% | không đổi |

Cơ chế cái giá: bậc DCA nặng (w=3/w=8) của T170 chính là thứ đã "cứu" cụm FTT 11/2022
(+353 → thành -1,261 khi làm phẳng), kéo thời gian dưới nước cụm đó 63 → 147 ngày.

## CẢNH BÁO cấu hình (đã tránh)
Phải đổi **CẢ HAI** dòng. Chỉ đổi `DCA_GRID_WEIGHTS=1,1,1,1` mà giữ `DCA_GRID_SCALE=19.5` sẽ
thành biến thể **KEEPSCALE**: `sum(w)` ở mẫu giảm 13→4 ⇒ **phóng to mọi lệnh 3.25 lần**, trần
tập trung **vẫn 58.5%** (không giảm gì), và FAIL ràng buộc cứng 3/5 năm. env.sh đã set đồng thời
`DCA_GRID_SCALE=6.0`.

## Triển khai
- Live: `/home/ubuntu/shadow_c3/app/conf/env.sh` (backup trước khi sửa:
  `env.sh.bak_20260919_pre_flatgrid`).
- Reference version-control: `deploy/shadow_c3/env.sh` (cập nhật khớp).
- Restart qua watchdog systemd (`shadow-c3.service`), đã verify `/proc/<pid>/environ`:
  `DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6.0`, `SIM_GATE_DYN_SCALE=1.70`,
  `SHADOW_NO_PUSH=true`, process active + tick theo lưới 15m, `createOrder=0`.

## Kỷ luật giữ nguyên
Không push. Không chạm 242. Không đổi holdout 2026. Không tắt `SHADOW_NO_PUSH`. Đây chỉ đổi
cấu hình chạy của **shadow paper**; incumbent nghiên cứu (T170) và các luật đánh giá không đổi.
