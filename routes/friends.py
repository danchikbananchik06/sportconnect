from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import sqlite3

friends_bp = Blueprint('friends_bp', __name__, url_prefix='/friends')
DB_PATH = "database.db"

# ---------- Helper ----------
def get_user_id(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None

# ---------- Main Friends Page ----------
@friends_bp.route('/', methods=['GET', 'POST'])
def friends_index():
    if 'username' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # --- Add Friend (Send Request) ---
    if request.method == 'POST':
        nickname = request.form.get('nickname', '').strip()
        if nickname:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            # Find receiver
            c.execute("SELECT id FROM users WHERE username=?", (nickname,))
            receiver = c.fetchone()
            if not receiver:
                flash(f"User '{nickname}' does not exist.", "danger")
                conn.close()
                return redirect(url_for('friends_bp.friends_index'))

            receiver_id = receiver[0]
            if receiver_id == user_id:
                flash("You can't add yourself as a friend.", "warning")
                conn.close()
                return redirect(url_for('friends_bp.friends_index'))

            # Check existing friendships
            c.execute("""
                SELECT * FROM friendships 
                WHERE ((requester_id=? AND receiver_id=?) OR (requester_id=? AND receiver_id=?))
                AND status IN ('pending', 'accepted')
            """, (user_id, receiver_id, receiver_id, user_id))
            exists = c.fetchone()

            if exists:
                flash(f"You already have a pending or existing friendship with {nickname}.", "info")
            else:
                # Create new pending request
                c.execute("""
                    INSERT INTO friendships (requester_id, receiver_id, status)
                    VALUES (?, ?, 'pending')
                """, (user_id, receiver_id))
                conn.commit()
                flash(f"Friend request sent to {nickname}!", "success")

            conn.close()
            return redirect(url_for('friends_bp.friends_index'))

    # --- Fetch Accepted Friends ---
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT f.id, u1.username AS requester_name, u1.profile_pic AS requester_pic,
               u2.username AS receiver_name, u2.profile_pic AS receiver_pic, f.status
        FROM friendships f
        JOIN users u1 ON f.requester_id = u1.id
        JOIN users u2 ON f.receiver_id = u2.id
        WHERE (f.requester_id=? OR f.receiver_id=?) AND f.status='accepted'
    """, (user_id, user_id))
    friends = c.fetchall()

    # --- Fetch Incoming Pending Requests ---
    c.execute("""
        SELECT f.id, u1.username as requester_name
        FROM friendships f
        JOIN users u1 ON f.requester_id = u1.id
        WHERE f.receiver_id=? AND f.status='pending'
    """, (user_id,))
    requests = c.fetchall()

    conn.close()
    return render_template('friends.html', friends=friends, requests=requests)

# ---------- Accept Friend ----------
@friends_bp.route('/accept/<int:friendship_id>')
def accept(friendship_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE friendships SET status='accepted' WHERE id=?", (friendship_id,))
    conn.commit()
    conn.close()
    flash("Friend request accepted!", "success")
    return redirect(url_for('friends_bp.friends_index'))

# ---------- Reject Friend ----------
@friends_bp.route('/reject/<int:friendship_id>')
def reject(friendship_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM friendships WHERE id=?", (friendship_id,))
    conn.commit()
    conn.close()
    flash("Friend request rejected.", "info")
    return redirect(url_for('friends_bp.friends_index'))

# ---------- Delete Friend ----------
@friends_bp.route('/delete/<int:friendship_id>')
def delete(friendship_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM friendships WHERE id=?", (friendship_id,))
    conn.commit()
    conn.close()
    flash("Friend removed.", "info")
    return redirect(url_for('friends_bp.friends_index'))

# ---------- Block Friend ----------
@friends_bp.route('/block/<int:friendship_id>')
def block(friendship_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE friendships SET status='blocked' WHERE id=?", (friendship_id,))
    conn.commit()
    conn.close()
    flash("Friend blocked.", "info")
    return redirect(url_for('friends_bp.friends_index'))
