# Zotero Analytical Writer

一个用于论文精读笔记生成的 Codex skill 包，包含：

- `SKILL.md`：精读流程与约束说明
- `论文精读模板.md`：Obsidian 精读模板
- `README.md`：使用说明

## 目录结构

```text
zotero-analytical-writer-github/
├── README.md
├── SKILL.md
└── 论文精读模板.md
```

## 用途

这个 skill 用来接收论文原始语料，按中文学术笔记风格进行重构，并严格套用精读模板输出 Obsidian 笔记。

它特别强调：

- Frontmatter 字段必须高度提炼，不能机械复制摘要
- 研究区、数据来源、方法、核心变量等字段要精准提取
- 公式识别要防乱码、防胡编，并在需要时调用 OCR
- 正文分析区要过滤作者单位、基金号、投稿须知等学术噪音

## 使用方式

1. 将本目录上传到 GitHub 仓库。
2. 使用时确保 `SKILL.md` 与 `论文精读模板.md` 保持在同一目录。
3. `SKILL.md` 当前通过相对路径 `./论文精读模板.md` 引用模板，因此下载后无需修改为本机绝对路径。

## 建议

- 如果你后续要给别人分发，建议仓库名也使用 `zotero-analytical-writer`
- 如果你未来更换模板文件名，记得同步修改 `SKILL.md` 中的模板路径
- 如果你希望模板进一步参数化，可以后续再补一个示例输入输出
