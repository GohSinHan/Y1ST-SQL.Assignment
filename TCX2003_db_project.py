from flask import Flask, render_template, request, redirect, session
import mysql.connector
import hashlib
from uuid import uuid4
from datetime import datetime
import os
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
            cnx = mysql.connector.connect(
                host="ziadesouza.mysql.pythonanywhere-services.com",           # or "yourusername.mysql.pythonanywhere-services.com" on PythonAnywhere
                user="ziadesouza",
                password="thinkpad",
                database="ziadesouza$default"
            )
            status_msg += "Connection successful"

            cursor = cnx.cursor()
            status_msg += "Cursor Created"
            cursor.execute(
                'SELECT username FROM students WHERE username=%s AND password_hash=%s',
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
        submit_time = datetime.now()

        try:
            # Connect to DB
            cnx = mysql.connector.connect(
                host="ziadesouza.mysql.pythonanywhere-services.com",
                user="ziadesouza",
                password="thinkpad",
                database="ziadesouza$default"
            )
            cursor = cnx.cursor()

            # Get model answer and due date
            cursor.execute("SELECT model_answer FROM tasks WHERE tid = %s", (tid,))
            model_answer = cursor.fetchone()[0]

            cursor.execute("SELECT due_date FROM assessments WHERE aid = %s", (aid,))
            due_date = cursor.fetchone()[0]

            # Run model answer and student answer on test DB
            test_cursor = cnx.cursor()
            test_cursor.execute(model_answer)
            expected_result = test_cursor.fetchall()

            test_cursor.execute(student_sql)
            student_result = test_cursor.fetchall()

            # Compare results (simple version)
            if student_result == expected_result:
                raw_score = 100
            else:
                raw_score = 60  # You can use more advanced scoring later

            # Check for lateness
            if submit_time > due_date:
                final_score = round(raw_score * 0.9, 2)  # Apply 10% penalty
            else:
                final_score = raw_score

            # Find current attempt number
            cursor.execute("""
                SELECT COUNT(*) FROM submissions
                WHERE username = %s AND aid = %s AND tid = %s
            """, (username, aid, tid))
            attempt_number = cursor.fetchone()[0] + 1

            # Insert submission
            cursor.execute("""
                INSERT INTO submissions (username, aid, tid, code, submit_at, attempt_number, score)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (username, aid, tid, student_sql, submit_time, attempt_number, final_score))

            cnx.commit()
            cnx.close()

            return render_template('submit.html', success="Submission received! Score: " + str(final_score))

        except Exception as e:
            return render_template('submit.html', error="Submission failed. Error: " + str(e))

    else:
        # GET method: show available assessments/tasks
        cnx = mysql.connector.connect(
                host="ziadesouza.mysql.pythonanywhere-services.com",
                user="ziadesouza",
                password="thinkpad",
                database="ziadesouza$default"
            )
        cursor = cnx.cursor()

        cursor.execute("SELECT aid, title FROM assessments")
        assessments = cursor.fetchall()

        cursor.execute("SELECT tid, title FROM tasks")
        tasks = cursor.fetchall()

        return render_template('submit.html', assessments=assessments, tasks=tasks)


@app.route("/view-score")
def view_score():
    if 'student_id' not in session:
        return redirect('/login')

    username = session['student_id']

    try:
        cnx = mysql.connector.connect(
            host="ziadesouza.mysql.pythonanywhere-services.com",
            user="ziadesouza",
            password="thinkpad",
            database="ziadesouza$default"
        )
        cursor = cnx.cursor(dictionary=True)

        cursor.execute("""
            SELECT s.username, s.aid AS assessment, s.tid AS task,
                   s.attempt_number AS test_case, s.score,
                   a.due_date, s.submit_at AS submit_date,
                   s.code AS submitted_code
            FROM submissions s
            JOIN assessments a ON s.aid = a.aid
            WHERE s.username = %s
            ORDER BY s.submit_at DESC
        """, (username,))

        rows = cursor.fetchall()
        cnx.close()

        return render_template("score.html", submissions=rows)

    except Exception as e:
        return f"Error: {e}"

# @app.route("/submit-sql", methods=['GET','POST'])
# def sql_submit():
#     if request.method == 'POST':
#         aid = int(request.form['aid'])
#         tid = int(request.form['tid'])
#         code = request.form['code']
#         cnx = mysql.connector.connect(
#                 host="ziadesouza.mysql.pythonanywhere-services.com",
#                 user="ziadesouza",
#                 password="thinkpad",
#                 database="ziadesouza$default"
#             )
#         cursor = cnx.cursor()
#         result = cursor.callproc("submit_sql", (session['number'], aid, tid, code, ''))
#         cnx.commit()
#         cursor.close()
#         cnx.close()
#         return render_template('submit_result.html', username=result[4], aid=aid, tid=tid, code=code)
#     return render_template('submit.html')
