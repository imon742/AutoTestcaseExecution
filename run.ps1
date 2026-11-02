param(
    [ValidateSet('demo','login','explore','report','review','generate','replay')]
    [string]$Command = 'report',
    [string]$Csv = 'demo/cases.csv',
    [int]$Batch = 5,
    [string]$Case = ''
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if ($Command -eq 'demo') {
    & $pythonExe 'demo/server.py'
} else {
    & $pythonExe 'qa.py' $Command --csv $Csv --batch $Batch --case $Case
}
exit $LASTEXITCODE
