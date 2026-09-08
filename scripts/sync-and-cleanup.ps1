# IDE fontFamily 同步 + 孤儿字体清理（review 修复项）
$ErrorActionPreference = 'Continue'
$fontDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
$regPath = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
Add-Type -Name Native -Namespace Win32 -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int RemoveFontResource(string lpFileName);
[DllImport("gdi32.dll", CharSet = CharSet.Auto)]
public static extern int AddFontResource(string lpFileName);
'@

# 1) 孤儿清理：注册表当前指向 -v4.ttf；删除同名无后缀旧文件 + RemoveFontResource
$removed = 0; $locked = 0
foreach ($s in @('Regular','Bold','Italic','BoldItalic')) {
    $orphan = Join-Path $fontDir "FiraCodeMapleMono-$s.ttf"
    if (Test-Path -LiteralPath $orphan) {
        [Win32.Native]::RemoveFontResource($orphan) | Out-Null
        try { Remove-Item -LiteralPath $orphan -Force -ErrorAction Stop; $removed++ }
        catch { $locked++ }
    }
}
Write-Output "orphan removed=$removed locked=$locked"

# 2) 注册表指向从 -v4.ttf 换回标准文件名（v4.1 内容已覆盖同路径旧 -v4 名义上的空缺，
#    此处直接把标准名文件装上：先试复制，被锁则保留 -v4 指向）
foreach ($s in @('Regular','Bold','Italic','BoldItalic')) {
    $base = "FiraCodeMapleMono-$s"
    $stdDest = Join-Path $fontDir "$base.ttf"
    $v4Src = Join-Path $fontDir "$base-v4.ttf"
    $newSrc = "D:\AgentWork\fonts\merged-v4\$base.ttf"
    $copied = $true
    try { Copy-Item -LiteralPath $newSrc -Destination $stdDest -Force -ErrorAction Stop }
    catch { $copied = $false }
    if ($copied) {
        # 标准名文件已是 v4.1 → 注册表改指标准名，删除 -v4 换名文件
        [Win32.Native]::RemoveFontResource($v4Src) | Out-Null
        try { Remove-Item -LiteralPath $v4Src -Force -ErrorAction Stop } catch {}
        New-ItemProperty -Path $regPath -Name "$base (TrueType)" -Value $stdDest -PropertyType String -Force | Out-Null
        [Win32.Native]::AddFontResource($stdDest) | Out-Null
        Write-Output "$base -> standard-name v4.1 installed"
    } else {
        # 锁定 → 用新名 -v41 注册 v4.1，注册表改指
        $tmpDest = Join-Path $fontDir "$base-v41.ttf"
        Copy-Item -LiteralPath $newSrc -Destination $tmpDest -Force
        New-ItemProperty -Path $regPath -Name "$base (TrueType)" -Value $tmpDest -PropertyType String -Force | Out-Null
        [Win32.Native]::AddFontResource($tmpDest) | Out-Null
        Write-Output "$base -> locked, registered as -v41.ttf"
    }
}

# 3) 六个 IDE fontFamily 同步到终态家族（R2 补全：terminal+editor 都指向 FiraCode Maple Mono）
$ides = @('Code','Trae CN','TRAE SOLO CN','Antigravity IDE','Kiro','QoderCN')
foreach ($ide in $ides) {
    $p = Join-Path $env:APPDATA "$ide\User\settings.json"
    if (-not (Test-Path -LiteralPath $p)) { Write-Output "$ide settings.json missing"; continue }
    $json = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
    $json.'terminal.integrated.fontFamily' = 'FiraCode Maple Mono'
    $json.'editor.fontFamily' = 'FiraCode Maple Mono'
    $out = $json | ConvertTo-Json -Depth 10
    # ConvertTo-Json 会转义中文为 \uXXXX，无功能影响；保持 UTF8 无 BOM 写回
    [IO.File]::WriteAllText($p, $out, (New-Object System.Text.UTF8Encoding($false)))
    Write-Output "$ide updated"
}
