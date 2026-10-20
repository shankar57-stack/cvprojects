from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

    profile = db.relationship('PatientProfile', backref='user', uselist=False)
    parameters = db.relationship('ParameterSet', backref='user', lazy=True)
    sessions = db.relationship('SessionLog', backref='user', lazy=True)

class PatientProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    condition = db.Column(db.String(200))
    protocol = db.Column(db.String(200))

class ParameterSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    min_angle = db.Column(db.Float, nullable=False, default=0.0)
    max_angle = db.Column(db.Float, nullable=False, default=180.0)
    target_angle = db.Column(db.Float, nullable=False, default=90.0)

class SessionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    duration_seconds = db.Column(db.Integer, nullable=False, default=0)
    validated_reps = db.Column(db.Integer, nullable=False, default=0)
    measured_values_json = db.Column(db.Text) # Storing JSON string of reps
    feedback_events = db.Column(db.Text) # Storing JSON string of feedback

