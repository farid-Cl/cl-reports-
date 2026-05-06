import os
import json
import csv
from datetime import datetime, timezone, timedelta
from functools import wraps
from io import StringIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-replace-in-production')

# DB Configuration
if os.environ.get('FLASK_ENV') == 'production':
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///reports.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 10 # 50 MB total to allow multiple files
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ROLES AND PERMISSIONS
ROLES = {
    'admin': ['view_all_reports', 'view_dept_reports', 'view_own_reports', 'submit_report', 'view_analytics', 'manage_users', 'manage_departments', 'export_data', 'delete_reports', 'approve_reports'],
    'manager': ['view_dept_reports', 'view_analytics', 'export_data', 'approve_reports'],
    'employee': ['view_own_reports', 'submit_report'],
    'viewer': ['view_all_reports', 'view_analytics']
}

# --- MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150))
    role = db.Column(db.String(50), default='employee')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def has_permission(self, permission):
        return permission in ROLES.get(self.role, [])

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employee_name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    report_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Submitted')
    images = db.Column(db.Text) # JSON string array
    date_submitted = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', backref=db.backref('reports', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if not current_user.has_permission(permission):
                flash("You don't have permission to access this page.", "danger")
                return redirect(url_for('index')), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- ROUTES ---

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.context_processor
def inject_now():
    return {'now': datetime.now(timezone.utc)}

@app.route('/')
@login_required
def index():
    today = datetime.now(timezone.utc).date()
    if current_user.has_permission('view_all_reports'):
        total_reports = Report.query.count()
        today_reports = Report.query.filter(db.func.date(Report.date_submitted) == today).count()
        unique_employees = db.session.query(db.func.count(db.distinct(Report.employee_name))).scalar() or 0
        total_departments = Department.query.count()
    elif current_user.has_permission('view_dept_reports'):
        total_reports = Report.query.count()
        today_reports = Report.query.filter(db.func.date(Report.date_submitted) == today).count()
        unique_employees = db.session.query(db.func.count(db.distinct(Report.employee_name))).scalar() or 0
        total_departments = Department.query.count()
    else: 
        total_reports = Report.query.filter_by(user_id=current_user.id).count()
        today_reports = Report.query.filter(Report.user_id == current_user.id, db.func.date(Report.date_submitted) == today).count()
        unique_employees = 1
        total_departments = 0

    return render_template('index.html', total_reports=total_reports, today_reports=today_reports, 
                           unique_employees=unique_employees, total_departments=total_departments)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')

        if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
            flash('Email or username already exists.', 'danger')
            return redirect(url_for('signup'))
        
        is_first_user = User.query.count() == 0
        role = 'admin' if is_first_user else 'employee'

        new_user = User(
            username=username, 
            email=email, 
            password=generate_password_hash(password),
            full_name=full_name,
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/submit', methods=['GET', 'POST'])
@permission_required('submit_report')
def submit():
    departments = Department.query.all()
    if request.method == 'POST':
        employee_name = request.form.get('employee_name')
        department = request.form.get('department')
        report_text = request.form.get('report_text')
        
        uploaded_images = request.files.getlist('images')
        saved_images = []
        
        for file in uploaded_images:
            if file and file.filename != '' and allowed_file(file.filename):
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(0)
                if size > 5 * 1024 * 1024:
                    flash(f'File {file.filename} exceeds 5MB limit.', 'danger')
                    continue
                filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                saved_images.append(filename)

        report = Report(
            user_id=current_user.id,
            employee_name=employee_name,
            department=department,
            report_text=report_text,
            images=json.dumps(saved_images)
        )
        db.session.add(report)
        db.session.commit()
        flash('Report submitted successfully!', 'success')
        return redirect(url_for('view_reports'))
        
    return render_template('submit.html', departments=departments)

@app.route('/view')
@login_required
def view_reports():
    page = request.args.get('page', 1, type=int)
    department = request.args.get('department', '')
    employee_name = request.args.get('employee', '')
    date_filter = request.args.get('date', '')

    query = Report.query
    
    if not current_user.has_permission('view_all_reports'):
        if current_user.has_permission('view_dept_reports'):
             pass
        else:
             query = query.filter_by(user_id=current_user.id)

    if department:
        query = query.filter(Report.department.ilike(f'%{department}%'))
    if employee_name:
        query = query.filter(Report.employee_name.ilike(f'%{employee_name}%'))
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Report.date_submitted) == filter_date)
        except ValueError:
            pass

    pagination = query.order_by(Report.date_submitted.desc()).paginate(page=page, per_page=10, error_out=False)
    departments = Department.query.all()
    
    return render_template('view.html', pagination=pagination, departments=departments, 
                           request_args=request.args, json=json)

