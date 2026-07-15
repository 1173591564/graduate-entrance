# Graduate Entrance

11408 备考系统，面向数学一、408、英语一和政治的任务规划、进度追踪、题库复习与学习分析。

## 工程状态

仓库当前提供完整的可运行工程骨架，并已进入首个 P0 业务纵切片：

- FastAPI、SQLAlchemy、Alembic 与 PostgreSQL/pgvector 后端基线；
- Vue 3、Vite、TypeScript Web 管理端；
- Kotlin、Jetpack Compose、Room/Retrofit Android 基线；
- Docker Compose、Caddy、健康检查和本地环境模板；
- 后端、Web、Android 与基础设施 CI。
- 单用户 Bearer token、统一错误响应、请求日志与 OpenAPI 类型生成。
- 643 条原始考纲的幂等导入、五级考纲树 API 与 Web 只读浏览。
- 阶段与四科配比、Availability、资料库和任务模板的配置 API 与 Web 页面。

## 快速启动

```bash
cp .env.example .env
docker compose up --build
```

- Web：`http://localhost:8080`
- API 文档：`http://localhost:8000/api/docs`
- 考纲树：`http://localhost:8080/syllabus`
- 规划配置：`http://localhost:8080/planning`

## 仓库结构

```text
backend/          FastAPI 服务
web/              Vue Web 应用
android/          Android 应用
infra/            数据库初始化
seed/             版本化考纲源数据
docs/             架构、开发、部署与产品资料
```

详细命令见 [开发文档](docs/development.md)，系统边界见
[架构文档](docs/architecture.md)，协作规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 后续顺序

后续按“任务池 → 确定性排程 → 日历与今日任务 → 打卡与顺延”推进，再扩展题库、
SM-2、AI/RAG 和离线同步。

## 安全

仓库不得提交服务器密码、API Key、Token、`.env`、数据库备份或用户上传文件。
