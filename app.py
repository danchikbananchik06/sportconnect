from flask import Flask, render_template, session, redirect, url_for, flash, request, jsonify
import sqlite3
import webbrowser
import threading
import os
from werkzeug.utils import secure_filename
from routes.friends import friends_bp

# ---------- FLASK APP ----------
app = Flask(__name__)
app.secret_key = "super_puper_secret_key"

# ---------- UPLOADS ----------
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------- DATABASE ----------
DB_PATH = "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            profile_pic TEXT,
            description TEXT
        )
    ''')
    try:
        c.execute("ALTER TABLE users ADD COLUMN pronouns TEXT")
    except sqlite3.OperationalError:
        pass

    # Friendships table
    c.execute('''
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (requester_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    ''')

    # User sports table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_sports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sport_name TEXT NOT NULL,
            UNIQUE(user_id, sport_name),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Activity invites table
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invitee_id INTEGER NOT NULL,
            sport_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            UNIQUE(inviter_id, invitee_id, sport_name),
            FOREIGN KEY (inviter_id) REFERENCES users(id),
            FOREIGN KEY (invitee_id) REFERENCES users(id)
        )
    ''')

    # Posts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT,
            image TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Sports uploads table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sport_name TEXT NOT NULL,
            description TEXT NOT NULL,
            image TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Ensure 'image' column exists in posts
    c.execute("PRAGMA table_info(posts)")
    columns = [col[1] for col in c.fetchall()]
    if "image" not in columns:
        c.execute("ALTER TABLE posts ADD COLUMN image TEXT")

    conn.commit()
    conn.close()

# ---------- UTIL ----------
def get_user_id(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None

# ---------- REGISTER BLUEPRINT ----------
app.register_blueprint(friends_bp)

# ----------  ALL THE ROUTES ----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["username"] = username
            session["user_id"] = user[0]
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Username already exists.")
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Handle uploads
    if request.method == "POST":
        sport_name = request.form.get("sport_name")
        description = request.form.get("description")
        file = request.files.get("image")
        filename = None

        if file and allowed_file(file.filename):
            filename = f"sport_{session['user_id']}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        if sport_name and description:
            c.execute(
                "INSERT INTO sports (user_id, sport_name, description, image) VALUES (?, ?, ?, ?)",
                (session["user_id"], sport_name, description, filename)
            )
            conn.commit()
            flash("Sport uploaded successfully!", "success")

    # Fetch all sports
    c.execute("""
        SELECT s.id, s.sport_name, s.description, s.image, s.timestamp, u.username
        FROM sports s
        JOIN users u ON s.user_id = u.id
        ORDER BY s.timestamp DESC
    """)
    sports = c.fetchall()
    conn.close()
    return render_template("dashboard.html", username=session["username"], sports=sports)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/feed", methods=["GET", "POST"])
def feed():
    if "username" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        file = request.files.get("image")
        filename = None

        if file and file.filename != "" and allowed_file(file.filename):
            filename = f"{session['user_id']}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if content or filename:
            c.execute("INSERT INTO posts (user_id, content, image) VALUES (?, ?, ?)",
                      (session['user_id'], content, filename))
            conn.commit()
            flash("Post created!", "success")

    c.execute("""
        SELECT p.id, p.content, p.image, p.timestamp, u.username, u.profile_pic, p.user_id
        FROM posts p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.timestamp DESC
    """)
    posts = c.fetchall()
    conn.close()
    return render_template("feed.html", posts=posts, session_user_id=session['user_id'])


@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id=? AND user_id=?", (post_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Post deleted!", "info")
    return redirect(url_for("feed"))


@app.route("/me", methods=["GET", "POST"])
def me():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if request.method == "POST":
        file = request.files.get("profile_pic")
        if file and file.filename != "":
            filename = f"{user_id}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            c.execute("UPDATE users SET profile_pic=? WHERE id=?", (filename, user_id))

        description = request.form.get("description", "")
        pronouns = request.form.get("pronouns", "")
        c.execute("UPDATE users SET description=?, pronouns=? WHERE id=?", (description, pronouns, user_id))

    c.execute("SELECT username, profile_pic, description, pronouns FROM users WHERE id=?", (user_id,))
    user = c.fetchone()

    # Fetch user sports
    c.execute("SELECT sport_name FROM user_sports WHERE user_id=?", (user_id,))
    sports = [row['sport_name'] for row in c.fetchall()]

    # Fetch friends
    c.execute("""
        SELECT u.id, u.username, u.pronouns
        FROM users u
        JOIN friendships f ON
        (f.requester_id = ? AND f.receiver_id = u.id AND f.status='accepted')
        OR (f.receiver_id = ? AND f.requester_id = u.id AND f.status='accepted')
    """, (user_id, user_id))
    friends = c.fetchall()

    # Incoming invites
    c.execute("""
        SELECT ai.id, u.username AS inviter, u.pronouns AS inviter_pronouns, ai.sport_name
        FROM activity_invites ai
        JOIN users u ON ai.inviter_id = u.id
        WHERE ai.invitee_id=? AND ai.status='pending'
    """, (user_id,))
    incoming_invites = c.fetchall()

    # Sport participants
    sport_participants = {}
    for sport in sports:
        c.execute("""
            SELECT u.username, u.pronouns
            FROM user_sports us
            JOIN users u ON us.user_id = u.id
            WHERE us.sport_name=? AND us.user_id != ?
        """, (sport, user_id))
        participants = [
            f"{row['username']} ({row['pronouns']})" if row['pronouns'] else row['username']
            for row in c.fetchall()
        ]
        sport_participants[sport] = participants

    conn.close()
    return render_template(
        "me.html",
        username=user["username"],
        pronouns=user["pronouns"],
        profile_pic=user["profile_pic"],
        profile_description=user["description"],
        user_sports=sports,
        friends=friends,
        incoming_invites=incoming_invites,
        sport_participants=sport_participants
    )