@app.route('/report/<int:id>')
@login_required
def single_report(id):
    report = db.session.get(Report, id)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('view_reports'))
        
    if not current_user.has_permission('view_all_reports') and not current_user.has_permission('view_dept_reports'):
        if report.user_id != current_user.id:
            flash('Permission denied.', 'danger')
            return redirect(url_for('view_reports'))
            
    images = json.loads(report.images) if report.images else []
    return render_template('single_report.html', report=report, images=images)

@app.route('/report/<int:id>/delete', methods=['POST'])
@permission_required('delete_reports')
def delete_report(id):
    report = db.session.get(Report, id)
    if report:
        if report.images:
            images = json.loads(report.images)
            for img in images:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img))
                except OSError:
                    pass
        db.session.delete(report)
        db.session.commit()
        flash('Report deleted.', 'success')
    return redirect(url_for('view_reports'))

@app.route('/report/<int:id>/status', methods=['POST'])
@permission_required('approve_reports')
def update_report_status(id):
    report = db.session.get(Report, id)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('view_reports'))
    
    new_status = request.form.get('status')
    if new_status in ['Approved', 'Rejected', 'Submitted']:
        report.status = new_status
        db.session.commit()
        flash(f'Report #{report.id} marked as {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')
        
    return redirect(request.referrer or url_for('view_reports'))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/analytics')
