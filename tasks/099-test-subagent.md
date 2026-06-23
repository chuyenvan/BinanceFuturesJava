---
id: 099
status: TODO
touches_live_process: false
writes_242_data: false
resource: local
---

# TASK-099: Test CCD có gọi được subagent không

## Mục đích
Claude Desktop (CDK) đã thử `claude-code:Agent` và nhận lỗi "Agent type 'general-purpose' not found".
Cần biết CCD (chạy trong IntelliJ terminal) có spawn subagent được không — để quyết định có dùng
kiến trúc CDK orchestrate → CCD subagent hay không.

## Việc làm (CCD)
Chạy lệnh sau trong terminal, báo lại output đúng 1 dòng:

```bash
claude -p "chỉ cần reply 1 dòng: SUBAGENT_OK" --model claude-haiku-4-5-20251001 2>&1 | tail -3
```

Nếu không có `claude` CLI trong PATH thì thử:
```bash
which claude || echo NOT_FOUND
```

## Báo lại
- Lệnh chạy được và trả về "SUBAGENT_OK" → **SUBAGENT_WORKS**
- Lệnh không tìm thấy / lỗi auth / lỗi khác → **SUBAGENT_FAILS: <lý do>**
- Không cần làm gì thêm sau khi báo kết quả.
