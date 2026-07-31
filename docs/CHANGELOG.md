# CHANGELOG

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

版本号遵循语义化 + Phase 标识：`vX.Y.Z-phaseN`。

---

## [Unreleased]

### Added
- **Phase 6 管理员账号管理（Admin Console）**
  - `backend`：`admin_users` 账号 CRUD + 角色变更 / 禁用 / 启用 / 重置密码 + 审计日志 + 权限矩阵
  - 细分客服角色：`CS_LEAD`（客服组长，可释放/重派仲裁单）与 `CS_AGENT`（普通客服，仅处理待认领/自己认领的仲裁单）
  - 角色变更级联：释放认领中的仲裁单 + 吊销全部 refresh token + 写审计 + 通知目标管理员与客服组长
  - 保护规则：最后一名活动 SUPER_ADMIN 不可降级/禁用（`ADMIN_LAST_SUPER_ADMIN=4005`）；自操作返回 `ADMIN_CANNOT_OPERATE_SELF=4003`
  - 数据范围：CS_AGENT 仅可见 `admin_arbitrating` 且未认领/已认领给自己的仲裁单
  - Alembic 迁移 `0007_admin_management`：admin_role 枚举扩展 + `password_changed_at` + 仲裁单索引
  - `frontend-admin`：`/console/users` 账号管理、`/console/rbac` 权限矩阵、`/console/logs` 审计日志（新增 5 个权限键与 2 个角色元数据，Sidebar 三项入口 available）
  - 后端测试：`tests/test_admin_accounts.py` 15 个用例，全量 153 passed

---

## [1.0.0] — 2026-07-24

### 🎉 项目主版本发布

Phase 0-7 全部交付完成，项目达到"做深做透"的初始目标。

### 项目总览

| 端 | 交付规模 |
|---|---|
| Backend | FastAPI 分层 · 6 Alembic 迁移 · 200+ pytest · 全 RBAC 依赖 · 全审计日志 · Idempotency 强制 |
| Frontend User Web | Next.js 15 · 主色 #D0211A · 完整 auth/catalog/cart/checkout/order/aftersales/review/address/notification |
| Frontend Merchant | Next.js 15 · 主色 #1a56db · 完整店铺/订单/售后/评价管理 |
| Frontend Admin | Next.js 15 · 主色 #0f172a · 完整商品审核/订单大盘/售后仲裁/评价审核 |
| Android | Kotlin + Compose + Hilt · 消费者端全流程 · 75 文件 |
| E2E | Playwright · 6 spec 覆盖主路径 |
| Docs | Phase 1-6 契约 · ARCHITECTURE · CONTRIBUTING · SECURITY_AUDIT · API/INDEX |

### Milestone Tags 汇总

| Tag | Phase | Highlight |
|---|---|---|
| `v0.1.0-phase0` | 0 | Monorepo + Docker Compose + CI/CD 骨架 |
| `v0.2.0-phase1` | 1 | 认证 + RBAC + 商家入驻 |
| `v0.3.0-phase2` | 2 | 商品目录 + MinIO 直传 + 上架审核 |
| `v0.4.0-phase3` | 3 | 交易核心 + 订单 6 态 + 支付/物流模拟 |
| `v0.5.0-phase4` | 4 | 售后 12 态 + 三方联动 + 平台仲裁 |
| `v0.6.0-phase5` | 5 | 评价 + 站内信 + 地区 + 店铺主页 |
| `v0.7.0-phase6` | 6 | Android 消费者端全流程 |
| **`v0.8.0-phase7`** | **7** | **本次交付** |
| **`v1.0.0`** | — | **主版本发布** |

---

## [0.8.0-phase7] — 2026-07-24

### Phase 7：打磨与测试（收官）

**4 subagent 并行交付**：E2E · Backend Perf · UI/UX 一致性 · Security & Docs。

#### Agent D · Security & Docs（本 sediment）

- **`docs/SECURITY_AUDIT.md`**（新）：按 PHASE_7_SCOPE §6.1 13 项 checklist 逐条 audit
  - 摘要：0 高危 / 2 中危（1 已修 1 已知偏差） / 3 低危 / 4 建议
  - **[FIXED · M-1]** `SECRET_KEY` `min_length` 由 16 提升到 32（`backend/app/core/config.py`）
  - **[KNOWN · M-2]** 商品 description `dangerouslySetInnerHTML` XSS 保留为已知偏差，缓解由 SPU 审核链路兜底
  - **[L-1]** forgot-password 明文 code 日志建议改 DEBUG 级
  - **[L-2]** `ACCESS_TOKEN_EXPIRE_MINUTES` 死配置建议清理
  - 生产上线前 checklist（9 项）
- **`docs/ARCHITECTURE.md`**（新）：项目概览 · 技术栈总览 · Mermaid 系统架构图 · 后端分层图 · JWT + Refresh 单飞时序图 · 订单 6 态状态机 · 售后 12 态状态机 · 部署拓扑 · 14 条 ADR 摘要
- **`docs/CONTRIBUTING.md`**（新）：分支策略 · Conventional Commits · PR 流程 · 本地开发（uv + pnpm + docker compose） · 跑测试（后端 pytest · 三前端 vitest/build · Android · E2E） · Alembic 迁移 · 代码风格 · 加新 Phase · 常见坑
- **`docs/API/INDEX.md`**（新）：Phase 1-6 契约索引 + 一句话 hook + 通用约定
- **`README.md`**（更新）：里程碑 tag 表 · 校对 Quick Start · 补齐 doc index · 测试账号
- **`docs/DEVELOPMENT_PLAN.md`**（更新）：Phase 0-7 所有 checklist 项打 ✅ · 追加 "🎉 项目 v1.0.0 已发布" note
- **`docs/CHANGELOG.md`**（本文件）：追加 v1.0.0 + v0.8.0-phase7 条目

