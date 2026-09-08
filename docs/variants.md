# Maple Mono 字体变体说明与切换指南（R3 沉淀）

来源：[subframe7536/maple-font](https://github.com/subframe7536/maple-font) v7.9。

## 变体矩阵

命名 = **字形风格 × 发行格式** 两个维度的组合。

### 维度一：字形风格（决定字符长相）

| 后缀 | 含义 | 适用 |
|---|---|---|
| （无后缀） | 默认连字版，圆润风格，`=>` `!=` 合并为单箭头形 | 默认推荐 |
| `NL` | No Ligature，禁用所有连字 | 不喜欢连字 |
| `Normal` | 字形比例接近 JetBrains Mono（更窄更传统），保留连字 | JetBrains 用户 |
| `NormalNL` | JetBrains 风格 + 无连字 | 两者都要 |

### 维度二：发行格式（决定图标/中文支持与渲染方式）

| 后缀 | 含义 |
|---|---|
| `NF` | 内嵌 Nerd Font 图标（终端提示符必需） |
| `CN` | 内嵌中文宽字形（思源系，中英 2:1 对齐） |
| `NF-CN` | 两者都有 |
| `Variable` | 可变字体，单文件全字重轴（200-800） |
| `-AutoHint` / 无标记 | hinted 版低分辨率（≤1080P）更锐利 |

下载名示例：`MapleMono-NF-CN.zip` = 默认风格 + 图标 + 中文。

## 本机已安装家族与切换

| 家族名 | 来源 | 当前用途 |
|---|---|---|
| `Maple Mono NF CN` | 官方 NF-CN hinted | WT defaults（Git Bash/cmd/WSL 等） |
| `FiraCode Maple Mono` | 本仓库合成（FiraCode 拉丁 + Maple CJK） | WT pwsh profile + 6 个 VSCode 系 IDE |
| `FiraCode Nerd Font Mono` | 官方 NF Mono | 备用（纯拉丁场景） |
| `JetBrains Maple Mono` | [SpaceTimee/Fusion-JetBrainsMapleMono](https://github.com/SpaceTimee/Fusion-JetBrainsMapleMono) | 备用（JetBrains 风格合成的官方版） |

## 切换方法

**Windows Terminal**：`settings.json` → `profiles.defaults.font.face`（全局）或具体 profile 内加 `font.face` 覆盖（如 pwsh）。GUI 路径：设置 → [profile] → 外观 → 字体面。

**VSCode 系 IDE**：`settings.json` 两个键：
```json
{
  "terminal.integrated.fontFamily": "FiraCode Maple Mono",
  "editor.fontFamily": "FiraCode Maple Mono"
}
```

**字重**：WT 用 `"font": { "face": "...", "weight": "medium" }`；VSCode 用 `"editor.fontWeight": 500`。

**连字开关**：VSCode `"editor.fontLigatures": false`；WT 1.22+ `"font": { "features": { "calt": 0 } }`。

## 注意

- 已开标签/窗口需重启才能加载新字体或新配置。
- 换名注册（`-v4.ttf` 等）的旧文件在字体被占用时无法删除，注销后手动清理。
