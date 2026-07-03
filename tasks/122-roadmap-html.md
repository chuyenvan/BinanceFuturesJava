# TASK-122: Trang HTML lộ trình kiểm chứng 6 bước (CCD sonnet)

- **status:** done (CCD 2026-07-04)
- **resource:** local · **touches_live_process:** không

## Việc làm
1. Tạo file `docs/architecture/roadmap.html` — trực quan hóa lộ trình kiểm chứng 6 bước, nguồn sự thật: `docs/ROADMAP.md`.
2. Hiển thị đủ 6 bước (Bước 0–5) với status badge đúng: Bước 0 (áp xong / đo đối chứng chưa), Bước 1 (todo), Bước 2 (PASS 2026-06-23), Bước 3 (2 track song song), Bước 4 (đang chạy), Bước 5 (todo). Chi tiết nội dung đọc từ `docs/ROADMAP.md`.
3. **Bước 3 — trạng thái CHỐT (master cung cấp, dùng nguyên văn, không suy diễn):** nội dung block-quote trạng thái từ `docs/ROADMAP.md §Bước 3` (▶️ TRẠNG THÁI 2026-06-29 — 2 TRACK SONG SONG…) phải hiển thị nguyên văn trong HTML, không tóm tắt, không diễn giải lại.
4. Yêu cầu HTML: single-file tự chứa (CSS inline, không build step), tiếng Việt, màu trạng thái (xanh=done/vàng=wip/đỏ=todo) + legend, responsive, click component hiện tooltip + đường dẫn nguồn. Style (dark-theme, font, card layout) khớp `wfo_architecture.html` + `system_architecture_all.html`.
5. Output: file HTML + commit theo quy ước (`docs(122): …`) + done marker `/d/claudedata/CCD122_DONE`.

## Kết quả

**Hoàn thành 2026-07-04 (CCD sonnet)**

### File đã tạo
| File | Ghi chú |
|---|---|
| `tasks/122-roadmap-html.md` | File task này |
| `docs/architecture/roadmap.html` | Single-file HTML ~18KB |

### Nội dung HTML
- **B0:** Bịt look-ahead + slippage: guard áp xong ✅ · đo đối chứng chưa ❌
- **B1:** Đo MODEL độc lập: chưa làm ❌ · 2 lỗi leak hiện tại
- **B2:** Ablation PASS ✅ 2026-06-23 · A: +69217 Calmar 3.40 vs B/C LỖ → AI CÓ EDGE THẬT
- **B3:** Nguyên văn trạng thái CHỐT từ ROADMAP.md §Bước 3 (2 track song song, 2026-06-29)
- **B4:** WFO đang chạy 🔄 · leaked V4 16/17 DONE · WFE=0.239, %OOS+=75%, worstDD=16.6%
- **B5:** Hợp nhất sim/product: chưa làm ❌

### HTML đáp ứng yêu cầu
- Single-file tự chứa (CSS inline) ✅
- Tiếng Việt ✅
- Màu trạng thái: xanh=done / vàng=wip / đỏ=todo + legend ✅
- Responsive ✅
- Click component → tooltip mô tả + đường dẫn nguồn ✅
- Style khớp wfo_architecture.html + system_architecture_all.html ✅
- Bước 3: nguyên văn block-quote từ ROADMAP.md, không suy diễn ✅

## Phát hiện ngoài scope

Không có.