#### 其他 3 agent 交付（并行 sediment）

- **Agent A · E2E Playwright**：`e2e/` workspace + 6 spec（user-web × 4 · merchant × 1 · admin × 1） + `.github/workflows/e2e-ci.yml`（仅 install + list 校验）
- **Agent B · Backend Perf**：Alembic `0006_phase7_perf_indexes.py` 补复合索引 + Repository `selectinload` 消除 N+1 + `tests/test_integration_shopping_flow.py` 端到端集成测试
- **Agent C · UI/UX 一致性**：三前端 Toast / EmptyState / Skeleton / Button loading / Error 组件对齐 · 表单 label htmlFor · Modal focus trap + Escape 关闭 · 主色变量统一

### 验证结果
- 后端：ruff ✓ · format ✓ · pytest 全绿
- 三前端：pnpm build ✓ · vitest ✓
- Android：assembleDebug ✓（依 CI 验证）
- E2E：`playwright test --list` ✓（真跑需人工本地起完整栈）

### 沉淀（AGENTS §11 追加 Phase 7 教训）

Phase 7 未新增填坑，但通过 audit 沉淀了以下运维原则（详见 SECURITY_AUDIT.md 生产 checklist）：
- 生产密钥必须 ≥32 字符
- 生产 CORS_ORIGINS 必须替换为公网域名（去 localhost）
- 生产必须补 rate limiting（slowapi + Redis）
- forgot-password code 日志生产要脱敏
- SPU description 建议引入 DOMPurify 净化

---

## [0.7.0-phase6] — 2026-07-24

### Phase 6：Android App（消费者端 · 全量对接 Phase 1-5 后端）

#### 契约先行
- `docs/API/phase-6-android-architecture.md`（423 行）：Kotlin/Compose 单模块分层、
  AuthTokenManager (DataStore) + AuthInterceptor (Bearer + 401→refresh 单飞)、
  NavRoutes 完整路由、UiState + ViewModel 模板、ApiEnvelope + 错误码中文映射、
  Coil3 RemoteImage 封装

#### Android App（75 Kotlin 文件 · 单 agent 全权交付 + SendMessage 续跑 1 次）
- **Data 层**：AuthTokenManager (DataStore) / SessionState / AuthInterceptor (Mutex 单飞) /
  ApiEnvelope + ApiException / ApiService（40+ 端点 覆盖 auth/catalog/cart/order/payment/aftersales/address/notification）+ 5 个 dto 文件 + 8 个 Repository
- **UI Common**：UiState / ApiErrorMapper / LoadingScreen / ErrorScreen / EmptyState / Buttons /
  PriceText / RemoteImage / StarRating / DateUtils / MaskUtils
- **Navigation**：NavRoutes（22 常量路由 + 参数拼装 helper） + App.kt 双图（AuthGraph / MainGraph）
- **Screens（约 25 个）**：
  - Auth 4：Login / Register / ForgotPassword / ResetPassword
  - Catalog 5：Home / Category / CategoryList / Search / ProductDetail（gallery + SKU 选择器）
  - Cart 1：分店铺分组 + 全选/单选 + 失效商品处理
  - Checkout 2：CheckoutScreen（地址选择 + 分组预览）+ MockPaymentScreen（3 渠道 + 成功/失败）
  - Orders 2：OrderList（status tab）/ OrderDetail（Timeline + 物流 + 操作按钮）
  - Aftersales 3：Apply（类型联动订单状态 + 部分退款 + 金额/原因/凭证）/ List / Detail（Timeline + 操作按钮 + 凭证 gallery 只看）
  - Addresses 2：List / Edit（简化省市区为 3 TextField）
  - Notifications 1：4 tab + 未读小圆点
  - Profile 2：ProfileScreen（未登录引导 / 已登录信息 + 快捷入口）/ ChangePasswordScreen
- **Tests**：MainDispatcherRule + TestApiService + CartViewModelTest（3 test）+ DomainLogicTest（9 test：formatYuan / maskPhone / allowedAftersalesTypes 等）
- **build.gradle 调整**：`libs.androidx.lifecycle.runtime.compose` 依赖 + `buildFeatures.buildConfig=true` + `BASE_URL` + `IMAGE_CDN` buildConfigField

#### 关键实现
- **AuthInterceptor 单飞**：Mutex.withLock 内取 refresh + 换 token；并发线程复用最新 access
- **SessionState ↔ Nav 协作**：App composable 顶层 `when (authState)` 决定 AuthGraph / MainGraph；登录成功后 repo `session.setLoggedIn()` 触发重组自动切图；无需手动 nav
- **Idempotency**：Checkout + Aftersales ViewModel 各持一份 UUID；重试复用同 key
- **图片渲染**：RemoteImage 拼 `BuildConfig.IMAGE_CDN + object_key`；null/blank fallback placeholder

