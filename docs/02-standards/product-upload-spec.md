# 小红书商品上传流程规范（用于 MCP 自动化）

版本：v1.0  
更新日期：2026-04-02（Asia/Shanghai）

## 1. 适用范围

本规范用于“通过 MCP 自动化上传商品基础信息到小红书商品管理界面/系统”。

说明：
1. 小红书千帆商家后台页面需要登录后可见，公开可验证的“官方全流程”主要来自小红书大学开放平台文档。
2. 本规范以官方商品结构与商品 API 流程为基线，作为你后续 Chrome-MCP 执行任务的标准。

---

## 2. 官方流程基线（必须遵循）

### 2.1 上架前准备
1. 获取 app-key / app-secret（开发者页面）。
2. 按官方签名规则生成 `sign`，并在请求头带 `timestamp/app-key/sign`。
3. 使用正确环境：测试环境 `flssandbox.xiaohongshu.com`，正式环境 `ark.xiaohongshu.com`。

### 2.2 商品创建核心流程（官方推荐顺序）
1. 品牌搜索：先拿 `brand_id`（品牌不能商家自行创建）。
2. 分类查询：获取最末级 `category_id`。
3. 规格与属性查询：根据末级分类拿可用规格/属性及属性值 id。
4. 创建商品结构：
   - 可一次性创建（`创建SPU` 时同时带 SPL/SPL ITEM/SPV/ITEM）
   - 或分步创建（`创建SPU` -> `创建SPL` -> `创建SPL ITEM` -> `创建SPV` -> `创建ITEM`）
5. 提交审核：SPL ITEM（创意编辑/文描）需要单独提交审核。
6. 上下架：审核通过后设置 ITEM `available=true` 进行上架（实际可售看 `buyable`）。
7. （可选）库存同步：通过 item_id 或 barcode 设置库存。

### 2.3 状态判定（发布成功标准）
1. `available=true` 表示可操作上架。
2. `buyable=true` 表示实际可售（最终前台状态）。
3. 审核相关状态需结合商品状态码判断（如待审核、已审核、审核不通过）。

---

## 3. 商品“基础信息”最小字段规范（MVP）

## 3.1 必备主数据
1. 品牌：`brand_id`
2. 分类：`category_id`（必须末级）
3. 商品名称：`spu.name`
4. 商品简称：`spu.short_name`（不超过 15 个中文字符）

## 3.2 规格与销售信息（至少一组 SKU）
1. SPL 规格：`spl.variants[]`（按类目规则 1~2 个）
2. SPV 基础：`barcode`、`qty`（注意是“内含数量”不是库存）、`unit`
3. ITEM 价格：
   - 非跨境：`price` + `original_price`
   - 跨境税：`pre_tax_price`（并按规则带税前/税后字段）

## 3.3 图文信息（决定审核通过与可售）
1. 商品主图：`spl_item.image_urls[]`
2. 商品描述：`spl_item.desc`
3. 商品特色：`spl_item.feature`（不超过 8 字）
4. 图文详情/使用指南：`image_desc`、`user_guide`（建议）

---

## 4. 官方规则约束（上传时必须校验）

1. 文描字段不要带 HTML 标签，换行用 `\n`。
2. 图片必须符合官方规格，否则可能“接口成功但后台不展示”：
   - 商品图：800x800 或 750x1000；JPG/PNG/JPEG；比例 1:1 或 3:4
   - 详情/使用指南图：宽 750~1242px，高 <= 1546px
   - 详情图单张 <= 2MB
3. 属性/规格建议优先传 `value_id`（若传 `value_id`，`value` 不生效）。
4. `attributes` 或 `faqs` 传 `[]` 会清空已填信息。
5. `available=true` 不等于一定可售，仍需满足图片/描述/备案等条件。
6. 不同物流模式下库存同步能力有差异（Red Express/Red Post/国内贸易不支持库存同步与增减库存接口）。

---

