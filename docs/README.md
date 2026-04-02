# xhs-ai-bot 文档中心

本目录是项目唯一文档主入口（Single Source of Truth）。

## 文档结构

1. `01-architecture/`：系统架构与模块边界
2. `02-standards/`：业务规范与平台规则
3. `03-execution/`：执行清单、任务模板、落地步骤
4. `04-capability/`：能力矩阵、建设计划、里程碑
5. `05-runbooks/`：运行手册与故障处置

## 当前关键文档

1. `01-architecture/system-architecture.md`
2. `02-standards/product-upload-spec.md`
3. `03-execution/mcp-upload-v1-checklist.md`
4. `03-execution/mcp-action-mapping.md`
5. `03-execution/templates/product-upload-template.csv`
6. `04-capability/capability-matrix.md`
7. `04-capability/capability-build-plan.md`
8. `05-runbooks/upload-runbook.md`

## 文档管理规则

1. 新功能必须先补 `02-standards` 或 `03-execution` 文档再开发。
2. 涉及架构边界调整，必须同步更新 `01-architecture`。
3. 每次迭代结束，更新 `04-capability` 的能力状态（Planned/In Progress/Ready）。
4. 线上问题复盘必须沉淀到 `05-runbooks`。
5. 对外共享文档，默认引用本目录路径，不再引用项目外散落文件。

## 版本约定

1. 规范类文档：`v主版本.次版本`（例如 v1.1）。
2. 执行清单：按迭代编号（例如 `v1`, `v1.1`）。
3. 每个文档头部保留：`版本`、`更新时间`、`责任模块`。