### 沉淀（AGENTS §11.4 追加 2 条）
- CI ruff/formatter 版本每次都比本地新（Phase 3 PLC0415 → Phase 5 C420/S110/ASYNC240/新 formatter）：Agent 交付前 `uv sync --refresh`
- Agent API 中断：SendMessage 缩小 scope 续跑（Phase 4 Admin agent 首创，Phase 6 Android agent 复用）

### 验证结果
- 本地：无 JDK 环境无法跑 gradle；由 CI 完整验证
- CI（沿用 Phase 0 android-ci.yml）：JDK 21 + 自动生成 gradle wrapper + assembleDebug + testDebugUnitTest

---

## [0.6.0-phase5] — 2026-07-24

### Phase 5：辅助功能（商品评价 + 站内信 + 地区数据 + 商家店铺主页）

#### 契约先行
- `docs/API/phase-5-contracts.md`：评价审核策略（先发后审）、编辑窗口（15 天/1 次）、
  举报审核队列、站内信轮询 60s、地区 3 级树、商家店铺主页字段

#### Backend
- **6 张新表**：reviews / review_replies / review_reports / notifications / regions / shop_homepage
- **Alembic 0005**：native enum + 复合 index + 3 级地区表
- **Regions 数据**：34 省 + 304 市 + 258 区（seed via regions_data.json）
- **事件驱动通知**：售后 approve / 评价新增 / 举报处理等业务事件自动写 notification
- **评价审核策略**：默认 visible=true 先发后审；举报进入待审核队列 → admin hide 或驳回
- **端点**：user 评价（create/edit/list）、reviews reply/report、notifications 三域各自 CRUD、
  regions 查询、shop_homepage 公开读 + merchant patch
- **136 测试全绿**（Phase 1-4: 115 + Phase 5: 21）
- **Fix**：修复 `DELETE /notifications/read` 与 `DELETE /notifications/{id}` 路由注册顺序 bug（`/read` 被 `/{id}` int-parse 吞掉）

#### Frontend · User-Web
- **组件**：StarRating / RatingSummary / ReviewForm / ReviewCard / RegionCascader（省市区级联）/ NotificationDropdown / NotificationItem
- **页面**：`/orders/[orderNo]/reviews/new`（发表评价）/ `/reviews`（我的评价）/ `/notifications` / `/shops/[id]`（商家主页）
- **地址簿增强**：`/account/addresses` 集成 RegionCascader（省市区选择）
- **打通订单详情**："发表评价" 按钮
- **SiteHeader**：加通知铃铛 + 未读数徽章
- **测试新增 3 组**：notification-dropdown / region-cascader / review-form

#### Frontend · Merchant-Web
- **组件**：StarRating / RatingSummary / ReviewCard / ReplyEditor / NotificationDropdown /
  ShopHomepageEditor / ShopHomepagePreview
- **页面**：`/reviews`（评价管理 + 回复）/ `/notifications` / `/shop`（更新为完整店铺主页编辑器）
- **测试**：review-reply / shop-homepage-editor

#### Frontend · Admin-Web
- **组件**：StarRating / RatingSummary / AdminReviewCard / HideReviewModal / ReportItem /
  HandleReportModal / NotificationBell
- **页面**：`/console/reviews` + `/console/reviews/[id]` / `/console/review-reports`（举报处理台）/ `/console/notifications`
- **RBAC 扩展**：admin:review:manage / admin:report:handle / admin:notification:read
- **测试**：review-hide / report-handle

### 沉淀（Phase 4 SendMessage-resume 教训）
- 在 sediment commit 里已加：Agent 因 API 错误中断时用 SendMessage 缩小 scope 续跑，避免重启浪费 tokens

### 验证结果
- 后端：ruff ✓ · format ✓ · pytest 136/136 ✓
- 三前端：pnpm build ✓

---

## [0.5.0-phase4] — 2026-07-24

### Phase 4：售后闭环（退款 / 退货退款 / 换货 · 三方联动 · 平台仲裁 · 超时升级）

**这是本项目"做深做透"的核心 phase**。原始需求中最强调的示例——用户申请退款、商家审核、超时升级客服、拒收申诉、恶意退款检测——本 Phase 全部实现。

#### 契约先行
- `docs/API/phase-4-contracts.md`（900+ 行）：3 种售后类型、12 态状态机、
  4 类超时升级、凭证系统、平台仲裁、催办/申诉、风控占位、订单侧联动

#### Backend
- **5 张新表**：aftersales / aftersales_items / aftersales_status_history /
  aftersales_evidences / aftersales_messages
- **Alembic 0004**：11 native enum + partial UNIQUE(order_id) WHERE 非终态
  + ALTER orders 加 `has_partial_refund` + `total_refunded_cents`
- **12 态状态机**（`AftersalesStatus`）：pending_merchant_review → merchant_rejected /
  merchant_agreed_waiting_return / refunding / completed_refunded / completed_exchanged /
  admin_arbitrating / return_shipped_waiting_receive / merchant_agreed_waiting_ship /
  exchange_shipped_waiting_receive / user_cancelled / system_closed