@permission_required('view_analytics')
def analytics():
    dept_counts = db.session.query(Report.department, db.func.count(Report.id)).group_by(Report.department).all()
    dept_labels = [d[0] for d in dept_counts]
    dept_data = [d[1] for d in dept_counts]

    emp_counts = db.session.query(Report.employee_name, db.func.count(Report.id)).group_by(Report.employee_name).order_by(db.func.count(Report.id).desc()).limit(10).all()
    emp_labels = [e[0] for e in emp_counts]
    emp_data = [e[1] for e in emp_counts]

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_reports = Report.query.filter(Report.date_submitted >= seven_days_ago).all()
    
    trend_dict = {}
    for i in range(7, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date().strftime('%Y-%m-%d')
        trend_dict[d] = 0
        
    for r in recent_reports:
        d_str = r.date_submitted.date().strftime('%Y-%m-%d')
        if d_str in trend_dict:
            trend_dict[d_str] += 1
            
    trend_labels = list(trend_dict.keys())
    trend_data = [trend_dict[k] for k in trend_labels]

    employees = db.session.query(db.distinct(Report.employee_name)).order_by(Report.employee_name).all()
    employee_names = [e[0] for e in employees]

    return render_template('analytics.html', 
                           dept_labels=json.dumps(dept_labels), dept_data=json.dumps(dept_data),
                           emp_labels=json.dumps(emp_labels), emp_data=json.dumps(emp_data),
                           trend_labels=json.dumps(trend_labels), trend_data=json.dumps(trend_data),
                           employee_names=employee_names)

@app.route('/export')
@permission_required('export_data')
def export():
    department = request.args.get('department', '')
    query = Report.query
    if department:
        query = query.filter(Report.department.ilike(f'%{department}%'))
    
    reports = query.order_by(Report.date_submitted.desc()).all()
    
    def generate():
        data = StringIO()
        writer = csv.writer(data)
        writer.writerow(['ID', 'Employee', 'Department', 'Report Text', 'Status', 'Images', 'Date Submitted'])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        for r in reports:
            images = ", ".join(json.loads(r.images)) if r.images else ""
            writer.writerow([r.id, r.employee_name, r.department, r.report_text, r.status, images, r.date_submitted.strftime('%Y-%m-%d %H:%M:%S')])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)
            
    response = Response(generate(), mimetype='text/csv')
    response.headers.set('Content-Disposition', f'attachment; filename=reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    return response

@app.route('/audit-log')
@permission_required('manage_users') 
def audit_log():
    page = request.args.get('page', 1, type=int)
    pagination = db.session.query(Report, User).join(User, Report.user_id == User.id).order_by(Report.date_submitted.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('audit_log.html', pagination=pagination)

@app.route('/admin/departments', methods=['GET', 'POST'])
@permission_required('manage_departments')
def admin_departments():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if name:
            if Department.query.filter_by(name=name).first():
                flash('Department already exists.', 'danger')
            else:
                dept = Department(name=name, description=description)
                db.session.add(dept)
                db.session.commit()
                flash('Department created.', 'success')
        return redirect(url_for('admin_departments'))
    departments = Department.query.all()
    return render_template('admin_departments.html', departments=departments)

@app.route('/admin/departments/<int:id>/edit', methods=['POST'])
@permission_required('manage_departments')
def edit_department(id):
    dept = db.session.get(Department, id)
    if dept:
        dept.name = request.form.get('name', dept.name)
        dept.description = request.form.get('description', dept.description)
        db.session.commit()
        flash('Department updated.', 'success')
    return redirect(url_for('admin_departments'))

@app.route('/admin/departments/<int:id>/delete', methods=['POST'])
@permission_required('manage_departments')
def delete_department(id):
    dept = db.session.get(Department, id)
    if dept:
        db.session.delete(dept)
        db.session.commit()
        flash('Department deleted.', 'success')
    return redirect(url_for('admin_departments'))

@app.route('/admin/users', methods=['GET', 'POST'])
@permission_required('manage_users')
def admin_users():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('role')
        user = db.session.get(User, user_id)
        if user and user.id != current_user.id:
            user.role = new_role
            db.session.commit()
            flash(f"User {user.username} role updated to {new_role}.", 'success')
        elif user and user.id == current_user.id:
            flash("Cannot change your own role.", 'danger')
        return redirect(url_for('admin_users'))
    users = User.query.all()
    return render_template('admin_users.html', users=users, roles=ROLES.keys())

@app.route('/admin/users/<int:id>/delete', methods=['POST'])
@permission_required('manage_users')
def delete_user(id):
    if id == current_user.id:
        flash("You cannot delete yourself.", 'danger')
        return redirect(url_for('admin_users'))
    user = db.session.get(User, id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted.", 'success')
    return redirect(url_for('admin_users'))

@app.route('/api/reports')
def api_reports():
    page = request.args.get('page', 1, type=int)
    pagination = Report.query.order_by(Report.date_submitted.desc()).paginate(page=page, per_page=10, error_out=False)
    data = []
    for r in pagination.items:
        data.append({
            'id': r.id,
            'employee_name': r.employee_name,
            'department': r.department,
            'report_text': r.report_text,
            'status': r.status,
            'date_submitted': r.date_submitted.isoformat()
        })
    return jsonify({
        'reports': data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })

@app.route('/api/analytics/employee/<employee_name>')
@permission_required('view_analytics')
def api_employee_analytics(employee_name):
    reports = Report.query.filter_by(employee_name=employee_name).all()
    if not reports:
        return jsonify({'error': 'Employee not found or has no reports'}), 404
        
    total = len(reports)
    approved = sum(1 for r in reports if r.status == 'Approved')
    rejected = sum(1 for r in reports if r.status == 'Rejected')
    submitted = sum(1 for r in reports if r.status == 'Submitted')
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_reports = [r for r in reports if r.date_submitted >= seven_days_ago]
    
    trend_dict = {}
    for i in range(7, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date().strftime('%Y-%m-%d')
        trend_dict[d] = 0
        
    for r in recent_reports:
        d_str = r.date_submitted.date().strftime('%Y-%m-%d')
        if d_str in trend_dict:
            trend_dict[d_str] += 1
            
    return jsonify({
        'employee_name': employee_name,
        'total_reports': total,
        'status_breakdown': {
            'Approved': approved,
            'Rejected': rejected,
            'Submitted': submitted
        },
        'trend_labels': list(trend_dict.keys()),
        'trend_data': list(trend_dict.values())
    })

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', 'True') == 'True', port=int(os.environ.get('PORT', 5000)))
