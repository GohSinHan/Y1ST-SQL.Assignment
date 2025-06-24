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

    return render_template("dashboard.html")

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

@app.route("/submit-sql", methods=['GET','POST'])
def sql_submit():
    if request.method == 'POST':
        aid = int(request.form['aid'])
        tid = int(request.form['tid'])
        code = request.form['code']
        cnx = mysql.connector.connect(option_files = config_path)
        cursor = cnx.cursor()
        result = cursor.callproc("submit_sql", (session['number'], aid, tid, code, ''))
        cnx.commit()
        cursor.close()
        cnx.close()
        return render_template('submit_result.html', username=result[4], aid=aid, tid=tid, code=code)
    return render_template('submit.html')
