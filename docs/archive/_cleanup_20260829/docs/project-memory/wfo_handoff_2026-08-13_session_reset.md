# HANDOFF — reset session (2026-08-13) — ĐỌC ĐẦU TIÊN

Session cũ bẩn context + kẹt kết nối. Doc này để session MỚI nối mạch không phải dò lại. Nguồn chi tiết: `claude/wfo_ops_runbook_2026-08-13.md` (luồng vận hành) + `claude/wfo_roadmap_2026-08-13.md` (kế hoạch) + `claude/wfo_phase3_status_2026-08-13.md` (matrix đang chạy).

## 0. BLOCKER KẾT NỐI — sửa TRƯỚC khi làm gì (quan trọng nhất)
Việc chạy trên **oracle box = `161.118.212.3:22`** (user: ubuntu) + **Kaggle** (CLI trên oracle). `.226`/`.242` chỉ là Aerospike data — KHÔNG SSH vào đó để làm việc.

Tình trạng lúc reset (đã kiểm chứng trong session này):
1. **System32 OpenSSH bị chặn** ở máy Windows: `C:\Windows\System32\OpenSSH\ssh.exe` chạy ra 0 output / exit 255 (kể cả `ssh -V`). Nghi EDR/AppLocker. → **BẮT BUỘC dùng git-ssh**: `& "C:\Program Files\Git\usr\bin\ssh.exe"`. (Đã ghi trong runbook.)
2. **Không auth được oracle**: oracle:22 sống nhưng từ chối `id_rsa` và `id_ed25519` (`Permission denied (publickey)`). Key đúng nhiều khả năng là **`id_product_2048`** — nhưng **private key này KHÔNG có trong `C:\Users\pc\.ssh\`** (chỉ còn `.pub`). Trước đây nó nằm trong ssh-agent.
3. **ssh-agent Disabled + Stopped**, và PowerShell tool **không có quyền admin** để bật lại (Set-Service → Access denied). ssh-add rỗng.

→ **Session mới KHÔNG vào được oracle cho tới khi user làm 1 trong các cách sau** (cần user, không tự làm được):
- (a) Mở terminal thường (không sandbox) → `Start-Service ssh-agent` (bật service nếu cần, có thể phải Admin) → `ssh-add <đường-dẫn-private-key-oracle>`; hoặc
- (b) Đặt lại **file private key** của oracle (id_product_2048 hoặc key tương ứng) vào `C:\Users\pc\.ssh\` → session dùng `git-ssh -i`; hoặc
- (c) Cho biết đường dẫn/paste key oracle để cấu hình.
- (Phụ, không bắt buộc: gỡ chặn System32 ssh.exe — đã có workaround git-ssh nên không cần.)

Cách kiểm tra nhanh đã kết nối được:
```
& "C:\Program Files\Git\usr\bin\ssh.exe" -p 22 -o StrictHostKeyChecking=no -o PubkeyAcceptedAlgorithms=+ssh-rsa ubuntu@161.118.212.3 "hostname; date -u"
```
Ra hostname = OK. `Permission denied (publickey)` = vẫn kẹt key.

## 1. ĐANG Ở ĐÂU — Phase 3 matrix (Track B)
- **Track A native-5m: BỎ** (OOM Kaggle GPU, xem phase3_status).
- **Track B (train15→pred5): đang chạy.** 4 selector train xong 18 fold. Ma trận fanout 4 threshold × 2 moveSL = **8 ô**:
  - ✅ **B008** (moveSL0.03) DONE: total +15,139, t=2.88, %pos 68.8%, maxDD 796 (2023+: +13,795, t=2.85, %pos 75%, maxDD 500). *Xác minh lại từ `DONE_B008.txt`.*
  - 🟡 **B015** (moveSL0.03) đã launch nền — **kiểm `log_B015.txt` xem "DONE tag=B015" chưa**, cp report, parse.
  - ⬜ **B02, B03** (moveSL0.03) — chưa chạy.
  - ⬜ **B008/B015/B02/B03 sl05** (moveSL0.05) — chưa chạy.
- Bảng đầy đủ 8 ô + chọn best → **Phase 4**. (Chi tiết + lệnh trong phase3_status + runbook mục 1 Bước D.)

## 2. RESUME (sau khi mở khoá SSH mục 0)
Trên oracle, mọi lệnh remote đi qua **git-ssh + OrBash base64** (tránh lỗi quote PowerShell — runbook mục 5).
1. Xác minh live: `free -g` (không launch batch mới nếu batch cũ chưa DONE — 1 Java Xmx18g/lần), `tail log_B015.txt`, `ls claudedata/sweep/`.
2. Nếu B015 xong → `cp .../oracle_worker_cwd/docs/reports/wfo_strategy_window.md claudedata/sweep/REPORT_B015.md` NGAY (report bị ghi đè mỗi run), parse per-window OOS_pnl (python heredoc, dùng `int()` so sánh — TRÁNH f-string backslash).
3. Launch ô kế: `bash /home/ubuntu/fan_sel.sh B02 chuyendinh/selector-15mtr-pred5-net02-gpu` (rồi B03). moveSL0.03 là default `drive_exp18.sh`.
4. Batch sl05: set `SIM_RATE_PROFIT_STOP_MARKET=0.05` trong `run_worker.py` env block rồi chạy 4 tag sl05.
5. Đủ 8 ô → cập nhật `wfo_phase3_status_2026-08-13.md` (bảng) + báo user + đề xuất best config.

## 3. LÀM TIẾP SAU MATRIX (theo roadmap)
- Phase 4: chốt best (lưới×threshold×moveSL) + STEP3 rank-K {5,8,12} + audit label-leak theo ts.
- Phase 5: **gate v2** — thêm chiều risk/đuôi WF-clean (dùng label `maxAdv_4h`/`maxFav`), veto entry khi tail dự đoán xấu → mục tiêu cắt maxDD lớn (nguồn gốc: gate hiện chỉ MOM15, mù downside). Chi tiết roadmap Phase 5.
- Phase 6: **DCA v2** market-gated `shouldDca`.

## 4. Nguyên tắc bắt buộc (đừng vi phạm)
- `free -g` trước mỗi fanout; KHÔNG chồng 2 job Xmx nặng (đã crash+reboot 13/8). 1 batch/lần, serial.
- verify jar-stage trước fanout (`verify_stage.py` — chống jar stale).
- Kaggle không inject env động → hardcode vào kernel .py trước push.
- Verdict: `WfoCoordinator report` + `WFO_HARNESS_FIX=true` + gatecount.jar; KHÔNG cache `wfo_report`. Tiêu chí frozen: %OOS-dương ≥70% & maxDD-OOS ≤50% (bỏ WFE).
- Deploy production: **PHẢI hỏi user scope trước** (config nào → box nào). Chưa làm.

## 5. Con trỏ
- Vận hành chi tiết: `claude/wfo_ops_runbook_2026-08-13.md`.
- Kế hoạch tổng: `claude/wfo_roadmap_2026-08-13.md`.
- Matrix hiện tại: `claude/wfo_phase3_status_2026-08-13.md`.
- Gate hiện trạng/điểm yếu: `claude/wfo_gate_recheck_2026-08-13.md`.
