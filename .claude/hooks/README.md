# Hooks - backstop co hoc chong ssh raw (chong dot token)

## block-raw-ssh.sh (DRAFT - chua bat)
Chan Bash goi `ssh`/`scp` truc tiep khi KHONG di qua `ce.cmd`. Ap cho ca master-thread lan
subagent (`claude -p` cua supervisor.py chay trong repo). Day la thu DUY NHAT song sot qua "quen
delegate" - luat trong doc chi la hanh vi, hook moi la co che.

Pham vi: hook la tinh nang Claude Code (`.claude/settings.json`). Chay cho phien Claude Code / CCD
worker trong repo. Phien Cowork (goi ssh qua Desktop Commander start_process) co the KHONG kich hoat
hook nay -> Cowork van phai tu giu ky luat CE.

## Bat (sau khi Uni duyet)
Them vao `.claude/settings.json` (KHONG phai settings.local.json):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/block-raw-ssh.sh" }
        ]
      }
    ]
  }
}
```

Test nhanh sau khi bat:
- `ssh ubuntu@... "cat x"` -> phai bi BLOCKED (exit 2).
- `orchestrator/ce.cmd wfo_status` -> phai CHAY binh thuong.

## TODO (chua lam)
- Chan Read > N dong (kho hon: Read khong di qua Bash; can hook rieng cho tool Read hoac
  guard o tang doc file). Hien tai chi chan ssh/scp raw.
