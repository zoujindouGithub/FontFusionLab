# FontFusionLab install.ps1 - recipe/variant 驱动的用户级字体安装
# 家族名与文件前缀来自 recipe; -WhatIf 只输出解析后的安装计划, 不做任何变更。
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Variant = 'firacode-sarasa',
    [string]$Recipe,
    [string]$OutputRoot,
    [switch]$ConfigureEditors
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# 通过 catalog 解析 recipe (ID 或 JSON 路径); family/prefix 全部来自 recipe。
$catalogCode = 'import json,sys;sys.path.insert(0,"scripts");import catalog;r=catalog.load_recipe(sys.argv[1]);print(json.dumps({"family":r["family"],"prefix":r["file_prefix"],"id":r["id"]}))'
$catalogArgs = @($(if ($Recipe) { $Recipe } else { $Variant }))
$catalogArgs = @('-c', $catalogCode) + $catalogArgs
$pyExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pyExe)) { $pyExe = 'python' }
$recipeJson = & $pyExe @catalogArgs
if ($LASTEXITCODE -ne 0) { throw "Recipe 解析失败: $($recipeJson -join ' ')" }
$recipeInfo = $recipeJson | ConvertFrom-Json
$Family = $recipeInfo.family
$Prefix = $recipeInfo.prefix

$BuildRoot = if ($OutputRoot) { $OutputRoot } else { Join-Path $ProjectRoot 'build' }
$FontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
$RegPath = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'

Write-Output "=========================================="
Write-Output "安装 $($Family) 到当前用户字体库"
Write-Output "=========================================="

# 预检: 所有字体文件必须存在, 缺失在任何变更前失败。
$subfamilies = @('Regular', 'Bold', 'Italic', 'BoldItalic')
$missing = @()
foreach ($sub in $subfamilies) {
    $srcFile = Join-Path $BuildRoot "$($recipeInfo.id)\$Prefix-$sub.ttf"
    if (-not (Test-Path -LiteralPath $srcFile)) { $missing += $srcFile }
}
if ($missing.Count -gt 0) {
    foreach ($m in $missing) { Write-Error "源文件不存在: $m" }
    throw "缺少 $($missing.Count) 个字体文件, 已中止安装"
}

# WhatIf: 只输出解析后的计划, 不加载原生库/不复制/不写注册表。
# (不依赖 cmdlet WhatIf 传播: 预检已通过, 此处显式分支。)
if ($WhatIfPreference) {
    foreach ($sub in $subfamilies) {
        $registryStyle = if ($sub -eq 'BoldItalic') { 'Bold Italic' } else { $sub }
        Write-Output "  [WhatIf] 注册表项: '$Family $registryStyle (TrueType)' -> $BuildRoot\$($recipeInfo.id)\$Prefix-$sub.ttf"
    }
    if ($ConfigureEditors) {
        Write-Output "  [WhatIf] 将同步 IDE 配置 fontFamily='$Family'"
    }
    Write-Output "  [WhatIf] 将广播 WM_FONTCHANGE"
    return
}

Add-Type -Name Native -Namespace Win32 -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int RemoveFontResource(string lpFileName);

[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int AddFontResource(string lpFileName);

[DllImport("user32.dll", CharSet = CharSet.Auto)]
public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
'@

foreach ($sub in $subfamilies) {
    $baseName = "$Prefix-$sub"
    $srcFile = Join-Path $BuildRoot "$($recipeInfo.id)\$baseName.ttf"
    $registryStyle = if ($sub -eq 'BoldItalic') { 'Bold Italic' } else { $sub }
    $regName = "$Family $registryStyle (TrueType)"

    $currentRegVal = (Get-ItemProperty -Path $RegPath -Name $regName -ErrorAction SilentlyContinue)."$regName"

    $candidates = @(
        (Join-Path $FontDir "$baseName.ttf"),
        (Join-Path $FontDir "$baseName-v42.ttf"),
        (Join-Path $FontDir "$baseName-v41.ttf")
    )

    $installedFile = $null
    foreach ($cand in $candidates) {
        try {
            Copy-Item -LiteralPath $srcFile -Destination $cand -Force -ErrorAction Stop
            $installedFile = $cand
            break
        } catch {
            # 当前槽位被系统进程锁定，尝试下一个槽位
        }
    }

    if (-not $installedFile) {
        Write-Error "无法写入字体 $baseName 到任何候选槽位，请关闭相关终端进程后重试"
        continue
    }

    if ($currentRegVal -and ($currentRegVal -ne $installedFile) -and (Test-Path -LiteralPath $currentRegVal)) {
        [Win32.Native]::RemoveFontResource($currentRegVal) | Out-Null
    }

    New-ItemProperty -Path $RegPath -Name $regName -Value $installedFile -PropertyType String -Force | Out-Null
    [Win32.Native]::AddFontResource($installedFile) | Out-Null
    Write-Output "  [OK] $regName -> 已安装至: $(Split-Path -Leaf $installedFile)"
}

# 异步广播 WM_FONTCHANGE 消息，通知系统所有打开的终端与编辑器刷新字体资源
$HWND_BROADCAST = [IntPtr]0xffff
$WM_FONTCHANGE = 0x001d
[Win32.Native]::PostMessage($HWND_BROADCAST, $WM_FONTCHANGE, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
Write-Output "  [OK] 已异步广播系统级 WM_FONTCHANGE 字体刷新事件"

if ($ConfigureEditors) {
    Write-Output "`n同步 IDE 配置..."
    $ides = @('Code', 'Trae CN', 'TRAE SOLO CN', 'Antigravity IDE', 'Kiro', 'QoderCN')
    foreach ($ide in $ides) {
        $settingsPath = Join-Path $env:APPDATA "$ide\User\settings.json"
        if (-not (Test-Path -LiteralPath $settingsPath)) { continue }

        try {
            $json = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $json.'terminal.integrated.fontFamily' = $Family
            $json.'editor.fontFamily' = $Family
            $out = $json | ConvertTo-Json -Depth 10
            [System.IO.File]::WriteAllText($settingsPath, $out, (New-Object System.Text.UTF8Encoding($false)))
            Write-Output "  [OK] $ide 配置已同步"
        } catch {
            Write-Warning "  [FAIL] $ide 配置更新失败: $_"
        }
    }
}

Write-Output "`n=========================================="
Write-Output "全部安装与环境配置已就绪！"
Write-Output "=========================================="
