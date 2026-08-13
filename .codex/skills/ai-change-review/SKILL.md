---
name: ai-change-review
description: 为工程内真实写入、新增或删除的源代码维护 MyCocs 审核包：在首次修改前保存不可变快照，代码稳定后同步真实 diff，并为每个改动块编写中文的原始逻辑、修改后逻辑和需求关系说明。仅在即将实际改代码、继续同一功能修改或用户明确点名 ai-change-review 时使用；讨论方案、只读分析、排查但尚未修改或只做代码审核时不要使用。
---

# AI 修改审核包

从工程根目录运行本 Skill 的脚本，按固定格式交付 `MyCocs/<change-id>/`。格式是首要约束；第一次填写时直接遵守本文件，不要先写错再依赖 `validate` 纠正。

## 定位工程与脚本

1. 将当前工作区根目录作为源工程根目录，并在该目录运行所有命令。
2. 使用与本 `SKILL.md` 同目录的 `scripts/review_package.py`。下文以 `<review-script>` 表示它的实际路径。
3. 不假定 Skill 安装在某个固定隐藏目录；它可能位于 `.codebuddy`、`.agents`、`.codex`、`.cursor` 或其他 Skill 根目录。
4. 首次修改时选用表达功能的英文 kebab-case `<change-id>`；继续同一功能时复用已有 ID。

执行命令前，必须把 `<review-script>` 替换为当前已加载 Skill 中脚本的绝对路径；绝不能原样执行占位符。

不要为了猜测已有 ID 而全工程搜索。存在多个合理候选且无法从上下文确定时，询问用户。

## 固定交付目录

```text
MyCocs/<change-id>/
├── originals/                         # 首次修改前的不可变快照
│   └── <sourcePath>
├── modified/                          # sync 生成的修改后快照
│   └── <sourcePath>
├── docs/
│   └── 用户需求.md
├── files.json
└── review.json
```

- `originals/` 只由 `backup` 建立，绝不能覆盖或手改。
- `modified/` 只由 `sync` 根据当前源文件生成，不要手工创建或编辑。删除文件没有对应的修改后快照。
- `files.json` 由 `init`、`backup` 和 `sync` 维护；不要手工重建。
- `review.json` 的结构和 diff 元数据由脚本维护；Agent 只调整 `readingOrder` 并填写四个中文说明字段。

## 固定文件格式

### `docs/用户需求.md`

必须使用 UTF-8，并严格按编号深度匹配 Markdown 标题层级：

```markdown
# 用户需求

## REQ-001 整体需求标题

说明用户遇到的场景、期望行为和可观察结果。每项正文至少 24 个非空白字符。

### REQ-001.1 子需求标题

说明更具体的触发条件、期望行为和可验证结果。每项正文至少 24 个非空白字符。

#### REQ-001.1.1 细分需求标题

说明最具体的场景和验收结果。每项正文至少 24 个非空白字符。
```

固定规则：

- `REQ-001` 使用 `##`，`REQ-001.1` 使用 `###`，每增加一个编号段就增加一个 `#`，最多到 `######`。
- 每个需求标题至少 4 个非空白字符；编号不得重复。
- 子需求的父需求必须已经写在前面。
- 每项都要说明场景、期望行为和可观察结果，不能只有标题。
- 只记录用户明确或确认的需求，不把实现选择、顺手优化或猜测写成需求。
- 用户改变需求时保留最终确认内容；删除已撤销且代码不再实现的旧需求。
- 禁止使用“请填写”“待补充”“TODO”“TBD”“待确认”“后续完善”“同上”“满足需求”“优化逻辑”等占位或空泛表述。

### `files.json`

顶层和文件项只能包含下面列出的字段：

```json
{
  "schemaVersion": "review-package-v1",
  "changeId": "example-change",
  "title": "本次修改的中文标题",
  "sourceRoot": ".",
  "createdAt": "2026-08-01T07:00:00Z",
  "updatedAt": "2026-08-01T08:00:00Z",
  "files": [
    {
      "id": "file-0123456789ab",
      "fileName": "Example.cpp",
      "sourcePath": "Source/Module/Example.cpp",
      "originalPath": "originals/Source/Module/Example.cpp",
      "originalHash": "0000000000000000000000000000000000000000000000000000000000000000",
      "status": "modified",
      "language": "cpp"
    }
  ]
}
```

固定规则：

- `schemaVersion` 必须是 `review-package-v1`；`changeId` 必须与目录名相同。
- `sourceRoot` 固定为 `.`，表示当前工程根目录；不得写绝对路径。
- `id` 由脚本生成，格式为 `file-` 加 12 位小写十六进制字符，不要手改。
- `sourcePath` 必须是相对工程根目录的规范正斜杠路径，不得是绝对路径或包含 `..`。
- `status` 只能是 `added`、`modified`、`deleted`。
- 新增文件必须使用 `"originalPath": null` 和 `"originalHash": null`。
- 修改或删除文件必须有 `originalPath`；它固定为 `originals/<sourcePath>`。
- 修改或删除文件的 `originalHash` 必须是原始快照完整字节的 64 位小写 SHA-256。
- `createdAt` 和 `updatedAt` 使用 ISO 8601 时间；通常由脚本维护。

新增文件项的完整形态：

```json
{
  "id": "file-0123456789ab",
  "fileName": "NewFile.cpp",
  "sourcePath": "Source/Module/NewFile.cpp",
  "originalPath": null,
  "originalHash": null,
  "status": "added",
  "language": "cpp"
}
```

