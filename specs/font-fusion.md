# Spec: FiraCode × Maple Mono 混血字体（FiraCode Maple Mono）

本 spec 由会话需求链固化而成（无 issue tracker，无 PRD 文件）。逐条为验收依据。

## 需求

- **R1** 下载 https://github.com/subframe7536/maple-font 的字体并应用到当前终端（pwsh）。
- **R2** 保障 Trae IDE 等 VSCode 衍生 IDE 能正确识别该字体。
- **R3** 说明该字体有哪几种变体，以及具体如何切换。
- **R4** 改试 https://github.com/ryanoasis/nerd-fonts/tree/master/patched-fonts/FiraCode ，切给 pwsh 看效果。
- **R5** FiraCode 无中文内嵌，需回退使用先前下载的 Maple Mono。
  - 用户在三个方案中选定：**合并混血字体**（FiraCode 拉丁+图标 / Maple CJK）。
- **R6** 把自建家族改名：`FiraCode Maple CN` → `FiraCode Maple Mono`。
- **R7** 参照 https://github.com/SpaceTimee/Fusion-JetBrainsMapleMono 的思路优化自建字体。
- **R8** 优化方向明确为：**仅对 CJK 字形注入 hinting，拉丁保留原指令**。
- **R9** 产物须可在 Windows Terminal 的 pwsh profile 中生效，且不影响其他 profile。

## 隐含约束

- 用户级安装（无管理员权限）。
- 中英 2:1 等宽对齐不得破坏（终端表格/边框依赖）。
- 不得静默劣化拉丁字形渲染质量。
