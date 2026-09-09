# FiraCode Maple Mono 终态安装与环境同步脚本
# 动态解析脚本目录，杜绝硬编码绝对路径
$ErrorActionPreference = 'Continue'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$MergedDir = Join-Path $ProjectRoot 'merged-v4'

$FontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
$RegPath = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'

Write-Output "=========================================="
Write-Output "安装 FiraCode Maple Mono 到当前用户字体库"
Write-Output "=========================================="

Add-Type -Name Native -Namespace Win32 -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int RemoveFontResource(string lpFileName);
[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int AddFontResource(string lpFileName);
'@

$subfamilies = @('Regular', 'Bold', 'Italic', 'BoldItalic')

# 1. 复制字体并向 GDI 与注册表注册
foreach ($sub in $subfamilies) {
    $baseName = "FiraCodeMapleMono-$sub"
    $srcFile = Join-Path $MergedDir "$baseName.ttf"
    $destFile = Join-Path $FontDir "$baseName.ttf"

    if (-not (Test-Path -LiteralPath $srcFile)) {
        Write-Error "源文件不存在: $srcFile"
        continue
    }

    # 如果有被锁定的旧文件，先行解除注册
    if (Test-Path -LiteralPath $destFile) {
        [Win32.Native]::RemoveFontResource($destFile) | Out-Null
    }

    $installedFile = $destFile
    try {
        Copy-Item -LiteralPath $srcFile -Destination $destFile -Force -ErrorAction Stop
        Write-Output "  [OK] $baseName -> 已安装至标准路径"
    } catch {
        # 若当前运行的终端仍占用标准文件名句柄，安全采用版本后缀规避锁定冲突
        $installedFile = Join-Path $FontDir "$baseName-v41.ttf"
        Copy-Item -LiteralPath $srcFile -Destination $installedFile -Force
        Write-Output "  [WARN] $baseName -> 标准文件被系统占用，已通过热更新槽位安装 ($installedFile)"
    }

    # 注册表项与 GDI 注册
    New-ItemProperty -Path $RegPath -Name "$baseName (TrueType)" -Value $installedFile -PropertyType String -Force | Out-Null
    [Win32.Native]::AddFontResource($installedFile) | Out-Null
}

# 2. 清理历史遗留的旧版改名孤儿文件（如 FiraCodeMapleCN 等）
Get-ChildItem $FontDir -Filter "FiraCodeMapleCN*.ttf" -ErrorAction SilentlyContinue | ForEach-Object {
    [Win32.Native]::RemoveFontResource($_.FullName) | Out-Null
    try { Remove-Item $_.FullName -Force -ErrorAction Stop } catch {}
}

# 3. 同步 6 个 VSCode 衍生 IDE 的配置
Write-Output "`n同步 IDE 配置..."
$ides = @('Code', 'Trae CN', 'TRAE SOLO CN', 'Antigravity IDE', 'Kiro', 'QoderCN')
foreach ($ide in $ides) {
    $settingsPath = Join-Path $env:APPDATA "$ide\User\settings.json"
    if (-not (Test-Path -LiteralPath $settingsPath)) { continue }

    try {
        $json = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $json.'terminal.integrated.fontFamily' = 'FiraCode Maple Mono'
        $json.'editor.fontFamily' = 'FiraCode Maple Mono'
        $out = $json | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($settingsPath, $out, (New-Object System.Text.UTF8Encoding($false)))
        Write-Output "  [OK] $ide 配置已同步"
    } catch {
        Write-Warning "  [FAIL] $ide 配置更新失败: $_"
    }
}

Write-Output "`n=========================================="
Write-Output "全部安装与环境配置已就绪！"
Write-Output "=========================================="
