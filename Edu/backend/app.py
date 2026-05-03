import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import streamlit as st
import requests


app = Flask(__name__)  # Fixed
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///edumate.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --------------------------- DATABASE MODEL ---------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    approved = db.Column(db.Boolean, default=False)


with app.app_context():
    db.create_all()
# ------------------- IMPORTS -------------------


# ------------------- Groq API Config -------------------
GROQ_API_KEY = "enter your api key"
 # Streamlit secrets will pass this if using env variable
GROQ_BASE = "https://api.groq.com/openai/v1"
CHAT_ENDPOINT = f"{GROQ_BASE}/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"

def get_groq_chat_response(messages, temperature=0.2, max_tokens=512):
    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens)
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(CHAT_ENDPOINT, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0]["message"]["content"].strip()
        return "[Empty response from Groq API]"
    except Exception as e:
        return f"[Error calling Groq API] {e}"

# ------------------- CHATBOT ROUTE -------------------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "No question provided"}), 400

    system_prompt = {
        "role": "system",
        "content": "You are an expert, patient tutor. Teach clearly with examples and step-by-step explanations."
    }
    messages_to_send = [
        system_prompt,
        {"role": "user", "content": question}
    ]

    answer = get_groq_chat_response(messages_to_send)
    return jsonify({"answer": answer}), 200

# --------------------------- INITIAL USERS ---------------------------
def seed_users():
    if not User.query.first():
        users = [
            User(username="admin", password="admin123", role="Admin", approved=True),
            User(username="teacher", password="teach123", role="Teacher", approved=True),
            User(username="student", password="stud123", role="Student", approved=True),
        ]
        db.session.add_all(users)
        db.session.commit()

with app.app_context():
    seed_users()

# --------------------------- IN-MEMORY STORAGE ---------------------------
QUIZZES = []
LESSONS = []
NOTES = []
DOUBTS = []
DOUBT_COUNTER = 1

# --------------------------- AUTH ROUTES ---------------------------
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or empty request"}), 400

        username = data.get("username")
        password = data.get("password")
        role = data.get("role")
        full_name = data.get("full_name")
        email = data.get("email")
        phone = data.get("phone")

        if not all([username, password, role, full_name, email, phone]):
            return jsonify({"error": "All fields required"}), 400

        existing = User.query.filter_by(username=username).first()
        if existing:
            return jsonify({"error": "User already exists"}), 409

        new_user = User(
            username=username,
            password=password,
            full_name=full_name,
            email=email,
            phone=phone,
            role=role,
            approved=False
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "Registered successfully, waiting approval"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get("username"), password=data.get("password")).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    if not user.approved:
        return jsonify({"error": "Account pending approval"}), 403
    return jsonify({"message": "Login successful", "role": user.role, "username": user.username}), 200

# --------------------------- ADMIN ROUTES ---------------------------
@app.route("/admin/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([{
        "username": u.username,
        "role": u.role,
        "approved": u.approved
    } for u in users])


@app.route("/admin/pending_users", methods=["GET"])
def get_pending_users():
    users = User.query.filter_by(approved=False).all()
    return jsonify([u.username for u in users])


