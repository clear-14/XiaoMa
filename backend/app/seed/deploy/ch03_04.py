"""软件工程与项目部署：第 3—4 章（Docker 基础、Docker Compose）。"""

CHAPTERS: list[dict] = [
    # ==================================================================
    # 第 3 章 Docker 基础
    # ==================================================================
    {
        "code": "software-engineering-deploy-03",
        "title": "Docker 基础",
        "description": "把运行环境固化进镜像，消除「我这能跑」。",
        "order_index": 3,
        "lessons": [
            {
                "code": "software-engineering-deploy-03-lesson-01",
                "objectives": """1. 能说清镜像与容器的关系，以及「分层」为什么能节省空间；
2. 能读懂 `docker ps` / `docker images` 的关键列；
3. 会用 `run / exec / logs / stop / rm` 完成日常容器操作；
4. 理解容器内文件为什么会丢，数据该怎么留住。""",
                "why_learn": """同一份代码，在你的机器上跑得好好的，到同事电脑上报 `ModuleNotFoundError`，到服务器上报 `GLIBC 版本过低`。
差异不在代码，在环境：Python 版本、系统库、时区、字体。
Docker 把环境和代码一起打包，让「跑起来」这件事只取决于镜像，而不取决于谁的电脑。""",
                "concepts": """**镜像 image**：只读的模板，由多层文件系统叠加而成，每层对应一条 Dockerfile 指令。
**容器 container**：镜像的一个运行实例，在只读层之上加一个可写层。
**分层复用**：多个镜像共享相同的底层，所以再装一个 Python 镜像往往只占几百兆。
**容器的可写层随容器删除而消失**：这是"容器里的数据会丢"的根本原因，需要卷来持久化。
**生命周期**：created → running → paused → exited → removed。""",
                "plain": """镜像像一张系统安装光盘，容器像用这张光盘装出来的一台机器。
同一张光盘可以装很多台机器，机器坏了删掉重装，光盘还在。
但你在机器上存的文件只存在那台机器上——机器一删，文件就没了。
所以「数据库放哪儿」这个问题的标准答案是：放进卷里，而不是放在容器自己的硬盘上。""",
                "syntax": """```bash
docker pull python:3.12-slim             # 从仓库拉镜像
docker images                            # 列出本地镜像
docker run -d --name demo -p 8000:8000 python:3.12-slim sleep infinity
docker ps                                # 正在运行的容器
docker ps -a                             # 含已退出的容器
docker exec -it demo bash                # 进入容器执行命令
docker logs -f demo                      # 持续查看输出
docker stop demo && docker rm demo      # 停止并删除
docker rmi python:3.12-slim              # 删除镜像
```

- `-d` 后台运行，`-it` 交互式，`-p 宿主:容器` 映射端口，`--name` 起名便于操作。
- `docker rm` 删容器，`docker rmi` 删镜像，两者不可混用。""",
                "example_code": '''# 场景：把一个小应用跑进容器并观察数据丢失

# 1) 拉取基础镜像
docker pull python:3.12-slim

# 2) 启动一个容器，容器内写一个文件
docker run -d --name demo python:3.12-slim sleep infinity
docker exec demo sh -c "echo hello > /tmp/note.txt"
docker exec demo cat /tmp/note.txt
# hello

# 3) 删除容器（模拟重新部署）
docker rm -f demo

# 4) 用同一个镜像再起一个容器，文件还在吗？
docker run -d --name demo2 python:3.12-slim sleep infinity
docker exec demo2 ls /tmp/note.txt
# ls: /tmp/note.txt: No such file or directory

# 5) 用卷再来一次
docker run -d --name demo3 -v demo-data:/data python:3.12-slim sleep infinity
docker exec demo3 sh -c "echo hello > /data/note.txt"
docker rm -f demo3
docker run -d --name demo4 -v demo-data:/data python:3.12-slim sh -c "cat /data/note.txt"
docker logs demo4
# hello''',
                "code_lines": """1. `python:3.12-slim` 是「官方 Python 3.12 + 精简 Debian」镜像，比完整版小一半以上。
2. `-d` 让容器后台运行；用 `sleep infinity` 占住主进程，否则容器会立刻退出。
3. `docker exec` 在运行中的容器里执行命令，是排查问题的常用入口。
4. 删容器后 `/tmp/note.txt` 消失——它写在容器的可写层，随容器一起销毁。
5. `-v demo-data:/data` 把命名卷挂到容器内 `/data`，卷独立于容器生命周期。
6. 删掉 demo3 之后卷仍然存在，新容器挂同一个卷就能读到之前写的内容。
7. `docker logs` 读取容器主进程的输出，是看服务是否起来的第一手段。""",
                "output": """$ docker ps
CONTAINER ID   IMAGE              STATUS         PORTS                    NAMES
a1b2c3d4e5f6   python:3.12-slim   Up 2 minutes   0.0.0.0:8000->8000/tcp   demo

$ docker images
REPOSITORY   TAG        IMAGE ID       SIZE
python       3.12-slim  8f3a1c2d9e0b   127MB

$ docker exec demo sh -c "echo hello > /tmp/note.txt"
$ docker exec demo cat /tmp/note.txt
hello

$ docker rm -f demo
demo

$ docker run -d --name demo2 python:3.12-slim sleep infinity
$ docker exec demo2 ls /tmp/note.txt
ls: /tmp/note.txt: No such file or directory""",
                "mistakes": """- 把数据库文件放在容器内路径（如 `/app/data`）却没挂卷，重建容器数据全丢。
- `docker run` 不带 `-d`，容器前台运行把终端占住，以为卡死了。
- 用 `docker ps` 找不到容器就以为没起，其实是已退出——要用 `docker ps -a` 并看 `docker logs`。
- 直接改容器内文件当"修 bug"，容器一重建改动全消失。
- 不清理废弃容器与镜像，磁盘越来越小，最后 `no space left on device`。""",
                "error_analysis": """`docker: Cannot connect to the Docker daemon`
—— Docker Desktop 没启动，或当前用户无权限。启动 Docker Desktop 后重试。

`docker: Error response from daemon: port is already allocated`
—— 宿主机端口被占用。`netstat -ano | findstr :8000` 找到进程，或改用 `-p 8001:8000`。

容器 `Exited (0)` 立刻退出
—— 主进程执行完了。服务类容器要前台常驻（如 `uvicorn ... `），或用 `sleep infinity` 占位。

`no space left on device`
—— 镜像与容器堆积。`docker system df` 看占用，`docker system prune` 清理（注意会删未使用卷）。""",
                "beginner_practice": """1. 拉取 `python:3.12-slim`，启动容器，用 `exec` 查看 Python 版本与系统信息。
2. 重复示例中的实验：分别在容器内路径与命名卷里写文件，删容器后对比是否还在。""",
                "advanced_practice": """用 `docker system df` 查看本机镜像、容器、卷、构建缓存各占多少空间。
然后回答：(1) 为什么 `docker system prune -a` 可能删掉你还要用的东西？
(2) 想只清理「已停止的容器和悬空镜像」但不碰卷，应该用什么命令？""",
                "quiz_note": "本节 6 道题：2 道基础理解（镜像与容器关系、分层复用）+ 2 道输出阅读（读 ps、读日志/错误）+ 2 道应用练习（选对持久化方式、选对清理命令）。",
                "summary": """镜像是只读模板，容器是它的运行实例，可写层随容器销毁。
容器内的数据默认不持久，要留住必须挂卷。
`docker ps -a` 与 `docker logs` 是排查容器退出的第一组合。
`rm` 删容器、`rmi` 删镜像，清理前先 `system df` 看占用。""",
                "next_lesson": "手动 `run` 参数越来越多，下一节把这些步骤写成 Dockerfile，让镜像可以重复构建。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-03-01",
                        "name": "镜像、容器与数据持久化",
                        "goal": "能区分镜像与容器，完成容器日常操作，并用卷解决数据丢失问题。",
                        "minutes": 30,
                        "criteria": "能解释容器删除后数据为什么丢失，并独立用命名卷完成一次跨容器数据保留验证。",
                        "requires": ["software-engineering-deploy-02-04"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-03-01-1",
                        "kp": 0,
                        "title": "为什么数据丢了",
                        "description": """某同事把 SQLite 数据库放在容器的 `/app/data/xiaoma.db`，没有挂卷。
每次 `docker compose up --build` 之后用户数据都没了。
请解释原因，并写出修复方案。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''原因：`/app/data` 在容器的可写层里。`up --build` 会重建容器，
可写层随旧容器销毁，数据库文件一起消失。镜像里也没有这份数据（它不在构建上下文中）。

修复：把数据目录挂成命名卷：
```yaml
services:
  backend:
    volumes:
      - xiaoma-data:/app/data
volumes:
  xiaoma-data:
```
卷独立于容器生命周期，重建容器后数据仍在。

顺带检查：卷里应同时保存 `.secret_key`，否则模型 API Key 无法解密。''',
                        "explanation": "这是容器化最常见的数据事故，成因永远是「数据写在了容器的可写层」。",
                    },
                    {
                        "code": "sed-ex-03-01-2",
                        "kp": 0,
                        "title": "看日志定位容器退出原因",
                        "description": """`docker ps` 看不到 `xiaoma-backend`，`docker ps -a` 显示 `Exited (1)`。
写出你的排查步骤与最可能的三个原因。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''步骤：
1. `docker ps -a` 确认状态与退出码；
2. `docker logs xiaoma-backend --tail 50` 看最后输出；
3. `docker inspect xiaoma-backend --format '{{.State.ExitCode}}'` 确认退出码。

最可能的三个原因：
- 启动脚本校验失败（例如 `BIND_ADDRESS=0.0.0.0` 但没设访问密码，entrypoint 主动拒启，exit 1）；
- 数据库迁移失败（路径不可写、旧库结构冲突）；
- 依赖服务未就绪就去连接（数据库容器还没 healthy）。

退出码 1 多为应用主动 `exit 1`，先看日志里的中文错误提示。''',
                        "explanation": "容器退出不看日志等于盲猜，日志里通常已经有明确结论。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-03-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "关于镜像与容器的关系，正确的是？",
                        "options": [
                            ("A", "一个容器只能对应一个专属镜像，不能复用"),
                            ("B", "镜像是只读模板，容器是它的运行实例"),
                            ("C", "容器删除后镜像也会被删除"),
                            ("D", "镜像可以直接运行，不需要容器"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "同一镜像可以启动任意多个容器；删容器不影响镜像。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "容器内数据会随容器删除而丢失，正确说法有？（多选）",
                        "options": [
                            ("A", "数据写在容器可写层，随容器销毁"),
                            ("B", "挂命名卷可以保留数据"),
                            ("C", "只要不重启 Docker 数据就不会丢"),
                            ("D", "绑定挂载宿主机目录也能保留"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 错误：删除容器就会丢，与是否重启 Docker 无关。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """`docker ps -a` 输出如下，这个容器现在在做什么？

```
CONTAINER ID   IMAGE           STATUS                     NAMES
a1b2c3d4e5f6   xiaoma-backend  Exited (1) 3 minutes ago   xiaoma-backend
```""",
                        "options": [
                            ("A", "正在运行"),
                            ("B", "已退出，退出码 1，需要看日志排查"),
                            ("C", "处于暂停状态"),
                            ("D", "正在重启"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`Exited (1)` 表示进程以非零码结束，属于异常退出。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-01-4",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": """执行 `docker run -d --name demo python:3.12-slim` 后 `docker ps` 看不到 demo。请说明原因，并写出确认容器的命令。""",
                        "answer": {"reference": "`python:3.12-slim` 的默认命令是交互式解释器，没有标准输入时立刻退出，容器的主进程结束，容器随之停止。用 `docker ps -a` 查看已退出容器，用 `docker logs demo` 看退出原因；想让它常驻要给一个前台命令，如 `sleep infinity`。", "keywords": ["主进程", "docker ps -a", "docker logs", "交互式解释器"]},
                        "explanation": "`python:3.12-slim` 不带命令会进入交互解释器并立即结束，容器随之退出。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-01-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让容器的 `/app/data` 使用命名卷 `xiaoma-data`，`docker run` 参数应写？",
                        "options": [
                            ("A", "-v /app/data"),
                            ("B", "-v xiaoma-data:/app/data"),
                            ("C", "--mount xiaoma-data"),
                            ("D", "-p xiaoma-data:/app/data"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "卷语法是 `卷名:容器路径`；`-p` 是端口映射，不是挂载。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-03-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "为了修一个线上 bug，可以直接 `docker exec` 进去改代码并重启容器，这是推荐做法。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "容器重建后改动全丢，且其他环境无法复现。正确做法是改代码、重建镜像。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-03-lesson-02",
                "objectives": """1. 能写出一个可运行的 Python 应用 Dockerfile，包含工作目录、依赖安装与启动命令；
2. 理解 `CMD` 与 `ENTRYPOINT` 的区别与配合方式；
3. 会选择合适的基础镜像（slim / alpine / full）；
4. 知道为什么不要用 `latest` 标签，以及怎么固定版本。""",
                "why_learn": """手敲 `docker run` 有十几个参数，换台机器就要重来一遍，还容易漏。
Dockerfile 把这些步骤写成文件，让"构建环境"变成可版本控制、可评审、可重复执行的代码。
它是 CI 与部署的输入：镜像构建得可复现，部署才可能稳定。""",
                "concepts": """**每条指令一层**：`FROM` / `WORKDIR` / `COPY` / `RUN` / `CMD` 各产生一层，层数影响体积与构建速度。
**WORKDIR**：设定之后所有相对路径的基准目录，比 `cd` 可靠。
**CMD vs ENTRYPOINT**：`ENTRYPOINT` 是固定可执行体，`CMD` 是默认参数；`docker run` 后面的参数会覆盖 CMD，追加在 ENTRYPOINT 之后。
**基础镜像取舍**：`slim`（Debian 精简，兼容好）、`alpine`（极小但 musl libc 可能编译失败）、`full`（体积大但工具全）。
**版本固定**：`python:3.12.7-slim` 而不是 `python:latest`，否则某天构建出的镜像和你昨天的不一样。""",
                "plain": """Dockerfile 是一份"装机说明书"：从哪张光盘开始、把哪些文件拷进去、装什么、最后运行什么。
`CMD` 是说明书的最后一句"默认执行这个"，你可以在开工时改口说"执行那个"。
`ENTRYPOINT` 更像"这台机器只能干这件事"，你只能给它加参数，不能换掉它。
基础镜像选型就是"选毛坯房"：精装省事但大，毛坯小但要自己装水管（缺编译工具）。""",
                "syntax": """```dockerfile
FROM python:3.12.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**ENTRYPOINT 配合 CMD**

```dockerfile
ENTRYPOINT ["uvicorn"]
CMD ["app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# docker run img app.other:app → 替换 CMD，ENTRYPOINT 不变
```

- `PYTHONUNBUFFERED=1` 让日志立刻输出，否则容器里看不到实时日志。
- `--no-cache-dir` 不留 pip 缓存，镜像更小。""",
                "example_code": '''# backend/Dockerfile
FROM python:3.12.7-slim

# 系统时区与编译依赖：只装必需的，装完清理 apt 缓存
ENV TZ=Asia/Shanghai \\
    PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先只拷贝依赖清单：依赖不变时这一层命中缓存，改代码不用重装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝源码
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# 以非 root 用户运行，降低容器逃逸风险
RUN useradd --create-home --uid 10001 appuser \\
    && mkdir -p /app/data \\
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
VOLUME ["/app/data"]

HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"

ENTRYPOINT ["./entrypoint.sh"]''',
                "code_lines": """1. `FROM python:3.12.7-slim` 固定到补丁版本：三个月后重新构建得到的仍是同一套运行时。
2. `PYTHONUNBUFFERED=1` 必须有，否则 stdout 被缓冲，`docker logs` 看不到实时输出。
3. `PIP_NO_CACHE_DIR=1` 省掉 pip 缓存层，镜像小几十兆。
4. `WORKDIR /app` 之后所有 `COPY`、`RUN` 的相对路径都以 `/app` 为基准。
5. **先拷 requirements 再拷源码**：依赖层不会因为改业务代码而失效，构建从 90 秒降到 5 秒。
6. `COPY app ./app` 只拷运行需要的目录，`tests/`、`.venv/` 不进镜像。
7. `chmod +x` 单独一层：entrypoint 必须有执行权限，否则容器报 permission denied。
8. `USER appuser` 切到非 root，是容器安全的基本要求。
9. `VOLUME` 声明数据目录，提醒使用者这里需要持久化。
10. `HEALTHCHECK` 让编排能判断"服务真的可用"，而不只是"进程还在"。""",
                "output": """$ docker build -t xiaoma-backend:dev ./backend
[+] Building 42.1s (12/12) FINISHED
 => [1/7] FROM docker.io/library/python:3.12.7-slim          12.3s
 => [2/7] WORKDIR /app                                        0.1s
 => [3/7] COPY requirements.txt ./                            0.0s
 => [4/7] RUN pip install --no-cache-dir -r requirements.txt  24.8s
 => [5/7] COPY app ./app                                      0.3s
 => [6/7] COPY entrypoint.sh ./entrypoint.sh                  0.0s
 => [7/7] RUN chmod +x entrypoint.sh                          0.4s
 => exporting to image                                        2.1s

$ docker run --rm -p 8000:8000 xiaoma-backend:dev
正在执行数据库迁移...
正在写入课程种子数据（幂等）...
启动小码后端...
INFO:     Uvicorn running on http://0.0.0.0:8000

$ docker images xiaoma-backend
REPOSITORY        TAG    SIZE
xiaoma-backend    dev    241MB""",
                "mistakes": """- 用 `COPY . .` 把 `.venv`、`node_modules`、`.env`、数据库全拷进镜像，体积暴涨且泄漏密钥。
- `CMD uvicorn app.main:app` 用 shell 形式，信号无法传递，`docker stop` 要等 10 秒超时。
- `FROM python:latest` 导致今天能构建、明天报错，且无法复现线上镜像。
- 用 `alpine` 跑需要编译 C 扩展的包（如 `psycopg2`），报 `gcc not found` 或 musl 兼容错误。
- `RUN cd /app && ...` 代替 `WORKDIR`，下一条指令又回到根目录。""",
                "error_analysis": """`exec ./entrypoint.sh: no such file or directory`
—— 常见两个原因：脚本没有执行权限（漏 `chmod +x`），或脚本 CRLF 换行（Windows 下编辑导致）。

`permission denied while trying to connect to the Docker daemon`
—— 当前用户无权限，Linux 需加入 `docker` 组，Windows 确认 Docker Desktop 运行。

`ModuleNotFoundError: No module named 'app'`
—— `COPY` 路径或 `WORKDIR` 不对。确认镜像里 `/app/app/main.py` 存在：`docker run --rm -it img ls /app`。

构建极慢且每次都重装依赖
—— `COPY . .` 放在 `pip install` 之前，任何代码改动都会打破依赖层缓存。把依赖安装提到前面。""",
                "beginner_practice": """1. 为一个最小的 FastAPI 应用写 Dockerfile，构建并运行，用 curl 访问它的 `/health`。
2. 故意把 `COPY` 与 `RUN pip install` 顺序调换，改一行代码后重新构建，对比耗时差异。""",
                "advanced_practice": """把现有 Dockerfile 改成以非 root 用户运行，并加上 HEALTHCHECK。
完成后回答：(1) 为什么 `USER` 要放在 `COPY` 之后？
(2) `HEALTHCHECK` 与 `docker ps` 显示的 `Up` 有什么区别？""",
                "quiz_note": "本节 6 道题：2 道基础理解（CMD 与 ENTRYPOINT、基础镜像选型）+ 2 道代码阅读（读 Dockerfile 层顺序、读构建日志）+ 2 道应用练习（选对 COPY 顺序、判断安全写法）。",
                "summary": """Dockerfile 是构建环境的代码化表达，每条指令一层。
依赖清单先拷贝、源码后拷贝，是构建提速最有效的一招。
`CMD` 可被覆盖，`ENTRYPOINT` 不行；exec 形式才能正确接收信号。
固定基础镜像版本、非 root 运行、加健康检查，是上线的最低要求。""",
                "next_lesson": "镜像能跑了，但 240MB 里有大半是构建工具，下一节用多阶段构建把它瘦下来。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-03-02",
                        "name": "编写可复现的 Dockerfile",
                        "goal": "能写出包含工作目录、依赖层优化、非 root 运行与健康检查的应用镜像。",
                        "minutes": 35,
                        "criteria": "能独立写出一个可构建可运行的 Dockerfile，并说明 COPY 顺序对构建缓存的影响。",
                        "requires": ["software-engineering-deploy-03-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-03-02-1",
                        "kp": 0,
                        "title": "修掉这个 Dockerfile 的四个问题",
                        "description": """```dockerfile
FROM python:latest
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD uvicorn app.main:app --host 0.0.0.0
```

指出至少四个问题并给出修正。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''1. `FROM python:latest`：版本不固定，构建不可复现 → 改为 `python:3.12.7-slim`。
2. `COPY . /app` 在最前且包含一切：每次改代码都打破依赖缓存，还把 .venv/.env/数据库拷进镜像
   → 改为先 `COPY requirements.txt` + `RUN pip install`，再 `COPY app ./app`；配合 .dockerignore。
3. `CMD` 用 shell 形式：信号传不到 uvicorn，`docker stop` 会等到超时被杀
   → 改为 exec 形式 `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`。
4. 没有 `EXPOSE` / 非 root 用户 / HEALTHCHECK：安全与可观测性不足 → 补 `USER` 与 `HEALTHCHECK`。
5. `WORKDIR` 放在 `COPY` 之后语义混乱：虽然不报错，但可读性差 → 提到最前面。''',
                        "explanation": "这四处问题在真实项目里几乎必现，是评审 Dockerfile 的固定检查项。",
                    },
                    {
                        "code": "sed-ex-03-02-2",
                        "kp": 0,
                        "title": "CMD 与 ENTRYPOINT 的行为",
                        "description": """镜像里写了：

```dockerfile
ENTRYPOINT ["uvicorn"]
CMD ["app.main:app", "--port", "8000"]
```

执行 `docker run img app.other:app --port 9000` 时，容器最终运行的命令是什么？""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''最终命令：`uvicorn app.other:app --port 9000`

规则：`docker run` 后的参数会**替换 CMD**，并追加到 ENTRYPOINT 之后。
所以 ENTRYPOINT 决定"运行什么程序"，CMD 提供"默认参数"。
若想追加而不是替换，需要 `docker run --entrypoint uvicorn img app.main:app --reload` 之类的显式写法（这里已用 ENTRYPOINT 固定）。''',
                        "explanation": "理解这一层关系，才能在编排里灵活覆盖启动参数而不改镜像。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-03-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`CMD` 与 `ENTRYPOINT` 的核心区别是？",
                        "options": [
                            ("A", "CMD 只能用于 Linux，ENTRYPOINT 跨平台"),
                            ("B", "ENTRYPOINT 是固定可执行体，CMD 提供可被 docker run 覆盖的默认参数"),
                            ("C", "CMD 只允许一条指令，ENTRYPOINT 允许多条"),
                            ("D", "两者完全等价，只是写法不同"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这正是「固定程序 + 可变参数」组合的由来。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些做法能加快镜像构建？（多选）",
                        "options": [
                            ("A", "先 COPY requirements.txt 再 COPY 源码"),
                            ("B", "使用 .dockerignore 排除 .venv 与 node_modules"),
                            ("C", "把 COPY . . 放在最前面"),
                            ("D", "合并多个 RUN 减少层数"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 会让任何代码改动都使依赖层缓存失效，是最常见的构建变慢原因。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """构建日志显示依赖安装每次都重新执行：

```
=> [4/7] RUN pip install --no-cache-dir -r requirements.txt  24.8s
```

而代码只改了一行。最可能的原因？""",
                        "options": [
                            ("A", "pip 缓存被禁用"),
                            ("B", "COPY . . 在 RUN pip install 之前，改动使该层缓存失效"),
                            ("C", "基础镜像有问题"),
                            ("D", "Docker 版本太低"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "层缓存按指令内容与输入文件哈希判断，任何 COPY 内容变化都会让后续层重建。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "容器启动报 `exec ./entrypoint.sh: no such file or directory`，但文件确实在镜像里。最可能原因是？",
                        "options": [
                            ("A", "文件路径写错"),
                            ("B", "脚本没有执行权限，或使用了 CRLF 换行"),
                            ("C", "镜像没有 Python"),
                            ("D", "端口被占用"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "无执行权限会报 permission denied；CRLF 换行会让解释器路径解析失败，报 no such file。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让容器日志实时可见，Dockerfile 里必须设置哪个环境变量？",
                        "options": [
                            ("A", "PYTHONUNBUFFERED=1"),
                            ("B", "LOG_LEVEL=DEBUG"),
                            ("C", "STDOUT=true"),
                            ("D", "TZ=UTC"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "Python 默认缓冲 stdout，容器里看不到实时日志；该变量关闭缓冲。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-03-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "容器默认以 root 运行，应通过 USER 指令切换到非 root 用户以降低风险。",
                        "options": None,
                        "answer": {"value": True},
                        "explanation": "非 root 运行能限制容器逃逸后的破坏范围，是容器安全的基本项。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-03-lesson-03",
                "objectives": """1. 能用多阶段构建把编译依赖与运行时分离；
2. 能估算镜像体积的主要来源并针对性瘦身；
3. 理解前端 `standalone` 产物与后端 slim 镜像的取舍；
4. 会用 `docker history` 定位体积异常层。""",
                "why_learn": """镜像不是越大越好：体积直接决定推送时间、拉取时间、冷启动速度与磁盘占用。
一个 1.2GB 的镜像在 CI 上每次推送要几分钟，回滚时拉取又是几分钟——故障恢复的窗口就这么被吃掉。
多阶段构建让你"用大镜像构建，用小镜像运行"。""",
                "concepts": """**多阶段构建**：一个 Dockerfile 里多个 `FROM`，用 `AS` 命名，`COPY --from=build` 只取产物。
**构建期 vs 运行期依赖**：gcc、node_modules、构建缓存只在构建阶段需要。
**体积来源**：基础镜像 > 依赖 > 源码 > 缓存残留。
**清理技巧**：`--no-cache-dir`、`rm -rf /var/lib/apt/lists/*`、合并 RUN 减少层。
**前端 standalone**：Next.js 的 `output: "standalone"` 只输出运行必需文件，比完整 node_modules 小一个数量级。""",
                "plain": """多阶段构建像做家具：在工厂（构建阶段）用锯子电钻把板材加工好，
送到客户家（运行阶段）的只有成品，不把整套工具一起搬过去。
镜像瘦身的思路是同一个：把"只在制造时需要"的东西留在工厂。
判断标准就一句：这个文件在容器运行时会被用到吗？不会就别带。""",
                "syntax": """```dockerfile
# ---- 构建阶段 ----
FROM python:3.12.7-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.12.7-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**前端 standalone**

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
```

- `COPY --from=builder` 只搬运指定路径，构建工具不进最终镜像。
- `npm ci` 比 `npm install` 更快且严格按 lock 文件安装。""",
                "example_code": '''# 后端：多阶段 + 依赖预编译
FROM python:3.12.7-slim AS builder

ENV PIP_NO_CACHE_DIR=1
WORKDIR /build

# 需要编译 C 扩展时临时安装工具链（仅构建阶段）
RUN apt-get update \\
    && apt-get install -y --no-install-recommends gcc libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt


FROM python:3.12.7-slim AS runtime

ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    TZ=Asia/Shanghai

# 只保留运行时需要的系统库
RUN apt-get update \\
    && apt-get install -y --no-install-recommends libpq5 \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app ./app

RUN useradd --create-home --uid 10001 appuser \\
    && mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]''',
                "code_lines": """1. 第一个 `FROM ... AS builder` 是构建阶段：gcc 与 libpq-dev 只装在这里。
2. `pip install --prefix=/install` 把包装到独立目录，方便整目录搬走。
3. 第二个 `FROM` 重新从干净基础镜像开始，**不会**继承 builder 里装的 gcc。
4. 运行时只装 `libpq5`（运行库）而不是 `libpq-dev`（开发头文件），体积差几十兆。
5. `rm -rf /var/lib/apt/lists/*` 放在同一个 RUN 里：分开写的话，前一层已经把那几十兆记进镜像了。
6. `COPY --from=builder /install /usr/local` 只搬依赖，不搬源码与工具链。
7. 用户在 runtime 阶段创建，`chown` 在 `COPY` 之后，避免权限被覆盖。
8. 最终镜像不含 gcc、不含 pip 缓存、不含 `requirements.txt` 之外的构建文件。""",
                "output": """$ docker build -t xiaoma-backend:multi ./backend
$ docker images xiaoma-backend
REPOSITORY        TAG      SIZE
xiaoma-backend    dev      241MB      # 单阶段
xiaoma-backend    multi    168MB      # 多阶段

$ docker history xiaoma-backend:dev --format "{{.Size}}\\t{{.CreatedBy}}" | head -6
98MB    RUN /bin/sh -c apt-get update && apt-get install -y --no-instal…
24.8MB  RUN /bin/sh -c pip install --no-cache-dir -r requirements.txt
34MB    COPY . /app
7.4kB   CMD ["uvicorn" "app.main:app" …]""",
                "mistakes": """- 在最终阶段又装了一遍开发依赖，「多阶段」只是形式，体积没降。
- `apt-get update` 与 `install` 分成两个 RUN，导致 apt 列表层永久留在镜像里。
- 镜像里保留测试代码、示例数据、`.git` 目录，既大又泄漏信息。
- 前端把整个 `node_modules` 拷进运行阶段，镜像从 150MB 变成 1.2GB。
- 为省体积用 `alpine` 却需要 glibc 兼容的二进制（如某些预编译包），运行时直接崩。""",
                "error_analysis": """`ImportError: libpq.so.5: cannot open shared object file`
—— 运行时缺少系统库。多阶段里只搬了 Python 包，忘了 `libpq5` 这类运行库。

构建成功但运行报 `ModuleNotFoundError`
—— `--prefix` 安装路径与运行时的 `sys.path` 不一致。补 `ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages` 或改用 venv 方式。

镜像体积没变化
—— 大概率在最终阶段又执行了 `pip install` 或 `COPY` 了大目录。用 `docker history` 逐层看谁最大。

前端容器启动报 `Cannot find module 'next'`
—— standalone 产物没拷全，缺少 `.next/static` 或 `server.js` 路径不对。""",
                "beginner_practice": """1. 把单阶段 Dockerfile 改成两阶段，用 `docker images` 对比体积变化。
2. 用 `docker history` 找出体积最大的三层，判断哪些本可以去掉。""",
                "advanced_practice": """为一个带 C 扩展依赖的 Python 应用做多阶段构建：构建阶段装 gcc 编译，运行阶段只保留运行库。
验收：(1) 体积比单阶段小 30% 以上；(2) 容器能正常启动；(3) 说明为什么 `apt-get update` 与 `install` 必须在同一个 RUN 里。""",
                "quiz_note": "本节 6 道题：2 道基础理解（多阶段作用、体积来源）+ 2 道代码阅读（读 docker history、读 COPY --from）+ 2 道应用练习（选对清理写法、判断是否该用 alpine）。",
                "summary": """多阶段构建的核心是「构建用大镜像、运行用小镜像」，靠 `COPY --from` 搬运产物。
`apt-get update && install && rm -rf lists` 必须在同一条 RUN 里。
体积问题先用 `docker history` 定位，再决定优化哪层。
用 alpine 之前先确认依赖有 musl 兼容的二进制，否则省下的空间要用调试时间来还。""",
                "next_lesson": "镜像瘦了，但构建时仍会把一堆无关文件拷进去，下一节用 .dockerignore 和缓存策略收口。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-03-03",
                        "name": "多阶段构建与镜像瘦身",
                        "goal": "能用多阶段构建分离构建与运行环境，并用 docker history 定位体积来源。",
                        "minutes": 40,
                        "criteria": "能把一个单阶段 Dockerfile 改成多阶段并让体积下降 30% 以上，且容器能正常启动。",
                        "requires": ["software-engineering-deploy-03-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-03-03-1",
                        "kp": 0,
                        "title": "找出体积浪费",
                        "description": """`docker history` 显示：

```
98MB    RUN apt-get update
52MB    RUN apt-get install -y gcc build-essential
24.8MB  RUN pip install -r requirements.txt
34MB    COPY . /app
```

指出两处可优化点并说明改法。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''1. `apt-get update` 单独成层占了 98MB：它下载的包索引在安装后就没用了，
   但因为分了两条 RUN，索引被固化在这一层。
   改法：`RUN apt-get update && apt-get install -y --no-install-recommends ... && rm -rf /var/lib/apt/lists/*`
   合并到同一个 RUN，索引不会进入最终镜像。

2. `gcc build-essential` 52MB 只在编译时用，运行期不需要：
   改法：放进 builder 阶段，最终阶段用 `COPY --from=builder` 搬产物，
   运行时只装 `--no-install-recommends` 的运行库。

3. 另外 `COPY . /app` 34MB 应配合 .dockerignore 排除 .git、tests、data。
   `--no-install-recommends` 也能省掉一批非必需的建议包。''',
                        "explanation": "体积优化的顺序永远是：先看 history 找最大层，再判断这层运行时是否需要。",
                    },
                    {
                        "code": "sed-ex-03-03-2",
                        "kp": 0,
                        "title": "为什么体积没降",
                        "description": """改成多阶段后镜像体积从 241MB 只降到 235MB。检查 Dockerfile 发现最终阶段里仍有：

```dockerfile
FROM python:3.12.7-slim
COPY --from=builder /install /usr/local
RUN pip install -r requirements.txt
COPY . .
```

问题在哪？""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''问题有三处：
1. `RUN pip install -r requirements.txt` 在最终阶段又装了一遍——多阶段的意义被抵消，
   而且这次没用 `--no-cache-dir`，缓存也进了镜像。
   删掉这行，依赖已经由 `COPY --from=builder /install` 提供。

2. `COPY . .` 把所有文件（含 .venv、tests、data）拷入最终镜像。
   改成只拷运行必需：`COPY app ./app`，并用 .dockerignore 兜底。

3. 若 requirements 里有构建期依赖（gcc 编译的包），它现在装在最终阶段，
   应该只装运行期依赖清单（常见做法：requirements.txt + requirements-dev.txt 分离）。

结论：多阶段不是加了 `AS builder` 就自动瘦身，**最终阶段不能再做构建动作**。''',
                        "explanation": "这是改造多阶段最常犯的错：复制粘贴时把原阶段的安装步骤一起带过来了。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-03-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "多阶段构建的主要目的是？",
                        "options": [
                            ("A", "让 Dockerfile 更短"),
                            ("B", "把构建依赖留在构建阶段，最终镜像只含运行时所需"),
                            ("C", "加快 pip 安装速度"),
                            ("D", "支持多平台构建"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "核心价值是体积与攻击面：gcc、构建缓存、测试代码都不进最终镜像。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些能有效减小镜像体积？（多选）",
                        "options": [
                            ("A", "pip install --no-cache-dir"),
                            ("B", "apt-get update 与 install 分开写"),
                            ("C", "同一 RUN 内 rm -rf /var/lib/apt/lists/*"),
                            ("D", "用 .dockerignore 排除 .venv 与 .git"),
                        ],
                        "answer": {"values": ["A", "C", "D"]},
                        "explanation": "B 反而增大体积：索引层被固化，无法在同层删除。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`COPY --from=builder /install /usr/local` 的作用是？",
                        "options": [
                            ("A", "把整个 builder 镜像复制过来"),
                            ("B", "只把 builder 阶段 `/install` 目录复制到最终镜像的 `/usr/local`"),
                            ("C", "在 builder 里执行命令"),
                            ("D", "删除 builder 阶段"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "精确路径复制是多阶段的核心：只搬需要的产物，不搬工具链。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """`docker history` 里出现 `98MB RUN apt-get update`，说明？

```
98MB   RUN /bin/sh -c apt-get update
52MB   RUN /bin/sh -c apt-get install -y gcc
```""",
                        "options": [
                            ("A", "apt 索引被固化在独立层，后续无法删除，白白占用空间"),
                            ("B", "这是正常的，apt 索引必须保留"),
                            ("C", "说明基础镜像损坏"),
                            ("D", "说明 Docker 缓存有问题"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "所以 update 与 install 要在同一条 RUN 里，末尾清理索引才能真正减小体积。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要在一个 RUN 里完成安装并清理索引，正确写法是？",
                        "options": [
                            ("A", "RUN apt-get update\nRUN apt-get install -y gcc\nRUN rm -rf /var/lib/apt/lists/*"),
                            ("B", "RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*"),
                            ("C", "RUN apt-get install -y gcc --clean"),
                            ("D", "RUN apt-get update --no-cache"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "必须在同一条 RUN（同一层）内完成，否则索引层的体积已经记入镜像。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-03-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只要用了多阶段构建，镜像体积就一定会显著下降。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "若最终阶段仍执行 pip install 或 COPY 大目录，体积不会下降。多阶段需要配合正确的阶段划分。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-03-lesson-04",
                "objectives": """1. 能用 `.dockerignore` 排除不该进镜像的文件；
2. 能按「变更频率从低到高」排列 Dockerfile 指令，最大化缓存命中；
3. 能读懂构建日志里的 `CACHED` 标记并判断缓存是否合理；
4. 知道构建上下文过大会带来什么问题。""",
                "why_learn": """`docker build .` 会先把整个项目目录打包发给 Docker 引擎——包括 `.venv`（几百兆）、`.git`（历史全部）、`node_modules`。
构建慢、镜像大、还可能把 `.env` 里的密钥打进镜像。
缓存则决定你改一行代码后是等 5 秒还是等 90 秒。这两件事决定了开发循环的舒适度。""",
                "concepts": """**构建上下文**：`docker build` 的目录参数，整个目录（受 .dockerignore 过滤后）会传给引擎。
**`.dockerignore`**：语法类似 `.gitignore`，在传输前就排除文件，既省时间又防泄漏。
**层缓存**：指令文本 + 输入文件内容哈希一致则命中；任何不一致，该层及其之后全部重建。
**指令排序原则**：越稳定的越靠前（基础镜像 → 系统依赖 → 语言依赖 → 源码）。
**缓存失效是连锁的**：第 5 层失效，第 6-12 层全部重跑。""",
                "plain": """构建上下文像寄快递：你把整个房间的东西装箱寄给工厂，工厂再从中挑需要的。
`.dockerignore` 就是装箱清单——不寄的东西干脆别装，运费（传输时间）和风险（泄漏）都省了。
缓存像流水线的半成品区：前面的工序没变，半成品可以直接拿来用；前面一改，后面全得重做。
所以要把"很少变的东西"放前面，"天天改的代码"放最后。""",
                "syntax": """**`.dockerignore`**

```gitignore
.git
.github
.venv
__pycache__
*.pyc
.pytest_cache
node_modules
frontend/.next
data
*.db
*.log
.env
.secret_key
tests
```

**缓存友好的顺序**

```dockerfile
FROM python:3.12.7-slim          # 1. 基础镜像：极少变
RUN apt-get update && ...        # 2. 系统依赖：偶尔变
COPY requirements.txt .          # 3. 依赖清单：偶尔变
RUN pip install -r requirements.txt   # 4. 依赖安装：随清单变
COPY app ./app                   # 5. 业务代码：天天变
CMD ["uvicorn", ...]             # 6. 启动命令：极少变
```

- `docker build --no-cache` 强制不用缓存，排查"缓存导致的问题"时用。
- `docker builder prune` 清理构建缓存，占用大时用。""",
                "example_code": '''# 场景：对比有无 .dockerignore 的构建耗时与上下文大小

# 1) 先看当前目录有多大
du -sh .              # 1.2G
du -sh .venv node_modules .git
# 420M  .venv
# 680M  node_modules
# 96M   .git

# 2) 不加 .dockerignore 直接构建
time docker build -t demo:no-ignore .
# Sending build context to Docker daemon  1.196GB
# real  1m38s

# 3) 加 .dockerignore 后
cat > .dockerignore <<'EOF'
.git
.venv
node_modules
__pycache__
*.pyc
.pytest_cache
data
*.db
*.log
.env
.secret_key
EOF

time docker build -t demo:ignored .
# Sending build context to Docker daemon  42.6MB
# real  0m26s

# 4) 改一行代码后再构建，观察缓存命中
sed -i 's/print("hi")/print("hello")/' app/main.py
docker build -t demo:ignored .
# => CACHED [2/6] RUN pip install -r requirements.txt   0.0s
# => [5/6] COPY app ./app                               0.2s''',
                "code_lines": """1. `du -sh` 先量化问题：上下文 1.2G 里 1.1G 是虚拟环境、node_modules 和 git 历史。
2. 构建日志第一行 `Sending build context to Docker daemon 1.196GB` 就是上下文大小，很多人忽略它。
3. `.dockerignore` 在传输**之前**生效，所以能把 1.19GB 降到 42MB，耗时从 98 秒降到 26 秒。
4. 除了速度，更重要的是安全：`.env`、`.secret_key`、`*.db` 根本不会进入构建上下文，不可能被打进镜像。
5. 改代码后重建，依赖安装那层显示 `CACHED`——因为 `requirements.txt` 没变。
6. 只有 `COPY app ./app` 及其后面的层重新执行，这就是"5 秒构建"的来源。
7. 若看到依赖层也重建了，说明 `COPY . .` 在它之前，或 requirements 被无意改动。""",
                "output": """$ docker build -t demo:no-ignore .
[+] Building 98.4s (9/9) FINISHED
 => Sending build context to Docker daemon  1.196GB
 => [4/9] RUN pip install -r requirements.txt                24.8s

$ docker build -t demo:ignored .
[+] Building 26.1s (9/9) FINISHED
 => Sending build context to Docker daemon  42.6MB
 => [4/9] RUN pip install -r requirements.txt                24.8s

$ docker build -t demo:ignored .      # 只改了一行业务代码
[+] Building 1.8s (9/9) FINISHED
 => CACHED [2/9] WORKDIR /app                                 0.0s
 => CACHED [3/9] COPY requirements.txt .                      0.0s
 => CACHED [4/9] RUN pip install -r requirements.txt          0.0s
 => [5/9] COPY app ./app                                      0.2s
 => [6/9] RUN chmod +x entrypoint.sh                          0.3s

$ docker system df
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Build Cache     42        0         1.8GB     1.8GB (100%)""",
                "mistakes": """- 完全没有 `.dockerignore`，`.venv` 与 `node_modules` 每次都传给引擎。
- 写了 `.dockerignore` 但漏了 `.env`，密钥被打进镜像层，`docker history` 也删不掉。
- `COPY . .` 放在 `RUN pip install` 之前，任何代码改动都重装依赖。
- 用 `docker build --no-cache` 当作"解决所有构建问题"的万能方法，浪费大量时间。
- 构建缓存堆积到几 GB 从不清理，磁盘告警时才排查。""",
                "error_analysis": """`failed to compute cache key: ... not found`
—— `COPY` 的源路径不存在（可能被 .dockerignore 排除了）。检查忽略规则是否误伤。

`Sending build context to Docker daemon  1.2GB` 且构建极慢
—— 缺 `.dockerignore`，或忽略规则没覆盖大目录。用 `du -sh *` 定位。

镜像里出现 `.env` 文件
—— 构建上下文包含它且 `COPY . .` 把它带进去了。加忽略规则并重建（旧层仍在，需重新构建镜像，不能只删文件）。

依赖层每次重建
—— `COPY . .` 在依赖安装之前；或 `.dockerignore` 没排除某些频繁变动的文件（如 `data/`）。""",
                "beginner_practice": """1. 给项目写 `.dockerignore`，用 `docker build` 日志里的上下文大小对比前后差异。
2. 改一行业务代码后重建，确认依赖层显示 `CACHED`，记录耗时。""",
                "advanced_practice": """把一个"每次构建都要 90 秒"的 Dockerfile 优化到 10 秒以内（仅改代码时）。
要求：(1) 写全 `.dockerignore`；(2) 重排指令顺序；(3) 用构建日志证明依赖层命中缓存。
最后说明：如果某天发现缓存"骗了自己"（用了旧的依赖），该怎么排查？""",
                "quiz_note": "本节 6 道题：2 道基础理解（.dockerignore 作用时机、缓存失效连锁）+ 2 道日志阅读（读上下文大小、读 CACHED）+ 2 道应用练习（选对指令顺序、选对清理方式）。",
                "summary": """`.dockerignore` 在传输前排除文件，同时解决速度、体积与密钥泄漏三个问题。
指令按「很少变 → 天天变」排序，依赖安装必须在源码拷贝之前。
第 N 层失效会导致其后所有层重建，所以顺序比技巧更重要。
构建上下文大小写在日志第一行，是判断配置是否生效的最快指标。""",
                "next_lesson": "单个容器已经会做了，下一章用 Compose 把前端、后端、数据库编排在一起。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-03-04",
                        "name": "构建上下文与缓存优化",
                        "goal": "能写全 .dockerignore 并按变更频率排列指令，让仅改代码时的构建命中依赖缓存。",
                        "minutes": 30,
                        "criteria": "能把仅改业务代码的构建耗时降到 10 秒以内，并用日志证明依赖层为 CACHED。",
                        "requires": ["software-engineering-deploy-03-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-03-04-1",
                        "kp": 0,
                        "title": "写出这份 .dockerignore",
                        "description": """项目根目录包含：`.git/`、`.venv/`、`node_modules/`、`frontend/.next/`、`data/xiaoma.db`、
`tests/`、`.env`、`**/__pycache__/`、`*.log`。
写出 `.dockerignore`，并说明每一项的真实目的。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''```gitignore
.git
.venv
node_modules
frontend/.next
data
tests
.env
.secret_key
__pycache__
*.pyc
*.log
*.db
```

目的分类：
- 体积与速度：`.git`（96MB 历史）、`.venv`、`node_modules`、`frontend/.next`。
- 安全：`.env`、`.secret_key`、`data`（含数据库，用户隐私）。
- 无运行时价值：`tests`、`__pycache__`、`*.pyc`、`*.log`、`*.db`。

注意 `data` 整个目录忽略比 `data/*.db` 更稳：将来新增的备份文件也不会误进镜像。''',
                        "explanation": "忽略列表要按「为什么忽略」来写，而不是照抄别人的模板。",
                    },
                    {
                        "code": "sed-ex-03-04-2",
                        "kp": 0,
                        "title": "重排 Dockerfile",
                        "description": """现有顺序导致每次改代码都重装依赖：

```dockerfile
FROM python:3.12.7-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "app.main:app"]
```

重排并解释每一层的缓存特性。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''```dockerfile
FROM python:3.12.7-slim            # 几乎不变：长期命中
WORKDIR /app                       # 几乎不变
COPY requirements.txt ./           # 偶尔变：改依赖时
RUN pip install --no-cache-dir -r requirements.txt   # 随清单变
COPY app ./app                     # 天天变：改代码时
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

缓存特性：
- 前三层稳定，日常构建全部 CACHED。
- 改业务代码只让 `COPY app` 一层重建，构建从 90 秒降到 1-2 秒。
- 改依赖时才重跑 `pip install`，这是合理的（依赖本来就变了）。

关键点：`COPY` 的粒度要小于 `RUN pip install` 的输入范围。''',
                        "explanation": "顺序优化的本质是让「高频变化的输入」尽量排在最后。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-03-04-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`.dockerignore` 相对于 `.gitignore` 的关键区别是？",
                        "options": [
                            ("A", "语法完全不同"),
                            ("B", "它在构建上下文传输前生效，被排除的文件不会发给 Docker 引擎"),
                            ("C", "它只对镜像层生效"),
                            ("D", "它可以替代 .gitignore"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这决定了它既能提速，也能防止密钥被打进镜像。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-04-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 Docker 层缓存，正确说法有？（多选）",
                        "options": [
                            ("A", "指令文本与输入文件内容一致才命中"),
                            ("B", "某层失效后，其后的层全部重建"),
                            ("C", "缓存永远不会失效"),
                            ("D", "COPY 的文件内容变化会使该层失效"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 错误；且缓存失效具有连锁性，这正是指令排序重要的原因。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-03-04-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "构建日志第一行 `Sending build context to Docker daemon  1.196GB` 意味着？",
                        "options": [
                            ("A", "最终镜像会是 1.19GB"),
                            ("B", "有 1.19GB 的项目文件被发送给 Docker 引擎，通常说明缺 .dockerignore"),
                            ("C", "磁盘剩余空间不足"),
                            ("D", "缓存已满"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "上下文大小与最终镜像大小无直接关系，但它直接决定构建开始前的等待时间。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-04-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "日志显示 `=> CACHED [4/9] RUN pip install ...`，说明？",
                        "options": [
                            ("A", "依赖安装这一步被跳过执行，直接复用上次结果"),
                            ("B", "依赖安装失败"),
                            ("C", "依赖没有安装"),
                            ("D", "Docker 正在下载依赖"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "CACHED 表示该层输入未变，复用缓存，不出现在最终耗时里。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-03-04-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "改动频率从低到高，正确的 Dockerfile 顺序是？",
                        "options": [
                            ("A", "FROM → COPY app → RUN pip install → CMD"),
                            ("B", "FROM → RUN 系统依赖 → COPY requirements → RUN pip install → COPY app → CMD"),
                            ("C", "COPY requirements → FROM → RUN pip install → CMD"),
                            ("D", "CMD → FROM → COPY app"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "FROM 必须在最前；其后按稳定性递减排列，业务代码放最后。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-03-04-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`docker build --no-cache` 应该作为解决构建异常的常规手段。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "它是排查手段而非常规手段：每次都要重装依赖，代价高。应先定位是哪一层缓存出了问题。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },

    # ==================================================================
    # 第 4 章 Docker Compose
    # ==================================================================
    {
        "code": "software-engineering-deploy-04",
        "title": "Docker Compose",
        "description": "用一个文件描述整套服务，并保证启动顺序正确。",
        "order_index": 4,
        "lessons": [
            {
                "code": "software-engineering-deploy-04-lesson-01",
                "objectives": """1. 能写出包含 frontend / backend / db 三个服务的 `docker-compose.yml`；
2. 理解 `depends_on` 只保证启动顺序，不保证服务可用；
3. 会用 `docker compose ps / logs / exec / down` 完成日常运维；
4. 知道 `container_name` 固定带来的副作用。""",
                "why_learn": """真实项目不是一个容器，而是前端、后端、数据库、缓存、Agent 服务一起协作。
用 `docker run` 逐个启动要记十几条命令与依赖顺序，换台机器就得重来。
Compose 把"整套系统"写成一个文件，一条命令拉起、一条命令停掉。""",
                "concepts": """**service**：一个可复制的容器定义，`scale` 后可以有多个实例。
**depends_on**：控制启动先后，默认**不等**健康，容器起了就继续。
**container_name**：固定容器名，会阻止同名容器被 Compose 创建（重复 `up` 时报冲突）。
**compose 项目名**：默认取目录名，同目录下所有资源归为一组，`down` 按组清理。
**声明式**：文件描述期望状态，Compose 计算差异并只做必要变更。""",
                "plain": """Compose 像一张乐谱：单独一个乐器（容器）谁都会拉，但合奏要知道谁先起、谁等谁、谁音量多大。
`depends_on` 只写"谁先上场"，不写"上场后准备好了没有"——这就是很多人遇到
"后端先于数据库就绪直接崩"的原因。
真正判断"准备好了没"要用 `healthcheck`（下一节讲）。""",
                "syntax": """```yaml
services:
  backend:
    build: ./backend
    container_name: xiaoma-backend
    environment:
      - DATABASE_URL=sqlite:////app/data/xiaoma.db
    volumes:
      - xiaoma-data:/app/data
    expose:
      - "8000"

  frontend:
    build: ./frontend
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      - BACKEND_INTERNAL_URL=http://backend:8000
    depends_on:
      - backend

volumes:
  xiaoma-data:
```

```bash
docker compose up -d --build     # 构建并后台启动
docker compose ps                # 服务状态
docker compose logs -f backend   # 跟踪日志
docker compose exec backend sh   # 进容器
docker compose down              # 停止并删除容器与网络（保留卷）
docker compose down -v           # 连卷一起删（数据会没）
```

- 顶级 `services` / `volumes` / `networks` 是 Compose v2 格式，旧版 `version:` 字段已废弃。
- `expose` 只在内部网络可见，`ports` 才映射到宿主机。""",
                "example_code": '''# docker-compose.yml
services:
  backend:
    build: ./backend
    container_name: xiaoma-backend
    env_file:
      - path: .env
        required: false
    environment:
      XIAOMA_BIND_ADDRESS: ${BIND_ADDRESS:-127.0.0.1}
    volumes:
      - xiaoma-data:/app/data
    expose:
      - "8000"
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: xiaoma-frontend
    environment:
      PORT: 3000
      HOSTNAME: 0.0.0.0
      BACKEND_INTERNAL_URL: http://backend:8000
    ports:
      - "${BIND_ADDRESS:-127.0.0.1}:${FRONTEND_PORT:-3000}:3000"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  xiaoma-data:''',
                "code_lines": """1. `services` 下每个键就是一个服务名，服务名同时是容器间访问的 DNS 名（`backend`、`frontend`）。
2. `build: ./backend` 指定构建上下文，Compose 会找该目录的 Dockerfile。
3. `env_file` 从 `.env` 加载变量；`required: false` 表示文件不存在也不报错。
4. `${BIND_ADDRESS:-127.0.0.1}` 读取宿主机环境变量，缺省绑定回环地址，默认安全。
5. `volumes` 把命名卷挂到数据目录，容器重建数据仍在。
6. `expose: 8000` 只在 Compose 网络内开放，宿主机**无法**直接访问——这是安全设计。
7. `ports` 才把端口映射出去，且默认只绑 `127.0.0.1`。
8. `depends_on: backend` 只保证 backend 容器先启动，不保证它的 uvicorn 已就绪。
9. `restart: unless-stopped` 让服务在崩溃或宿主重启后自动拉起。""",
                "output": """$ docker compose up -d --build
[+] Running 4/4
 ✔ Network xiaoma_default       Created
 ✔ Container xiaoma-backend     Started
 ✔ Container xiaoma-frontend    Started
 ✔ Volume "xiaoma_xiaoma-data"  Created

$ docker compose ps
NAME              IMAGE             STATUS                    PORTS
xiaoma-backend    xiaoma-backend    Up 12 seconds (healthy)   8000/tcp
xiaoma-frontend   xiaoma-frontend   Up 3 seconds (healthy)    127.0.0.1:3000->3000/tcp

$ docker compose logs -f backend
xiaoma-backend  | 正在执行数据库迁移...
xiaoma-backend  | 正在写入课程种子数据（幂等）...
xiaoma-backend  | INFO:     Uvicorn running on http://0.0.0.0:8000

$ docker compose down
[+] Running 3/3
 ✔ Container xiaoma-frontend  Removed
 ✔ Container xiaoma-backend   Removed
 ✔ Network xiaoma_default     Removed""",
                "mistakes": """- 以为 `depends_on` 能保证"数据库就绪"，结果后端连接被拒就直接退出。
- 给所有服务都写 `container_name`，导致无法 `scale`，也容易出现同名冲突。
- 用 `docker compose down -v` 清环境，顺手把数据库卷删了。
- 把 `ports: "8000:8000"` 加在后端上，把内部服务暴露到宿主机。
- 改了 Dockerfile 只 `docker compose up -d`（不加 `--build`），发现改动没生效。""",
                "error_analysis": """`Error response from daemon: Conflict. The container name "/xiaoma-backend" is already in use`
—— 有同名容器（可能来自另一次 `up` 或另一个工程目录）。`docker ps -a` 找到后删除，或去掉 `container_name`。

`Error: port is already allocated`
—— 宿主机端口被占。改端口或结束占用进程。

后端日志 `Connection refused` 连数据库
—— `depends_on` 只保证启动顺序，不等就绪。加 `healthcheck` + `condition: service_healthy`。

改了代码但容器行为没变
—— 忘记 `--build`，或没有重新创建容器。用 `docker compose up -d --build --force-recreate`。""",
                "beginner_practice": """1. 写一个三服务 Compose 文件（web、api、redis），用 `docker compose up -d` 启动并 `ps` 查看状态。
2. 修改一个环境变量后重启，验证 `docker compose up -d` 会重建容器并生效。""",
                "advanced_practice": """给现有 Compose 工程加一个 `restart` 策略与资源限制（`deploy.resources.limits`），
然后回答：(1) `restart: always` 与 `unless-stopped` 的行为差异？
(2) `depends_on` 的 `service_started` 与 `service_healthy` 条件有什么区别？""",
                "quiz_note": "本节 6 道题：2 道基础理解（depends_on 语义、expose 与 ports 区别）+ 2 道输出阅读（读 ps、读启动错误）+ 2 道应用练习（选对重建命令、判断容器名风险）。",
                "summary": """Compose 用一个文件描述整套服务，一条命令拉起或停掉。
`depends_on` 只管启动顺序，不管服务是否可用。
`expose` 只对内，`ports` 才对外；默认绑回环地址更安全。
`down` 保留卷、`down -v` 删卷，后者会丢数据。""",
                "next_lesson": "服务之间怎么互相找到对方、端口该不该暴露，下一节专门讲网络。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-04-01",
                        "name": "Compose 服务编排与依赖",
                        "goal": "能写出多服务 Compose 文件并用 ps/logs/exec/down 完成日常运维。",
                        "minutes": 35,
                        "criteria": "能独立编写含前后端与数据卷的 Compose 文件，并说明 depends_on 不能替代健康检查的原因。",
                        "requires": ["software-engineering-deploy-03-04"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-04-01-1",
                        "kp": 0,
                        "title": "为什么后端连不上数据库",
                        "description": """Compose 里写了：

```yaml
backend:
  depends_on:
    - db
db:
  image: postgres:16
  environment:
    POSTGRES_PASSWORD: dev
```

后端启动时报 `connection refused`。请解释原因并给出两种修复方式。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''原因：`depends_on` 只保证 `db` 容器**已启动**，不保证 PostgreSQL **可接受连接**。
Postgres 首次启动要初始化数据目录，通常需要几秒，这期间后端已经尝试连接并失败。

修复方式一（推荐，v2 语法）：
```yaml
backend:
  depends_on:
    db:
      condition: service_healthy
db:
  image: postgres:16
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 5s
    timeout: 3s
    retries: 10
```

修复方式二（应用侧兜底）：后端启动时重试连接若干次，或迁移脚本带等待逻辑。
两种可以叠加：健康检查负责编排层，重试负责应用层，双保险。''',
                        "explanation": "这是 Compose 最经典的误解，也是线上偶发启动失败的主要来源。",
                    },
                    {
                        "code": "sed-ex-04-01-2",
                        "kp": 0,
                        "title": "改代码没生效",
                        "description": """改了 `app/main.py`，执行 `docker compose up -d` 之后行为没变。列出排查步骤。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''1. 确认是否重建镜像：`up -d` 只在镜像不存在时构建，改代码需要 `--build`。
   正确命令：`docker compose up -d --build`。
2. 确认容器是否被重建：`docker compose ps` 看 CREATED 时间，若仍是旧时间说明没重建。
   必要时 `--force-recreate`。
3. 确认代码是否真的进了镜像：`docker compose exec backend cat /app/app/main.py`。
4. 若挂载了源码卷（开发模式），检查挂载路径与 volume 覆盖关系：卷会"遮住"镜像内同路径内容。''',
                        "explanation": "「改了不生效」九成是没加 --build 或容器没重建。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-04-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`depends_on` 默认能保证什么？",
                        "options": [
                            ("A", "被依赖服务已经可以接受请求"),
                            ("B", "被依赖容器已经启动，但不保证内部服务就绪"),
                            ("C", "网络一定连通"),
                            ("D", "数据已经初始化完成"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "要保证可用必须配合 `healthcheck` + `condition: service_healthy`。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "`ports` 与 `expose` 的区别，正确说法有？（多选）",
                        "options": [
                            ("A", "ports 把端口映射到宿主机"),
                            ("B", "expose 只在 Compose 内部网络可见"),
                            ("C", "两者完全等价"),
                            ("D", "后端服务通常只需 expose，由前端代理访问"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 错误：expose 不映射宿主机端口，这正是「后端不对外暴露」的实现方式。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """`docker compose ps` 显示 backend 状态为 `Up 12 seconds (healthy)`，说明？

```
xiaoma-backend  Up 12 seconds (healthy)  8000/tcp
```""",
                        "options": [
                            ("A", "容器运行中且健康检查通过"),
                            ("B", "容器已退出"),
                            ("C", "容器正在重启"),
                            ("D", "健康检查未配置"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`(healthy)` 来自 Dockerfile 或 compose 里的 HEALTHCHECK 结果。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-01-4",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": """对比 `docker compose down` 与 `docker compose down -v` 的差异，并举一个执行 `-v` 会造成不可逆后果的例子。""",
                        "answer": {"reference": "`down` 只停止并删除容器与网络；`down -v` 还会删除 compose 文件里声明的命名卷。项目里 `xiaoma-data:/app/data` 存着数据库与 `.secret_key`，删卷等于删库，且不可恢复，只能靠备份还原。", "keywords": ["命名卷", "删卷", "不可恢复", "备份"]},
                        "explanation": "`-v` 会删卷，数据库、密钥文件都在卷里，属于不可逆操作。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-01-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "改了业务代码后要让改动生效，最直接的命令是？",
                        "options": [
                            ("A", "docker compose restart"),
                            ("B", "docker compose up -d --build"),
                            ("C", "docker compose stop && start"),
                            ("D", "docker compose pull"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`restart` 只是重启现有容器，镜像不变；必须重建镜像。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-04-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "给每个服务都写死 `container_name` 是推荐做法，便于识别。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "固定容器名会阻止横向扩容，也容易与旧容器同名冲突。默认让 Compose 生成更安全。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-04-lesson-02",
                "objectives": """1. 理解 Compose 默认网络的 DNS 解析规则；
2. 能正确使用「服务名 + 容器内端口」进行跨服务访问；
3. 能判断哪些端口该映射、哪些只该 `expose`；
4. 会排查容器间"连不上"的三类原因（网络、端口、监听地址）。""",
                "why_learn": """90% 的容器互联问题都出在这里：代码里写 `127.0.0.1:8000`，容器里它指的是自己；
或者写了 `localhost:5432`，数据库在另一个容器里。
网络与端口是最容易"看起来对、跑起来错"的部分。""",
                "concepts": """**默认网络**：Compose 为每个工程创建一个 bridge 网络，所有服务自动加入。
**服务名即主机名**：`http://backend:8000` 中 `backend` 由 Docker 内置 DNS 解析到该容器 IP。
**容器内端口不是宿主端口**：容器里监听 8000，无论宿主映射成什么，容器内都用 8000 访问。
**`127.0.0.1` 在容器里指容器自身**，不是宿主机；要访问宿主机用 `host.docker.internal`（Docker Desktop）。
**监听地址**：服务必须监听 `0.0.0.0`，监听 `127.0.0.1` 会导致容器外（含同网络其他容器）连不上。""",
                "plain": """把每个容器想成一间独立的房间，房间号就是服务名。同一栋楼（Compose 网络）里的人喊房间号就能找到对方。
`127.0.0.1` 是"我自己这个房间"，所以你在 A 房间喊它，永远喊不到 B 房间。
楼外的人（宿主机上的浏览器）要进来，得先在一楼设一个门牌映射（ports）。
服务程序如果只听"房间内部广播"（127.0.0.1），隔壁房间也听不到——这就是必须监听 0.0.0.0 的原因。""",
                "syntax": """**正确的跨服务访问**

```yaml
services:
  backend:
    expose: ["8000"]           # 内部可见
  frontend:
    environment:
      BACKEND_INTERNAL_URL: http://backend:8000   # 用服务名
    ports:
      - "127.0.0.1:3000:3000"  # 只有前端对外
```

**排查三步**

```bash
docker compose exec frontend sh -c "wget -qO- http://backend:8000/api/v1/health"
docker compose exec backend sh -c "netstat -lntp | grep 8000"
docker network inspect xiaoma_default --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\\n"}}{{end}}'
```

- 第一条验证 DNS 与连通性；第二条看监听地址是不是 `0.0.0.0`；第三条看容器是否在同一网络。""",
                "example_code": '''# 场景：前端容器访问后端失败，逐步定位

# 1) 现象：前端页面提示「无法连接后端」
docker compose logs frontend --tail 20
# Error: connect ECONNREFUSED 127.0.0.1:8000

# 2) 定位：代码里写的是 127.0.0.1，容器内它指向自己
docker compose exec frontend env | grep BACKEND
# BACKEND_INTERNAL_URL=http://127.0.0.1:8000     ← 错

# 3) 修正为服务名
# docker-compose.yml
#   frontend:
#     environment:
#       BACKEND_INTERNAL_URL: http://backend:8000

# 4) 验证 DNS 解析
docker compose exec frontend sh -c "getent hosts backend"
# 172.19.0.3      backend

# 5) 验证端口连通
docker compose exec frontend sh -c "wget -qO- http://backend:8000/api/v1/health"
# {"status":"ok","version":"1.4.1"}

# 6) 若仍失败，检查后端监听地址
docker compose exec backend sh -c "netstat -lntp | grep 8000"
# tcp  0  0 0.0.0.0:8000  0.0.0.0:*  LISTEN    ← 正确
# tcp  0  0 127.0.0.1:8000 ...          LISTEN    ← 错误，只有自己可达''',
                "code_lines": """1. 日志里的 `ECONNREFUSED 127.0.0.1:8000` 已指明问题：它连的是容器自己。
2. `docker compose exec ... env` 确认容器内实际生效的配置，比看 yml 更可靠（可能有覆盖）。
3. 服务名 `backend` 由 Docker 内置 DNS 解析，不需要写 IP，也不该硬编码 IP（重建容器后 IP 会变）。
4. `getent hosts backend` 验证 DNS 是否工作——解析不到说明不在同一网络。
5. `wget`/`curl` 在容器内测试，能区分「网络不通」与「应用没响应」。
6. `netstat -lntp | grep 8000` 看监听地址：`0.0.0.0` 才对，`127.0.0.1` 就是根因。
7. 检查顺序固定为：配置值 → DNS → 端口连通 → 监听地址，一层层排除。""",
                "output": """$ docker compose exec frontend sh -c "getent hosts backend"
172.19.0.3      backend

$ docker compose exec frontend sh -c "wget -qO- http://backend:8000/api/v1/health"
{"status":"ok","service":"xiaoma-backend","version":"1.4.1"}

$ docker compose exec backend sh -c "netstat -lntp | grep 8000"
tcp        0      0 0.0.0.0:8000            0.0.0.0:*               LISTEN      1/python

$ docker network inspect xiaoma_default \\
    --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\\n"}}{{end}}'
xiaoma-backend 172.19.0.3/16
xiaoma-frontend 172.19.0.4/16

$ curl -s http://127.0.0.1:8000/api/v1/health
curl: (7) Failed to connect      # 后端未映射到宿主机，符合预期""",
                "mistakes": """- 代码里写 `localhost` 或 `127.0.0.1` 访问同网络其他服务。
- 把容器内端口写成宿主映射端口（如宿主 30080 → 容器 8000，却用 30080 互访）。
- 后端 `uvicorn --host 127.0.0.1`，导致前端容器连不上。
- 用容器 IP 直连，重建容器后 IP 变化，全部失效。
- 为了让前端能访问，把后端 `ports` 暴露到 `0.0.0.0:8000`，直接把内部服务开到公网。""",
                "error_analysis": """`ECONNREFUSED 127.0.0.1:8000`
—— 地址写成了自己。改为服务名。

`getaddrinfo ENOTFOUND backend`
—— 服务名解析失败：服务不在同一网络，或服务名拼错（区分大小写与连字符）。

`Connection reset by peer` / 连上即断
—— 端口通了但应用崩了或协议不对（比如用 HTTP 访问 HTTPS 端口）。看后端日志。

宿主机 `curl 127.0.0.1:8000` 失败但容器间正常
—— 后端只写了 `expose`，没有 `ports`。这是预期行为，应通过前端代理访问。""",
                "beginner_practice": """1. 在 `frontend` 容器内用 `wget` 访问 `backend` 的 `/health`，再用 `getent hosts` 确认 DNS。
2. 故意把 `BACKEND_INTERNAL_URL` 改成 `127.0.0.1:8000`，复现错误并说明原因。""",
                "advanced_practice": """为三个服务（frontend、backend、worker）设计网络：要求 backend 与 worker 可互通，
frontend 只能访问 backend，且外部只能访问 frontend。
写出 Compose 的 `networks` 配置，并用 `docker network inspect` 验证隔离生效。""",
                "quiz_note": "本节 6 道题：2 道基础理解（服务名解析、容器内端口语义）+ 2 条排查阅读（读 ECONNREFUSED、读 netstat）+ 2 道应用练习（选对连接地址、判断端口暴露策略）。",
                "summary": """同网络内用「服务名:容器内端口」互访，不用 IP、不用 localhost。
容器内 `127.0.0.1` 指自己，跨容器访问必然失败。
服务必须监听 `0.0.0.0`，否则同网络其他容器也连不上。
排查顺序固定：配置值 → DNS → 端口 → 监听地址。""",
                "next_lesson": "数据要怎么留在容器之外？下一节讲卷与绑定挂载的取舍。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-04-02",
                        "name": "Compose 网络与端口",
                        "goal": "能用服务名完成容器间访问，正确区分 expose 与 ports，并独立排查连接失败。",
                        "minutes": 30,
                        "criteria": "能定位并修复一次 ECONNREFUSED 故障，说明监听地址与端口映射各自的作用。",
                        "requires": ["software-engineering-deploy-04-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-04-02-1",
                        "kp": 0,
                        "title": "改对连接地址",
                        "description": """后端监听 `0.0.0.0:8000`，只写 `expose`；前端在自己容器内要调用它。
下面四种写法哪些能用、哪些会失败？为什么？

(1) `http://127.0.0.1:8000`
(2) `http://localhost:8000`
(3) `http://backend:8000`
(4) `http://宿主机IP:8000`""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''(1) 失败：容器内 127.0.0.1 是自己，自己没在 8000 监听。
(2) 失败：同 (1)，localhost 解析到容器自身回环。
(3) 成功：服务名由 Compose 内置 DNS 解析，且后端监听 0.0.0.0。
(4) 失败：后端只有 expose，没有 ports，宿主机上没有 8000 映射；即使有映射，走宿主机再绕回容器也不必要。

结论：容器间互访统一用「服务名:容器内端口」。''',
                        "explanation": "这四种写法的对比能一次性建立正确的网络直觉。",
                    },
                    {
                        "code": "sed-ex-04-02-2",
                        "kp": 0,
                        "title": "设计端口暴露方案",
                        "description": """系统含 frontend(3000)、backend(8000)、postgres(5432)、redis(6379)。
要求：外部只能访问 frontend；backend 只能被 frontend 访问；数据库与缓存不被任何外部访问。
写出 ports/expose 配置并说明理由。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''```yaml
services:
  frontend:
    ports: ["127.0.0.1:3000:3000"]   # 唯一对外
  backend:
    expose: ["8000"]                 # 仅内部
  postgres:
    expose: ["5432"]
  redis:
    expose: ["6379"]
```

理由：
- 只有浏览器需要访问的才用 ports，且绑定 127.0.0.1（需要局域网/公网时再改，并加访问密码）。
- backend 由 frontend 在同网络内以服务名访问，无需宿主映射。
- 数据库与缓存只在内部网络，减少攻击面；调试时可临时 `docker compose exec postgres psql`。
- 若确实需要本地用客户端连数据库，加 `ports: ["127.0.0.1:5432:5432"]` 并明确这只是开发便利。''',
                        "explanation": "「默认不暴露」是最省事的安全策略，需要时再显式打开。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-04-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "在 Compose 网络中，容器 A 要访问容器 B 的 8000 端口，应使用？",
                        "options": [
                            ("A", "http://127.0.0.1:8000"),
                            ("B", "http://localhost:8000"),
                            ("C", "http://<B 的服务名>:8000"),
                            ("D", "http://宿主机IP:8000"),
                        ],
                        "answer": {"value": "C"},
                        "explanation": "服务名由内置 DNS 解析，且容器内端口就是服务实际监听端口。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "容器间连不上，可能的原因有？（多选）",
                        "options": [
                            ("A", "代码里写了 127.0.0.1"),
                            ("B", "服务监听在 127.0.0.1 而不是 0.0.0.0"),
                            ("C", "两个服务不在同一网络"),
                            ("D", "宿主机没映射端口"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 只影响宿主机访问，不影响容器间互通。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """日志出现如下错误，最先该改什么？

```
Error: connect ECONNREFUSED 127.0.0.1:8000
```""",
                        "options": [
                            ("A", "把地址改成服务名 backend"),
                            ("B", "重启 Docker"),
                            ("C", "增加内存"),
                            ("D", "改数据库密码"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`ECONNREFUSED` + `127.0.0.1` 几乎是容器间互访写错地址的固定组合。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """`netstat` 输出中，下面哪种监听方式会导致同网络其他容器连不上？

```
A: tcp 0 0 0.0.0.0:8000     0.0.0.0:*     LISTEN
B: tcp 0 0 127.0.0.1:8000   0.0.0.0:*     LISTEN
```""",
                        "options": [
                            ("A", "A"),
                            ("B", "B"),
                            ("C", "两者都会"),
                            ("D", "两者都不会"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "监听 127.0.0.1 只接受本机回环连接，其他容器访问不到。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让后端只能被内部访问、不被宿主机直接访问，应写？",
                        "options": [
                            ("A", "ports: [\"8000:8000\"]"),
                            ("B", "expose: [\"8000\"]"),
                            ("C", "network_mode: host"),
                            ("D", "ports: [\"0.0.0.0:8000:8000\"]"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`expose` 只在 Compose 网络内开放，不产生宿主机映射。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-04-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "容器间访问应写容器 IP 而不是服务名，因为 IP 更直接。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "IP 在容器重建后会变；服务名由 DNS 动态解析，是唯一稳定写法。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-04-lesson-03",
                "objectives": """1. 能区分命名卷、绑定挂载、tmpfs 三种方式；
2. 能判断什么数据该放卷、什么该用绑定挂载；
3. 会备份、恢复、清理卷，并知道 `down -v` 的后果；
4. 理解卷权限问题（容器内 UID 与宿主 UID 的差异）。""",
                "why_learn": """容器是易失的，数据必须活在容器之外。
但"挂出来"有三种方式，选错的后果差别很大：用绑定挂载跑数据库，Windows 上会遇到权限与性能问题；
用卷存源码做开发，改代码不会热更新。
这一节把"什么数据放哪里"讲清楚。""",
                "concepts": """**命名卷 volume**：由 Docker 管理，位于 `/var/lib/docker/volumes`，跨平台一致，适合数据库与用户数据。
**绑定挂载 bind mount**：直接映射宿主机路径，适合开发时热更新源码、传配置文件。
**tmpfs**：内存文件系统，容器停止即消失，适合临时缓存与敏感中间数据。
**匿名卷**：`VOLUME /app/data` 未指定名字时自动创建的乱码名卷，难以管理，建议显式命名。
**权限**：容器内以 UID 10001 运行时，绑定挂载的宿主目录若属主不同会 permission denied。""",
                "plain": """命名卷像公司的档案室：位置你不用管，公司负责保管与搬迁，跨机器也能带走（通过导出）。
绑定挂载像直接把你的桌面文件夹接过去：改文件立刻生效，方便，但换台电脑路径就没了。
tmpfs 像白板：写得快，擦得也快，容器一停就空。
判断规则：**生产数据用卷，开发源码用绑定挂载，临时敏感数据用 tmpfs**。""",
                "syntax": """```yaml
services:
  backend:
    volumes:
      - xiaoma-data:/app/data                    # 命名卷（生产数据）
      - ./backend/app:/app/app:ro                # 绑定挂载（开发热更新，只读）
      - /tmp/xiaoma:/tmp/xiaoma                  # 绑定挂载（宿主绝对路径）
    tmpfs:
      - /run/cache                               # 内存盘

volumes:
  xiaoma-data:            # 显式声明，便于备份与清理
```

```bash
docker volume ls                                # 列出卷
docker volume inspect xiaoma-data               # 查看挂载点
docker compose exec backend ls -la /app/data    # 验证挂载生效
docker run --rm -v xiaoma-data:/data -v "$PWD":/backup alpine \\
  tar czf /backup/data-backup.tar.gz -C /data .
```

- 卷名会被加上工程前缀：`xiaoma_xiaoma-data`。
- 备份卷的标准做法：起一个临时容器，把卷与宿主目录同时挂进去打包。""",
                "example_code": '''# docker-compose.yml
services:
  backend:
    build: ./backend
    volumes:
      # 生产数据：命名卷，跨平台一致
      - xiaoma-data:/app/data

  frontend:
    build: ./frontend

# 开发专用：docker-compose.override.yml（Compose 自动叠加）
# 只在本地生效，不进生产
services:
  backend:
    volumes:
      - ./backend/app:/app/app:ro      # 源码热更新，只读防止容器写回
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

volumes:
  xiaoma-data:''',
                "code_lines": """1. `xiaoma-data:/app/data` 是命名卷：Docker 管理实际路径，重建容器数据仍在。
2. 卷必须出现在顶级 `volumes:` 里显式声明（Compose v2 会校验）。
3. `docker-compose.override.yml` 是 Compose 的官方分层机制：`up` 时自动与主文件合并。
4. 开发叠加层用绑定挂载把源码映进容器，配合 `--reload` 实现热更新。
5. `:ro` 只读：容器不能改宿主源码，降低"容器内改了就以为改了仓库"的误操作。
6. 生产环境不加载 override 文件，因此不会有源码挂载与 `--reload`。
7. `volumes:` 顶层声明放在最后，与 services 同级，缺了会报 `undefined volume`。""",
                "output": """$ docker compose up -d
$ docker compose exec backend ls -la /app/data
total 1016
drwxr-xr-x 2 appuser appuser    4096 Nov  9 22:40 .
-rw-r--r-- 1 appuser appuser 1015808 Nov  9 22:41 xiaoma.db
-rw------- 1 appuser appuser      44 Nov  9 22:40 .secret_key

$ docker volume ls | grep xiaoma
local     xiaoma_xiaoma-data

$ docker volume inspect xiaoma_xiaoma-data --format '{{.Mountpoint}}'
/var/lib/docker/volumes/xiaoma_xiaoma-data/_data

# 备份卷
$ docker run --rm -v xiaoma_xiaoma-data:/data -v "$PWD":/backup alpine \\
    tar czf /backup/data-20261109.tar.gz -C /data .
$ ls -lh data-20261109.tar.gz
-rw-r--r-- 1 root root 412K Nov  9 22:42 data-20261109.tar.gz

# 危险操作
$ docker compose down -v
[+] Running 2/2
 ✔ Volume xiaoma_xiaoma-data  Removed     ← 数据没了""",
                "mistakes": """- 用绑定挂载跑数据库，Windows 上遇到文件锁与权限问题，Linux 上遇到 UID 不匹配。
- 开发时把源码挂载目录设成可写，容器内改了代码但仓库没变，最后找不到改动去哪了。
- 用 `docker compose down -v` 清环境，把数据库卷一起删掉。
- 忘记在顶级 `volumes:` 声明，报 `service refers to undefined volume`。
- 把 `.secret_key` 放在容器内非挂载路径，重建后密钥变化，已保存的 API Key 全部无法解密。""",
                "error_analysis": """`service "backend" refers to undefined volume xiaoma-data`
—— 顶级 `volumes:` 里没声明该卷。

`PermissionError: [Errno 13] Permission denied: '/app/data/xiaoma.db'`
—— 容器内用户 UID 与挂载目录属主不一致。三种解法：调整宿主目录属主、用命名卷、或在 Dockerfile 里对齐 UID。

`database is locked`（SQLite）
—— 绑定挂载在部分平台的文件锁语义不同，或同时有两个容器访问同一文件。改用命名卷并保证单实例写入。

改了卷里的数据但容器看不到
—— 挂载路径被镜像内同路径内容遮住顺序搞反，或改的是另一个容器的卷（工程前缀不同）。""",
                "beginner_practice": """1. 给后端挂一个命名卷到 `/app/data`，写入一个文件后重建容器，验证文件仍在。
2. 用临时 alpine 容器把该卷打包成 tar.gz 到宿主目录，再解压确认内容。""",
                "advanced_practice": """搭建开发/生产两套挂载配置：`docker-compose.yml` 用卷与正式启动命令，
`docker-compose.override.yml` 用绑定挂载与 `--reload`。
验收：(1) 开发时改代码立即生效；(2) 生产配置不含源码挂载；
(3) 说明为什么不能用 `down -v` 来"重置开发环境"。""",
                "quiz_note": "本节 6 道题：2 道基础理解（卷与绑定挂载区别、tmpfs 用途）+ 2 道输出阅读（读挂载结果、读权限错误）+ 2 道应用练习（选对存储方式、判断 down -v 风险）。",
                "summary": """生产数据用命名卷，开发源码用绑定挂载，临时数据用 tmpfs。
卷跨平台一致、好备份；绑定挂载快、路径与宿主强耦合。
`down -v` 会删卷，是不可逆操作，执行前确认已备份。
挂载权限问题的根源是 UID 不一致，用命名卷可规避大部分。""",
                "next_lesson": "有了卷和网络，最后一个问题是「谁先就绪」——下一节用健康检查把启动顺序做对。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-04-03",
                        "name": "卷、绑定挂载与数据持久化",
                        "goal": "能按数据类型选择持久化方式，并完成卷的备份与恢复。",
                        "minutes": 35,
                        "criteria": "能说明命名卷与绑定挂载的取舍，并独立完成一次卷备份与解压验证。",
                        "requires": ["software-engineering-deploy-04-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-04-03-1",
                        "kp": 0,
                        "title": "给四类数据选存储方式",
                        "description": """分别选择命名卷 / 绑定挂载 / tmpfs，并说明理由：
(1) SQLite 数据库文件
(2) 开发时的 Python 源码
(3) Nginx 的配置文件
(4) 单次请求的临时上传缓存""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''(1) 命名卷：需要跨容器重建持久化，且跨平台一致；绑定挂载在 Windows 上有文件锁与权限问题。
(2) 绑定挂载：开发时要热更新，改宿主文件立即生效；生产不打这个挂载。
(3) 绑定挂载（只读 :ro）：配置需要版本控制与人工编辑，映射宿主文件最直观；
    也可以构建进镜像，改动时重建。
(4) tmpfs：只在处理期间存在，容器停即消失，且不落盘更安全。

判断口诀：要持久 + 跨平台 → 卷；要热更新 / 人工编辑 → 绑定挂载；只要临时 → tmpfs。''',
                        "explanation": "选错存储方式会带来权限、性能、数据丢失等连锁问题。",
                    },
                    {
                        "code": "sed-ex-04-03-2",
                        "kp": 0,
                        "title": "备份一个卷",
                        "description": """把命名卷 `xiaoma_xiaoma-data` 备份成宿主当前目录下的 `data-backup.tar.gz`，
并给出恢复命令。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''备份：
```bash
docker run --rm \\
  -v xiaoma_xiaoma-data:/data \\
  -v "$PWD":/backup \\
  alpine tar czf /backup/data-backup.tar.gz -C /data .
```

恢复（先停服务避免写入）：
```bash
docker compose stop backend
docker run --rm \\
  -v xiaoma_xiaoma-data:/data \\
  -v "$PWD":/backup \\
  alpine sh -c "rm -rf /data/* && tar xzf /backup/data-backup.tar.gz -C /data"
docker compose start backend
```

要点：用临时容器同时挂卷与宿主目录；恢复前清空目标目录，否则旧文件会残留。''',
                        "explanation": "这是卷备份的标准手法，不依赖容器内是否装了 tar。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-04-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "生产环境的数据库文件最适合放在？",
                        "options": [
                            ("A", "容器内未挂载的目录"),
                            ("B", "命名卷"),
                            ("C", "tmpfs"),
                            ("D", "镜像里"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "命名卷跨平台一致、可备份、不随容器销毁；镜像内数据每次重建都会回到初始状态。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于绑定挂载，正确说法有？（多选）",
                        "options": [
                            ("A", "映射宿主真实路径，改文件立即生效"),
                            ("B", "适合开发时热更新"),
                            ("C", "跨平台行为完全一致"),
                            ("D", "可能有 UID 与权限问题"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 错误：Windows 与 Linux 在文件锁、权限、性能上差异明显。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """`docker compose exec backend ls -la /app/data` 输出如下，能推出什么？

```
-rw-r--r-- 1 appuser appuser 1015808 Nov 9 22:41 xiaoma.db
-rw------- 1 appuser appuser      44 Nov 9 22:40 .secret_key
```""",
                        "options": [
                            ("A", "数据目录挂载成功，且与容器运行用户 UID 一致"),
                            ("B", "挂载失败，文件在容器可写层"),
                            ("C", "文件属于 root，后续会写入失败"),
                            ("D", "卷是只读的"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "属主是 appuser（容器内用户），说明挂载生效且权限对齐。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "报错 `PermissionError: Permission denied: '/app/data/xiaoma.db'`，最可能原因是？",
                        "options": [
                            ("A", "容器内用户 UID 与挂载目录属主不一致"),
                            ("B", "磁盘满了"),
                            ("C", "SQLite 版本过低"),
                            ("D", "端口被占用"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "绑定挂载到宿主目录时最常遇到；改用命名卷或对齐 UID 可解决。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要显式声明命名卷 `xiaoma-data`，Compose 文件里应写在哪？",
                        "options": [
                            ("A", "services 下的 volumes"),
                            ("B", "与 services 同级的顶级 volumes"),
                            ("C", "networks 下"),
                            ("D", "任意位置均可"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "服务内只写挂载关系，卷本身必须在顶级 `volumes:` 声明。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-04-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`docker compose down -v` 只删除容器与网络，不影响数据卷。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "`-v` 正是用来删除卷的，数据库与密钥文件会一并消失，属于不可逆操作。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-04-lesson-04",
                "objectives": """1. 能给服务配置 `healthcheck` 并读懂 healthy / unhealthy 状态；
2. 能用 `depends_on` 的 `condition: service_healthy` 保证真实就绪；
3. 能解释 `start_period` 在首次启动中的作用；
4. 会设计一条能真实反映业务可用性的健康检查。""",
                "why_learn": """「容器起来了」不等于「服务能用了」。
后端要跑迁移、加载种子、连接数据库，这些都可能要几十秒。
如果前端在它之前启动，用户会看到 502；如果自动化脚本在它之前调用接口，会得到连接被拒。
健康检查是让编排"等到真的能用"的唯一手段。""",
                "concepts": """**healthcheck**：容器内定期执行探测命令，结果分为 starting / healthy / unhealthy。
**三个关键参数**：`interval` 间隔、`timeout` 单次超时、`retries` 连续失败次数。
**start_period**：首次启动的宽限期，期间失败不计入 retries——这是长启动服务的救命参数。
**condition 语义**：`service_started`（容器起了）、`service_healthy`（健康检查通过）、`service_completed_successfully`（一次性任务成功退出）。
**健康检查要测"业务可用"**：只测进程存在没意义，要测关键依赖（数据库、关键接口）。""",
                "plain": """健康检查像餐厅的"可以点菜了吗"：灯亮只说明店门开了（容器启动），
要问一句"厨师准备好了吗"才知道能不能点（服务可用）。
`start_period` 是给新店开业的缓冲期：刚开门那几分钟手忙脚乱不算失误。
`condition: service_healthy` 就是让客人在得到"可以点菜"答复后才进门店，而不是看到灯亮就冲进去。""",
                "syntax": """```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"]
      interval: 15s        # 每 15 秒探一次
      timeout: 5s          # 单次超过 5 秒算失败
      retries: 5           # 连续失败 5 次标记 unhealthy
      start_period: 90s    # 前 90 秒的失败不计入 retries

  frontend:
    depends_on:
      backend:
        condition: service_healthy

  migrate:
    depends_on:
      db:
        condition: service_healthy
```

```bash
docker compose ps                       # STATUS 里能看到 (healthy)
docker inspect --format '{{json .State.Health}}' xiaoma-backend
docker compose up --wait                # 等到全部 healthy 才返回
```

- `CMD` 形式不经过 shell，避免引号与转义问题；需要管道时用 `CMD-SHELL`。
- `up --wait` 适合脚本与 CI，失败会返回非零码。""",
                "example_code": '''# docker-compose.yml 节选：三段式启动顺序
services:
  backend:
    build: ./backend
    volumes:
      - xiaoma-data:/app/data
    # 后端要跑迁移 + 种子，首次启动可能需要 60-90 秒
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 90s

  frontend:
    build: ./frontend
    environment:
      BACKEND_INTERNAL_URL: http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
    # 前端的健康检查走同源代理，顺带验证了「代理 → 后端」整条链路
    healthcheck:
      test:
        - CMD
        - node
        - -e
        - "fetch('http://127.0.0.1:3000/api/v1/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s''',
                "code_lines": """1. 后端的 `start_period: 90s` 是必需的：迁移与种子在前 90 秒内可能一直失败，不应判死。
2. `interval: 15s` 与 `retries: 5` 组合意味着最坏情况下约 75 秒后标记 unhealthy（不含 start_period）。
3. `test` 用 `CMD` 数组形式，避免 shell 引号问题；单引号包住内层字符串。
4. 探测的是真实的 `/api/v1/health`，而不是 `ps` 看进程——进程活着不代表接口可用。
5. 前端 `depends_on` 用 `condition: service_healthy`，保证后端真的能响应后才启动。
6. 前端的健康检查刻意走 `/api/v1/health`（同源代理）：它同时验证了前端自身与后端链路。
7. 如果前端的健康检查只测首页 HTML，后端挂了它仍然 healthy——健康检查要测真正关键的依赖。""",
                "output": """$ docker compose up -d
[+] Running 3/3
 ✔ Container xiaoma-backend   Healthy    28.4s
 ✔ Container xiaoma-frontend  Started

$ docker compose ps
NAME              STATUS                    PORTS
xiaoma-backend    Up 2 minutes (healthy)    8000/tcp
xiaoma-frontend   Up 1 minute (healthy)     127.0.0.1:3000->3000/tcp

$ docker inspect --format '{{json .State.Health}}' xiaoma-backend | head -c 300
{"Status":"healthy","FailingStreak":0,"Log":[{"Start":"2026-11-09T14:41:02Z","End":"...","ExitCode":0,"Output":""}]}

# 启动阶段的样子
$ docker compose ps
NAME              STATUS
xiaoma-backend    Up 12 seconds (health: starting)
xiaoma-frontend   Created

# 后端挂掉之后
$ docker compose ps
NAME              STATUS
xiaoma-backend    Up 5 minutes (unhealthy)""",
                "mistakes": """- `depends_on` 不写 condition，以为等价于健康检查。
- 把 `start_period` 设成 0 或很短，长迁移的服务被误判 unhealthy 而反复重启。
- 健康检查探测 `/` 首页而不是业务健康接口，后端挂了仍然 healthy。
- `test` 用 `CMD-SHELL` 并塞复杂引号，命令解析失败导致永远 unhealthy。
- 健康检查里做重操作（如查全表），每 15 秒给数据库加一次压力。""",
                "error_analysis": """`dependency failed to start: container xiaoma-backend is unhealthy`
—— 依赖的服务健康检查没通过。`docker inspect .State.Health.Log` 看失败原因。

状态长时间停在 `(health: starting)`
—— 探测一直失败但还在 `start_period` 内。检查命令是否真的能在容器里跑通：
`docker compose exec backend python -c "..."`。

`(unhealthy)` 但服务其实能用
—— 探测命令本身有问题（路径、端口、依赖缺失），或 `retries` 太少。

健康检查通过但接口 502
—— 探测的路径与应用实际路径不一致（如探了 `/health` 而应用只有 `/api/v1/health`）。""",
                "beginner_practice": """1. 给后端加 healthcheck，用 `docker compose ps` 观察从 `health: starting` 到 `healthy` 的过程。
2. 把 `start_period` 改成 5 秒，观察是否被误判 unhealthy，再改回来。""",
                "advanced_practice": """设计一套三段式启动：db（healthy）→ migrate（一次性任务，completed_successfully）→ backend（healthy）→ frontend。
写出完整的 Compose 配置并验证顺序，说明 `service_completed_successfully` 与 `service_started` 的区别。""",
                "quiz_note": "本节 6 道题：2 道基础理解（healthcheck 作用、start_period 语义）+ 2 道输出阅读（读 ps 状态、读 unhealthy 日志）+ 2 道应用练习（选对 condition、判断健康检查设计）。",
                "summary": """健康检查让编排知道"服务真的能用"，而不只是"进程还活着"。
`start_period` 给长启动服务留缓冲，期间失败不计入 retries。
`condition: service_healthy` 是保证启动顺序正确的关键写法。
健康检查要探测关键业务路径，不要探测无关页面或做重操作。""",
                "next_lesson": "编排搞定后，环境差异怎么处理？下一章讲配置与密钥的分离。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-04-04",
                        "name": "健康检查与启动顺序",
                        "goal": "能配置真实反映业务可用性的 healthcheck，并用 service_healthy 保证启动顺序。",
                        "minutes": 40,
                        "criteria": "能给出含 start_period 与 condition 的完整配置，并解释为何健康检查要探测业务接口而非进程。",
                        "requires": ["software-engineering-deploy-04-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-04-04-1",
                        "kp": 0,
                        "title": "为什么一直 unhealthy",
                        "description": """配置如下，容器状态一直是 `(health: starting)`，日志里没有明显错误。

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://127.0.0.1:8000/health"]
  interval: 5s
  timeout: 2s
  retries: 3
```

后端实际接口是 `/api/v1/health`，且镜像里没有装 curl。指出两处问题。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''1. 路径错：实际是 `/api/v1/health`，探测 `/health` 返回 404，`curl -f` 因此非零退出。
2. 镜像里没有 curl：`python:3.12-slim` 不带 curl，命令直接 `executable file not found`，
   每次探测都失败。这也解释了为什么容器状态只有 starting 而没有报错日志——
   失败信息在 `.State.Health.Log` 里，不在应用日志里。

修正：
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"]
  interval: 15s
  timeout: 5s
  retries: 5
  start_period: 90s
```

排查技巧：`docker inspect --format '{{json .State.Health.Log}}' 容器名` 能看到每次探测的输出。''',
                        "explanation": "健康检查失败不会写进应用日志，必须查 Health.Log，这是最容易被忽略的排查点。",
                    },
                    {
                        "code": "sed-ex-04-04-2",
                        "kp": 0,
                        "title": "设计三段式启动",
                        "description": """要求：db 就绪 → 执行迁移 → 后端启动 → 前端启动。
写出依赖配置片段（只需 depends_on 与 condition 部分）。""",
                        "type": "coding",
                        "difficulty": "advanced",
                        "answer": '''```yaml
services:
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 10

  migrate:
    build: ./backend
    command: ["python", "-m", "app.cli", "init-db"]
    depends_on:
      db:
        condition: service_healthy
    restart: "no"

  backend:
    build: ./backend
    depends_on:
      migrate:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 90s

  frontend:
    build: ./frontend
    depends_on:
      backend:
        condition: service_healthy
```

要点：迁移是一次性任务，用 `service_completed_successfully` 而不是 `service_started`——
否则迁移还没跑完后端就起来了。`restart: "no"` 避免迁移失败后无限重试。''',
                        "explanation": "一次性任务与常驻服务的依赖语义不同，混用会导致启动竞态。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-04-04-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`start_period` 的作用是？",
                        "options": [
                            ("A", "首次启动的宽限期，期间探测失败不计入 retries"),
                            ("B", "健康检查的间隔时间"),
                            ("C", "容器启动前的延迟"),
                            ("D", "重启次数上限"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "长迁移、大种子数据的服务必须靠它，否则会被误判 unhealthy 而反复重启。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-04-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于健康检查设计，正确做法有？（多选）",
                        "options": [
                            ("A", "探测真实业务健康接口"),
                            ("B", "在探测命令里做全表扫描以确认数据库可用"),
                            ("C", "为启动缓慢的服务设置合理 start_period"),
                            ("D", "让前端健康检查经代理访问后端，覆盖整条链路"),
                        ],
                        "answer": {"values": ["A", "C", "D"]},
                        "explanation": "B 会给数据库持续加压，健康检查必须轻量。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-04-04-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`docker compose ps` 显示 `Up 12 seconds (health: starting)`，说明？",
                        "options": [
                            ("A", "容器已退出"),
                            ("B", "容器运行中，健康检查尚在初始宽限/探测阶段"),
                            ("C", "健康检查未配置"),
                            ("D", "容器被标记为 unhealthy"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "starting 表示还没判定，通常在 start_period 内或探测次数不足。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-04-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "报错 `dependency failed to start: container xiaoma-backend is unhealthy`，第一步应做什么？",
                        "options": [
                            ("A", "重启 Docker"),
                            ("B", "查看 `docker inspect --format '{{json .State.Health}}' xiaoma-backend` 的探测日志"),
                            ("C", "删除数据卷"),
                            ("D", "改端口"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "健康检查失败的原因不在应用日志里，必须看 Health.Log 才能看到每次探测的输出与退出码。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-04-04-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让前端在后端**健康**后才启动，`depends_on` 应写成？",
                        "options": [
                            ("A", "depends_on: [backend]"),
                            ("B", "depends_on: {backend: {condition: service_healthy}}"),
                            ("C", "depends_on: {backend: {condition: service_started}}"),
                            ("D", "links: [backend]"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "只有 `service_healthy` 会等待健康检查通过，其余都只等容器创建/启动。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-04-04-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "健康检查探测 `/` 首页就可以了，只要能返回 200 就说明后端可用。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "静态首页可能由前端自身返回；后端挂掉也照样 200。必须探测真正依赖后端的接口。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
