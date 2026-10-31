from flask import Flask, render_template_string, request, redirect, send_from_directory, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os, secrets, html, time, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(64)

site_config = {
    "site_name": "TerraSoft",
    "logo_letter": "T",
    "logo_image": "",
    "color_primary": "#1e88e5",
    "color_secondary": "#ff8f00",
    "bg_color": "#121212",
    "card_color": "#1e1e1e",
}

CEO_EMAIL = "mohmadraaft0@gmail.com"
CEO_PASSWORD_HASH = generate_password_hash("12345ma00")

DATA_DIR = "data_store"
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

def load_data(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

developers = load_data('developers.json')
visitors = load_data('visitors.json')
games = load_data('games.json')
user_sessions = load_data('sessions.json')
login_attempts = {}

UPLOAD_FOLDER = 'static_uploads'
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

def ceo_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_ceo'): abort(403)
        return f(*args, **kwargs)
    return decorated

def dev_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_dev') and not session.get('is_ceo'): abort(403)
        return f(*args, **kwargs)
    return decorated

def generate_csrf_token():
    if '_csrf_token' not in session: session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def verify_csrf_token(token): return token == session.get('_csrf_token')

def log_login(name, email, role):
    user_sessions.append({'name': name, 'email': email, 'role': role, 'login_time': datetime.now().strftime("%Y-%m-%d %H:%M"), 'logout_time': '-'})
    save_data('sessions.json', user_sessions)

def log_logout():
    if session.get('user_email'):
        for s in reversed(user_sessions):
            if s['email'] == session.get('user_email') and s['logout_time'] == '-':
                s['logout_time'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_data('sessions.json', user_sessions)
                break

BASE_STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background-color: {{ config.bg_color }}; color: #fff; }
    .gp-header { background-color: {{ config.card_color }}; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #333; }
    .gp-header .logo { display: flex; align-items: center; text-decoration: none; color: white; font-weight: 500; font-size: 18px; }
    .gp-header .logo-icon { width: 28px; height: 28px; background: linear-gradient(135deg, {{ config.color_primary }} 50%, {{ config.color_secondary }} 50%); border-radius: 50%; margin-right: 8px; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 14px; }
    .gp-header .logo-img { width: 28px; height: 28px; border-radius: 50%; margin-right: 8px; object-fit: cover; }
    .gp-header .nav-links { display: flex; gap: 15px; }
    .gp-header .nav-links a { color: #fff; text-decoration: none; font-size: 13px; opacity: 0.9; }
    .gp-container { padding: 16px; max-width: 500px; margin: 0 auto; }
    .gp-game-card { background: {{ config.card_color }}; border-radius: 12px; padding: 12px; margin-bottom: 12px; display: flex; align-items: center; border: 1px solid #333; }
    .gp-game-icon { width: 64px; height: 64px; border-radius: 16px; background: linear-gradient(135deg, {{ config.color_primary }}, {{ config.color_secondary }}); display: flex; justify-content: center; align-items: center; font-size: 28px; margin-right: 12px; flex-shrink: 0; object-fit: cover; }
    .gp-btn { display: block; width: 100%; padding: 14px; background-color: {{ config.color_primary }}; color: white; text-decoration: none; border-radius: 8px; font-weight: 500; margin-top: 12px; border: none; cursor: pointer; font-size: 15px; text-align: center; }
    .gp-btn-orange { background-color: {{ config.color_secondary }}; }
    .gp-card { background: {{ config.card_color }}; padding: 16px; border-radius: 12px; margin-top: 12px; border: 1px solid #333; }
    input, select, textarea { width: 100%; padding: 14px; margin: 8px 0; border-radius: 8px; border: 1px solid #444; background: {{ config.bg_color }}; color: white; font-size: 15px; outline: none; }
    .gp-tabs { display: flex; gap: 8px; overflow-x: auto; padding: 4px 0; margin-bottom: 12px; scrollbar-width: none; }
    .gp-tabs::-webkit-scrollbar { display: none; }
    .gp-tabs button { padding: 8px 16px; background: {{ config.card_color }}; color: #fff; border: 1px solid #333; border-radius: 20px; cursor: pointer; font-weight: 500; font-size: 13px; white-space: nowrap; }
    .gp-tabs button.active { background: {{ config.color_primary }}; border-color: {{ config.color_primary }}; }
    .tab-content { display: none; } .tab-content.active { display: block; }
    .gp-hero { text-align: center; padding: 30px 16px; }
    .gp-hero-icon { width: 100px; height: 100px; background: linear-gradient(135deg, {{ config.color_primary }} 50%, {{ config.color_secondary }} 50%); border-radius: 24px; margin: 0 auto 16px auto; display: flex; justify-content: center; align-items: center; font-size: 48px; font-weight: bold; color: white; transform: rotate(45deg); }
    .gp-hero-icon span { transform: rotate(-45deg); }
    .gp-hero-icon-img { width: 100px; height: 100px; border-radius: 24px; margin: 0 auto 16px auto; display: block; object-fit: contain; }
    .gp-stat { background: {{ config.bg_color }}; padding: 16px; border-radius: 10px; text-align: center; margin: 8px 0; border: 1px solid #333; }
    .gp-stat-num { font-size: 28px; font-weight: 500; color: {{ config.color_primary }}; }
    .gp-log-item { background: {{ config.bg_color }}; padding: 12px; border-radius: 10px; margin-top: 8px; border-right: 3px solid {{ config.color_primary }}; }
</style>
"""

def get_header(config):
    logo_html = f'<img src="/{config["logo_image"]}" class="logo-img">' if config['logo_image'] and os.path.exists(config['logo_image']) else f'<div class="logo-icon"><span>{config["logo_letter"]}</span></div>'
    links = '<a href="/">الرئيسية</a><a href="/store">المتجر</a>'
    if session.get('is_ceo'): links += '<a href="/admin">الإدارة</a>'
    if session.get('is_dev'): links += '<a href="/dev">لوحتي</a>'
    if session.get('is_ceo') or session.get('is_dev') or session.get('is_visitor'): links += '<a href="/logout" style="color:#ff5252;">خروج</a>'
    else: links += '<a href="/login">دخول</a><a href="/register">حساب جديد</a>'
    return f'<div class="gp-header"><a href="/" class="logo">{logo_html}{config["site_name"]}</a><div class="nav-links">{links}</div></div>'

HOME_HTML = BASE_STYLE + "{{ header|safe }}" + """
<div class="gp-container"><div class="gp-hero">
    {% if config.logo_image %}<img src="/{{ config.logo_image }}" class="gp-hero-icon-img">{% else %}<div class="gp-hero-icon"><span>{{ config.logo_letter }}</span></div>{% endif %}
    <h1>{{ config.site_name }}</h1><p style="color:#aaa; margin-bottom:20px;">متجر الألعاب والتطبيقات</p>
    <a href="/store" class="gp-btn">تصفح المتجر 🎮</a>
</div></div>
"""

STORE_HTML = BASE_STYLE + "{{ header|safe }}" + """
<div class="gp-container">
    <h3 style="margin-bottom:12px;">الألعاب والتطبيقات</h3>
    {% if games|length == 0 %}
    <div class="gp-card" style="text-align:center; padding:40px 20px;"><h3 style="color:#aaa;">لا توجد ألعاب بعد</h3></div>
    {% else %}
    {% for g in games %}
    <a href="/game/{{ g.id }}" style="text-decoration:none; color:inherit;">
        <div class="gp-game-card">
            {% if g.image %}
            <img src="/{{ g.image }}" class="gp-game-icon">
            {% else %}
            <div class="gp-game-icon">🎮</div>
            {% endif %}
            <div style="flex:1;">
                <div style="font-size:15px; font-weight:500;">{{ g.name }}</div>
                <div style="font-size:12px; color:#aaa;">{{ g.dev_name }}</div>
            </div>
            <button class="gp-btn" style="width:auto; margin:0; padding:6px 15px; font-size:12px;">تثبيت</button>
        </div>
    </a>
    {% endfor %}
    {% endif %}
</div>
"""

GAME_DETAIL_HTML = BASE_STYLE + "{{ header|safe }}" + """
<div class="gp-container">
    <div style="display:flex; gap:16px; margin-bottom:20px; align-items:center;">
        {% if game.image %}
        <img src="/{{ game.image }}" style="width:80px; height:80px; border-radius:20px; object-fit:cover;">
        {% else %}
        <div style="width:80px; height:80px; border-radius:20px; background:linear-gradient(135deg, {{ config.color_primary }}, {{ config.color_secondary }}); display:flex; justify-content:center; align-items:center; font-size:36px;">🎮</div>
        {% endif %}
        <div><h2>{{ game.name }}</h2><p style="font-size:13px; color:#aaa;">{{ game.dev_name }}</p></div>
    </div>
    
    {% if game.file %}
    <a href="/{{ game.file }}" download class="gp-btn gp-btn-orange" style="text-decoration:none; display:block;">تثبيت اللعبة (تحميل APK) ⬇️</a>
    {% else %}
    <button class="gp-btn" onclick="alert('اللعبة لم يتم رفع ملفها بعد')">تثبيت اللعبة</button>
    {% endif %}

    <div class="gp-card" style="margin-top:20px;">
        <form action="/add_review/{{ game.id }}" method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            {% if not session.get('user_name') %}<input type="text" name="user_name" placeholder="اسمك" required>{% endif %}
            <select name="rating" required><option value="5">★★★★★ ممتاز</option><option value="4">★★★★☆ جيد جداً</option><option value="3">★★★☆☆ جيد</option></select>
            <textarea name="comment" placeholder="اكتب تعليقك..." required></textarea>
            <button type="submit" class="gp-btn gp-btn-orange">نشر التعليق</button>
        </form>
    </div>
    <div style="margin-top:16px;">
        {% for r in game.reviews %}
        <div style="border-bottom:1px solid #333; padding:12px 0;">
            <strong>{{ r.name }}</strong> <span style="color:#fbbc04;">{{ '★' * r.rating }}</span>
            <p style="font-size:13px; color:#aaa; margin-top:4px;">{{ r.comment }}</p>
            {% if r.ceo_reply %}<div style="background:#1e1e1e; padding:8px; border-right:3px solid {{ config.color_secondary }}; margin-top:6px; font-size:12px;"><b>👑 رد الرئيس:</b> {{ r.ceo_reply }}</div>{% endif %}
        </div>
        {% else %}<p style="text-align:center; color:#aaa; font-size:13px;">لا توجد تعليقات</p>{% endfor %}
    </div>
</div>
"""
LOGIN_HTML = BASE_STYLE + "{{ header|safe }}" + """
<div class="gp-container" style="margin-top:40px;">
    <div class="gp-card">
        <h2 style="text-align:center; margin-bottom:20px;">تسجيل الدخول</h2>
        <form action="/login" method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <input type="email" name="email" placeholder="البريد الإلكتروني" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit" class="gp-btn">دخول</button>
        </form>
        {% if error %}<div style="color:#ff5252; text-align:center; margin-top:10px;">{{ error }}</div>{% endif %}
        <p style="text-align:center; margin-top:15px; font-size:13px; color:#aaa;">ماعندكش حساب؟ <a href="/register" style="color:{{ config.color_primary }};">حساب جديد</a></p>
    </div>
</div>
"""

REGISTER_HTML = BASE_STYLE + "{{ header|safe }}" + """
<div class="gp-container" style="margin-top:40px;">
    <div class="gp-card">
        <h2 style="text-align:center; margin-bottom:20px;">إنشاء حساب زائر</h2>
        <form action="/register" method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <input type="text" name="name" placeholder="الاسم" required>
            <input type="email" name="email" placeholder="البريد الإلكتروني" required>
            <input type="password" name="password" placeholder="كلمة المرور" required minlength="6">
            <button type="submit" class="gp-btn">إنشاء الحساب</button>
        </form>
        {% if error %}<div style="color:#ff5252; text-align:center; margin-top:10px;">{{ error }}</div>{% endif %}
    </div>
</div>
"""

ADMIN_HTML = BASE_STYLE + "{{ header|safe }}" + """
<div class="gp-container">
    <h2 style="margin: 16px 0;">لوحة الرئيس 👑</h2>
    <div class="gp-tabs">
        <button class="active" onclick="showTab('stats', this)">📊 إحصائيات</button>
        <button onclick="showTab('identity', this)">🎨 الهوية</button>
        <button onclick="showTab('devs', this)">👨‍💻 مبرمجين</button>
        <button onclick="showTab('visitors', this)">👥 زوار</button>
        <button onclick="showTab('games', this)">🎮 الألعاب</button>
        <button onclick="showTab('logs', this)">📋 السجل</button>
    </div>
    
    <div id="stats" class="tab-content active">
        <div class="gp-card">
            <div class="gp-stat"><div class="gp-stat-num">{{ games|length }}</div>لعبة</div>
            <div class="gp-stat"><div class="gp-stat-num">{{ developers|length }}</div>مبرمج</div>
            <div class="gp-stat"><div class="gp-stat-num">{{ visitors|length }}</div>زائر</div>
        </div>
    </div>
    
    <div id="identity" class="tab-content">
        <div class="gp-card">
            <form action="/update_config" method="POST" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <label style="font-size:13px; color:#aaa;">اسم الموقع</label>
                <input type="text" name="site_name" value="{{ config.site_name }}">
                <label style="font-size:13px; color:#aaa;">حرف الشعار</label>
                <input type="text" name="logo_letter" value="{{ config.logo_letter }}" maxlength="1">
                <label style="font-size:13px; color:#aaa;">رفع صورة الشعار</label>
                <input type="file" name="logo_file" accept="image/*">
                <button type="submit" class="gp-btn">حفظ</button>
            </form>
        </div>
    </div>
    
    <div id="devs" class="tab-content">
        <div class="gp-card">
            <h3>إضافة مبرمج</h3>
            <form action="/add_dev" method="POST">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input type="text" name="name" placeholder="الاسم" required>
                <input type="email" name="email" placeholder="الإيميل" required>
                <input type="password" name="password" placeholder="الباسورد" required>
                <button type="submit" class="gp-btn">إضافة</button>
            </form>
        </div>
        <div class="gp-card">
            {% for dev in developers %}
            <div style="display:flex; justify-content:space-between; border-bottom:1px solid #333; padding:10px 0;">
                <div><b>{{ dev.name }}</b><br><small style="color:#aaa;">{{ dev.email }}</small></div>
                <form action="/ban_dev" method="POST"><input type="hidden" name="csrf_token" value="{{ csrf_token }}"><input type="hidden" name="email" value="{{ dev.email }}"><button class="gp-btn" style="width:auto; padding:5px 10px; font-size:12px;">{% if dev.banned %}فك{% else %}حظر{% endif %}</button></form>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <div id="visitors" class="tab-content">
        <div class="gp-card">
            {% for v in visitors %}
            <div style="display:flex; justify-content:space-between; border-bottom:1px solid #333; padding:10px 0;">
                <div><b>{{ v.name }}</b><br><small style="color:#aaa;">{{ v.email }}</small></div>
                <form action="/ban_visitor" method="POST"><input type="hidden" name="csrf_token" value="{{ csrf_token }}"><input type="hidden" name="email" value="{{ v.email }}"><button class="gp-btn" style="width:auto; padding:5px 10px; font-size:12px;">{% if v.banned %}فك{% else %}حظر{% endif %}</button></form>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <div id="games" class="tab-content">
        <div class="gp-card">
            <h3>رفع لعبة جديدة</h3>
            <form action="/upload_game_ceo" method="POST" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
                <input type="text" name="game_name" placeholder="اسم اللعبة" required>
                <label style="font-size:13px; color:#aaa;">صورة اللعبة (اختياري)</label>
                <input type="file" name="game_image" accept="image/*">
                <label style="font-size:13px; color:#aaa;">ملف اللعبة (APK)</label>
                <input type="file" name="game_file" accept=".apk" required>
                <button type="submit" class="gp-btn">رفع</button>
            </form>
        </div>
        <div class="gp-card">
            {% for g in games %}<div style="border-bottom:1px solid #333; padding:10px 0;"><b>{{ g.name }}</b></div>{% endfor %}
        </div>
    </div>
    
    <div id="logs" class="tab-content">
        <div class="gp-card">
            {% for log in user_sessions|reverse %}
            <div class="gp-log-item">
                <b>{{ log.name }}</b> ({{ log.role }})<br>
                <small style="color:#aaa;">📧 {{ log.email }}</small><br>
                <small style="color:#aaa;">🟢 {{ log.login_time }} | 🔴 {{ log.logout_time }}</small>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
<script>
    function showTab(n, btn){
        document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
        document.querySelectorAll('.gp-tabs button').forEach(b=>b.classList.remove('active'));
        document.getElementById(n).classList.add('active');
        btn.classList.add('active');
    }
</script>
"""

DEV_HTML = BASE_STYLE + "{{ header|safe }}" + """
<div class="gp-container">
    <h2>أهلاً {{ dev_name }} 💻</h2>
    <div class="gp-card">
        <h3>رفع لعبة جديدة</h3>
        <form action="/upload_game" method="POST" enctype="multipart/form-data">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <input type="text" name="game_name" placeholder="اسم اللعبة" required>
            <label style="font-size:13px; color:#aaa;">صورة اللعبة (اختياري)</label>
            <input type="file" name="game_image" accept="image/*">
            <label style="font-size:13px; color:#aaa;">ملف اللعبة (APK)</label>
            <input type="file" name="game_file" accept=".apk" required>
            <button type="submit" class="gp-btn">رفع لعبة</button>
        </form>
    </div>
    <div class="gp-card">
        {% set my_games = games|selectattr('dev_name', 'equalto', dev_name)|list %}
        {% for g in my_games %}<div style="border-bottom:1px solid #333; padding:10px 0;">{{ g.name }}</div>{% endfor %}
    </div>
</div>
"""

@app.context_processor
def inject_csrf(): return dict(csrf_token=generate_csrf_token())

@app.route('/')
def home(): return render_template_string(HOME_HTML, config=site_config, header=get_header(site_config))

@app.route('/store')
def store(): return render_template_string(STORE_HTML, config=site_config, header=get_header(site_config), games=games)

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    game = next((g for g in games if g['id'] == game_id), None)
    if not game: abort(404)
    return render_template_string(GAME_DETAIL_HTML, config=site_config, header=get_header(site_config), game=game)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
        email = request.form['email']
        password = request.form['password']
        if email == CEO_EMAIL and check_password_hash(CEO_PASSWORD_HASH, password):
            session.clear(); session['is_ceo'] = True; session['user_email'] = email; session['user_name'] = 'رئيس الشركة'
            log_login('رئيس الشركة', email, 'أدمن'); return redirect('/admin')
        for d in developers:
            if d['email'] == email and check_password_hash(d['password_hash'], password) and not d['banned']:
                session.clear(); session['is_dev'] = True; session['dev_name'] = d['name']; session['user_email'] = email; session['user_name'] = d['name']
                log_login(d['name'], email, 'مبرمج'); return redirect('/dev')
        for v in visitors:
            if v['email'] == email and check_password_hash(v['password_hash'], password) and not v['banned']:
                session.clear(); session['is_visitor'] = True; session['visitor_name'] = v['name']; session['user_email'] = email; session['user_name'] = v['name']
                log_login(v['name'], email, 'زائر'); return redirect('/')
        error = "بيانات غير صحيحة أو الحساب محظور"
    return render_template_string(LOGIN_HTML, config=site_config, header=get_header(site_config), error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
        name = html.escape(request.form['name']); email = html.escape(request.form['email']); password = request.form['password']
        for u in visitors + developers:
            if u['email'] == email: error = "هذا الإيميل مسجل بالفعل"; break
        if not error:
            visitors.append({'name': name, 'email': email, 'password_hash': generate_password_hash(password), 'banned': False})
            save_data('visitors.json', visitors)
            session.clear(); session['is_visitor'] = True; session['visitor_name'] = name; session['user_email'] = email; session['user_name'] = name
            log_login(name, email, 'زائر'); return redirect('/')
    return render_template_string(REGISTER_HTML, config=site_config, header=get_header(site_config), error=error)

@app.route('/admin')
@ceo_required
def admin(): return render_template_string(ADMIN_HTML, config=site_config, header=get_header(site_config), developers=developers, visitors=visitors, games=games, user_sessions=user_sessions)

@app.route('/dev')
@dev_required
def dev(): return render_template_string(DEV_HTML, config=site_config, header=get_header(site_config), dev_name=session.get('dev_name', 'مبرمج'), games=games)

@app.route('/logout')
def logout():
    log_logout(); session.clear(); return redirect('/')

@app.route('/update_config', methods=['POST'])
@ceo_required
def update_config():
    if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
    site_config['site_name'] = request.form.get('site_name', site_config['site_name'])
    site_config['logo_letter'] = request.form.get('logo_letter', site_config['logo_letter'])
    if 'logo_file' in request.files:
        f = request.files['logo_file']
        if f and f.filename:
            fn = "logo_" + f.filename; f.save(os.path.join(UPLOAD_FOLDER, fn)); site_config['logo_image'] = os.path.join(UPLOAD_FOLDER, fn)
    return redirect('/admin')

@app.route('/add_dev', methods=['POST'])
@ceo_required
def add_dev():
    if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
    developers.append({'name': html.escape(request.form['name']), 'email': html.escape(request.form['email']), 'password_hash': generate_password_hash(request.form['password']), 'banned': False})
    save_data('developers.json', developers)
    return redirect('/admin')

@app.route('/ban_dev', methods=['POST'])
@ceo_required
def ban_dev():
    for d in developers:
        if d['email'] == request.form['email']: d['banned'] = not d['banned']
    save_data('developers.json', developers)
    return redirect('/admin')

@app.route('/ban_visitor', methods=['POST'])
@ceo_required
def ban_visitor():
    for v in visitors:
        if v['email'] == request.form['email']: v['banned'] = not v['banned']
    save_data('visitors.json', visitors)
    return redirect('/admin')

@app.route('/upload_game', methods=['POST'])
@dev_required
def upload_game():
    if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
    name = html.escape(request.form['game_name'])
    dev_name = session.get('dev_name', 'مبرمج')
    file_path, image_path = "", ""
    
    if 'game_file' in request.files:
        f = request.files['game_file']
        if f and f.filename:
            fn = f"game_{int(time.time())}_{f.filename}"
            f.save(os.path.join(UPLOAD_FOLDER, fn))
            file_path = os.path.join(UPLOAD_FOLDER, fn)
            
    if 'game_image' in request.files:
        img = request.files['game_image']
        if img and img.filename:
            fn_img = f"img_{int(time.time())}_{img.filename}"
            img.save(os.path.join(UPLOAD_FOLDER, fn_img))
            image_path = os.path.join(UPLOAD_FOLDER, fn_img)
            
    games.append({'id': max([g['id'] for g in games], default=0) + 1, 'name': name, 'dev_name': dev_name, 'file': file_path, 'image': image_path, 'reviews': []})
    save_data('games.json', games)
    return redirect('/dev')

@app.route('/upload_game_ceo', methods=['POST'])
@ceo_required
def upload_game_ceo():
    if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
    name = html.escape(request.form['game_name'])
    file_path, image_path = "", ""
    
    if 'game_file' in request.files:
        f = request.files['game_file']
        if f and f.filename:
            fn = f"game_{int(time.time())}_{f.filename}"
            f.save(os.path.join(UPLOAD_FOLDER, fn))
            file_path = os.path.join(UPLOAD_FOLDER, fn)
            
    if 'game_image' in request.files:
        img = request.files['game_image']
        if img and img.filename:
            fn_img = f"img_{int(time.time())}_{img.filename}"
            img.save(os.path.join(UPLOAD_FOLDER, fn_img))
            image_path = os.path.join(UPLOAD_FOLDER, fn_img)
            
    games.append({'id': max([g['id'] for g in games], default=0) + 1, 'name': name, 'dev_name': 'رئيس الشركة', 'file': file_path, 'image': image_path, 'reviews': []})
    save_data('games.json', games)
    return redirect('/admin')

@app.route('/add_review/<int:game_id>', methods=['POST'])
def add_review(game_id):
    if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
    user_name = html.escape(session.get('user_name', request.form.get('user_name', 'زائر')))
    for g in games:
        if g['id'] == game_id:
            g['reviews'].append({'name': user_name, 'rating': int(request.form['rating']), 'comment': html.escape(request.form['comment']), 'ceo_reply': ''})
            break
    save_data('games.json', games)
    return redirect(f'/game/{game_id}')

@app.route('/reply_review/<int:game_id>/<int:review_index>', methods=['POST'])
@ceo_required
def reply_review(game_id, review_index):
    if not verify_csrf_token(request.form.get('csrf_token', '')): abort(403)
    for g in games:
        if g['id'] == game_id:
            if 0 <= review_index < len(g['reviews']):
                g['reviews'][review_index]['ceo_reply'] = html.escape(request.form['reply'])
            break
    save_data('games.json', games)
    return redirect('/admin')

@app.route('/' + UPLOAD_FOLDER + '/<filename>')
def uploaded_file(filename): return send_from_directory(UPLOAD_FOLDER, filename)

@app.errorhandler(403)
def forbidden(e): return "<h1 style='text-align:center; padding:50px; color:white; background:#121212;'>403 - غير مصرح</h1>", 403

@app.errorhandler(404)
def not_found(e): return "<h1 style='text-align:center; padding:50px; color:white; background:#121212;'>404 - غير موجود</h1>", 404

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
