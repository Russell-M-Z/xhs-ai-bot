# xhs-ai-bot

通过 Chrome-MCP 管理小红书店铺的 AI 辅助机器人项目。

## 文档入口

项目文档统一在：
- `docs/README.md`

请以 `docs/` 目录作为唯一规范来源（Single Source of Truth）。

## 文档分层

1. `docs/01-architecture/`：系统架构
2. `docs/02-standards/`：规则与规范
3. `docs/03-execution/`：执行清单与模板
4. `docs/04-capability/`：能力矩阵与建设计划
5. `docs/05-runbooks/`：运行手册与故障处置

## 当前重点文档

1. `docs/01-architecture/system-architecture.md`
2. `docs/02-standards/product-upload-spec.md`
3. `docs/03-execution/mcp-upload-v1-checklist.md`
4. `docs/03-execution/mcp-action-mapping.md`
5. `docs/03-execution/templates/product-upload-template.csv`
6. `docs/04-capability/capability-matrix.md`
7. `docs/04-capability/capability-build-plan.md`
8. `docs/05-runbooks/upload-runbook.md`

## 项目结构

- `apps/console-web`: 运营控制台（前端）
- `apps/orchestrator-api`: 任务编排 API
- `services/agent-core`: AI 任务规划与工具调用
- `services/rule-engine`: 规则与审批引擎
- `services/chrome-mcp-worker`: 浏览器自动化执行器
- `infra`: 本地基础依赖（PostgreSQL/Redis）
