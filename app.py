"""
AI Career Advisor - Main Flask Application
Backend: Python + Flask
Database: SQLite
Auth: Flask Session + Password Hashing
AI Logic: Career & Skill Matching
"""

import os
import re
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash

# ─────────────────────────────────────────────
# APP CONFIGURATION
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ai-career-advisor-super-secret-key-change-in-prod')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(days=7)

DATABASE = os.path.join(os.path.dirname(__file__), 'database', 'career.db')


# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────
def get_db():
    """Get SQLite connection for current request."""
    if 'db' not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database tables + seed data."""
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Skills table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            proficiency INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Careers table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS careers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            required_skills TEXT,
            avg_salary TEXT,
            growth_rate TEXT
        )
    ''')

    # Seed careers if empty
    cur.execute('SELECT COUNT(*) FROM careers')
    if cur.fetchone()[0] == 0:
        careers_data = [
            ('Data Scientist',
             'Analyze complex data to extract insights and build ML models.',
             'python,machine learning,statistics,sql,pandas',
             '$120,000', 'High'),
            ('Full Stack Developer',
             'Build end-to-end web applications from UI to database.',
             'javascript,react,node.js,sql,html,css',
             '$105,000', 'High'),
            ('AI/ML Engineer',
             'Design and deploy machine learning systems at scale.',
             'python,tensorflow,pytorch,mlops,deep learning',
             '$135,000', 'Very High'),
            ('DevOps Engineer',
             'Automate and manage cloud infrastructure and CI/CD pipelines.',
             'docker,kubernetes,aws,terraform,linux',
             '$115,000', 'High'),
            ('Data Analyst',
             'Interpret data and create reports to drive business decisions.',
             'sql,excel,tableau,python,statistics',
             '$85,000', 'Medium'),
            ('Product Manager',
             'Lead product strategy and coordinate cross-functional teams.',
             'communication,agile,analytics,leadership,roadmapping',
             '$125,000', 'High'),
            ('Frontend Developer',
             'Craft beautiful, responsive user interfaces for web apps.',
             'html,css,javascript,react,vue,typescript',
             '$95,000', 'High'),
            ('Backend Developer',
             'Build APIs, services, and server-side logic at scale.',
             'python,java,node.js,sql,rest api,docker',
             '$110,000', 'High'),
            ('Cloud Architect',
             'Design scalable cloud infrastructure and migration strategies.',
             'aws,azure,gcp,kubernetes,terraform,networking',
             '$140,000', 'Very High'),
            ('Cybersecurity Analyst',
             'Protect systems from cyber threats and respond to incidents.',
             'networking,linux,security,python,siem,encryption',
             '$100,000', 'Very High'),
        ]
        cur.executemany(
            'INSERT INTO careers (title, description, required_skills, avg_salary, growth_rate) '
            'VALUES (?, ?, ?, ?, ?)',
            careers_data
        )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# AUTH DECORATOR
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# AI MATCHING LOGIC
# ─────────────────────────────────────────────
def normalize_skill(skill):
    return re.sub(r'[^a-z0-9 ]', '', skill.lower().strip())


def match_careers(user_skills):
    """
    Match user's skills against career requirements.
    Returns sorted list of dicts with match score (0-100).
    """
    if not user_skills:
        return []

    db = get_db()
    careers = db.execute('SELECT * FROM careers').fetchall()

    user_skill_set = {normalize_skill(s) for s in user_skills if s.strip()}
    if not user_skill_set:
        return []

    results = []
    for career in careers:
        required = [
            normalize_skill(s)
            for s in (career['required_skills'] or '').split(',')
            if s.strip()
        ]
        if not required:
            continue

        score = 0
        for req in required:
            if req in user_skill_set:
                score += 1
            elif any(req in us or us in req for us in user_skill_set):
                score += 0.5

        match_pct = round((score / len(required)) * 100, 1)

        results.append({
            'id': career['id'],
            'title': career['title'],
            'description': career['description'],
            'required_skills': career['required_skills'],
            'avg_salary': career['avg_salary'],
            'growth_rate': career['growth_rate'],
            'match_score': match_pct,
            'missing_skills': [
                r for r in required if r not in user_skill_set
            ]
        })

    results.sort(key=lambda x: x['match_score'], reverse=True)
    return results[:6]


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            errors.append('Please enter a valid email address.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('register.html', username=username, email=email)

        db = get_db()
        existing = db.execute(
            'SELECT id FROM users WHERE email = ? OR username = ?',
            (email, username)
        ).fetchone()

        if existing:
            flash('An account with that email or username already exists.', 'error')
            return render_template('register.html', username=username, email=email)

        pw_hash = generate_password_hash(password, method='pbkdf2:sha256')
        db.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, pw_hash)
        )
        db.commit()

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']

            if remember:
                session.permanent = True

            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user_id = session['user_id']

    user_skills_rows = db.execute(
        'SELECT skill_name FROM skills WHERE user_id = ?', (user_id,)
    ).fetchall()
    user_skills = [row['skill_name'] for row in user_skills_rows]

    # Lowercase set for template comparison
    user_skills_lower = {s.lower().strip() for s in user_skills}

    matches = match_careers(user_skills)

    return render_template(
        'dashboard.html',
        username=session.get('username'),
        user_skills=user_skills,
        user_skills_lower=user_skills_lower,
        matches=matches
    )


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────
@app.route('/api/skills', methods=['POST'])
@login_required
def add_skill():
    data = request.get_json() or {}
    skill = (data.get('skill') or '').strip()
    if not skill:
        return jsonify({'error': 'Skill name required'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO skills (user_id, skill_name) VALUES (?, ?)',
        (session['user_id'], skill)
    )
    db.commit()
    return jsonify({'success': True, 'skill': skill})


@app.route('/api/skills', methods=['GET'])
@login_required
def get_skills():
    db = get_db()
    rows = db.execute(
        'SELECT skill_name FROM skills WHERE user_id = ?', (session['user_id'],)
    ).fetchall()
    return jsonify({'skills': [r['skill_name'] for r in rows]})


@app.route('/api/skills/<int:skill_id>', methods=['DELETE'])
@login_required
def delete_skill(skill_id):
    db = get_db()
    db.execute(
        'DELETE FROM skills WHERE id = ? AND user_id = ?',
        (skill_id, session['user_id'])
    )
    db.commit()
    return jsonify({'success': True})


@app.route('/api/match', methods=['POST'])
@login_required
def api_match():
    data = request.get_json() or {}
    skills = data.get('skills', [])
    return jsonify({'matches': match_careers(skills)})


@app.errorhandler(404)
def not_found(e):
    flash('Page not found.', 'warning')
    return redirect(url_for('login'))


@app.errorhandler(500)
def server_error(e):
    return render_template('login.html'), 500


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print('✅ Database initialized at', DATABASE)
    print('🚀 Server running at http://localhost:5000')
    app.run(debug=True, host='0.0.0.0', port=5000)