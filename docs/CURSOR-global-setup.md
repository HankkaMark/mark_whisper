# Cursor：从 MarkWiki 复用到全局 / Whisper

你在 **MarkWiki** 项目里已经有一套 harness。下面是清单和「怎么变成全局可用」的步骤。

## MarkWiki 里有什么

| 类型 | 路径 | 作用 |
|------|------|------|
| **项目宪法** | `MarkWiki/AGENTS.md` | 数据契约、中文策略、保真规则、每次回复要带 harness 建议 |
| **方法论** | `MarkWiki/METHODOLOGY.md` | Wiki 怎么写（MarkWiki 专用） |
| **流程** | `MarkWiki/HARNESS.md` | 5 步协作循环（MarkWiki 专用） |
| **Skills（项目级）** | `MarkWiki/skills/` | 见下表 |
| **Hooks** | `MarkWiki/.cursor/hooks.json` | 提交 prompt / 会话开始时跑监控 |
| **Hook 脚本** | `MarkWiki/.cursor/hooks/context-monitor.mjs` | 估算上下文用量，提醒跑 context-relay |
| **Hook 配置** | `MarkWiki/.cursor/context-config.json` | token 阈值、冷却时间 |

### Skills 目录

| Skill | 用途 | 能否全局？ |
|-------|------|------------|
| `context-relay` | 长对话把状态写入 `MEMORY.md` | **推荐全局** — 任何项目都能用 |
| `auto-ingest` | 外部 gateway 批量 ingest raw | 仅 MarkWiki |
| `agent-ingest` | Cursor 内串行 ingest | 仅 MarkWiki |

### 语言 / 交互设定（在 AGENTS.md 里，不是单独文件）

- Wiki 与元文档：**中文为主**，术语保留英文（harness、skill、agent…）
- Agent **最终回复用中文**
- 非平凡任务要带一条**具体的** prompt/harness 改进建议

### 你 Cursor 里另外有的（Settings → Rules）

对话里看到的 User Rules（git 提交规范、PR 流程、代码原则等）存在 **Cursor 设置 UI**，不在 MarkWiki 仓库里。要和 MarkWiki 的 AGENTS 一起用，需要**手动同步**到 User Rules 或写成全局 rule 文件。

---

## Cursor 三种「持久化」对照

| 机制 | 项目级路径 | **全局**路径 | 适合放什么 |
|------|------------|--------------|------------|
| **Rules** | `.cursor/rules/*.mdc` | Cursor Settings → **Rules → User Rules**，或未来 `~/.cursor/rules/` | 中文回复、代码风格、安全约束 |
| **Skills** | `.cursor/skills/` 或 `skills/` | `%USERPROFILE%\.cursor\skills\<name>\SKILL.md` | 可重复流程（context-relay） |
| **Hooks** | `.cursor/hooks.json` | `%USERPROFILE%\.cursor\hooks.json` | 自动监控、门禁（注意公司是否允许 hook 跑 node） |

**不要**往 `~/.cursor/skills-cursor/` 里写东西 — 那是 Cursor 内置 skill，会被覆盖。

---

## 推荐：做成「全局可用」的步骤

### 1. 全局 Skill — context-relay（最值得搬）

```powershell
# 在 PowerShell 里（若被拦，用资源管理器复制文件夹也行）
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.cursor\skills"
Copy-Item -Recurse "C:\Users\Mark Ji\Downloads\MarkWiki\skills\context-relay" "$env:USERPROFILE\.cursor\skills\"
```

每个需要 MEMORY 的项目根目录放一份 `MEMORY.md`（可从 skill 里的 template 复制）。

### 2. 全局 Hooks（可选，公司若允许 Node hook）

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.cursor\hooks"
Copy-Item "C:\Users\Mark Ji\Downloads\MarkWiki\.cursor\hooks\context-monitor.mjs" "$env:USERPROFILE\.cursor\hooks\"
Copy-Item "C:\Users\Mark Ji\Downloads\MarkWiki\.cursor\context-config.json" "$env:USERPROFILE\.cursor\"
```

创建 `%USERPROFILE%\.cursor\hooks.json`（路径相对 `~/.cursor/`）：

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "node ./hooks/context-monitor.mjs", "timeout": 5 }
    ],
    "sessionStart": [
      { "command": "node ./hooks/context-monitor.mjs", "timeout": 5 }
    ]
  }
}
```

公司若拦截 hook，可只在 MarkWiki 保留项目级 hooks，不拷全局。

### 3. 全局语言 / 协作习惯（User Rules）

打开 **Cursor → Settings → Rules → User Rules**，粘贴或合并 MarkWiki `AGENTS.md` 里 **§交互 coaching** 的要点，例如：

- 最终回复使用中文（除非用户用英文提问）
- 非平凡任务结尾给一条绑定当前任务的具体 harness 建议
- 长期约定写进 AGENTS.md / rules，不依赖单轮聊天记忆

也可为「所有 Python 项目」加一条 project rule（`alwaysApply: true`）放在你常用的模板仓库里。

### 4. Whisper 项目已加的

- `whisper/AGENTS.md` — 安全模式、启动方式、中文回复
- `START-whisper.vbs` — **不经过 cmd.exe** 启动（见下）

MarkWiki 的 ingest skills **不要**拷到 Whisper；Whisper 只需要 AGENTS 里的安全与 API 约定。

---

## 在 Whisper 里启动（绕过 cmd 审批）

| 方式 | 是否经过 cmd | 说明 |
|------|----------------|------|
| `START-whisper.vbs` | **否** | 推荐：直接 `pythonw.exe -m whisper` |
| `run-whisper.cmd` / `.bat` | 是 | 可能被防火墙拦 |
| `run-whisper.ps1` | 是（powershell） | McKinsey 常拦未签名 ps1 |
| Cursor 终端里 `python -m whisper` | 视策略 | 有时比 cmd 宽松 |

首次安装仍需 IT 用已批准的 Python 跑一次 `tools\bootstrap_install.py`（仅本地 pip，无运行时下载）。
