# Quadrant · 纯 Markdown 待办系统（人 + AI Agent 共用）

[English](README.md) · [设计说明](docs/design.md) · [Agent skill](skill/quadrant/SKILL.md)

> 一行一条任务，一个文件一个项目。没有数据库、没有账号、没有云端黑箱。

<p align="center">
  <img src="docs/screenshot-board.png" alt="Quadrant 看板：P×U 九宫格" width="100%">
</p>

待办就是一堆 `.md` 文件。你可以用 Obsidian、VSCode、vim 或手机备忘录改它们，也可以
直接对 AI 说「这周五之前把接口错误码整理成表」，让它落到正确的那一行。内置面板是可选的
化妆品 —— **没有它，`grep` + 编辑器照样能用**。

## 为什么再造一个待办

| | Notion / Todoist | Obsidian 插件 | **Quadrant** |
| --- | --- | --- | --- |
| 数据在哪 | 别人的服务器 | 本地 md | **本地 md（唯一真源）** |
| 离线 | ✗ | ✓ | ✓ |
| 能 `git log` 看历史 | ✗ | 半 | ✓ |
| AI Agent 能安全读写 | ✗ 要 API + 授权 | ✗ 格式不一 | **✓ 就是改一行文本** |
| 拖拽排序 | ✓ | 看插件 | ✓（顺序单独存，不污染 md） |
| 优先级 / 四象限 | ✓ | 各异 | **P×U 九宫格，字段就是 `#P1 #U2`** |

三条核心想法：

1. **捕获零成本**：想不清楚的先丢 `0-inbox.md`，一行一个，不整理。
2. **优先级是字段不是顺序**：改优先级 = 改一个字母（`#P2` → `#P1`），绝不搬段落。
3. **Agent 只改该改的那一行**：行序、缩进详情、换行符都不碰，所以人和 Agent 能同时改。

## 60 秒跑起来

```bash
git clone https://github.com/chillrain666/quadrant-md.git
cd quadrant-md
python scripts/init_tasks.py          # 生成 tasks/（目录 + 示例数据）
cd app
uv sync                               # 或：pip install -r requirements.txt
uv run python main.py                 # → http://127.0.0.1:8000
```

看到九宫格就成功了。前端构建产物已随仓库提供，**不用装 Node**。

用别处的数据目录（比如你已有的笔记库）：

```bash
TASKS_ROOT=/path/to/my/tasks uv run python main.py        # macOS / Linux
set TASKS_ROOT=D:\notes\tasks && uv run python main.py    # Windows
```

## 目录就是"数据库"

```
tasks/
├── 0-inbox.md       捕获箱：还没想清楚的，随手一行（不上看板）
├── 1-active/        正在做：一个文件 = 一个项目      ← 四象限只看这里
│   ├── study/study.md
│   └── life/chores/chores.md
├── 2-notes/         长详情（不扫描）
├── 3-log/           时间线日志，只增不改（不扫描）
├── 4-someday.md     明确的"将来某天" + 灵感（单独面板）
├── 5-archive/       完结项目（不扫描）
└── watch/           清单轨道：追剧 / 追文 / 在读书（单独面板，不过 P/U）
```

四条轨道各扇各的：任务进象限、清单不进、灵感进 someday、捕获的**哪儿都不显示**。
最后一条是刻意的 —— 一被看见就会开始整理，而捕获的意义正是先别整理。

## 一行任务长什么样

```markdown
- [ ] T-261021-1 Read chapter 3 of DDIA #P1 #U2 #reading DDL:2026-11-05
      缩进的行是这条任务的详情，原样保留，删任务时一起删
```

| 片段 | 含义 |
| --- | --- |
| `- [ ]` `- [x]` `- [-]` | 待办 / 完成 / 搁置 |
| `T-261021-1` | 全局唯一 ID：`T-` + `YYMMDD` + `-` + 当天序号，永不变 |
| `#P1`~`#P3` | 重要性，P1 最重要 |
| `#U1`~`#U3` | 紧迫性，U1 最急 |
| `#标签` | 可多个，支持中文 / 大写 / `a/b` |
| `DDL:2026-11-05` | 截止日 |
| `DONE:2026-10-21` | 完成日（打勾时自动补） |

**四象限是 `P × U` 现算的，不写进文件** —— 所以改优先级只是改两个字符。
看板用 3×3 九宫格（P 一行、U 一列），因为 P、U 各有三档，硬压成四格会丢信息。

## 给 AI Agent 用（重点）

`skill/quadrant/` 是一个 agent skill（`SKILL.md` 结构，Claude Agent Skills / pi /
Cursor 等都认）。放进 Agent 的 skills 目录后，它就知道：

- 用户说一句话 → 该落到哪个文件（"记一下" → inbox；"这周要做" → active；
  "以后" → someday；"开始看某剧" → watch）
