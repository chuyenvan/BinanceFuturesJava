# TASK-122: Trang HTML lộ trình kiểm chứng 6 bước (CCD sonnet)

- **status:** done (CCD 2026-07-04)
- **resource:** local · **touches_live_process:** không

## Việc làm
1. Tạo file `docs/architecture/roadmap.html` — trực quan hóa lộ trình kiểm chứng 6 bước, nguồn sự thật: `docs/ROADMAP.md`.
2. Hiển thị đủ 6 bước (Bước 0–5) với status badge đúng: Bước 0 (áp xong / đo đối chứng chưa), Bước 1 (todo), Bước 2 (PASS 2026-06-23), Bước 3 (2 track song song), Bước 4 (đang chạy), Bước 5 (todo). Chi tiết nội dung đọc từ `docs/ROADMAP.md`.
3. **Bước 3 — trạng thái CHỐT (master cung cấp, dùng nguyên văn, không suy diễn):** nội dung block-quote trạng thái từ `docs/ROADMAP.md §Bước 3` (▶️ TRẠNG THÁI 2026-06-29 — 2 TRACK SONG SONG…) phải hiển thị nguyên văn trong HTML, không tóm tắt, không diễn giải lại.
4. Yêu cầu HTML: single-file tự chứa (CSS inline, không build step), tiếng Việt, màu trạng thái (xanh=done/vàng=wip/đỏ=todo) + legend, responsive, click component hiện tooltip + đường dẫn nguồn. Style (dark-theme, font, card layout) khớp `wfo_architecture.html` + `system_architecture_all.html`.
5. Output: file HTML + commit theo quy ước (`docs(122): …`) + done marker `/d/claudedata/CCD122_DONE`.

## LÀM LẠI (lần 2 — lần 1 lệch spec: gộp 1 file roadmap.html, thiếu hẳn roadmap WFO chi tiết)
YÊU CẦU CỨNG lần 2:
1. PHẢI tạo ĐÚNG 2 file tên chính xác: `docs/architecture/roadmap_tong.html` và `docs/architecture/roadmap_wfo.html`.
   File roadmap.html cũ: XOÁ (git rm) — thay bằng 2 file trên. README cập nhật.
2. roadmap_wfo.html PHẢI có đủ: 5 giai đoạn GĐ0→GĐ4 (từ WFO_ROADMAP.md §3b) dạng timeline · từng TASK 112-122
   với trạng thái · khối 3 vế A/B/C (PREREG_3WAY + phụ lục replication Kaggle) · critical path.
3. TRẠNG THÁI CHỐT MỚI (2026-07-04 09:55 — dùng nguyên văn, thay cho mục 3 cũ):
   ✅ xong: TASK-112,113,114,116,117,120,121-code · GATE-112/113 PASS · coverage audit (gap 8-16x) ·
   bin restricted verify PASS · universe 886/83-delist · nạp gate WF full 1.795.680 record vào ai_pred_market_gate_wfo ·
   report leaked V4 16/17 (w16 OOM; 0.239/75%/16.6%) · report leak-free V4 (0.098/76.5%/30.7%) ·
   **VẾ A V4.1 XONG 17/17: FAIL/REVIEW (WFE_med 0.227 · %+ 47.1% · maxDD 30.7%)**
   🔄 đang chạy: **VẾ B V4.1 leaked-restricted (Oracle, từ 09:49)** · kernel Kaggle test-1 (đo tốc độ 1 window, ticker 226)
   ⏳ chờ lượt: export dataset v3 gate-WF (sau vế B — RAM) · vế C + re-run w16 (Xmx cao hơn) · TASK-118 đo Δ
   ⏭ chưa: run fully-leak-free (GĐ2) · survivorship tool chuẩn · TASK-119 (chờ thiết kế) · read-set env · fleet Kaggle (chờ số test-1)
   ⬜ chờ Uni quyết: fleet 5 slot Kaggle · thiết kế TASK-119

## Kết quả lần 2

**CCD 2026-07-04 — commit dcb4d6d (branch module)**

✅ Tạo đúng 2 file tên chính xác:
- `docs/architecture/roadmap_tong.html` — lộ trình 6 Bước tổng quan, click mở/đóng, Bước 3 verbatim status từ ROADMAP.md, Bước 4 link sang roadmap_wfo.html
- `docs/architecture/roadmap_wfo.html` — WFO chi tiết: 5 giai đoạn GĐ0→GĐ4 timeline, TASK 112–122 table, 3 vế A/B/C (vế A XONG FAIL · vế B đang chạy · vế C chờ) + phụ lục Kaggle replication, critical path 2 mức (blocking + song song), trạng thái chốt 2026-07-04 09:55 nguyên văn

✅ `git rm docs/architecture/roadmap.html` (file lần 1 sai spec)
✅ README.md cập nhật bảng 2 file mới
✅ Style dark-theme khớp wfo_architecture.html (background #0f172a, card #1e293b, badge done/wip/todo, tooltip overlay, font Segoe UI)
✅ Trạng thái chốt mới dùng nguyên văn mục 3 (không diễn giải lại)