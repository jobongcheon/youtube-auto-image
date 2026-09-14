// 거북선 컷 작업대 — 윈도우 단일 실행파일.
//
// 작업대 HTML 을 실행파일 안에 넣어 두고, 실행하면 꺼내어 Chrome 앱 모드로 띄운다.
// 앱 모드는 주소창과 탭이 없는 단독 창이라 브라우저가 아니라 프로그램처럼 보인다.
// 설치도 런타임도 필요 없다 — 이 파일 하나를 바탕화면에 두고 더블클릭하면 된다.
package main

import (
	_ "embed"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

//go:embed app.html
var appHTML []byte

const appName = "거북선 작업대"

// 브라우저 실행 파일 후보. 앞에 있는 것을 먼저 쓴다.
var browsers = []string{
	`Google\Chrome\Application\chrome.exe`,
	`Microsoft\Edge\Application\msedge.exe`,
	`Chromium\Application\chrome.exe`,
}

// dataDir 은 HTML 을 꺼내 둘 곳이다. 실행파일 옆이 아니라 LOCALAPPDATA 를 쓴다 —
// 바탕화면이나 USB 등 쓰기가 막힌 위치에서 실행돼도 동작해야 하기 때문이다.
func dataDir() (string, error) {
	base := os.Getenv("LOCALAPPDATA")
	if base == "" {
		base = os.Getenv("APPDATA")
	}
	if base == "" {
		base = os.TempDir()
	}
	dir := filepath.Join(base, "GeobukseonWorktable")
	return dir, os.MkdirAll(dir, 0o755)
}

// findBrowser 는 설치된 크로미움 계열 브라우저를 찾는다.
// 32비트 윈도우에는 ProgramFiles(x86) 이 없으므로 빈 루트는 걸러낸다.
func findBrowser() string {
	roots := []string{
		os.Getenv("ProgramFiles"),
		os.Getenv("ProgramFiles(x86)"),
		os.Getenv("LocalAppData"),
	}
	for _, rel := range browsers {
		for _, root := range roots {
			if root == "" {
				continue
			}
			p := filepath.Join(root, rel)
			if st, err := os.Stat(p); err == nil && !st.IsDir() {
				return p
			}
		}
	}
	return ""
}

func fileURL(path string) string {
	return "file:///" + strings.ReplaceAll(path, `\`, "/")
}

func run() error {
	dir, err := dataDir()
	if err != nil {
		return fmt.Errorf("작업 폴더를 만들 수 없습니다: %w", err)
	}

	html := filepath.Join(dir, "작업대.html")
	// 매번 새로 쓴다. 진행 상황은 브라우저에 남으므로 덮어써도 잃는 것이 없다.
	if err := os.WriteFile(html, appHTML, 0o644); err != nil {
		return fmt.Errorf("파일을 쓸 수 없습니다: %w", err)
	}

	if browser := findBrowser(); browser != "" {
		cmd := exec.Command(browser, "--app="+fileURL(html))
		if err := cmd.Start(); err != nil {
			return fmt.Errorf("브라우저를 실행할 수 없습니다: %w", err)
		}
		return nil
	}

	// 크로미움 계열이 없으면 기본 브라우저에 맡긴다. 앱 모드는 아니지만 열리기는 한다.
	cmd := exec.Command("rundll32", "url.dll,FileProtocolHandler", html)
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("기본 브라우저를 열 수 없습니다: %w", err)
	}
	return nil
}

func main() {
	if err := run(); err != nil {
		// 창 없이(GUI 모드로) 빌드하므로 콘솔 출력 대신 메시지 상자를 띄운다.
		alert(appName, err.Error())
		os.Exit(1)
	}
}
