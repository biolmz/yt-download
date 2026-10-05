<#
.SYNOPSIS
    Archive a YouTube channel on Windows: 1080p, resumable, safe to rerun.

.DESCRIPTION
    Fetches every upload of a channel or playlist, skipping videos that were already
    downloaded (tracked in an archive file). Intended to be scheduled with Task
    Scheduler: run it as often as you like and only new videos are fetched.

.EXAMPLE
    .\archive_a_channel.ps1 -Url "https://www.youtube.com/@SomeChannel"

.EXAMPLE
    .\archive_a_channel.ps1 -Url "https://www.youtube.com/@SomeChannel" -OutDir "D:\Videos" -Quality 720
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [string]$OutDir = (Join-Path $HOME "Videos\yt-archive"),

    [ValidateSet("best", "2160", "1440", "1080", "720", "480", "360")]
    [string]$Quality = "1080",

    [string]$SubsLangs = "en",

    # Optional: use a proxy. Omit to let yt-download auto-detect a local one.
    [string]$Proxy
)

$ErrorActionPreference = "Stop"

$archiveDir = Join-Path $env:LOCALAPPDATA "yt-download"
$archiveFile = Join-Path $archiveDir "channel.txt"
New-Item -ItemType Directory -Force -Path $OutDir, $archiveDir | Out-Null

Write-Host "Channel : $Url"
Write-Host "Output  : $OutDir"
Write-Host "Archive : $archiveFile"
Write-Host ""

$arguments = @(
    $Url
    "--playlist"
    "--quality", $Quality
    "--download-archive", $archiveFile
    "--subs"
    "--subs-langs", $SubsLangs
    "--thumb"
    "--meta"
    "--save-json"
    "--ignore-errors"
    "--output", $OutDir
    "--template", "%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s"
)

if ($Proxy) { $arguments += @("--proxy", $Proxy) }

& yt-download @arguments
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "Done. Finished videos are recorded in $archiveFile"
} else {
    Write-Warning "yt-download exited with code $exitCode. Some items may have failed; see the output above."
}

exit $exitCode
