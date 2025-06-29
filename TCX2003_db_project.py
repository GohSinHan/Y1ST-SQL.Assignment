from flask import Flask, render_template, request, redirect, session, jsonify
import mysql.connector
import hashlib
from uuid import uuid4
from datetime import datetime, timedelta
import os
import sqlparse
from difflib import SequenceMatcher
# import logging # Write logs in PythonAnywhere

app = Flask(__name__)
app.debug = True
app.secret_key = 'TCX2003_Secret_Key'
config_path = os.path.join(os.path.dirname(__file__), 'my.ini')

# logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return redirect('/login')  # Redirects to the 'login' route

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    status_msg = None
    if request.method == "POST":
        # Process login data
        user_name = request.form['txt_username']

        # Hash password
        m = hashlib.md5()
        m.update(request.form['txt_password'].encode('UTF-8'))
        password = m.hexdigest()

        try:
            status_msg = "Attempting DB connection ... "
            cnx = mysql.connector.connect(option_files = config_path)
            status_msg += "Connection successful"

            cursor = cnx.cursor()
            status_msg += "Cursor Created"
            cursor.execute(
                'SELECT Student_ID FROM Student WHERE Email=%s AND Password_Hash=%s',
                (user_name, password)
            )
            result = cursor.fetchone()

            if(result):
                student_id = result[0]

                # Create session
                session_token = str(uuid4())
                session['session_token'] = session_token
                session['student_id'] = student_id

                # Add to session DB
                cursor.execute(
                    "INSERT INTO Session (Session_Token, Student_ID, Login_Time) VALUES (%s, %s, %s)",
                    (session_token, student_id, datetime.now())
                )
                cnx.commit()

                # Close connection
                cursor.close()
                cnx.close()

                # redirect to dashboard
                return redirect("/dashboard")
            else:
                error = "Invalid Credentials. Please try again."
        except Exception as e:
            print("Login error:", e)
            error = "Internal server error."
            status_msg = f"Exception occurred!: {e}"

    # direct to login page upon failed login
    return render_template('login.html', error=error, status_msg=status_msg)

@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect('/login')

    student_name = None

    try:
        cnx = mysql.connector.connect(option_files = config_path)
        cursor = cnx.cursor()
        cursor.execute(
            'SELECT First_Name, Last_Name FROM Student WHERE Student_ID = %s',
            (session['student_id'],)
        )
        result = cursor.fetchone()

        if result:
            student_name = f'{result[0]} {result[1]}'

        cursor.close()
        cnx.close()
    except Exception as e:
        print('Error:', e)

    return render_template("dashboard.html", student_name=student_name)

@app.route('/logout')
def logout():
    error = None
    try:
        session_token = session.get('session_token')
        if session_token:
            cnx = mysql.connector.connect(option_files = config_path)
            cursor = cnx.cursor()
            cursor.execute(
                'UPDATE Session SET Is_Active = %s WHERE Session_Token = %s',
                (False, session_token)
            )
            cnx.commit()
            cursor.close()
            cnx.close()
    except Exception as e:
        error = f"Exception occurred! {e}"

    # Clear Flask session and redirect
    session.clear()
    return redirect('/login')

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    # 1. Check new vs confirm, 2. Check current pwd, 3. Sucess
    if 'student_id' not in session:
        return redirect('/login')

    error = None
    msg = None

    if request.method == "POST":
        # Hash password
        m = hashlib.md5()
        m.update(request.form['txt_current_password'].encode('UTF-8'))
        current_password = m.hexdigest()

        # Get current password
        try:
            cnx = mysql.connector.connect(option_files = config_path)
            cursor = cnx.cursor()
            cursor.execute(
                'SELECT Password_Hash FROM Student WHERE Student_ID=%s',
                (session['student_id'],)
            )
            result = cursor.fetchone()

            if not result or result[0] != current_password:
                error = "[ERR] Current password is incorrect!"
            elif(request.form['txt_new_password'] != request.form['txt_confirm_password']):
                error = "[ERR] Password do not match!"
            else:
                encrypt_2 = hashlib.md5()
                encrypt_2.update(request.form['txt_new_password'].encode('UTF-8'))
                new_password = encrypt_2.hexdigest()

                # Update password
                cursor.execute(
                    'UPDATE Student SET Password_Hash=%s WHERE Student_ID=%s',
                    (new_password, session['student_id'])
                )
                cnx.commit()
                msg = "Password changed successfully!"

            # Close connection
            cursor.close()
            cnx.close()
        except Exception as e:
            print("Login error:", e)
            error = "Internal server error."
    return render_template("change-password.html", error=error, success=msg)

