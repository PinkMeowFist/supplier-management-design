"""供应商管理系统 - Flask 主程序"""
import os
import shutil
import sqlite3
import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, send_from_directory
)

app = Flask(__name__)
app.secret_key = 'supplier-mgmt-secret-key-2025'

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'supplier.db'
UPLOAD_DIR = BASE_DIR / 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================
# 数据库工具
# ============================================================

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """建表 + 预置分类"""
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level1 TEXT NOT NULL,
            level2 TEXT NOT NULL,
            UNIQUE(level1, level2)
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT,
            address TEXT,
            contact_person TEXT,
            contact_info TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT (datetime('now','localtime')),
            updated_at DATETIME DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS supplier_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
            UNIQUE(supplier_id, category_id)
        );

        CREATE TABLE IF NOT EXISTS products (
            erp_sku TEXT PRIMARY KEY,
            supplier_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category_id INTEGER,
            product_url TEXT,
            package_type TEXT,
            package_size TEXT,
            package_weight TEXT,
            carton_size TEXT,
            carton_quantity INTEGER,
            carton_weight TEXT,
            is_new INTEGER DEFAULT 1,
            new_product_date DATE,
            notes TEXT,
            created_at DATETIME DEFAULT (datetime('now','localtime')),
            updated_at DATETIME DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            erp_sku TEXT NOT NULL,
            price REAL NOT NULL,
            price_date DATE NOT NULL,
            source TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (erp_sku) REFERENCES products(erp_sku) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            erp_sku TEXT NOT NULL,
            filename TEXT NOT NULL,
            sort_order INTEGER DEFAULT 1,
            uploaded_at DATETIME DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (erp_sku) REFERENCES products(erp_sku) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            erp_sku TEXT,
            follow_date DATE NOT NULL,
            content TEXT,
            follow_type TEXT DEFAULT '常规维护',
            is_replied INTEGER DEFAULT 0,
            next_follow_date DATE,
            created_at DATETIME DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
            FOREIGN KEY (erp_sku) REFERENCES products(erp_sku) ON DELETE SET NULL
        );
    ''')

    # ---- 预置1688分类数据 ----
    default_cats = [
        ('玩具', '积木'), ('玩具', '模型'), ('玩具', '玩偶'), ('玩具', '拼图'),
        ('玩具', '遥控玩具'), ('玩具', '益智玩具'), ('玩具', '沙滩玩具'),
        ('五金', '手动工具'), ('五金', '电动工具'), ('五金', '锁具'), ('五金', '紧固件'),
        ('五金', '卫浴五金'), ('五金', '门窗五金'),
        ('家具', '桌椅'), ('家具', '床具'), ('家具', '收纳柜'), ('家具', '户外家具'),
        ('家具', '办公家具'), ('家具', '儿童家具'),
        ('小电器', '厨房小电'), ('小电器', '生活电器'), ('小电器', '个护电器'),
        ('小电器', '数码配件'), ('小电器', '灯具'),
        ('服饰', '女装'), ('服饰', '男装'), ('服饰', '童装'), ('服饰', '内衣'),
        ('服饰', '运动服装'), ('服饰', '袜子手套'),
        ('箱包', '双肩包'), ('箱包', '单肩包'), ('箱包', '拉杆箱'), ('箱包', '钱包卡包'),
        ('箱包', '化妆包'), ('箱包', '旅行袋'),
        ('日用百货', '收纳用品'), ('日用百货', '清洁用品'), ('日用百货', '厨房用品'),
        ('日用百货', '卫浴用品'), ('日用百货', '雨具'),
        ('家纺', '床品套件'), ('家纺', '被芯'), ('家纺', '枕芯'), ('家纺', '凉席'),
        ('家纺', '窗饰'),
        ('礼品工艺品', '摆件'), ('礼品工艺品', '节庆礼品'), ('礼品工艺品', '手工DIY'),
        ('礼品工艺品', '水晶制品'),
        ('母婴', '喂养用品'), ('母婴', '洗护用品'), ('母婴', '安全用品'), ('母婴', '出行用品'),
        ('运动户外', '健身器材'), ('运动户外', '骑行用品'), ('运动户外', '帐篷露营'),
        ('运动户外', '垂钓用具'),
        ('汽摩配', '车用内饰'), ('汽摩配', '车用外饰'), ('汽摩配', '车载电子'),
        ('汽摩配', '维护工具'),
    ]
    existing = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if existing == 0:
        conn.executemany(
            "INSERT INTO categories (level1, level2) VALUES (?, ?)",
            default_cats
        )
    conn.commit()
    conn.close()


# ============================================================
# 辅助函数
# ============================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_latest_price(sku):
    """获取产品最新报价"""
    db = get_db()
    row = db.execute(
        "SELECT price, price_date FROM price_history WHERE erp_sku=? ORDER BY price_date DESC LIMIT 1",
        (sku,)
    ).fetchone()
    db.close()
    return row


def get_price_change(sku):
    """获取最近两次报价的变化量"""
    db = get_db()
    rows = db.execute(
        "SELECT price FROM price_history WHERE erp_sku=? ORDER BY price_date DESC LIMIT 2",
        (sku,)
    ).fetchall()
    db.close()
    if len(rows) == 2:
        return round(rows[0]['price'] - rows[1]['price'], 2)
    return None


# ============================================================
# 前端 - 自动启动页面
# ============================================================

@app.route('/')
def index():
    """仪表盘首页"""
    db = get_db()
    supplier_count = db.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    today = datetime.date.today()
    month_start = today.replace(day=1).isoformat()
    new_count = db.execute(
        "SELECT COUNT(*) FROM products WHERE is_new=1 AND new_product_date >= ?",
        (month_start,)
    ).fetchone()[0]
    pending_count = db.execute(
        "SELECT COUNT(*) FROM follow_ups WHERE is_replied=0 AND next_follow_date <= ?",
        (today.isoformat(),)
    ).fetchone()[0]

    # 最近报价变动
    recent_prices = db.execute('''
        SELECT p.erp_sku, p.name, ph.price, ph.price_date,
               s.short_name, s.name as supplier_name
        FROM price_history ph
        JOIN products p ON ph.erp_sku = p.erp_sku
        JOIN suppliers s ON p.supplier_id = s.id
        WHERE ph.id IN (
            SELECT MAX(id) FROM price_history GROUP BY erp_sku
        )
        ORDER BY ph.price_date DESC LIMIT 10
    ''').fetchall()
    db.close()
    return render_template('index.html',
                           supplier_count=supplier_count,
                           new_count=new_count,
                           pending_count=pending_count,
                           recent_prices=recent_prices)


# ============================================================
# 供应商模块
# ============================================================

@app.route('/suppliers')
def supplier_list():
    """供应商列表"""
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', '').strip()
    db = get_db()

    query = '''SELECT DISTINCT s.*, GROUP_CONCAT(c.level2, '、') as cats
               FROM suppliers s
               LEFT JOIN supplier_categories sc ON s.id = sc.supplier_id
               LEFT JOIN categories c ON sc.category_id = c.id'''
    conditions = []
    params = []

    if search:
        conditions.append(
            "(s.name LIKE ? OR s.short_name LIKE ? OR s.contact_person LIKE ? OR s.contact_info LIKE ?)"
        )
        like = f'%{search}%'
        params.extend([like, like, like, like])

    if category_id:
        conditions.append("s.id IN (SELECT supplier_id FROM supplier_categories WHERE category_id=?)")
        params.append(category_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY s.id ORDER BY s.updated_at DESC"
    suppliers = db.execute(query, params).fetchall()

    # 获取每个供应商的关联分类，转成字典列表以便模板访问
    supplier_list = []
    for s in suppliers:
        sdict = dict(s)
        cats = db.execute('''
            SELECT c.level1, c.level2
            FROM supplier_categories sc
            JOIN categories c ON sc.category_id = c.id
            WHERE sc.supplier_id = ?
        ''', (s['id'],)).fetchall()
        sdict['categories'] = cats
        supplier_list.append(sdict)

    categories = db.execute("SELECT * FROM categories ORDER BY level1, level2").fetchall()
    db.close()
    return render_template('suppliers/list.html',
                           suppliers=supplier_list,
                           categories=categories,
                           search=search,
                           selected_category=category_id)


@app.route('/suppliers/<int:sid>')
def supplier_detail(sid):
    """供应商详情"""
    db = get_db()
    supplier = db.execute("SELECT * FROM suppliers WHERE id=?", (sid,)).fetchone()
    if not supplier:
        flash("供应商不存在", "error")
        return redirect(url_for('supplier_list'))

    # 关联分类
    cats = db.execute('''
        SELECT c.* FROM categories c
        JOIN supplier_categories sc ON c.id = sc.category_id
        WHERE sc.supplier_id = ?
        ORDER BY c.level1, c.level2
    ''', (sid,)).fetchall()

    # 关联产品
    products = db.execute('''
        SELECT p.*, c.level1, c.level2
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.supplier_id = ?
        ORDER BY p.updated_at DESC
    ''', (sid,)).fetchall()

    # 为产品附上最新报价
    products_with_price = []
    for p in products:
        pdict = dict(p)
        pdict['cat_name'] = (p['level1'] + '→' + p['level2']) if p['level1'] else None
        latest = get_latest_price(p['erp_sku'])
        pdict['latest_price'] = latest['price'] if latest else None
        pdict['latest_price_date'] = latest['price_date'] if latest else None
        products_with_price.append(pdict)

    # 跟进记录
    follow_ups = db.execute('''
        SELECT fu.*, p.name as product_name
        FROM follow_ups fu
        LEFT JOIN products p ON fu.erp_sku = p.erp_sku
        WHERE fu.supplier_id = ?
        ORDER BY fu.follow_date DESC
    ''', (sid,)).fetchall()

    # 转成dict以避免模板中Row对象不可赋属性问题
    supplier_dict = dict(supplier)
    supplier_dict['categories'] = cats
    supplier_dict['products'] = products_with_price

    db.close()
    return render_template('suppliers/detail.html',
                           supplier=supplier_dict,
                           follow_ups=follow_ups,
                           today=datetime.date.today().isoformat())


@app.route('/suppliers/new', methods=['GET', 'POST'])
@app.route('/suppliers/add', methods=['GET', 'POST'])
def supplier_add():
    """新增供应商"""
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash("供应商名称不能为空", "error")
            return redirect(url_for('supplier_add'))

        short_name = request.form.get('short_name', '').strip()
        address = request.form.get('address', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        contact_info = request.form.get('contact_info', '').strip()
        notes = request.form.get('notes', '').strip()
        category_ids = request.form.getlist('category_ids')

        cur = db.execute(
            "INSERT INTO suppliers (name, short_name, address, contact_person, contact_info, notes) VALUES (?,?,?,?,?,?)",
            (name, short_name, address, contact_person, contact_info, notes)
        )
        sid = cur.lastrowid

        for cid in category_ids:
            db.execute("INSERT INTO supplier_categories (supplier_id, category_id) VALUES (?,?)", (sid, cid))

        db.commit()
        flash("供应商添加成功", "success")
        return redirect(url_for('supplier_detail', sid=sid))

    # 按一级分类分组
    all_cats = db.execute("SELECT * FROM categories ORDER BY level1, level2").fetchall()
    cat_tree = {}
    for cat in all_cats:
        if cat['level1'] not in cat_tree:
            cat_tree[cat['level1']] = []
        cat_tree[cat['level1']].append(cat)
    cat_tree_list = [{'level1': k, 'categories': v} for k, v in cat_tree.items()]
    db.close()
    return render_template('suppliers/form.html',
                           supplier=None,
                           cat_tree=cat_tree_list)


@app.route('/suppliers/<int:sid>/edit', methods=['GET', 'POST'])
def supplier_edit(sid):
    """编辑供应商"""
    db = get_db()
    supplier = db.execute("SELECT * FROM suppliers WHERE id=?", (sid,)).fetchone()
    if not supplier:
        flash("供应商不存在", "error")
        return redirect(url_for('supplier_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash("供应商名称不能为空", "error")
            return redirect(url_for('supplier_edit', sid=sid))

        db.execute(
            "UPDATE suppliers SET name=?, short_name=?, address=?, contact_person=?, contact_info=?, notes=?, updated_at=datetime('now','localtime') WHERE id=?",
            (name, request.form.get('short_name', '').strip(),
             request.form.get('address', '').strip(),
             request.form.get('contact_person', '').strip(),
             request.form.get('contact_info', '').strip(),
             request.form.get('notes', '').strip(), sid)
        )
        # 更新分类关联
        db.execute("DELETE FROM supplier_categories WHERE supplier_id=?", (sid,))
        for cid in request.form.getlist('category_ids'):
            db.execute("INSERT INTO supplier_categories (supplier_id, category_id) VALUES (?,?)", (sid, cid))
        db.commit()
        flash("供应商更新成功", "success")
        return redirect(url_for('supplier_detail', sid=sid))

    # 已选分类
    selected = db.execute("SELECT category_id FROM supplier_categories WHERE supplier_id=?", (sid,)).fetchall()
    selected_cat_ids = [str(r['category_id']) for r in selected]
    all_cats = db.execute("SELECT * FROM categories ORDER BY level1, level2").fetchall()
    cat_tree = {}
    for cat in all_cats:
        if cat['level1'] not in cat_tree:
            cat_tree[cat['level1']] = []
        cat_tree[cat['level1']].append(cat)
    cat_tree_list = [{'level1': k, 'categories': v} for k, v in cat_tree.items()]
    # 将 cat_ids 注入 supplier Row 以便模板访问
    supplier_dict = dict(supplier)
    supplier_dict['cat_ids'] = [int(x) for x in selected_cat_ids]
    db.close()
    return render_template('suppliers/form.html',
                           supplier=supplier_dict,
                           cat_tree=cat_tree_list)


@app.route('/suppliers/<int:sid>/delete', methods=['POST'])
def supplier_delete(sid):
    db = get_db()
    db.execute("DELETE FROM suppliers WHERE id=?", (sid,))
    db.commit()
    db.close()
    flash("供应商已删除", "success")
    return redirect(url_for('supplier_list'))


# ============================================================
# 产品模块
# ============================================================

@app.route('/products')
def product_list():
    """产品列表"""
    search = request.form.get('search', '') or request.args.get('search', '').strip()
    supplier_id = request.args.get('supplier_id', '').strip()
    category_id = request.args.get('category_id', '').strip()
    new_only = request.args.get('new_only', '').strip()
    price_changed = request.args.get('price_changed', '').strip()

    db = get_db()
    query = '''
        SELECT p.*, s.short_name as supplier_short, s.name as supplier_name,
               c.level1, c.level2
        FROM products p
        JOIN suppliers s ON p.supplier_id = s.id
        LEFT JOIN categories c ON p.category_id = c.id
    '''
    conditions = []
    params = []

    if search:
        conditions.append("(p.name LIKE ? OR p.erp_sku LIKE ? OR s.name LIKE ? OR s.short_name LIKE ?)")
        like = f'%{search}%'
        params.extend([like, like, like, like])

    if supplier_id:
        conditions.append("p.supplier_id = ?")
        params.append(supplier_id)

    if category_id:
        conditions.append("p.category_id = ?")
        params.append(category_id)

    if new_only:
        conditions.append("p.is_new = 1")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY p.updated_at DESC"
    products = db.execute(query, params).fetchall()

    # 附上最新报价和分类名称（转dict避免Row不可赋属性）
    product_list = []
    for p in products:
        pdict = dict(p)
        pdict['cat_name'] = (p['level1'] + '→' + p['level2']) if p['level1'] else None
        latest = get_latest_price(p['erp_sku'])
        pdict['latest_price'] = latest['price'] if latest else None
        pdict['latest_price_date'] = latest['price_date'] if latest else None
        pdict['price_change'] = get_price_change(p['erp_sku'])
        product_list.append(pdict)

    suppliers = db.execute("SELECT id, short_name, name FROM suppliers ORDER BY short_name").fetchall()
    categories = db.execute("SELECT * FROM categories ORDER BY level1, level2").fetchall()
    db.close()
    return render_template('products/list.html',
                           products=product_list,
                           suppliers_list=suppliers,
                           categories=categories,
                           selected_supplier=supplier_id,
                           selected_category=category_id,
                           new_only=new_only,
                           price_changed=price_changed)


@app.route('/products/<sku>')
def product_detail(sku):
    """产品详情"""
    db = get_db()
    product = db.execute('''
        SELECT p.*, s.short_name as supplier_short, s.name as supplier_name,
               s.id as supplier_id,
               c.level1, c.level2
        FROM products p
        JOIN suppliers s ON p.supplier_id = s.id
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.erp_sku = ?
    ''', (sku,)).fetchone()
    if not product:
        flash("产品不存在", "error")
        return redirect(url_for('product_list'))

    # 报价历史
    price_history = db.execute(
        "SELECT * FROM price_history WHERE erp_sku=? ORDER BY price_date DESC",
        (sku,)
    ).fetchall()

    # 产品图片
    images = db.execute(
        "SELECT * FROM product_images WHERE erp_sku=? ORDER BY sort_order",
        (sku,)
    ).fetchall()

    # 该产品的跟进记录
    follow_ups = db.execute('''
        SELECT fu.*, s.short_name as supplier_short
        FROM follow_ups fu
        JOIN suppliers s ON fu.supplier_id = s.id
        WHERE fu.erp_sku = ?
        ORDER BY fu.follow_date DESC
    ''', (sku,)).fetchall()

    # 计算分类显示名
    product_dict = dict(product)
    product_dict['cat_name'] = (product['level1'] + '→' + product['level2']) if product['level1'] else None

    db.close()
    return render_template('products/detail.html',
                           product=product_dict,
                           price_history=price_history,
                           images=images,
                           product_follow_ups=follow_ups,
                           today=datetime.date.today().isoformat())


@app.route('/products/new', methods=['GET', 'POST'])
@app.route('/products/add', methods=['GET', 'POST'])
def product_add():
    """新增产品"""
    db = get_db()
    if request.method == 'POST':
        erp_sku = request.form.get('erp_sku', '').strip() or None
        supplier_id = request.form.get('supplier_id', '').strip()
        name = request.form.get('name', '').strip()

        if not name:
            flash("产品名称不能为空", "error")
            return redirect(url_for('product_add'))

        # 如果没有填写SKU，自动生成
        if not erp_sku:
            ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            erp_sku = f"PROD-{ts}"

        # 检查SKU是否重复
        exists = db.execute("SELECT erp_sku FROM products WHERE erp_sku=?", (erp_sku,)).fetchone()
        if exists:
            flash(f"SKU '{erp_sku}' 已存在", "error")
            return redirect(url_for('product_add'))

        product_url = request.form.get('product_url', '').strip()
        category_id = request.form.get('category_id', '').strip() or None
        package_type = request.form.get('package_type', '').strip()
        package_size = request.form.get('package_size', '').strip()
        package_weight = request.form.get('package_weight', '').strip()
        carton_size = request.form.get('carton_size', '').strip()
        carton_quantity = request.form.get('carton_quantity', '').strip() or None
        carton_weight = request.form.get('carton_weight', '').strip()
        is_new = 1 if request.form.get('is_new', '1') == '1' else 0
        new_product_date = request.form.get('new_product_date', '').strip() or None
        notes = request.form.get('notes', '').strip()

        # 产品信息
        db.execute('''
            INSERT INTO products (erp_sku, supplier_id, name, category_id, product_url,
                package_type, package_size, package_weight, carton_size, carton_quantity,
                carton_weight, is_new, new_product_date, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (erp_sku, supplier_id, name, category_id, product_url,
              package_type, package_size, package_weight, carton_size,
              carton_quantity, carton_weight, is_new, new_product_date, notes))

        # 报价
        price = request.form.get('price', '').strip()
        if price:
            price_date = request.form.get('price_date', '').strip() or datetime.date.today().isoformat()
            price_source = request.form.get('price_source', '').strip()
            price_notes = request.form.get('price_notes', '').strip()
            db.execute(
                "INSERT INTO price_history (erp_sku, price, price_date, source, notes) VALUES (?,?,?,?,?)",
                (erp_sku, float(price), price_date, price_source, price_notes)
            )

        # 图片上传
        files = request.files.getlist('images')
        for idx, f in enumerate(files):
            if f and f.filename and allowed_file(f.filename):
                filename = secure_filename(f.filename)
                sku_dir = UPLOAD_DIR / erp_sku
                sku_dir.mkdir(parents=True, exist_ok=True)
                f.save(str(sku_dir / filename))
                db.execute(
                    "INSERT INTO product_images (erp_sku, filename, sort_order) VALUES (?,?,?)",
                    (erp_sku, filename, idx + 1)
                )

        db.commit()
        flash("产品添加成功", "success")
        return redirect(url_for('product_detail', sku=erp_sku))

    suppliers = db.execute("SELECT id, short_name, name FROM suppliers ORDER BY short_name").fetchall()
    categories = db.execute("SELECT * FROM categories ORDER BY level1, level2").fetchall()
    db.close()
    return render_template('products/form.html',
                           product=None,
                           suppliers=suppliers,
                           categories=categories,
                           selected_supplier=request.args.get('supplier_id', ''))


