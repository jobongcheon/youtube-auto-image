#!/bin/sh
# 윈도우 실행파일을 만든다. 리눅스·맥에서도 교차 컴파일된다.
#   sh exe/build.sh
set -e
cd "$(dirname "$0")"
python3 -m src.cli build --installer >/dev/null 2>&1 || true
cp ../out/작업대.html app.html
if [ ! -f rsrc_windows_amd64.syso ]; then
  go run github.com/akavel/rsrc@latest -ico icon.ico -arch amd64 -o rsrc_windows_amd64.syso
fi
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 \
  go build -ldflags="-s -w -H=windowsgui" -o "../out/거북선작업대.exe" .
ls -lh "../out/거북선작업대.exe"
