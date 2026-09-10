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

# 旧版本槽位残留清理。为什么必须做：旧产线把同 family 的 TTF 注册成文件名词形
# (如 'FiraCodeMapleMono-Regular (TrueType)' -> FiraCodeMapleMono-Regular-vNN.ttf)。
# GDI 对同一 family 多文件去重选字时, 这些残留会遮蔽本产线新注册的字形
# (实测: 新装 Maple CJK 被旧 Sarasa 时代 -v42 文件顶掉)。因此升级安装必须与新装
# 同批清理, 保证"单一幂等入口"。识别: 文件名匹配 FiraCode(Maple|Sarasa)Mono-*-vNN.ttf
# 且位于用户字体目录; 只删这些带版本槽的文件及其文件名词形登记项,
# 本脚本自用的标准/槽位登记项 (family 词形) 不受影响。
$stalePattern = '^FiraCode(Maple|Sarasa)Mono-.*-v\d+\.ttf$'
$staleFiles = @()
if (Test-Path -LiteralPath $FontDir) {
    $staleFiles = @(Get-ChildItem -LiteralPath $FontDir -Filter '*.ttf' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match $stalePattern })
}
$regInfo = Get-ItemProperty -Path $RegPath -ErrorAction SilentlyContinue
$stale = foreach ($f in $staleFiles) {
    $referencing = @()
    if ($regInfo) {
        $referencing = @($regInfo.PSObject.Properties | Where-Object {
            $_.Name -like '* (TrueType)' -and (([string]$_.Value | Split-Path -Leaf) -eq $f.Name)
        })
    }
    # 只要存在任一"非文件名词形"登记项(本产线 family 词形合法注册)指向该文件,
    # 它就是活槽位, 绝不能删; 只有孤儿文件或纯旧词形登记的文件才是残留。
    $live = @($referencing | Where-Object { $_.Name -notmatch '^FiraCode(Maple|Sarasa)Mono-' })
    if ($live.Count -gt 0) { continue }
    [pscustomobject]@{ File = $f.FullName; Name = $f.Name;
        EntryNames = @($referencing | ForEach-Object { $_.Name }) }
}

# WhatIf: 只输出解析后的计划 (含 CLEAN 条目), 不加载原生库/不复制/不写注册表/不删除。
# (不依赖 cmdlet WhatIf 传播: 预检已通过, 此处显式分支。)
if ($WhatIfPreference) {
    foreach ($s in $stale) {
        $names = if ($s.EntryNames.Count) { $s.EntryNames -join ', ' } else { '(无登记项)' }
        Write-Output "  [WhatIf] CLEAN 旧版本槽位: $($s.Name) 登记项: $names"
    }
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

# 先清理残留再写入新文件: 释放 GDI 锁 → 删文件 → 删登记项。文件被占用则立即报错
# 停止 (注册表保持原样), 不允许半清理状态进入安装。
foreach ($s in $stale) {
    [Win32.Native]::RemoveFontResource($s.File) | Out-Null
    try {
        Remove-Item -LiteralPath $s.File -Force -ErrorAction Stop
    } catch {
        Write-Error "旧版本槽位文件被占用, 无法清理: $($s.File) — 请关闭使用该股位的终端/编辑器后重试。安装已中止, 未做任何部分变更。"
        throw $_
    }
    foreach ($n in $s.EntryNames) {
        Remove-ItemProperty -Path $RegPath -Name $n -ErrorAction Stop
    }
    $namesText = if ($s.EntryNames.Count) { $s.EntryNames -join ', ' } else { '(无登记项)' }
    Write-Output "  [CLEAN] 移除旧版本槽位: $($s.Name) 登记项: $namesText"
}

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
