# BUG lưới 5m + threshold tương quan cho net-all — 2026-08-18

## 1. BUG: so sánh 5m vs 15m bị lệch window (user phát hiện qua trade count)
Triệu chứng user bắt: old@15m 2128 trades > old@5m 1820 trades — VÔ LÝ, lưới 5m cadence dày hơn phải NHIỀU lệnh hơn.

Nguyên nhân:
- predwf_5m015f09 chỉ có **10 predict_wf bin** (20230101..20250401 = 2023Q1..2025Q2).
- predwf_G015x26e có **18 bin** (2022Q1..2026Q2).
- Report của CẢ HAI đều render đủ 18 window (win0..win17) theo lịch WFO cố định; win nào 5m KHÔNG có prediction
  thì trades=0, pnl=0. Với old5m: win0-3=0 và win14-17=0; chỉ **win4-13** có data thật.
- Aggregator slice **win4-15** → với 5m gộp thêm win14-15 (rỗng) làm 0, còn 15m win14-15 là data thật.
  → so index-với-index nhưng 5m thiếu 2 window + bị 2 số 0 kéo tụt. KHÔNG apples-to-apples.

## 2. SỬA: so trên vùng chung cả 2 lưới đều có prediction = win4-13 (2023Q1..2025Q2), bỏ window rỗng
| nhánh (win4-13) | TOTAL | trades | worstDD% | Calmar | pos% | Sharpe | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| **old@5m (max)** | **12,659.7** | **1820** | 16.9 | 1.234 | 90% | 1.243 | 14.90 |
| old@15m (max) | 8,196.3 | 1327 | 19.1 | 1.178 | 90% | 1.027 | 11.42 |
| net-all@5m (th0.008) | 4,492.3 | 200 | 1.8 | 1.331 | 100% | 1.506 | ∞ |
| net-all@15m (th0.008) | 3,964.2 | 164 | 2.3 | 1.234 | 100% | 1.599 | ∞ |

Kết luận đảo chiều so với bảng win4-15 cũ:
- **old@5m 1820 trades > old@15m 1327** — 5m nhiều lệnh hơn, đúng trực giác user. Số "15m>5m" cũ là artifact window.
- Trên cùng 10 window, **5m THẮNG 15m mọi mặt**: total 12,660>8,196, Sharpe 1.24>1.03, DD 16.9<19.1.
- Verdict cũ "15m gom total nhiều hơn" (track2_gate_ab_results) SAI — đã sửa ở đây.
- off (8019 trades) chạy bằng predwf 15m → chỉ là baseline của 15m, KHÔNG so được với nhánh 5m.

## 3. Threshold 0.008 CỨNG cho net-all là sai bản chất (user yêu cầu chỉ số tương quan)
Phân phối gate pred (cột predReturn15M, n=2.72M mỗi label):
- **MAX(oldbasket):** mean 0.00610, std 0.00259 → 0.008 ở percentile **83%** → GO **17.0%** số phút.
- **NET(retall15m):** mean **−0.00006** (~0), std **0.00099** → 0.008 ở ~8σ đuôi → GO chỉ **0.11%**.
→ Net chỉ 200 lệnh KHÔNG phải vì kém, mà vì 0.008 với net = "chỉ bắn outlier cực đoan". So cùng 0.008 = vô nghĩa.
Threshold tương quan (matched pass-rate): τ_net(17%)=0.000075 ; net-scale grid 0.00005–0.0007.

## 4. SWEEP net-all@5m HOÀN CHỈNH (win4-13, đủ 8 threshold)
| th | net GO% | trades | TOTAL | worstDD% | Calmar | pos% | Sharpe | PF |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.00005 | 20.8 | 6717 | 1,459 | 39.9 | 0.379 | 60% | 0.028 | 1.07 |
| 0.000075 | 17.0 | 6435 | 1,531 | 42.3 | 0.387 | 70% | 0.030 | 1.08 |
| 0.0001 | 14.0 | 6221 | 5,637 | 42.9 | 0.386 | 70% | 0.118 | 1.35 |
| 0.00015 | 10.1 | 5520 | 7,482 | 33.6 | 0.446 | 70% | 0.201 | 1.60 |
| 0.0002 | 7.7 | 5037 | 10,451 | 29.4 | 0.550 | 70% | 0.341 | 2.18 |
| **0.0003** | 5.2 | 4129 | **11,475** | 29.0 | 0.672 | 80% | 0.433 | 2.79 |
| 0.0005 | 3.0 | 2836 | 9,205 | 28.8 | 0.731 | 90% | 0.397 | 2.57 |
| 0.0007 | 2.0 | 2309 | 10,225 | 21.0 | 1.053 | 90% | **0.810** | 5.07 |
| 0.008 | 0.11 | 200 | 4,492 | 1.8 | 1.331 | 100% | 1.506 | ∞ |
| **old@5m (max)** | — | 1820 | **12,660** | 16.9 | 1.234 | 90% | **1.243** | 14.90 |

Đường cong: siết net → total đỉnh **11,475 @ th0.0003**; quality (Sharpe/PF) tăng dần về đuôi (0.0007 Sharpe 0.81/PF 5.07
là điểm tradeable tốt nhất), rồi total sụp về 0.008 (200 lệnh). 2 điểm 0.0005/0.0007 chạy lại được sau khi user dọn
Kaggle (403 lúc trước = rate-limit tạo dataset tạm thời, KHÔNG phải hết compute quota).

## VERDICT net-all (ĐÓNG — dữ liệu đầy đủ)
- **Hệ số gate tốt nhất cho net-all = 0.0003** (total 11,475) hoặc 0.0007 nếu ưu tiên quality (Sharpe 0.81/PF 5.07).
- **NHƯNG net-all KHÔNG BAO GIỜ vượt old@5m (max) ở BẤT KỲ threshold nào:** total tốt nhất 11,475<12,660;
  Sharpe tradeable tốt nhất 0.81<1.24; DD tốt nhất 21%>16.9; PF tốt nhất 5.07<14.90.
- Net chỉ "thắng" Sharpe/DD ở đuôi cực chặt 0.008 (200 lệnh) nơi total sụp còn 35% của old = cherry-pick, không dùng được.
- **KHÔNG đổi gate live. Giữ max/oldbasket.** Net-all là profile kém hơn ở mọi volume thực dụng.
- Workers ĐÃ restore SIM_MIN_MOMENTUM_15M=0.008 (TOPK=5, moveSL=0.05 nguyên vẹn).

## Ghi chú hạ tầng Kaggle (fix cho lần sau)
- Driver drive_gate_ab_5m.sh tạo 1 dataset 2.4GB MỚI mỗi threshold — dataset GIỐNG HỆT nhau (threshold là env
  worker, không nằm trong dataset). Nên: **build 1 dataset dùng chung, mỗi threshold chỉ đổi env + re-push kernel.**
  Tránh throttle create-dataset + phí storage. CHƯA patch (để lần sweep sau nếu cần).
- Kaggle CLI/API KHÔNG xoá được dataset (chỉ web UI). Reclaim quota: xoá web, hoặc version-đè xuống file rỗng.

## Files
- agg_win.py; gate_dist.py; masters: gate_ab_net_mpr_master.sh, gate_ab_net_grid2_master.sh, net_finish_master.sh
- reports: /home/ubuntu/claudedata/sweep/REPORT_gateab_netall5m_*.md
