# 供应商管理系统 (Supply Chain Master)

跨境电商供应链开发的本地供应商信息管理工具。

## 技术栈

- **后端:** Python 3.9+ / Flask
- **数据库:** SQLite（单文件，零配置）
- **前端:** Jinja2 模板 + 原生 JavaScript
- **运行方式:** 本地浏览器打开，数据不上传云端

## 快速开始

```bash
git clone https://github.com/PinkMeowFist/supplier-management-design.git
cd supplier-management-design/workspace
pip install flask
python app.py
# 浏览器打开 → http://localhost:5000
```

## 功能概览

| 模块 | 功能 |
|------|------|
| 仪表盘 | 供应商总数、本月新品数、待跟进数统计卡片；最近报价变动 |
| 供应商管理 | 新增/编辑/删除供应商，多选 1688 类目（36 一级 × 280+ 二级带三级自定义） |
| 产品报价管理 | 产品 CRUD、报价历史（支持多次报价+价格趋势图）、多图上传、包装数据 |
| 新品动态台 | 按供应商分组展示新品、跟进状态标注、下次跟进日期提醒 |
| 跟进记录 | 关联产品 SKU、多种跟进类型（报价咨询/新品问询等）、下次跟进日期 |
| 搜索筛选 | 全局搜索、供应商/产品列表级联筛选（先选一级类目再选二级） |

## 类目体系

预置 36 个一级类目（基于 1688 平台），涵盖约 280+ 个二级类目：

**优先类目（排在前面）：** 流行配饰、家具、礼品工艺品、家居用品、家电、灯具照明、箱包、办公文教、橡胶塑料、运动娱乐、五金工具、玩具、汽车配件

其余：农业、服装、美容与个人护理、商务服务、化工、建筑、消费电子、电气设备、电子元器件、能源、环保、定制加工、食品饮料、医药保健、机械、矿物冶金、包装印刷、促销品、安全防护、服务设备、鞋类配件、纺织皮革、钟表珠宝

## 数据模型

```
suppliers ──< supplier_categories >── categories
suppliers ──< products ──< price_history
products  ──< product_images
suppliers ──< follow_ups
```

7 张表，涵盖供应商档案、产品信息、报价历史、图片管理、跟进追踪。

## 开发进度

| 版本 | 日期 | 内容 |
|------|------|------|
| v1.0 | 2025-01 | 初始版本：供应商/产品/报价/跟进/新品动态 |
| v1.1 | 2025-06 | 36 类目扩展、级联筛选、三级类目、供应商搜索过滤 |
| v1.2 | 2025-06 | 分类标签支持 ✕ 直接移除 |

## 打包为 exe（可选）

```bash
pip install pyinstaller
pyinstaller --onefile --add-data "templates;templates" app.py
```

生成 `dist/app.exe`，公司电脑无需安装 Python，双击即用。数据文件 `supplier.db` 和 `uploads/` 文件夹拷贝即可迁移。

## 设计文档

详见 [docs/specs/2025-01-20-supplier-management-design.md](workspace/docs/specs/2025-01-20-supplier-management-design.md)

## License

MIT
