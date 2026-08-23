# WFO — CANONICAL CONFIG (đóng băng 2026-08-15) — nguồn sự thật cho các bước sau

Doc này chốt cấu hình đã chọn để **các bước sau (Phase 4 regime/holdout) không bị lệch**. Mọi run mới mặc định dùng cấu hình này trừ khi cố ý đổi.

## ✅ CẤU HÌNH ĐÓNG BĂNG
| Thành phần | Giá trị | Đặt ở đâu |
|---|---|---|
| **Lưới (grid)** | **15m** (train15→pred15, TRACKC) | model kernel `chuyendinh/selector-15mtr-pred15-net015-gpu`; predwf = `predwf_G015` |
| **Threshold (NET_THR)** | **0.015** | model net015 |
| **moveSL** (`SIM_RATE_PROFIT_STOP_MARKET`) | **0.05** | run_worker.py env + config.properties |
| **rank-K** (`SELECTOR_RANK_TOPK`) | **5** | run_worker.py env + config.properties |
| Đòn bẩy | 1x (`LEVERAGE_ORDER=1`) | config.properties |
| Vốn | 35,000 (`CAPITAL_START`) | config.properties |
| Phí | 0.1%/lệnh (`RATE_FEE=0.001`) | config.properties |
| Funding | ON (`SIM_APPLY_FUNDING=true`) | run_worker.py |
| **WFO_MAX_OOS_DATE** | **20261001** (đã bump để nhận 2026) | run_worker.py |

- run_worker.py (5 worker) canonical: K5 + moveSL0.05 + MAX_OOS 20261001, **md5 = 0aebaf049158** (`.sl03bak` = canonical). Bản gốc K8/moveSL0.03/MAX_OOS20260101 ở `run_worker.py.orig_k8sl03`.

## ✅ KẾT QUẢ CANONICAL — G015-K5 (16 window 2022–2025)
total **18,528** (+53%/35k/4yr) · lệnh **3,058** (ít nhất) · quý dương 14/16 · worst DD **19.1%** vốn · margin-call **0/16**. Robust nhất bộ.

## K-SWEEP — chốt rank-K (moveSL0.05, thr015)
### Lưới 15m (16 window, report đầy đủ)
| K | total | lệnh | quý dương | worst DD %vốn |
|---|------:|----:|:---:|---:|
| **K5** | 18,440 | 3,058 | **14/16** | **19.1%** |
| K8 | **20,803** | 3,828 | 13/16 | 25.7% |
| K12 | 19,868 | 4,634 | 12/16 | 29.4% |
### Lưới 5m (16 window) — đối chứng
| K | total | lệnh | quý dương | worst DD %vốn |
|---|------:|----:|:---:|---:|
| K5 | 22,171 | 3,905 | 15/16 | 24.0% |
| K8 | **23,513** | 4,774 | 14/16 | 28.8% |
| K20 | 18,136 | 6,148 | 11/16 | 34.5% |

**Kết luận K (cả 2 lưới cùng shape):** total đỉnh ở **K8**; ổn định + DD + turnover tốt nhất ở **K5** (đơn điệu: K↑→quý dương↓, DD↑, lệnh↑). K12/K20 dominated (pha loãng vào pick conviction thấp). → **Sweet spot K5–K8.** Canonical = **K5** (robust, chịu slippage/compound tốt nhất); K8 nếu đấu gross ở phí lý tưởng.

## An toàn 1x (validate bằng sim)
margin-call check (Binance cross 1x, equity≤0.5% notional): **0/16 window** mọi config; worst DD 19–29% vốn. → 1x + chia nhiều coin: cháy chỉ khi hệ thống sập. maxDD-như-cổng-cháy KHÔNG phải ràng buộc.

## Hàm mục tiêu (khung cho bước sau)
Max terminal wealth, net phí thật, tính compounding drag. maxDD quan trọng qua compounding + turnover/slippage (KHÔNG phải ruin). rank-K: edge dồn top ~5–8, nống K = thêm rác.

## ⚠️ RỦI RO LỚN NHẤT (chưa giải quyết)
Edge dồn **2–3 quý pump** (win8=2024Q1, win15=2025Q4). Câu hỏi sống-còn: **kỹ năng chọn coin hay chỉ beta mùa pump?** → Regime/outlier analysis là ưu tiên #1.

## 🔧 TRẠNG THÁI 2026 (chẩn đoán XONG, thực thi CHỜ)
- **Cap đã fix:** `WFO_MAX_OOS_DATE=20260101→20261001` trong run_worker (canonical). Worker giờ THỬ fold 2026.
- **Nhưng vẫn thiếu 2026** vì DATA: A6 log worker cho thấy **market+funding data DỪNG ở 2026-06-07** (`range=[...1780794600000]`, coverage 0.97 — A6 KHÔNG block, chỉ WARN). Hệ quả: win17(2026Q2, cần tới 2026-07-01) không tạo được; win16(2026Q1) fail do gap coverage cụm ở vùng 2026.
- **Pipeline data (user xác nhận):** ticker(kline) từ **242** → local (kline_1m_opt local ĐÃ có tới 2026-08-13). `market_data_object` dựng bằng **`ExportMarketData2File`** xuất từ ticker. Set local hiện copy từ 226 (migrate_226_oracle.sh) nên stale 2026-06-07.
- **FIX = chạy lại `ExportMarketData2File`** (local, từ kline 2026-08 đã có) để tái tạo `market_data_object` phủ tới 2026-08 + refresh funding set tương tự → rồi re-fanout canonical G015-K5 → 2026Q1/Q2 vào.
- **CHẶN:** lệnh/args chính xác của `ExportMarketData2File` chưa rõ (không có trong ~/.bash_history, không trong binance-futures-wfo.jar). **Cần user cung cấp lệnh chạy** (hoặc tự chạy). Cũng cần xác nhận funding set refresh thế nào.

## Bước tiếp (Phase 4)
1. ✅ Config đóng băng + G015-K5 + K-sweep {5,8,12} 2 lưới — XONG.
2. **2026 data fix:** chạy ExportMarketData2File rebuild market_data_object→2026-08 + funding → re-fanout. (chờ lệnh từ user)
3. **Regime/outlier analysis** (ưu tiên #1): tách PnL theo mùa BTC + bỏ win8/win15 xem edge còn lại.
4. Holdout 2024H2+ OOS thật; sign-test paired.

## Con trỏ vận hành
- SSH: `ssh -i ~/.ssh/id_rsa_chuyennd_openssh -o PubkeyAcceptedAlgorithms=+ssh-rsa -o IdentitiesOnly=yes ubuntu@161.118.212.3`.
- Fanout 1 tag (workers đã canonical K5): `drive_exp18.sh <TAG> 0`, predwf hardlink từ predwf_G015; `cp $OWD/docs/reports/wfo_strategy_window.md sweep/REPORT_<tag>.md`. Cột report: OOS_pnl, trades, ddPct%, calmar, marginCall.
- **RAM 23G: KHÔNG chạy 2 job Java Xmx nặng cùng lúc** (ExportWfoDataset Xmx18g / ExportMarketData / market rebuild). Serial.
- Kaggle quota: `wfo-ds-*` là dataset tạm mỗi fanout, xóa an toàn sau khi có REPORT/DONE (trừ tag đang chạy). **`hpo-ticker-daily` + `java-run-lc` là worker source — ĐỪNG xóa.**
- Fold 2026 fail-chậm kéo poll→90 (+~15'/run). Khi chưa fix data 2026, có thể hạ MAX_OOS về 20260101 tạm để run nhanh.
