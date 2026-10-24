export PATH=$HOME/.local/bin:$PATH
# key.txt format is "<label>: <64-hex>"; take part after last colon. Never echoed.
export CRYPTOHFTDATA_API_KEY="$(sed 's/.*:[[:space:]]*//' /home/ubuntu/key.txt | tr -d ' \r\n')"
cd ~/claude_master/chd_wk