## 5. MCP 自动化执行规范（落地到“商品管理界面”）

说明：以下步骤是把官方“数据流程”映射成 MCP 任务编排标准。

1. 任务入参校验
   - 校验必填：品牌、末级分类、名称、至少一个 SKU、价格、主图。
   - 校验规则：名称长度、图片规格、价格非负。

2. 资料预处理
   - 先补齐 id 映射：`brand_id`、`category_id`、规格 id、属性 id、value_id。
   - 生成标准化 payload（SPU/SPL/SPL_ITEM/SPV/ITEM）。

3. 创建商品
   - 优先一次性创建（减少中间失败点）。
   - 若失败则降级分步创建并记录每步返回 id。

4. 提交审核
   - 对 SPL ITEM 调用提交审核。
   - 轮询商品状态，直到“已审核”或“审核不通过”。

5. 上架与库存
   - 审核通过后设置 `available=true`。
   - 根据物流模式决定是否调用库存同步。

6. 审计与回放
   - 记录：任务号、请求参数摘要、返回 id、状态流转、失败原因。
   - 保存关键截图/页面快照（若走 UI 自动化）。

---

## 6. 异常处理规范

1. 401/403：优先检查环境 host 与 app-key 是否匹配，再校验 sign。
2. 审核失败：回收失败原因 -> 回写“文描修正任务” -> 人工复核后重提。
3. 部分创建成功：按返回 id 做幂等续跑，禁止整单盲目重建。
4. 上架失败且 `buyable=false`：检查图片、描述、备案、状态码。

---

## 7. 验收标准（针对“基础信息上传”）

1. 100% 能生成有效 item_id。
2. 95% 以上商品可在 10 分钟内走完“创建->提审->上架请求”。
3. 图片/描述问题可被预校验拦截，不进入线上失败。
4. 每条任务具备可追溯日志与失败定位信息。

---

## 8. 官方来源（用于审计）

1. Product & Item APIs 总览：
   https://school.xiaohongshu.com/en/open/product/summary.html
2. 商品结构说明（含推荐步骤）：
   https://school.xiaohongshu.com/en/open/product/product-structure.html
3. 创建 SPU：
   https://school.xiaohongshu.com/en/open/product/create-spu.html
4. 创建 SPL：
   https://school.xiaohongshu.com/en/open/product/create-spl.html
5. 创建 SPL ITEM：
   https://school.xiaohongshu.com/en/open/product/create-spl-item.html
6. 创建 SPV：
   https://school.xiaohongshu.com/en/open/product/create-spv.html
7. 创建 ITEM：
   https://school.xiaohongshu.com/en/open/product/create-item.html
8. 商品提交审核：
   https://school.xiaohongshu.com/en/open/product/spl-item-submit.html
9. 上下架商品：
   https://school.xiaohongshu.com/en/open/product/availability.html
10. 商品状态码：
    https://school.xiaohongshu.com/en/open/product/product-status.html
11. 品牌搜索：
    https://school.xiaohongshu.com/en/open/common/brand-search.html
12. 分类列表：
    https://school.xiaohongshu.com/en/open/common/category-list.html
13. 由末级分类获取规格：
    https://school.xiaohongshu.com/en/open/common/category-variants.html
14. 由末级分类获取属性：
    https://school.xiaohongshu.com/en/open/common/category-attributes.html
15. 由属性获取属性值：
    https://school.xiaohongshu.com/en/open/common/attributes-values.html
16. 编辑 ITEM 物流模式：
    https://school.xiaohongshu.com/en/open/product/update-item-logistics.html
17. 同步库存：
    https://school.xiaohongshu.com/en/open/inventory/sync.html
18. 接入流程与参数：
    https://school.xiaohongshu.com/en/open/quick-start/workflow.html
    https://school.xiaohongshu.com/en/open/quick-start/system-parameter.html
    https://school.xiaohongshu.com/en/open/quick-start/sign.html
