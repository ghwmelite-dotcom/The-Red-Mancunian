# Red Mancunian daily news automation.
# Runs /mufc-update headlessly, then raises a Windows toast when videos are ready.
# Scheduled via Task Scheduler (see tiktok/PLAYBOOK.md "Automation" section).
# Manual test of the alert only:  powershell -File tiktok\run-daily.ps1 -TestAlert

param([switch]$TestAlert)

$ErrorActionPreference = "Continue"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$Today = Get-Date -Format "yyyy-MM-dd"
$OutDir = Join-Path $ProjectDir "tiktok\output\$Today"
$LogDir = Join-Path $ProjectDir "tiktok\output\automation-logs"
$LogFile = Join-Path $LogDir "$Today.log"

function Show-Toast($title, $body) {
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $xmlText = "<toast scenario='reminder'><visual><binding template='ToastGeneric'>" +
                   "<text>$title</text><text>$body</text></binding></visual>" +
                   "<audio src='ms-winsoundevent:Notification.Default'/></toast>"
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($xmlText)
        $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
        # PowerShell's registered AppUserModelID - toasts from unregistered ids are dropped
        $appId = "{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
    } catch {
        # Fallback: non-blocking popup (auto-dismisses after 30s)
        (New-Object -ComObject WScript.Shell).Popup($body, 30, $title, 64) | Out-Null
    }
}

if ($TestAlert) {
    Show-Toast "Red Mancunian - test alert" "If you can read this, the automation alert works."
    exit 0
}

New-Item -ItemType Directory -Force $LogDir | Out-Null
Set-Location $ProjectDir

$before = @(Get-ChildItem $OutDir -Filter *.mp4 -ErrorAction SilentlyContinue)

$prompt = "/mufc-update UNATTENDED RUN: never wait for user input. On slow days do " +
          "not render evergreen content - write the recommendation in your summary " +
          "instead. Render both platform versions of any selected story."

"=== Run started $(Get-Date -Format o) ===" | Out-File $LogFile -Encoding utf8 -Append
& claude -p $prompt `
    --allowedTools "WebFetch,WebSearch,Read,Glob,Grep,Write,Bash(python tiktok/render.py:*),Bash(curl:*)" `
    *>> $LogFile
$claudeExit = $LASTEXITCODE
"=== Run finished $(Get-Date -Format o) exit=$claudeExit ===" | Out-File $LogFile -Encoding utf8 -Append

$after = @(Get-ChildItem $OutDir -Filter *.mp4 -ErrorAction SilentlyContinue)
$newVideos = @($after | Where-Object { $before.Name -notcontains $_.Name })

if ($newVideos.Count -gt 0) {
    $names = ($newVideos | ForEach-Object { $_.BaseName }) -join ", "
    Show-Toast "Red Mancunian: $($newVideos.Count) video(s) ready to post" `
               "$names - open tiktok\output\$Today and follow the post-notes files."
} elseif ($claudeExit -ne 0) {
    Show-Toast "Red Mancunian: run FAILED" "Check tiktok\output\automation-logs\$Today.log"
} else {
    Show-Toast "Red Mancunian: no new videos today" `
               "Editor found nothing worth posting (or story already rendered). Log: automation-logs\$Today.log"
}
