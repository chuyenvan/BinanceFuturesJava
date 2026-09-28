@echo off
C:\PROGRA~1\Git\usr\bin\ssh.exe -o BatchMode=yes -o ConnectTimeout=20 -i %USERPROFILE%\.ssh\id_rsa_chuyennd_openssh ubuntu@161.118.212.3 "cat > /home/ubuntu/claude_audit_0928/ofirx/%1 && md5sum /home/ubuntu/claude_audit_0928/ofirx/%1" < "E:\educa\source\github\20260415\BinanceFuturesJava\_claude_tmp\ofirx\%1"
