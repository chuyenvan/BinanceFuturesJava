# ADR-0003: Genome HPO gồm 13 gene

- **Ngày:** 2026-06-09
- **Trạng thái:** ⛔ đã thay thế bởi [ADR-0012](0012-genome-18-gene-off-cung-cum-C.md) (genome thật = 18 gene, gồm cả tầng trailing+budget mà ADR này thiếu; OFF cứng 9 gene cụm C). Giữ file để truy vết lịch sử 13-gene; KHÔNG dùng làm genome hiện hành.
- **Bối cảnh phát sinh:** chốt layout genome để `buildTaskId` băm đủ gene và để bump CONFIG_VERSION đúng lúc. Nguồn xác minh: `src/main/java/com/binance/chuyennd/ai_ml/hpo/master/RunHpoMaster_Distributed.java`.

## Vấn đề

Cần một danh sách gene CHÍNH THỨC, đúng thứ tự, để: (a) không ai thêm/bớt gene mà quên cập nhật `buildTaskId` (trùng key = HPO vô nghĩa), (b) biết khi nào phải bump CONFIG_VERSION.

## Các lựa chọn đã cân nhắc

(Không phải lựa chọn nhị phân — đây là ghi nhận layout đang dùng.) Lựa chọn liên quan đã thực hiện: **bỏ gene `MIN_MOMENTUM_24H`** (14 → 13 gene) khi gỡ hẳn `predReturn24H`/MOM24 khỏi hệ.

## Quyết định

Genome = **13 gene** `DoubleChromosome`, định nghĩa tại `RunHpoMaster_Distributed.java:89-107`, gán sang task ở `:163-175`, in kết quả ở `:245-257`. Theo đúng index:

| # | Tên (theo log :245-257) | Range (`:91-107`) | Field task (`:163-175`) | Nhóm |
|---|---|---|---|---|
| 0 | MS_UP_BIG_THRES | 0.010–0.040 | `msUpBig` | market-status |
| 1 | MS_DOWN_BIG_AVG | -0.100–-0.025 | `msDownBig` | market-status |
| 2 | MS_DOWN_SMALL_AVG_OR_15M | -0.030–-0.010 | `msSmall` | market-status |
| 3 | AI_MAX_THRES / PREDICT_MAX_THRES | 0.10–0.25 | `aiMaxThres` | AI filter |
| 4 | MIN_MOMENTUM_15M | 0.010–0.035 | `aiMin15M` | AI filter |
| 5 | HARD_RISK_LIMIT_4H | -0.25–-0.05 | `aiRisk4H` | AI filter (risk) |
| 6 | AI_DYNAMIC_MULTIPLIER | 1.0–2.0 | `aiDynMul` | AI dynamic |
| 7 | AI_DYNAMIC_MIN | 0.1–0.5 | `aiDynMin` | AI dynamic |
| 8 | AI_DYNAMIC_MAX | 1.5–3.0 | `aiDynMax` | AI dynamic |
| 9 | DCA_LOSS_BIG_DOWN | -0.30–-0.08 | `dcaLossBigDown` | DCA |
| 10 | DCA_LOSS_BIG_UP | -0.40–-0.10 | `dcaLossBigUp` | DCA |
| 11 | DCA_TIME_BIG_DOWN | 3–20 (phút) | `dcaTimeBigDown` | DCA |
| 12 | DCA_TIME_BIG_Up | 5–30 (phút) | `dcaTimeBigUp` | DCA |

Ý nghĩa từng gene đọc theo TÊN + nhóm; chi tiết hành vi chính xác của gene 2 (`MS_DOWN_SMALL_AVG_OR_15M`) cần soi `MarketBigChangeDetector`/`Configs` nếu dùng để diễn giải sâu: `<CẦN XÁC NHẬN: ngữ nghĩa chính xác MS_DOWN_SMALL_AVG_OR_15M nếu cần>`.

**Trước đây 14 gene** — đã **bỏ `MIN_MOMENTUM_24H`** (v5 → v6), theo comment `RunHpoMaster_Distributed.java:41-42`, đồng bộ với việc gỡ hẳn `predReturn24H` + nhánh MOM24 khỏi runtime/filter/config/train (ablation cho thấy nhánh predReturn24H không bao giờ kích hoạt).

## LÝ DO

- 13 gene chia 4 nhóm (market-status 0–2, AI filter/dynamic 3–8, DCA 9–12) — phục vụ Bước 4 roadmap (tối ưu THEO NHÓM tuần tự, khóa dần) và sensitivity analysis (nghi nhóm `AI_DYNAMIC_*` phẳng).
- Bỏ `MIN_MOMENTUM_24H` vì feature 24H đã chứng minh vô dụng (ablation A=C) → giữ lại chỉ làm loãng không gian tìm kiếm.
- **Ràng buộc cứng:** thêm/bớt/đổi thứ tự gene BẮT BUỘC (a) cập nhật `eval()` mapping (`:163-175`), (b) cập nhật `buildTaskId` (`:229`) để key băm đủ gene — quên = các cá thể khác nhau trùng key = HPO vô nghĩa; (c) bump CONFIG_VERSION (xem [ADR-0004](0004-ky-luat-config-version.md)).

## Hệ quả

- Mốc "14 gene" trong `docs/ROADMAP.md` Bước 4 đã CŨ (thực tế 13) — chỉ báo, không sửa roadmap ở ADR.
- Mọi tài liệu/HPO nói "14 gene" cần đọc lại theo 13.
