# Phương pháp: chúng ta đang trộn HPO vào WFO — sửa thế nào (2026-08-15)

Câu hỏi user: "WFO mà sweep grid nhiều tham số — có đang làm cả phần HPO không? Bước nào không hợp lý? Có phương pháp tốt hơn?"

## Chẩn đoán (thẳng)
CÓ. Việc sweep grid `threshold × moveSL × lưới(5m/15m) × K` rồi đọc **ô tốt nhất theo total/t-stat GỘP trên toàn bộ 16–18 cửa sổ OOS** = chọn hyperparameter bằng chính tập OOS, rồi lại báo cáo hiệu năng OOS đó làm "kết quả walk-forward". OOS bị dùng 2 lần (chọn config + chấm điểm) → **selection bias / multiple-testing**. Con số headline (ô total cao nhất) là **trần lạc quan, KHÔNG phải kỳ vọng**. Mỗi trục thêm vào grid nhân thêm độ lạc quan. Đây chính là "làm phần HPO trên OOS" — và là lý do câu hỏi lõi project "edge có thực không" vẫn chưa trả lời được.

## 3 tầng tách đúng (đang gộp tầng 2 vào tầng 3)
1. Train model/feature — retrain expanding từng quý, leak-free sau khi sửa fold-0. **ĐANG ĐÚNG.**
2. Chọn knob (threshold/moveSL/K) — PHẢI chọn trên inner validation (dữ liệu TRƯỚC mỗi cửa sổ OOS). **ĐANG SAI: chọn trên toàn OOS.**
3. Báo cáo — chỉ tầng này mới được đọc PnL OOS, và chỉ khi tầng 2 không đụng vào.

Làm ĐÚNG (giữ, đừng tự phủ nhận sạch): expanding retrain, sửa leak, bản năng chọn vùng phẳng thay vì đỉnh nhọn (đã cảnh báo loại B03sl08 total 20k/t=1.64). Vấn đề khu trú ở **cách rút con số cuối từ grid**, không phải toàn bộ WFO.

## Giải pháp (xếp theo chi phí/lợi ích)
- **(a) Tail holdout — KHUYẾN NGHỊ.** Khóa config trên ≤2024/2025, test lạnh 2025H2–2026 (chưa từng dùng chọn config). Rẻ, 1 con số honest, khớp go-live + 2026.
  - MẤU CHỐT: G015-K5 (15m/thr0.015/moveSL0.05/K5) đã freeze trên ≤2025 → **2026 hiện là holdout SẠCH**. Re-sweep grid trên 2026 = ĐỐT mất holdout sạch duy nhất. → Khi ticker 2026 live: chạy ĐÚNG 1 config canonical như cold test (drive_exp18, WFO_MAX_OOS_DATE=20261001), KHÔNG đổi tham số theo kết quả 2026. Giữ edge → bằng chứng go-live mạnh; vỡ → edge là artifact regime/selection.
- **(b) Nested/anchored WFO cho knob** — chuẩn vàng nhưng đắt + high-variance với chỉ 16–18 cửa sổ (bước inner-select cũng có thể chọn nhầm). Chỉ làm nếu (a) tích cực và cần con số kỳ vọng chặt.
- **(c) Đổi tiêu chí chọn ô**: 1-SE rule / best-worst-window / tâm vùng phẳng thay vì max-total. Miễn phí, làm ngay trên grid đã có.
- **(d) Deflated Sharpe / multiplicity correction**: deflate t-stat/Sharpe theo ~18 ô đã thử. t=2.5 sau deflate tụt đáng kể → biết edge còn sống sau khi trừ may mắn dò grid.

## Nguyên tắc thiết kế
Selector (ML) = giả thuyết edge; threshold/moveSL/K = knob execution/risk. **KHÔNG co-optimize ML và knob trên cùng một OOS.** Freeze selector từ validation của nó → set knob từ validation nhỏ → mới test.

## Việc cần đổi
Giữ config đã freeze; coi 2026 là cold holdout (KHÔNG re-tune); hạ "ô tốt nhất theo OOS gộp" khỏi vai trò headline; bổ sung lăng kính deflated-Sharpe/worst-window lên grid cũ.

## Cross-ref hạ tầng (2026-08-15)
Cloud container mới CHẶN outbound port 22 → SSH Oracle phải qua Windows git-ssh (desktop-commander start_process): `& "C:\Program Files\Git\usr\bin\ssh.exe" -p 22 -o PubkeyAcceptedAlgorithms=+ssh-rsa -o IdentitiesOnly=yes -i "C:\Users\pc\.ssh\id_rsa_chuyennd_openssh" ubuntu@161.118.212.3 "<bash>"`. Lệnh phức tạp: base64 trong PowerShell → `echo <b64> | base64 -d | bash`. Reader `.gz` OK (KaggleDataLoader có gzFile+GZIPInputStream). Ticker 2026: tar `ticker_all.tar` (2050 file .bin.gz) đang lên qua hpo-ticker-daily v8 + slug fresh hpo-ticker-tar; run_worker glob `**/ticker_all.tar`.
