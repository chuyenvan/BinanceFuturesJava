# STATUS - orchestrator dashboard (supervisor ghi, dung sua tay)

- supervisor_pid: 59020 | last_tick: 2026-06-15T11:37:03+07:00 | last_action: idle
- slots: 1/4  (heavy_226 0/1, kaggle 0/5, kaggle_distributed 1/1)

## Dang chay
- 013: pid=10828 resource=kaggle_distributed started=2026-06-15T11:21:01+07:00 report_age=0.3'

## Cho nguoi (live-process / NEEDS_HUMAN / REVIEW)
- 017: REVIEW
- 035: touches_live_process -> nguoi deploy tay

## Queue (TODO san sang / bi chan deps)
- 018 (kaggle): BLOCKED deps['013']
- 025 (heavy_226): BLOCKED deps['012', '015', '017', '018']
- 026 (kaggle): BLOCKED deps['025']
- 037 (kaggle): BLOCKED deps['036']
- 038 (kaggle): BLOCKED deps['013', '037']
- 039 (kaggle): BLOCKED deps['037', '038', '024']
- 040 (heavy_226): BLOCKED deps['013']
