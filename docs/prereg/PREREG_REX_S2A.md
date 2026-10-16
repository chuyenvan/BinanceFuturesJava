# PRE-REG — REX Bước 2a: regime cho danh mục long top-k (hướng P3) (MASTER 2026-10-17)

**Bối cảnh:**
- Owner (10-17): giữ nguyên hệ cũ (shadow / go-live tách riêng), KHÔNG sửa logic hệ cũ. REX là hệ MỚI hoàn toàn.
- P1 (market-neutral) đã đóng. Bước này đi tiếp theo plan REX: Bước 2a xác định khi nào nên có mặt trên thị trường.

**Công khai mức nhiễm dữ liệu:**
- DEV đã bị xem ở S1, S1b và phần chẩn đoán.
- VAL 2025 đã nhìn 2 lần: một lần IC + top-10 long-only của C1, một lần market-neutral N7.
- Các luật regime dưới đây CHƯA được đo lần nào, trên bất kỳ kỳ nào.
- HO 2026 chưa chạm.

## Danh mục gốc (đóng băng, không tune)
- Dự báo walk-forward OOS `pred_s1_C7.parquet`.
- Long top-20 theo score, chia đều trọng số, 7 tranche (mỗi ngày mua mới 1/7 vốn, giữ 7 ngày).
- Lý do chọn C7 / top-20 trước khi đo regime: turnover thấp nhất, và excess ròng cao nhất trong phần chẩn đoán S1.
- Chi phí 0,10 %/chiều. Funding thật. Chỉ long, không short.

## Luật regime
Quyết định ở close ngày t, chỉ dùng dữ liệu ≤ t, áp cho ngày t+1:

| Mã | Ở trong thị trường khi |
|---|---|
| R0 | Luôn luôn (baseline) |
| R1 | Close BTC > MA50 của BTC |
| R2 | Breadth `br50` > 0,5 (hơn nửa universe nằm trên MA50) |
| R3 | `btc_mom28` > 0 |
| R4 | R1 VÀ R2 |
| R5 | Chỉ số alt EW (tích luỹ lợi suất trung bình của universe) > MA50 của chính nó |

**Cơ chế:**
- Trạng thái OUT nghĩa là đứng cash: danh mục về 0, lợi suất 0, không funding.
- Khi vào hoặc ra, tính phí trên toàn bộ phần thay đổi của Σ|Δw|.
- Các tranche vẫn được tính tiếp ở nền. Trọng số thực = W_t × e_t, với e_t ∈ {0, 1}.

**Benchmark bắt buộc** (để biết lãi đến từ chọn coin hay chỉ từ regime):
- (i) BTC buy & hold.
- (ii) BTC áp CÙNG luật regime, phí 0,06 %/chiều.
- (iii) Universe EW áp cùng luật regime.

## Thước đo (DEV = 2022–2024)
- Sharpe ròng tuyệt đối (ngày × √365), lãi/năm, maxDD, Calmar.
- Sharpe theo năm; % thời gian ở trong thị trường; số lần chuyển trạng thái.
- Chi phí ×2.
- Correlation với BTC; correlation tuần với crash-buy C2.

## Chọn và gate
**Luật thắng:** luật có Sharpe ròng DEV cao nhất trong R1–R5. R0 chỉ dùng để tham chiếu.

**Gate** (phải đạt tất cả):

| # | Điều kiện |
|---|---|
| G1 | Sharpe DEV ≥ 1,0 |
| G2 | Lãi ròng ≥ 0 ở cả 3 năm 2022, 2023, 2024 |
| G3 | maxDD DEV ≥ −30 % |
| G4 | Chi phí ×2: Sharpe DEV ≥ 0,7 |
| G5 | Sharpe DEV ≥ Sharpe của BTC áp cùng luật (benchmark ii). Nếu trượt, lãi chỉ đến từ regime, không cần chọn coin |
| G6 | VAL 2025, nhìn một lần: Sharpe ≥ 0,5 và lãi > 0 |

**Kết luận theo kết quả gate:**
- Nếu G1–G4 và G6 đạt nhưng G5 trượt: ghi nhận ứng viên "BTC + regime" là một hệ riêng. Hệ này cần pre-reg mới; không coi là REX GO.
- Nếu GO: sang Bước 2b (vào lệnh trên 1m) và Bước 3 (thoát lệnh), với danh mục và luật regime đóng băng.