# ---------- ADD / REMOVE SPORT ----------
@app.route("/add_sport", methods=["POST"])
def add_sport():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    sport = data.get("sport")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO user_sports (user_id, sport_name) VALUES (?, ?)",
                  (session["user_id"], sport))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True})


@app.route("/remove_sport", methods=["POST"])
def remove_sport():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    sport = data.get("sport")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_sports WHERE user_id=? AND sport_name=?", (session["user_id"], sport))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ---------- INVITE FRIEND ----------
@app.route("/invite_friend", methods=["POST"])
def invite_friend():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    friend_id = data.get("friend_id")
    sport = data.get("sport")

    if not friend_id or not sport:
        return jsonify({"error": "Missing data"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO activity_invites (inviter_id, invitee_id, sport_name) VALUES (?, ?, ?)",
            (session["user_id"], friend_id, sport)
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True})


@app.route("/respond_invite", methods=["POST"])
def respond_invite():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    invite_id = data.get("invite_id")
    response = data.get("response")

    if not invite_id or response not in ["accepted", "declined"]:
        return jsonify({"error": "Invalid data"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE activity_invites SET status=? WHERE id=? AND invitee_id=?", (response, invite_id, session["user_id"]))

    if response == "accepted":
        c.execute("""
            INSERT OR IGNORE INTO user_sports (user_id, sport_name)
            SELECT invitee_id, sport_name FROM activity_invites WHERE id=?
        """, (invite_id,))

    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/delete_sport/<int:sport_id>", methods=["POST"])
def delete_sport(sport_id):
    if "user_id" not in session:
        flash("You must be logged in to delete a sport.", "error")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Check if sport belongs to the logged-in user
    c.execute("SELECT image, user_id FROM sports WHERE id=?", (sport_id,))
    sport = c.fetchone()
    if not sport:
        conn.close()
        flash("Sport not found.", "error")
        return redirect(url_for("dashboard"))

    if sport["user_id"] != session["user_id"]:
        conn.close()
        flash("You don’t have permission to delete this sport.", "error")
        return redirect(url_for("dashboard"))

    # Delete image file if it exists
    if sport["image"]:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], sport["image"])
        if os.path.exists(image_path):
            os.remove(image_path)

    # Delete record from database
    c.execute("DELETE FROM sports WHERE id=?", (sport_id,))
    conn.commit()
    conn.close()
    flash("Sport deleted successfully!", "info")
    return redirect(url_for("dashboard"))

@app.route("/user/<username>")
def user_profile(username):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get user info
    c.execute("SELECT id, username, profile_pic, description, pronouns FROM users WHERE username=?", (username,))
    user = c.fetchone()
    if not user:
        conn.close()
        return "User not found", 404

    # Get user sports
    c.execute("SELECT sport_name FROM user_sports WHERE user_id=?", (user["id"],))
    sports = [row["sport_name"] for row in c.fetchall()]

    # Get user's friends
    c.execute("""
        SELECT u.id, u.username, u.profile_pic
        FROM users u
        JOIN friendships f ON
        (f.requester_id = ? AND f.receiver_id = u.id AND f.status='accepted')
        OR (f.receiver_id = ? AND f.requester_id = u.id AND f.status='accepted')
    """, (user["id"], user["id"]))
    friends = c.fetchall()

    conn.close()
    return render_template("user_profile.html", user=user, sports=sports, friends=friends)


# ---------- AUTO OPEN BROWSER ----------
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")


if __name__ == "__main__":
    init_db()
    # Only auto-open browser when running locally
    if os.environ.get("RAILWAY_ENVIRONMENT") is None:
        threading.Timer(1.25, open_browser).start()
        app.run(debug=True)
    else:
        app.run(host="0.0.0.0", debug=False)