@app.route('/products/<sku>/edit', methods=['GET', 'POST'])
def product_edit(sku):
    """编辑产品"""
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE erp_sku=?", (sku,)).fetchone()
    if not product:
        flash("产品不存在", "error")
        return redirect(url_for('product_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash("产品名称不能为空", "error")
            return redirect(url_for('product_edit', sku=sku))

        db.execute('''
            UPDATE products SET supplier_id=?, name=?, category_id=?, product_url=?,
                package_type=?, package_size=?, package_weight=?, carton_size=?,
                carton_quantity=?, carton_weight=?, is_new=?, new_product_date=?,
                notes=?, updated_at=datetime('now','localtime')
            WHERE erp_sku=?
        ''', (
            request.form.get('supplier_id', '').strip(),
            name,
            request.form.get('category_id', '').strip() or None,
            request.form.get('product_url', '').strip(),
            request.form.get('package_type', '').strip(),
            request.form.get('package_size', '').strip(),
            request.form.get('package_weight', '').strip(),
            request.form.get('carton_size', '').strip(),
            request.form.get('carton_quantity', '').strip() or None,
            request.form.get('carton_weight', '').strip(),
            1 if request.form.get('is_new', '1') == '1' else 0,
            request.form.get('new_product_date', '').strip() or None,
            request.form.get('notes', '').strip(),
            sku
        ))

        # 新报价
        price = request.form.get('price', '').strip()
        if price:
            price_date = request.form.get('price_date', '').strip() or datetime.date.today().isoformat()
            price_source = request.form.get('price_source', '').strip()
            price_notes = request.form.get('price_notes', '').strip()
            db.execute(
                "INSERT INTO price_history (erp_sku, price, price_date, source, notes) VALUES (?,?,?,?,?)",
                (sku, float(price), price_date, price_source, price_notes)
            )

        # 新图片
        files = request.files.getlist('images')
        if files and any(f and f.filename for f in files):
            max_order = db.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM product_images WHERE erp_sku=?", (sku,)
            ).fetchone()[0]
            for idx, f in enumerate(files):
                if f and f.filename and allowed_file(f.filename):
                    filename = secure_filename(f.filename)
                    sku_dir = UPLOAD_DIR / sku
                    sku_dir.mkdir(parents=True, exist_ok=True)
                    f.save(str(sku_dir / filename))
                    db.execute(
                        "INSERT INTO product_images (erp_sku, filename, sort_order) VALUES (?,?,?)",
                        (sku, filename, max_order + idx + 1)
                    )

        db.commit()
        flash("产品更新成功", "success")
        return redirect(url_for('product_detail', sku=sku))

    suppliers = db.execute("SELECT id, short_name, name FROM suppliers ORDER BY short_name").fetchall()
    categories = db.execute("SELECT * FROM categories ORDER BY level1, level2").fetchall()
    db.close()
    return render_template('products/form.html',
                           product=product,
                           suppliers=suppliers,
                           categories=categories,
                           selected_supplier='')


@app.route('/products/<sku>/delete', methods=['POST'])
def product_delete(sku):
    """删除产品"""
    db = get_db()
    # 删除图片文件夹
    sku_dir = UPLOAD_DIR / sku
    if sku_dir.exists():
        shutil.rmtree(str(sku_dir))
    db.execute("DELETE FROM products WHERE erp_sku=?", (sku,))
    db.commit()
    db.close()
    flash("产品已删除", "success")
    return redirect(url_for('product_list'))


@app.route('/products/<sku>/images/<int:img_id>/delete', methods=['POST'])
def image_delete(sku, img_id):
    """删除产品图片"""
    db = get_db()
    img = db.execute("SELECT * FROM product_images WHERE id=? AND erp_sku=?", (img_id, sku)).fetchone()
    if img:
        filepath = UPLOAD_DIR / sku / img['filename']
        if filepath.exists():
            filepath.unlink()
        db.execute("DELETE FROM product_images WHERE id=?", (img_id,))
        db.commit()
    db.close()
    flash("图片已删除", "success")
    return redirect(url_for('product_detail', sku=sku))


@app.route('/products/<sku>/upload-image', methods=['POST'])
def product_upload_image(sku):
    """为产品上传图片"""
    db = get_db()
    product = db.execute("SELECT erp_sku FROM products WHERE erp_sku=?", (sku,)).fetchone()
    if not product:
        db.close()
        flash("产品不存在", "error")
        return redirect(url_for('product_list'))

    files = request.files.getlist('images')
    if not files or not any(f and f.filename for f in files):
        flash("请选择图片", "error")
        db.close()
        return redirect(url_for('product_detail', sku=sku))

    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order),0) FROM product_images WHERE erp_sku=?", (sku,)
    ).fetchone()[0]

    for idx, f in enumerate(files):
        if f and f.filename and allowed_file(f.filename):
            filename = secure_filename(f.filename)
            sku_dir = UPLOAD_DIR / sku
            sku_dir.mkdir(parents=True, exist_ok=True)
            f.save(str(sku_dir / filename))
            db.execute(
                "INSERT INTO product_images (erp_sku, filename, sort_order) VALUES (?,?,?)",
                (sku, filename, max_order + idx + 1)
            )

    db.commit()
    db.close()
    flash("图片上传成功", "success")
    return redirect(url_for('product_detail', sku=sku))