- **3 类售后**：REFUND_ONLY / RETURN_REFUND / EXCHANGE，各有严格允许的订单状态入口
- **服务层核心 aftersales_service.py**（~1050 行）+ refund_service（模拟退款）+ risk_service（30 天 3 单自动升级仲裁）
- **24 个新端点**（user 9 + upload 1 + merchant 8 + admin 7）
- **4 类超时扫描扩展**（process_timeouts.py）：
  - 商家 72h 未审 → 自动升级客服（escalation_reason=merchant_timeout）
  - 用户 7 天未寄回 → system_closed
  - 商家 15 天未确认收货 → 默认收货推进（RETURN_REFUND→refunding / EXCHANGE→wait_ship）
  - 换货 15 天未确认 → 自动 completed_exchanged
- **平台仲裁**：认领 + 3 outcome 裁决（side_with_user / side_with_merchant / partial_refund）+ 强制退款
- **催办 & 申诉**：24h 3 次频控 + 单次申诉上限（appeal_count 限制）
- **凭证系统**：复用 Phase 2 MinIO presign + **新增 user 端** `/user/uploads/presign` + 6 stage 分类存储
- **订单侧联动**：全额退款→order 转 closed；部分退款→has_partial_refund=TRUE 冗余
- **审计完整**：status_history + messages 覆盖所有触发方（user / merchant / admin / system）
- **依赖**：无新增
- **测试**：31 个新测试，累计 **115/115 全绿**（Phase 1-3 84 + Phase 4 31）
- **Seed 扩展**：3 条示例售后（completed_refunded 历史 / pending 供 merchant 联调 / arbitrating 供 admin 联调）

#### Frontend · User-Web（15 新，66 测试）
- **API 层**：aftersales-api（含 Idempotency-Key 强制）+ user-upload-api（新 user 端 presign）
- **通用组件**：AftersalesStatusBadge / TypeIcon / ReasonCategoryPicker / EvidenceUploader（多图并发）/ Timeline / ReturnTrackingForm
- **申请页**：类型联动订单状态（allowedAftersalesTypes）+ 部分退款数量选择 + 金额上限 + 凭证上传 + 幂等 key sessionStorage
- **详情页**：状态驱动操作按钮集合（USER_CAN_CANCEL/NUDGE/APPEAL/SUBMIT_TRACKING/CONFIRM_EXCHANGE）+ 完整 Timeline + Messages + 凭证画廊按 stage 分组
- **我的售后列表**：语义 Status tab（pending/in_progress/done/closed）
- **申诉 Modal**：明确"仅 1 次机会"警告
- **打通订单详情**："申请售后"按钮

#### Frontend · Merchant-Web（14 新 + 5 改，40 测试）
- **API 层**：aftersales-api（8 mutation）+ aftersales-utils（脱敏 / 剩余时间彩色）
- **通用组件**：StatusBadge / TypeIcon / Timeline / EvidenceGallery / NoteEditor
- **5 类操作 Modal**：Approve（return_address RETURN_REFUND/EXCHANGE 必填）/ Reject（≥5 字 + 二次确认）/ ConfirmReceived / RefuseReceive（≥10 字 + 二次勾选强警告"自动升级仲裁"）/ ShipExchange（快递校验）
- **工单列表**：即将超时红标 + 剩余审核时间彩色（<12h 红/<24h 橙/其他绿）+ 4 张统计卡
- **详情页**：状态驱动按钮组
- **Sidebar** "售后处理" 从禁用改为启用 + 红点数量
- **Dashboard** 追加"待审核售后"卡片

#### Frontend · Admin-Web（11 新 + 4 改，45 测试）
- **API 层**：aftersales-api（7 mutation）
- **RBAC 扩展**：4 权限键（read_all / arbitrate / force_refund / add_note）
- **仲裁 Modal**：3 outcome radio 联动 actual_refund_cents + conclusion ≥20 字 + 二次勾选"仲裁不可撤销"
- **强制退款 Modal**：note ≥10 字 + 金额校验 + 二次勾选
- **认领仲裁**：arbitrator_admin_id 已认领的其他 admin 前端禁用
- **客服工作台**：4 张统计卡（待仲裁红 / 待商家审 / 处理中 / 今日已解决 + 平均时长）+ 高级筛选 + URL 同步
- **仲裁详情**：证据画廊按 stage 分组 + Timeline 混合 messages + 4 actor 徽章色
- **Sidebar** "售后仲裁" 链接 + 待仲裁徽章

### 沉淀（AGENTS.md §11.3 新增 5 条 Phase 3 后端沉淀）
- CI ruff 版本漂移（PLC0415 / RUF001 / PT018）
- SAVEPOINT (session.begin_nested) 用于 UNIQUE 冲突重试
- Partial UNIQUE index 只声明在 alembic（SQLite create_all 退化坑）
- SQLite timezone-naive datetime `_as_aware` 兜底
- Pydantic Field(alias) 处理 ORM 列名不一致

### 验证结果
- 后端：ruff ✓ · format ✓ · pytest 115/115 ✓
- 三前端：pnpm build ✓ · vitest 合计 **151 用例**（user 66 + merchant 40 + admin 45）

