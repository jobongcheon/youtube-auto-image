package main

import (
	"syscall"
	"unsafe"
)

// alert 는 윈도우 기본 메시지 상자를 띄운다. GUI 모드에는 콘솔이 없어서
// 오류를 화면에 보여줄 다른 방법이 없다.
func alert(title, body string) {
	user32 := syscall.NewLazyDLL("user32.dll")
	messageBoxW := user32.NewProc("MessageBoxW")

	t, err := syscall.UTF16PtrFromString(title)
	if err != nil {
		return
	}
	b, err := syscall.UTF16PtrFromString(body)
	if err != nil {
		return
	}
	const mbIconError = 0x00000010
	messageBoxW.Call(0, uintptr(unsafe.Pointer(b)), uintptr(unsafe.Pointer(t)), mbIconError)
}
