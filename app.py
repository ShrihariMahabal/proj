from flask import Flask, render_template, request, redirect, session, url_for
from flask_session import Session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import secrets

# i am gay shri

app = Flask(__name__)

app.secret_key = 'sk'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'db1'
app.config['MYSQL_PORT'] = 3309
app.config['MYSQL_CURSORCLASS'] = "DictCursor"

mysql = MySQL(app)

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

def split(gid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT uid FROM group_members WHERE gid=%s", (gid,))
    members = cur.fetchall()
    n = len(members)
    matrix = []
    for i in range(n):
        matrix.append([0]*n)
    dic = {}
    for idx, i in enumerate(members):
        dic[i['uid']] = idx
    cur.execute("SELECT * FROM paid_by WHERE gid=%s", (gid,))
    expenses = cur.fetchall()
    for i in expenses:
        eid = i['eid']
        payer = i['payer']
        amount = i['amount']
        cur.execute("SELECT fid FROM paid_for WHERE eid=%s", (eid,))
        fids = cur.fetchall()
        n = len(fids)
        owed = amount / n
        cur.close()
        for j in fids:
            fid = j['fid']
            matrix[dic[payer]][dic[fid]] += owed
    return matrix, expenses, dic, fids

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s and password = %s", (username,password,))
        user = cur.fetchone()
        cur.close()

        if user:
            session['username'] = user['username']
            session['uid'] = user['uid']
            return redirect(url_for('home'))
        else:
            error = 'User does not exist'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            error = 'Please fill all the details'
            return render_template('register.html', error=error)

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user:
            error = 'Username already exists'
            cur.close()
            return render_template('register.html', error=error)

        cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/home')
def home():
    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM groups")
        groups = cur.fetchall()
        cur.close()
        return render_template('home.html', groups=groups, username=session['username'], active_page='home')
    return redirect(url_for('login'))

@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    if request.method == 'POST':
        group_name = request.form['group_name']

        if not group_name:
            error = 'Please enter valid group name !'
            return render_template('create_group.html', error=error)
        invite_code = secrets.token_hex(6)  # Generate random invite code
        uid = session['uid']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO groups (group_name, invite_code) VALUES (%s, %s)", (group_name, invite_code))
        mysql.connection.commit()
        cur.execute("SELECT LAST_INSERT_ID()")
        gid = cur.fetchone()['LAST_INSERT_ID()']
        cur.execute("INSERT INTO group_members (gid, uid) VALUES (%s, %s)", (gid, uid))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('home'))
    return render_template('create_group.html')

@app.route('/group/<int:gid>')
def group_page(gid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT group_name FROM groups WHERE gid = %s", (gid,))
    group_name = cur.fetchone()['group_name']

    #to get all members of the group
    cur.execute("SELECT username FROM users JOIN group_members ON users.uid = group_members.uid WHERE gid = %s", (gid,))
    members = [row['username'] for row in cur.fetchall()]

    cur.execute("SELECT invite_code FROM groups WHERE gid=%s", (gid,))
    invite_code = cur.fetchone()['invite_code']
    cur.execute("SELECT * FROM paid_by WHERE gid=%s", (gid,))
    expenses = cur.fetchall()
    payers = []
    owed = []
    for i in expenses:
        cur.execute("SELECT username FROM users WHERE uid=%s", (i['payer'],))
        payers.append(cur.fetchone()['username'])
        amount = i['amount']
        owes = 0
        eid = i['eid']
        cur.execute("SELECT fid FROM paid_for WHERE eid=%s", {eid,})
        fids = [int(row['fid']) for row in cur.fetchall()]
        n = len(fids)
        if i['payer'] == session['uid']:   #the user has paid
            for j in fids:
                if j == i['payer']:
                    continue
                else:
                    owes += amount / n
            owes = round(owes,2)
            owed.append(-owes)
        else:
            if session['uid'] not in fids:
                owes = 0
            else:
                owes = amount / n
            owed.append(round(owes,2))
    cur.close()

    return render_template('group_page.html', group_name=group_name, members=members, invite_code=invite_code, gid=gid, expenses=expenses, payers=payers, owed=owed, uid=session['uid'])

@app.route('/join_group', methods=['GET', 'POST'])
def join_group():
    if request.method == 'POST':
        invite_code = request.form['invite_code']
        cur = mysql.connection.cursor()
        cur.execute("SELECT gid FROM groups WHERE invite_code = %s", (invite_code,))
        group = cur.fetchone()
        if group:
            gid = group['gid']
            uid = session['uid']
            cur.execute("SELECT * FROM group_members WHERE gid=%s and uid=%s", (gid, uid,))
            mem = cur.fetchall()
            if mem:
                error = 'You are already a member !'
                return render_template('join_group.html', error=error)
            cur.execute("INSERT INTO group_members (gid, uid) VALUES (%s, %s)", (gid, uid,))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('group_page', gid=gid))
        else:
            error = 'Invalid group key. Please try again.'
            return render_template('join_group.html', error=error)

    return render_template('join_group.html')

@app.route('/add_expense/<int:gid>', methods=['GET', 'POST'])
def add_expense(gid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users JOIN group_members ON users.uid=group_members.uid WHERE gid=%s", (gid,))
    members = cur.fetchall()
    cur.close()
    paid_for = []

    if request.method == 'POST':
        description = request.form['description']
        amount = request.form['amount']
        paid_by = request.form.getlist('paid_by[]')
        paid_for = request.form.getlist('paid_for[]')

        if not description or not amount or len(paid_by)==0 or len(paid_for)==0:
            error = 'Please fill all details !'
            return render_template('add_expense.html', error=error, gid=gid, paid_for=paid_for, members=members)
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO paid_by(description, amount, payer, gid) VALUES (%s, %s, %s, %s)", (description, amount, int(paid_by[0]), gid))
        mysql.connection.commit()
        cur.execute("SELECT LAST_INSERT_ID()")
        eid = cur.fetchone()['LAST_INSERT_ID()']
        paid_for_no = len(paid_for)
        for i in range(paid_for_no):
            cur.execute("INSERT INTO paid_for(eid, fid) VALUES (%s, %s)", (eid, int(paid_for[i])))
            mysql.connection.commit()
        cur.close()
        return redirect(url_for('group_page', gid=gid))
        
    return render_template('add_expense.html', gid=gid, members=members, paid_for=paid_for)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/exp/<int:gid>/<int:eid>')
def exp(gid,eid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM paid_by WHERE eid=%s", (eid,))
    expense = cur.fetchone()
    payerID = expense['payer']
    cur.execute("SELECT username FROM users WHERE uid=%s", (payerID,))
    payer = cur.fetchone()['username']
    return render_template('exp.html', gid=gid, expense=expense, payer=payer)


if __name__ == '__main__':
    app.run(debug=True)