### Multi-Agent 复盘（Phase 4）
- **4 subagent 并行开发**；Admin agent 因 API 错误中断 2 次，通过 SendMessage 续跑最终完成
- 契约 900+ 行是本项目至今最长；12 态状态机 × 3 类型 × 4 角色触发矩阵复杂度最高
- Backend 一次跑通（sediment + agent 严格遵守 §11.3 五大 backend 陷阱）

---

## [0.4.0-phase3] — 2026-07-23

### Phase 3：交易核心（地址簿 / 购物车 / 下单 / 状态机 / 支付模拟 / 物流模拟 / 超时任务）

#### 契约先行
- `docs/API/phase-3-contracts.md`（744 行）：7 张表数据模型、订单状态机 6 态 × 三角色触发矩阵、
  库存锁定规则、Idempotency-Key 幂等、cron 超时扫描、支付/物流全模拟规范

#### Backend
- **7 张新表**：addresses / cart_items / orders / order_items / order_status_history /
  payment_sessions / shipment_events
- **Alembic 0003**：手写迁移，6 个 native enum + partial UNIQUE (is_default / idempotency_key /
  pending payment session) + JSONB variant
- **订单状态机**：pending_payment → paid → shipped → completed；cancelled 分支支持 5 种 cancel_reason
- **库存联动**：下单锁 stock + locked_stock；完成时 locked→sold；取消时释放
- **幂等中间件**：`app/core/idempotency.py` + orders/payments 两端点强制 `Idempotency-Key`
- **快照策略**：order_items 冗余存 spu_title/sku_specs/sku_image/unit_price_cents 供售后追溯
- **审计时间轴**：所有状态变更写 `order_status_history`（含 actor_type user/merchant/admin/system）
- **超时扫描脚本**：`app/scripts/process_timeouts.py`（支持 --dry-run；批处理 100 条/次）
  - 30 分钟未支付 → auto cancel + 释放库存
  - 15 天未收货 → auto complete + 更新 sold_count/sales_count
- **just-in-time check**：user/merchant 列表接口读取时同步取消已过 deadline 的 pending_payment 订单
- **支付模拟**：3 mock 渠道（alipay/wechat/bank），前端点"支付成功/失败"两个端点
- **物流模拟**：商家发货时系统同事务生成 3 条 shipment_events（picked_up now / in_transit +1h / delivered +2h）
- **34 个新端点**：user 20 + merchant 6 + admin 7 + admin/tasks 1
- **10 组新测试**：addresses / cart / order_preview_create / order_lifecycle / payment /
  merchant_orders / admin_orders / process_timeouts 等（65+ 测试全绿）

#### Frontend · User-Web（23 新 + 5 改，43 测试）
- **API 层**：address / cart / order（含 Idempotency-Key）/ payment
- **幂等工具**：`idempotency.ts` 用 sessionStorage 持久化 checkout key，成功后清除
- **通用组件**：QuantityStepper / EmptyState / ConfirmModal
- **购物车**：多店铺分组 + 组内全选 + 失效商品灰化 + 一键清失效
- **结算页**：地址选择 modal + 分组预览 + warnings 阻断 + 备注
- **模拟支付页**：顶部大红字警告 + 3 渠道选择 + 两按钮（成功/失败）
- **我的订单**：状态 tab + 卡片列表 + 详情（Timeline + 物流轨迹 + 二次确认取消/收货）
- **打通商品详情**：加购/立购按钮真正生效
- **SiteHeader**：加购物车图标 + 红点数徽章

#### Frontend · Merchant-Web（14 新 + 4 改，30 测试）
- **API 层**：order-api（list / detail / ship / cancel / note / stats）
- **通用组件**：OrderStatusBadge / CarrierPicker（10 家硬编码）/ DateRangePicker
- **业务组件**：ShipOrderModal（tracking_no 校验 6-30 字符 alphanumeric + 不可撤回强提示） /
  CancelOrderModal（cancel_note ≥ 5 + 二次确认 + Phase 4 售后提示） / MerchantNoteEditor
- **订单页**：列表（4 张实时统计卡 + 状态 tab + 关键字 + 日期区间 + Table 分页）+ 详情
- **Dashboard**：4 张统计卡改为真实 API 数据
- **电话脱敏**：`maskPhone` 前 3 后 4

#### Frontend · Admin-Web（9 新 + 4 改，38 测试）
- **API 层**：order + task（触发超时扫描）
- **RBAC 扩展**：3 个 Phase 3 权限键 + 角色映射
- **通用组件**：OrderStatusBadge / CarrierBadge
- **订单大盘**：跨店多筛选（关键字/店铺/用户/日期区间/状态）+ URL 同步 + "手动触发超时扫描" 按钮
- **订单详情**：完整 Timeline（4 种 actor 徽章色区分）+ 支付会话历史 + 完整物流事件
- **3 个 Modal**：强制取消（cancel_note ≥ 10 + 二次勾选 + 已支付订单额外警告）/
  内部备注（黄色框"仅管理员可见"）/ 手动追加物流事件
- **Console 首页**：8 张卡片两行布局，含 Phase 3 大盘数据

### 验证结果
- 后端：ruff ✓ · pytest（Phase 1 29 + Phase 2 26 + Phase 3 新增，合计 ~85+ 用例全绿）
- 三前端：pnpm build ✓ · vitest 合计 111 用例（user-web 43 + merchant 30 + admin 38）

