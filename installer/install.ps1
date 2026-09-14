# 거북선 컷 작업대 — 바탕화면 설치
# 하는 일: app.html 을 바탕화면 폴더로 복사하고, Chrome 앱 모드로 여는 바로가기를 만든다.

$ErrorActionPreference = 'Stop'

function Say($t) { Write-Host $t }

try {
    $src = Join-Path $PSScriptRoot 'app.html'
    if (-not (Test-Path $src)) {
        Say ''
        Say '  [실패] app.html 을 찾을 수 없습니다.'
        Say '  압축을 푼 폴더 안에서 INSTALL.bat 을 실행해 주세요.'
        Say '  (압축 파일 안에서 바로 실행하면 이 오류가 납니다)'
        exit 1
    }

    # OneDrive 리디렉션 등으로 비어 올 때가 있어 USERPROFILE 로 한 번 더 찾는다.
    $desktop = [Environment]::GetFolderPath('Desktop')
    if ([string]::IsNullOrWhiteSpace($desktop) -and $env:USERPROFILE) {
        $desktop = Join-Path $env:USERPROFILE 'Desktop'
    }
    if ([string]::IsNullOrWhiteSpace($desktop) -or -not (Test-Path $desktop)) {
        Say ''
        Say '  [실패] 바탕화면 폴더를 찾을 수 없습니다.'
        Say "  확인한 경로: '$desktop'"
        Say '  app.html 을 직접 원하는 곳에 두고 더블클릭해도 똑같이 동작합니다.'
        exit 1
    }

    $dir = Join-Path $desktop '거북선 작업대'
    $html    = Join-Path $dir '작업대.html'

    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    # 이미 설치돼 있으면 진행 상황은 브라우저에 있으므로 덮어써도 안전하다.
    Copy-Item -LiteralPath $src -Destination $html -Force
    Say "  파일 복사  $html"

    # Chrome 앱 모드로 열면 주소창 없이 창 하나만 떠서 앱처럼 쓸 수 있다.
    # 32비트 윈도우에는 ProgramFiles(x86) 이 없다. 빈 루트는 걸러내고 조합한다.
    $roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LocalAppData) |
             Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $apps  = @('Google\Chrome\Application\chrome.exe', 'Microsoft\Edge\Application\msedge.exe')

    $chrome = $null
    foreach ($app in $apps) {
        foreach ($root in $roots) {
            $try = Join-Path $root $app
            if (Test-Path -LiteralPath $try) { $chrome = $try; break }
        }
        if ($chrome) { break }
    }

    # 파일은 이미 자리를 잡았다. 바로가기를 못 만들어도 쓸 수는 있으므로
    # 여기서 실패해도 전체를 실패로 처리하지 않는다.
    $lnk = Join-Path $desktop '거북선 작업대.lnk'
    try {
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut($lnk)

        if ($chrome) {
            $uri = 'file:///' + ($html -replace '\\', '/')
            $sc.TargetPath   = $chrome
            $sc.Arguments    = '--app="' + $uri + '"'
            $sc.IconLocation = "$chrome,0"
            Say ("  실행 방식  {0} 앱 모드 (주소창 없는 단독 창)" -f (Split-Path $chrome -Leaf))
        } else {
            # Chrome/Edge 를 못 찾으면 기본 브라우저로 연다.
            $sc.TargetPath = $html
            Say '  실행 방식  기본 브라우저 (Chrome 과 Edge 를 찾지 못했습니다)'
        }

        $sc.WorkingDirectory = $dir
        $sc.Description      = '거북선 컷 작업대 - 이미지 183장 / 영상 132개'
        $sc.Save()

        Say "  바로가기  $lnk"
        Say ''
        Say '  설치가 끝났습니다. 바탕화면의 [거북선 작업대] 를 더블클릭하세요.'
    }
    catch {
        Say ''
        Say '  바로가기는 만들지 못했지만 프로그램은 설치됐습니다.'
        Say "  이 파일을 더블클릭하면 똑같이 열립니다:"
        Say "    $html"
    }
    exit 0
}
catch {
    Say ''
    Say "  [실패] $($_.Exception.Message)"
    exit 1
}
