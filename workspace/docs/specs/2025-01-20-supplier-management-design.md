# 供应商管理系统 — 设计文档

**日期:** 2025-01-20（持续更新）  
**状态:** v1.2 迭代中  
**技术方案:** 本地 Python Flask + SQLite 网页应用（可打包为 exe 跨电脑使用）

---

## 1. 概述

为跨境电商供应链开发人员设计的本地供应商信息管理工具。核心解决三个问题：

- **供应商档案管理混乱** — 工厂/经销商的基本信息、联系人、主营分类没有统一记录
- **报价与新品数据散落** — 报价表、包装尺寸、重量等数据分散在微信/Excel/邮件里
- **新品跟进追不紧** — 问了谁、跟到哪、下次什么时候问，靠脑子记

系统完全运行在本地，数据不依赖网络，通过 U 盘即可跨电脑使用。

---

## 2. 业务流程图

```
┌────────────────────────────────────────────────────────────────────┐
│                        供应商管理全流程                              │
└────────────────────────────────────────────────────────────────────┘

  ① 新增供应商 ───────────────────────────────────────────────
  │
  │  录入：公司名、地址、联系人
  │  选择主营分类：一级→二级→三级（三级可自填，仅作标注不参与筛选）
  │     ↳ 36 个一级类目按优先级排序，13 个常用类目排在最前
  │     ↳ 支持多选（如一个工厂既做积木又做玩偶）
  │
  │  结果：保存到 suppliers 表 + supplier_categories 表
  └──────────────────────────────────────────────────────────
                   │
                   ▼
  ② 添加产品 / 导入报价 ──────────────────────────────────────
  │
  │  方式 A: 手工录入
  │  · 填写产品信息 + ERP-SKU + 包装数据 + 1688链接
  │  · 上传多张产品图片（自动按SKU建文件夹）
  │  · 录入首次报价
  │
  │  方式 B: Excel批量导入
  │  · 下载Excel模板（16列：SKU/产品名/供应商/分类/包装/报价等）
  │  · 按模板填好后上传，系统逐行解析匹配
  │  · 供应商按名称或简称自动匹配，分类按"一级→二级"自动匹配
  │  · SKU为空自动生成，重复自动跳过
  │  · 成功N条/失败M条逐行显示原因
  │
  │  结果：一条产品存 products 表，N条报价存 price_history 表
  │        图片文件存 uploads/{SKU}/，记录存 product_images 表
  └──────────────────────────────────────────────────────────
                   │
                   ▼
  ③ 比价决策 ────────────────────────────────────────────────
  │
  │  分类行情：筛选某二级分类 → 按价格排序 → 底部品类统计
  │             均价/最低/最高 一目了然
  │
  │  产品对比：勾选 2-5 个产品 → 横向对比表格
  │             报价/包装尺寸/重量/1688链接全对比
  │             最低报价列绿色高亮标记
  │
  │  价格趋势：单个产品报价历史 + 柱状图 / 涨跌金额标记
  └──────────────────────────────────────────────────────────
                   │
                   ▼
  ④ 跟进维护 ────────────────────────────────────────────────
  │
  │  跟进记录：报价咨询 / 新品问询 / 常规维护 / 其他
  │           可关联到具体产品 SKU
  │           设定下次跟进提醒日期
  │
  │  新品动态台：按供应商分组展示所有新品
  │             标注跟进状态（已跟进/待跟进）
  │             到期提醒（下次跟进日期）
  │
  │  结果：存 follow_ups 表，供应商详情页同步展示
  └──────────────────────────────────────────────────────────
```

---

## 3. 整体架构

