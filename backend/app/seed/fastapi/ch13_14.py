"""FastAPI 后端开发：第 13—14 章（权限与文件上传、API 文档与接口测试）。"""

CHAPTERS: list[dict] = [
    {
        "code": "fastapi-backend-13",
        "title": "权限控制与文件上传",
        "description": "谁能做什么，以及怎么安全收文件。",
        "order_index": 13,
        "lessons": [
            {
                "code": "fastapi-backend-13-lesson-01",
                "objectives": """1. 能区分认证（401）与授权（403）；
2. 会把角色校验做成可复用依赖；
3. 能实现资源级权限（只能改自己的任务）；
4. 知道最小权限原则与越权漏洞的常见形态。""",
                "why_learn": """只校验「登录了」是不够的：普通用户拿着自己的令牌去改别人的任务，接口照样返回 200——这就是最常见的越权漏洞（IDOR）。
权限要落到「这个用户 + 这个资源 + 这个动作」三个维度上。""",
                "concepts": """**认证与授权**：认证回答「你是谁」（401），授权回答「你能不能做」（403）。
**角色校验依赖**：`Depends(require_admin)` 挂在路由或 router 上。
**资源级权限**：拿到资源后比较 `owner_id` 与当前用户，不匹配即 403。
**最小权限**：默认拒绝，按需开放；不要用「非管理员都允许」这种反向逻辑。
**越权形态**：改 ID 访问他人资源、批量接口漏过滤、用旧令牌访问已移交资源。""",
                "plain": """认证像进楼刷卡：证明你是这栋楼的人。
授权像进具体房间：你是这栋楼的员工，但不代表能进财务室。
资源级权限更像「这间办公室的钥匙只发给这间屋的主人」——同部门同事也进不去。
所以每次都要问三件事：你是谁、这个资源是谁的、这个动作允许吗。""",
                "syntax": """**API 说明**

```python
def require_role(role: str):
    def checker(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return checker

@app.delete("/tasks/{task_id}", dependencies=[Depends(require_role("admin"))])
def delete_task(task_id: str): ...
```

- 依赖工厂可生成「按角色」的校验器，避免为每个角色写一遍。
- `dependencies=[...]` 挂在装饰器上，表示「进函数前先过关」，返回值不用。
- 资源级判断必须在拿到资源之后做。""",
                "example_code": '''from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException

app = FastAPI(title="权限控制示例")

USERS = {
    "u1": {"id": "u1", "role": "user"},
    "u2": {"id": "u2", "role": "user"},
    "admin": {"id": "admin", "role": "admin"},
}
TASKS = {
    "t1": {"id": "t1", "title": "写周报", "owner": "u1"},
    "t2": {"id": "t2", "title": "交报表", "owner": "u2"},
}


def get_current_user(x_user: Annotated[str | None, Header()] = None) -> dict:
    user = USERS.get(x_user or "")
    if user is None:
        raise HTTPException(status_code=401, detail="未认证")
    return user


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


@app.patch("/tasks/{task_id}")
def update_task(task_id: str, title: str, user: Annotated[dict, Depends(get_current_user)]) -> dict:
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if user["role"] != "admin" and task["owner"] != user["id"]:
        raise HTTPException(status_code=403, detail="只能修改自己的任务")
    task["title"] = title
    return task


@app.delete("/tasks/{task_id}", dependencies=[Depends(require_admin)])
def delete_task(task_id: str) -> dict:
    if TASKS.pop(task_id, None) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"deleted": task_id}''',
                "code_lines": """1. `get_current_user` 负责认证：拿不到用户就是 401。
2. `require_admin` 是授权依赖：已登录但角色不对返回 403，两者语义不能混。
3. `PATCH` 接口先查资源（404），再判断归属（403）——顺序影响错误信息是否泄漏资源存在性。
4. `user["role"] != "admin" and task["owner"] != user["id"]` 表示「管理员或本人」。
5. `dependencies=[Depends(require_admin)]` 挂在装饰器上，删除接口只允许管理员。
6. 装饰器上的依赖不需要在函数签名里接参数，适合「只要过关、不要结果」的场景。
7. 所有判断都在服务端完成，绝不依赖前端隐藏按钮。""",
                "output": """# 本人修改自己的任务
curl -X PATCH "http://127.0.0.1:8000/tasks/t1?title=写月报" -H "x-user: u1"
{"id":"t1","title":"写月报","owner":"u1"}

# 改别人的任务：403
curl -i -X PATCH "http://127.0.0.1:8000/tasks/t2?title=改掉" -H "x-user: u1"
HTTP/1.1 403 Forbidden
{"detail":"只能修改自己的任务"}

# 未带身份：401
curl -i -X PATCH "http://127.0.0.1:8000/tasks/t1?title=x"
HTTP/1.1 401 Unauthorized
{"detail":"未认证"}

# 普通用户删除：403（管理员才能删）
curl -i -X DELETE http://127.0.0.1:8000/tasks/t1 -H "x-user: u1"
HTTP/1.1 403 Forbidden
{"detail":"需要管理员权限"}""",
                "mistakes": """- 用 401 表示「已登录但没权限」，前端会误以为要重新登录。
- 只校验登录不校验归属，任何人改 ID 就能操作别人的数据。
- 列表接口忘了按 `owner_id` 过滤，一次拉出全站数据。
- 把权限判断写在前端（隐藏按钮），直接调接口照样能改。
- 用「非管理员都能访问」的反向逻辑，新增角色时默认获得权限。""",
                "error_analysis": """`403` 出现在管理员账号
—— 角色字段值不一致（如 `role="Admin"` 大小写不同），或当前用户依赖取错了字段。

`401` 但令牌没问题
—— 自定义依赖里读的头名字与前端发送的不一致。

列表接口返回了他人的任务
—— 查询忘了加 `where(Task.owner_id == user["id"])`，权限判断只做在详情接口上。""",
                "beginner_practice": """1. 给 `GET /tasks` 加过滤：普通用户只看到自己的任务，管理员看到全部。
2. 新增「仅创建者可删除」的接口，并用两个账号验证。""",
                "advanced_practice": """设计「团队协作」权限模型：任务属于团队，成员分 owner/member/viewer。
写出权限判断表（动作 × 角色），并说明如何避免「列表接口漏过滤」这类系统性越权。""",
                "quiz_note": "本节 6 道题：2 道基础理解（401 与 403、资源级权限）+ 2 道代码阅读（读判断顺序、读装饰器依赖）+ 2 道应用练习（加过滤、改权限表）。",
                "summary": """认证解决「你是谁」（401），授权解决「能不能做」（403），不要混用。
角色校验做成依赖，资源归属在拿到资源后判断。
权限永远在服务端执行，列表接口必须按归属过滤。""",
                "next_lesson": "下一节收文件：怎么限制大小与类型，怎么防住 `../` 这类路径穿越。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-13-01",
                        "name": "角色与资源级权限",
                        "goal": "能实现角色依赖与资源归属校验，区分 401 与 403。",
                        "minutes": 40,
                        "criteria": "能写出「管理员或本人」的判断，并指出列表接口的过滤盲点。",
                        "requires": ["fastapi-backend-12-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-13-01-1",
                        "kp": 0,
                        "title": "列表按归属过滤",
                        "description": "实现 `GET /tasks`：普通用户只返回自己的任务，管理员返回全部；用 u1、u2、admin 三个身份验证。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''@app.get("/tasks")
def list_tasks(user: Annotated[dict, Depends(get_current_user)]) -> list[dict]:
    items = list(TASKS.values())
    if user["role"] != "admin":
        items = [task for task in items if task["owner"] == user["id"]]
    return items''',
                        "explanation": "过滤放在服务端且默认收紧；管理员走单独分支，避免「忘了加条件」导致越权。",
                    },
                    {
                        "code": "fa-ex-13-01-2",
                        "kp": 0,
                        "title": "401 与 403 的边界",
                        "description": "对「未登录访问」「登录了但删别人的任务」两种情况，分别应返回什么状态码与提示？",
                        "type": "short_answer",
                        "difficulty": "beginner",
                        "answer": '''未登录：401 Unauthorized，提示缺少/无效凭证，前端应跳登录。
已登录但无权限：403 Forbidden，提示权限不足，前端不应跳登录而是提示无权限。
混用会让前端做出错误动作（反复跳登录或误以为已登录）。''',
                        "explanation": "状态码是契约的一部分，前端据此决定交互，不能随手写。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-13-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "已登录用户尝试删除他人的任务，应返回？",
                        "options": [("A", "401"), ("B", "403"), ("C", "404"), ("D", "409")],
                        "answer": {"value": "B"},
                        "explanation": "身份已确认（非 401），但没有该动作的权限，属于授权失败，用 403。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-13-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "可能导致越权访问的写法有？（多选）",
                        "options": [
                            ("A", "列表接口不按归属过滤"),
                            ("B", "详情接口只校验登录不校验归属"),
                            ("C", "权限判断只写在前端"),
                            ("D", "用依赖统一校验角色"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "依赖统一校验是正确的做法，D 不是问题。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-13-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "u1 请求 `PATCH /tasks/t2?title=x` 的结果是？",
                        "options": [("A", "200 并修改成功"), ("B", "403"), ("C", "404"), ("D", "401")],
                        "answer": {"value": "B"},
                        "explanation": "t2 属于 u2，u1 非管理员，走到归属判断返回 403。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-13-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`dependencies=[Depends(require_admin)]` 的依赖结果会自动注入函数参数。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "装饰器上的依赖只做校验，结果不注入；要拿结果需在函数签名里声明该依赖。",
                        "difficulty": "intermediate",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-13-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全判断，使「管理员或本人」才能继续。横线处应填什么？\n\n```python\nif user[\"role\"] != \"admin\" ____ task[\"owner\"] != user[\"id\"]:\n    raise HTTPException(status_code=403, detail=\"只能修改自己的任务\")\n```",
                        "options": [("A", "and"), ("B", "or"), ("C", "not"), ("D", "in")],
                        "answer": {"value": "A"},
                        "explanation": "两个条件同时成立才拒绝：不是管理员「且」不是本人。用 or 会把管理员也拦住。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-13-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么列表接口比详情接口更容易漏权限？怎么系统性地避免？",
                        "answer": {"value": "列表接口返回多条数据，权限条件要写进查询的 where 里，容易漏；详情接口只需判断单个对象，漏了也更容易在测试中被发现。系统性做法：① 把「当前用户可见范围」封装成仓储层方法（如 `list_for_user`），业务代码不允许直接调用全量查询；② 测试里固定建两个用户的数据，断言各自只能看到自己的；③ 代码评审把「是否带归属条件」列为必查项。"},
                        "explanation": "核心是「用一个统一入口限制可见范围」，而不是靠每处记得写条件。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-13-lesson-02",
                "objectives": """1. 会用 `UploadFile` 接收上传并正确读取；
2. 能限制文件大小与类型，返回合适的状态码；
3. 能防止路径穿越与覆盖已有文件；
4. 知道大文件为什么要流式处理。""",
                "why_learn": """上传接口是最容易被滥用的入口：有人传 2GB 文件打满磁盘，有人传 `.php` 或 `../config` 试图越界写入。
这些都不是「理论上可能」，而是扫描器每天在试的事情。""",
                "concepts": """**UploadFile**：带文件名的类文件对象，提供 `read/seek/close` 与 `filename/content_type`。
**依赖**：使用表单上传需要安装 `python-multipart`。
**大小限制**：读入后判断长度，或分块累计；超限返回 413。
**类型校验**：`content_type` 只是客户端声明，必要时校验文件头。
**路径安全**：用 `Path(filename).name` 去掉目录部分，目标目录固定，绝不拼接用户输入。""",
                "plain": """上传接口像公司前台收快递：可以收，但要看清「多大、什么品类、寄给谁」。
大小限制是别让一个人把仓库堆满；类型校验是别收危险品；文件名清洗是别让快递单上写「放到财务室保险柜里」这种地址。
这三件事少了任何一件，前台就成了漏洞。""",
                "syntax": """**API 说明**

```python
from fastapi import File, UploadFile

@app.post("/files")
async def upload(file: Annotated[UploadFile, File()]) -> dict: ...
```

- `file.filename` 是客户端提供的名字，不可信。
- `await file.read()` 一次读全量；大文件应 `while chunk := await file.read(64 * 1024)`。
- 超限用 413，类型不支持用 415，都是语义更准的状态码。
- 需要 `pip install python-multipart` 才能解析表单。""",
                "example_code": '''from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

app = FastAPI(title="文件上传示例")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_SIZE = 1_000_000
ALLOWED_TYPES = {"image/png", "image/jpeg", "text/plain"}


@app.post("/files")
async def upload_file(file: Annotated[UploadFile, File()]) -> dict:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=f"不支持的类型：{file.content_type}")

    size = 0
    chunks: list[bytes] = []
    while chunk := await file.read(64 * 1024):
        size += len(chunk)
        if size > MAX_SIZE:
            raise HTTPException(status_code=413, detail="文件超过 1MB 限制")
        chunks.append(chunk)

    safe_name = Path(file.filename or "unnamed").name
    target = (UPLOAD_DIR / safe_name).resolve()
    if UPLOAD_DIR.resolve() not in target.parents:
        raise HTTPException(status_code=400, detail="非法文件名")
    target.write_bytes(b"".join(chunks))
    return {"name": safe_name, "size": size, "content_type": file.content_type}''',
                "code_lines": """1. `Path("uploads").mkdir(exist_ok=True)` 保证目录存在，重复启动不报错。
2. `file.content_type` 来自客户端，先做白名单过滤，别直接信任。
3. `while chunk := await file.read(64 * 1024)` 分块读取，边读边累计大小。
4. 超过上限立刻 413，避免把整个大文件读进内存。
5. `Path(file.filename).name` 只保留最后一段，`../etc/passwd` 会变成 `passwd`。
6. `resolve()` 后再判断目标是否在 `UPLOAD_DIR` 之内，挡住符号链接与残留路径。
7. 写盘用固定目录 + 清洗后的名字，绝不直接拼接用户输入。""",
                "output": """# 正常上传
curl -F "file=@notes.txt;type=text/plain" http://127.0.0.1:8000/files
{"name":"notes.txt","size":128,"content_type":"text/plain"}

# 类型不允许
curl -i -F "file=@run.exe" http://127.0.0.1:8000/files
HTTP/1.1 415 Unsupported Media Type
{"detail":"不支持的类型：application/octet-stream"}

# 超过大小
curl -i -F "file=@big.bin" http://127.0.0.1:8000/files
HTTP/1.1 413 Request Entity Too Large
{"detail":"文件超过 1MB 限制"}

# 路径穿越尝试会被清洗
文件名 ../../etc/passwd  ->  实际写入 uploads/passwd""",
                "mistakes": """- 直接用 `file.filename` 拼路径，`../` 可写到任意目录。
- 一次 `await file.read()` 读全量，大文件直接把内存打满。
- 只看 `content_type` 就当安全，攻击者可伪造。
- 同名文件直接覆盖，导致用户互相覆盖数据。
- 上传目录可执行或在 Web 根目录下，被上传脚本后门。""",
                "error_analysis": """`AssertionError: The `python-multipart` library must be installed to use form data`
—— 缺依赖。`pip install python-multipart`。

`413` 但文件明明很小
—— 反向代理（Nginx `client_max_body_size`）先拦了，需要同时调整代理配置。

文件名变成乱码
—— 客户端与服务器编码不一致。保存时统一用 ASCII 安全名 + 记录原名的映射。""",
                "beginner_practice": """1. 把大小限制改成 200KB，验证 413。
2. 上传同名文件两次，改成「自动加序号」而不是覆盖。""",
                "advanced_practice": """设计大文件上传方案：支持 500MB 文件、断点续传与秒传。
说明分片、合并、去重（内容哈希）分别怎么做，以及为什么不能把整个文件读进内存。""",
                "quiz_note": "本节 6 道题：2 道基础理解（大小/类型限制、路径安全）+ 2 道代码阅读（读分块读取、读 413/415）+ 2 道应用练习（改限制、防覆盖）。",
                "summary": """`UploadFile` 提供文件名与流式读取，表单上传需要 `python-multipart`。
大小超限用 413、类型不支持用 415，且要分块累计而不是一次读全量。
文件名必须清洗（`Path(name).name`），落盘目录固定且不可执行。""",
                "next_lesson": "下一节把文档整理好：标题、分组、示例与错误码都写进 OpenAPI。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-13-02",
                        "name": "文件上传与安全校验",
                        "goal": "能实现带大小与类型限制、且防路径穿越的上传接口。",
                        "minutes": 40,
                        "criteria": "能写出分块读取的上传接口，并解释为什么要清洗文件名。",
                        "requires": ["fastapi-backend-13-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-13-02-1",
                        "kp": 0,
                        "title": "防覆盖与防穿越",
                        "description": "改造上传接口：同名文件自动加时间戳后缀，并拒绝解析后落在上传目录之外的文件名。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''import time

safe_name = Path(file.filename or "unnamed").name
target = (UPLOAD_DIR / safe_name).resolve()
if target.parent != UPLOAD_DIR.resolve():
    raise HTTPException(status_code=400, detail="非法文件名")
if target.exists():
    target = target.with_name(f"{target.stem}-{int(time.time())}{target.suffix}")''',
                        "explanation": "`Path.name` 去掉目录、`resolve` 后再比对父目录，两层防护才挡得住畸形文件名。",
                    },
                    {
                        "code": "fa-ex-13-02-2",
                        "kp": 0,
                        "title": "为什么不用一次 read()",
                        "description": "说明 `content = await file.read()` 在 500MB 文件上的问题，并给出替代写法。",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''一次 read() 会把整个文件读进内存，500MB 会直接吃掉同等内存，并发几个请求就可能 OOM。
替代：按 64KB 分块读取，边读边写临时文件/对象存储，并累计大小提前拒绝超限文件。''',
                        "explanation": "核心是「内存占用与文件大小线性相关」，流式处理让内存占用变成常量。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-13-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "处理上传时，哪个字段最不可信？",
                        "options": [("A", "file.filename"), ("B", "服务器生成的 uuid"), ("C", "代码里写死的目录"), ("D", "配置项 MAX_SIZE")],
                        "answer": {"value": "A"},
                        "explanation": "文件名完全由客户端提供，可能含路径穿越字符或特殊扩展名，必须清洗。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-13-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "上传接口应具备的保护有？（多选）",
                        "options": [
                            ("A", "限制文件大小"),
                            ("B", "校验内容类型"),
                            ("C", "清洗文件名"),
                            ("D", "把上传目录放在 Web 根目录并允许执行"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "D 会让上传的文件被当作脚本执行，是典型的提权入口。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-13-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "客户端传 `../../etc/passwd` 时，`Path(file.filename).name` 得到什么？",
                        "options": [("A", "../../etc/passwd"), ("B", "passwd"), ("C", "etc"), ("D", "报错")],
                        "answer": {"value": "B"},
                        "explanation": "`.name` 只保留最后一段，目录部分被丢弃——这是第一层防护。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-13-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "只要 `content_type` 是 `image/png`，就可以确定文件真的是 PNG。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "`content_type` 由客户端声明，可任意伪造；需要读文件头（magic bytes）校验真实格式。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-13-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全分块读取循环。横线处应填什么？\n\n```python\nwhile chunk := ____:\n    size += len(chunk)\n```",
                        "options": [
                            ("A", "await file.read(64 * 1024)"),
                            ("B", "file.read(64 * 1024)"),
                            ("C", "await file.read()"),
                            ("D", "file.content"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`UploadFile.read` 是协程，必须 await；不传参数会一次读完整个文件。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-13-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "为什么上传目录不能放在 Web 可直接访问的路径下？",
                        "answer": {"value": "上传内容本质上是「用户可控的字节」，一旦能被直接访问且可执行（如 .php/.jsp/.py），攻击者就能上传后门脚本并通过 URL 触发执行，等于拿到服务器权限。正确做法：文件存到 Web 根之外或对象存储，通过受控接口鉴权后下载，并对下载响应设置 `Content-Disposition: attachment` 与正确的 `Content-Type`。"},
                        "explanation": "要点是「用户可控内容 + 可执行 + 可直接访问」三者叠加才致命，解法是移出可执行范围。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
    {
        "code": "fastapi-backend-14",
        "title": "API 文档与接口测试",
        "description": "文档自动生成不等于不用管，测试才是回归的底气。",
        "order_index": 14,
        "lessons": [
            {
                "code": "fastapi-backend-14-lesson-01",
                "objectives": """1. 会用 `tags_metadata`、`summary`、`description` 组织文档；
2. 会用 `responses` 声明错误响应示例；
3. 会用 `deprecated` 标记待下线接口；
4. 知道文档该写什么、不该写什么。""",
                "why_learn": """FastAPI 自动生成的文档只有「字段名 + 类型」，调用方仍然不知道「这个接口什么时候用、失败了怎么办」。
把这些补上，能省掉大量「接口怎么调」的沟通；而文档一旦与代码脱节，比没文档更糟。""",
                "concepts": """**tags_metadata**：给分组加说明，文档页小组件更清晰。
**summary 与 description**：前者一行短标题，后者可写背景与注意事项。
**responses**：按状态码声明响应模型与示例，错误也能出现在文档里。
**deprecated**：标记接口即将下线，文档会显示删除线。
**文档与代码同源**：所有信息来自代码，不维护第二份文档。""",
                "plain": """自动文档像自动生成的菜单：只列了菜名和价格。
你补的 `description` 是「这道菜偏辣、需等 20 分钟」；`responses` 是「卖完了会怎么提示」。
这些补充信息不写进代码，自动菜单就永远不会显示——所以文档质量取决于你写了多少。""",
                "syntax": """**API 说明**

```python
app = FastAPI(
    title="任务管理 API",
    version="1.0.0",
    openapi_tags=[{"name": "tasks", "description": "任务的增删改查"}],
)

@app.post(
    "/tasks",
    tags=["tasks"],
    summary="创建任务",
    description="标题必填，长度 1—50；创建成功后返回任务 ID。",
    responses={409: {"description": "标题已存在"}},
)
def create_task(...): ...
```

- `responses` 的 key 是状态码，值是描述与可选模型/示例。
- `deprecated=True` 即可标记下线中。""",
                "example_code": '''from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="任务管理 API",
    version="1.0.0",
    description="小码教学示例：演示如何把文档写好。",
    openapi_tags=[
        {"name": "tasks", "description": "任务的增删改查"},
        {"name": "system", "description": "健康检查等系统接口"},
    ],
)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50, examples=["写周报"])


class TaskOut(BaseModel):
    id: int
    title: str


TASKS: dict[int, dict] = {}


@app.get("/health", tags=["system"], summary="健康检查")
def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    tags=["tasks"],
    summary="创建任务",
    description="标题长度 1—50 个字符；重复标题返回 409。",
    responses={409: {"description": "标题已存在"}},
)
def create_task(payload: TaskCreate) -> dict:
    if any(task["title"] == payload.title for task in TASKS.values()):
        raise HTTPException(status_code=409, detail="标题已存在")
    task_id = len(TASKS) + 1
    TASKS[task_id] = {"id": task_id, "title": payload.title}
    return TASKS[task_id]


@app.get("/tasks/legacy", tags=["tasks"], deprecated=True, summary="旧版列表（即将下线）")
def legacy_list() -> list[dict]:
    return list(TASKS.values())''',
                "code_lines": """1. `openapi_tags` 给每个 tag 写说明，文档页分组处会显示这段文字。
2. `title/description/version` 出现在文档页顶部，是调用方第一眼看到的信息。
3. `Field(..., examples=[...])` 让请求体示例不是空的占位结构。
4. `summary` 是短标题，`description` 写约束与注意事项，两者分工不同。
5. `responses={409: {...}}` 把错误也写进文档，调用方知道要处理哪些状态码。
6. `deprecated=True` 会让接口显示删除线，提示调用方迁移。
7. 所有文档信息都来自代码，不需要额外维护一份 Markdown。""",
                "output": """# 请求与响应（同一接口的两种视角）
curl -i -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"写周报"}'
HTTP/1.1 201 Created
{"id":1,"title":"写周报"}

curl -i -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"写周报"}'
HTTP/1.1 409 Conflict
{"detail":"标题已存在"}

# 打开 /docs 可见
任务管理 API  v1.0.0
小码教学示例：演示如何把文档写好。

system
  GET /health  健康检查
tasks
  POST /tasks  创建任务
    标题长度 1—50 个字符；重复标题返回 409。
    Responses: 201 成功、409 标题已存在、422 参数校验失败
  GET /tasks/legacy  旧版列表（即将下线）  ← 显示删除线

# openapi.json 片段
{"paths":{"/tasks":{"post":{"summary":"创建任务","deprecated":false,
"responses":{"201":{...},"409":{"description":"标题已存在"}}}}}""",
                "mistakes": """- 只写 `summary` 不写 `description`，调用方仍不知道约束。
- 错误码不写进 `responses`，文档里只有 200 一种响应。
- 文档手工维护一份 Markdown，几周后就与代码不一致。
- 把内部实现细节（表名、内部服务地址）写进描述。
- 接口已废弃却直接删掉，调用方毫无预警。""",
                "error_analysis": """`/docs` 空白或加载失败
—— 常见是跨域或静态资源被代理拦了；先看浏览器控制台与 `openapi.json` 是否能直接访问。

文档里没有新增接口
—— 路由写在未 include 的 router 上，或应用实例不是被启动的那个。

文档与实际不符
—— 手工改了 schema 或用了旧缓存。FastAPI 的文档是运行时生成的，不符通常意味着有中间层缓存了 openapi.json。""",
                "beginner_practice": """1. 给 `GET /health` 加 `description`，说明它被容器探针调用。
2. 给创建接口补 `responses={422: ...}`，在 /docs 里确认能看到。""",
                "advanced_practice": """为一个已有接口补全文档：一句话摘要、使用场景、参数约束、所有可能的错误码与处理建议。
说明为什么「错误码」比「字段说明」更值得写。""",
                "quiz_note": "本节 6 道题：2 道基础理解（文档来源、responses 作用）+ 2 道代码阅读（读配置、读 deprecated）+ 2 道应用练习（补文档、补错误码）。",
                "summary": """文档质量取决于你写了多少：`summary` 一句话、`description` 写约束。
错误响应通过 `responses` 声明，调用方才知道要处理哪些状态码。
文档与代码同源，废弃接口用 `deprecated` 标记而不是直接删除。""",
                "next_lesson": "下一节写测试：用 TestClient 把「能跑通」变成「能回归」。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-14-01",
                        "name": "OpenAPI 元数据与文档定制",
                        "goal": "能把摘要、约束与错误码写进自动文档。",
                        "minutes": 30,
                        "criteria": "能让 /docs 清楚表达一个接口的用途、约束与失败情形。",
                        "requires": ["fastapi-backend-13-02"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-14-01-1",
                        "kp": 0,
                        "title": "给接口补全文档",
                        "description": "给「删除任务」接口补 summary、description、responses（404/403/204），并说明每项在 /docs 里显示在哪。",
                        "type": "coding",
                        "difficulty": "beginner",
                        "answer": '''@app.delete(
    "/tasks/{task_id}",
    status_code=204,
    tags=["tasks"],
    summary="删除任务",
    description="仅创建者或管理员可删除；成功返回 204，无响应体。",
    responses={403: {"description": "无权限"}, 404: {"description": "任务不存在"}},
)
def delete_task(task_id: int) -> None: ...''',
                        "explanation": "summary 显示为接口标题，description 显示在展开区，responses 显示在 Responses 列表。",
                    },
                    {
                        "code": "fa-ex-14-01-2",
                        "kp": 0,
                        "title": "错误码为什么更值得写",
                        "description": "从调用方视角说明：字段说明与错误码，哪个对集成更有价值？",
                        "type": "short_answer",
                        "difficulty": "intermediate",
                        "answer": '''字段说明决定「怎么填对」，错误码决定「填错或失败时怎么办」。
集成阶段真正耗时的是异常分支：409 要不要重试、403 是提示还是跳登录、429 要不要退避。
字段能从类型与校验信息推断，错误码无法推断，因此更值得写进 responses。''',
                        "explanation": "这是文档投入产出比的判断：调用方最缺的是失败路径的信息。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-14-01-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`/docs` 的内容来自哪里？",
                        "options": [
                            ("A", "运行时根据代码与类型注解生成的 OpenAPI 描述"),
                            ("B", "项目里手工维护的 openapi.json 文件"),
                            ("C", "数据库中的接口表"),
                            ("D", "README 中的表格"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "FastAPI 在启动时根据路由、模型与装饰器参数生成 OpenAPI，再渲染成文档页。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-14-01-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "下列能提升文档质量的做法有？（多选）",
                        "options": [
                            ("A", "openapi_tags 给分组写说明"),
                            ("B", "responses 声明错误码"),
                            ("C", "deprecated 标记待下线接口"),
                            ("D", "把内部数据库表名写进 description"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "内部实现细节不应出现在对外文档中，D 反而降低质量并增加泄漏风险。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-14-01-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中重复创建同名任务返回什么？",
                        "options": [("A", "200 并覆盖"), ("B", "409"), ("C", "422"), ("D", "500")],
                        "answer": {"value": "B"},
                        "explanation": "代码里显式判断标题重复并抛 409，同时该状态码已写进 `responses`。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-14-01-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "`summary` 与 `description` 可以互换使用，效果一样。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "`summary` 是列表里的一行标题，`description` 是展开后的详细说明，长度与用途都不同。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-14-01-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全装饰器参数，使接口在文档中显示为「即将下线」。横线处应填什么？\n\n```python\n@app.get(\"/tasks/legacy\", ____)\ndef legacy_list(): ...\n```",
                        "options": [
                            ("A", "deprecated=True"),
                            ("B", "deprecated=\"yes\""),
                            ("C", "hidden=True"),
                            ("D", "status=410"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "`deprecated` 接收布尔值；`hidden=True` 会直接把接口从文档里藏起来，而不是标记下线。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-14-01-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "接口要下线，除了加 `deprecated`，还应该做哪些事？",
                        "answer": {"value": "① 在 description 与响应里注明迁移目标与下线时间；② 记录调用量（按调用方/UA 统计），确认无人使用后再删；③ 对仍在调用的客户端返回提示头（如 `Deprecation`、`Sunset`）；④ 提前通知调用方并给迁移窗口；⑤ 保留一段时间只读或返回 410，而不是直接 404，避免调用方误判为路径写错。"},
                        "explanation": "要点是「可观测 + 提前告知 + 渐进下线」，直接删除会让调用方无法区分故障与下线。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                ],
            },
            {
                "code": "fastapi-backend-14-lesson-02",
                "objectives": """1. 会用 `TestClient` 发起请求并断言状态码与响应体；
2. 会用 pytest fixture 准备独立测试数据；
3. 会用 `dependency_overrides` 替换数据库依赖；
4. 能为核心路径写出可回归的用例。""",
                "why_learn": """手工 curl 验证一次就忘，改代码后没人知道有没有弄坏别的接口。
测试把「我知道它能跑」变成「任何人改完都能一键确认」——这是接口数量上来后唯一的可行方式。""",
                "concepts": """**TestClient**：基于 httpx 的测试客户端，直接调用 ASGI 应用，不用起真实端口。
**fixture**：pytest 的准备工作，可为每个用例提供独立的客户端与数据。
**dependency_overrides**：把真实依赖（如数据库会话）换成测试实现。
**断言三件套**：状态码、响应结构、副作用（如再查一次确认真被删除）。
**隔离**：内存库 + 每用例建表删表，避免顺序依赖。""",
                "plain": """测试像出厂前的通电检查：不用真把电器卖出去，也能确认开关、指示灯、保护装置都正常。
`TestClient` 是插头，直接接到应用上；fixture 是每次检查前把台面清空；override 是把真电源换成安全的模拟电源。
三者配合，测试才既能跑得快，又不会污染你的真实数据。""",
                "syntax": """**API 说明**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200

app.dependency_overrides[get_session] = override_get_session
```

- 用法与 `requests` 类似：`client.get/post/patch/delete`，可传 `json=`、`headers=`。
- `dependency_overrides` 要在用例结束或 fixture 收尾时清空。
- 断言失败时打印 `resp.text` 能快速看到后端返回。""",
                "example_code": '''from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

app = FastAPI(title="接口测试示例")

STORE: dict[int, dict] = {}


def get_store() -> Iterator[dict]:
    STORE.clear()
    try:
        yield STORE
    finally:
        STORE.clear()


@app.post("/tasks", status_code=201)
def create_task(payload: dict, store: Annotated[dict, Depends(get_store)]) -> dict:
    task_id = len(store) + 1
    store[task_id] = {"id": task_id, "title": payload["title"]}
    return store[task_id]


@app.get("/tasks/{task_id}")
def get_task(task_id: int, store: Annotated[dict, Depends(get_store)]) -> dict:
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


client = TestClient(app)


def test_create_and_get() -> None:
    created = client.post("/tasks", json={"title": "写周报"})
    assert created.status_code == 201
    assert created.json()["title"] == "写周报"

    task_id = created.json()["id"]
    fetched = client.get(f"/tasks/{task_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == task_id


def test_missing_task_returns_404() -> None:
    resp = client.get("/tasks/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "任务不存在"


def test_create_requires_title() -> None:
    resp = client.post("/tasks", json={})
    assert resp.status_code == 500 or resp.status_code == 422''',
                "code_lines": """1. `get_store` 依赖在每个用例开始时清空数据，保证用例之间互不影响。
2. 接口用依赖拿「存储」，测试里就能整体替换成内存实现。
3. `TestClient(app)` 直接测 ASGI 应用，不需要启动 uvicorn 或占用端口。
4. `client.post(..., json=...)` 会带上 `Content-Type: application/json`。
5. 断言分两步：状态码与关键字段，避免「只断言 200」导致结构错误漏掉。
6. 「创建后再查」验证的是副作用，比只看响应体更接近真实使用。
7. 第三条用例演示反面教材：用 `dict` 收请求体时缺字段会 500，正解是用 Pydantic 模型得到 422。""",
                "output": """# 请求与响应
curl -X POST http://127.0.0.1:8000/tasks -H "Content-Type: application/json" -d '{"title":"写周报"}'
{"id":1,"title":"写周报"}

curl -i http://127.0.0.1:8000/tasks/999
HTTP/1.1 404 Not Found
{"detail":"任务不存在"}

# 测试输出
$ pytest -q
...                                                                      [100%]
3 passed in 0.42s

# 断言失败时的输出示例
$ pytest -q
E   assert 404 == 200
E    +  where 404 = <Response [404 Unprocessable Entity]>.status_code
E   响应体: {"detail":"任务不存在"}

# 用 -k 只跑某个用例
$ pytest -q -k missing
1 passed, 2 deselected in 0.31s""",
                "mistakes": """- 测试共用全局数据，用例顺序一变就失败。
- 只断言状态码，响应结构改了也发现不了。
- 直接用生产/开发数据库跑测试，把数据写脏。
- 改了 `dependency_overrides` 却没清理，影响后续用例。
- 用 `time.sleep` 等待异步结果，测试又慢又不稳。""",
                "error_analysis": """`TypeError: TestClient(...) takes no arguments`
—— 导入错了：应为 `fastapi.testclient.TestClient`，不是 httpx 的同名类。

`RuntimeError: Event loop is closed`
—— 在用例里混用了同步与异步客户端；统一用一种，或改用 `httpx.AsyncClient` + `pytest-asyncio`。

用例偶发失败、单独跑却通过
—— 数据没隔离。检查 fixture 是否每个用例都重置状态。""",
                "beginner_practice": """1. 给示例加一条「重复创建同名任务应 409」的用例（先补业务判断）。
2. 用 `pytest -k` 只跑 404 那条，确认能单独通过。""",
                "advanced_practice": """为一个带数据库的项目设计测试方案：用内存 SQLite、每用例建表、用 `dependency_overrides` 替换会话。
说明如何保证测试之间完全隔离，以及为什么不该用「测试完删表」的方式。""",
                "quiz_note": "本节 6 道题：2 道基础理解（TestClient 作用、隔离意义）+ 2 道代码阅读（读断言、读依赖替换）+ 2 道应用练习（补用例、设计 fixture）。",
                "summary": """`TestClient` 直接调用 ASGI 应用，不起端口也能测。
断言要覆盖状态码、响应结构与副作用，只测 200 等于没测。
用 fixture 与依赖替换保证隔离，测试绝不能碰真实数据。""",
                "next_lesson": "下一节收尾：日志、配置与部署，把服务真正跑在生产环境。",
                "knowledge_points": [
                    {
                        "code": "fastapi-backend-14-02",
                        "name": "pytest、TestClient 与测试隔离",
                        "goal": "能用 TestClient 与 fixture 写出可回归的接口测试。",
                        "minutes": 60,
                        "criteria": "能写出覆盖成功、404、校验失败的三个用例，且用例之间互不影响。",
                        "requires": ["fastapi-backend-14-01"],
                    }
                ],
                "practice": [
                    {
                        "code": "fa-ex-14-02-1",
                        "kp": 0,
                        "title": "补一条 409 用例",
                        "description": "先给创建接口加「标题重复返回 409」，再写测试断言第二次创建返回 409 且响应体含提示。",
                        "type": "coding",
                        "difficulty": "intermediate",
                        "answer": '''def test_duplicate_title_returns_409() -> None:
    client.post("/tasks", json={"title": "写周报"})
    resp = client.post("/tasks", json={"title": "写周报"})
    assert resp.status_code == 409
    assert "已存在" in resp.json()["detail"]''',
                        "explanation": "用例要能独立通过：第一个请求自己创建数据，不依赖其它用例的准备结果。",
                    },
                    {
                        "code": "fa-ex-14-02-2",
                        "kp": 0,
                        "title": "替换数据库依赖",
                        "description": "写出用 `dependency_overrides` 把会话依赖换成内存库的 fixture，并说明为什么要在 teardown 里清理。",
                        "type": "short_answer",
                        "difficulty": "advanced",
                        "answer": '''@pytest.fixture
def client():
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

不清理会让后面的用例继续用测试依赖，甚至在别的测试文件里造成「莫名连的是内存库」。''',
                        "explanation": "override 是全局字典，必须显式清理；用 fixture 的 yield + clear 能保证即使用例失败也会复原。",
                    },
                ],
                "questions": [
                    {
                        "code": "q-fa-14-02-1",
                        "kp": 0,
                        "type": "single_choice",
                        "stem": "`TestClient` 的主要优势是？",
                        "options": [
                            ("A", "直接调用 ASGI 应用，不需要启动真实服务器"),
                            ("B", "能自动生成测试用例"),
                            ("C", "能替代数据库"),
                            ("D", "自动修复失败的接口"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "它在进程内调用应用，速度快且不占端口，适合接口级回归测试。",
                        "difficulty": "beginner",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-14-02-2",
                        "kp": 0,
                        "type": "multiple_choice",
                        "stem": "一条好的接口用例通常断言哪些内容？（多选）",
                        "options": [
                            ("A", "状态码"),
                            ("B", "响应关键字段"),
                            ("C", "副作用（如数据真的被删除）"),
                            ("D", "函数内部变量的值"),
                        ],
                        "answer": {"values": ["A", "B", "C"]},
                        "explanation": "测试应基于可观察行为；断言内部实现细节会让重构寸步难行。",
                        "difficulty": "intermediate",
                        "category": "基础理解",
                    },
                    {
                        "code": "q-fa-14-02-3",
                        "kp": 0,
                        "type": "code_analysis",
                        "stem": "示例中 `test_missing_task_returns_404` 断言了什么？",
                        "options": [
                            ("A", "状态码 404 与 detail 内容"),
                            ("B", "只断言状态码"),
                            ("C", "只断言响应体"),
                            ("D", "断言数据库记录数"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "两个断言分别覆盖状态码与错误信息，避免只测一半。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-14-02-4",
                        "kp": 0,
                        "type": "true_false",
                        "stem": "测试可以直接连开发数据库，只要最后手工清一下数据即可。",
                        "options": [("A", "正确"), ("B", "错误")],
                        "answer": {"value": "B"},
                        "explanation": "测试必须是可重复、可无人值守执行的，手工清理既不可靠也会污染数据，应使用独立测试库或依赖替换。",
                        "difficulty": "beginner",
                        "category": "代码阅读",
                    },
                    {
                        "code": "q-fa-14-02-5",
                        "kp": 0,
                        "type": "code_writing",
                        "stem": "补全依赖替换语句。横线处应填什么？\n\n```python\napp.____[get_session] = override_get_session\n```",
                        "options": [
                            ("A", "dependency_overrides"),
                            ("B", "dependencies"),
                            ("C", "override_map"),
                            ("D", "injections"),
                        ],
                        "answer": {"value": "A"},
                        "explanation": "FastAPI 提供的是 `dependency_overrides` 字典，键是原依赖函数。",
                        "difficulty": "intermediate",
                        "category": "应用练习",
                    },
                    {
                        "code": "q-fa-14-02-6",
                        "kp": 0,
                        "type": "short_answer",
                        "stem": "用例单独跑通过、整套跑失败，通常是什么原因？怎么修？",
                        "answer": {"value": "测试之间不隔离：共享了全局状态（模块级字典、同一数据库、未清理的 dependency_overrides），前一个用例留下的数据影响了后一个。修法：每个用例用 fixture 重置状态（清空数据、重建内存库、清理 overrides），并避免用例间有顺序依赖；必要时用 `-p no:randomly` 或固定顺序复现问题。"},
                        "explanation": "「单独通过、批量失败」是隔离问题的典型特征，排查从全局可变状态入手。",
                        "difficulty": "advanced",
                        "category": "应用练习",
                    },
                ],
            },
        ],
    },
]
