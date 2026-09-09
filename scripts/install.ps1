# FiraCode Maple Mono 终态安装与环境同步脚本
# 动态解析脚本目录，支持槽位热替换与系统级字体变更广播
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

[DllImport("user32.dll", CharSet = CharSet.Auto)]
public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
'@

$subfamilies = @('Regular', 'Bold', 'Italic', 'BoldItalic')

# 1. 复制字体并向 GDI 与注册表注册
foreach ($sub in $subfamilies) {
    $baseName = "FiraCodeMapleMono-$sub"
    $srcFile = Join-Path $MergedDir "$baseName.ttf"

    if (-not (Test-Path -LiteralPath $srcFile)) {
        Write-Error "源文件不存在: $srcFile"
        continue
    }

    # 获取注册表当前指向的路径
    $currentRegVal = (Get-ItemProperty -Path $RegPath -Name "$baseName (TrueType)" -ErrorAction SilentlyContinue)."$baseName (TrueType)"

    # 定义候选槽位：标准名 -> -v42 -> -v41
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

    # 如果切换到了新槽位，解除旧槽位的 GDI 注册
    if ($currentRegVal -and ($currentRegVal -ne $installedFile) -and (Test-Path -LiteralPath $currentRegVal)) {
        [Win32.Native]::RemoveFontResource($currentRegVal) | Out-Null
    }

    # 注册新槽位到注册表与 GDI
    New-ItemProperty -Path $RegPath -Name "$baseName (TrueType)" -Value $installedFile -PropertyType String -Force | Out-Null
    [Win32.Native]::AddFontResource($installedFile) | Out-Null
    Write-Output "  [OK] $baseName -> 已安装至: $(Split-Path -Leaf $installedFile)"
}

# 2. 异步广播 WM_FONTCHANGE 消息，通知系统所有打开的终端与编辑器刷新字体资源
$HWND_BROADCAST = [IntPtr]0xffff
$WM_FONTCHANGE = 0x001d
[Win32.Native]::PostMessage($HWND_BROADCAST, $WM_FONTCHANGE, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
Write-Output "  [OK] 已异步广播系统级 WM_FONTCHANGE 字体刷新事件"

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
