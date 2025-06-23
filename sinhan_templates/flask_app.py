from flask import Flask, request, redirect, render_template, session
from uuid import uuid4
import hashlib
import mysql.connector

app = Flask(__name__)
app.debug = True
app.secret_key = '*************'

@app.route("/sql_eval", methods=['GET', 'POST'])
def sql_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        m = hashlib.md5()
        m.update(request.form['password'].encode('UTF-8'))
        password = m.hexdigest()

        cnx = mysql.connector.connect(
            host="SinHan.mysql.pythonanywhere-services.com",
            user="SinHan",
            password="shgoh123",
            database="SinHan$sql_eval"
        )
        cursor = cnx.cursor()
        cursor.execute(
            "SELECT username FROM student WHERE username=%s AND password=%s",
            (username, password)
        )
        result_rows = cursor.fetchall()
        #return result_rows
        if len(result_rows) != 1 or result_rows[0][0] != username:
            error = 'Invalid Credentials. Please try again.'
            cursor.close()
            cnx.close()
        else:
            session['number'] = str(uuid4())
            cursor.execute(
                "INSERT INTO sessions (session_num, started_at, username) VALUES (%s, now(), %s)",
                (session['number'], username)
            )
            cnx.commit()
            cursor.close()
            cnx.close()
            return redirect('/sql_home')

    return render_template('login.html', error=error)

@app.route("/sql_home", methods=['GET','POST'])
def sql_home():
    return render_template('home.html')

@app.route("/sql_submit", methods=['GET','POST'])
def sql_submit():
    if request.method == 'POST':
        aid = int(request.form['aid'])
        tid = int(request.form['tid'])
        code = request.form['code']
        cnx = mysql.connector.connect(
            host="SinHan.mysql.pythonanywhere-services.com",
            user="SinHan",
            password="shgoh123",
            database="SinHan$sql_eval"
        )
        cursor = cnx.cursor()
        result = cursor.callproc("submit_sql", (session['number'], aid, tid, code, ''))
        cnx.commit()
        cursor.close()
        cnx.close()
        return render_template('submit_result.html', username=result[4], aid=aid, tid=tid, code=code)
    return render_template('submit.html')

@app.route("/sql_score", methods=['GET','POST'])
def sql_score():
    return render_template('score.html')

@app.route("/sql_leaderboard", methods=['GET','POST'])
def sql_leaderboard():
    return render_template('leaderboard.html')
