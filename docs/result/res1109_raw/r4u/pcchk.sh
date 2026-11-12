#!/bin/bash
# in do dai + loai (URL hay khac) cua chuoi >=20 trong PrivateConfig.class r4u; khong in gia tri khong phai URL
unzip -p ~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u com/binance/chuyennd/config/PrivateConfig.class \
 | strings -n 20 | grep -v -E '^.?[A-Za-z0-9_/$;()<>.\[]+$' \
 | while read -r l; do case "$l" in *https://*|*wss://*) echo "${#l} URL ${l#?}";; *) echo "${#l} OTHER";; esac; done
