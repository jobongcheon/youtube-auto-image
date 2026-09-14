//go:build !windows

package main

import (
	"fmt"
	"os"
)

// 윈도우가 아닌 환경(테스트용)에서는 표준 오류로 낸다.
func alert(title, body string) {
	fmt.Fprintf(os.Stderr, "%s: %s\n", title, body)
}
