[CmdletBinding()]
param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonCommand = Get-Command python -ErrorAction Stop

Push-Location $ProjectRoot
try {
    Write-Host "Checking Python packaging tools..." -ForegroundColor Cyan
    & $PythonCommand.Source -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller is missing. Run: python -m pip install -r requirements-build.txt"
    }

    Write-Host "Generating application icon..." -ForegroundColor Cyan
    & $PythonCommand.Source (Join-Path $ProjectRoot "tools\build_icon.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Application icon generation failed with exit code $LASTEXITCODE."
    }

    Write-Host "Building the Windows application..." -ForegroundColor Cyan
    & $PythonCommand.Source -m PyInstaller --noconfirm --clean "ImageReliefStudio.spec"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    $ApplicationExe = Join-Path $ProjectRoot "dist\ImageReliefStudio\ImageReliefStudio.exe"
    if (-not (Test-Path -LiteralPath $ApplicationExe)) {
        throw "Expected application executable was not created: $ApplicationExe"
    }
    Write-Host "Application built: $ApplicationExe" -ForegroundColor Green

    Write-Host "Running packaged application smoke test..." -ForegroundColor Cyan
    $SmokeTest = Start-Process -FilePath $ApplicationExe `
        -ArgumentList "--smoke-test" `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    if ($SmokeTest.ExitCode -ne 0) {
        throw "Packaged application smoke test failed with exit code $($SmokeTest.ExitCode)."
    }
    Write-Host "Packaged application smoke test passed." -ForegroundColor Green

    if ($SkipInstaller) {
        Write-Host "Skipping installer compilation." -ForegroundColor Yellow
        exit 0
    }

    $CompilerCandidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $InnoCompiler = $CompilerCandidates |
        Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
        Select-Object -First 1

    if (-not $InnoCompiler) {
        throw "Inno Setup 6 was not found. Install it with: winget install --id JRSoftware.InnoSetup -e"
    }

    Write-Host "Compiling the Windows installer..." -ForegroundColor Cyan
    $SystemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $InstallerBuildDir = Join-Path $SystemTemp "ImageReliefStudioInstallerBuild-$PID"
    New-Item -ItemType Directory -Path $InstallerBuildDir -Force | Out-Null
    & $InnoCompiler `
        "/DMyOutputDir=$InstallerBuildDir" `
        (Join-Path $ProjectRoot "installer\ImageReliefStudio.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup failed with exit code $LASTEXITCODE."
    }

    $InstallerExe = Join-Path $ProjectRoot "installer\output\ImageReliefStudio-Setup-1.0.0.exe"
    $TemporaryInstaller = Join-Path $InstallerBuildDir "ImageReliefStudio-Setup-1.0.0.exe"
    $ProjectInstallerDir = Split-Path -Parent $InstallerExe
    New-Item -ItemType Directory -Path $ProjectInstallerDir -Force | Out-Null
    Copy-Item -LiteralPath $TemporaryInstaller -Destination $InstallerExe -Force
    $ResolvedBuildDir = [IO.Path]::GetFullPath($InstallerBuildDir)
    if (-not $ResolvedBuildDir.StartsWith($SystemTemp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean installer build directory outside the system temp path."
    }
    Remove-Item -LiteralPath $ResolvedBuildDir -Recurse -Force
    if (-not (Test-Path -LiteralPath $InstallerExe)) {
        throw "Expected installer was not created: $InstallerExe"
    }
    Write-Host "Installer built: $InstallerExe" -ForegroundColor Green
}
finally {
    Pop-Location
}