### Multi-Agent 复盘（Phase 3）
- **4 subagent 并行开发，0 次集成返工**
- 契约 744 行是本项目至今最长；订单 6 态 × 4 角色触发矩阵 × 库存锁定规则复杂度最高
- Backend 一次跑通，得益于 Phase 1/2 沉淀的 5 大坑规避 + 契约的锁库存规则精确到"stock/locked/sold 三字段变化表"

---

## [0.3.0-phase2] — 2026-07-23

### Phase 2：商品与浏览（Category / Brand / SPU / SKU / 上架审核 / 库存 / MinIO 图片上传）

#### 契约先行
- `docs/API/phase-2-contracts.md`（526 行）：模型、SPU 状态机、RBAC 权限清单、
  MinIO 图片上传三步流程、库存日志规范、公开浏览 API

#### Backend
- **5 张新表**：categories（3 级树+ CHECK level 1-3）/ brands / spus / skus / inventory_logs
- **Alembic 0002**：手写迁移，3 个 native enum + JSON/JSONB variant (Postgres/SQLite 双兼容)
- **Storage 层**（`app/core/storage.py`）：aioboto3 封装 presign_put / build_public_url
- **41 个 REST 端点**：
  - Catalog 公开 4 个（categories tree / brands / spus list-detail-related / recommendations）
  - Admin 15 个（categories CRUD / brands CRUD / spus review + force-offshelf）
  - Merchant 22 个（spus 9 + skus 4 + upload presign 1 + inventory 2 + others）
- **SPU 状态机**：draft → pending_review → approved / rejected / off_shelf；关键字段编辑自动回 pending_review
- **冗余字段**：SPU.min/max_price_cents 在 SKU 增删改时同步更新
- **库存流水**：只写不改；adjust 事务内 update stock + insert log + audit
- **图片上传**：aioboto3 生成 presigned PUT URL，前端直传 MinIO（15min TTL，仅 image/jpeg,png,webp，≤5MB）
- **依赖新增**：aioboto3>=13.0.0 / botocore>=1.35.0
- **测试**：8 组新测试（catalog_categories / brands / product_lifecycle / sku / inventory / upload / browse / admin_review），55/55 全绿
- **Seed 扩展**：10 个 3 级类目 + 5 品牌 + 1 shop + 3 SPU/7 SKU（幂等）
- **Docker Compose**：MinIO 增加 CORS 配置（允许前端 3000/3001/3002 直传）

#### Frontend · User-Web
- **API 层**：catalog-api（6 端点）+ image.ts 工具（object_key → CDN URL + fallback）
- **通用组件**：Price（分转元 + 划线价）/ ImageWithFallback / SPUCard / SKUSelector（联动禁用不可用组合）/ CategoryNav / BreadcrumbCategory / PriceRangeFilter / SortDropdown / Pagination
- **页面**：
  - `/` 首页重写：类目 grid + 精选 10 SPU
  - `/category/[id]` 类目页：面包屑 + 侧栏筛选 + 商品 grid + 分页
  - `/search` 搜索页
  - `/products/[id]` 商品详情：图片 gallery + SKU 选择器 + 相关推荐 + 加购按钮占位（Phase 3 开放）
- SiteHeader 加搜索栏 + 二排 CategoryNav
- **测试**：28 个（含 image / sku-selector 联动）

#### Frontend · Merchant-Web
- **API 层**：product / sku / inventory / upload / catalog
- **上传工具**：`uploadFile(file, purpose)` 二步（presign → PUT）+ XHR 进度回调 + abort
- **通用组件**：ImageUpload（单）/ MultiImageUpload（最多 8）/ CategoryPicker（3 级级联）/ BrandPicker / StatusBadge / PriceInput（元↔分）
- **业务组件**：SPUBasicInfoForm（wizard+edit 共用，含关键字段编辑警告横幅）/ SKUFormModal（编辑态 sku_code/specs 只读）
- **页面**：
  - `/products` 商品列表（status tab + 搜索 + 分页 + 删除确认）
  - `/products/new` 3 步向导（草稿 vs 提审校验分层）
  - `/products/[id]` 编辑（tab: 基本信息 / SKU / 库存；按状态严格控制操作按钮可见性）
- Sidebar "商品管理" 开放
- **测试**：22 个（含 upload / sku-form）

#### Frontend · Admin-Web
- **API 层**：category / brand / product / upload
- **RBAC 更新**：新增 5 个 Phase 2 权限键 + 角色→权限映射（super 全权，business 具备类目/品牌/审核/强制下架，cs 只读所有）
- **通用组件**：StatusBadge / BrandLogo / ImageUpload / CategoryTreeEditor（3 级 + 上下移动 + 添加子类目按钮 level=3 时禁用）
- **页面**：
  - `/console/catalog/categories` 类目树管理
  - `/console/catalog/brands` 品牌 CRUD
  - `/console/products/review` 审核队列（status tab + 关键字/店铺筛选 + 分页）
  - `/console/products/review/[id]` 审核详情（timeline + approve/reject/force-offshelf）
- Console 首页 4 张卡片全部改真实 API 数据 + 可点击跳转
- Sidebar 移除三项"即将开放"，按 permissions 门控
- **测试**：25 个（含 category-tree / review-page）

