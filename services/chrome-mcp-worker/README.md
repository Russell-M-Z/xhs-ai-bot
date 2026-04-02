# chrome-mcp-worker

Chrome-MCP execution layer for product upload.

## What is implemented in V1

1. `upload_executor` CLI to run product upload tasks from CSV.
2. Input validation for required product fields.
3. Step-based execution pipeline with per-step retries.
4. Batch controls: delay randomization + consecutive-failure circuit breaker.
5. Report output as JSON under `runs/reports/`.
6. MCP action bridge mode (`--mode mcp`) for real browser integration.
7. Auto-debug mode to invoke Codex automatically when failures occur.

## Directory layout

- `upload_executor/`: executor, validator, adapters, CLI
- `configs/selector-map.example.json`: selector map template
- `tools/chrome_mcp_action_bridge.mjs`: real bridge via Chrome remote debugging
- `tools/mock_mcp_action_bridge.py`: local mock bridge for mcp-mode testing
- `runs/`: runtime outputs (reports/artifacts)

## Prepare real bridge

1. Install node dependencies:

```bash
cd services/chrome-mcp-worker/tools
npm install
```

2. Start Chrome with remote debugging (macOS example):

```bash
/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\
  --remote-debugging-port=9222 \\
  --user-data-dir=/tmp/xhs-chrome-profile
```

## Run (dry-run)

```bash
cd services/chrome-mcp-worker
python3 -m upload_executor \
  --input ../../docs/03-execution/templates/product-upload-template.csv \
  --selector-map configs/selector-map.example.json \
  --output-dir runs \
  --mode dry-run \
  --item-delay-min-ms 0 \
  --item-delay-max-ms 0
```

## Run (mcp mode + mock bridge)

```bash
cd services/chrome-mcp-worker
python3 -m upload_executor \
  --input ../../docs/03-execution/templates/product-upload-template.csv \
  --selector-map configs/selector-map.example.json \
  --output-dir runs \
  --mode mcp \
  --mcp-action-cmd "python3 tools/mock_mcp_action_bridge.py" \
  --item-delay-min-ms 0 \
  --item-delay-max-ms 0
```

## Run (mcp mode + real bridge)

```bash
cd services/chrome-mcp-worker
python3 -m upload_executor \
  --input ../../docs/03-execution/templates/product-upload-template.csv \
  --selector-map configs/selector-map.example.json \
  --output-dir runs \
  --mode mcp \
  --mcp-action-cmd "node tools/chrome_mcp_action_bridge.mjs" \
  --item-delay-min-ms 3000 \
  --item-delay-max-ms 8000
```

## Bridge contract for real MCP integration

Your bridge command receives one action at a time:
1. Called as: `<bridge_cmd> <action_name>`
2. Reads JSON payload from stdin
3. Returns JSON from stdout
4. Exit code `0` means success, non-zero means failure

Required actions:
1. `open_new_product_page`
2. `set_category`
3. `set_brand`
4. `set_product_names`
5. `set_primary_spec`
6. `set_prices`
7. `upload_main_images`
8. `set_description`
9. `save_draft` (should return `{"toast": "..."}`)
10. `capture_screenshot` (should return `{"path": "/abs/path"}`)

## Useful runtime options

1. `--step-retries` / `--step-retry-backoff-ms`
2. `--max-consecutive-failures`
3. `--item-delay-min-ms` / `--item-delay-max-ms`
4. `--random-seed`
5. `--mcp-timeout-sec`
6. `--auto-debug-on-failure`
7. `--auto-debug-timeout-sec`
8. `--auto-debug-cmd`

## Auto-debug (invoke Codex on failure)

When `--auto-debug-on-failure` is enabled and the batch has failures/validation errors/pause:
1. An incident file is generated under `<output-dir>/incidents/<run_id>.json`
2. Codex is invoked automatically to troubleshoot and fix
3. Execution result is written back to report field `auto_debug`

Example:

```bash
cd services/chrome-mcp-worker
python3 -m upload_executor \
  --input ../../docs/03-execution/templates/product-upload-template.csv \
  --selector-map configs/selector-map.example.json \
  --output-dir runs \
  --mode mcp \
  --mcp-action-cmd "python3 tools/mock_mcp_action_bridge.py" \
  --auto-debug-on-failure
```