### `review.json`

顶层、文件项和改动块只能包含下面列出的字段：

```json
{
  "schemaVersion": "review-package-v1",
  "changeId": "example-change",
  "readingOrder": [
    "file-aaaaaaaaaaaa"
  ],
  "files": [
    {
      "fileId": "file-aaaaaaaaaaaa",
      "changes": [
        {
          "id": "change-0123456789ab",
          "title": "逐个筛选有效的候选目标",
          "kind": "modify",
          "before": {
            "startLine": 10,
            "endLine": 18,
            "contentHash": "1111111111111111111111111111111111111111111111111111111111111111"
          },
          "after": {
            "startLine": 10,
            "endLine": 27,
            "contentHash": "2222222222222222222222222222222222222222222222222222222222222222"
          },
          "originalLogic": "原流程在取得候选列表后只读取第一个对象，没有继续检查对象是否有效，也不会在第一个对象不可用时尝试后续候选，因此后面仍有可用对象时流程也会提前失败。",
          "modifiedLogic": "修改后的流程会按列表顺序检查每个候选对象，只有对象有效且满足业务条件时才返回；当前候选不合格时继续检查下一个，全部候选都不合格后再进入既有兜底流程。",
          "requirementRelation": "[REQ-001.1.1] 该需求要求首个候选不可用时继续寻找后续有效对象；本段循环让每个候选依次接受相同检查，使后续有效对象能够被选中，用户最终不会再因首个坏候选直接失败。"
        }
      ]
    }
  ]
}
```

固定规则：

- `schemaVersion` 必须是 `review-package-v1`；`changeId` 必须与目录名相同。
- `readingOrder` 必须且只能包含 `files.json.files` 的全部 ID，每个恰好一次。
- `review.json.files` 必须且只能包含全部文件，每个 `fileId` 恰好一次。
- `kind` 只能是 `add`、`modify`、`delete`。
- `startLine` 和 `endLine` 从 1 开始并包含两端；`contentHash` 是对应行以 `\n` 连接后的 SHA-256。
- 新增块的 `before` 固定为 `{"startLine": 0, "endLine": 0, "contentHash": ""}`。
- 删除块的 `after` 固定为 `{"startLine": 0, "endLine": 0, "contentHash": ""}`。
- `id`、`kind`、`before`、`after` 由 `sync` 生成，Agent 不得修改。
- `title` 至少 6 个非空白字符，用中文说明本段职责。
- `originalLogic`：新增块至少 12 个非空白字符，其他块至少 30 个；说明原触发条件、判断、数据流和结果。
- `modifiedLogic` 至少 35 个非空白字符；说明真实新增、删除或改变的分支以及最终结果。
- `requirementRelation` 至少 35 个非空白字符，必须以 `[REQ-xxx]` 开头。可连续引用多个编号，例如 `[REQ-001.1.1][REQ-001.2]`。
- 引用编号必须真实存在于 `docs/用户需求.md`；若需求有子项，必须引用最具体的末级需求，不能只引用父需求。
- 四个说明字段都要包含清楚的中文，禁止占位、空泛套话或“同上”。
- 不得添加 `risks` 或任何其他字段；JSON 不得包含注释、尾逗号、重复键或 Markdown 包裹。

## 执行流程

### 1. 初始化并一次写好用户需求

首次实际修改时执行：

```powershell
python "<review-script>" init <change-id> --title "<中文标题>"
```

初始化后、修改代码前，立即按上面的固定格式写好 `MyCocs/<change-id>/docs/用户需求.md`。继续修改时先读取该文件；需求发生变化时先同步需求文档。

### 2. 先登记每个文件，再修改

修改或删除现有文件前执行：

```powershell
python "<review-script>" backup <change-id> "Source/相对/文件.cpp"
```

创建新文件前执行：

```powershell
python "<review-script>" backup <change-id> "Source/相对/新文件.cpp" --added
```

遵守以下约束：

- 不得先改后备份。
- 已有快照时继续使用，不得覆盖 `originals/`。
- 后续新增涉及文件时，也必须先单独登记。
- 若误改后没有可信原文件可恢复，立即停止并告知用户。
- 同时遵守工程根目录的版本控制规则；审核包自身不要加入源码变更列表。

### 3. 代码稳定后同步一次

```powershell
python "<review-script>" sync <change-id>
```

`sync` 会更新状态、生成 `modified/`、计算真实改动块，并保留内容未变化的已有说明。仅当代码再次变化时重新运行；不要用它反复试探格式。

### 4. 一次完成 `review.json`

1. 读取完整 `files.json`、`review.json` 和 `docs/用户需求.md`。
2. 读取 [references/explanation-guide.md](references/explanation-guide.md)。
3. 按依赖关系一次调整 `readingOrder`。
4. 按阅读顺序逐个改动块填写 `title`、`originalLogic`、`modifiedLogic`、`requirementRelation`。
5. 写入前对照本文件的完整 JSON 结构和最小长度自检，集中保存一次。

不要修改脚本生成的 diff 元数据，不要手工重建整个 JSON。

### 5. 最终校验

```powershell
python "<review-script>" validate <change-id>
```

校验失败时只修复报错指出的字段。纯说明或 JSON 格式问题不要重新运行 `sync`；只有代码真实变化后才重新同步。校验通过前不要声称审核资料已完成。

## 完成回报

向用户报告 `<change-id>`、相对审核包路径、文件数、改动块数和最终校验结果。