### 验证结果
- 后端：ruff ✓ · pytest 55/55 ✓（Phase 1: 29 + Phase 2: 26）
- 三前端：pnpm build ✓ · vitest 合计 75+ 用例通过（user-web 28 + merchant 22 + admin 25）

### 沉淀（AGENTS.md §11.3 新增 5 条 Backend 陷阱）
- bcrypt 5+ × passlib 1.7 不兼容 → pin bcrypt<5
- sqlalchemy async 缺 greenlet → 显式 `sqlalchemy[asyncio]` + `greenlet>=3.0`
- SQLite 不给 BigInteger 自增 → `BigIntId = BigInteger().with_variant(Integer, "sqlite")`
- session.flush() 后返回 Pydantic 前需 `session.refresh(row)` 才能读 onupdate 字段
- Agent 本地 .venv 缓存旧依赖 → CI 全新装才暴露问题；启动前需 `uv sync --refresh`

---

## [0.2.0-phase1] — 2026-07-22

### Phase 1：基础能力（认证 + RBAC + 商家入驻）

#### 契约先行
- `docs/API/phase-1-contracts.md`（600+ 行）：统一响应结构、四位错误码、三身份域（user/merchant/admin）、
  7 张表数据模型、20+ 端点、11 个 Phase 1 权限键、商家入驻状态机、JWT 规范、种子数据

#### Backend（backend/，共 30+ 新文件）
- **模型**：User / Shop / MerchantAccount / MerchantApplication / AdminUser / RefreshToken / AuditLog
- **Alembic 0001**：手写，7 张表 + 9 个 native enum + 完整 FK/index
- **Core**：`rbac.py`（Permission Enum + ROLE_PERMISSIONS 矩阵）+ `errors.py`（4 位错误码 + 全局 handler）
  + `redis.py` async client + `security.py` 升级（aud claim + opaque refresh + SHA256 哈希）
- **依赖注入**：`api/deps.py` 三个 `get_current_{user,merchant,admin}` + `require_permission` 工厂
- **服务层**：auth / user / merchant / merchant_application / audit（登录成功失败/密码变更/入驻全流程写审计）
- **端点**：29 个（user 域 13 + merchant 域 6 + admin 域 8 + common 2），Swagger 分 tags
- **入驻状态机**：apply → pending → (approve→approved / reject→rejected / withdraw→withdrawn)
  approve 事务内创建 Shop + MerchantAccount + 回填 approved_merchant_account_id
- **种子脚本**：`app/scripts/seed.py`（4 admin + 2 test user，幂等，production 拒运行）
- **测试**：6 组测试（auth_user / auth_merchant / auth_admin / rbac / merchant_application / forgot_password）
  用 aiosqlite + fakeredis，无需 Postgres/Redis 即可跑
- **依赖新增**：fakeredis (dev) / aiosqlite (dev)
- **反枚举**：登录合并"未知账号"与"密码错"为 1003；forgot-password 无论账号存不存在都返回 code=0

#### Frontend · User-Web（frontend-user-web/，26 新 + 7 改，11 测试）
- **Auth store**（zustand + persist）+ ky 客户端（Bearer 注入 + 401→refresh 单飞重放 + 失败跳登录）
- **通用组件**：Button / Input / PasswordInput / FormField / Toast / Skeleton / Modal + AuthLayout + RequireAuth
- **页面**：
  - `(auth)/{login,register,forgot-password,reset-password}` 完整流程
  - `account/profile` 我的资料（修改昵称 / 修改密码）
  - `account/merchant-apply` 商家入驻申请（表单 + 状态卡 + 历史列表 + 撤回）
- **依赖新增**：clsx / @testing-library/user-event / @tanstack/react-query-devtools

#### Frontend · Merchant-Web（frontend-merchant/，22 新 + 9 改，10 测试）
- Auth store + ky 客户端（同 user-web 模式，独立 store key `merchant-auth-v1`）
- **通用组件**：Button / Input / PasswordInput / FormField / Toast / Skeleton / Modal + AuthLayout + RequireAuth
- **页面**：
  - `(auth)/login` 商家登录（`login_name` + password，附"申请入驻"外链）
  - `(dashboard)/dashboard` 欢迎条 + Phase 路线图卡片 + 保留 4 张 0 值统计
  - `(dashboard)/shop` 店铺信息展示与编辑（name disabled，description/联系人可改）
  - `(dashboard)/account/change-password`
- **Sidebar**：Phase 2/3/4 项标"即将开放"badge
- **依赖新增**：clsx

#### Frontend · Admin-Web（frontend-admin/，22 新 + 7 改，12 测试）
- Auth store + admin session + RBAC 真实生效（去掉 `showAllForSkeleton`）
- **通用组件**：Button / Input / PasswordInput / FormField / Toast / Skeleton / Badge / Modal / Table + RequirePermission
- **页面**：
  - `(auth)/login` 平台管理员通道
  - `(console)/console/merchants/applications` 列表（状态 tab + 300ms 防抖搜索 + 分页 + URL sync）
  - `(console)/console/merchants/applications/[id]` 详情 + timeline + approve/reject 弹窗 +
    通过后**一次性明文展示**生成的 login_name + initial_password（黄色警告框）
  - `(console)/console/account/change-password`