```
┌────────────────────────────────────────────────────────────┐
│                    用户浏览器 (用户界面)                      │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌────────┐  ┌────────┐  │
│  │ 仪表盘 │  │供应商  │  │产品报  │  │新品动态│  │ 产品   │  │
│  │       │  │管理    │  │价管理  │  │台     │  │对比    │  │
│  └───────┘  └───────┘  └───────┘  └────────┘  └────────┘  │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│                  Flask 后端 (Python)                         │
│                                                             │
│  路由层: @app.route('/suppliers', '/products', ...)          │
│  业务层: CRUD + 数据校验 + Excel解析 + 分类匹配 + 价格计算   │
│  模板层: Jinja2 渲染 HTML + 原生 JS 交互                     │
│                                                             │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│                  SQLite 数据库                                 │
│                                                             │
│  supplier.db 文件                                               │
│  ├─ categories       (36一级×280+二级 + sort_order排序)      │
│  ├─ suppliers         (供应商基本信息)                        │
│  ├─ supplier_categories (多对多关联 + level3三级类目)        │
│  ├─ products          (产品+包装数据+1688链接)              │
│  ├─ price_history     (N条报价历史)                          │
│  ├─ product_images    (多张图片, 文件存 uploads/{SKU}/)      │
│  └─ follow_ups        (跟进记录+关联SKU+提醒日期)          │
└────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层次 | 选型 | 理由 |
|------|------|------|
| 后端 | Python Flask | 轻量，装好 Python 就能跑，适合单机应用 |
| 前端 | HTML + CSS + JS (Jinja2) | 不引入前端框架，对新手友好，改模板即改界面 |
| 数据库 | SQLite | 单一 .db 文件，零配置，备份即复制 |
| 图片 | 本地文件系统 `uploads/{SKU}/` | 按产品分文件夹管理 |
| Excel | openpyxl | 读写 .xlsx 文件，用于模板下载 + 批量导入 |
| 启动 | `python app.py` | 浏览器打开 http://localhost:5000 |

---

## 4. 数据模型

### 4.1 实体关系

```
categories ──< supplier_categories >── suppliers
                                          │
                                     products ──< price_history
                                          │
                                     product_images
                                          │
                                     follow_ups