@app.route('/uploads/<path:filepath>')
def uploaded_file(filepath):
    """提供图片访问"""
    return send_from_directory(str(UPLOAD_DIR), filepath)


# ============================================================
# 报价模块
# ============================================================

@app.route('/products/<sku>/add-price', methods=['GET', 'POST'])
def price_add(sku):
    """新增报价记录"""
    db = get_db()
    product = db.execute("SELECT p.*, s.name as supplier_name, c.level1, c.level2 FROM products p JOIN suppliers s ON p.supplier_id=s.id LEFT JOIN categories c ON p.category_id=c.id WHERE p.erp_sku=?", (sku,)).fetchone()
    if not product:
        db.close()
        flash("产品不存在", "error")
        return redirect(url_for('product_list'))

    # 获取最新报价
    latest = db.execute("SELECT price FROM price_history WHERE erp_sku=? ORDER BY price_date DESC LIMIT 1", (sku,)).fetchone()
    latest_price = latest['price'] if latest else None

    if request.method == 'POST':
        price = request.form.get('price', '').strip()
        if not price:
            flash("报价不能为空", "error")
            db.close()
            return redirect(url_for('product_detail', sku=sku))

        price_date = request.form.get('price_date', '').strip() or datetime.date.today().isoformat()
        source = request.form.get('source', '').strip()
        notes = request.form.get('notes', '').strip()

        db.execute(
            "INSERT INTO price_history (erp_sku, price, price_date, source, notes) VALUES (?,?,?,?,?)",
            (sku, float(price), price_date, source, notes)
        )
        db.commit()
        db.close()
        flash("报价已添加", "success")
        return redirect(url_for('product_detail', sku=sku))

    db.close()
    return render_template('products/add_price.html', product=product, latest_price=latest_price, today=datetime.date.today().isoformat())


