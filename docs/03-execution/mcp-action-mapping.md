# MCP 动作映射（上传执行器）

版本：v1.1  
更新时间：2026-04-03（Asia/Shanghai）  
责任模块：chrome-mcp-worker

## 目标

将 `upload_executor` 的业务步骤映射到 Chrome-MCP 原子动作，作为 `ChromeMCPBrowserAdapter` 的实现标准。

## 步骤映射

1. `open_new_product_page`
   - MCP: `navigate_page` 或 `new_page`
   - 结果: 到达新建商品页面并可交互

2. `set_category`
   - MCP: `click` + `fill/type_text` + `click`
   - 结果: 末级类目选中

3. `set_brand`
   - MCP: `fill` + `click`
   - 结果: 品牌候选已选中

4. `set_product_names`
   - MCP: `fill_form` 或多次 `fill`
   - 结果: 名称和简称都写入

5. `set_primary_spec`
   - MCP: `fill` / `click`
   - 结果: 规格名、规格值、条码已写入

6. `set_prices`
   - MCP: `fill`
   - 结果: 售价与划线价已写入

7. `upload_main_images`
   - MCP: `upload_file`
   - 结果: 图片上传成功标识出现

8. `set_description`
   - MCP: `fill`
   - 结果: 描述写入完成

9. `save_draft`
   - MCP: `click` + `wait_for`
   - 结果: 出现“保存成功/创建成功”提示

10. `capture_screenshot`
    - MCP: `take_screenshot`
    - 结果: 每步关键证据落盘

## 选择器策略

1. 优先稳定属性：`data-testid`, `data-qa`。
2. 次选控件语义：`placeholder`, `aria-label`。
3. 最后使用文本锚点或层级路径。
4. 每个控件必须配置主备选择器。

## 失败策略

1. 单步骤重试最多 2 次。
2. 主选择器失败后切备用选择器。
3. 连续 3 个商品失败触发批次暂停。

## Bridge 对接规范

执行器通过 `--mcp-action-cmd` 调用桥接命令，协议如下：
1. 调用形式：`<bridge_cmd> <action_name>`
2. 入参：stdin JSON（包含业务字段与选择器信息）
3. 出参：stdout JSON
4. 失败：非 0 退出码 + stderr 错误信息

示例（本地联调）：
1. `python3 tools/mock_mcp_action_bridge.py open_new_product_page`
2. stdin 输入对应 payload JSON
3. stdout 返回动作结果 JSON

真实桥接（Chrome 远程调试）：
1. `node tools/chrome_mcp_action_bridge.mjs <action_name>`
2. 默认连接 `http://127.0.0.1:9222`，可用 `CHROME_REMOTE_URL` 覆盖

## 运行时控制参数

1. `--step-retries`：每步失败重试次数
2. `--step-retry-backoff-ms`：重试退避时间
3. `--max-consecutive-failures`：连续失败熔断阈值
4. `--item-delay-min-ms` / `--item-delay-max-ms`：商品间隔限速
