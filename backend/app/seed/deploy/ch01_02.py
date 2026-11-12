"""软件工程与项目部署：第 1—2 章（Git 与协作、测试工程）。

章节与课时的标题、说明、难度、时长以课程目录（``course_catalog_seed``）为准，
本文件只提供 15 个内容模块、知识点、练习与测验题。
"""

CHAPTERS: list[dict] = [
    # ==================================================================
    # 第 1 章 Git 与协作
    # ==================================================================
    {
        "code": "software-engineering-deploy-01",
        "title": "Git 与协作",
        "description": "让改动可追溯、可评审、可回退。",
        "order_index": 1,
        "lessons": [
            {
                "code": "software-engineering-deploy-01-lesson-01",
                "objectives": """1. 能说清工作区、暂存区、本地仓库、远程仓库四者的关系；
2. 独立完成「改代码 → 暂存 → 提交 → 推送」的完整循环；
3. 写出让人一眼看懂的提交信息，而不是「改了一下」；
4. 会查看历史、对比差异，并在提交前撤错文件。""",
                "why_learn": """代码写错可以改，历史记错就很难救。当你需要回答「这行代码谁改的、为什么改、能不能退回去」时，
只有规范提交的仓库能给你答案。它是团队协作的地基，也是单人项目给自己留的后路。""",
                "concepts": """**四个区**：工作区（你正在编辑的文件）→ 暂存区（`git add` 后待提交的快照）→ 本地仓库（`git commit` 后的历史）→ 远程仓库（`git push` 后的备份与协作中心）。
**提交是快照，不是差异**：每次 commit 记录的是那一刻整个项目的状态，差异是两次快照比出来的。
**HEAD**：指向当前所在提交的指针，`HEAD~1` 就是上一个提交。
**分支只是一个可移动的标签**：创建分支几乎零成本，它只记录"从哪条历史长出来"。""",
                "plain": """把 Git 想成写日记：工作区是你脑子里的草稿，`git add` 是把这一页抄到正式本子上，
`git commit` 是签上日期封存，`git push` 是拍照发给同伴。
没抄到本子上的内容，一旦写坏就没了；抄上去了，哪怕删掉整页也能翻回来。
提交信息就是那一页的目录——三个月后你只会看目录决定要不要翻。""",
                "syntax": """**日常四步**

```bash
git status                  # 现在哪些文件变了
git add app/main.py         # 把指定文件放进暂存区（. 表示全部）
git commit -m "feat: 新增任务导出接口"
git push origin main        # 推到远程
```

**查看与撤销**

```bash
git log --oneline -10        # 最近 10 条提交，一行一条
git diff                     # 工作区 vs 暂存区
git diff --staged            # 暂存区 vs 上次提交
git restore app/main.py      # 丢弃工作区改动（危险，不可恢复）
git restore --staged a.py    # 从暂存区撤出，改动仍保留
```

- `git status` 是你最该多敲的命令，先看清楚再动手。
- `git restore` 丢弃工作区改动**不可恢复**，用之前确认不需要。""",
                "example_code": '''# 场景：给项目加一个导出功能，走完一次完整提交

# 1) 先看现状
git status
# On branch main
# Changes not staged for commit:
#   modified:   app/api/v1/tasks.py
# Untracked files:
#   app/services/export_service.py

# 2) 只暂存这次要提交的两个文件（别把临时调试文件带进去）
git add app/api/v1/tasks.py app/services/export_service.py

# 3) 再确认一次暂存了什么
git status
# Changes to be committed:
#   modified:   app/api/v1/tasks.py
#   new file:   app/services/export_service.py

# 4) 查看即将提交的具体改动
git diff --staged

# 5) 提交：类型 + 范围 + 做了什么
git commit -m "feat(tasks): 新增任务导出为 CSV 的接口"

# 6) 推送
git push origin main

# 7) 完事后确认历史
git log --oneline -3
# 9f2c1ab feat(tasks): 新增任务导出为 CSV 的接口
# 4d8e0f1 fix(auth): 修正令牌过期判断''',
                "code_lines": """1. `git status` 先看清楚：这里有 1 个修改文件和 1 个新增文件，是有意为之。
2. `git add` 指定具体文件而不是 `git add .`：临时调试文件、本地配置不会被误提交。
3. 第二次 `git status` 是核对动作——暂存区就是"将要进入历史的全部内容"，必须自己过一眼。
4. `git diff --staged` 看的是**已经暂存**的差异；不加 `--staged` 只看未暂存部分，容易看漏。
5. 提交信息用 `feat(tasks):` 前缀：类型 + 影响范围 + 一句话结论。
6. `git push origin main` 把本地提交推到远程 `origin` 的 `main` 分支。
7. `git log --oneline` 确认这次提交真的进了历史，而不是只停在本地。""",
                "output": """$ git status
On branch main
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        modified:   app/api/v1/tasks.py
        new file:   app/services/export_service.py

$ git commit -m "feat(tasks): 新增任务导出为 CSV 的接口"
[main 9f2c1ab] feat(tasks): 新增任务导出为 CSV 的接口
 2 files changed, 87 insertions(+), 2 deletions(-)
 create mode 100644 app/services/export_service.py

$ git push origin main
To github.com:xiaoma/tasks.git
   4d8e0f1..9f2c1ab  main -> main""",
                "mistakes": """- 提交信息写「update」「修改」「fix bug」，三个月后自己都看不懂。
- 用 `git add .` 一把梭，把 `.env`、`.venv/`、调试脚本一起提交上去。
- 把「一次改动」拆成十几个 `wip` 提交，历史无法阅读。
- 提交前不看 `git diff --staged`，把注释掉的调试代码带上线。
- 报错就用 `git reset --hard` 清空一切，连没提交的改动一起丢。""",
                "error_analysis": """`error: failed to push some refs ... (fetch first)` / `non-fast-forward`
—— 远程有你本地没有的提交。先 `git pull --rebase` 把本地提交接到最新历史后面，再推。**不要**直接 `push -f`。

`fatal: not a git repository`
—— 当前目录不是仓库。`cd` 到项目根目录，或用 `git init` 初始化。

`nothing to commit, working tree clean`
—— 改动已经提交过，或者你改的文件不在当前仓库路径下。用 `git status` 确认。

`warning: LF will be replaced by CRLF`
—— Windows 换行符提示，无害。项目里用 `.gitattributes` 固定为 LF 可消除噪音。""",
                "beginner_practice": """1. 在项目里改一行注释，走完 `status → add → diff --staged → commit` 四步，提交信息写成 `docs: 补充任务模块注释`。
2. 随便新建一个临时文件，`git add` 之后用 `git restore --staged` 撤出暂存区，确认文件本身还在。""",
                "advanced_practice": """故意制造一次「提交了不该提交的文件」：把 `debug.log` 提交上去，然后用
`git rm --cached debug.log` 从版本库移除、加入 `.gitignore`、再提交一次修复。
最后回答：如果这次提交已经推到远程并被别人拉取，为什么不能直接 `git reset --hard` 解决？""",
                "quiz_note": "本节 6 道题：2 道基础理解（四区关系、暂存区语义）+ 2 道命令阅读（读 status 输出、读 log）+ 2 道应用练习（选对撤销命令、判断提交信息质量）。",
                "summary": """工作区 → 暂存区 → 本地仓库 → 远程仓库，每一步都有明确的边界。
暂存区是"我决定把哪些改动放进这次提交"的地方，不是多余步骤。
提交信息按「类型(范围): 一句话结论」写，是给三个月后的自己看。
想丢弃改动先 `git status` 看清楚，`git restore` 之后不可恢复。""",
                "next_lesson": "下一节把这些动作放进多人协作场景：用分支隔离改动，用合并请求收口。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-01-01",
                        "name": "Git 四个区与提交规范",
                        "goal": "能独立完成改代码、暂存、提交、推送的完整循环，并写出可读的提交信息。",
                        "minutes": 30,
                        "criteria": "能在不看笔记的情况下走完四步循环，并能说明暂存区与工作区的区别、解释一次提交信息各段含义。",
                        "requires": [],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-01-01-1",
                        "kp": 0,
                        "title": "挑出这次要提交的文件",
                        "description": """`git status` 显示：`app/a.py`（修改）、`app/b.py`（修改）、`.env`（未跟踪）、`debug.log`（未跟踪）。
现在只想提交 `a.py` 里与登录相关的改动。写出你的命令序列。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''```bash
git add app/a.py
git status                 # 确认暂存区只有 a.py
git diff --staged          # 确认差异只包含登录相关代码
git commit -m "feat(auth): 新增登录失败三次锁定"
```
`.env` 与 `debug.log` 都不能进仓库：前者含密钥，后者是运行时产物，两者都应写进 `.gitignore`。''',
                        "explanation": "按文件暂存而不是 `git add .`，是避免误提交最有效的一招。",
                    },
                    {
                        "code": "sed-ex-01-01-2",
                        "kp": 0,
                        "title": "把提交信息写清楚",
                        "description": """原始提交信息是 `修改`。这次改动给任务列表接口加了分页，并把默认页大小设为 20。
改写成符合「类型(范围): 一句话结论」的提交信息，并说明为什么这样改。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''`feat(tasks): 任务列表支持分页，默认每页 20 条`

理由：
- `feat` 表明是新增能力，不是修 bug；
- `(tasks)` 让 `git log` 里能一眼看出影响模块；
- 后半句说清"做了什么 + 关键默认值"，比「修改」多提供三倍信息量。''',
                        "explanation": "提交信息不是日记，是索引。索引要能被搜索、被扫读。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-01-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`git add app/main.py` 之后，文件内容保存在哪里？",
                        "options": [
                            ("A", "远程仓库"),
                            ("B", "工作区"),
                            ("C", "暂存区"),
                            ("D", "已经算一次提交"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "`add` 只把内容放进暂存区（index），要执行 `commit` 才进入本地仓库历史。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-01-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些内容绝对不应该提交到仓库？（多选）",
                        "options": [
                            ("A", ".env 里的数据库密码"),
                            ("B", "requirements.txt"),
                            ("C", ".venv/ 虚拟环境目录"),
                            ("D", "data/xiaoma.db 用户数据库"),
                        ],
                        "answer": {"values": ["A", "C", "D"]},
                        "explanation": "密钥、虚拟环境、用户数据都不进仓库：前两者泄漏与体积问题，后者是隐私且每次运行都变。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-01-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """看到如下 status 输出，这次 `git commit` 会包含哪些改动？

```
Changes not staged for commit:
        modified:   app/a.py
Untracked files:
        app/b.py
```""",
                        "options": [
                            ("A", "a.py 和 b.py"),
                            ("B", "什么都提交不了，暂存区为空"),
                            ("C", "只有 a.py"),
                            ("D", "只有 b.py"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "两个文件都没 `git add`，暂存区为空，`commit` 会提示 `nothing to commit`。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-01-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": """`git log --oneline` 第一列 `9f2c1ab` 代表什么？说明它在 `git show`、`git checkout` 里的作用。""",
                        "answer": {"reference": "`9f2c1ab` 是提交哈希的短形式（完整 SHA-1 的前 7 位），唯一标识这次提交；`git show 9f2c1ab` 查看该提交的完整改动，`git checkout 9f2c1ab` 可切到该提交（分离头指针）。", "keywords": ["短哈希", "唯一标识", "SHA-1", "git show", "git checkout"]},
                        "explanation": "短哈希是完整 SHA-1 的前 7 位，用于 `git show`、`git checkout` 等操作定位提交。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-01-01-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "误把 `debug.log` 放进了暂存区，但还没提交。要把它撤出暂存区且**保留文件本身**，应执行？",
                        "options": [
                            ("A", "git restore --staged debug.log"),
                            ("B", "git restore debug.log"),
                            ("C", "rm debug.log"),
                            ("D", "git reset --hard"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`--staged` 只撤出暂存区；不带该参数是丢弃工作区改动（文件内容会变回上次提交的样子）。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-01-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "推送时提示 `failed to push some refs (fetch first)`，正确做法是先 `git pull --rebase` 再推送，而不是 `git push -f`。",
                        "options": None,
                        "answer": {"value": True},
                        "explanation": "强推会覆盖远程他人提交，属于破坏性操作。先同步再推送才是正确顺序。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-01-lesson-02",
                "objectives": """1. 能用功能分支隔离一次改动，不走主干直接提交；
2. 能完成「建分支 → 开发 → 合并」的完整流程；
3. 遇到冲突时能读懂冲突标记并正确解决；
4. 能判断什么时候该用 `merge`、什么时候用 `rebase`。""",
                "why_learn": """直接在 `main` 上改代码，等于所有人共用一张草稿纸。两个人同时改同一个函数，
谁的改动先进去，另一个人的工作就被覆盖或者卡在冲突里。
分支把「你的草稿」和「团队的定稿」分开，让改动可以并行、可以讨论、可以随时废弃。""",
                "concepts": """**功能分支**：一次改动一条分支，命名体现目的（`feat/task-export`、`fix/login-lock`）。
**merge**：把两条历史合到一起，保留真实分叉，会多出一个合并提交。
**rebase**：把当前分支的提交「搬」到目标分支最新提交之后，历史变成一条直线，代价是改写了提交哈希。
**冲突**：同一文件的同一位置被两边改过，Git 无法替你决定保留哪个，只能由人来判断。
**快进合并**：目标分支没有新提交时，合并只是把指针往前挪，不产生合并提交。""",
                "plain": """分支像给项目开一个平行副本：你在副本里随便折腾，主干上的人照常往前走。
合并是把两条线接起来；变基是把自己的改动"重新抄一遍"到别人最新进度之后，看起来像一直跟着主线做。
冲突不是错误，是 Git 在说「这两处我判断不了，你来定」。解决冲突的动作本质就是：把文件改成你最终想要的样子，然后提交。""",
                "syntax": """**分支与合并**

```bash
git switch -c feat/task-export     # 新建并切换（旧写法：git checkout -b）
git switch main                    # 切回主干
git merge feat/task-export         # 把功能分支合进当前分支
git branch -d feat/task-export     # 删除已合并的本地分支
git branch -a                      # 列出所有分支（含远程）
```

**变基**

```bash
git switch feat/task-export
git rebase main                    # 把本分支提交搬到 main 最新之后
```

- `switch` 是 Git 2.23+ 的新命令，语义比 `checkout` 清楚（`checkout` 还能切文件，容易误用）。
- 变基会改写哈希，**已经推到远程并被别人拉取的分支不要再变基**。""",
                "example_code": '''# 场景：在功能分支上开发任务导出，期间主干也有新提交

# 1) 从最新主干建分支
git switch main
git pull --rebase
git switch -c feat/task-export

# 2) 开发并提交（可以多次）
#    ... 写 export_service.py、改路由 ...
git add app/services/export_service.py app/api/v1/tasks.py
git commit -m "feat(tasks): 新增 CSV 导出服务"
git commit --allow-empty -m "feat(tasks): 导出接口接入路由"

# 3) 期间主干有新提交，先把本地分支接到最新主干后面
git fetch origin
git rebase origin/main

# 4) 切回主干合并（--no-ff 保留分支痕迹，便于回溯）
git switch main
git pull --rebase
git merge --no-ff feat/task-export -m "merge: 任务导出功能"

# 5) 推送并清理
git push origin main
git branch -d feat/task-export''',
                "code_lines": """1. 建分支前先 `git pull --rebase`：保证分支从最新主干长出来，减少后面冲突。
2. `git switch -c` 一步完成"新建 + 切换"，比 `checkout -b` 语义更明确。
3. 一个功能拆成两个有意义的提交，历史可读；但不必为每行代码都提交。
4. `git fetch origin` 只更新远程跟踪引用，不自动合并——先看清楚再决定。
5. `git rebase origin/main` 把本分支的两个提交重新应用到最新主干之后，历史成直线。
6. `--no-ff` 强制生成合并提交，`git log --graph` 时能看出"这里合并过一个功能分支"。
7. 合并完成后删本地分支，远程分支由合并请求（PR）流程负责删除。""",
                "output": """$ git merge --no-ff feat/task-export -m "merge: 任务导出功能"
Merge made by the 'ort' strategy.
 app/api/v1/tasks.py            | 12 ++++++++++++
 app/services/export_service.py | 64 ++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 76 insertions(+)
 create mode 100644 app/services/export_service.py

$ git log --oneline --graph -4
*   7c1d3e9 (HEAD -> main) merge: 任务导出功能
|\\
| * 5b8a2f0 feat(tasks): 导出接口接入路由
| * 3a9e7c1 feat(tasks): 新增 CSV 导出服务
|/
* 2f6b4d8 docs: 补充部署说明""",
                "mistakes": """- 一直待在 `main` 上开发，出问题只能回滚整个主干。
- 一个分支改三件事，评审时无法聚焦，出问题也难定位。
- 冲突时把 `<<<<<<<` 那段直接删掉了事，结果把别人的改动删没了。
- 对已经推到远程、别人也在用的分支执行 `rebase` 后强推。
- 用 `git merge` 时不断言方向（`A merge B` 和 `B merge A` 结果不同）。""",
                "error_analysis": """`CONFLICT (content): Merge conflict in app/tasks.py`
—— 确实冲突。打开文件会看到 `<<<<<<< HEAD` / `=======` / `>>>>>>> 分支名`，
把整段改成最终想要的样子（三个标记全删），`git add` 后 `git commit` 完成合并。

`error: Your local changes would be overwritten by merge`
—— 工作区有未提交改动。先 `git stash` 或提交，再合并。

`fatal: The current branch has no upstream branch`
—— 新分支还没有远程对应。首次推送用 `git push -u origin feat/task-export`。

`Auto-merging` 之后文件里多了一个 `<<<<<<<` 却没人管
—— 合并提交进去了但代码是坏的。合并后必须搜索一遍 `<<<<<<<` 再提交。""",
                "beginner_practice": """1. 从 `main` 建 `feat/hello` 分支，加一个注释提交，再切回 `main` 合并且删除该分支。
2. 用 `git log --oneline --graph` 对比 `merge` 与 `merge --no-ff` 生成的历史差异。""",
                "advanced_practice": """模拟一次真实冲突：在 `main` 与 `feat` 分支上分别修改同一行代码，执行合并解决冲突。
完成后回答两个问题：(1) 什么情况下应该 rebase 而不是 merge？
(2) 已经推到远程的功能分支为什么不能 rebase？""",
                "quiz_note": "本节 6 道题：2 道基础理解（分支本质、merge 与 rebase 差异）+ 2 道输出阅读（读 graph 历史、读冲突标记）+ 2 道应用练习（选对建分支命令、判断危险操作）。",
                "summary": """分支是隔离改动的工具，一条分支只做一件事。
`merge` 保留分叉与合并提交，`rebase` 拉直历史但改写哈希。
冲突的本质是"同一位置两边都改过"，解决冲突就是人工给出最终版本。
已共享的分支不变基、不强推，这是协作底线。""",
                "next_lesson": "分支合进来之后要有人把关——下一节讲评审清单与版本发布。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-01-02",
                        "name": "功能分支与合并策略",
                        "goal": "能用功能分支隔离改动，正确选择 merge 或 rebase，并独立解决内容冲突。",
                        "minutes": 35,
                        "criteria": "能独立走完建分支到合并的完整流程，正确解决一次内容冲突，并说明 rebase 后不能强推的原因。",
                        "requires": ["software-engineering-deploy-01-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-01-02-1",
                        "kp": 0,
                        "title": "解决一次内容冲突",
                        "description": """合并时 `app/config.py` 出现冲突：

```
<<<<<<< HEAD
MAX_RETRY = 3
=======
MAX_RETRY = 5
>>>>>>> feat/retry-policy
```

请写出解决步骤，并说明为什么不能简单删掉其中一段就完事。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''步骤：
1. 打开文件，理解两边意图：主干是 3 次，功能分支改成 5 次；
2. 确认业务结论（例如重试策略以 5 次为准，或改成可配置项）；
3. 删除 `<<<<<<<`、`=======`、`>>>>>>>` 三行及不要的那一段，保留最终版本；
4. `git add app/config.py`；
5. `git commit` 完成合并（信息里写明结论）。

不能"删掉一段就走"的原因：删除只是让文件能编译，没有做决策。
若两者的语义可以共存（比如做成 `MAX_RETRY = int(os.getenv("MAX_RETRY", "5"))`），
最优解往往是合并意图，而不是二选一。''',
                        "explanation": "冲突标记的三行必须全部删除，提交前搜索一次 `<<<<<<<` 是低成本保险。",
                    },
                    {
                        "code": "sed-ex-01-02-2",
                        "kp": 0,
                        "title": "选 merge 还是 rebase",
                        "description": """三种场景，分别说明该用哪个、为什么：
(1) 本地功能分支落后主干 5 个提交，尚未推送到远程；
(2) 已推送到远程、同事正在基于它开发的分支落后主干；
(3) 想把一个已完成的功能分支合入主干，希望历史里能看出这是个独立功能。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''(1) `rebase origin/main`：本地分支没有共享，拉直历史零风险，也让后续合并更干净。
(2) `merge origin/main`：分支已被别人使用，rebase 会改写哈希导致同事历史错乱；宁可多一个合并提交。
(3) `merge --no-ff`：强制保留合并提交，`git log --graph` 能看到功能边界，便于整体回滚。''',
                        "explanation": "判断标准只有一个：这条历史是否已经被别人拉取。已被共享就不改写。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-01-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "在 Git 里，分支本质上是什么？",
                        "options": [
                            ("A", "项目的一份完整拷贝"),
                            ("B", "指向某个提交的可移动指针"),
                            ("C", "一个独立的文件夹"),
                            ("D", "远程服务器上的副本"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "分支只是一个 41 字节的引用文件（指向提交哈希），所以创建分支几乎零成本。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-01-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 rebase，下列说法正确的是？（多选）",
                        "options": [
                            ("A", "会改写提交哈希"),
                            ("B", "能让历史变成一条直线"),
                            ("C", "对已共享的分支可以随意使用"),
                            ("D", "冲突时解决方式与 merge 类似"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 错误：改写哈希会让别人的分支历史与你分叉，必须避免。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-01-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """历史图如下，说明发生了什么：

```
*   7c1d3e9 (HEAD -> main) merge: 任务导出功能
|\\
| * 5b8a2f0 feat(tasks): 导出接口接入路由
| * 3a9e7c1 feat(tasks): 新增 CSV 导出服务
|/
* 2f6b4d8 docs: 补充部署说明
```""",
                        "options": [
                            ("A", "用了 fast-forward 合并"),
                            ("B", "用 --no-ff 合并，保留了分支分叉与合并提交"),
                            ("C", "用了 rebase"),
                            ("D", "发生了冲突"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "存在合并提交 `7c1d3e9` 且有两个父提交（分叉可见），是 `--no-ff` 的典型形态。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-01-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """文件里出现如下内容，第一步应该做什么？

```
<<<<<<< HEAD
timeout = 10
=======
timeout = 30
>>>>>>> feat/timeout
```""",
                        "options": [
                            ("A", "直接删掉下面那段，保留上面的"),
                            ("B", "理解两边意图，确认最终取值，再删除三个标记行与不要的分支"),
                            ("C", "执行 git reset --hard"),
                            ("D", "执行 git push -f"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "冲突是决策请求，不是格式错误。不确认业务结论就删，等于随机丢改动。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-01-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "从当前 `main` 新建并切换到 `fix/login-lock` 分支，正确的命令是？",
                        "options": [
                            ("A", "git branch fix/login-lock"),
                            ("B", "git switch -c fix/login-lock"),
                            ("C", "git checkout fix/login-lock"),
                            ("D", "git merge fix/login-lock"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`-c` 表示同时创建并切换；A 只创建不切换，C 假设分支已存在。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-01-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "同事正在使用的远程分支，你本地 rebase 后可以放心强推上去，因为这样历史更整洁。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "强推会重写共享历史，同事拉取时会出现大量重复提交或丢失自己的工作。这是协作禁忌。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-01-lesson-03",
                "objectives": """1. 能用一份固定清单完成代码评审，而不是凭感觉说「看着还行」；
2. 能给出可执行的评审意见（指出位置、说明原因、给出建议）；
3. 能按语义化版本判断这次改动该升哪一位；
4. 会打标签、写变更说明，并知道发布后可怎么回退。""",
                "why_learn": """评审是成本最低的缺陷拦截手段：线上修一个 bug 要几小时，评审时发现只要几分钟。
版本号与变更说明则是给使用者的契约——别人需要知道「这次升级会不会破坏我的用法」。""",
                "concepts": """**评审清单**：正确性、边界、错误处理、安全、可读性、测试覆盖，按固定顺序过一遍。
**评审粒度**：一次不超过 400 行的改动才能被认真看完，超了就该拆。
**语义化版本 `MAJOR.MINOR.PATCH`**：不兼容改动升 MAJOR，向下兼容的新功能升 MINOR，修 bug 升 PATCH。
**标签 `tag`**：给某个提交起一个永不移动的名字（如 `v1.4.1`），是发布的锚点。
**变更说明 ChangeLog**：面向使用者，写"有什么影响"，不是把提交信息复制一遍。""",
                "plain": """评审不是挑刺，是两个人一起确认「这段代码在生产环境会不会出事」。
版本号的三位数字对应三种承诺：会不会让旧代码报错、有没有新东西、只是修了毛病。
标签就像给发布拍了张定格照，出问题时能精确回到那一刻，而不是靠回忆"大概是上周三那个提交"。""",
                "syntax": """**打标签与查看**

```bash
git tag -a v1.4.1 -m "1.4.1：修复登录锁定计数错误"   # 附注标签
git push origin v1.4.1                                # 标签要单独推
git tag -l "v1.4.*"                                   # 列出匹配标签
git show v1.4.1                                       # 查看标签指向的提交
```

**从标签回退**

```bash
git switch --detach v1.4.0     # 只查看，不建分支
git revert <commit>            # 用新提交抵消错误改动（推荐，不改历史）
```

- 标签默认不随 `git push` 上传，必须显式推。
- 线上回退优先 `revert` 而不是 `reset`：历史保留，别人不会被打乱。""",
                "example_code": '''# 场景：功能合并后走一遍评审 → 发布

# ---- 评审侧 ----
git fetch origin
git diff origin/main...origin/feat/task-export --stat
git diff origin/main...origin/feat/task-export -- app/services/export_service.py

# 评审意见必须能落到行：指出位置、原因、建议
# app/services/export_service.py:42
#   问题：写文件时直接用用户传入的文件名，存在路径穿越风险
#   建议：用 os.path.basename 过滤，并固定输出目录

# ---- 发布侧 ----
git switch main
git pull --rebase
git tag -a v1.4.1 -m "1.4.1：任务导出（CSV）"
git push origin main
git push origin v1.4.1

# ---- 出问题时 ----
git log --oneline v1.4.1 -5          # 定位可疑提交
git revert 9f2c1ab                   # 生成一个抵消提交
git tag -a v1.4.2 -m "1.4.2：回退导出文件名处理""''',
                "code_lines": """1. `git diff A...B`（三个点）比较的是「B 相对分叉点」的改动，比两个点更适合评审分支。
2. `--stat` 先看改了哪些文件、多少行，超过 400 行就该要求拆分。
3. 再按文件细看核心逻辑，评审顺序从"影响面"到"实现细节"。
4. 评审意见必须带行号与理由：`文件:行号 + 问题 + 建议`，否则作者无法执行。
5. 打附注标签 `-a` 会记录打标签的人、时间与说明，比轻量标签更适合发布。
6. 标签必须单独 `git push origin v1.4.1`，否则远程看不到这次发布。
7. `revert` 生成一个新提交来抵消旧改动，历史完整可追溯；`reset` 会让别人历史错乱。""",
                "output": """$ git tag -a v1.4.1 -m "1.4.1：任务导出（CSV）"
$ git push origin v1.4.1
To github.com:xiaoma/tasks.git
 * [new tag]         v1.4.1 -> v1.4.1

$ git tag -l "v1.4.*"
v1.4.0
v1.4.1
v1.4.2

$ git show v1.4.1 --stat
tag v1.4.1
Tagger: xiaoma <dev@xiaoma.cn>
Date:   Sun Nov 9 22:10:31 2026 +0800

    1.4.1：任务导出（CSV）

commit 7c1d3e9...
 app/api/v1/tasks.py            | 12 +++++
 app/services/export_service.py | 64 +++++++++++++""",
                "mistakes": """- 评审只说「看着没问题」，不指出任何具体行，等于没评审。
- 一次 PR 改了 2000 行，评审者只能扫一眼标题就给通过。
- 修个 bug 却升了 MINOR 版本，让使用者以为有新功能要适配。
- 打了标签没推，本地看到 `v1.4.1` 而远程没有。
- 线上出问题直接 `git reset --hard` 强推主干。""",
                "error_analysis": """`fatal: tag 'v1.4.1' already exists`
—— 标签名重复。确认是否要改版本号；确实要覆盖时用 `git tag -f`，但已推送的标签覆盖会影响别人，需谨慎。

远程看不到标签
—— 没用 `git push origin <tag>`，标签不会随普通推送自动上传。

`revert` 后出现冲突
—— 被回退的改动之后又有新提交动了同一区域。手工解决冲突后提交即可，仍然是安全的做法。

`git switch --detach` 后警告 "detached HEAD"
—— 正常现象，此时提交不会挂在任何分支上。要保留改动就 `git switch -c hotfix/xxx` 建分支。""",
                "beginner_practice": """1. 给当前最新提交打一个 `v0.1.0` 附注标签，推送到远程，再用 `git show` 查看内容。
2. 找一段最近写的代码，按「正确性 / 边界 / 错误处理 / 安全 / 可读性 / 测试」六项写一份自查清单结果。""",
                "advanced_practice": """为一次真实改动写完整发布说明：包含版本号判定理由（为什么是 PATCH 而不是 MINOR）、
使用者需要做什么（是否要迁移数据、是否要改配置）、以及回退方案。
然后回答：如果这次发布后发现严重缺陷，用 `revert` 还是 `reset`，为什么？""",
                "quiz_note": "本节 6 道题：2 道基础理解（评审清单、语义化版本）+ 2 道命令阅读（读 diff 参数、读标签输出）+ 2 道应用练习（选对版本号、选对回退方式）。",
                "summary": """评审按固定清单走，意见必须落到「文件:行号 + 问题 + 建议」。
一次改动不超过 400 行，超了就拆——这是让评审有效的前提。
语义化版本三位数字对应三种承诺，升错会让使用者误判风险。
发布用标签锚定，回退用 revert，历史永远不改写。""",
                "next_lesson": "评审和发布都靠人盯不住，下一章用自动化测试把质量变成可执行的门槛。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-01-03",
                        "name": "代码评审与语义化版本发布",
                        "goal": "能用固定清单完成评审并给出可执行意见，能按语义化版本正确发布与回退。",
                        "minutes": 30,
                        "criteria": "能对一段真实改动写出 3 条以上带行号的可执行评审意见，并能正确判断一次改动应升 MAJOR/MINOR/PATCH 中的哪一位。",
                        "requires": ["software-engineering-deploy-01-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-01-03-1",
                        "kp": 0,
                        "title": "写三条可执行的评审意见",
                        "description": """这段代码被提交评审：

```python
@app.get("/export")
def export_tasks(filename: str):
    path = os.path.join("/tmp", filename)
    with open(path, "w") as f:
        f.write(to_csv(TASKS))
    return {"path": path}
```

请写出至少三条可执行的评审意见（带位置、问题、建议）。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''1. `第 2 行`：`filename` 直接拼路径，存在路径穿越（传 `../../etc/passwd` 可写出目录外）。
   建议：`filename = os.path.basename(filename)`，并校验扩展名为 `.csv`。
2. `第 3 行`：`open` 未指定编码，Windows 下默认 GBK，导出的中文在别的机器上会乱码。
   建议：`open(path, "w", encoding="utf-8", newline="")`。
3. `第 5 行`：接口同步返回服务器本地路径，对前端无意义且泄漏目录结构。
   建议：改为 `FileResponse` 直接下载，或返回任务 id 供后续查询。
4. `整个函数`：没有鉴权校验，任何人可导出全量数据。
   建议：加 `Depends(require_user)` 并限定为本人数据。''',
                        "explanation": "好的评审意见是可执行的：看到行号就知道改哪里，看到建议就知道怎么改。",
                    },
                    {
                        "code": "sed-ex-01-03-2",
                        "kp": 0,
                        "title": "判断版本号",
                        "description": """当前版本 `1.4.1`。以下三次改动各自应该升到哪个版本？
(1) 修复导出文件中文乱码；
(2) 新增任务标签功能，旧接口与字段完全不变；
(3) 把 `GET /tasks` 的返回结构从数组改成 `{"items": [...], "total": n}`。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''(1) PATCH → `1.4.2`：只修缺陷，接口契约不变。
(2) MINOR → `1.5.0`：新增能力，向下兼容，旧用法继续有效。
(3) MAJOR → `2.0.0`：返回结构变化会让旧前端解析失败，属于不兼容改动。
   若必须保留旧结构，可先新增 `GET /tasks/v2` 并行一段时间，再按 MAJOR 发布。''',
                        "explanation": "判断依据只有一个：老代码升级后会不会坏。会坏就是 MAJOR。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-01-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "当前版本 `1.4.1`，新增一个向下兼容的功能，新版本号应为？",
                        "options": [
                            ("A", "1.4.2"),
                            ("B", "1.5.0"),
                            ("C", "2.0.0"),
                            ("D", "1.4.1.1"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "向下兼容的新功能升 MINOR，并把 PATCH 归零。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-01-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "一份有效的评审意见通常包含哪些要素？（多选）",
                        "options": [
                            ("A", "具体位置（文件:行号）"),
                            ("B", "问题是什么、为什么是问题"),
                            ("C", "可执行的修改建议"),
                            ("D", "「我觉得不太好」"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 无法执行，属于无效意见。评审的目的是让作者能改，不是表达情绪。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-01-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`git diff origin/main...origin/feat/x --stat` 中三个点的含义是？",
                        "options": [
                            ("A", "比较两个分支的最新提交差异"),
                            ("B", "比较 feat/x 相对两者分叉点的改动"),
                            ("C", "语法错误，应为两个点"),
                            ("D", "比较文件的三个版本"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "三点形式 `A...B` 等价于 `diff $(merge-base A B) B`，评审分支时能排除主干自身的改动。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-01-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "执行 `git push origin main` 之后，远程能看到的标签是？",
                        "options": [
                            ("A", "所有本地标签"),
                            ("B", "一个都没有，标签需要单独推送"),
                            ("C", "只有带注释的标签"),
                            ("D", "最近一个标签"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "标签不会随分支推送上传，必须 `git push origin <tag>` 或 `git push --tags`。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-01-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要给当前提交打附注标签 `v1.4.1` 并推送到远程，命令序列是？",
                        "options": [
                            ("A", "git tag v1.4.1 && git push origin main"),
                            ("B", "git tag -a v1.4.1 -m \"说明\" && git push origin v1.4.1"),
                            ("C", "git push --tags-only"),
                            ("D", "git commit -m v1.4.1"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`-a` 生成附注标签（带作者、时间、说明），并且标签要显式推送到 origin。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-01-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "线上出问题后，用 `git revert` 生成抵消提交，比 `git reset --hard` 强行回退主干更安全。",
                        "options": None,
                        "answer": {"value": True},
                        "explanation": "revert 不改写历史，协作者不受影响；reset 改写历史，已共享时会破坏别人的分支。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },

    # ==================================================================
    # 第 2 章 测试工程
    # ==================================================================
    {
        "code": "software-engineering-deploy-02",
        "title": "测试工程",
        "description": "测试不是负担，而是让重构敢下手的安全网。",
        "order_index": 2,
        "lessons": [
            {
                "code": "software-engineering-deploy-02-lesson-01",
                "objectives": """1. 能用参数化把「同一逻辑多组输入」写成一条用例；
2. 会用 `pytest.raises` 断言异常，而不是只测正常路径；
3. 会用标记区分快慢用例，并只跑自己关心的那部分；
4. 理解断言改写如何让失败信息直接指出差异。""",
                "why_learn": """手写 20 个 `if` 判断输出对不对，既啰嗦又容易漏。
pytest 的价值在于：一条用例可以覆盖多组输入，失败时直接告诉你「哪个输入、期望什么、实际是什么」。
写测试的成本决定了你愿不愿意写——降低这个成本，质量才可能持续。""",
                "concepts": """**参数化**：`@pytest.mark.parametrize` 把输入-期望做成表，一组失败只影响那一组。
**异常断言**：`with pytest.raises(ValueError, match="...")` 既断言类型也断言信息。
**标记**：`@pytest.mark.slow` 等自定义标记，配合 `-m` 选择执行子集。
**断言改写**：pytest 会重写 `assert`，失败时展示表达式两侧的实际值，比 `assertEqual` 更直观。
**测试命名**：`test_<被测行为>_<场景>_<期望>`，从名字就能看出覆盖了什么。""",
                "plain": """参数化就是把「手工跑十遍」变成「写一张表格，程序帮你跑十遍」。
它和 Excel 里拉公式一个道理：公式写一次，换每行数据自动出结果。
标记像给用例贴标签——上高速走 ETC 通道，跑全量测试时走慢速队列。
失败信息是测试的价值所在：告诉你差在哪，而不是只说「不对」。""",
                "syntax": """```python
import pytest

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  hello  ", "hello"),
        ("hello", "hello"),
        ("", ""),
    ],
    ids=["两侧空格", "无空格", "空字符串"],
)
def test_normalize_title(raw, expected):
    assert normalize_title(raw) == expected

def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        divide(1, 0)

@pytest.mark.slow
def test_export_large_file():
    ...
```

- `ids=` 给每组数据起名字，失败时显示 `[两侧空格]` 而不是 `[0]`。
- `match=` 支持正则，断言错误信息也符合预期。""",
                "example_code": '''# tests/test_title.py
import pytest

from app.utils.text import normalize_title


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  写周报  ", "写周报"),
        ("写周报", "写周报"),
        ("", ""),
        ("   ", ""),
        ("a" * 200, "a" * 200),
    ],
    ids=["两侧空格", "无空格", "空串", "全空格", "超长"],
)
def test_normalize_title(raw: str, expected: str) -> None:
    assert normalize_title(raw) == expected


def test_normalize_title_rejects_none() -> None:
    with pytest.raises(TypeError, match="title 必须是字符串"):
        normalize_title(None)


@pytest.mark.slow
def test_export_10k_tasks(tmp_path) -> None:
    from app.services.export_service import export_tasks

    path = tmp_path / "tasks.csv"
    export_tasks([{"id": i, "title": f"任务{i}"} for i in range(10_000)], path)
    assert path.read_text(encoding="utf-8").count("\\n") == 10_001''',
                "code_lines": """1. `@pytest.mark.parametrize` 接收「参数名元组 + 数据列表」，每组数据跑一次用例。
2. `ids=` 让失败报告里出现「两侧空格」这样的可读标识，而不是数组下标。
3. `normalize_title` 是纯函数，这类逻辑最适合参数化：无 IO、无状态、结果确定。
4. `pytest.raises(TypeError, match=...)` 同时断言异常类型与信息，避免"抛了别的错也算过"。
5. `match` 里不要写太长的完整句子，写关键片段即可，否则改文案就挂。
6. `@pytest.mark.slow` 标记慢用例，本地开发用 `-m "not slow"` 跳过。
7. `tmp_path` 是 pytest 内置 fixture，给每个用例一个独立临时目录，天然隔离。""",
                "output": """$ pytest tests/test_title.py -v
tests/test_title.py::test_normalize_title[两侧空格] PASSED
tests/test_title.py::test_normalize_title[无空格] PASSED
tests/test_title.py::test_normalize_title[空串] PASSED
tests/test_title.py::test_normalize_title[全空格] PASSED
tests/test_title.py::test_normalize_title[超长] PASSED
tests/test_title.py::test_normalize_title_rejects_none PASSED
tests/test_title.py::test_export_10k_tasks PASSED

========== 7 passed in 0.31s ==========

# 失败时的样子（断言改写）
$ pytest tests/test_title.py -q
E   AssertionError: assert '写周报 ' == '写周报'
E     - 写周报
E     + 写周报
E     ?    +
tests/test_title.py:18: AssertionError
============ short test summary ============
FAILED tests/test_title.py::test_normalize_title[两侧空格]""",
                "mistakes": """- 只测正常路径，边界（空串、超长、None）一个都没覆盖。
- 用 `assert result` 而不是 `assert result == 期望值`，失败时看不到实际值。
- `parametrize` 一次塞 50 组数据，失败后不知道该看哪组（应拆分成多个用例）。
- `pytest.raises` 不加 `match`，导致抛出完全无关的异常也算通过。
- 用例名写成 `test_1`、`test_2`，半年后没人知道测的是什么。""",
                "error_analysis": """`TypeError: parametrize() missing required positional argument`
—— 参数名要写成字符串或元组，且数量与每组数据长度一致。

`Failed: DID NOT RAISE <class 'TypeError'>`
—— 代码根本没抛异常。先确认被测函数在该输入下是否真的应该报错。

`E   assert 'a' == 'b'` 但你看不出哪里不同
—— 用 `-vv` 让 pytest 展示更完整差异，或临时加 `print(repr(a), repr(b))`。

`PytestUnknownMarkWarning: Unknown pytest.mark.slow`
—— 自定义标记要在 `pytest.ini` 的 `markers` 里注册，否则只是警告、`-m` 过滤也不生效。""",
                "beginner_practice": """1. 给一个 `format_price(cents: int) -> str` 函数写 5 组参数化用例，覆盖 0、整数、带小数、负数、超大值。
2. 写一条用例断言「传入非整数时抛 TypeError」，并带上 `match`。""",
                "advanced_practice": """把一段已有测试里的 6 个 `if/else` 断言改成参数化用例，对比改造前后的行数与失败可读性。
再给慢用例加 `slow` 标记，验证 `pytest -m "not slow"` 确实跳过了它。""",
                "quiz_note": "本节 6 道题：2 道基础理解（参数化作用、异常断言）+ 2 道代码阅读（读 parametrize 定义、读失败报告）+ 2 道应用练习（补 ids、补 match）。",
                "summary": """参数化把「多组输入」压成一条可维护的用例，`ids` 决定失败时好不好读。
异常也是行为的一部分，用 `pytest.raises(..., match=...)` 断言类型与信息。
标记让测试可以分层执行，本地跑快的、CI 跑全的。
断言要写成 `== 期望值`，失败信息本身就是最好的文档。""",
                "next_lesson": "多个用例都要准备数据库和客户端，下一节用 fixture 把这些准备工作分层复用。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-02-01",
                        "name": "pytest 参数化与断言进阶",
                        "goal": "能用参数化覆盖多组输入，用 pytest.raises 断言异常，用标记分层执行测试。",
                        "minutes": 35,
                        "criteria": "能独立把一段重复断言改造成参数化用例，并为异常路径写出带 match 的断言。",
                        "requires": ["software-engineering-deploy-01-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-02-01-1",
                        "kp": 0,
                        "title": "把重复断言改成参数化",
                        "description": """现有测试：

```python
def test_price_1():
    assert format_price(0) == "¥0.00"

def test_price_2():
    assert format_price(1999) == "¥19.99"

def test_price_3():
    assert format_price(100000) == "¥1000.00"
```

改写成一条参数化用例，并给每组数据起中文 id。""",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''import pytest

@pytest.mark.parametrize(
    ("cents", "expected"),
    [(0, "¥0.00"), (1999, "¥19.99"), (100000, "¥1000.00")],
    ids=["零值", "两位小数", "千位整数"],
)
def test_format_price(cents: int, expected: str) -> None:
    assert format_price(cents) == expected''',
                        "explanation": "三个函数变一条，新增用例只需加一行数据。ids 让失败报告直接指出是哪类输入出问题。",
                    },
                    {
                        "code": "sed-ex-02-01-2",
                        "kp": 0,
                        "title": "补全异常断言",
                        "description": """`parse_duration("abc")` 应抛出 `ValueError`，信息包含「格式不正确」。
补全这条用例，并说明为什么需要 `match`。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def test_parse_duration_invalid_format() -> None:
    with pytest.raises(ValueError, match="格式不正确"):
        parse_duration("abc")

需要 match 的原因：不加 match 时，只要抛出任意 ValueError 就算通过，
哪怕信息是「内部状态异常」这种完全无关的错误，测试也会误判为通过。''',
                        "explanation": "断言异常信息，等于同时约束了「错在哪个分支」，测试更精确。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-02-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`@pytest.mark.parametrize` 的主要作用是？",
                        "options": [
                            ("A", "让测试跑得更快"),
                            ("B", "用一组数据表驱动同一段断言，减少重复代码"),
                            ("C", "自动修复失败的断言"),
                            ("D", "跳过指定用例"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "参数化解决的是「同一逻辑、多组输入」的表达问题，不是性能或跳过。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 `pytest.raises`，正确说法有？（多选）",
                        "options": [
                            ("A", "可以只断言异常类型"),
                            ("B", "match 参数可以断言异常信息片段"),
                            ("C", "如果代码没抛异常，用例判定为失败"),
                            ("D", "它会把异常吞掉并让用例通过"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 错误：raises 是断言「应该抛」，没抛就是失败（DID NOT RAISE）。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """这段 parametrize 会生成几条用例？

```python
@pytest.mark.parametrize(("a", "b"), [(1, 2), (3, 4), (5, 6)])
def test_add(a, b):
    assert a < b
```""",
                        "options": [("A", "1 条"), ("B", "2 条"), ("C", "3 条"), ("D", "6 条")],
                        "answer": {"value": "C"},
                        "explanation": "每组数据生成一条独立用例，失败互不影响，便于定位。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-01-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """失败报告 `test_normalize_title[两侧空格] FAILED` 中 `[两侧空格]` 来自哪里？

```python
@pytest.mark.parametrize(("raw", "expected"), [...], ids=["两侧空格", ...])
```""",
                        "options": [
                            ("A", "函数名"),
                            ("B", "parametrize 的 ids 参数"),
                            ("C", "异常信息"),
                            ("D", "文件路径"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "ids 决定每组数据的显示名，是提升失败可读性最直接的参数。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": """补全断言：要求 `load_config("")` 抛出 `ValueError`，且异常信息包含「不能为空」。

```python
with pytest.raises(____, ____):
    load_config("")
```""",
                        "answer": {"reference": "with pytest.raises(ValueError, match=\"不能为空\"):", "keywords": ["pytest.raises", "ValueError", "match"]},
                        "explanation": "参数名是 `match`，支持正则匹配异常字符串。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-02-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`assert result` 与 `assert result == 1` 相比，后者失败时能提供更有用的信息。",
                        "options": None,
                        "answer": {"value": True},
                        "explanation": "带期望值的断言失败时会打印实际值，省去再跑一次加 print 的功夫。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-02-lesson-02",
                "objectives": """1. 能按 `session / module / function` 三种作用域组织 fixture；
2. 能区分「昂贵且可共享」与「必须隔离」的准备动作；
3. 会用 `yield` 写带清理逻辑的 fixture；
4. 会用 `conftest.py` 共享 fixture 而不重复定义。""",
                "why_learn": """每个用例都新建数据库、启动客户端，跑 200 个用例要十几分钟——这样的测试没人愿意跑。
但如果为了快就把数据全共享，用例之间会互相污染，失败顺序一变结果就变。
fixture 就是在这两者之间做取舍的工具。""",
                "concepts": """**作用域**：`function`（默认，每用例一次）、`module`（每文件一次）、`session`（整轮一次）。
**隔离与共享的边界**：连接/引擎可以 session 级共享，事务与业务数据必须 function 级隔离。
**yield fixture**：`yield` 之前是准备、之后是清理，即使用例失败也会执行清理。
**conftest.py**：同目录及子目录自动可见的 fixture 集合，不需要 import。
**依赖注入**：fixture 可以依赖别的 fixture，pytest 按依赖图自动排序与缓存。""",
                "plain": """把 fixture 想成做菜的备料：洗菜切菜（准备）很费时，如果每道菜都重来一遍就太慢。
但有些东西不能共用——比如调味碗，一道菜用完必须洗。
`session` 作用域是"整个厨房只备一次料"，`function` 是"每道菜单独一份"。
判断标准很简单：共享会不会让上一道菜的味道串到下一道。""",
                "syntax": """```python
import pytest

@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite:///:memory:")
    yield eng
    eng.dispose()

@pytest.fixture(scope="function")
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()      # 每个用例结束回滚，天然隔离
    connection.close()
```

- `scope="session"` 在整轮测试中只创建一次。
- `yield` 之后的代码是清理逻辑，失败也会执行。
- 事务回滚是"共享引擎 + 用例隔离"的标准做法。""",
                "example_code": '''# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.main import app
from app.db.session import get_db


@pytest.fixture(scope="session")
def engine():
    """整轮测试共用一个内存库引擎：建表昂贵，只做一次。"""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    """每个用例独立事务，结束后回滚，用例之间互不影响。"""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """覆盖 get_db，让接口用测试事务里的会话。"""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()''',
                "code_lines": """1. `scope="session"` 只建一次表：`create_all` 在 200 个用例里跑 200 次纯属浪费。
2. `check_same_thread=False` 让内存库可跨线程访问（TestClient 会切线程）。
3. `engine.dispose()` 在整轮结束时释放连接，避免资源泄漏。
4. `scope="function"` 的 `db` 依赖 `engine`，pytest 自动保证 engine 先建好。
5. `transaction.rollback()` 是关键：用例写入的数据在结束时全部撤销，下一个用例看到的是干净状态。
6. `dependency_overrides` 把生产用的 `get_db` 换成测试会话，接口代码一行不改。
7. `clear()` 必须放在 `finally` 语义的位置（yield 之后），否则后续用例会串用覆盖。""",
                "output": """$ pytest tests/ -q
........................................................................
........................................................................
..............................................................
========== 134 passed in 4.21s ==========

$ pytest tests/ -q --setup-show | head -12
SETUP    S engine
        SETUP    F db
        SETUP    F client
        tests/test_tasks.py::test_create_task (fixtures used: client, db, engine)
        TEARDOWN F client
        TEARDOWN F db
        SETUP    F db
        SETUP    F client
        tests/test_tasks.py::test_list_tasks (fixtures used: client, db, engine)
        TEARDOWN F client
        TEARDOWN F db
TEARDOWN S engine""",
                "mistakes": """- 所有 fixture 都用默认 `function` 作用域，导致每个用例都重建数据库。
- 把 `session` 作用域的 `db` 直接给用例写入数据，用例之间互相污染。
- `yield` 之后忘记清理，测试跑完连接没释放，第二次跑就报「database is locked」。
- fixture 定义在每个测试文件里复制粘贴，改一处漏三处。
- 在 fixture 里 `assert`，失败信息会指向 fixture 而不是用例，难以定位。""",
                "error_analysis": """`ScopeMismatch: You tried to access the function scoped fixture db with a session scoped request object`
—— 作用域方向错了：`session` 级 fixture 不能依赖 `function` 级 fixture。把依赖顺序倒过来。

`sqlite3.OperationalError: database is locked`
—— 前一用例的事务没关。检查 `yield` 后是否真的 `rollback()` + `close()`。

用例单独跑通过、一起跑失败
—— 典型的用例间污染。把共享 fixture 改成事务回滚隔离。

`fixture 'client' not found`
—— fixture 不在 `conftest.py` 里、或者测试文件不在其子目录下。""",
                "beginner_practice": """1. 写一个 `session` 作用域的 `engine` fixture 和一个 `function` 作用域的 `db` fixture，并验证后者在用例结束后回滚。
2. 把某个测试文件里重复定义的 fixture 移到 `conftest.py`，确认所有文件仍能正常使用。""",
                "advanced_practice": """给现有测试套件加一个 `tmp_project` fixture：在临时目录生成一个最小项目结构（两个文件），
用例结束后自动删除。要求：(1) 用 `tmp_path` 而非 `tempfile`；(2) 某用例失败时目录仍被清理；
(3) 说明为什么这个 fixture 应该是 `function` 作用域而不是 `session`。""",
                "quiz_note": "本节 6 道题：2 道基础理解（作用域语义、yield fixture）+ 2 道代码阅读（读 setup-show 输出、读依赖关系）+ 2 道应用练习（选对作用域、判断隔离方案）。",
                "summary": """作用域是成本与隔离的权衡：引擎 session 级、数据 function 级。
`yield` 之前准备、之后清理，失败也会执行清理。
`conftest.py` 是共享 fixture 的唯一正确位置，避免复制粘贴。
「共享引擎 + 事务回滚」是数据库测试的标准隔离方案。""",
                "next_lesson": "数据库能隔离了，但网络和模型调用还不行——下一节用 mock 把它们换掉。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-02-02",
                        "name": "fixture 作用域与测试隔离",
                        "goal": "能按成本与隔离需求选择 fixture 作用域，用事务回滚实现用例隔离。",
                        "minutes": 40,
                        "criteria": "能写出 session 级引擎 + function 级会话的 fixture 组合，并说明为什么这个组合既快又不串数据。",
                        "requires": ["software-engineering-deploy-02-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-02-02-1",
                        "kp": 0,
                        "title": "选出正确的作用域",
                        "description": """四个准备动作，分别应该用哪个作用域？说明理由。
(1) 创建数据库引擎并建表（约 300ms）
(2) 插入一个测试用户
(3) 启动 TestClient
(4) 生成一份 5MB 的临时 CSV 文件供导出用例使用""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''(1) `session`：建表最贵，且表结构在所有用例间一致，共享无副作用。
(2) `function`：用户数据会被用例修改或删除，必须每个用例一份干净数据。
(3) `function`：TestClient 内部持有依赖覆盖状态，跨用例共享容易串。
   若有大量用例且启动成本高，可考虑 `module`，但要确保 `dependency_overrides` 每次清理。
(4) `function`：文件内容可能被用例改写；若只读且生成昂贵，可提升到 `module` 并在文档里写明"只读"。
判断标准始终是：共享会不会让一个用例的副作用影响另一个。''',
                        "explanation": "作用域不是越共享越好，是「共享安全」才共享。",
                    },
                    {
                        "code": "sed-ex-02-02-2",
                        "kp": 0,
                        "title": "补上清理逻辑",
                        "description": """下面 fixture 漏了清理，导致第二次运行报 `database is locked`。补全它。

```python
@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
```""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

顺序很重要：先关 session（它会提交/刷新），再回滚事务，最后关连接。
用 try/finally 包住 yield，确保用例抛异常时清理也会执行。''',
                        "explanation": "fixture 的清理是正确性的一部分，不是可选项。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-02-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "默认情况下，`@pytest.fixture` 的作用域是？",
                        "options": [
                            ("A", "session"),
                            ("B", "module"),
                            ("C", "function"),
                            ("D", "class"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "默认 function：每个用例都会重新执行一次，隔离性最好但成本最高。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 `yield` 形式的 fixture，正确说法有？（多选）",
                        "options": [
                            ("A", "yield 之前是准备阶段"),
                            ("B", "yield 之后是清理阶段"),
                            ("C", "用例失败时清理不会执行"),
                            ("D", "清理应放在 try/finally 里更稳妥"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 错误：pytest 保证 yield fixture 的清理会执行，这也是它优于 setup/teardown 的地方。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """从输出看，`engine` 这个 fixture 在整个测试过程中被创建了几次？

```
SETUP    S engine
        SETUP    F db
        ...
TEARDOWN S engine
```""",
                        "options": [("A", "每个用例一次"), ("B", "每个文件一次"), ("C", "整轮一次"), ("D", "没有创建")],
                        "answer": {"value": "C"},
                        "explanation": "`S` 表示 session 作用域，整个测试会话只 SETUP 与 TEARDOWN 一次。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "用例单独跑通过、和其他用例一起跑失败，最可能的原因是？",
                        "options": [
                            ("A", "Python 版本不兼容"),
                            ("B", "用例之间存在数据污染，共享了未隔离的状态"),
                            ("C", "断言的写法有问题"),
                            ("D", "pytest 版本太低"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这是典型症状：固定顺序下前一个用例留下的数据影响了后一个。改用事务回滚隔离。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让某个 fixture 在整轮测试中只执行一次，装饰器应写？",
                        "options": [
                            ("A", "@pytest.fixture()"),
                            ("B", "@pytest.fixture(scope=\"session\")"),
                            ("C", "@pytest.fixture(once=True)"),
                            ("D", "@pytest.fixture(scope=\"global\")"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "合法作用域是 function / class / module / package / session，没有 global。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-02-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "把数据库引擎设为 session 作用域、把业务数据设为 function 作用域，既能加速又能保证隔离。",
                        "options": None,
                        "answer": {"value": True},
                        "explanation": "引擎与建表昂贵且无副作用，业务数据必须可回滚。这个组合是数据库测试的标准做法。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-02-lesson-03",
                "objectives": """1. 能识别测试里哪些依赖需要被隔离（网络、时间、随机、模型）；
2. 会用 `monkeypatch` 替换函数与属性，不污染全局；
3. 会用 `unittest.mock.patch` 断言"被调用了什么参数"；
4. 能判断什么时候不该 mock。""",
                "why_learn": """真实调用一次大模型接口要 2 秒、要花钱、还可能超时；跑 50 个用例就是 100 秒加几十次不稳定。
mock 的作用是让测试只验证你自己的逻辑，把不可控的外部因素换成可控的假实现。
但 mock 用多也会骗自己——它测的是"我以为的调用方式"，不是"真实行为"。""",
                "concepts": """**测试替身**：stub（返回固定值）、mock（可断言调用）、fake（可用实现，如内存队列）。
**monkeypatch**：pytest 内置，替换属性/环境变量/字典项，用例结束自动还原。
**patch 装饰器**：`@patch("app.services.llm.chat")` 替换模块路径上的名字，注意是「使用处」而不是「定义处」。
**断言调用**：`mock.assert_called_once_with(model="deepseek-chat", ...)`。
**不该 mock 的东西**：纯函数、你自己写的业务逻辑、数据库（用事务隔离更真实）。""",
                "plain": """mock 像电影里的替身演员：需要跳水、跳楼的镜头让替身上，主演只演文戏。
测试里的"危险镜头"是网络、时间、随机数、付费接口——这些换成替身，用例才能稳定又快速。
但替身演完，你得相信它长得像主演——所以每次 mock 都要确认「替身的行为与真实实现一致」，
否则测试全绿而线上全挂。""",
                "syntax": """```python
import pytest
from unittest.mock import patch, MagicMock

def test_uses_fake_clock(monkeypatch):
    monkeypatch.setattr("app.services.clock.now", lambda: fixed_time)
    assert is_expired(token) is False

def test_env_override(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    assert load_config().api_key == "test-key"

@patch("app.services.llm.httpx.post")
def test_chat_retries_on_timeout(mock_post):
    mock_post.side_effect = [httpx.TimeoutException("t/o"), MagicMock(json=lambda: {"ok": 1})]
    result = chat("hi")
    assert mock_post.call_count == 2
```

- `monkeypatch.setattr` 指定完整路径，作用域自动还原。
- `patch` 要 patch「被使用处的名字」，不是定义处。""",
                "example_code": '''# tests/test_llm_service.py
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.llm import chat


@patch("app.services.llm.httpx.post")
def test_chat_returns_content(mock_post) -> None:
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": "你好"}}]},
    )

    assert chat("你好") == "你好"
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "deepseek-chat"
    assert kwargs["timeout"] == 60


@patch("app.services.llm.httpx.post")
def test_chat_retries_once_then_succeeds(mock_post) -> None:
    mock_post.side_effect = [
        httpx.TimeoutException("timeout"),
        MagicMock(status_code=200, json=lambda: {"choices": [{"message": {"content": "ok"}}]}),
    ]

    assert chat("hi") == "ok"
    assert mock_post.call_count == 2


@patch("app.services.llm.httpx.post")
def test_chat_raises_after_retries(mock_post) -> None:
    mock_post.side_effect = httpx.TimeoutException("timeout")

    with pytest.raises(RuntimeError, match="模型服务超时"):
        chat("hi")
    assert mock_post.call_count == 2''',
                "code_lines": """1. `@patch("app.services.llm.httpx.post")` 替换的是 `llm.py` 里 `httpx.post` 这个名字，
   不是 `httpx` 库本身——patch 的目标永远是「被测代码查找它的位置」。
2. `MagicMock(json=lambda: ...)` 让假响应的 `.json()` 返回固定结构，避免真实网络。
3. `assert_called_once()` 断言只调用了一次，防止无意重复请求（浪费钱）。
4. `call_args` 取出实际参数，断言 `model` 与 `timeout`——这测的是"我们发对了请求"，不是模型返回什么。
5. `side_effect` 列表让前一次抛异常、后一次成功，精确模拟"重试一次就成功"。
6. `call_count == 2` 验证重试逻辑真的执行了，而不是碰巧一次成功。
7. 全部失败时断言抛出明确的中文异常，这条最有价值：它保证重试耗尽后不会静默返回空。""",
                "output": """$ pytest tests/test_llm_service.py -v
tests/test_llm_service.py::test_chat_returns_content PASSED
tests/test_llm_service.py::test_chat_retries_once_then_succeeds PASSED
tests/test_llm_service.py::test_chat_raises_after_retries PASSED

========== 3 passed in 0.08s ==========

# 对比：不打 mock 直接调真实接口
$ pytest tests/test_llm_real.py -q
========== 1 failed in 30.42s ==========
E   httpx.ConnectTimeout: timed out""",
                "mistakes": """- patch 了「定义处」而不是「使用处」，导致 mock 完全不生效（最经典的坑）。
- mock 返回值与真实响应结构不一致，测试绿了但线上 KeyError。
- 只断言 `called` 不断言参数，漏掉「传错 model 名」这类问题。
- 把数据库也 mock 掉，等于测试自己写的假实现，没有验证真实 SQL。
- 用 mock 掩盖了本该修的架构问题（比如业务逻辑里直接 new 了 HTTP 客户端）。""",
                "error_analysis": """mock 没生效，真实请求仍发出
—— patch 路径写错。规则是：被测文件里怎么写导入，就 patch 哪个名字。
若 `from app.services.llm import chat`，则 patch `tests.test_x.chat`；
若 `import app.services.llm` 再 `llm.chat()`，则 patch `app.services.llm.chat`。

`AttributeError: <module> does not have the attribute 'post'`
—— 路径第一段拼错，或该模块没有导入该名字。

`AssertionError: Expected 'post' to be called once. Called 0 times.`
—— 代码走了别的分支（比如参数校验提前返回），先确认被测路径真的执行到了调用点。

`TypeError: 'MagicMock' object is not subscriptable`
—— 假响应没配 `json` 或返回的不是 dict。给 MagicMock 显式传 `json=lambda: {...}`。""",
                "beginner_practice": """1. 用 `monkeypatch.setenv` 覆盖一个配置项，断言 `load_config()` 读到的是新值，并验证用例结束后环境变量已还原。
2. 给一个调用外部 HTTP 的函数写测试，用 `patch` 让它在 0.1 秒内返回固定结果。""",
                "advanced_practice": """为一个带重试的请求函数写三条用例：成功、重试一次成功、重试耗尽抛错。
要求断言调用次数与关键参数，并回答：为什么这三条用例比"调真实接口一次成功"更有价值？""",
                "quiz_note": "本节 6 道题：2 道基础理解（mock 的目标、monkeypatch 作用）+ 2 道代码阅读（读 patch 路径、读 call_count）+ 2 道应用练习（选对 patch 目标、判断是否该 mock）。",
                "summary": """mock 的目标是「被测代码查找依赖的位置」，不是依赖的定义处。
`monkeypatch` 适合替换属性与环境变量，结束后自动还原。
断言调用次数与参数，比断言返回值更能发现"发错请求"的问题。
纯函数和业务逻辑不要 mock，数据库用事务隔离而不是替身。""",
                "next_lesson": "测试都写好了，怎么知道测得够不够？下一节用覆盖率与 CI 把门槛固定下来。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-02-03",
                        "name": "mock 与外部依赖隔离",
                        "goal": "能用 monkeypatch 与 patch 隔离网络、时间与模型调用，并断言调用参数。",
                        "minutes": 40,
                        "criteria": "能独立为一个调用外部接口的函数写出成功、重试、耗尽三条用例，并正确断言调用次数与关键参数。",
                        "requires": ["software-engineering-deploy-02-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-02-03-1",
                        "kp": 0,
                        "title": "找出 patch 路径写错的地方",
                        "description": """被测代码 `app/services/mail.py`：

```python
import httpx

def send(to: str, body: str) -> None:
    httpx.post("https://mail/api/send", json={"to": to, "body": body})
```

测试里写了 `@patch("httpx.post")`，但 mock 不生效，仍然真的发请求。为什么？正确写法是什么？""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''原因：`mail.py` 里是 `import httpx` 再 `httpx.post(...)`，
它在自己的模块命名空间里查找 `httpx`，再取 `.post`。
patch 全局的 `httpx.post` 不会替换 `mail.py` 已经绑定的模块引用。

正确写法：
```python
@patch("app.services.mail.httpx.post")
def test_send(mock_post):
    send("a@b.c", "hi")
    mock_post.assert_called_once()
```

规则：patch 的路径 = 「被测代码查找这个名字的位置」。''',
                        "explanation": "这是 mock 最常见的失败原因，记住这条规则能省掉大量排查时间。",
                    },
                    {
                        "code": "sed-ex-02-03-2",
                        "kp": 0,
                        "title": "断言重试次数",
                        "description": """`fetch_with_retry(url, retries=3)` 在超时时应重试 3 次（共 4 次请求）后抛错。
写一条用例验证这个行为。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@patch("app.services.fetch.httpx.get")
def test_fetch_retries_three_times_then_raises(mock_get):
    mock_get.side_effect = httpx.TimeoutException("timeout")

    with pytest.raises(RuntimeError, match="重试"):
        fetch_with_retry("https://example.com", retries=3)

    assert mock_get.call_count == 4   # 首次 + 3 次重试

注意断言的是 4 而不是 3：retries 表示"额外重试次数"，不是总请求数。
用例名里写清 three_times，避免下一个人误读语义。''',
                        "explanation": "调用次数断言能发现「少重试一次」或「无限重试」这类隐蔽缺陷。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-02-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "被测试文件里写的是 `from app.services.llm import chat`，要 mock 掉 `chat`，patch 目标应是？",
                        "options": [
                            ("A", "app/services/llm.py"),
                            ("B", "app.services.llm.chat"),
                            ("C", "被测文件所在模块的 chat（如 tests.test_x.chat）"),
                            ("D", "builtins.chat"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "`from ... import` 把名字绑定到当前模块命名空间，必须 patch 使用处的名字。",
                        "difficulty": "advanced",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些通常**不该**用 mock 替换？（多选）",
                        "options": [
                            ("A", "自己写的纯函数"),
                            ("B", "付费的大模型接口"),
                            ("C", "数据库查询（应改用测试事务）"),
                            ("D", "当前系统时间"),
                        ],
                        "answer": {"values": ["A", "C"]},
                        "explanation": "mock 纯函数等于测试自己写的假实现，没有价值；数据库用事务隔离更真实。B/D 是合理的 mock 对象。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """`mock_post.assert_called_once()` 失败并提示 `Called 2 times`，说明？

```python
mock_post.side_effect = [TimeoutException(), MagicMock(...)]
chat("hi")
assert mock_post.call_count == 1
```""",
                        "options": [
                            ("A", "mock 配置错了"),
                            ("B", "代码里发生了重试，实际请求了两次"),
                            ("C", "pytest 计数有 bug"),
                            ("D", "断言写法不对"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "第一次超时触发重试逻辑，这正是要验证的行为；断言应改为 `call_count == 2`。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """`mock_post.call_args` 返回什么？

```python
args, kwargs = mock_post.call_args
```

用途是什么？""",
                        "options": [
                            ("A", "返回 mock 对象的配置"),
                            ("B", "返回最后一次调用的位置参数与关键字参数，可断言请求内容"),
                            ("C", "返回调用次数"),
                            ("D", "返回异常信息"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "用它断言 model、timeout 等关键参数，能发现「请求发错了」这类问题。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "用 monkeypatch 让 `app.services.clock.now` 返回固定时间，写法是？",
                        "options": [
                            ("A", "monkeypatch.setenv(\"now\", fixed)"),
                            ("B", "monkeypatch.setattr(\"app.services.clock.now\", lambda: fixed)"),
                            ("C", "clock.now = fixed"),
                            ("D", "monkeypatch.patch(now=fixed)"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`setattr` 接收「点分路径 + 新值」，且用例结束后自动还原，不需要手动恢复。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-02-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "mock 的返回值结构可以与真实接口不同，只要测试自己想断言的部分对得上就行。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "结构不一致会导致真实运行时 KeyError/AttributeError，而测试全绿——这是最危险的假绿。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-02-lesson-04",
                "objectives": """1. 能读懂覆盖率报告的四个数字（语句、分支、缺失行、未覆盖函数）；
2. 能判断「覆盖率 80%」是否真的有质量，识别被凑数的用例；
3. 能配置 `pyproject.toml` 设定覆盖率门槛；
4. 能写一条最小的 GitHub Actions 流水线，在提交时自动跑测试。""",
                "why_learn": """覆盖率不是目标，是雷达：它告诉你哪些代码从来没有被执行过——那里藏着的 bug 没人知道。
但覆盖率也能被刷：一个用例把所有函数都调用一遍，覆盖率 95%，断言一个都没有。
真正要建立的是「提交即验证」的机制，让不合格的改动根本合不进去。""",
                "concepts": """**语句覆盖 vs 分支覆盖**：前者看每行是否执行，后者看每个 `if` 的两个方向是否都走过。
**覆盖率的局限**：执行过 ≠ 断言过。100% 覆盖仍可能漏掉错误行为。
**门槛策略**：新项目设 70–80% 并逐步提高；老项目先锁住当前值，禁止下降（ratchet）。
**CI 流水线**：`on: pull_request` 触发，跑 lint + 测试 + 覆盖率，失败则阻止合并。
**缓存**：缓存 `~/.cache/pip` 与依赖，能把流水线从 3 分钟压到 40 秒。""",
                "plain": """覆盖率就像体检报告里的"检查了哪些项目"，不是"身体好不好"。
它只说明这些代码被执行过，不说明结果对不对——就像考试时把每道题都写了名字但没作答，出席率满分。
门槛的作用是防止退步：今天 80%，明天提了个功能掉到 60%，流水线就该把它拦下来。
CI 是那个不会累、不会忘、不会"这次先放过"的检查员。""",
                "syntax": """**pyproject.toml 配置**

```toml
[tool.pytest.ini_options]
markers = ["slow: 慢用例"]
addopts = "-q"

[tool.coverage.run]
source = ["app"]
branch = true

[tool.coverage.report]
fail_under = 75
show_missing = true
skip_covered = true
```

**命令**

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=75
```

- `branch = true` 打开分支覆盖，比语句覆盖更严格。
- `fail_under` 低于门槛直接非零退出，CI 据此判定失败。""",
                "example_code": '''# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: 安装依赖
        run: |
          python -m pip install -U pip
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov

      - name: 代码检查
        run: ruff check backend/app

      - name: 运行测试并校验覆盖率
        working-directory: backend
        run: pytest --cov=app --cov-report=term-missing --cov-fail-under=75

      - name: 上传覆盖率报告
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: backend/.coverage''',
                "code_lines": """1. `on: pull_request` 让每次提 PR 都自动跑，这是"提交即验证"的关键触发器。
2. `cache: pip` 缓存依赖，第二次运行省掉 1–2 分钟安装时间。
3. 依赖分两步装：先项目依赖，再装测试工具，职责清晰且便于单独升级。
4. `ruff check` 放在测试之前：语法/风格问题比测试失败更廉价，早失败早修。
5. `working-directory: backend` 避免在每个命令前加 `cd`。
6. `--cov-fail-under=75` 让覆盖率不达标时流水线直接失败，这是"门槛"的落地方式。
7. `if: always()` 保证测试失败时也上传报告，否则最需要看报告的时候反而没有。""",
                "output": """$ pytest --cov=app --cov-report=term-missing -q
---------- coverage: platform linux ----------
Name                          Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------------
app/services/llm.py              82      6     18      3    89%   47-52
app/services/export.py           61     14     12      4    74%   88-96, 102
app/api/v1/tasks.py              95      0     22      0   100%
---------------------------------------------------------------------
TOTAL                           738     42    126     11    92%

1 failed, 133 passed in 6.12s

# 门槛未达时
$ pytest --cov=app --cov-fail-under=95
ERROR: Coverage failure: total of 92 is less than fail-under=95
exit code 1""",
                "mistakes": """- 为了凑覆盖率写「只调用不断言」的用例，覆盖率上去了，缺陷一个没拦住。
- 把 `fail_under` 设成 100，团队天天被拦，最后集体学会加 `# pragma: no cover`。
- 只统计语句覆盖，`if` 的异常分支从来没走过却显示 100%。
- CI 只在 `push` 时跑、不在 `pull_request` 时跑，等于没有门禁。
- 覆盖率报告当成成绩单给人排名，导致大家拆分函数刷指标。""",
                "error_analysis": """`ERROR: Coverage failure: total of 92 is less than fail-under=95`
—— 覆盖率未达门槛，退出码非零。要么补测试，要么评估门槛是否设得过高。

`ModuleNotFoundError: No module named 'app'`
—— 在错误的目录执行，或没装项目为可编辑包。用 `working-directory` 或 `pip install -e .` 解决。

`CoverageWarning: No data was collected`
—— `--cov=app` 的路径不对，或测试根本没跑到该包。

CI 上超时
—— 通常是没缓存依赖，或测试里有真实网络调用（应 mock 掉）。""",
                "beginner_practice": """1. 给现有项目加 `[tool.coverage.report]` 配置，设 `fail_under = 75`、开 `branch = true`，跑一次看当前覆盖率。
2. 找出 `Missing` 列里的一行未覆盖代码，补一条能走到它的用例。""",
                "advanced_practice": """写一个最小 CI 配置，要求：(1) 在 PR 上触发；(2) 缓存依赖；(3) lint 与测试分两步；
(4) 覆盖率不达标时失败；(5) 失败时仍上传报告。
完成后说明：如果团队当前覆盖率只有 40%，`fail_under` 应该设成多少，为什么？""",
                "quiz_note": "本节 6 道题：2 道基础理解（覆盖率局限、分支覆盖）+ 2 道流程阅读（读覆盖率报告、读 CI 配置）+ 2 道应用练习（选对门槛策略、判断 CI 触发器）。",
                "summary": """覆盖率是雷达不是成绩：它指出没被执行过的代码，不保证行为正确。
分支覆盖比语句覆盖更严格，异常路径必须被走到。
门槛要能守住但不逼人作弊，老项目用「禁止下降」而不是一步到位。
CI 在 PR 上触发才是门禁，只在 push 上跑等于事后通知。""",
                "next_lesson": "代码有了测试和门禁，下一步把运行环境也固化下来——进入 Docker。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-02-04",
                        "name": "覆盖率门槛与 CI 流水线",
                        "goal": "能读懂覆盖率报告并设置合理门槛，写出在 PR 上自动执行的 CI 流水线。",
                        "minutes": 35,
                        "criteria": "能根据报告指出未覆盖的关键分支，并写出一条含缓存、lint、测试与覆盖率门槛的 CI 配置。",
                        "requires": ["software-engineering-deploy-02-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-02-04-1",
                        "kp": 0,
                        "title": "读懂覆盖率报告",
                        "description": """报告显示：

```
Name                    Stmts   Miss Branch BrPart  Cover   Missing
app/services/export.py     61     14     12      4    74%   88-96
app/services/llm.py        82      6     18      3    89%   47-52
```

两个模块哪个更该优先补测试？为什么？""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''优先 `export.py`。理由：
1. 覆盖率更低（74% vs 89%），缺失语句更多（14 行 vs 6 行）；
2. `88-96` 是连续 9 行，通常是一个完整函数或一个异常分支，属于"整块没测过"，风险高于零散的几行；
3. 还要看业务重要性：导出涉及用户数据与文件写入，出错代价比内部工具函数高。

判断顺序：未覆盖块的连续性 → 业务关键度 → 覆盖率数字本身。''',
                        "explanation": "覆盖率数字只是入口，真正要看的是「哪段代码从没被执行过」。",
                    },
                    {
                        "code": "sed-ex-02-04-2",
                        "kp": 0,
                        "title": "写一条覆盖率门槛配置",
                        "description": """在 `pyproject.toml` 里配置：开启分支覆盖、只统计 `app`、覆盖率低于 75% 时失败、报告显示缺失行。""",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''[tool.coverage.run]
source = ["app"]
branch = true

[tool.coverage.report]
fail_under = 75
show_missing = true

配合命令：
pytest --cov=app --cov-report=term-missing

注意：fail_under 只在使用 --cov 时生效；只写配置不跑覆盖率不会拦截。''',
                        "explanation": "配置一次，全队一致，比每个人记不同命令可靠。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-02-04-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "覆盖率 100% 能否说明代码没有缺陷？",
                        "options": [
                            ("A", "能，全覆盖等于无 bug"),
                            ("B", "不能，只说明代码被执行过，不说明断言了正确行为"),
                            ("C", "能，只要同时开启分支覆盖"),
                            ("D", "取决于使用哪种报告格式"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "执行不等于验证。没有断言的用例也能刷满覆盖率，却拦不住任何缺陷。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-04-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 CI 流水线，正确做法有？（多选）",
                        "options": [
                            ("A", "在 pull_request 上触发"),
                            ("B", "缓存依赖以缩短时间"),
                            ("C", "只在发布前手动跑一次"),
                            ("D", "覆盖率不达标时让流水线失败"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 会让问题在合并后才暴露，失去门禁意义。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-02-04-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "报告里 `Branch 12, BrPart 4` 表示什么？",
                        "options": [
                            ("A", "12 个分支中 4 个只走了一个方向"),
                            ("B", "12 个文件里有 4 个没测"),
                            ("C", "4 个分支全部未覆盖"),
                            ("D", "分支覆盖率为 4%"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "BrPart（partial branch）指该分支的两个方向只走过其一，是分支覆盖的重点关注项。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-04-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "CI 里 `if: always()` 用在「上传覆盖率报告」这一步，作用是？",
                        "options": [
                            ("A", "让这一步永远成功"),
                            ("B", "即使前面步骤失败也执行，保证失败时也能拿到报告"),
                            ("C", "跳过这一步"),
                            ("D", "无条件重复执行三次"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "最需要报告的时刻恰恰是失败时，默认行为会因为前一步失败而跳过。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-02-04-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让 `pytest` 在覆盖率低于 75% 时以非零码退出，命令里应加？",
                        "options": [
                            ("A", "--cov-min=75"),
                            ("B", "--cov-fail-under=75"),
                            ("C", "--coverage=75"),
                            ("D", "--fail=75"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "参数名是 `--cov-fail-under`；也可以在 pyproject 里配 `fail_under`。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-02-04-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "老项目当前覆盖率 40%，直接把门槛设成 80% 是最合理的做法。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "门槛过高会逼团队写凑数用例或加 pragma。合理做法是先锁住 40% 并禁止下降，逐步提高。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