- 怎么写不破坏文件（只追加、只改那一行、换行符逐文件保留、ID 现算）
- 怎么跑面板、周复盘五步怎么做

对话就变成：

> **你**：记一下，想试试把周复盘改成两周一次
> **Agent**：写进 `tasks/0-inbox.md`：`- Try a two-week review cycle`

> **你**：这周五之前把接口错误码整理成表，挺重要的
> **Agent**：写进 `tasks/1-active/work/demo-project.md`：
> `- [ ] T-261021-18 Turn the API error codes into a table #P2 #U1 #work DDL:2026-10-23`

> **你**：这条做完了
> **Agent**：`- [x] ... DONE:2026-10-23`（只改两个地方）

装到 pi：

```bash
cp -r skill/quadrant ~/.pi/agent/skills/
```

其它支持 skills 的客户端放到对应目录即可；不支持 skills 的，把 `SKILL.md`
当规则文件喂给 Agent 也一样能用。

## 面板能力

- **3×3 九宫格**：P 一行、U 一列；空格子也画出来（一眼看出哪格空）
- **搜索**：标题 / 详情行 / 标签 / 项目 / 目录 / ID，认大小写、认同义词
- **筛选**：P、U 两条独立轴 + 时间 + 状态 + 目录多级 + 标签
- **编辑**：点任务弹右侧抽屉，改标题 / P / U / 状态 / DDL / 标签，**不动布局**
- **回写**：打勾盖 `DONE:`、新建、删除、拖拽排序，全部直接改 md
- **Focus**：给任务打 `#TopN`，按「过期 → 今天 → P1U1 → …」自动排序
- **追更 / 清单**：追剧、追文、在读书，单独 tab，不过 P/U
- **someday**：卡片只露摘要，点开看全文，卡片可四向拖动排序
- **拖到 tab 上**：拖到 **Focus** = 给它加 `#TopN` 标签；拖到 **someday** = 整条（含详情）
  移到 `4-someday.md`
- **每个面板都能搜**：搜索框对看板、Focus、追更、someday 同时生效
- **不用手填 ID**：手写的任务第一次被编辑时自动补 ID；重复 ID 会自检并一键重编号
- **中英文切换**：右上角 EN / 中文，按浏览器记住

<p align="center">
  <img src="docs/screenshot-focus.png" width="49%" alt="Focus">
  <img src="docs/screenshot-someday.png" width="49%" alt="someday">
</p>

拖拽顺序**不写进 markdown**：看板顺序存在 `app/.order.json`（全局一条全序），
Focus / 追更 / someday 存在 `app/.lists.json`。两个文件都是派生数据，删掉就回默认排序。

## 这套体系借了谁的灵感（有据可查）

- **重要 × 紧急**来自**艾森豪威尔矩阵**：常引艾森豪威尔那句"重要的事很少紧急"，
  经**史蒂芬·柯维《高效能人士的七个习惯》（1989）**普及。本项目把它从 2×2 改成
  **3×3** —— 只有两档会逼你对"中等"说谎。
- **捕获箱、"将来某天"清单、周复盘**这三件事来自**戴维·艾伦《搞定》（GTD，2001）**。
  本项目只取这三样，其余不要。
- **一行一条、可 grep 的纯文本**沿用 **todo.txt** 的约定（Gina Trapani，2007）与
  **Obsidian** 一带的 local-first 思路：文件优先于数据库，`git` 优先于同步服务。
- **Agent 原生打包**沿用 **Anthropic 的 Agent Skills（`SKILL.md`）**：操作手册和数据
  放在一起，任何 Agent 都能直接接手。
- 这套 markdown 契约的第一版是 2026 年 10 月用**豆包**起草的，之后两周在真实使用里
  被反复修改：九宫格、三条轨道、全局一条全序、"只改一行"的回写铁律，都是踩出来的。

一句话：**真正有意思的不是九宫格，而是"文件就是接口"。**

## 代码结构

```
app/          FastAPI 后端 + React 前端（无第三方 UI / 拖拽库）
skill/quadrant/ Agent skill：SKILL.md + references
templates/tasks/ 数据目录模板（init_tasks.py 复制它）
scripts/      init_tasks.py、screenshot.mjs
```

## 测试

```bash
cd app && uv run python run_tests.py    # 100+ 条断言，全在临时目录跑
```

## 已知取舍（都是有意为之）

- **顺序不写进 md**：写进去就要重排文件，diff 爆炸，还会和"人改 md"打架。
- **分组口径 ≠ 筛选口径**：时间桶互斥；`due=week` 是滚动 7 天含今天。
- **ID 里的日期是创建日**：跨年不撞号，也不用维护"排到几了"。
- **不做云同步**：数据是你的文件，用 git / Syncthing / iCloud 自己选。

## License

MIT
