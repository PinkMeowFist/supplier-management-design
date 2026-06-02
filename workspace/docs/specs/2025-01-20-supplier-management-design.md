# 供应商管理系统 — 设计文档

**日期:** 2025-01-20  
**状态:** v1.0 已完成  
**技术方案:** 本地 Python Flask + SQLite 网页应用（可打包为 exe 跨电脑使用）

---

## 1. 概述

为跨境电商供应链开发人员设计的本地供应商信息管理系统，解决供应商档案管理混乱、产品报价与新品数据难以追溯的问题。

系统完全运行在本地，数据不依赖网络或云端服务，通过 U 盘即可在办公室与家庭电脑之间迁移。

---

## 2. 整体架构

```
浏览器 (用户界面)          ←→        Flask后端 (Python)          ←→        SQLite数据库 (本地文件)
  供应商管理页                         REST API 路由                      supplier.db
  产品报价管理页                       业务逻辑层                          uploads/ 
  新品动态台                                                               └── 按SKU的图片文件夹
  搜索与筛选
```

| 层次 | 技术 | 描述 |
|------|------|------|
| 前端 | HTML + CSS + JS (Jinja2模板) | 浏览器打开页面，无需安装额外软件 |
| 后端 | Python Flask | 处理请求，存取数据，返回页面 |
| 数据库 | SQLite | 单一 `.db` 文件，零配置，备份即复制 |
| 图片存储 | 本地文件系统 | `uploads/{SKU}/` 按产品管理图片 |

**启动方式:** `python app.py` → 浏览器打开 `http://localhost:5000`

---

## 3. 数据模型

共 7 张表，覆盖完整业务场景。

### 3.1 供应商表 (suppliers)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自动编号 |
| name | TEXT | 公司全名 |
| short_name | TEXT | 简称（可选） |
| address | TEXT | 地址 |
| contact_person | TEXT | 联系人 |
| contact_info | TEXT | 电话/微信 |
| notes | TEXT | 备注 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 最后修改时间 |

### 3.2 分类表 (categories)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自动编号 |
| level1 | TEXT | 一级分类 |
| level2 | TEXT | 二级分类 |

> 基于 1688 类目体系预置，含玩具、五金、家具、小电器、服饰、箱包等 14+ 一级分类。

### 3.3 供应商-分类关联表 (supplier_categories)

多对多关系：一个供应商可属多个分类。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自动编号 |
| supplier_id | INTEGER FK | 关联供应商 |
| category_id | INTEGER FK | 关联分类 |

### 3.4 产品表 (products)

| 字段 | 类型 | 说明 |
|------|------|------|
| erp_sku | TEXT PK | ERP SKU编号，可为空 |
| supplier_id | INTEGER FK | 所属供应商 |
| name | TEXT | 产品全称 |
| category_id | INTEGER FK | 关联二级分类 |
| product_url | TEXT | 1688商品链接 |
| package_type | TEXT | 单套包装方式 |
| package_size | TEXT | 单套包装尺寸 |
| package_weight | TEXT | 单套重量 |
| carton_size | TEXT | 外箱尺寸 |
| carton_quantity | INTEGER | 每箱套数 |
| carton_weight | TEXT | 外箱重量 |
| is_new | BOOLEAN | 是否新品 |
| new_product_date | DATE | 新品上架日期 |
| notes | TEXT | 备注 |

### 3.5 报价历史表 (price_history)

一个产品 N 条报价，追踪价格变动。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自动编号 |
| erp_sku | TEXT FK | 关联产品 |
| price | DECIMAL | 报价（元） |
| price_date | DATE | 报价日期 |
| source | TEXT | 来源 |
| notes | TEXT | 备注 |

### 3.6 产品图片表 (product_images)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自动编号 |
| erp_sku | TEXT FK | 关联产品 |
| filename | TEXT | 图片文件名 |
| sort_order | INTEGER | 排序 |

### 3.7 跟进记录表 (follow_ups)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自动编号 |
| supplier_id | INTEGER FK | 关联供应商 |
| erp_sku | TEXT FK | 关联产品SKU（可选） |
| follow_date | DATE | 跟进日期 |
| content | TEXT | 跟进内容 |
| follow_type | TEXT | 类型：报价咨询/新品问询/常规维护/其他 |
| is_replied | BOOLEAN | 是否已回复 |
| next_follow_date | DATE | 下次跟进提醒 |

### 3.8 数据关系

```
供应商 ──< 供应商-分类关联 >── 分类
供应商 ──< 产品                (一对多)
产品   ──< 报价历史            (一对多)
产品   ──< 产品图片            (一对多)
供应商 ──< 跟进记录            (一对多)
跟进记录 ---> 产品SKU          (可选关联)
```

---

## 4. 功能页面

| 页面 | 功能 |
|------|------|
| 仪表盘 | 统计卡片（供应商总数/本月新品/待跟进）、最近报价变动、快捷入口 |
| 供应商管理 | 列表+搜索筛选、详情（产品+跟进）、新增/编辑（多选1688分类） |
| 产品报价管理 | 列表+多条件筛选、详情（包装数据+图片+报价历史+趋势图）、CRUD |
| 搜索 | 全局搜索+列表页组合筛选（分类/供应商/仅新品） |
| 新品动态台 | 按供应商分组展示新品、跟进状态标注、下次跟进提醒 |
| 跟进记录 | 关联产品SKU、多种跟进类型、下次跟进日期设定 |

---

## 5. 数据录入流程

1. **新增供应商:** 填写信息 → 勾选分类（支持多选） → 保存
2. **录入新品:** 填写产品+包装数据+1688链接 → 上传图片 → 填报价 → 保存
3. **更新报价:** 产品详情页 → 报价历史 → 新增报价 → 保留历史
4. **记录跟进:** 供应商详情页 → 新增跟进 → 选类型+关联产品+设定提醒

---

## 6. 技术细节

### 运行环境
- Python 3.9+
- `pip install flask`
- SQLite3（Python 内置）

### 启动
```bash
python app.py
# 浏览器打开 http://localhost:5000
```

### 数据安全
- 全部数据存储本地 `supplier.db` + `uploads/`
- 备份 = 复制这两个文件/文件夹

### 打包 exe（可选）
```bash
pip install pyinstaller
pyinstaller --onefile --add-data "templates;templates" app.py
```
生成 `dist/app.exe`，无需 Python 即可运行。

---

## 7. 错误处理

- 表单前后端双重校验，必填项红字提示
- 数据不存在时友好提示而非白屏
- 图片上传限制格式和大小
- SQL异常捕获，不崩溃

---

## 8. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2025-01-20 | 初始版本，含供应商/产品/报价/跟进/新品动态全部功能 |