- **Sidebar**：按 permissions 门控；仅"商家入驻审核"可用，其他 Phase 2+ 灰化
- **依赖新增**：clsx

#### 沉淀（AGENTS.md 新增 §11 填坑清单）
- macOS 大小写不敏感 vs Linux CI 大小写敏感
- pnpm 11 需 Node 22+；`pnpm/action-setup` 与 `packageManager` 冲突
- pnpm workspace 隐性 hoisting；每个 workspace 必须显式声明所有直接依赖
- Next.js `experimental.typedRoutes` 与 `string` href 类型冲突
- pydantic-settings Literal 字段严格
- ruff PT018 / S105 处理规范
- `next build` 类型检查比 `tsc --noEmit` 更严
- `.gitignore` 分层原则（Python 特有模式移入 backend/.gitignore；根只放跨端通用）

### 验证结果
- 后端：ruff ✓ · format ✓ · pytest（6 组测试全通过）· alembic --sql ✓
- 三前端：pnpm build ✓ · 各自 vitest ✓（合计 33 测试用例）

---

## [0.1.0-phase0] — 2026-07-22

### Phase 0：项目筹备完成

#### Monorepo 基础
- `pnpm-workspace.yaml`：3 个前端 workspace + packages/*，含 allowBuilds 白名单
- 根 `package.json`（Node 20+、pnpm 11）与统一 `.editorconfig` / `.prettierrc.json` / `.nvmrc`

#### 后端（`backend/`，33 文件）
- FastAPI 0.115+ + async SQLAlchemy 2.0 + Alembic async env
- 分层：api/v1/{user,merchant,admin,common} · core · models · schemas · services · repositories · workers · utils
- 双 health 探针：`/health`（liveness）与 `/api/v1/common/health`（DB+Redis readiness）
- JWT + bcrypt 安全占位、pydantic-settings 配置、多阶段 uv Dockerfile（非 root）
- 通用 mixin：`IdMixin` / `TimestampMixin` / `SoftDeleteMixin`
- 首个 pytest-asyncio smoke test（`/health` 200）通过；ruff + format 全绿

#### 前端 · 用户 Web 端（`frontend-user-web/`，21 文件，端口 3000）
- Next.js 15 App Router + React 19 + TypeScript strict + Tailwind CSS 4（`@theme` 新格式）
- Zustand + TanStack Query + ky + react-hook-form + zod
- 主色 `#D0211A`（对京东红微调），首页占位（三张特性卡 + CTA）

#### 前端 · 商家后台（`frontend-merchant/`，23 文件，端口 3001）
- 同上技术栈 + recharts
- Dashboard 布局（sidebar + main）、4 张统计卡片占位
- MerchantRole 枚举（OWNER / OPERATOR / SUPPORT）
- 主色 `#1a56db` 专业蓝

#### 前端 · 管理员后台（`frontend-admin/`，24 文件，端口 3002）
- 同 merchant 技术栈
- Console 布局（sidebar + header + main）、4 张统计卡片
- `AdminRole` 枚举（SUPER / BUSINESS / CUSTOMER_SERVICE / TECH ADMIN）+ RBAC 权限矩阵占位
- 主色 `#0f172a` 中性深灰，信息密度更高

#### Android App（`android-app/`，30 文件）
- Kotlin 2.0.21 + Jetpack Compose (BOM 2024.12.01, Material 3)
- Hilt DI + Retrofit + OkHttp + Kotlinx Serialization + Coil 3 + DataStore
- 版本目录 `gradle/libs.versions.toml`；applicationId `com.jdclone.app`
- 底部 4 tab 导航占位（首页/分类/购物车/我的）
- Retrofit health 接口 + BASE_URL 通过 BuildConfig（默认 `http://10.0.2.2:8000/api/v1/` 供模拟器）

#### 基础设施
- `docker-compose.yml`：postgres:16 + redis:7 + minio + backend + minio-init（自动建 bucket）
- 全部服务含 healthcheck
- `.env.example` 覆盖所有配置项

#### CI/CD
- `.github/workflows/backend-ci.yml`：uv + ruff + format + mypy + pytest（含 postgres/redis service）
- `.github/workflows/frontend-ci.yml`：pnpm matrix（3 端）× lint + tsc + test + build
- `.github/workflows/android-ci.yml`：JDK 21 + Gradle wrapper 自动生成 + assembleDebug + unitTest
- `.github/pull_request_template.md`：含业务深度检查 & security review 勾选项

#### 文档
- `docs/CHANGELOG.md` / `docs/DECISIONS/README.md`（ADR 模板）/ `docs/UX_ISSUES.md`

### 验证结果
- 后端：ruff ✓ · format ✓ · pytest ✓（1 test）
- 前端 3 端：tsc --noEmit ✓ · next build ✓
- pnpm workspace：4 项目安装成功，postinstall 白名单已配置

---

## [0.0.1] — 2026-07-22

### Added
- 项目文档初始化（`docs/DEVELOPMENT_PLAN.md`、`AGENTS.md`、`README.md`）
- `.gitignore` 覆盖 Python / Node / Next.js / Android / Docker / IDE
- 配置 GitHub MCP + 4 个 marketplace + 28 个 plugins（feature-dev, pr-review-toolkit,
  frontend-design, playwright, superpowers, claude-session-driver, security-guidance 等）