@app.route('/products/<sku>/delete-price/<int:pid>', methods=['POST'])
def price_delete(sku, pid):
    """删除报价记录"""
    db = get_db()
    db.execute("DELETE FROM price_history WHERE id=?", (pid,))
    db.commit()
    db.close()
    flash("报价记录已删除", "success")
    return redirect(url_for('product_detail', sku=sku))


# ============================================================
# 跟进记录模块
# ============================================================

@app.route('/follow-ups/new', methods=['GET', 'POST'])
def follow_up_add_form():
    """新增跟进记录"""
    db = get_db()
    supplier_id = request.args.get('supplier_id', '')

    if request.method == 'POST':
        sid = request.form.get('supplier_id', '').strip()
        if not sid:
            flash("请选择供应商", "error")
            db.close()
            return redirect(url_for('supplier_list'))
        sid = int(sid)

        follow_date = request.form.get('follow_date', '').strip() or datetime.date.today().isoformat()
        content = request.form.get('content', '').strip()
        follow_type = request.form.get('follow_type', '').strip() or '常规维护'
        erp_sku = request.form.get('erp_sku', '').strip() or None
        is_replied = 1 if request.form.get('is_replied') == '1' else 0
        next_follow_date = request.form.get('next_follow_date', '').strip() or None

        db.execute(
            "INSERT INTO follow_ups (supplier_id, erp_sku, follow_date, content, follow_type, is_replied, next_follow_date) VALUES (?,?,?,?,?,?,?)",
            (sid, erp_sku, follow_date, content, follow_type, is_replied, next_follow_date)
        )
        db.commit()
        db.close()
        flash("跟进记录已添加", "success")
        return redirect(url_for('supplier_detail', sid=sid))

    # GET: render form
    supplier = None
    if supplier_id:
        supplier = db.execute("SELECT id, name FROM suppliers WHERE id=?", (supplier_id,)).fetchone()
    products = db.execute("SELECT erp_sku, name FROM products ORDER BY name").fetchall()
    suppliers_list = db.execute("SELECT id, name FROM suppliers ORDER BY name").fetchall()
    db.close()
    return render_template('follow_ups/form.html',
                           supplier=supplier,
                           products=products,
                           suppliers_list=suppliers_list,
                           today=datetime.date.today().isoformat())


