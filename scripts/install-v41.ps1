# 安装 v4.1（lsb 修复版）：标准名被锁定 → 注册 -v41 名；随后尽力清旧缓存
$ErrorActionPreference = 'Continue'
$fontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
$regPath = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
Add-Type -Name Native -Namespace Win32 -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int RemoveFontResource(string lpFileName);
[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int AddFontResource(string lpFileName);
'@

foreach ($s in @('Regular','Bold','Italic','BoldItalic')) {
    $base = "FiraCodeMapleMono-$s"
    $src = "D:\AgentWork\fonts\merged-v4\$base.ttf"
    $stdDest = Join-Path $fontDir "$base.ttf"
    $copied = $true
    try { Copy-Item -LiteralPath $src -Destination $stdDest -Force -ErrorAction Stop } catch { $copied = $false }
    if ($copied) {
        $target = $stdDest
        Write-Output "$base -> standard name updated"
    } else {
        $target = Join-Path $fontDir "$base-v41.ttf"
        Copy-Item -LiteralPath $src -Destination $target -Force
        Write-Output "$base -> locked; registered as -v41.ttf"
    }
    New-ItemProperty -Path $regPath -Name "$base (TrueType)" -Value $target -PropertyType String -Force | Out-Null
    [Win32.Native]::AddFontResource($target) | Out-Null
}
# 斜体/粗斜体没修 lsb（它们是 Maple 原字面无注入），但 v4.1 的 RIBBI 命名要同步——斜体文件同源重建
Write-Output '--- done ---'
