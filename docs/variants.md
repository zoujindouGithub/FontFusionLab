# 字体变体说明与配置指南 (Font Variants & Configuration Guide)

本文档说明 **FiraCode Maple Mono** 的字体族系特点，以及在各主流终端与编辑器中的配置方法。

---

## 字体特性矩阵

| 特性 | 说明 | 适用场景 |
|---|---|---|
| **拉丁字符与数字** | 继承自 FiraCode，具备优美清晰的编程连字（Ligatures）与字符区分度 | 编程阅读、日常代码编写 |
| **CJK 中日文字形** | 继承自 Maple Mono CN，圆角微衬线设计，视觉柔和 | 中文注释、文档、多语言混排 |
| **Nerd Fonts 图标** | 完整包含 Nerd Fonts 图标集（Powerline, Devicons, FontAwesome 等） | 终端提示符（Starship/Oh My Posh）、状态栏 |
| **等宽对齐比例** | 严格保证 1 个汉字 = 2 个英文字符格宽（2:1 经典比例） | 终端 TUI、字符表格、代码对齐 |
| **RIBBI 四字面** | 包含 Regular（正体）、Bold（粗体）、Italic（斜体）、Bold Italic（粗斜体） | 语法高亮全覆盖 |

---

## 终端与编辑器配置

在完成字体安装后，系统识别的字体家族名称全局统一为：
```text
FiraCode Maple Mono
```

### 1. Windows Terminal

打开 Windows Terminal 设置（`Ctrl + ,`），可以在全局默认配置或特定 Profile（如 PowerShell / Command Prompt / WSL）中进行配置。

**图形界面**：
> 设置 -> 默认值（或具体 Profile） -> 外观 -> 字体面 -> 选择 **FiraCode Maple Mono**

**JSON 配置 (`settings.json`)**：
```json
{
  "profiles": {
    "defaults": {
      "font": {
        "face": "FiraCode Maple Mono",
        "size": 12.0
      }
    }
  }
}
```

### 2. VSCode 及衍生 IDE (Cursor, Trae, Antigravity, Kiro 等)

打开编辑器设置（`settings.json`），添加或修改以下两个配置项：

```json
{
  "editor.fontFamily": "'FiraCode Maple Mono', Consolas, monospace",
  "terminal.integrated.fontFamily": "FiraCode Maple Mono"
}
```

### 3. 连字开关控制 (Ligatures)

默认情况下，FiraCode 的编程连字（如 `=>`, `!=`, `===`）是开启的。如果不习惯连字：

- **VSCode / Cursor**：
  ```json
  "editor.fontLigatures": false
  ```
- **Windows Terminal** (1.22+)：
  ```json
  "font": {
    "face": "FiraCode Maple Mono",
    "features": { "calt": 0 }
  }
  ```

---

## 常见问题 (FAQ)

**Q: 安装后终端或编辑器没有立即识别新字体？**  
A: 请完全关闭并重新启动对应的终端或编辑器进程。部分应用仅在进程启动时扫描系统字体表。

**Q: Windows 提示字体文件已被占用无法覆盖？**  
A: 运行仓库提供的 `scripts/install.ps1`，脚本会自动检测文件锁定并采用平滑热更新槽位机制完成安全更新，无需重启系统。
