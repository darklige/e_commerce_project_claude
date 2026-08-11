# JD-Clone 电商平台项目

> 一个复刻京东（JD.com）业务生态的大规模全栈电商项目
> 覆盖 用户 Web / Android App / 商家后台 / 管理员后台 四端 + FastAPI 后端

**当前版本**：`v1.0.0` · Phase 0-7 全部交付完成 · 详见 [CHANGELOG](docs/CHANGELOG.md)

## 项目文档索引

| 文档 | 用途 |
|---|---|
| [`docs/DEVELOPMENT_PLAN.md`](docs/DEVELOPMENT_PLAN.md) | 开发规划流程 — 项目愿景、业务范围、技术选型、Phase 划分、验收标准 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 系统架构 — 分层图 · 状态机 · 认证时序 · 部署拓扑 · 关键设计决策 |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | 贡献指南 — 分支策略 · 本地开发 · 跑测试 · 数据库迁移 · 代码风格 |
| [`docs/API/INDEX.md`](docs/API/INDEX.md) | API 契约索引 — Phase 1-6 契约文档 |
| [`docs/SECURITY_AUDIT.md`](docs/SECURITY_AUDIT.md) | Phase 7 安全审查报告 |
| [`docs/CHANGELOG.md`](docs/CHANGELOG.md) | 变更日志（每 Phase） |
| [`AGENTS.md`](AGENTS.md) | 多智能体协作与开发规范 — Git 工作流、Agent 分工、Skills 清单 |

## 项目核心理念

> **做深做透，而非做多做浅**

- 不追求功能数量，而追求每个业务模块的**真实深度**
- 每个功能都要覆盖：**正常流程 + 异常流程 + 三方角色（用户/商家/管理员）联动**
- 可选模块（如支付）可简化模拟；一旦决定实现的模块，必须扎实

## 里程碑（Git Tags）

| Tag | Phase | 主题 | 交付时间 |
|---|---|---|---|
| `v0.1.0-phase0` | Phase 0 | 项目筹备 · monorepo 骨架 · Docker Compose · CI/CD | 2026-07-22 |
| `v0.2.0-phase1` | Phase 1 | 认证 + RBAC + 商家入驻 · 三端 auth UI | 2026-07-22 |
| `v0.3.0-phase2` | Phase 2 | 商品目录 · SPU/SKU · MinIO 图片上传 · 上架审核 | 2026-07-23 |
| `v0.4.0-phase3` | Phase 3 | 交易核心 · 购物车 · 订单 6 态 · 支付/物流模拟 · 超时任务 | 2026-07-23 |
| `v0.5.0-phase4` | Phase 4 | 售后闭环 · 12 态状态机 · 三方联动 · 平台仲裁 · 超时升级 | 2026-07-24 |
| `v0.6.0-phase5` | Phase 5 | 评价 · 站内信 · 3 级地区 · 商家店铺主页 | 2026-07-24 |
| `v0.7.0-phase6` | Phase 6 | Android 消费者端 · 对接 Phase 1-5 后端 | 2026-07-24 |
| `v0.8.0-phase7` | Phase 7 | 打磨 · 测试 · 安全审查 · 文档终稿 | 2026-07-24 |
| **`v1.0.0`** | — | **项目主版本发布** | 2026-07-24 |

## 技术栈概览

| 端 | 技术 |
|---|---|
| 后端 | FastAPI 0.115 + SQLAlchemy 2.0 (async) + PostgreSQL 16 + Redis 7 + MinIO |
| 用户 Web / 商家后台 / 管理员后台 | Next.js 15 + React 19 + Tailwind CSS 4 + Zustand + TanStack Query |
| Android App | Kotlin 2.0 + Jetpack Compose + Hilt + Retrofit + Coil3 |
| 基础设施 | Docker Compose + GitHub Actions + Nginx (生产) |

详见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §2。

## 快速开始

前置：**Node ≥ 22** · **pnpm ≥ 11** · **Python ≥ 3.12** · **uv** · **Docker** · **JDK 21**（Android）

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 启动基础设施（Postgres + Redis + MinIO）
docker compose up -d postgres redis minio minio-init

# 3. 后端（本地开发）
cd backend
uv sync --all-extras
uv run alembic upgrade head        # 首次运行前
uv run python -m app.scripts.seed  # 灌种子（可选）
uv run uvicorn app.main:app --reload
# 后端: http://localhost:8000  Swagger: /docs

# 4. 三前端（在项目根目录）
pnpm install
pnpm dev:user-web     # http://localhost:3000  用户 Web
pnpm dev:merchant     # http://localhost:3001  商家后台
pnpm dev:admin        # http://localhost:3002  管理员后台

# 5. Android
cd android-app && gradle wrapper --gradle-version 8.10.2 && ./gradlew assembleDebug
```

**测试账号**（seed 生成）：
- Admin：`admin_super / Passw0rd!` · `admin_business / Passw0rd!` · `admin_cs / Passw0rd!` · `admin_tech / Passw0rd!`
- User：`13800000001 / Passw0rd!` · `13800000002 / Passw0rd!`

**Android 实际可用账号**（以 `backend/app/scripts/seed.py` 与 Android 登录页提示为准）：
- Android 用户端：`13800000001 / Test1234` · `13800000002 / Test1234`
- Android 商家端：`shop1_owner / Merch1234`

> 说明：
> - 当前 README 里的 User 密码 `Passw0rd!` 与 Android/seed 实际数据不一致。
> - Android 用户端应使用 `Test1234`。
> - 商家端 Android 登录提示与 seed 一致，均为 `shop1_owner / Merch1234`。

跑测试 / 数据库迁移 / 加新 Phase 请阅读 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)。

## 目录结构

```
e_commerce_project_claude/
├── backend/                # FastAPI 后端 (api / services / models / alembic)
├── frontend-user-web/      # 用户 Web (Next.js :3000)
├── frontend-merchant/      # 商家后台 (Next.js :3001)
├── frontend-admin/         # 管理员后台 (Next.js :3002)
├── android-app/            # Android 客户端 (Compose)
├── e2e/                    # Playwright E2E 测试 (Phase 7)
├── docs/                   # 全局文档
│   ├── DEVELOPMENT_PLAN.md
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   ├── SECURITY_AUDIT.md
│   ├── CHANGELOG.md
│   ├── API/                # Phase 契约索引
│   ├── DECISIONS/          # ADR
│   └── UX_ISSUES.md
├── infra/                  # Docker / CI 配置
├── .github/workflows/      # backend-ci · frontend-ci · android-ci · e2e-ci
├── AGENTS.md               # 多智能体协作规范
└── README.md
```

## Git 工作流

- `main`：受保护，仅接受 `release/*` 和 `hotfix/*`
- `develop`：集成分支
- `feature/<scope>-<name>`：功能分支（`scope` = backend / user-web / merchant / admin / android）
- **每完成一个 Phase 必须推送到远端并打 Tag**

详见 [AGENTS.md](AGENTS.md) §2。

## Multi-Agent 开发模式

本项目采用 Multi-Agent 并行开发：
- **Orchestrator**（主 Claude）统筹分派
- 各端由独立 Agent 负责（Backend / User-Web / Merchant / Admin / Android）
- Explorer / Reviewer / Security / Test / Docs Agent 提供横向支持
- 已在 Phase 3-6 沉淀出可复用模式（SendMessage 续跑 · 契约先行 · 交付前自检）

详见 [AGENTS.md](AGENTS.md) §3-4。

---

**License**：本项目为学习性质，不用于商业用途。
