from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, PatientProfile, ParameterSet, SessionLog
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    with app.app_context():
        db.create_all()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check username and password.')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.')
            return redirect(url_for('register'))
            
        new_user = User(username=username, password_hash=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        
        # Create an empty profile and default parameters
        profile = PatientProfile(user_id=new_user.id)
        db.session.add(profile)
        
        default_exercises = [
            {'name': 'Squats', 'min': 60, 'max': 180, 'target': 90},
            {'name': 'Lunges', 'min': 70, 'max': 180, 'target': 90},
            {'name': 'Push-ups', 'min': 70, 'max': 180, 'target': 90},
            {'name': 'Jumping Jacks', 'min': 30, 'max': 180, 'target': 150},
            {'name': 'Shoulder Press', 'min': 45, 'max': 180, 'target': 180}
        ]
        
        for ex in default_exercises:
            param = ParameterSet(user_id=new_user.id, exercise_name=ex['name'], min_angle=ex['min'], max_angle=ex['max'], target_angle=ex['target'])
            db.session.add(param)
            
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    sessions = SessionLog.query.filter_by(user_id=current_user.id).order_by(SessionLog.date.desc()).all()
    return render_template('dashboard.html', sessions=sessions, user=current_user)

@app.route('/start_session', methods=['POST'])
@login_required
def start_session():
    condition = request.form.get('condition')
    body_part = request.form.get('body_part')
    exercise = request.form.get('exercise')
    
    # Update profile with latest condition
    current_user.profile.condition = condition
    db.session.commit()
    
    return redirect(url_for('tracker', exercise_name=exercise))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.profile.first_name = request.form.get('first_name')
        current_user.profile.last_name = request.form.get('last_name')
        current_user.profile.age = request.form.get('age')
        current_user.profile.condition = request.form.get('condition')
        current_user.profile.protocol = request.form.get('protocol')
        
        # Update parameters
        for param in current_user.parameters:
            ex_name = param.exercise_name
            min_val = request.form.get(f'{ex_name}_min')
            max_val = request.form.get(f'{ex_name}_max')
            target_val = request.form.get(f'{ex_name}_target')
            
            if min_val: param.min_angle = float(min_val)
            if max_val: param.max_angle = float(max_val)
            if target_val: param.target_angle = float(target_val)
            
        db.session.commit()
        flash('Profile updated successfully.')
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=current_user)

@app.route('/tracker/<exercise_name>')
@login_required
def tracker(exercise_name):
    param = ParameterSet.query.filter_by(user_id=current_user.id, exercise_name=exercise_name).first()
    if not param:
        # Create default if not exists
        param = ParameterSet(user_id=current_user.id, exercise_name=exercise_name, min_angle=45, max_angle=180, target_angle=90)
        db.session.add(param)
        db.session.commit()
        
    return render_template('tracker.html', exercise=exercise_name, params=param)

@app.route('/api/log_session', methods=['POST'])
@login_required
def log_session():
    data = request.json
    exercise_name = data.get('exercise_name')
    duration = data.get('duration', 0)
    reps = data.get('validated_reps', 0)
    measured_values = data.get('measured_values', '[]')
    feedback = data.get('feedback_events', '[]')
    
    new_log = SessionLog(
        user_id=current_user.id,
        exercise_name=exercise_name,
        duration_seconds=duration,
        validated_reps=reps,
        measured_values_json=str(measured_values),
        feedback_events=str(feedback)
    )
    db.session.add(new_log)
    db.session.commit()
    return jsonify({"status": "success", "message": "Session logged.", "session_id": new_log.id})

@app.route('/report/<int:session_id>')
@login_required
def report(session_id):
    session_log = SessionLog.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    return render_template('report.html', session=session_log)

if __name__ == '__main__':
    if not os.path.exists('tracker.db'):
        init_db()
    app.run(debug=True, port=5000)