@app.route('/submit-sql', methods=['GET', 'POST'])
def submit():
    if 'student_id' not in session:
        return redirect('/login')

    username = session['student_id']

    if request.method == 'POST':
        aid = request.form['aid']
        tid = request.form['tid']
        student_sql = request.form['code']
        submit_time = datetime.utcnow() + timedelta(hours=8) # Original implementation of datetime.now() indicated 8 hours behind SG time.

        try:
            # Connect to DB
            cnx = mysql.connector.connect(option_files=config_path)
            cursor = cnx.cursor(buffered=True)

            # Get Assessment ID
            cursor.execute("SELECT aid, title FROM Assessment")
            assessments = cursor.fetchall()

            # Get model answer and due date
            cursor.execute("""
            SELECT model_answer FROM Tasks
            WHERE tid = %s AND aid = %s
            """, (tid, aid))
            model_answer = cursor.fetchone()[0]

            cursor.execute("SELECT due_date FROM Assessment WHERE aid = %s", (aid,))
            due_date = cursor.fetchone()[0]

            raw_score = calculate_similarity_preserve_case_names(model_answer, student_sql)

            # Check for lateness
            if submit_time > due_date:
                final_score = round(raw_score * 0.9, 2)  # Apply 10% penalty
            else:
                final_score = round(raw_score, 2)

            # Find current attempt number
            cursor.execute("""
                SELECT COUNT(*) FROM Submission
                WHERE Student_ID = %s AND Aid = %s AND Tid = %s
            """, (username, aid, tid))
            attempt_number = cursor.fetchone()[0] + 1

            # Insert submission
            cursor.execute("""
                INSERT INTO Submission (Student_ID, Aid, Tid, Code, Submitted_At, Attempt_No, Score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (username, aid, tid, student_sql, submit_time, attempt_number, final_score))

            cnx.commit()
            cnx.close()

            return render_template('submit.html', success="Submission received! Score: " + str(final_score), assessments=assessments)

        except Exception as e:
            return render_template('submit.html', error="Submission failed. Error: " + str(e))

    else:
        # GET method: show available assessments/tasks
        cnx = mysql.connector.connect(option_files=config_path)
        cursor = cnx.cursor()

        cursor.execute("SELECT aid, title FROM Assessment")
        assessments = cursor.fetchall()

        cursor.execute("SELECT tid FROM Tasks")
        tasks = cursor.fetchall()

        return render_template('submit.html', assessments=assessments, tasks=tasks)

@app.route('/get-tasks/<int:aid>')
def get_tasks_by_aid(aid):
    try:
        cnx = mysql.connector.connect(option_files=config_path)
        cursor = cnx.cursor()
        cursor.execute("SELECT Tid FROM Tasks WHERE Aid = %s", (aid,))
        tasks = [row[0] for row in cursor.fetchall()]
        cursor.close()
        cnx.close()
        return jsonify(tasks)
    except Exception as e:
        return jsonify([]), 500

@app.route("/view-score")
def view_score():
    if 'student_id' not in session:
        return redirect('/login')

    username = session['student_id']

    try:
        cnx = mysql.connector.connect(option_files=config_path)
        cursor = cnx.cursor(dictionary=True)

        cursor.execute("""
            SELECT Aid, Tid, Code, Score, Submitted_At
            FROM Submission
            WHERE Student_ID = %s
            ORDER BY Submitted_At DESC
        """, (username,))

        rows = cursor.fetchall() or []
        cnx.close()

        return render_template("score.html", submissions=rows)

    except Exception as e:
        return f"Error: {e}"

@app.route('/export-score')
def export_score():
    if 'student_id' not in session:
        return redirect('/login')

    try:
        cnx = mysql.connector.connect(option_files=config_path)
        cursor = cnx.cursor()
        cursor.execute('''
            SELECT A.Title, T.Tid, S.Score, S.Submitted_At
            FROM Submission S
            JOIN Tasks T ON S.Tid = T.Tid AND S.Aid = T.Aid
            JOIN Assessment A ON T.Aid = A.Aid
            WHERE S.Student_ID = %s
        ''', (session['student_id'],))
        rows = cursor.fetchall()
        cursor.close()
        cnx.close()
    except Exception as e:
        return f"Error: {e}"

    from io import StringIO
    import csv
    from flask import make_response

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Assignment Title', 'Task ID', 'Score', 'Submitted At'])
    writer.writerows(rows)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=scores.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/leaderboard')
def leaderboard():
    selected_aid = request.args.get('aid')  # This may be None
    try:
        cnx = mysql.connector.connect(option_files=config_path)
        cursor = cnx.cursor()
        # Fetch all assessments
        cursor.execute("SELECT Aid, Title FROM Assessment")
        assessments = cursor.fetchall()
        leaderboard = []
        if selected_aid and selected_aid.isdigit():
            selected_aid = int(selected_aid)
            cursor = cnx.cursor(dictionary=True)
            query = """
                SELECT s.Student_ID, CONCAT(st.First_Name, ' ', st.Last_Name) AS name,
                       ROUND(AVG(s.Score), 2) AS avg_score
                FROM Submission s
                JOIN (
                    SELECT Student_ID, Aid, Tid, MAX(Score) AS MaxScore
                    FROM Submission
                    WHERE Aid = %s
                    GROUP BY Student_ID, Aid, Tid
                ) best
                ON s.Student_ID = best.Student_ID
                   AND s.Aid = best.Aid
                   AND s.Tid = best.Tid
                   AND s.Score = best.MaxScore
                JOIN Student st ON s.Student_ID = st.Student_ID
                WHERE s.Aid = %s
                GROUP BY s.Student_ID
                ORDER BY avg_score DESC
                LIMIT 5;
            """
            cursor.execute(query, (selected_aid, selected_aid))
            results = cursor.fetchall()
            # Ranking logic with ties
            last_score = None
            rank = 0
            actual_position = 0
            for row in results:
                actual_position += 1
                if row['avg_score'] != last_score:
                    rank = actual_position
                leaderboard.append({
                    'rank': rank,
                    'name': row['name'],
                    'score': row['avg_score']
                })
                last_score = row['avg_score']
        return render_template(
            'leaderboard.html',
            assessments=assessments,
            leaderboard=leaderboard,
            selected_aid=selected_aid
        )
    except Exception as e:
        return f"Error: {e}"

# Helper Fn
def normalize_sql_keywords_only(query):
    parsed = sqlparse.parse(query)[0]
    tokens = []

    for token in parsed.tokens:
        if token.ttype in sqlparse.tokens.Keyword:
            tokens.append(token.value.upper())  # normalize keyword
        else:
            tokens.append(token.value)  # preserve case for table names etc.

    return ''.join(tokens)

def calculate_similarity_preserve_case_names(q1, q2):
    norm_q1 = normalize_sql_keywords_only(q1)
    norm_q2 = normalize_sql_keywords_only(q2)
    return SequenceMatcher(None, norm_q1.strip(), norm_q2.strip()).ratio()