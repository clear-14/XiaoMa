"""软件工程与项目部署：第 5—6 章（配置与密钥、部署与发布）。"""

CHAPTERS: list[dict] = [
    # ==================================================================
    # 第 5 章 配置与密钥
    # ==================================================================
    {
        "code": "software-engineering-deploy-05",
        "title": "配置与密钥",
        "description": "同一份镜像，靠配置适配不同环境。",
        "order_index": 5,
        "lessons": [
            {
                "code": "software-engineering-deploy-05-lesson-01",
                "objectives": """1. 能列出项目里哪些属于「配置」、哪些必须硬编码；
2. 理解 12-Factor 中「配置存于环境」的实际含义；
3. 能把硬编码的数据库地址、密钥、开关改成环境变量；
4. 知道配置校验缺失会导致什么样的线上事故。""",
                "why_learn": """同一份代码要跑在开发机、测试环境、生产服务器上，它们的数据库地址、日志级别、外部服务 Key 都不同。
如果把这些写死在代码里，每次部署都要改代码、重新构建、还得小心别把生产密码提交上去。
配置外置是为了让**同一个镜像在任何环境都能跑**。""",
                "concepts": """**配置的定义**：随部署环境变化的值。数据库 URL、密钥、端口、外部服务地址、功能开关。
**不是配置的东西**：代码里的算法、路由路径、常量表——这些不随环境变。
**12-Factor 第 3 条**：配置存于环境（环境变量），而不是代码里的常量文件。
**优先级链**：环境变量 > 配置文件 > 代码默认值，越靠前优先级越高。
**启动即校验**：缺失关键配置应在启动时立刻失败，而不是等第一个请求进来才报错。""",
                "plain": """把配置想成家里的水电接口：房子（镜像）是一样的，接哪家的水电（环境变量）由入住时决定。
如果装修时就把水管焊死在墙上（硬编码），换房子就得砸墙重装。
判断标准很简单：这个值换一台机器会不会变？会变就是配置，不会变就是代码。
密钥也是配置的一种，但它比普通配置更敏感——所以还要额外一层加密与轮换（下一节讲）。""",
                "syntax": """```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "xiaoma-backend"
    database_url: str = "sqlite:///./data/xiaoma.db"
    log_level: str = "INFO"
    access_password: str | None = None
    llm_api_key: str | None = None

settings = Settings()
```

- 字段名大写即环境变量名（`DATABASE_URL` 对应 `database_url`）。
- 有默认值的字段可缺省；无默认值的字段缺失会启动失败——这正是"启动即校验"。
- `extra="ignore"` 避免 `.env` 里多余变量导致报错。""",
                "example_code": '''# app/config.py：启动即校验 + 敏感值脱敏
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "xiaoma-backend"
    version: str = "1.4.1"

    database_url: str = "sqlite:///./data/xiaoma.db"
    log_level: str = "INFO"

    # 需要开放局域网/公网时必填，本机访问可留空
    bind_address: str = "127.0.0.1"
    access_password: SecretStr | None = None

    # 模型服务密钥：只允许从环境变量注入
    llm_api_key: SecretStr | None = None
    llm_base_url: str | None = None

    @field_validator("log_level")
    @classmethod
    def _check_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL 必须是 {sorted(allowed)} 之一")
        return upper

    @property
    def is_remote(self) -> bool:
        return self.bind_address not in {"127.0.0.1", "localhost", "::1"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()''',
                "code_lines": """1. `BaseSettings` 会自动从环境变量与 `.env` 读取，字段名不区分大小写。
2. `SecretStr` 让密钥在日志、`repr` 里显示为 `**********`，只能显式 `.get_secret_value()` 取出。
3. `access_password` 与 `llm_api_key` 默认 `None`：本机开发可以不配，但使用时会校验。
4. `field_validator` 在启动时就拦住非法值——`LOG_LEVEL=verbose` 会让进程直接起不来。
5. `is_remote` 把"是否对外开放"的判断集中在一处，启动保护逻辑复用它。
6. `lru_cache` 保证整个进程只解析一次配置，避免每次请求都读文件。
7. 这个文件里没有任何密钥字面量，`grep -r "sk-" app/` 应该永远为空。""",
                "output": """$ python -c "from app.config import settings; print(settings)"
app_name='xiaoma-backend' version='1.4.1' database_url='sqlite:///./data/xiaoma.db'
log_level='INFO' bind_address='127.0.0.1' access_password=None llm_api_key=None

$ LLM_API_KEY=sk-abcdef123456 python -c "from app.config import settings; print(settings.llm_api_key)"
**********                                  # SecretStr 自动脱敏

$ LOG_LEVEL=verbose python -c "from app.config import settings"
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
log_level
  Value error, LOG_LEVEL 必须是 ['DEBUG', 'ERROR', 'INFO', 'WARNING'] 之一

$ BIND_ADDRESS=0.0.0.0 XIAOMA_ALLOW_REMOTE=false ./entrypoint.sh
错误：BIND_ADDRESS=0.0.0.0 需要同时设置 XIAOMA_ALLOW_REMOTE=true
拒绝以无保护方式启动。""",
                "mistakes": """- 把 `DATABASE_URL` 写死在代码里，部署到生产还要改代码。
- 密钥通过 `print(settings)` 打进日志，`SecretStr` 没用在密钥字段上。
- 缺配置时不报错，等用户点开页面才 500，排查成本从 1 分钟变成 1 小时。
- 一个 `.env` 文件同时装开发与生产配置，改一处忘另一处。
- 把配置默认值设成"生产可用"的值（如默认绑定 0.0.0.0），安全默认值被破坏。""",
                "error_analysis": """`pydantic_core.ValidationError: 1 validation error for Settings`
—— 某个必填配置缺失或格式不对。错误信息里会明确指出字段名。

`KeyError: 'LLM_API_KEY'` 在请求处理时才出现
—— 配置不是在启动时校验的。把字段改成无默认值的必填项，或在使用前显式检查。

`SecretStr` 打印出来是 `**********`，但接口返回了明文
—— 序列化时调用了 `.get_secret_value()`，且没有做脱敏。响应模型里也只暴露后四位。

`env_file` 没生效
—— 工作目录不对，或变量已存在于环境中（环境变量优先级高于 .env）。""",
                "beginner_practice": """1. 把项目里三处硬编码（数据库地址、端口、日志级别）改成 `Settings` 字段，用环境变量覆盖验证。
2. 制造一个非法 `LOG_LEVEL`，确认启动直接失败并给出可读错误。""",
                "advanced_practice": """为项目设计完整配置清单：把每个字段分类为「必填 / 有安全默认值 / 敏感」，
并写出启动校验逻辑（含绑定地址与访问密码的联动规则）。
完成后回答：为什么"默认绑定 127.0.0.1"比"默认绑定 0.0.0.0"更合适？""",
                "quiz_note": "本节 6 道题：2 道基础理解（配置定义、12-Factor 原则）+ 2 道代码阅读（读 Settings 输出、读校验报错）+ 2 道应用练习（选对默认值、判断哪些该外置）。",
                "summary": """配置是随环境变化的值，代码是算法与结构，两者要分开。
12-Factor 要求配置存于环境，让同一镜像适配所有环境。
缺配置要在启动时失败，而不是留到第一个请求。
敏感字段用 `SecretStr`，默认值要选"不安全环境也不出事"的那一侧。""",
                "next_lesson": "配置能注入了，但 dev 与 prod 的差异清单怎么维护？下一节讲多环境管理。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-05-01",
                        "name": "12-Factor 配置外置",
                        "goal": "能区分配置与代码，把硬编码值改成启动即校验的环境变量配置。",
                        "minutes": 30,
                        "criteria": "能列出项目的配置清单并完成外置改造，且故意缺配置时进程启动即失败并给出可读错误。",
                        "requires": ["software-engineering-deploy-04-04"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-05-01-1",
                        "kp": 0,
                        "title": "分拣：哪些是配置",
                        "description": """把下列八项分成「配置」与「代码」两类，并说明判断依据。
(1) 数据库连接地址 (2) HTTP 状态码常量 (3) 大模型 API Key (4) 路由路径 /api/v1/tasks
(5) 日志级别 (6) 分页默认每页 20 条 (7) 是否开放注册的开关 (8) 密码哈希算法""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''配置（随环境/运营变化）：
(1) 数据库地址 —— 开发用本地文件，生产用独立实例。
(3) API Key —— 每个环境、每个用户都不同。
(5) 日志级别 —— 开发 DEBUG，生产 INFO。
(7) 功能开关 —— 运营策略，可能随时调整。
(6) 分页默认值 —— 边界情况：技术上可硬编码，但常需要按数据量调整，建议做成配置。

代码（不随环境变）：
(2) 状态码常量 —— HTTP 协议规定，永远不变。
(4) 路由路径 —— 属于接口契约，改它等于改 API 版本。
(8) 密码哈希算法 —— 属于安全实现，不能由环境随意改动（否则同一密码在不同环境产生不同结果）。

判断依据一句话：换一台机器部署时，这个值会不会变？''',
                        "explanation": """把不该外置的东西外置，会造成"配置地狱"——同一份代码在不同环境行为不一致。""",
                    },
                    {
                        "code": "sed-ex-05-01-2",
                        "kp": 0,
                        "title": "补上启动校验",
                        "description": """现有配置类缺少校验，导致 `BIND_ADDRESS=0.0.0.0` 但没设密码时服务裸奔启动。
写出启动时的校验逻辑。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''```python
# app/config.py 中的模型校验
from pydantic import model_validator

class Settings(BaseSettings):
    ...

    @model_validator(mode="after")
    def _guard_remote_access(self) -> "Settings":
        if self.is_remote and self.access_password is None:
            raise ValueError(
                f"BIND_ADDRESS={self.bind_address} 将服务开放到本机之外，"
                "必须设置 XIAOMA_ACCESS_PASSWORD"
            )
        return self
```

要点：
1. 校验放在配置层，任何入口（uvicorn、CLI、测试）都会经过它；
2. 错误信息要写清"改哪个变量"，而不是只说"配置错误"；
3. 用 `model_validator(mode="after")` 才能同时访问多个字段。''',
                        "explanation": "把安全规则写进配置校验，比写在启动脚本里更难被绕过。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-05-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "12-Factor 中「配置存于环境」的核心目的是？",
                        "options": [
                            ("A", "让代码更短"),
                            ("B", "让同一份构建产物能在不同环境运行，无需改代码重建"),
                            ("C", "提高程序运行速度"),
                            ("D", "减少依赖数量"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "构建一次、处处运行，是容器化与持续交付的前提。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-05-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些属于应外置的配置？（多选）",
                        "options": [
                            ("A", "数据库连接地址"),
                            ("B", "HTTP 状态码常量"),
                            ("C", "日志级别"),
                            ("D", "第三方服务密钥"),
                        ],
                        "answer": {"values": ["A", "C", "D"]},
                        "explanation": "B 是协议规定，永远不变，外置只会增加出错可能。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-05-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`print(settings)` 输出里 `llm_api_key=None`，设置环境变量后输出 `**********`，这说明？",
                        "options": [
                            ("A", "密钥丢失了"),
                            ("B", "字段使用了 SecretStr，打印时自动脱敏"),
                            ("C", "配置读取失败"),
                            ("D", "环境变量没生效"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "SecretStr 的 `repr` 固定输出 `**********`，需要显式 `.get_secret_value()` 才拿到明文。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-05-01-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": """启动时报错：

```
ValidationError: 1 validation error for Settings
log_level
  Value error, LOG_LEVEL 必须是 ['DEBUG', 'ERROR', 'INFO', 'WARNING'] 之一
```

这说明什么？""",
                        "options": [
                            ("A", "配置校验生效，进程在启动阶段就拒绝了非法值"),
                            ("B", "日志模块损坏"),
                            ("C", "端口冲突"),
                            ("D", "数据库连接失败"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "这正是「启动即校验」的价值：错误在部署时暴露，而不是运行时。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-05-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": """某配置字段存 API Key，要求打印与写日志都不出现明文。写出字段的类型声明，并说明真正调用模型时怎样取到明文。""",
                        "answer": {"reference": "声明为 `api_key: SecretStr`；调用时用 `settings.api_key.get_secret_value()` 取明文，直接打印对象或写日志只会得到 `**********`。", "keywords": ["SecretStr", "get_secret_value", "明文"]},
                        "explanation": "`SecretStr` 的 `repr` 与日志输出都是 `**********`，降低误泄漏风险。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-05-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "配置默认值应尽量选择「即使在配置缺失时也不会造成安全问题」的那一侧。",
                        "options": None,
                        "answer": {"value": True},
                        "explanation": "例如默认绑定 127.0.0.1、默认关闭调试。安全默认值能兜住配置疏漏。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-05-lesson-02",
                "objectives": """1. 能维护一份「开发 / 生产」差异清单，避免配置漂移；
2. 会用 `.env` + `.env.example` 的组合管理变量；
3. 理解 Compose 的 `.env`、`env_file`、`environment` 三者的优先级；
4. 能识别并修复配置漂移导致的"只在生产复现"问题。""",
                "why_learn": """「本地没问题，线上有问题」八成是配置漂移：某个变量在生产写错了、漏了，或者多环境共用了一份配置。
配置漂移不会报错，它只是让行为悄悄不同——这类问题最难查。
把差异显式化、把必填项集中声明，是最省事的预防手段。""",
                "concepts": """**`.env.example`**：进版本库的模板，只写变量名与示例值，不含真实密钥。
**`.env`**：本地实际值，进 `.gitignore`，永不提交。
**优先级**：`docker compose run -e` > `environment` > `env_file` > 宿主机 shell 环境。
**差异清单**：用一张表列出每个变量在 dev / prod 的取值与是否必填。
**配置漂移**：环境间某个变量取值或存在性不一致，导致行为不同且无报错。""",
                "plain": """`.env.example` 是"购物清单"，告诉大家需要买哪些菜；`.env` 是"实际买回来的菜"，各家不同。
清单进仓库，实际值不进——这样别人 clone 下来知道要配什么，又拿不到你的密码。
优先级像点菜时的临时要求：命令行 `-e` 是"这顿不要香菜"，会盖过菜单（environment）和默认配菜（env_file）。
差异清单就是那张"哪些菜只有晚餐才有"的对照表，缺了它，晚班的人只能靠猜。""",
                "syntax": """**`.env.example`（进仓库）**

```bash
# 访问范围：本机开发保持 127.0.0.1；对外开放必须同时设置密码
BIND_ADDRESS=127.0.0.1
FRONTEND_PORT=3000

# 访问密码：开放局域网/公网时必填，留空表示不启用
# XIAOMA_ACCESS_PASSWORD=

# 数据库：本地默认 data/xiaoma.db
# DATABASE_URL=sqlite:///./data/xiaoma.db

# 模型密钥：仅从环境变量注入，不写入代码
# XIAOMA_SECRET_KEY=
```

**`.gitignore`**

```gitignore
.env
backend/.env
*.db
.secret_key
```

**Compose 优先级示例**

```yaml
services:
  backend:
    env_file: [.env]
    environment:
      LOG_LEVEL: INFO        # 覆盖 .env 里的同名变量
```

- 注释掉的行 = "通常不需要改的变量"，写出来是为了让人知道它存在。
- `environment` 优先于 `env_file`，容易造成"改了 .env 不生效"的困惑。""",
                "example_code": '''# 场景：生产环境日志级别错，导致磁盘被写满

# 1) 现象：生产磁盘一周内涨了 40GB
docker compose exec backend du -sh /app/data/logs
# 38G    /app/data/logs

# 2) 定位：生产用的是 DEBUG 级别
docker compose exec backend env | grep LOG_LEVEL
# LOG_LEVEL=DEBUG

# 3) 查根因：.env 是照抄开发环境的，没改过
grep LOG_LEVEL .env
# LOG_LEVEL=DEBUG

# 4) 修复：在 compose 里显式声明生产值（优先级高于 env_file）
# docker-compose.yml
#   backend:
#     environment:
#       LOG_LEVEL: ${LOG_LEVEL:-INFO}

# 5) 但更根本的做法是维护差异清单，部署前逐项核对
cat > docs/环境变量清单.md <<'EOF'
| 变量 | 开发 | 生产 | 必填 | 说明 |
|---|---|---|---|---|
| BIND_ADDRESS | 127.0.0.1 | 0.0.0.0 | 是 | 对外必须配密码 |
| LOG_LEVEL | DEBUG | INFO | 是 | DEBUG 会写满磁盘 |
| XIAOMA_ACCESS_PASSWORD | 空 | 强密码 | 对外时必填 | 不写日志 |
| DATABASE_URL | sqlite:///./data/xiaoma.db | 同左 | 否 | 换库时改这里 |
EOF

# 6) 验收
docker compose up -d
docker compose exec backend env | grep LOG_LEVEL
# LOG_LEVEL=INFO''',
                "code_lines": """1. 先量化问题：`du -sh` 定位到日志目录异常增长。
2. `env` 看容器内**实际生效**的值，这比看 `.env` 可靠——可能有覆盖或多层文件。
3. 根因是 `.env` 直接照抄开发环境，`DEBUG` 级别把每次请求的完整内容都写进日志。
4. `environment: LOG_LEVEL: ${LOG_LEVEL:-INFO}` 给出安全缺省：没配也不会退化成 DEBUG。
5. 差异清单是最高性价比的防漂移手段：部署前逐项核对，比出事后再查快十倍。
6. 清单里「必填」一列尤其重要，它对应启动校验要拦的字段。
7. 验收要看容器内实际值，而不是"我改了 .env 应该生效了吧"。""",
                "output": """$ docker compose exec backend env | grep -E "LOG_LEVEL|BIND_ADDRESS"
LOG_LEVEL=DEBUG
BIND_ADDRESS=0.0.0.0

$ docker compose exec backend du -sh /app/data/logs
38G     /app/data/logs

# 修正后
$ docker compose up -d
$ docker compose exec backend env | grep LOG_LEVEL
LOG_LEVEL=INFO

$ docker compose exec backend du -sh /app/data/logs
412M    /app/data/logs      # 历史文件仍在，需要另行清理

$ git status --short .env
# 无输出，说明 .env 已被忽略，不会误提交""",
                "mistakes": """- `.env` 被提交到仓库，密钥泄漏（尤其公开仓库，几分钟内就会被扫到）。
- 只维护 `.env` 不维护 `.env.example`，新人不知道要配哪些变量。
- `environment` 与 `env_file` 同时存在同名变量，改了 `.env` 却发现不生效。
- 开发与生产共用一份 `.env`，日志级别、调试开关一路带到线上。
- 用 `.env.example` 里填真实值当"方便"，模板从此变成泄漏源。""",
                "error_analysis": """改了 `.env` 但容器内值没变
—— `environment` 里有同名变量，优先级更高；或没重建容器（`up -d` 才会重新读取）。

`WARN[0000] The "X" variable is not set. Defaulting to a blank string.`
—— `.env` 里没这个变量但 compose 引用了 `${X}`。加默认值 `${X:-默认}` 或补进 `.env`。

新人 clone 后启动失败，报缺配置
—— 没有 `.env.example`，或模板里没写全必需变量。

生产行为与开发不同但无报错
—— 典型的配置漂移。逐项对比 `docker compose exec backend env` 的输出。""",
                "beginner_practice": """1. 为项目生成 `.env.example`，把真实 `.env` 加入 `.gitignore`，用 `git status` 确认不会被提交。
2. 用 `docker compose exec backend env` 导出实际生效变量，与 `.env` 对比找出差异。""",
                "advanced_practice": """制作一份「环境变量差异清单」表（变量、开发值、生产值、是否必填、说明），
并为「必填」项写启动校验。验收：删掉一个必填变量后服务启动即失败，且错误信息指出变量名。""",
                "quiz_note": "本节 6 道题：2 道基础理解（.env 与 .env.example 分工、优先级）+ 2 道输出阅读（读 env 输出、读 compose 警告）+ 2 道应用练习（选对忽略策略、判断漂移原因）。",
                "summary": """`.env.example` 进仓库当模板，`.env` 进忽略列表存真实值。
优先级是 `-e` > `environment` > `env_file` > shell 环境，改不生效先查这条链。
差异清单把"只在生产复现"的问题变成部署前就能核对的表格。
判断实际生效值永远看容器内 `env`，不看文件。""",
                "next_lesson": "配置分好类了，密钥还需要额外一层：加密、轮换与吊销。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-05-02",
                        "name": "多环境配置与差异清单",
                        "goal": "能用 .env + .env.example 管理变量，维护差异清单并识别配置漂移。",
                        "minutes": 30,
                        "criteria": "能产出含开发/生产值与必填标记的差异清单，并能通过容器内 env 输出定位一次配置漂移。",
                        "requires": ["software-engineering-deploy-05-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-05-02-1",
                        "kp": 0,
                        "title": "为什么改了 .env 不生效",
                        "description": """Compose 文件：

```yaml
backend:
  env_file: [.env]
  environment:
    LOG_LEVEL: DEBUG
```

`.env` 里写的是 `LOG_LEVEL=INFO`，但容器内实际是 `DEBUG`。解释原因并给出修复。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''原因：`environment` 的优先级高于 `env_file`，同名变量被前者覆盖。
写在 `environment` 里的 `LOG_LEVEL: DEBUG` 直接生效，`.env` 里的值被忽略。

修复方式（按推荐度）：
1. 删掉 `environment` 里的硬编码，只保留 `env_file`，让 `.env` 唯一来源；
2. 保留覆盖但改为引用变量：`LOG_LEVEL: ${LOG_LEVEL:-INFO}`，既能被 `.env` 覆盖又有安全默认；
3. 若确实需要固定值，就不要在 `.env` 里保留同名项，避免误导。

排查习惯：`docker compose config` 可以打印合并后的最终配置，一眼看出谁赢了。''',
                        "explanation": "`docker compose config` 是排查优先级问题最快的工具，比逐个文件比对可靠。",
                    },
                    {
                        "code": "sed-ex-05-02-2",
                        "kp": 0,
                        "title": "写差异清单",
                        "description": """为下列五个变量制作差异清单（开发值、生产值、是否必填、说明）：
BIND_ADDRESS、FRONTEND_PORT、LOG_LEVEL、XIAOMA_ACCESS_PASSWORD、DATABASE_URL""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''| 变量 | 开发 | 生产 | 必填 | 说明 |
|---|---|---|---|---|
| BIND_ADDRESS | 127.0.0.1 | 0.0.0.0 | 是 | 非回环时必须同时设密码与允许远程 |
| FRONTEND_PORT | 3000 | 3000 或 80 | 否 | 被占用时改这里 |
| LOG_LEVEL | DEBUG | INFO | 是 | DEBUG 会快速写满磁盘 |
| XIAOMA_ACCESS_PASSWORD | 空 | 强密码 | 对外时必填 | 不写日志、不返回前端 |
| DATABASE_URL | sqlite:///./data/xiaoma.db | 同左 | 否 | 换 PostgreSQL 时改这里 |

清单的价值在于「必填」列：它直接对应启动校验要拦的字段，
部署前逐项打勾，比上线后回滚便宜得多。''',
                        "explanation": "差异清单不用复杂工具，一张表加启动校验就能挡住大部分漂移。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-05-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`.env` 与 `.env.example` 的正确分工是？",
                        "options": [
                            ("A", "两者都提交，方便新人使用"),
                            ("B", ".env.example 提交当模板，.env 本地实际值且不提交"),
                            ("C", "只保留 .env，不需要 example"),
                            ("D", ".env 提交，.env.example 忽略"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "模板进仓库让人知道要配什么，真实值不进仓库避免泄漏。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-05-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "关于 Compose 变量优先级，正确说法有？（多选）",
                        "options": [
                            ("A", "environment 优先于 env_file"),
                            ("B", "命令行 -e 优先级最高"),
                            ("C", "env_file 优先于 environment"),
                            ("D", "同名变量会出现覆盖，容易导致改了不生效"),
                        ],
                        "answer": {"values": ["A", "B", "D"]},
                        "explanation": "C 反了。理解这条链能解释绝大多数「改了配置没反应」。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-05-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`docker compose exec backend env | grep LOG_LEVEL` 输出 `LOG_LEVEL=DEBUG`，但 `.env` 里是 INFO。最可能原因？",
                        "options": [
                            ("A", "容器没重启"),
                            ("B", "compose 的 environment 里有同名覆盖"),
                            ("C", "环境变量名拼错"),
                            ("D", "Docker 有 bug"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "也可能是容器未重建，但若已 `up -d` 仍如此，优先查 environment 覆盖。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-05-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`WARN[0000] The \"XIAOMA_ACCESS_PASSWORD\" variable is not set. Defaulting to a blank string.` 说明？",
                        "options": [
                            ("A", "compose 引用了该变量但环境中不存在，按空值处理"),
                            ("B", "密码太简单"),
                            ("C", "容器启动失败"),
                            ("D", "数据库不可用"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "空密码在对外开放时会被启动校验拦住，但在本机可能悄悄不启用鉴权，所以要显式设默认值。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-05-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让 `LOG_LEVEL` 可被 .env 覆盖、缺失时默认 INFO，compose 里应写？",
                        "options": [
                            ("A", "LOG_LEVEL: DEBUG"),
                            ("B", "LOG_LEVEL: ${LOG_LEVEL:-INFO}"),
                            ("C", "LOG_LEVEL: env"),
                            ("D", "LOG_LEVEL: null"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`${VAR:-默认}` 提供安全缺省，同时保留被外部覆盖的能力。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-05-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "开发与生产使用同一份 `.env` 可以避免配置不一致，是推荐做法。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "共用会让调试开关、DEBUG 日志一路带到生产，是配置漂移的主要来源。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-05-lesson-03",
                "objectives": """1. 能判断一个密钥"可以放哪里、绝不能放哪里"；
2. 会给密钥做静态加密存储，并在接口与日志中脱敏；
3. 能设计一次密钥轮换流程，包含过渡期与回滚方案；
4. 知道密钥泄漏后的应急步骤（吊销优先于清理痕迹）。""",
                "why_learn": """密钥泄漏的后果不是"多花点钱"，而是数据被拖走、账号被接管、账单失控。
而泄漏往往不是被黑，是自己交出去的：提交进 Git、打进镜像、写进日志、贴进工单。
密钥管理要解决三件事：**存得安全、用得可控、换得干净**。""",
                "concepts": """**四不原则**：不进代码、不进镜像、不进日志、不进工单/聊天。
**加密存储**：数据库里存密文（如 Fernet），解密密钥单独存放（环境变量或独立文件）。
**脱敏展示**：接口只返回 `sk-****abcd`（后四位），完整值永不回传前端。
**轮换**：新密钥上线 → 双密钥并存过渡 → 旧密钥吊销。
**吊销优先**：确认泄漏后第一动作是吊销，不是删日志；痕迹是证据，密钥才是风险。""",
                "plain": """密钥像家门钥匙。你不会把钥匙插在门上（进代码），不会把钥匙的照片贴在门上（进日志），
也不会在换锁后还留着旧钥匙能用（不吊销）。
加密存储是"把钥匙放进保险箱"，保险箱本身也有密码——那个密码必须在环境变量里，不在仓库里。
轮换就是换锁：新钥匙先发给家人，确认都能进，再让旧钥匙彻底失效。
如果钥匙丢过，第一件事是换锁，而不是先擦掉门口的可疑脚印。""",
                "syntax": """```python
# 加密存储
from cryptography.fernet import Fernet

key = Fernet.generate_key()              # 44 字节，保存在 data/.secret_key 或环境变量
fernet = Fernet(key)

cipher = fernet.encrypt(b"sk-real-key")  # 入库的密文
plain = fernet.decrypt(cipher).decode()  # 使用时解密

# 脱敏
def mask(key: str) -> str:
    return f"{key[:3]}****{key[-4:]}" if len(key) > 8 else "****"
```

```bash
# 轮换示意
# 1) 新增新密钥（旧密钥保留可用）
# 2) 观察一段时间，确认新请求都走新密钥
# 3) 吊销旧密钥
```

- Fernet 密钥换了，已存的密文就解不开了：**密钥本身必须一起备份**。
- 脱敏函数要能处理短字符串，否则 `key[-4:]` 会把整串暴露。""",
                "example_code": '''# app/services/secret_store.py：加密保存 + 脱敏返回
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretStore:
    """把模型 API Key 以 Fernet 密文存库，对外只给脱敏值。"""

    def __init__(self, key_file: Path) -> None:
        self.key_file = key_file
        self._fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        env_key = os.environ.get("XIAOMA_SECRET_KEY")
        if env_key:
            # 口令字符串经 SHA-256 派生为 44 字节 base64 密钥
            import base64
            import hashlib

            digest = hashlib.sha256(env_key.encode("utf-8")).digest()
            return base64.urlsafe_b64encode(digest)

        if self.key_file.exists():
            return self.key_file.read_bytes()

        key = Fernet.generate_key()
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file.write_bytes(key)
        self.key_file.chmod(0o600)
        return key

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode("utf-8")).decode("ascii")

    def decrypt(self, cipher: str) -> str:
        try:
            return self._fernet.decrypt(cipher.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError(
                "无法解密已保存的密钥：加密密钥可能已更换，请在设置页重新填写 API Key"
            ) from exc


def mask_key(plain: str) -> str:
    """只暴露前 3 位与后 4 位，用于接口与界面展示。"""
    if len(plain) <= 8:
        return "****"
    return f"{plain[:3]}****{plain[-4:]}"''',
                "code_lines": """1. 加密密钥优先取环境变量，其次读独立文件，都没有才生成——保证容器重建后仍能解密。
2. `chmod(0o600)` 限制密钥文件只有属主可读写。
3. `encrypt` 返回 ASCII 字符串，方便存进 VARCHAR/TEXT 列。
4. `decrypt` 捕获 `InvalidToken` 并转成可读中文提示：密钥换了，让用户重填。
5. `mask_key` 对短密钥直接返回 `****`，避免"脱敏"反而暴露全部内容。
6. 该类不提供"返回完整明文"的公开方法——只有真正需要调用的地方才解密。
7. 接口层只返回 `mask_key(...)` 的结果，完整值永不经过 HTTP 响应。""",
                "output": """# 首次启动自动生成密钥
$ ls -la backend/data/.secret_key
-rw------- 1 appuser appuser 44 Nov  9 22:40 .secret_key

# 入库的是密文
>>> store.encrypt("sk-1234567890abcdef")
'gAAAAABq7svu...（约 100 字符密文）'

# 接口返回脱敏值
$ curl -s http://127.0.0.1:3000/api/v1/model-configs
[{"name":"DeepSeek 默认","provider":"deepseek","model_name":"deepseek-chat","api_key":"sk-****cdef","is_default":true}]

# 换了加密密钥之后
$ XIAOMA_SECRET_KEY=another-value uvicorn app.main:app
ValueError: 无法解密已保存的密钥：加密密钥可能已更换，请在设置页重新填写 API Key

$ grep -rn "sk-" backend/app/ | wc -l
0                                        # 代码里没有任何密钥字面量""",
                "mistakes": """- 把 `.secret_key` 放在容器非挂载路径，重建后密钥变化，所有 API Key 无法解密。
- 接口返回完整 Key"方便调试"，前端 localStorage 里存着明文密钥。
- 日志里 `logger.info("calling with key=%s", api_key)`，日志文件成了泄漏源。
- 更换加密密钥前没备份旧密钥，导致存量密文永久失效。
- 怀疑泄漏后先删日志再吊销密钥，把取证材料毁了还留着风险窗口。""",
                "error_analysis": """`InvalidToken` / `无法解密已保存的密钥`
—— 加密密钥变了：可能是 `.secret_key` 没挂载导致重建后重新生成，或手动改了 `XIAOMA_SECRET_KEY`。
处理：恢复原密钥文件；确实无法恢复时，让用户重新填写 API Key。

`cryptography.fernet.InvalidToken` 偶发出现
—— 多实例部署时各自生成了不同的 `.secret_key`。必须让所有实例共用同一个密钥。

日志里出现完整密钥
—— 检查是否有 `%s` 直接打印配置对象，或异常堆栈携带了请求体。

接口返回 `api_key: null` 但模型能用
—— 说明查询时只取了密文没解密，或脱敏函数返回空。检查序列化层。""",
                "beginner_practice": """1. 给一个配置字段加上 `SecretStr`，分别在 `print`、日志、接口响应中确认不出现明文。
2. 实现 `mask_key`，验证 `sk-1234567890abcdef` 返回 `sk-****cdef`，且短字符串返回 `****`。""",
                "advanced_practice": """设计一次完整的密钥轮换：写清步骤（新增、并存、观察、吊销）、
需要监控的信号（新旧密钥调用比例）、以及失败时的回滚方式。
再回答：如果发现密钥已经泄漏到公开仓库，前三个动作分别是什么？""",
                "quiz_note": "本节 6 道题：2 道基础理解（四不原则、吊销优先）+ 2 道代码阅读（读脱敏输出、读 InvalidToken）+ 2 道应用练习（选对存储位置、判断轮换步骤）。",
                "summary": """密钥不进代码、镜像、日志、工单，这四条是底线。
加密存储时，解密密钥必须与密文分开且一起备份。
接口只返回脱敏值，脱敏函数要处理短字符串。
泄漏后的第一动作是吊销，不是清理痕迹。""",
                "next_lesson": "配置与密钥都稳了，下一章把服务真正发布出去：反向代理与 HTTPS。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-05-03",
                        "name": "密钥加密存储与轮换",
                        "goal": "能加密保存密钥并在接口与日志中脱敏，能按并存过渡的方式完成一次轮换。",
                        "minutes": 35,
                        "criteria": "能实现加密存储与脱敏返回，并写出含过渡期与吊销步骤的轮换方案。",
                        "requires": ["software-engineering-deploy-05-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-05-03-1",
                        "kp": 0,
                        "title": "找出三处泄漏",
                        "description": """下列代码有三处密钥泄漏风险，指出并修正。

```python
API_KEY = "sk-1234567890abcdef"

logger.info(f"调用模型，key={API_KEY}")

@app.get("/config")
def read_config():
    return {"api_key": API_KEY}
```""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''1. 硬编码密钥：`API_KEY = "sk-..."` 会进仓库历史，即使后来删掉也能被检出。
   改为 `settings.llm_api_key`（从环境变量读取，类型 `SecretStr | None`）。

2. 日志泄漏：`logger.info(f"...key={API_KEY}")` 把完整密钥写进日志文件。
   改为只记指纹：`logger.info("调用模型，key=%s", mask_key(key))`，或干脆不记。

3. 接口泄漏：`/config` 返回完整密钥，前端会存进 localStorage、浏览器插件可读。
   改为返回 `{"api_key": mask_key(key)}`，完整值永不出后端。

补充：若密钥已进过 Git 历史，必须吊销并重新生成——删文件不等于删除历史。''',
                        "explanation": "三处泄漏对应三个最常见场景：仓库、日志、接口。",
                    },
                    {
                        "code": "sed-ex-05-03-2",
                        "kp": 0,
                        "title": "写轮换方案",
                        "description": """线上正在使用密钥 A，需要换成密钥 B。写出轮换步骤，并说明为什么不能直接替换。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''步骤：
1. 在服务商后台创建密钥 B，**保留 A 可用**；
2. 把 B 写入配置（支持多密钥的按优先级排列；不支持的先灰度部分实例）；
3. 观察指标：新密钥调用成功率、配额消耗、错误码分布；
4. 确认 B 稳定后，吊销 A；
5. 记录轮换时间与操作人，更新差异清单。

不能直接替换的原因：
- 替换瞬间所有实例同时切换，若 B 配额不足或权限不同，会立即全线故障；
- 已排队/重试中的请求可能仍持 A，直接吊销会导致这批请求失败；
- 没有过渡期就无法区分"是 B 有问题"还是"网络问题"。

核心原则：**先让新密钥生效并验证，再让旧密钥失效**，中间留可观测的过渡窗口。''',
                        "explanation": """轮换的风险不在换，而在"同时失去两把钥匙"的瞬间。""",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-05-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "发现 API Key 泄漏到公开仓库，第一个动作应该是？",
                        "options": [
                            ("A", "删除仓库里的文件"),
                            ("B", "立即吊销该密钥"),
                            ("C", "清理日志"),
                            ("D", "通知用户改密码"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "删文件无法删除 Git 历史与他人克隆；只有吊销能真正止损。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-05-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些位置绝对不能出现真实密钥？（多选）",
                        "options": [
                            ("A", "源码与 Git 历史"),
                            ("B", "镜像层"),
                            ("C", "日志文件"),
                            ("D", "环境变量"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "环境变量是密钥的正确注入方式；其余三处都会留下可被读取的副本。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-05-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "接口返回 `\"api_key\": \"sk-****cdef\"`，说明？",
                        "options": [
                            ("A", "密钥被截断了，实际不可用"),
                            ("B", "返回的是脱敏值，真实密钥仍在后端"),
                            ("C", "密钥已失效"),
                            ("D", "前端会拿到完整密钥"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "脱敏只影响展示，完整值不出后端；这也是为什么接口不能返回使用中的完整 Key。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-05-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "报错 `无法解密已保存的密钥：加密密钥可能已更换`，最可能的原因是？",
                        "options": [
                            ("A", "数据库损坏"),
                            ("B", ".secret_key 未持久化，容器重建后重新生成"),
                            ("C", "网络超时"),
                            ("D", "密钥格式错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "这是容器化部署里最常见的密钥事故：数据卷没覆盖密钥文件路径。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-05-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "把 `sk-1234567890abcdef` 脱敏成前 3 后 4 的形式，结果是？",
                        "options": [
                            ("A", "sk-****cdef"),
                            ("B", "sk-1234****abcdef"),
                            ("C", "****"),
                            ("D", "sk-1234567890abcdef"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`f\"{key[:3]}****{key[-4:]}\"` 得 `sk-****cdef`，足以辨认是哪个 Key 而不泄漏内容。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-05-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "密钥轮换时应该先把旧密钥吊销，再启用新密钥，这样过渡最干净。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "顺序反了会造成服务中断窗口。正确顺序是新密钥生效并验证，再吊销旧密钥。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },

    # ==================================================================
    # 第 6 章 部署与发布
    # ==================================================================
    {
        "code": "software-engineering-deploy-06",
        "title": "部署与发布",
        "description": "从单机部署到可回滚的发布流程。",
        "order_index": 6,
        "lessons": [
            {
                "code": "software-engineering-deploy-06-lesson-01",
                "objectives": """1. 能画出「浏览器 → Nginx → 前端 → 后端」的请求路径；
2. 能写出转发前后端与流式接口的 Nginx 配置；
3. 会为 SSE / 长请求设置正确的超时与缓冲参数；
4. 能通过日志判断请求卡在哪一跳。""",
                "why_learn": """开发时前端直连后端很方便，上线后必须有统一入口：域名、端口、HTTPS、静态资源、限流都在这一层。
反向代理配错的典型症状是"页面能开但接口 502"，或者"流式回复一次性吐出来"——都能从这一层找到原因。""",
                "concepts": """**反向代理**：外部只访问 Nginx，由它按路径把请求转给内部服务。
**路径路由**：`/` 转前端，`/api/` 转后端，`/api/v1/chat/stream` 需要特殊处理。
**proxy_pass 结尾斜杠**：`proxy_pass http://backend;` 与 `proxy_pass http://backend/;` 的路径拼接结果不同。
**流式响应**：必须关闭 `proxy_buffering`，否则 SSE 会被 Nginx 攒着一次性发出。
**超时三件套**：`proxy_connect_timeout`、`proxy_read_timeout`、`proxy_send_timeout`。""",
                "plain": """Nginx 像大楼前台：访客只找前台，前台根据你要办的事指到不同楼层。
请求路径就是"办什么事"——看页面去 3 楼（前端），调接口去 5 楼（后端）。
`proxy_buffering` 像前台帮你攒快递：普通包裹攒一批送更高效，但"实时播报"（流式回复）被攒着就变成"延迟一次性播报"。
超时设置是"等多久算对方不在"：设太短长任务被掐断，设太长故障迟迟不暴露。""",
                "syntax": """```nginx
server {
    listen 80;
    server_name xiaoma.example.com;

    # 前端
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 后端 API
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 180s;
    }

    # 流式对话：关闭缓冲
    location /api/v1/chat/ {
        proxy_pass http://backend:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

- `X-Forwarded-*` 让后端能拿到真实客户端 IP 与协议。
- 流式接口必须单独 location，否则会被全局配置的缓冲影响。""",
                "example_code": '''# nginx.conf：小码的前后端与流式接口
upstream frontend_upstream {
    server frontend:3000;
    keepalive 32;
}

upstream backend_upstream {
    server backend:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    # 静态资源长缓存
    location /_next/static/ {
        proxy_pass http://frontend_upstream;
        proxy_cache_valid 200 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
    }

    # 流式对话：必须关闭缓冲，超时要够长
    location /api/v1/chat/ {
        proxy_pass http://backend_upstream;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;

        proxy_connect_timeout 10s;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }

    # 普通 API
    location /api/ {
        proxy_pass http://backend_upstream;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        proxy_connect_timeout 5s;
        proxy_read_timeout 180s;
    }

    # 前端其余路径
    location / {
        proxy_pass http://frontend_upstream;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}''',
                "code_lines": """1. `upstream` + `keepalive` 复用与上游的连接，减少每次请求的握手开销。
2. `client_max_body_size 20m` 限制上传体积，防止大文件打满内存。
3. `/_next/static/` 单独处理并加长缓存：哈希文件名内容不变，可放心缓存 30 天。
4. 流式 location 放在普通 `/api/` **之前**：Nginx 按最长前缀匹配，但同长度时先定义的生效，显式分开更安全。
5. `proxy_buffering off` 是流式能"一个字一个字出来"的关键；不关就会攒到最后一次性推送。
6. `proxy_http_version 1.1` + 空 `Connection` 头配合 keepalive，否则 SSE 在部分场景会被断开。
7. 普通接口 `read_timeout 180s`、流式 `600s`：区分对待，避免全局设成 600s 导致故障迟迟不暴露。
8. `X-Forwarded-For` 让后端日志能记录真实来源 IP。""",
                "output": """$ curl -I https://xiaoma.example.com/
HTTP/2 200
server: nginx/1.27.3
cache-control: public, max-age=2592000, immutable

$ curl -s https://xiaoma.example.com/api/v1/health
{"status":"ok","service":"xiaoma-backend","version":"1.4.1"}

# 流式接口：逐块输出（proxy_buffering off）
$ curl -N https://xiaoma.example.com/api/v1/chat/stream -d '{"message":"你好"}'
data: {"delta":"你"}
data: {"delta":"好"}
data: {"done":true}

# 配错时（缓冲未关）的样子：等 8 秒后一次性全出
$ curl -N https://xiaoma.example.com/api/v1/chat/stream -d '{"message":"你好"}'
（空白约 8 秒）
data: {"delta":"你"}data: {"delta":"好"}data: {"done":true}

$ tail -3 /var/log/nginx/error.log
2026/11/09 22:50:12 [error] 31#31: *8 upstream timed out (110: Connection timed out)
  while reading response header from upstream, client: 203.0.113.7,
  request: "GET /api/v1/chat/stream", upstream: "http://172.19.0.3:8000/api/v1/chat/stream""",
                "mistakes": """- `proxy_pass` 带不带结尾斜杠搞混，导致 `/api/v1/x` 变成 `/v1/x` 或 `/api/api/v1/x`。
- 全局设 `proxy_buffering off`，所有响应都失去缓冲优势；应按 location 精细设置。
- 流式接口沿用 60s 超时，长回答被中途掐断。
- 忘记转发 `X-Forwarded-Proto`，后端生成的重定向链接是 http，浏览器混合内容被拦。
- 把后端端口直接映射到宿主机"图方便"，绕过代理，HTTPS 与限流全部失效。""",
                "error_analysis": """`502 Bad Gateway`
—— 代理连不上上游。检查上游服务是否在跑、`proxy_pass` 的主机名能否解析（`nginx` 服务需与后端同网络）。

`504 Gateway Timeout`
—— 上游响应超过 `proxy_read_timeout`。长任务要单独 location 把超时上调。

`404` 但路径看着没错
—— `proxy_pass` 结尾斜杠导致路径被改写。用 `curl -v` 看实际请求 URL，或查 `error.log` 里的 `upstream: http://...`。

流式回复"卡住很久然后一次性出现"
—— `proxy_buffering` 没关，或 CDN 层有缓冲。

`upstream sent too big header`
—— 上游响应头过大，需调 `proxy_buffer_size` 与 `proxy_buffers`。""",
                "beginner_practice": """1. 写一个 Nginx 配置把 `/` 转前端、`/api/` 转后端，用 `curl` 验证两条路径都通。
2. 对比开/关 `proxy_buffering` 时流式接口的输出节奏。""",
                "advanced_practice": """为流式接口设计完整的代理配置：关闭缓冲、单独超时、支持 keepalive、记录真实 IP。
验收：(1) `curl -N` 能看到逐块输出；(2) 长回答（>60 秒）不中断；
(3) 后端日志里能看到真实客户端 IP 而非代理 IP。""",
                "quiz_note": "本节 6 道题：2 道基础理解（反向代理作用、proxy_buffering）+ 2 道输出阅读（读 502/504、读流式输出差异）+ 2 道应用练习（选对超时位置、判断路径改写）。",
                "summary": """反向代理是唯一入口，按路径把流量分给前端、后端与流式接口。
流式必须关 `proxy_buffering`，并给更长的 `proxy_read_timeout`。
`X-Forwarded-*` 让后端拿得到真实 IP 与协议。
502 查上游是否可达，504 查上游是否太慢，两者处理方向不同。""",
                "next_lesson": "有了域名和代理，下一个问题是证书：怎么配 HTTPS 且能自动续期。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-06-01",
                        "name": "反向代理与流式接口转发",
                        "goal": "能配置按路径分流的 Nginx，并为流式接口正确关闭缓冲、调整超时。",
                        "minutes": 35,
                        "criteria": "能写出含前端、普通 API、流式接口三条 location 的配置，并用 curl 验证流式逐块输出。",
                        "requires": ["software-engineering-deploy-05-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-06-01-1",
                        "kp": 0,
                        "title": "流式变成一次性输出",
                        "description": """SSE 接口在本地直连时逐块输出，经 Nginx 后等 10 秒一次性输出全部内容。
给出原因与修复。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''原因：Nginx 默认开启 `proxy_buffering on`，会把上游响应攒进缓冲区，
达到阈值或上游结束后才发给客户端。SSE 的"逐块"被合并成一次性。

修复：给流式接口单独 location 关闭缓冲。

```nginx
location /api/v1/chat/ {
    proxy_pass http://backend_upstream;
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding on;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_read_timeout 600s;
}
```

注意三点：
1. 不要全局关缓冲，静态与普通 JSON 响应仍需要缓冲；
2. 若前面还有 CDN，CDN 层也要关缓冲；
3. 超时要同时上调，否则长回答仍会被掐断。''',
                        "explanation": "「本地正常、上线变形」的流式问题，99% 是这一处。",
                    },
                    {
                        "code": "sed-ex-06-01-2",
                        "kp": 0,
                        "title": "区分 502 与 504",
                        "description": """线上出现两种错误：一部分请求 502、一部分 504。分别说明含义与排查方向。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''502 Bad Gateway：代理连上了上游但上游返回了无效响应，或根本连不上（连接被拒）。
排查方向：上游服务是否在运行、端口对吗、是否在同一网络、上游是否启动中崩溃。
`docker compose ps` + `docker compose logs backend` + `nginx -T` 看 upstream 配置。

504 Gateway Timeout：连接建立成功，但上游在 `proxy_read_timeout` 内没有返回。
排查方向：接口是否太慢（慢查询、外部 API 超时）、是否需要单独调大该 location 的超时、
上游是否卡在锁等待。

区分价值：502 多是"没起来/不可达"，504 多是"起来了但太慢"。两者优化方向完全不同。
先看 `error.log`，里面会写明 `connect() failed` 或 `upstream timed out`。''',
                        "explanation": "状态码本身就是线索，先分类再排查能省一半时间。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-06-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "SSE 流式接口经 Nginx 后变成一次性输出，根本原因是？",
                        "options": [
                            ("A", "后端不支持流式"),
                            ("B", "Nginx 的 proxy_buffering 默认开启，攒够才转发"),
                            ("C", "浏览器不支持 SSE"),
                            ("D", "HTTPS 加密导致"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "关闭该 location 的 `proxy_buffering` 即可恢复逐块输出。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列哪些是配置反向代理时应转发或设置的？（多选）",
                        "options": [
                            ("A", "Host"),
                            ("B", "X-Forwarded-For"),
                            ("C", "X-Forwarded-Proto"),
                            ("D", "数据库密码"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 与代理无关，绝不能在代理层传递任何密钥。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-01-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`error.log` 出现 `upstream timed out while reading response header`，对应客户端看到的？",
                        "options": [
                            ("A", "502"),
                            ("B", "504"),
                            ("C", "404"),
                            ("D", "301"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "读取上游超时对应 504；连接失败对应 502。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-01-4",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": """`location /v1/ { proxy_pass http://backend:8000/api/; }` 收到请求 `/v1/tasks` 时，后端实际收到的路径是什么？说明原因。""",
                        "answer": {"reference": "后端收到 `/api/tasks`。`proxy_pass` 带 URI（结尾是 `/api/`）时，会用它替换掉 location 匹配到的 `/v1/` 部分；若写成不带 URI 的 `proxy_pass http://backend:8000;`，则原样转发 `/v1/tasks`。", "keywords": ["/api/tasks", "location", "proxy_pass", "替换"]},
                        "explanation": "`proxy_pass` 带 URI（结尾有 `/api/`）时，会用它替换掉 location 匹配的部分。",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-01-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "要让流式接口不被缓冲，应加哪条指令？",
                        "options": [
                            ("A", "proxy_buffering off;"),
                            ("B", "proxy_cache on;"),
                            ("C", "chunked_transfer_encoding off;"),
                            ("D", "proxy_http_version 1.0;"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "关闭缓冲是流式的必要条件，配合 1.1 与长超时更稳。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-06-01-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "为了让配置简单，应该给所有接口统一设置 600 秒的 proxy_read_timeout。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "全局超长会让真正卡住的请求迟迟不暴露，故障发现时间被拉长。应只给流式接口放宽。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-06-lesson-02",
                "objectives": """1. 能说清 HTTPS 解决的三个问题（加密、身份、完整性）；
2. 能用 Let's Encrypt 申请证书并配置自动续期；
3. 会设置 HTTP→HTTPS 强制跳转与安全响应头；
4. 能读懂证书过期与域名不匹配的报错。""",
                "why_learn": """浏览器对 HTTP 页面会标"不安全"，很多 API（定位、剪贴板、Service Worker）只在 HTTPS 下可用。
更重要的是：登录密码、访问令牌、对话内容在 HTTP 下是明文传输，同一个 Wi-Fi 里就能被截获。
HTTPS 已经是上线的最低要求，不是加分项。""",
                "concepts": """**三件事**：加密（防窃听）、身份认证（防冒充）、完整性校验（防篡改）。
**证书链**：服务器证书 → 中间证书 → 根证书，缺中间证书会让部分客户端报错。
**Let's Encrypt**：免费证书，有效期 90 天，必须自动续期。
**ACME 验证**：HTTP-01（放文件到 `/.well-known/acme-challenge/`）或 DNS-01（加 TXT 记录）。
**HSTS**：告诉浏览器"以后只用 HTTPS 访问我"，一旦下发很难撤回。""",
                "plain": """HTTPS 像给快递加了带锁的箱子，还附了一张盖章的身份证明。
证书是那张证明：浏览器检查"这个箱子确实是 xiaoma.example.com 寄的"，不是别人冒充的。
90 天有效期是故意的——逼你自动化续期，降低证书被盗用后的风险窗口。
HSTS 是"以后只收带锁的快递"，一旦告诉浏览器，你再想退回普通快递（HTTP）就会被拦。""",
                "syntax": """**申请证书（HTTP-01）**

```bash
# 用 certbot webroot 模式，不中断现有 Nginx
certbot certonly --webroot -w /var/www/certbot \\
  -d xiaoma.example.com --email you@example.com --agree-tos --non-interactive
```

**Nginx HTTPS 配置**

```nginx
server {
    listen 80;
    server_name xiaoma.example.com;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    http2 on;
    server_name xiaoma.example.com;

    ssl_certificate     /etc/letsencrypt/live/xiaoma.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xiaoma.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;
}
```

**自动续期**

```bash
# crontab：每天两次尝试续期（到期前 30 天才真正续）
0 3,15 * * * certbot renew --quiet --deploy-hook "nginx -s reload"
```

- `fullchain.pem` 必须包含中间证书，否则部分 Android 设备报错。
- `--deploy-hook` 让续期成功后自动 reload，无需手动。""",
                "example_code": '''# 场景：从零给一个新域名上 HTTPS

# 1) 确认 80 端口可达（ACME 验证要用）
curl -I http://xiaoma.example.com/.well-known/acme-challenge/test
# 若返回 404 但能连通，即可继续；返回连接失败要先修 DNS 或防火墙

# 2) 申请证书
docker run --rm \\
  -v /etc/letsencrypt:/etc/letsencrypt \\
  -v /var/www/certbot:/var/www/certbot \\
  certbot/certbot certonly --webroot -w /var/www/certbot \\
  -d xiaoma.example.com -d www.xiaoma.example.com \\
  --email ops@example.com --agree-tos --non-interactive

# 3) 查看证书信息
openssl x509 -in /etc/letsencrypt/live/xiaoma.example.com/fullchain.pem \\
  -noout -subject -issuer -dates
# subject=CN = xiaoma.example.com
# issuer=C = US, O = Let's Encrypt, CN = R11
# notBefore=Nov  9 22:55:00 2026 GMT
# notAfter=Feb  7 22:55:00 2027 GMT

# 4) 验证 HTTPS 与跳转
curl -I http://xiaoma.example.com
# HTTP/1.1 301 Moved Permanently
# Location: https://xiaoma.example.com/

curl -sI https://xiaoma.example.com/api/v1/health
# HTTP/2 200
# strict-transport-security: max-age=31536000; includeSubDomains

# 5) 模拟续期
docker run --rm \\
  -v /etc/letsencrypt:/etc/letsencrypt \\
  -v /var/www/certbot:/var/www/certbot \\
  certbot/certbot renew --dry-run''',
                "code_lines": """1. 先验证 80 端口可达：ACME 的 HTTP-01 验证需要外部能访问 `/.well-known/acme-challenge/`。
2. 用 Docker 版 certbot 时两个目录都要挂载：证书目录与验证文件目录。
3. 多个 `-d` 一次申请多个域名，证书会包含 SAN（备用名称），覆盖 www 与裸域。
4. `openssl x509` 查看有效期与签发者，确认证书链正确。
5. `301` 跳转把所有 HTTP 流量导向 HTTPS，浏览器地址栏才会显示安全锁。
6. `strict-transport-security` 是 HSTS：告知浏览器后续强制走 HTTPS。
7. `renew --dry-run` 用测试环境演练续期流程，避免真到期那天才发现 cron 没生效。
8. `--deploy-hook "nginx -s reload"` 保证续期后立即加载新证书，否则 Nginx 仍用旧证书直到重启。""",
                "output": """$ curl -I http://xiaoma.example.com
HTTP/1.1 301 Moved Permanently
Location: https://xiaoma.example.com/

$ curl -sI https://xiaoma.example.com/api/v1/health
HTTP/2 200
strict-transport-security: max-age=31536000; includeSubDomains
x-content-type-options: nosniff

# 证书链检查（应看到 2 级以上）
$ openssl s_client -connect xiaoma.example.com:443 -servername xiaoma.example.com < /dev/null 2>/dev/null \\
    | openssl crl2pkcs7 -nocrl -certfile /dev/stdin | openssl pkcs7 -print_certs -noout
subject=CN = xiaoma.example.com
issuer=C = US, O = Let's Encrypt, CN = R11
subject=C = US, O = Let's Encrypt, CN = R11
issuer=C = US, O = Internet Security Research Group, CN = ISRG Root X1

# 证书快过期时的浏览器警告
NET::ERR_CERT_DATE_INVALID
您的连接不是私密连接
此服务器无法证明它是 xiaoma.example.com；它的安全证书已于 2026/11/1 过期。""",
                "mistakes": """- 只用了 `cert.pem` 而不是 `fullchain.pem`，部分客户端报"证书链不完整"。
- 证书配了但没有自动续期，90 天后整站不可用。
- 续期成功但没 reload Nginx，仍在用旧证书。
- 早期就开启 `preload` 的 HSTS，之后换域名或临时回退 HTTP 全被拦。
- 为了"兼容老设备"保留 TLSv1.0/1.1，被安全扫描判为高危。""",
                "error_analysis": """`NET::ERR_CERT_DATE_INVALID`
—— 证书过期。立即手动续期并检查自动续期任务是否在跑。

`NET::ERR_CERT_COMMON_NAME_INVALID`
—— 证书域名与实际访问域名不匹配（如证书只有裸域，访问的是 www）。

`unable to get local issuer certificate`
—— 缺中间证书，改配 `fullchain.pem`。

`certbot renew` 报 `Timeout during connect (likely firewall problem)`
—— 80 端口不可达，HTTP-01 无法验证。检查防火墙、安全组、或改用 DNS-01。""",
                "beginner_practice": """1. 用一个测试域名（或用 `localhost` + 自签证书）走一遍申请/配置流程，验证 301 跳转生效。
2. 用 `openssl x509 -noout -dates` 查看证书有效期，并执行 `certbot renew --dry-run`。""",
                "advanced_practice": """为生产站点设计证书方案：域名规划（裸域与 www）、验证方式选择（HTTP-01 还是 DNS-01）、
自动续期与 reload 的完整链路、以及到期前 15 天的告警。
完成后回答：为什么 HSTS 的 `includeSubDomains` 和 `preload` 要谨慎开启？""",
                "quiz_note": "本节 6 道题：2 道基础理解（HTTPS 三件事、HSTS 作用）+ 2 道输出阅读（读证书信息、读浏览器报错）+ 2 道应用练习（选对证书文件、判断续期链路）。",
                "summary": """HTTPS 同时解决加密、身份与完整性，是上线最低要求。
必须用 `fullchain.pem`，缺中间证书会挑客户端报错。
Let's Encrypt 只有 90 天，自动续期 + `deploy-hook` reload 缺一不可。
HSTS 一旦下发很难撤回，`preload` 更要慎重。""",
                "next_lesson": "证书有了，怎么把新版本发布上去又不中断服务？下一节讲发布流程与回退。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-06-02",
                        "name": "HTTPS 证书与自动续期",
                        "goal": "能申请并配置证书、强制跳转 HTTPS，并建立可靠的自动续期链路。",
                        "minutes": 30,
                        "criteria": "能独立完成证书配置与 301 跳转，且 `renew --dry-run` 通过并验证续期后会 reload。",
                        "requires": ["software-engineering-deploy-06-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-06-02-1",
                        "kp": 0,
                        "title": "整站突然不可用",
                        "description": """上线 90 天后所有用户打开页面都提示证书过期。
写出应急处理步骤，以及事后如何防止再次发生。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''应急处理（按顺序）：
1. 手动续期：`certbot renew --force-renewal`；
2. 重新加载：`nginx -s reload`（证书文件变了但 Nginx 不会自动重读）；
3. 验证：`curl -sI https://域名` 看是否 200，`openssl x509 -noout -dates` 看新有效期；
4. 通知用户刷新页面或等待浏览器重试。

事后防复发：
- 检查 cron / systemd timer 是否真的在跑（`systemctl list-timers`、`journalctl -u certbot`）；
- 加上 `--deploy-hook "nginx -s reload"`；
- 到期前 15 天设置告警（监控证书剩余天数，而不是等用户报错）；
- 每季度跑一次 `certbot renew --dry-run` 验证链路。

核心教训：证书过期不是"证书问题"，是"续期链路没被验证过"的问题。''',
                        "explanation": "绝大多数证书事故都不是没配自动续期，而是配了没验证过。",
                    },
                    {
                        "code": "sed-ex-06-02-2",
                        "kp": 0,
                        "title": "选哪个证书文件",
                        "description": """`/etc/letsencrypt/live/example.com/` 下有 `cert.pem`、`chain.pem`、`fullchain.pem`、`privkey.pem`。
Nginx 的 `ssl_certificate` 应该配哪个？为什么？""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''配 `fullchain.pem`。

原因：`fullchain.pem = cert.pem + chain.pem`（服务器证书 + 中间证书）。
只配 `cert.pem` 时，服务器不会下发中间证书，客户端若本地没有缓存该中间证书
（常见于较老 Android、部分 Java 客户端）就会报
`unable to get local issuer certificate` 或直接连接失败。
桌面 Chrome 可能因为缓存过中间证书而"看起来正常"，导致问题只在部分用户那里出现——更难排查。

`ssl_certificate_key` 配 `privkey.pem`。注意私钥权限应限制为 600 且属主为 root。''',
                        "explanation": """证书链不完整是"部分用户能开、部分报错"的典型原因。""",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-06-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "HTTPS 相比 HTTP 提供的三个保证不包括？",
                        "options": [
                            ("A", "传输加密"),
                            ("B", "服务器身份认证"),
                            ("C", "数据完整性校验"),
                            ("D", "服务端防 DDoS"),
                        ],
                        "answer": {"value": "D"},
                        "explanation": "DDoS 防护属于网络层/代理层能力，与 TLS 无关。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "证书自动续期链路需要哪些环节？（多选）",
                        "options": [
                            ("A", "定时任务执行 certbot renew"),
                            ("B", "续期成功后 reload Nginx"),
                            ("C", "到期前告警"),
                            ("D", "手动每月改一次配置"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 不是自动化，且容易遗忘。缺 B 会导致续期成功但仍用旧证书。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-02-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`openssl x509 ... -dates` 输出 `notAfter=Feb 7 22:55:00 2027 GMT`，含义是？",
                        "options": [
                            ("A", "证书签发时间"),
                            ("B", "证书到期时间"),
                            ("C", "证书指纹"),
                            ("D", "证书版本"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "`notBefore` 是签发时间，`notAfter` 是到期时间，是监控证书剩余天数的依据。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-02-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "浏览器报 `NET::ERR_CERT_COMMON_NAME_INVALID`，最可能的原因是？",
                        "options": [
                            ("A", "证书过期"),
                            ("B", "证书里的域名与实际访问域名不一致"),
                            ("C", "服务器宕机"),
                            ("D", "端口错误"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "常见于只申请了裸域却用 www 访问，或反代域名与证书不匹配。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-02-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "让所有 HTTP 请求永久跳转到 HTTPS，Nginx 里应写？",
                        "options": [
                            ("A", "return 302 https://$host$request_uri;"),
                            ("B", "return 301 https://$host$request_uri;"),
                            ("C", "rewrite ^ http://$host$request_uri;"),
                            ("D", "proxy_pass https://$host;"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "301 是永久跳转，浏览器会缓存，减少后续请求的往返。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-06-02-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "HSTS 的 preload 列表一旦提交，后续想撤回需要很长时间，因此要谨慎开启。",
                        "options": None,
                        "answer": {"value": True},
                        "explanation": "preload 写进浏览器内置列表，移除需等各浏览器版本更新，期间无法回退到 HTTP。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-06-lesson-03",
                "objectives": """1. 能设计一条含健康检查与失败回退的发布流程；
2. 理解蓝绿、滚动、灰度三种策略的取舍；
3. 能为一次发布定义成功指标与观察窗口；
4. 知道发布失败时"回退"与"修复"该如何选择。""",
                "why_learn": """发布是把改动送到用户面前的最后一步，也是最容易出事的时刻。
发布出问题不可怕，可怕的是"发现问题时已经无法快速回到上一个可用状态"。
一条好的发布流程，核心不是"不出错"，而是"出错能在一分钟内恢复"。""",
                "concepts": """**蓝绿部署**：两套环境并存，切流量即可回退，成本翻倍。
**滚动更新**：逐批替换实例，期间新旧版本共存，需要接口兼容。
**灰度/金丝雀**：先放 5% 流量给新版本，观察指标再全量。
**成功指标**：错误率、P95 延迟、关键业务成功率，发布前定好阈值。
**回退决策**：数据不可逆或错误率超阈值 → 回退；局部小问题 → 热修复更快。""",
                "plain": """发布像换轮胎：赛车进站（窗口）换胎，换完先低速跑一圈（健康检查 + 观察），
没问题再全速（全量）。发现轮胎有问题就立刻换回旧胎（回退），而不是在赛道上修。
蓝绿是"准备一套备用轮子"，滚动是"一个个轮子换"，灰度是"先换一个轮子试跑"。
选哪种取决于：能不能停、成本能付多少、出错影响多大。""",
                "syntax": """**发布脚本骨架**

```bash
#!/usr/bin/env bash
set -euo pipefail

PREV_IMAGE="$1"        # 上一个可用镜像标签
NEW_IMAGE="$2"
HEALTH_URL="http://127.0.0.1:3000/api/v1/health"

echo "[1/6] 预检：磁盘与当前健康状态"
curl -fsS "$HEALTH_URL" > /dev/null || { echo "当前服务已不健康，停止发布"; exit 1; }
df -h / | awk 'NR==2 && $5+0 > 80 { exit 1 }'

echo "[2/6] 备份数据"
docker compose exec -T backend python -m app.cli backup-db

echo "[3/6] 拉取并启动新版本"
TAG="$NEW_IMAGE" docker compose up -d --no-deps backend

echo "[4/6] 等待健康检查（最多 120 秒）"
for i in $(seq 1 24); do
  if curl -fsS "$HEALTH_URL" > /dev/null; then echo "健康检查通过"; break; fi
  [ "$i" -eq 24 ] && { echo "健康检查超时，开始回退"; TAG="$PREV_IMAGE" docker compose up -d --no-deps backend; exit 1; }
  sleep 5
done

echo "[5/6] 观察窗口（5 分钟错误率）"
# 这里接监控查询，错误率 > 1% 则回退

echo "[6/6] 发布完成，记录版本"
```

- `set -euo pipefail` 让任何一步失败立即停止。
- `--no-deps` 只更新目标服务，不牵连数据库。""",
                "example_code": '''# 发布流程的关键四段：预检 → 发布 → 观察 → 决策

# ---------- 1. 预检 ----------
curl -fsS http://127.0.0.1:3000/api/v1/health
docker compose exec -T backend python -m app.cli backup-db
docker compose ps

# ---------- 2. 发布（用镜像标签切换，不重建） ----------
export TAG=v1.4.2
docker compose up -d --no-deps backend

# ---------- 3. 观察 ----------
for i in $(seq 1 12); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3000/api/v1/health)
  echo "$(date +%H:%M:%S) health=$code"
  sleep 10
done

# ---------- 4. 决策 ----------
# 若持续 200 → 全量，清理旧镜像
# 若出现 5xx 或超时 → 回退
export TAG=v1.4.1
docker compose up -d --no-deps backend

# ---------- 回退后验证 ----------
curl -fsS http://127.0.0.1:3000/api/v1/health
curl -s http://127.0.0.1:3000/api/v1/courses | head -c 80''',
                "code_lines": """1. 预检的三件事：当前服务健康（否则问题在发布前就有）、数据已备份、资源足够。
2. 用镜像标签 `TAG` 切换版本，而不是每次 `--build`：回退只需把标签改回上一个。
3. `--no-deps` 避免连带重启数据库，把发布影响面缩到最小。
4. 观察窗口看的是**健康接口与错误率**，不是"容器起来了"——后者只是必要条件。
5. 回退动作与发布动作完全相同，只是标签不同——这是可回退设计的核心。
6. 回退后必须验证：健康检查 + 一个关键业务接口，否则"回退了但没生效"无人知晓。
7. 整个过程可脚本化，才可能在半夜出事时一分钟内执行完。""",
                "output": """$ ./deploy.sh v1.4.1 v1.4.2
[1/6] 预检：磁盘与当前健康状态
{"status":"ok","version":"1.4.1"}
备份完成：/app/data/backups/xiaoma-20261109-225501-112233.db
[2/6] 备份数据
[3/6] 拉取并启动新版本
 Container xiaoma-backend  Started
[4/6] 等待健康检查（最多 120 秒）
健康检查通过
[5/6] 观察窗口（5 分钟错误率）
22:55:10 health=200
22:55:20 health=200
...
[6/6] 发布完成，记录版本
version=1.4.2

# ---- 失败场景 ----
$ ./deploy.sh v1.4.1 v1.4.3
[4/6] 等待健康检查（最多 120 秒）
健康检查超时，开始回退
 Container xiaoma-backend  Started        # 已切回 v1.4.1
$ curl -s http://127.0.0.1:3000/api/v1/health
{"status":"ok","version":"1.4.1"}""",
                "mistakes": """- 直接在生产 `docker compose up --build`，构建失败时旧的容器已经被停掉，服务中断。
- 没有备份就发布带迁移的版本，回退时数据库结构已经变了。
- 发布后只看"容器 Up"就宣布完成，没人看守观察窗口。
- 回退时用 `git checkout` + 重建，耗时几分钟；应该用镜像标签秒级切换。
- 把灰度当"试试看"，不定义成功指标，出问题才现找基线。""",
                "error_analysis": """发布后 503 / 502 持续
—— 新版本没起来或健康检查没过。立即切回上一个标签，再排查。

回退后仍报错
—— 数据库迁移不可逆（新版本改了表结构），旧代码不兼容新结构。这类迁移必须"向前兼容两步"。

`no space left on device` 发生在发布时
—— 旧镜像堆积。发布前清理：`docker image prune -f`（先确认没有正在使用的旧版本需要保留）。

健康检查一直 starting 直到超时
—— 新版本启动脚本卡住（迁移耗时、依赖不可达）。看 `logs --tail 100` 定位卡在哪一步。""",
                "beginner_practice": """1. 写一个发布脚本骨架：预检、备份、切换标签、健康检查、失败回退。
2. 故意发布一个"启动即崩溃"的版本，验证脚本能自动回退。""",
                "advanced_practice": """为你的项目设计三个阶段：灰度 10% → 观察 10 分钟 → 全量。
定义明确的三条成功指标与回退阈值，并说明：
(1) 为什么带不可逆迁移的版本不能用灰度？
(2) 蓝绿与滚动在小团队单机部署下各有什么代价？""",
                "quiz_note": "本节 6 道题：2 道基础理解（发布策略取舍、回退决策）+ 2 道输出阅读（读发布日志、读回退失败）+ 2 道应用练习（选对回退方式、判断观察指标）。",
                "summary": """发布流程的核心是"可回退"：镜像标签切换比重新构建快一个数量级。
预检、备份、健康检查、观察窗口，四步都不能省。
回退与发布是同一个动作，只是标签不同。
带不可逆迁移的版本要格外小心，回退可能不成立。""",
                "next_lesson": "发布完还要能救回来——下一节专门讲备份与回滚的实操。",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-06-03",
                        "name": "发布流程与失败回退",
                        "goal": "能设计含预检、备份、健康检查与自动回退的发布流程。",
                        "minutes": 40,
                        "criteria": "能写出可执行的发布脚本，并在新版本启动失败时自动切回上一个可用标签。",
                        "requires": ["software-engineering-deploy-06-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-06-03-1",
                        "kp": 0,
                        "title": "回退还是热修",
                        "description": """发布后出现两种问题，分别该回退还是热修？说明理由。
(1) 错误率从 0.2% 升到 8%，大量用户无法登录。
(2) 某个次要页面的文案写错了，功能正常。""",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''(1) 立即回退。理由：影响面大、用户可感知、错误率远超阈值；回退是秒级操作，
    定位与修复需要时间。回退后再在本地复现、修复、重新走流程。
    回退前先确认这次发布没有不可逆迁移，否则回退本身会失败。

(2) 热修。理由：不影响功能，回退会牵扯其他已上线的改动；
    走一次小版本（PATCH）修复，成本低于回退再重发。

判断口诀：**影响用户核心路径 + 可秒级回退 → 回退；局部且回退代价更高 → 热修**。
无论哪种，都要记录到发布复盘里。''',
                        "explanation": "回退不是失败，是止损手段；把它当常规能力而不是应急补救。",
                    },
                    {
                        "code": "sed-ex-06-03-2",
                        "kp": 0,
                        "title": "写回退段",
                        "description": """补全脚本的回退部分：健康检查连续失败 3 次时，切回 `$PREV_IMAGE` 并验证。""",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''```bash
fail=0
for i in $(seq 1 24); do
  if curl -fsS "$HEALTH_URL" > /dev/null 2>&1; then
    fail=0
  else
    fail=$((fail + 1))
    echo "健康检查失败 $fail 次"
    if [ "$fail" -ge 3 ]; then
      echo "连续失败 3 次，回退到 $PREV_IMAGE"
      TAG="$PREV_IMAGE" docker compose up -d --no-deps backend
      sleep 10
      curl -fsS "$HEALTH_URL" > /dev/null \\
        && echo "回退成功，版本已恢复" \\
        || { echo "回退后仍不健康，需要人工介入"; exit 2; }
      exit 1
    fi
  fi
  sleep 5
done
```

要点：
- 用「连续失败」而不是「单次失败」，避免抖动误判；
- 回退后必须再验证一次，否则会误以为已恢复；
- 回退仍失败要显式报"需人工介入"，不能静默退出。''',
                        "explanation": "回退代码比发布代码更需要严谨，因为它在最紧张的时刻执行。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-06-03-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "实现秒级回退最有效的手段是？",
                        "options": [
                            ("A", "git checkout 上一个提交后重新构建"),
                            ("B", "保留上一个可用镜像，切换标签重启"),
                            ("C", "重启服务器"),
                            ("D", "恢复数据库备份"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": """重新构建要几分钟，切标签只要几秒。这是"可回退设计"的核心。""",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-03-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "发布前预检应包含哪些？（多选）",
                        "options": [
                            ("A", "确认当前服务健康"),
                            ("B", "备份数据库"),
                            ("C", "检查磁盘空间"),
                            ("D", "直接删除旧镜像释放空间"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 危险：旧镜像正是回退所需，删了就没有退路。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-03-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "发布日志显示 `健康检查超时，开始回退` 之后 `curl` 返回 `version: 1.4.1`，说明？",
                        "options": [
                            ("A", "回退成功，服务已回到上一个版本"),
                            ("B", "回退失败"),
                            ("C", "新版本已生效"),
                            ("D", "服务未启动"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "版本号回到 1.4.1 且有健康响应，说明回退生效。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-03-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "回退后接口仍报错，最可能的原因是？",
                        "options": [
                            ("A", "镜像标签没切"),
                            ("B", "新版本执行了不可逆的数据库迁移，旧代码不兼容新表结构"),
                            ("C", "网络故障"),
                            ("D", "证书过期"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": """有迁移的版本必须保证"向前兼容"至少两个版本，否则回退不成立。""",
                        "difficulty": "advanced",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-03-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "只更新 backend 服务、不重启其依赖服务，`docker compose up` 应加哪个参数？",
                        "options": [
                            ("A", "--no-deps"),
                            ("B", "--force-recreate"),
                            ("C", "--remove-orphans"),
                            ("D", "--abort-on-container-exit"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`--no-deps` 把发布影响面限制在目标服务，避免连带重启数据库。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-06-03-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "发布后只要容器状态是 Up，就可以宣布发布成功。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "Up 只说明进程在跑。必须验证健康接口与关键业务，并观察一段时间的错误率。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "software-engineering-deploy-06-lesson-04",
                "objectives": """1. 能制定备份策略（频率、保留期、异地）；
2. 能执行一次完整的备份 → 破坏 → 恢复演练；
3. 理解"备份没验证过等于没有备份"；
4. 能判断什么时候该回滚数据、什么时候该补偿数据。""",
                "why_learn": """发布失败可以回退镜像，但数据被误删、迁移写坏、勒索加密，只能靠备份。
备份最容易犯的错不是"没做"，而是"做了但从没试过恢复"——
真出事时才发现备份是空的、权限不对、或者恢复脚本根本跑不起来。""",
                "concepts": """**3-2-1 原则**：3 份副本、2 种介质、1 份异地。
**一致性备份**：数据库运行中直接 copy 文件可能拿到半个事务，要用在线备份 API。
**保留策略**：日备保留 7 天、周备保留 4 周、月备保留 12 个月。
**恢复演练**：定期在隔离环境真实恢复一次，验证可用性。
**不可逆操作前后必备份**：迁移、批量删除、结构变更。""",
                "plain": """备份像保险：买的时候觉得多余，出事时发现保额不够或条款不认。
"在线备份"是在店还开着的时候拍一张账本快照，而不是关店后复印——后者容易漏掉正在记的账。
恢复演练是"试赔一次"：不试过，你不知道保单到底管不管用。
3-2-1 原则是防"同一场火灾烧掉所有副本"：都在同一台机器上，机器坏了备份一起没。""",
                "syntax": """**SQLite 在线备份（项目内置）**

```bash
python -m app.cli backup-db                      # 生成一致性快照
python -m app.cli list-backups                   # 列出可用备份
python -m app.cli restore-db <文件名> --yes       # 恢复（需先停后端）
```

**卷级备份**

```bash
docker run --rm \\
  -v xiaoma_xiaoma-data:/data \\
  -v "$PWD":/backup \\
  alpine tar czf /backup/data-$(date +%Y%m%d).tar.gz -C /data .
```

**定期清理（保留 14 天）**

```bash
find /backup -name "data-*.tar.gz" -mtime +14 -delete
```

- 恢复前必须停后端，否则会与运行中的写入冲突。
- 备份文件要校验：`sqlite3 backup.db "PRAGMA integrity_check"`。""",
                "example_code": '''# 一次完整的备份 → 破坏 → 恢复演练

# ---------- 1. 备份 ----------
docker compose exec -T backend python -m app.cli backup-db
# 备份完成：/app/data/backups/xiaoma-20261109-225501-112233.db

# 导出到宿主机（异地留档）
MSYS_NO_PATHCONV=1 docker compose cp \\
  backend:/app/data/backups/xiaoma-20261109-225501-112233.db \\
  ./backups/volume-before-exercise.db

# ---------- 2. 校验备份可用性 ----------
docker compose exec -T backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/backups/xiaoma-20261109-225501-112233.db')
print('integrity:', c.execute('PRAGMA integrity_check').fetchone()[0])
print('courses:', c.execute('SELECT count(*) FROM courses').fetchone()[0])
print('knowledge_points:', c.execute('SELECT count(*) FROM knowledge_points').fetchone()[0])
"
# integrity: ok
# courses: 7
# knowledge_points: 194

# ---------- 3. 故意破坏（模拟事故） ----------
docker compose exec -T backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/xiaoma.db')
c.execute('DELETE FROM knowledge_points')
c.commit()
print('deleted')
"

# 此时前端「课程体系」应该显示「该课程没有可学习的知识点」

# ---------- 4. 停止写入并恢复 ----------
docker compose stop backend
docker compose run --rm backend python -m app.cli restore-db \\
  xiaoma-20261109-225501-112233.db --yes
docker compose start backend

# ---------- 5. 验证恢复 ----------
curl -s http://127.0.0.1:3000/api/v1/courses | head -c 200
docker compose exec -T backend python -c "
import sqlite3
c = sqlite3.connect('/app/data/xiaoma.db')
print('knowledge_points:', c.execute('SELECT count(*) FROM knowledge_points').fetchone()[0])
"
# knowledge_points: 194''',
                "code_lines": """1. 备份用内置 CLI，它走 SQLite 在线备份 API，服务运行中执行也能拿到一致快照。
2. 导出到宿主机是"异地副本"：容器卷被误删时，宿主机这份还在。
3. 恢复前先校验备份：`integrity_check` 与关键表行数，避免"恢复了一个坏备份"。
4. 第 3 步故意删数据，是为了证明"没有备份会怎样"——演练要有破坏环节才有意义。
5. 恢复必须停后端：`stop` 而不是 `down`，保留容器定义与卷。
6. `run --rm backend` 用一次性容器执行恢复，避开运行中的连接。
7. 恢复后验证看的是"业务能否读到数据"，不只是"文件存在"。""",
                "output": """$ docker compose exec -T backend python -m app.cli backup-db
备份完成：/app/data/backups/xiaoma-20261109-225501-112233.db
大小：1015808 字节

$ python -c "integrity_check"
integrity: ok
courses: 7
knowledge_points: 194

$ # 破坏后
$ curl -s http://127.0.0.1:3000/api/v1/courses/llm-api | python -c "import json,sys;print(json.load(sys.stdin)['knowledge_point_count'])"
0

$ docker compose stop backend
$ docker compose run --rm backend python -m app.cli restore-db xiaoma-20261109-225501-112233.db --yes
已自动备份当前数据库：pre-restore-20261109-225530.db
正在校验备份完整性...
校验通过，开始恢复...
恢复完成：knowledge_points=194

$ docker compose start backend
$ curl -s http://127.0.0.1:3000/api/v1/courses/llm-api | python -c "import json,sys;print(json.load(sys.stdin)['knowledge_point_count'])"
32""",
                "mistakes": """- 只备份数据库文件，忘了 `.secret_key`，恢复后所有 API Key 无法解密。
- 备份与数据在同一块磁盘上，磁盘故障时一起消失。
- 从未执行过恢复演练，真出事才发现备份脚本早就因为权限问题失败。
- 用 `cp` 直接复制正在写入的 SQLite 文件，拿到的是半写状态，恢复后数据损坏。
- 设置"保留 30 天"但没清理脚本，磁盘被备份填满，反而导致服务不可用。""",
                "error_analysis": """`sqlite3.DatabaseError: database disk image is malformed`
—— 备份不完整（大概率是运行中用 `cp` 复制的）。改用在线备份 API。

`restore-db` 报「校验失败：缺少必需表」
—— 备份文件不完整或版本不匹配。换一个更早的备份，并检查备份任务的日志。

恢复后接口正常但解密失败
—— 只恢复了数据库，没恢复 `.secret_key`。两者必须成对备份。

备份任务悄悄失败
—— cron 没配日志、没配告警。备份任务必须"失败要能知道"，否则等于没做。""",
                "beginner_practice": """1. 执行一次 `backup-db`，用 `integrity_check` 验证备份可用。
2. 完整走一遍"备份 → 删数据 → 恢复 → 验证"，记录每步耗时。""",
                "advanced_practice": """为项目设计备份方案：频率、保留策略、异地存储、监控告警、每月演练计划。
并回答：为什么"带不可逆迁移的发布"必须在上线前额外做一次备份？
如果恢复后发现了数据丢失，还有哪些补救手段？""",
                "quiz_note": "本节 6 道题：2 道基础理解（3-2-1 原则、在线备份必要性）+ 2 道输出阅读（读恢复日志、读损坏报错）+ 2 道应用练习（选对备份方式、判断恢复顺序）。",
                "summary": """备份的价值只在"能恢复"那一刻体现，没演练过的备份不算备份。
用在线备份 API 而不是复制文件，才能拿到一致快照。
数据库与 `.secret_key` 必须成对备份，否则恢复后密钥全废。
3-2-1 原则防的是"同一故障带走所有副本"。""",
                "next_lesson": """数据能救回来了，下一个能力是"怎么知道出了事"——进入日志与排障。""",
                "knowledge_points": [
                    {
                        "code": "software-engineering-deploy-06-04",
                        "name": "备份策略与恢复演练",
                        "goal": "能制定备份策略并完成一次真实的备份到恢复演练。",
                        "minutes": 35,
                        "criteria": "能独立完成一次含校验与破坏环节的恢复演练，且恢复后业务数据可正常读取。",
                        "requires": ["software-engineering-deploy-06-03"],
                    }
                ],
                "practice": [
                    {
                        "code": "sed-ex-06-04-1",
                        "kp": 0,
                        "title": "为什么备份恢复后密钥失效",
                        "description": """只备份了 `xiaoma.db`，恢复到新机器后所有模型配置都报"无法解密已保存的密钥"。
解释原因与正确做法。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''原因：数据库里存的是 Fernet 密文，解密需要 `data/.secret_key`。
只恢复了数据库，新环境的 `.secret_key` 是重新生成的（或不存在），
密钥不匹配 → 解密失败。

正确做法：
1. 备份时必须同时包含数据库与 `.secret_key`（整个 `/app/data` 目录最省事）；
2. 恢复时一起放回原路径；
3. 若确实丢失密钥，只能让用户重新填写 API Key——密文无法逆向恢复。

延伸：备份清单里应该明确列出"数据库 + 密钥 + 上传文件"三类，
只备份数据库是容器化部署里最常见的疏漏。''',
                        "explanation": "「数据」不只有数据库；加密密钥、上传文件同样属于必须恢复的状态。",
                    },
                    {
                        "code": "sed-ex-06-04-2",
                        "kp": 0,
                        "title": "设计保留策略",
                        "description": """日备 1 份约 1MB，磁盘可给备份 500MB。设计一套保留策略并写出清理命令。""",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''策略：
- 日备：保留 14 天（14 × 1MB = 14MB）
- 周备：每周日保留 1 份，保留 8 周（8MB）
- 月备：每月 1 日保留 1 份，保留 12 个月（12MB）
合计约 34MB，远低于 500MB 上限，留出增长空间。

清理命令（只删日备，保留周备与月备）：
```bash
find /backup/daily -name "xiaoma-*.db" -mtime +14 -delete
find /backup/weekly -name "xiaoma-*.db" -mtime +56 -delete
find /backup/monthly -name "xiaoma-*.db" -mtime +365 -delete
```

要点：
1. 保留期要按"最坏发现时间"定——数据被改坏可能一周后才发现，日备至少要覆盖这个窗口；
2. 清理命令先 `-print` 试运行，确认列表无误再加 `-delete`；
3. 备份目录要有容量告警，别等写满才处理。''',
                        "explanation": """保留策略的目标不是"越多越好"，而是"覆盖到能发现问题的那个时间窗口"。""",
                    },
                ],
                "questions": [
                    {
                        "code": "q-sed-06-04-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "3-2-1 备份原则中「1」指的是？",
                        "options": [
                            ("A", "1 份副本"),
                            ("B", "1 份异地副本"),
                            ("C", "1 天备份一次"),
                            ("D", "1 种介质"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "3 份副本、2 种介质、1 份异地，目的是防止单点故障带走全部备份。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-04-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "一个完整的备份方案应包含？（多选）",
                        "options": [
                            ("A", "备份频率与保留期"),
                            ("B", "异地副本"),
                            ("C", "定期恢复演练"),
                            ("D", "只在发布前手动备份一次"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 无法覆盖误删、勒索、磁盘故障等非发布场景。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-sed-06-04-3",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "恢复日志显示 `已自动备份当前数据库：pre-restore-*.db`，这个行为的意义是？",
                        "options": [
                            ("A", "多占磁盘空间"),
                            ("B", "为回退留后路：恢复错了还能回到恢复前的状态"),
                            ("C", "加快恢复速度"),
                            ("D", "校验备份完整性"),
                        ],
                        "answer": {"value": "B"},
                        "explanation": "恢复本身也是高风险操作，自动保留恢复前快照是安全网。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-04-4",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`database disk image is malformed` 出现在恢复阶段，最可能的原因？",
                        "options": [
                            ("A", "备份文件是运行中直接 cp 复制的，内容不一致"),
                            ("B", "磁盘满了"),
                            ("C", "SQLite 版本过高"),
                            ("D", "端口冲突"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "运行中复制可能拿到半个事务。必须用在线备份 API 生成快照。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-sed-06-04-5",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "恢复数据库前必须先做什么？",
                        "options": [
                            ("A", "停止后端服务，避免与运行中的写入冲突"),
                            ("B", "重启服务器"),
                            ("C", "删除卷"),
                            ("D", "重建镜像"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "运行中恢复会与写入冲突，可能导致文件损坏或数据错乱。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-sed-06-04-6",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只要设置了每日自动备份，就不需要做恢复演练。",
                        "options": None,
                        "answer": {"value": False},
                        "explanation": "备份任务可能长期静默失败、权限错误、内容不完整。不演练就无法发现。",
                        "difficulty": "beginner",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