```

- **categories** ↔ **suppliers**: 多对多，通过 supplier_categories 关联，附带可选的 level3
- **suppliers** → **products**: 一对多
- **products** → **price_history**: 一对多（一个产品 N 条报价）
- **products** → **product_images**: 一对多（一个产品多张图）
- **suppliers** → **follow_ups**: 一对多
- **follow_ups** → **products**: 可选关联（跟进记录可指向具体产品 SKU）

### 4.2 表结构

#### categories — 1688 类目表

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | INTEGER PK | 自动编号 | 1 |
| level1 | TEXT NOT NULL | 一级类目 | 玩具 |
| level2 | TEXT NOT NULL | 二级类目 | 积木 |
| sort_order | INT DEFAULT 0 | 排序权重 | 12 |

> 预置 36 个一级类目 / 280+ 二级类目。13 个常用类目（流行配饰、家具、礼品工艺品等）sort_order 1-13，其余 23 个 14-36。

#### suppliers — 供应商表

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | INTEGER PK | 自动编号 | 1 |
| name | TEXT NOT NULL | 公司全名 | XX玩具有限公司 |
| short_name | TEXT | 简称 | XX玩具 |
| address | TEXT | 地址 | 浙江省义乌市... |
| contact_person | TEXT | 联系人 | 张经理 |
| contact_info | TEXT | 联系方式 | 138xxxx |
| notes | TEXT | 备注 | 合作3年 |
| created_at | DATETIME | 创建时间 | |
| updated_at | DATETIME | 更新时间 | |

#### supplier_categories — 供应商-分类关联

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | INTEGER PK | 自动编号 | 1 |
| supplier_id | FK | → suppliers.id | 1 |
| category_id | FK | → categories.id | 12 |
| level3 | TEXT | 三级类目（可选，仅参考） | 大颗粒系列 |

#### products — 产品表

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| erp_sku | TEXT PK | ERP SKU（空则自动生成） | TOY-2401-001 |
| supplier_id | FK NOT NULL | → suppliers.id | 1 |
| name | TEXT NOT NULL | 产品名称 | 消防局积木 |
| category_id | FK | → categories.id | 12 |
| product_url | TEXT | 1688链接 | https://... |
| package_type | TEXT | 单套包装方式 | 彩盒 |
| package_size | TEXT | 单套包装尺寸 | 35×25×8 |
| package_weight | TEXT | 单套重量 | 580g |
| carton_size | TEXT | 外箱尺寸 | 72×52×42 |
| carton_quantity | INT | 每箱套数 | 24 |
| carton_weight | TEXT | 外箱重量 | 14.5kg |
| is_new | BOOL DEFAULT 1 | 是否新品 | 1 |
| new_product_date | DATE | 新品上架日期 | 2025-01-10 |
| notes | TEXT | 备注 | |
| created_at | DATETIME | | |
| updated_at | DATETIME | | |

#### price_history — 报价历史

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | INTEGER PK | 自动编号 | 1 |
| erp_sku | FK NOT NULL | → products.erp_sku | TOY-2401-001 |
| price | REAL NOT NULL | 报价（元） | 25.80 |
| price_date | DATE NOT NULL | 报价日期 | 2025-01-15 |
| source | TEXT | 来源 | 1月报价单 |
| notes | TEXT | 备注 | 满1000可议 |

#### product_images — 产品图片

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | INTEGER PK | 自动编号 | 1 |
| erp_sku | FK NOT NULL | → products.erp_sku | TOY-2401-001 |
| filename | TEXT NOT NULL | 文件名 | 正面.jpg |
| sort_order | INT DEFAULT 1 | 排序 | 1 |
| uploaded_at | DATETIME | 上传时间 | |

> 文件存储于 `uploads/{erp_sku}/{filename}`。图片 URL: `/uploads/{sku}/{filename}`。

#### follow_ups — 跟进记录

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | INTEGER PK | 自动编号 | 1 |
| supplier_id | FK NOT NULL | → suppliers.id | 1 |
| erp_sku | FK | → products.erp_sku（可选） | TOY-2401-001 |
| follow_date | DATE NOT NULL | 跟进日期 | 2025-01-20 |
| content | TEXT | 跟进内容 | 问了新品，下月初出 |
| follow_type | TEXT DEFAULT '常规维护' | 类型 | 新品问询 |
| is_replied | BOOL DEFAULT 0 | 已回复 | 0 或 1 |
| next_follow_date | DATE | 下次跟进提醒 | 2025-02-01 |
| created_at | DATETIME | 录入时间 | |

### 4.3 核心查询

**筛选 + 价格排序：**
```sql
SELECT p.*, s.name, ph.price
FROM products p
JOIN suppliers s ON p.supplier_id = s.id
LEFT JOIN price_history ph ON p.erp_sku = ph.erp_sku
WHERE p.category_id = ?
ORDER BY ph.price ASC
```

**品类统计：**
```sql
SELECT AVG(ph.price), MIN(ph.price), MAX(ph.price), COUNT(*)
FROM price_history ph
JOIN products p ON ph.erp_sku = p.erp_sku
WHERE p.category_id = ?
  AND ph.id IN (SELECT MAX(id) FROM price_history GROUP BY erp_sku)