@app.route('/follow-ups/<int:fid>/delete', methods=['POST'])
def follow_up_delete(fid):
    """删除跟进记录"""
    db = get_db()
    fu = db.execute("SELECT supplier_id FROM follow_ups WHERE id=?", (fid,)).fetchone()
    if fu:
        sid = fu['supplier_id']
        db.execute("DELETE FROM follow_ups WHERE id=?", (fid,))
        db.commit()
        flash("跟进记录已删除", "success")
    db.close()
    return redirect(url_for('supplier_detail', sid=sid))


# ============================================================
# 新品动态台
# ============================================================

@app.route('/new-products')
def new_products():
    """新品动态台"""
    month_filter = request.args.get('month', '').strip()
    db = get_db()

    query = '''
        SELECT p.*, s.short_name, s.name as supplier_name,
               c.level1, c.level2
        FROM products p
        JOIN suppliers s ON p.supplier_id = s.id
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.is_new = 1
    '''
    params = []
    if month_filter:
        query += " AND p.new_product_date LIKE ?"
        params.append(f'{month_filter}%')

    query += " ORDER BY p.new_product_date DESC, s.short_name"
    products = db.execute(query, params).fetchall()

    # 按供应商分组
    grouped = {}
    for p in products:
        pdict = dict(p)
        latest = get_latest_price(p['erp_sku'])
        pdict['latest_price'] = latest['price'] if latest else None
        pdict['latest_price_date'] = latest['price_date'] if latest else None
        # 检查是否有跟进记录
        fu = db.execute(
            "SELECT COUNT(*) as cnt FROM follow_ups WHERE erp_sku=? ORDER BY follow_date DESC LIMIT 1",
            (p['erp_sku'],)
        ).fetchone()
        pdict['follow_status'] = '已跟进' if (fu and fu['cnt'] > 0) else '待跟进'
        key = (p['supplier_id'], p['supplier_name'], p['short_name'])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(pdict)

    # 无新品的供应商，检查其跟进状态
    all_suppliers = db.execute("SELECT * FROM suppliers ORDER BY short_name").fetchall()
    no_new_suppliers = []
    for s in all_suppliers:
        has_new = any(k[0] == s['id'] for k in grouped.keys())
        if not has_new:
            last_fu = db.execute(
                "SELECT * FROM follow_ups WHERE supplier_id=? ORDER BY follow_date DESC LIMIT 1",
                (s['id'],)
            ).fetchone()
            no_new_suppliers.append({
                'supplier': s,
                'last_follow_up': last_fu
            })

    # 组装成模板期望的 supplier_blocks 结构
    supplier_blocks = []
    for (sid, sname, sshort), products_list in grouped.items():
        # 获取该供应商的跟进提醒
        upcoming = db.execute(
            "SELECT fu.*, p.name as product_name FROM follow_ups fu LEFT JOIN products p ON fu.erp_sku=p.erp_sku WHERE fu.supplier_id=? AND fu.next_follow_date IS NOT NULL AND fu.next_follow_date >= ? ORDER BY fu.next_follow_date",
            (sid, datetime.date.today().isoformat())
        ).fetchall()
        supplier_blocks.append({
            'supplier': {'id': sid, 'name': sname, 'short_name': sshort},
            'new_products': products_list,
            'upcoming_follow_ups': upcoming,
            'latest_follow': upcoming[0] if upcoming else None
        })

    # 没有新品的供应商
    for item in no_new_suppliers:
        s = item['supplier']
        lfu = item['last_follow_up']
        supplier_blocks.append({
            'supplier': {'id': s['id'], 'name': s['name'], 'short_name': s['short_name']},
            'new_products': [],
            'upcoming_follow_ups': [],
            'latest_follow': lfu
        })

    today = datetime.date.today().isoformat()
    db.close()
    return render_template('new_products.html',
                           supplier_blocks=supplier_blocks,
                           today=today,
                           month_filter=month_filter)


# ============================================================
# 搜索 (JSON API)
# ============================================================

@app.route('/api/search')
def api_search():
    """统一搜索API"""
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify({'products': [], 'suppliers': []})

    db = get_db()
    like = f'%{q}%'
    products = db.execute('''
        SELECT p.erp_sku, p.name, s.short_name
        FROM products p JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.name LIKE ? OR p.erp_sku LIKE ?
        LIMIT 10
    ''', (like, like)).fetchall()

    suppliers = db.execute('''
        SELECT id, name, short_name FROM suppliers
        WHERE name LIKE ? OR short_name LIKE ? OR contact_person LIKE ?
        LIMIT 10
    ''', (like, like, like)).fetchall()
    db.close()

    return jsonify({
        'products': [dict(p) for p in products],
        'suppliers': [dict(s) for s in suppliers]
    })


# ============================================================
# 启动
# ============================================================

if __name__ == '__main__':
    if not DB_PATH.exists():
        init_db()
        print("数据库初始化完成（含1688分类预置）")
    else:
        print("数据库已存在")
    print("启动服务器: http://localhost:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
