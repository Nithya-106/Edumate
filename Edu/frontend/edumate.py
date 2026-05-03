import os
import requests
import streamlit as st
import speech_recognition as sr
from googletrans import Translator
import subprocess
from gtts import gTTS

BASE_URL = "http://localhost:5000"
FFMPEG_PATH = os.path.join(os.getcwd(), "ffmpeg.exe")

# ------------------- Global Styling -------------------
st.set_page_config(page_title="EduMate", page_icon="🎓", layout="wide")
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(to right, #E3F2FD, #FCE4EC);
            font-family: 'Segoe UI', sans-serif;
            color: #1B2631;
        }
        h1, h2, h3, h4 {
            color: #2C3E50;
            text-align: center;
            font-weight: 600;
        }
        .stButton>button {
            background-color: #5DADE2;
            color: white;
            border-radius: 12px;
            padding: 10px 25px;
            border: none;
            transition: all 0.3s ease;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #3498DB;
            transform: scale(1.05);
        }
        .stTextInput>div>div>input, .stSelectbox>div>div>select {
            border-radius: 8px;
            border: 1px solid #A9CCE3;
            padding: 5px;
        }
        .stDownloadButton>button {
            background-color: #58D68D;
            color: white;
            border-radius: 8px;
            border: none;
        }
        .stDownloadButton>button:hover {
            background-color: #2ECC71;
        }
        hr { border: 1px solid #D6EAF8; }
    </style>
""", unsafe_allow_html=True)


def go_to(page): st.session_state.page = page


def back_to_dashboard(): go_to("dashboard")


# ---------------- Login ----------------
def login_page():
    st.title("👩‍🎓 Welcome to EduMate")
    with st.container():
        st.subheader("🔐 Login to your account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login 🚀"):
            try:
                res = requests.post(f"{BASE_URL}/login", json={"username": username, "password": password})
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.logged_in = True
                    st.session_state.role = data.get("role")
                    st.session_state.username = data.get("username", username)
                    go_to("dashboard")
                elif res.status_code == 403:
                    st.warning("⏳ Your account is awaiting admin approval.")
                else:
                    err = res.json().get("error") if res.headers.get("Cotent-Type", "").startswith(
                        "application/json") else None
                    st.error(f"❌ Invalid credentials. {err or ''}")
            except Exception as e:
                st.error(f"Login error: {e}")
        if st.button("📝 Register Instead"): go_to("register")


# ---------------- Register ----------------
def register_page():
    st.title("📝 Register New User")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    role = st.selectbox("Role", ["Student", "Teacher"])

    if st.button("Register ✅"):
        try:
            res = requests.post(f"{BASE_URL}/register", json={
                "username": username,
                "password": password,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "role": role
            })
            if res.status_code == 201:
                st.success("✅ Registration submitted. Awaiting admin approval.")
                go_to("login")
            else:
                st.error(res.json().get("error", "Registration failed"))
        except Exception as e:
            st.error(f"Error: {e}")
    if st.button("Back 🔙"): go_to("login")


# ---------------- Dashboard ----------------
def dashboard_page():
    st.header("🎓 Welcome to Your Dashboard")
    role = st.session_state.role
    col1, col2, col3 = st.columns(3)

    with col1:
        if role == "Admin":
            if st.button("👑 Admin Dashboard"): go_to("admin_dashboard")
        elif role == "Teacher":
            if st.button("📄 Upload Lesson"): go_to("upload_lesson")
        elif role == "Student":
            if st.button("📝 Take Quiz"): go_to("student_quiz_dashboard")

    with col2:
        if role == "Teacher":
            if st.button("📚 Upload Notes"): go_to("upload_notes")
        elif role == "Student":
            if st.button("📺 View Lessons"): go_to("lessons")

    with col3:
        if role == "Teacher":
            if st.button("🧠 Create Quiz"): go_to("create_quiz_multi")
        elif role == "Student":
            if st.button("📚 View Notes"): go_to("notes")

    # Doubt navigation (all roles see where applicable)
    st.markdown("---")
    if role == "Student":
        if st.button("💬 Ask Doubts"): go_to("student_doubts")
    if role == "Student":
        if st.button("🤖 Chatbot Assistant"): go_to("student_chatbot")

    if role == "Teacher":
        if st.button("📚 Student Doubts"): go_to("teacher_doubts")

    if st.button("🚪 Logout"):
        st.session_state.clear()
        go_to("login")


# ---------------- Teacher: Upload Lesson ----------------
def upload_lesson_page():
    st.header("📄 Upload Lesson (Video from System)")
    title = st.text_input("Lesson Title")
    lesson_number = st.text_input("Lesson Number")
    video_file = st.file_uploader("🎞 Upload a Video File", type=["mp4", "mkv", "mov", "avi"])
    if st.button("Upload 📤"):
        if not title or not video_file or not lesson_number:
            st.warning("⚠ Please provide lesson number, title and video file.")
        else:
            try:
                files = {"file": (video_file.name, video_file.getvalue(), video_file.type)}
                data = {"title": title, "lesson_number": lesson_number}
                res = requests.post(f"{BASE_URL}/teacher/upload", data=data, files=files)
                if res.status_code in (200, 201):
                    st.success("✅ Lesson uploaded successfully!")
                else:
                    st.error(res.json().get("error", "Failed to upload lesson"))
            except Exception as e:
                st.error(f"Error: {e}")
    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- Teacher: Upload Notes ----------------
def upload_notes_page():
    st.header("📚 Upload Notes")
    title = st.text_input("Note Title")
    note_file = st.file_uploader("🗂 Upload Note (PDF, DOCX, PPTX)", type=["pdf", "docx", "pptx"])
    if st.button("Upload 📤"):
        if not title or not note_file:
            st.warning("⚠ Please provide both title and note file.")
        else:
            try:
                files = {"file": (note_file.name, note_file.getvalue(), note_file.type)}
                data = {"title": title}
                res = requests.post(f"{BASE_URL}/teacher/upload_notes", data=data, files=files)
                if res.status_code in (200, 201):
                    st.success("✅ Note uploaded successfully!")
                else:
                    st.error(res.json().get("error", "Failed to upload note"))
            except Exception as e:
                st.error(f"Error: {e}")
    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- Student: Notes ----------------
def notes_page():
    st.header("📘 Notes")
    try:
        res = requests.get(f"{BASE_URL}/notes")
        notes = res.json() if res.status_code == 200 else []
        if not notes:
            st.info("📭 No notes uploaded yet.")
        else:
            os.makedirs("downloads", exist_ok=True)
            for idx, n in enumerate(notes):
                title = n.get("title") or n.get("filename")
                filename = n.get("filename") or os.path.basename(n.get("path", ""))
                st.subheader(f"📖 {title}")
                local_path = os.path.join("downloads", filename)
                if not os.path.exists(local_path):
                    file_data = requests.get(f"{BASE_URL}/uploads/{filename}").content
                    with open(local_path, "wb") as f: f.write(file_data)
                with open(local_path, "rb") as f:
                    st.download_button(
                        label=f"⬇ Download {filename}",
                        data=f,
                        file_name=filename,
                        mime="application/octet-stream",
                        key=f"note_{idx}"
                    )
    except Exception as e:
        st.error(f"Error: {e}")
    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- Student: Lessons ----------------
def lessons_page():
    st.header("📺 Lessons")
    language = st.selectbox("🌐 Select Language:", ["en", "hi", "kn"])
    try:
        res = requests.get(f"{BASE_URL}/lessons")
        lessons = res.json() if res.status_code == 200 else []
        if not lessons:
            st.info("📭 No lessons uploaded yet.")
        else:
            for lesson in lessons:
                # compatibility: backend may send filename or path/filename
                filename = lesson.get("filename") or os.path.basename(lesson.get("path", ""))
                title = lesson.get("title") or filename
                st.subheader(f"🎬 Lesson {lesson.get('id', '')}: {title}")
                video_url = f"{BASE_URL}/uploads/{filename}"
                local_video_path = os.path.join("uploads", filename)
                os.makedirs("uploads", exist_ok=True)
                if not os.path.exists(local_video_path):
                    video_data = requests.get(video_url).content
                    with open(local_video_path, "wb") as f: f.write(video_data)

                # Extract audio
                audio_file = os.path.join("uploads", filename.rsplit('.', 1)[0] + "_orig.wav")
                try:
                    cmd = [FFMPEG_PATH, "-i", local_video_path, "-vn", "-acodec", "pcm_s16le",
                           "-ar", "16000", "-ac", "1", audio_file, "-y"]
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception as e:
                    st.warning("ffmpeg processing failed or ffmpeg.exe not found. Audio transcription skipped.")
                    text = "[Audio processing unavailable]"
                    st.video(local_video_path)
                    st.text_area("📝 Subtitles", text, height=100)
                    continue

                r = sr.Recognizer()
                try:
                    with sr.AudioFile(audio_file) as source:
                        audio_data = r.record(source)
                        text = r.recognize_google(audio_data)
                except Exception:
                    text = "[Could not recognize audio]"

                translator = Translator()
                if language != "en":
                    try:
                        text = translator.translate(text, dest=language).text
                    except Exception:
                        pass

                translated_audio_file = os.path.join("uploads", filename.rsplit('.', 1)[0] + f"_{language}.mp3")
                try:
                    tts = gTTS(text=text, lang=language)
                    tts.save(translated_audio_file)
                except Exception:
                    st.warning("gTTS failed (maybe no internet). Showing original video and subtitles.")
                    st.video(local_video_path)
                    st.text_area("📝 Subtitles", text, height=100)
                    continue

                merged_video_file = os.path.join("uploads", filename.rsplit('.', 1)[0] + f"_{language}.mp4")
                try:
                    cmd_merge = [FFMPEG_PATH, "-i", local_video_path, "-i", translated_audio_file,
                                 "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", "-y", merged_video_file]
                    subprocess.run(cmd_merge, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    st.video(merged_video_file)
                except Exception:
                    st.warning("Merging translated audio with video failed. Playing original video.")
                    st.video(local_video_path)

                st.text_area("📝 Subtitles", text, height=100)
    except Exception as e:
        st.error(f"Error: {e}")
    if st.button("Back 🔙"): back_to_dashboard()


def student_chatbot_page():
    st.header("🤖 EduMate Chatbot")
    st.write("Ask your questions and get instant guidance!")

    user_input = st.text_input("Enter your question here:")

    if st.button("Send Question"):
        if user_input.strip():
            try:
                res = requests.post(f"{BASE_URL}/chatbot", json={"question": user_input})
                if res.status_code == 200:
                    answer = res.json().get("answer", "🤔 No answer available.")
                    st.success(f"💡 {answer}")
                else:
                    st.error("❌ Chatbot failed to respond.")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("⚠ Please enter a question.")

    if st.button("Back 🔙"):
        go_to("dashboard")


# ---------------- Teacher: Create Quiz ----------------
def create_quiz_multi_page():
    st.header("🧠 Create Quiz")
    title = st.text_input("Quiz Title")
    num_qs = st.number_input("Number of Questions", min_value=1, max_value=20, step=1)
    questions = []
    for i in range(int(num_qs)):
        st.markdown(f"---\n*Question {i + 1}:*")
        q = st.text_input(f"🗣 Question {i + 1}", key=f"q_{i}")
        opts = [st.text_input(f"Option {j + 1} Q{i + 1}", key=f"q_{i}opt{j}") for j in range(4)]
        ans = st.text_input(f"✅ Correct answer for Q{i + 1}", key=f"q_{i}_ans")
        questions.append({"question": q, "options": opts, "answer": ans})
    if st.button("Save Quiz 💾"):
        if title and all(q["question"] and all(q["options"]) and q["answer"] for q in questions):
            res = requests.post(f"{BASE_URL}/teacher/quiz", json={"title": title, "questions": questions})
            if res.status_code in (200, 201):
                st.success("✅ Quiz saved successfully!")
            else:
                st.error("❌ Failed to save quiz.")
        else:
            st.warning("⚠ Please fill all fields.")
    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- Student: Quiz Dashboard ----------------
def student_quiz_dashboard():
    st.header("📝 Take a Quiz")
    try:
        quizzes_res = requests.get(f"{BASE_URL}/quiz/list")
        quizzes = quizzes_res.json() if quizzes_res.status_code == 200 else []
    except Exception:
        quizzes = []
    if not quizzes:
        st.warning("📭 No quizzes yet.")
        if st.button("Back 🔙"): back_to_dashboard()
        return
    quiz_titles = [f"{q['title']} ({len(q.get('questions', []))} questions)" for q in quizzes]
    selected = st.selectbox("Select Quiz:", quiz_titles)
    selected_id = quizzes[quiz_titles.index(selected)]["id"]
    if st.button("Start Quiz ▶"):
        st.session_state.selected_quiz_id = selected_id
        st.session_state.quiz_progress = 0
        st.session_state.quiz_score = 0
        go_to("take_selected_quiz")
    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- Student: Take Selected Quiz ----------------
def take_selected_quiz_page():
    quiz_id = st.session_state.selected_quiz_id
    quiz = requests.get(f"{BASE_URL}/quiz/{quiz_id}").json()
    if "error" in quiz:
        st.error(quiz["error"])
        if st.button("Back 🔙"): back_to_dashboard()
        return
    i = st.session_state.quiz_progress
    total = len(quiz["questions"])
    if i < total:
        q = quiz["questions"][i]
        st.markdown(f"*Q{i + 1}: {q['question']}*")
        ans = st.radio("Choose:", q["options"], key=f"take_{i}")
        if st.button("Submit 📨"):
            # Local check to match backend behavior (avoids mismatched API signature)
            correct = q["answer"].strip().lower()
            user_ans = ans.strip().lower()
            if user_ans == correct:
                st.success("✅ Correct!")
                st.session_state.quiz_score += 1
            else:
                st.error("❌ Wrong!")
            st.session_state.quiz_progress += 1
    else:
        st.success(f"🎉 Quiz complete! Score: {st.session_state.quiz_score}/{total}")
        if st.button("Back to Dashboard 🔙"): back_to_dashboard()


# ---------------- Admin: Dashboard ----------------
def admin_dashboard_page():
    st.header("👑 Admin Dashboard")
    if st.button("👥 View Users"): go_to("admin_users")
    if st.button("🕒 Pending Users"): go_to("admin_pending_users")
    if st.button("📄 View Lessons"): go_to("admin_lessons")
    if st.button("📚 View Notes"): go_to("admin_notes")
    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- Admin: Pending Users ----------------
def admin_pending_users_page():
    st.header("🕒 Pending Users (Approval Required)")
    try:
        res = requests.get(f"{BASE_URL}/admin/pending_users")
        users = res.json() if res.status_code == 200 else []
        if not users:
            st.info("No pending users.")
        else:
            # Support both formats: list of usernames (strings) OR list of objects
            for u in users:
                if isinstance(u, dict):
                    username = u.get("username") or u.get("name") or str(u)
                    display = f"{u.get('username', '')} - {u.get('role', '')}"
                else:
                    username = u
                    display = username
                st.markdown(f"{display}")
                if st.button(f"✅ Approve {username}", key=f"approve_{username}"):
                    res = requests.post(f"{BASE_URL}/admin/approve_user/{username}")
                    if res.status_code == 200:
                        st.success(f"Approved {username}")
                        st.rerun()
                    else:
                        st.error(res.json().get("error", "Failed to approve"))
    except Exception as e:
        st.error(f"Error: {e}")
    if st.button("Back 🔙"): go_to("admin_dashboard")


# ---------------- Admin: Users ----------------
def admin_users_page():
    st.header("👥 All Users")
    try:
        res = requests.get(f"{BASE_URL}/admin/users")
        users = res.json() if res.status_code == 200 else []
        for u in users:
            st.markdown(f"{u.get('username')} - {u.get('role')} - Approved: {u.get('approved')}")
    except Exception as e:
        st.error(f"Error: {e}")
    if st.button("Back 🔙"): go_to("admin_dashboard")


# ---------------- Admin: Lessons ----------------
def admin_lessons_page():
    st.header("📄 Lessons")
    try:
        res = requests.get(f"{BASE_URL}/admin/lessons")
        lessons = res.json() if res.status_code == 200 else []
        if not lessons: st.info("No lessons uploaded.")
        for l in lessons:
            title = l.get("title") or l.get("filename")
            lid = l.get("id")
            filename = l.get("filename") or os.path.basename(l.get("path", ""))
            st.markdown(f"{l.get('lesson_number', '')}: {title} - {filename}")
            if st.button(f"🗑 Delete {title}", key=f"del_lesson_{lid}"):
                requests.delete(f"{BASE_URL}/admin/delete_lesson/{lid}")
                st.success("Deleted successfully")
                st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
    if st.button("Back 🔙"): go_to("admin_dashboard")


# ---------------- Admin: Notes ----------------
def admin_notes_page():
    st.header("📚 Notes")
    try:
        res = requests.get(f"{BASE_URL}/admin/notes")
        notes = res.json() if res.status_code == 200 else []
        if not notes: st.info("No notes uploaded.")
        for n in notes:
            title = n.get("title") or n.get("filename")
            nid = n.get("id")
            st.markdown(f"{title} - {n.get('filename') or os.path.basename(n.get('path', ''))}")
            if st.button(f"🗑 Delete {title}", key=f"del_note_{nid}"):
                requests.delete(f"{BASE_URL}/admin/delete_note/{nid}")
                st.success("Deleted successfully")
                st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")
    if st.button("Back 🔙"): go_to("admin_dashboard")


# ---------------- DOUBT: Student Page ----------------
def student_doubts_page():
    st.title("💬 Doubt Clarification")
    st.write(
        "Ask your academic doubts to your teacher. They can reply here or conduct a Zoom meeting for live clarification.")
    question = st.text_area("Enter your doubt/question:")
    if st.button("Submit Doubt"):
        if question.strip():
            payload = {
                "student": st.session_state.get("username", "anonymous"),
                "question": question
            }
            response = requests.post(f"{BASE_URL}/student/ask_doubt", json=payload)
            if response.status_code in (200, 201):
                st.success("✅ Doubt submitted successfully!")
                st.rerun()
            else:
                try:
                    st.error(response.json().get("error", "Failed to submit doubt."))
                except Exception:
                    st.error("Failed to submit doubt.")
        else:
            st.warning("Please enter your question before submitting.")

    st.subheader("📜 Your Previous Doubts")
    try:
        response = requests.get(f"{BASE_URL}/teacher/doubts")
        if response.status_code == 200:
            doubts = response.json()
            student_doubts = [d for d in doubts if d.get("student") == st.session_state.get("username")]
            if student_doubts:
                for d in student_doubts:
                    with st.expander(f"🟢 {d.get('question')}"):
                        st.write(f"*Status:* {d.get('status')}")
                        if d.get('reply'):
                            st.info(f"*Teacher's Reply:* {d.get('reply')}")
                        if d.get('zoom_link'):
                            st.markdown(f"🔗 *Zoom Meeting:* [Join Here]({d.get('zoom_link')})")
            else:
                st.info("No doubts asked yet.")
        else:
            st.error("Could not fetch doubts.")
    except Exception as e:
        st.error(f"Error: {e}")

    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- DOUBT: Teacher Page ----------------
def teacher_doubts_page():
    st.title("📚 Student Doubts")
    try:
        response = requests.get(f"{BASE_URL}/teacher/doubts")
        if response.status_code == 200:
            doubts = response.json()
            if doubts:
                for d in doubts:
                    with st.expander(f"❓ {d.get('student')} asked: {d.get('question')}"):
                        st.write(f"*Status:* {d.get('status')}")
                        if d.get('reply'):
                            st.info(f"*Your Reply:* {d.get('reply')}")
                        if d.get('zoom_link'):
                            st.markdown(f"🔗 *Zoom Meeting:* [Join Link]({d.get('zoom_link')})")

                        st.write("---")
                        reply = st.text_area(f"Enter reply for doubt {d.get('id')}", key=f"reply_{d.get('id')}")
                        zoom = st.text_input(f"Enter Zoom link (optional) for doubt {d.get('id')}",
                                             key=f"zoom_{d.get('id')}")
                        if st.button(f"Submit Reply for {d.get('id')}", key=f"btn_{d.get('id')}"):
                            payload = {"reply": reply, "zoom_link": zoom}
                            res = requests.post(f"{BASE_URL}/teacher/reply_doubt/{d.get('id')}", json=payload)
                            if res.status_code == 200:
                                st.success("✅ Reply/Zoom link sent successfully!")
                                st.rerun()
                            else:
                                try:
                                    st.error(res.json().get("error", "Failed to send reply."))
                                except Exception:
                                    st.error("Failed to send reply.")
            else:
                st.info("No student doubts yet.")
        else:
            st.error("Could not fetch doubts.")
    except Exception as e:
        st.error(f"Error: {e}")

    if st.button("Back 🔙"): back_to_dashboard()


# ---------------- State Initialization ----------------
if "page" not in st.session_state: st.session_state.page = "login"
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "role" not in st.session_state: st.session_state.role = None
if "username" not in st.session_state: st.session_state.username = "anonymous"


# ---------------- Student: Chatbot ----------------
def student_chatbot_page():
    st.header("🤖 EduMate Chatbot")
    st.write("Ask your questions and get instant guidance!")

    user_input = st.text_input("Enter your question here:")

    if st.button("Send Question"):
        if user_input.strip():
            try:
                # Example: using a local /chatbot API endpoint
                res = requests.post(f"{BASE_URL}/chatbot", json={"question": user_input})
                if res.status_code == 200:
                    answer = res.json().get("answer", "🤔 No answer available.")
                    st.success(f"💡 {answer}")
                else:
                    st.error("❌ Chatbot failed to respond.")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("⚠ Please enter a question.")

    if st.button("Back 🔙"):
        go_to("dashboard")


# ---------------- Page Routing ----------------
page = st.session_state.page
if page == "login":
    login_page()
elif page == "register":
    register_page()
elif page == "dashboard":
    dashboard_page()
elif page == "upload_lesson":
    upload_lesson_page()
elif page == "upload_notes":
    upload_notes_page()
elif page == "lessons":
    lessons_page()
elif page == "notes":
    notes_page()
elif page == "student_chatbot":
    student_chatbot_page()
elif page == "create_quiz_multi":
    create_quiz_multi_page()
elif page == "student_quiz_dashboard":
    student_quiz_dashboard()
elif page == "take_selected_quiz":
    take_selected_quiz_page()
elif page == "admin_dashboard":
    admin_dashboard_page()
elif page == "admin_pending_users":
    admin_pending_users_page()
elif page == "admin_users":
    admin_users_page()
elif page == "admin_lessons":
    admin_lessons_page()
elif page == "admin_notes":
    admin_notes_page()
elif page == "student_doubts":
    student_doubts_page()
elif page == "teacher_doubts":
    teacher_doubts_page()