```

**待跟进提醒：**
```sql
SELECT * FROM follow_ups
WHERE is_replied = 0 AND next_follow_date <= date('now')
ORDER BY next_follow_date
```

---

## 5. 功能模块

### 5.1 仪表盘
- 统计卡片：供应商总数、本月新品数、待跟进数
- 最近报价变动列表（10 条，按时间倒序）
- 快捷入口：新增供应商 / 新增产品 / 新品动态 / 产品列表

### 5.2 供应商管理
- **列表：** 分页展示，支持级联分类筛选（先选一级→再选二级）、关键词搜索（名称/简称/联系人）
- **新增/编辑：** 一级类目下拉 → 二级复选框 → 三级输入框；已选分类实时显示在摘要区，每项带 ✕ 按钮一键移除
- **详情：** 供应商档案 + 关联分类（含三级） + 关联产品列表（含最新报价+新品标记） + 跟进记录

### 5.3 产品报价管理
- **列表：** 级联筛选 + 关键词搜索 + 排序按钮（价格低→高 / 高→低 / 最新报价）
  - 底部品类统计：均价 / 最低 / 最高 / 共 N 个有报价的产品
  - 对比勾选框：选 2-5 个 → 横向对比
- **新增：** 供应商搜索过滤 + 级联分类 + 包装数据 + 多图上传 + 首次报价
- **详情：** 完整信息 + 报价历史（表格+趋势柱状图+涨跌金额） + 产品图片 + 相关跟进
- **Excel 导入：** 下载带表头的模板 → 填好后上传 → 逐行匹配入库

### 5.4 产品对比
- 在产品列表勾选 2-5 个产品 → 进入 `/products/compare?ids=...`
- 横向表格展示：报价 / 报价日期 / 分类 / 包装方式 / 包装尺寸 / 重量 / 外箱尺寸/套数/重量 / 1688链接 / 备注
- 最低报价列绿色高亮 + "💰 最低价"标记

### 5.5 新品动态台
- 按供应商分组展示所有 `is_new=1` 的产品
- 每个产品标注跟进状态（已跟进 / 待跟进）
- 显示该供应商即将到期的跟进提醒
- 无新品的供应商显示最近跟进记录

### 5.6 跟进记录
- 关联供应商 + 可选关联产品 SKU
- 类型：报价咨询 / 新品问询 / 常规维护 / 其他
- 设定下次跟进日期，仪表盘统计待跟进数

---

## 6. 技术细节

### 6.1 项目文件结构

```
workspace/
├── app.py                   ← 主程序（~1450行，全部逻辑集中）
├── requirements.txt         ← flask, openpyxl
├── supplier.db              ← SQLite 数据库（自动生成，不提交git）
├── .gitignore
├── static/style.css         ← 全局样式
├── templates/               ← Jinja2 模板
│   ├── layout.html          ← 公共布局
│   ├── index.html           ← 仪表盘
│   ├── new_products.html    ← 新品动态台
│   ├── suppliers/           ← 供应商(3个模板)
│   ├── products/            ← 产品(5个模板)
│   └── follow_ups/          ← 跟进(1个模板)
├── docs/specs/              ← 设计文档
└── uploads/                 ← 产品图片（不提交git）
```

### 6.2 路由清单

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 仪表盘 |
| `/suppliers` | GET | 供应商列表 |
| `/suppliers/<id>` | GET | 供应商详情 |
| `/suppliers/new` | GET/POST | 新增供应商 |
| `/suppliers/<id>/edit` | GET/POST | 编辑供应商 |
| `/suppliers/<id>/delete` | POST | 删除供应商 |
| `/products` | GET | 产品列表（排序+筛选+对比） |
| `/products/<sku>` | GET | 产品详情 |
| `/products/new` | GET/POST | 新增产品 |
| `/products/<sku>/edit` | GET/POST | 编辑产品 |
| `/products/<sku>/delete` | POST | 删除产品 |
| `/products/<sku>/upload-image` | POST | 上传图片 |
| `/products/<sku>/delete-image/<id>` | POST | 删除图片 |
| `/products/<sku>/add-price` | GET/POST | 新增报价 |
| `/products/<sku>/delete-price/<id>` | POST | 删除报价 |
| `/products/template` | GET | 下载 Excel 模板 |
| `/products/import` | POST | 导入 Excel |
| `/products/compare` | GET | 产品对比 |
| `/follow-ups/new` | GET/POST | 新增跟进 |
| `/follow-ups/<id>/delete` | POST | 删除跟进 |
| `/new-products` | GET | 新品动态台 |
| `/api/categories` | GET | 级联分类 API |
| `/api/search` | GET | 全局搜索 API |
| `/uploads/<path>` | GET | 查看图片 |

### 6.3 前端交互（原生 JS）

- **级联选择：** 一级下拉 `onchange` → Fetch `/api/categories?level1=玩具` → 填充二级下拉
- **供应商搜索过滤：** 输入框 `oninput` → 遍历 `<select>` 的 `option` → 按 `data-name`/`data-short` 显示/隐藏
- **对比栏：** 复选框 `onchange` → 更新 `compareSkus` 数组 → 显示/隐藏对比栏
- **分类摘要：** 复选框/三级输入 `change/input` → 遍历已选 → 生成标签 + ✕ 按钮

### 6.4 错误处理

- 表单验证：前端 required 属性 + 后端 if-not 拦截，空值时 flash 红字提示
- Excel 导入：逐行 try-except，失败行记录原因不中断，成功行才 commit
- 图片上传：限制扩展名 jpg/png/webp/gif/bmp，文件名用 `secure_filename` 清理
- 数据库：外键约束 + CASCADE 删除（删除供应商同时删除关联产品和跟进）

---

## 7. 类目体系

基于 1688 平台分类体系预置，共 **36 个一级类目 / 280+ 二级类目**。

### 优先类目（排序在前）

| 一级 | 二级示例 |
|------|---------|
| 流行配饰 | 发饰、帽子、围巾披肩、手套、腰带、眼镜太阳镜、丝巾、饰品配件 |
| 家具 | 桌椅、床具、收纳柜、户外家具、办公家具、儿童家具、沙发、床垫 |
| 礼品工艺品 | 摆件、节庆礼品、手工DIY、水晶制品、工艺礼品、商务礼品、促销礼品、收藏品 |
| 家居用品 | 收纳用品、清洁用品、厨房用品、卫浴用品、雨具、家纺、家居装饰、香薰蜡烛 |
| 家电 | 厨房小电、生活电器、个护电器、大家电、厨房大家电、热水器、净化除湿、影音电器 |
| 灯具照明 | 商业照明、LED灯具、室内灯具、室外灯具、台灯落地灯、吊灯、筒灯射灯、开关插座 |
| 箱包 | 双肩包、单肩包、拉杆箱、钱包卡包、化妆包、旅行袋、手提包、斜挎包 |
| 办公文教 | 书写工具、办公纸张、文件管理、教学用品、美术用品、办公耗材、计算器电子、学生文具 |
| 橡胶塑料 | 塑料原料、橡胶原料、塑料制品、橡胶制品、工业用橡胶、塑料包装、塑料管材、密封件 |
| 运动娱乐 | 健身器材、骑行用品、帐篷露营、垂钓用具、户外照明、球类运动、瑜伽舞蹈、体育用品 |
| 五金工具 | 手动工具、电动工具、锁具、紧固件、卫浴五金、门窗五金、测量工具、磨具磨料 |
| 玩具 | 积木、模型、玩偶、拼图、遥控玩具、益智玩具、沙滩玩具、电动玩具 |
| 汽车配件 | 车用内饰、车用外饰、车载电子、维护工具、汽车保养品、轮胎轮毂、汽车灯具、汽车零部件 |

### 其他类目

农业、服装、美容与个人护理、商务服务、化工、建筑、消费电子、电气设备、电子元器件、能源、环保、定制加工、食品饮料、医药保健、机械、矿物冶金、包装印刷、促销品、安全防护、服务设备、鞋类配件、纺织皮革、钟表珠宝

---

## 8. 安装与使用

### 运行环境
- Python 3.9+
- `pip install flask openpyxl`

### 启动
```bash
cd workspace
python app.py
# 浏览器打开 http://localhost:5000
```

首次启动自动创建 `supplier.db` 并预置全部类目数据。

### 跨电脑迁移
- 方案一（推荐）：U 盘拷贝整个 `workspace/` 目录，公司电脑装 Python 后直接运行
- 方案二：PyInstaller 打包为 exe（`pip install pyinstaller` → `pyinstaller --onefile app.py`），公司电脑无需 Python

### 数据备份
只需备份两个文件/文件夹：
- `supplier.db` — 全部结构化数据
- `uploads/` — 产品图片

---

## 9. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2025-01 | 初始版本：供应商/产品/报价/跟进/新品动态 |
| v1.1 | 2025-06 | 36 类目扩展、级联筛选、三级类目、供应商搜索过滤 |
| v1.2 | 2025-06 | 分类标签 ✕ 移除、Excel 导入、比价排序、产品对比页 |
| v1.3 | 2025-06 | 报价表文件管理、编辑供应商分类丢失Bug修复 |
| v1.3.1 | 2025-06 | 报价表改为平层目录、中文文件命名、📂一键打开文件夹 |
| v1.4 | 2025-06 | 仪表盘改造：待办提醒+品类分布+报价变动、双列布局 |
