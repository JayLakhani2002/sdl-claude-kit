<#
SDL Claude Kit - Windows bootstrap. Installs prerequisites, Claude Code, and chosen skill groups.

  powershell -ExecutionPolicy Bypass -File install-windows.ps1 -Groups marketing,sales
  powershell -ExecutionPolicy Bypass -File install-windows.ps1 -Groups all

Needs Windows 10 1809+ / 11 (winget). Safe to re-run.
#>
param(
  [string[]]$Groups = @('marketing'),
  [string]$Repo = 'CHANGE-ME/sdl-claude-kit'   # <github-org>/<repo>
)
$ErrorActionPreference = 'Stop'
if ($Groups -contains 'all') { $Groups = 'marketing','sales','content','design','research','engineering' }

# Which extra tools each group's skills need (git is always installed).
$need = @{
  marketing   = @()
  sales       = @()
  content     = @()
  design      = 'node','python','ffmpeg'
  research    = 'node'
  engineering = 'node','python'
}
$pkg = @{ git='Git.Git'; node='OpenJS.NodeJS.LTS'; python='Python.Python.3.12'; ffmpeg='Gyan.FFmpeg' }
$tools = @('git') + ($Groups | ForEach-Object { $need[$_] }) | Select-Object -Unique

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  throw 'winget missing. Install "App Installer" from the Microsoft Store, then re-run.'
}

foreach ($t in $tools) {
  Write-Host "== $t"
  winget install --id $pkg[$t] -e --silent --accept-package-agreements --accept-source-agreements
  # winget exits non-zero when already installed; verify by command below instead of exit code.
}

# Pick up new PATH entries in this session.
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')

# Skills call `python3`; python.org installs only provide `python`. Add a python3.exe copy.
if ($tools -contains 'python') {
  $py = (Get-Command python -ErrorAction SilentlyContinue).Source
  if ($py -and $py -notlike '*WindowsApps*') {
    $p3 = Join-Path (Split-Path $py) 'python3.exe'
    if (-not (Test-Path $p3)) { Copy-Item $py $p3 }
  }
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  Write-Host '== claude code'
  Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression
  $env:Path += ";$env:USERPROFILE\.local\bin"
}

Write-Host '== skills'
claude plugin marketplace add $Repo
foreach ($g in $Groups) { claude plugin install "sdl-$g@sdl-claude-kit" }

Write-Host "`nDone. Open a NEW terminal, run: claude   (log in with your SDL account on first run)"
foreach ($t in $tools) {
  $c = @{ git='git'; node='node'; python='python'; ffmpeg='ffmpeg' }[$t]
  $ok = [bool](Get-Command $c -ErrorAction SilentlyContinue)
  Write-Host ("  {0,-7} {1}" -f $t, $(if ($ok) {'OK'} else {'NOT FOUND - reopen terminal and check'}))
}