@app.route("/admin/approve_user/<username>", methods=["POST"])
def approve_user(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.approved = True
    db.session.commit()
    return jsonify({"message": "User approved"}), 200


@app.route("/admin/delete_user/<username>", methods=["DELETE"])
def delete_user(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"}), 200


@app.route("/admin/lessons", methods=["GET"])
def admin_lessons():
    return jsonify(LESSONS)


@app.route("/admin/notes", methods=["GET"])
def admin_notes():
    return jsonify(NOTES)


@app.route("/admin/delete_lesson/<int:lesson_id>", methods=["DELETE"])
def delete_lesson(lesson_id):
    global LESSONS
    LESSONS = [l for l in LESSONS if l["id"] != lesson_id]
    return jsonify({"message": "Lesson deleted"}), 200


@app.route("/admin/delete_note/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    global NOTES
    NOTES = [n for n in NOTES if n["id"] != note_id]
    return jsonify({"message": "Note deleted"}), 200

# --------------------------- TEACHER ROUTES ---------------------------
@app.route("/teacher/upload", methods=["POST"])
def upload_lesson():
    file = request.files["file"]
    title = request.form["title"]
    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    LESSONS.append({"id": len(LESSONS) + 1, "title": title, "path": path, "filename": filename})
    return jsonify({"message": "Lesson uploaded successfully"}), 201


@app.route("/teacher/upload_notes", methods=["POST"])
def upload_notes():
    file = request.files["file"]
    title = request.form["title"]
    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    NOTES.append({"id": len(NOTES) + 1, "title": title, "path": path, "filename": filename})
    return jsonify({"message": "Notes uploaded successfully"}), 201


@app.route("/teacher/quiz", methods=["POST"])
def add_quiz():
    data = request.json
    quiz = {
        "id": len(QUIZZES) + 1,
        "title": data.get("title"),
        "questions": data.get("questions")
    }
    QUIZZES.append(quiz)
    return jsonify({"message": "Quiz added successfully"}), 201

# --------------------------- DOUBT CLARIFICATION ---------------------------
@app.route("/student/ask_doubt", methods=["POST"])
def student_ask_doubt():
    global DOUBT_COUNTER
    data = request.json
    student = data.get("student")
    question = data.get("question")

    if not student or not question:
        return jsonify({"error": "Student name and question are required"}), 400

    doubt = {
        "id": DOUBT_COUNTER,
        "student": student,
        "question": question,
        "reply": None,
        "zoom_link": None,
        "status": "Pending"
    }
    DOUBT_COUNTER += 1
    DOUBTS.append(doubt)
    return jsonify({"message": "Doubt submitted successfully"}), 201


@app.route("/teacher/doubts", methods=["GET"])
def teacher_get_doubts():
    return jsonify(DOUBTS), 200


@app.route("/teacher/reply_doubt/<int:doubt_id>", methods=["POST"])
def teacher_reply_doubt(doubt_id):
    data = request.json
    reply = data.get("reply")
    zoom_link = data.get("zoom_link")

    for doubt in DOUBTS:
        if doubt["id"] == doubt_id:
            if reply:
                doubt["reply"] = reply
                doubt["status"] = "Answered"
            if zoom_link:
                doubt["zoom_link"] = zoom_link
                doubt["status"] = "Meeting Scheduled"
            return jsonify({"message": "Reply/Zoom link updated successfully"}), 200

    return jsonify({"error": "Doubt not found"}), 404

# --------------------------- QUIZ ROUTES ---------------------------
@app.route("/quiz/list", methods=["GET"])
def quiz_list():
    return jsonify(QUIZZES)


@app.route("/quiz/<int:quiz_id>", methods=["GET"])
def get_quiz(quiz_id):
    for quiz in QUIZZES:
        if quiz["id"] == quiz_id:
            return jsonify(quiz)
    return jsonify({"error": "Quiz not found"}), 404


@app.route("/quiz/answer", methods=["POST"])
def check_answer():
    data = request.json
    question = data.get("question")
    answer = data.get("answer")
    for quiz in QUIZZES:
        for q in quiz["questions"]:
            if q["question"] == question:
                return jsonify({"correct": q["answer"] == answer})
    return jsonify({"error": "Question not found"}), 404

# --------------------------- PUBLIC ROUTES ---------------------------
@app.route("/lessons", methods=["GET"])
def get_lessons():
    return jsonify(LESSONS)


@app.route("/notes", methods=["GET"])
def get_notes():
    return jsonify(NOTES)


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# --------------------------- RUN ---------------------------
if __name__ == "__main__":  # Fixed
    app.run(host="0.0.0.0", port=5000, debug=True)