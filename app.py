from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import json

app = Flask(__name__)
CORS(app)

DB_FILE = "student_monitor.db"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """Convert sqlite3.Row to dict"""
    if row is None:
        return None
    return dict(row)

def create_tables():
    """Initialize database schema"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            date       TEXT    UNIQUE NOT NULL,
            study      REAL    DEFAULT 0,
            workout    INTEGER DEFAULT 0,
            water      REAL    DEFAULT 0,
            sleep      REAL    DEFAULT 0,
            score      INTEGER DEFAULT 0,
            streak     INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_schedule (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            day        TEXT    NOT NULL,
            start_time TEXT    NOT NULL,
            end_time   TEXT    NOT NULL,
            subject    TEXT    NOT NULL,
            teacher    TEXT    DEFAULT '',
            room       TEXT    DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_plan (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            subject        TEXT    NOT NULL,
            daily_target_h REAL    NOT NULL,
            priority       INTEGER DEFAULT 2
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subject_completion (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            date       TEXT    NOT NULL,
            subject_id INTEGER NOT NULL,
            done_h     REAL    DEFAULT 0,
            completed  INTEGER DEFAULT 0,
            FOREIGN KEY (subject_id) REFERENCES study_plan(id),
            UNIQUE(date, subject_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT    NOT NULL,
            task_name  TEXT    NOT NULL,
            completed  INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
#  SCORE & STREAK LOGIC
# ─────────────────────────────────────────────

def calculate_streak(date_str):
    """Calculate current streak up to given date"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM daily_logs ORDER BY date DESC")
    rows = [r["date"] for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return 1

    streak = 1
    check = datetime.date.fromisoformat(date_str)
    for logged_date in rows:
        prev = datetime.date.fromisoformat(logged_date)
        if prev == check - datetime.timedelta(days=streak):
            streak += 1
        else:
            break
    return streak

def compute_score(study, workout, water, sleep, completion_pct=0):
    """Compute daily score (max 100)"""
    score = 0
    score += min(study / 8 * 35, 35)
    score += 20 if workout else 0
    score += min(water / 3 * 15, 15)
    score += min(sleep / 8 * 15, 15)
    score += int(completion_pct / 100 * 15)
    return min(int(score), 100)

# ─────────────────────────────────────────────
#  DAILY LOG ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get all recent logs (last 30 days)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_logs ORDER BY date DESC LIMIT 30")
    rows = [dict_from_row(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/logs/<date>', methods=['GET'])
def get_log(date):
    """Get specific log by date"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_logs WHERE date=?", (date,))
    row = cursor.fetchone()
    conn.close()
    return jsonify(dict_from_row(row)) if row else jsonify({"error": "Log not found"}), 404

@app.route('/api/logs', methods=['POST'])
def add_or_update_log():
    """Add or update a daily log"""
    data = request.get_json()
    date = data.get('date', str(datetime.date.today()))
    study = data.get('study', 0)
    workout = data.get('workout', 0)
    water = data.get('water', 0)
    sleep = data.get('sleep', 0)
    completion_pct = data.get('completion_pct', 0)

    streak = calculate_streak(date)
    score = compute_score(study, workout, water, sleep, completion_pct)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO daily_logs (date, study, workout, water, sleep, score, streak)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date, study, workout, water, sleep, score, streak))
        conn.commit()
        action = "added"
    except sqlite3.IntegrityError:
        cursor.execute("""
            UPDATE daily_logs
            SET study=?, workout=?, water=?, sleep=?, score=?, streak=?
            WHERE date=?
        """, (study, workout, water, sleep, score, streak, date))
        conn.commit()
        action = "updated"
    finally:
        conn.close()

    return jsonify({
        "message": f"Log {action}",
        "date": date,
        "score": score,
        "streak": streak
    }), 201

@app.route('/api/logs/<date>', methods=['DELETE'])
def delete_log(date):
    """Delete a log by date"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_logs WHERE date=?", (date,))
    cursor.execute("DELETE FROM subject_completion WHERE date=?", (date,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        return jsonify({"message": f"Log for {date} deleted"})
    else:
        return jsonify({"error": "Log not found"}), 404

# ─────────────────────────────────────────────
#  CLASS SCHEDULE ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """Get full schedule or by day"""
    day = request.args.get('day')
    conn = get_connection()
    cursor = conn.cursor()

    if day:
        cursor.execute("SELECT * FROM class_schedule WHERE day=? ORDER BY start_time", (day,))
    else:
        cursor.execute("""
            SELECT * FROM class_schedule ORDER BY
            CASE day
                WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
                ELSE 7 END, start_time
        """)

    rows = [dict_from_row(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/schedule/today', methods=['GET'])
def get_today_schedule():
    """Get today's schedule"""
    today = DAYS[datetime.date.today().weekday()]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM class_schedule WHERE day=? ORDER BY start_time", (today,))
    rows = [dict_from_row(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"day": today, "classes": rows})

@app.route('/api/schedule', methods=['POST'])
def add_class():
    """Add a class to schedule"""
    data = request.get_json()
    day = data.get('day')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    subject = data.get('subject')
    teacher = data.get('teacher', '')
    room = data.get('room', '')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO class_schedule (day, start_time, end_time, subject, teacher, room)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (day, start_time, end_time, subject, teacher, room))
    conn.commit()
    class_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": f"Class added: {subject}",
        "id": class_id
    }), 201

@app.route('/api/schedule/<int:class_id>', methods=['DELETE'])
def delete_class(class_id):
    """Delete a class"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM class_schedule WHERE id=?", (class_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        return jsonify({"message": f"Class #{class_id} deleted"})
    else:
        return jsonify({"error": "Class not found"}), 404

# ─────────────────────────────────────────────
#  STUDY PLAN ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/study-plan', methods=['GET'])
def get_study_plan():
    """Get study plan"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM study_plan ORDER BY priority, subject")
    rows = [dict_from_row(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/study-plan', methods=['POST'])
def add_subject():
    """Add subject to study plan"""
    data = request.get_json()
    subject = data.get('subject')
    daily_target_h = data.get('daily_target_h')
    priority = data.get('priority', 2)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO study_plan (subject, daily_target_h, priority)
        VALUES (?, ?, ?)
    """, (subject, daily_target_h, priority))
    conn.commit()
    subject_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": f"Subject added: {subject}",
        "id": subject_id
    }), 201

@app.route('/api/study-plan/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    """Delete a subject"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM study_plan WHERE id=?", (subject_id,))
    cursor.execute("DELETE FROM subject_completion WHERE subject_id=?", (subject_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    if affected > 0:
        return jsonify({"message": f"Subject #{subject_id} deleted"})
    else:
        return jsonify({"error": "Subject not found"}), 404

# ─────────────────────────────────────────────
#  SUBJECT COMPLETION ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/completion/<date>', methods=['GET'])
def get_completion_report(date):
    """Get subject completion for a date"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sp.id, sp.subject, sp.daily_target_h, sp.priority,
               sc.done_h, sc.completed
        FROM study_plan sp
        LEFT JOIN subject_completion sc
            ON sc.subject_id = sp.id AND sc.date = ?
        ORDER BY sp.priority, sp.subject
    """, (date,))
    rows = [dict_from_row(r) for r in cursor.fetchall()]

    total = len(rows)
    if total == 0:
        completion_pct = 0
    else:
        completed = sum(1 for r in rows if r['completed'])
        completion_pct = int(completed / total * 100)

    conn.close()
    return jsonify({
        "date": date,
        "subjects": rows,
        "completion_pct": completion_pct
    })

@app.route('/api/completion/<date>', methods=['POST'])
def log_completion(date):
    """Log subject completion for a date"""
    data = request.get_json()
    completions = data.get('completions', [])

    conn = get_connection()
    cursor = conn.cursor()

    for item in completions:
        subject_id = item.get('subject_id')
        done_h = item.get('done_h', 0)

        cursor.execute("SELECT daily_target_h FROM study_plan WHERE id=?", (subject_id,))
        target_row = cursor.fetchone()
        if not target_row:
            continue

        target_h = target_row['daily_target_h']
        completed = 1 if done_h >= target_h else 0

        cursor.execute("""
            INSERT INTO subject_completion (date, subject_id, done_h, completed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date, subject_id) DO UPDATE SET done_h=?, completed=?
        """, (date, subject_id, done_h, completed, done_h, completed))

    conn.commit()

    cursor.execute("SELECT * FROM daily_logs WHERE date=?", (date,))
    log_row = cursor.fetchone()
    if log_row:
        cursor.execute("SELECT COUNT(*) AS done FROM subject_completion WHERE date=? AND completed=1", (date,))
        done_count = cursor.fetchone()['done']
        cursor.execute("SELECT COUNT(*) AS total FROM study_plan")
        total_count = cursor.fetchone()['total']
        completion_pct = int(done_count / total_count * 100) if total_count > 0 else 0

        new_score = compute_score(log_row['study'], log_row['workout'], log_row['water'], log_row['sleep'], completion_pct)
        cursor.execute("UPDATE daily_logs SET score=? WHERE date=?", (new_score, date))
        conn.commit()

    conn.close()
    return jsonify({"message": "Completion logged"}), 201

# ─────────────────────────────────────────────
#  ANALYTICS ENDPOINTS
# ─────────────────────────────────────────────

@app.route('/api/progress-report', methods=['GET'])
def get_progress_report():
    """Get overall progress stats"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            COUNT(*) AS total_days,
            AVG(study) AS avg_study,
            AVG(water) AS avg_water,
            AVG(sleep) AS avg_sleep,
            SUM(workout) AS total_workouts,
            AVG(score) AS avg_score,
            MAX(streak) AS best_streak,
            MAX(score) AS best_score
        FROM daily_logs
    """)
    stats = dict_from_row(cursor.fetchone())
    conn.close()

    if stats['total_days'] is None or stats['total_days'] == 0:
        return jsonify({"message": "No data yet"})

    return jsonify({
        "total_days": int(stats['total_days']) if stats['total_days'] else 0,
        "avg_study": round(stats['avg_study'], 1) if stats['avg_study'] else 0,
        "avg_water": round(stats['avg_water'], 1) if stats['avg_water'] else 0,
        "avg_sleep": round(stats['avg_sleep'], 1) if stats['avg_sleep'] else 0,
        "total_workouts": int(stats['total_workouts']) if stats['total_workouts'] else 0,
        "avg_score": round(stats['avg_score'], 1) if stats['avg_score'] else 0,
        "best_streak": int(stats['best_streak']) if stats['best_streak'] else 0,
        "best_score": int(stats['best_score']) if stats['best_score'] else 0
    })

@app.route('/api/weekly-summary', methods=['GET'])
def get_weekly_summary():
    """Get subject-wise weekly summary"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            sp.id,
            sp.subject,
            sp.priority,
            COUNT(sc.id) AS days_logged,
            SUM(sc.completed) AS days_completed,
            SUM(sc.done_h) AS total_done_h
        FROM study_plan sp
        LEFT JOIN subject_completion sc ON sc.subject_id = sp.id
        GROUP BY sp.id
        ORDER BY sp.priority
    """)
    rows = [dict_from_row(r) for r in cursor.fetchall()]
    conn.close()

    result = []
    for r in rows:
        days_done = r['days_completed'] or 0
        days_log = r['days_logged'] or 0
        total_done = r['total_done_h'] or 0
        pct = int(days_done / days_log * 100) if days_log > 0 else 0

        result.append({
            "subject": r['subject'],
            "priority": r['priority'],
            "days_done": days_done,
            "days_logged": days_log,
            "total_hours": round(total_done, 1),
            "completion_rate": pct
        })

    return jsonify(result)

@app.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    """Get last 7 days score data for chart"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, score FROM daily_logs ORDER BY date DESC LIMIT 7")
    rows = list(reversed([dict_from_row(r) for r in cursor.fetchall()]))
    conn.close()
    return jsonify(rows)

# ─────────────────────────────────────────────
#  INITIALIZATION & RUN
# ─────────────────────────────────────────────

# ─────────────────────────────────────
#  CUSTOM TASKS ENDPOINTS
# ─────────────────────────────────────

@app.route('/api/custom-tasks', methods=['GET'])
def get_custom_tasks():
    """Get user's custom tasks"""
    username = request.args.get('username')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM custom_tasks WHERE username=? ORDER BY created_at DESC
    """, (username,))
    rows = [dict_from_row(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/custom-tasks', methods=['POST'])
def add_custom_task():
    """Add a custom task"""
    data = request.get_json()
    username = data.get('username')
    task_name = data.get('name')
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO custom_tasks (username, task_name, completed)
        VALUES (?, ?, 0)
    """, (username, task_name))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        "message": "Task added",
        "id": task_id
    }), 201

@app.route('/api/custom-tasks/<int:task_id>', methods=['DELETE'])
def delete_custom_task(task_id):
    """Delete a custom task"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_tasks WHERE id=?", (task_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected > 0:
        return jsonify({"message": "Task deleted"})
    else:
        return jsonify({"error": "Task not found"}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "online", "message": "Backend is running!"})

if __name__ == '__main__':
    create_tables()
    print("\n✅ Database initialized")
    print("🚀 Starting UniPilot Backend...")
    print("📡 Server running on http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
