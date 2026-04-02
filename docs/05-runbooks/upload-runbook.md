# 上传运行手册（Runbook）

版本：v1.1  
更新时间：2026-04-03（Asia/Shanghai）  
责任模块：chrome-mcp-worker

## 1. 运行前检查

1. Chrome Profile 已登录并具备商品管理权限。
2. 输入文件符合模板：`docs/03-execution/templates/product-upload-template.csv`。
3. 页面关键选择器映射文件可用（后续放 `configs/selector-map.json`）。
4. 若使用真实 mcp bridge，已安装 `tools/package.json` 依赖并启动 Chrome 远程调试端口（9222）。

## 2. 标准执行流程

1. 读取 CSV 并校验必填字段。
2. 打开商品管理页面并等待关键元素。
3. 按字段顺序填充：分类 -> 品牌 -> 名称 -> 规格 -> 价格 -> 图片 -> 描述。
4. 点击保存草稿/创建。
5. 读取结果提示并截图。
6. 写入执行日志。

执行命令（dry-run）：

```bash
cd /Users/russell/Desktop/店铺管理工具/xhs-ai-bot/services/chrome-mcp-worker
python3 -m upload_executor \
  --input ../../docs/03-execution/templates/product-upload-template.csv \
  --selector-map configs/selector-map.example.json \
  --output-dir runs \
  --mode dry-run \
  --item-delay-min-ms 0 \
  --item-delay-max-ms 0
```

执行命令（mcp + mock bridge）：

```bash
cd /Users/russell/Desktop/店铺管理工具/xhs-ai-bot/services/chrome-mcp-worker
python3 -m upload_executor \
  --input ../../docs/03-execution/templates/product-upload-template.csv \
  --selector-map configs/selector-map.example.json \
  --output-dir runs \
  --mode mcp \
  --mcp-action-cmd "python3 tools/mock_mcp_action_bridge.py" \
  --item-delay-min-ms 0 \
  --item-delay-max-ms 0
```

执行命令（mcp + real bridge）：

```bash
cd /Users/russell/Desktop/店铺管理工具/xhs-ai-bot/services/chrome-mcp-worker
python3 -m upload_executor \
  --input ../../docs/03-execution/templates/product-upload-template.csv \
  --selector-map configs/selector-map.example.json \
  --output-dir runs \
  --mode mcp \
  --mcp-action-cmd "node tools/chrome_mcp_action_bridge.mjs"
```

## 3. 常见问题与处理

1. 页面元素找不到：
   - 切换备用选择器。
   - 保存页面快照并更新 selector-map。
2. 上传图片失败：
   - 检查图片 URL 可访问性与格式。
   - 检查图片尺寸和大小是否符合平台要求。
3. 提交无响应：
   - 检查登录状态。
   - 刷新页面后重试单商品任务。
4. 连续失败：
   - 自动暂停批次任务。
   - 人工排查后再恢复。
5. mcp 模式报错 `requires --mcp-action-cmd`：
   - 增加桥接命令参数。
   - 先用 mock bridge 验证链路，再切换真实桥接命令。
6. real bridge 报错 `failed to connect Chrome remote debugging endpoint`：
   - 启动带 `--remote-debugging-port=9222` 的 Chrome。
   - 或设置环境变量 `CHROME_REMOTE_URL` 指向可用端口。
7. 失败后自动调试未触发：
   - 确认已加 `--auto-debug-on-failure`。
   - 检查 `report.auto_debug` 的 `status` 与 `stderr_tail`。

## 4. 日志与证据

1. 每商品必须保留：任务ID、external_id、步骤耗时、错误码。
2. 提交前后关键截图必须保留。
3. 批次任务输出成功率、失败分类、重试次数。

## 5. 自动调试机制（Codex）

触发条件：
1. `failed_tasks > 0`
2. 或存在 `validation_errors`
3. 或批次因熔断暂停 `paused=true`

行为：
1. 自动生成故障上下文文件：`<output-dir>/incidents/<run_id>.json`
2. 自动调用 `codex exec` 执行排查和修复
3. 调试执行结果回写到报告 `auto_debug` 字段

可选参数：
1. `--auto-debug-timeout-sec`
2. `--auto-debug-cmd`（自定义命令，支持 `{incident_path}` 与 `{workspace_root}` 占位符）
