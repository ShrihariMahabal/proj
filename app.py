from flask import Flask, render_template, request, redirect, session, url_for
from flask_session import Session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import secrets


app = Flask(__name__)

app.secret_key = 'sk'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'db1'
app.config['MYSQL_PORT'] = 3309
app.config['MYSQL_CURSORCLASS'] = "DictCursor"

mysql = MySQL(app)
colors = ['#6D9F71','#56CBF9','#525252','#FF8360','#30362F','#C7D66D']

@app.route('/')
def index():
    return render_template('intro.html')

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
        cur.execute("SELECT * FROM paid_for WHERE eid=%s", (eid,)) 
        paidfor = cur.fetchall()
        for j in paidfor:
            fid = j['fid']
            owed = j['amt']
            matrix[dic[payer]][dic[fid]] += owed
    cur.close()
    return matrix, dic

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT username, password, uid, email FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and user['password']==password:
            session['username'] = user['username']
            session['uid'] = user['uid']
            session['email'] = user['email']
            return redirect(url_for('home'))
        elif user:
            error="Incorrect Credentials"
            return render_template('login.html', error=error)
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
        uid = session['uid']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM groups JOIN group_members ON groups.gid=group_members.gid WHERE uid=%s", (uid,))
        groups = cur.fetchall()
        costs = []
        for i in groups:
            cur.execute("SELECT amount FROM paid_by WHERE gid=%s", (i['gid'],))
            amts = [row['amount'] for row in cur.fetchall()]
            costs.append(sum(amts))
        cur.close()
        return render_template('home.html', groups=groups, costs=costs, username=session['username'], active_page='home')
    return redirect(url_for('login'))

@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    if request.method == 'POST':
        group_name = request.form['group_name']

        if not group_name:
            error = 'Please enter valid group name !'
            return render_template('create_group.html', error=error)
        invite_code = secrets.token_hex(3)  # Generate random invite code
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
    cur.execute("SELECT * FROM users JOIN group_members ON users.uid = group_members.uid WHERE gid = %s", (gid,))
    users = cur.fetchall()
    # members = [row['username'] for row in users]
    # uids = [row['uid'] for row in users]

    cur.execute("SELECT invite_code FROM groups WHERE gid=%s", (gid,))
    invite_code = cur.fetchone()['invite_code']
    cur.execute("SELECT * FROM paid_by WHERE gid=%s", (gid,))
    expenses = cur.fetchall()
    payers = []
    owed = []
    for i in expenses:
        cur.execute("SELECT username FROM users WHERE uid=%s", (i['payer'],))
        payers.append(cur.fetchone()['username'])
        # amount = i['amount']
        owes = 0
        eid = i['eid']
        cur.execute("SELECT * FROM paid_for WHERE eid=%s", {eid,})
        paidfor = cur.fetchall()
        # n = len(fids)
        if i['payer'] == session['uid']:   #the user has paid
            for j in paidfor:
                if j['fid'] == i['payer']:
                    continue
                else:
                    owes += j['amt']
            owes = round(owes,2)
            owed.append(-owes)
        else:
            cur.execute("SELECT * FROM paid_for WHERE eid=%s AND fid=%s", (eid, session['uid'],))
            x = cur.fetchone()
            if x:
                owes = x['amt']
            else:
                owes = 0
            owed.append(round(owes,2))
    cur.close()
    matrix = split(gid)
    return render_template('group_page.html', group_name=group_name, invite_code=invite_code, gid=gid, expenses=expenses, payers=payers, owed=owed, matrix=matrix, users=users)

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

# @app.route('/add_expense/<int:gid>', methods=['GET', 'POST'])
# def add_expense(gid):
#     cur = mysql.connection.cursor()
#     cur.execute("SELECT * FROM users JOIN group_members ON users.uid=group_members.uid WHERE gid=%s", (gid,))
#     members = cur.fetchall()
#     cur.close()
#     paid_for = []

#     if request.method == 'POST':
#         description = request.form['description']
#         amount = request.form['amount']
#         paid_by = request.form.getlist('paid_by[]')
#         paid_for = request.form.getlist('paid_for[]')

#         if not description or not amount or len(paid_by)==0 or len(paid_for)==0:
#             error = 'Pleas    ill all details !'
#             return render_    plate('add_expense.html', error=error, gid=gid, paid_for=paid_for, members=members)
        
#         cur = mysql.connec    n.cursor()
#         cur.execute("INSER    NTO paid_by(description, amount, payer, gid) VALUES (%s, %s, %s, %s)", (description, amount, int(paid_by[0]), gid))
#         mysql.connection.commit()
#         cur.execute("SELECT LAST_INSERT_ID()")
#         eid = cur.fetchone()['LAST_INSERT_ID()']
#         paid_for_no = len(paid_for)
#         for i in range(paid_for_no):
#             cur.execute("INSERT INTO paid_for(eid, fid) VALUES (%s, %s)", (eid, int(paid_for[i])))
#             mysql.connection.commit()
#         cur.close()
#         return redirect(url_for('group_page', gid=gid))
        
#     return render_template('add_expense.html', gid=gid, members=members, paid_for=paid_for)

@app.route('/add_expense2/<int:gid>', methods=['GET', 'POST'])
def add_expense2(gid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users JOIN group_members ON users.uid=group_members.uid WHERE gid=%s", (gid,))
    members = cur.fetchall()
    paid_for = []

    if request.method == 'POST':
        description = request.form['description']
        amount = request.form['amount']
        paid_by = request.form.getlist('paid_by[]')
        paid_for = request.form.getlist('paid_for[]')
        per_person = []
        sum = 0
        for i in members:
            amt = request.form[f"ind{i['uid']}"]
            if not amt:
                amt = 0
            sum += float(amt)
            per_person.append(float(amt))
        
        if description and amount and paid_by:
            if paid_for:   #equal
                cur.execute("INSERT INTO paid_by(description, amount, payer, gid) VALUES (%s, %s, %s, %s)", (description, float(amount), int(paid_by[0]), gid))
                mysql.connection.commit()
                cur.execute("SELECT LAST_INSERT_ID()")
                eid = cur.fetchone()['LAST_INSERT_ID()']
                paid_for_no = len(paid_for)
                amt1 = float(amount) / paid_for_no
                for i in range(paid_for_no):
                    cur.execute("INSERT INTO paid_for(eid, fid, amt) VALUES (%s, %s, %s)", (eid, int(paid_for[i]), amt1,))
                    mysql.connection.commit()
                cur.close()
                return redirect(url_for('group_page', gid=gid))
            elif per_person.count(0) != len(members):        #unequal
                if sum != float(amount):
                    error = 'Individual Amounts and Total Amount not Equal'
                    return render_template('add_expense2.html', error=error, gid=gid, members=members)
                cur.execute("INSERT INTO paid_by(description, amount, payer, gid) VALUES (%s, %s, %s, %s)", (description, float(amount), int(paid_by[0]), gid))
                mysql.connection.commit()
                cur.execute("SELECT LAST_INSERT_ID()")
                eid = cur.fetchone()['LAST_INSERT_ID()']
                for idx, i in enumerate(members):
                    if per_person[idx] != 0:
                        cur.execute("INSERT INTO paid_for(eid, fid, amt) VALUES (%s, %s, %s)", (eid, int(i['uid']), per_person[idx]))
                        mysql.connection.commit()
                cur.close()
                return redirect(url_for('group_page', gid=gid))
            else:
                error = 'Please fill all details!'
                return render_template('add_expense2.html', error=error, gid=gid, members=members)
        else:
            error = 'Please fill all details!'
            return render_template('add_expense2.html', error=error, gid=gid, members=members)

    return render_template('add_expense2.html', gid=gid, members=members)

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
    cur.execute("SELECT * FROM paid_for WHERE eid=%s",(eid,))
    paidfor = cur.fetchall()
    dic = {}
    for i in paidfor:
        cur.execute("SELECT username FROM users WHERE uid=%s", (i['fid'],))
        user = cur.fetchone()['username']
        amt = i['amt']
        dic[user] = round(amt, 2)
    cur.close()
    return render_template('exp.html', gid=gid, colors=colors, eid=eid, expense=expense, payer=payer, dic=dic, n=len(dic))

@app.route('/edit_expense/<int:gid>/<int:eid>', methods=['GET', 'POST'])
def edit_exp(gid, eid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM paid_by WHERE eid=%s", (eid,))
    expense = cur.fetchone()
    cur.execute("SELECT * FROM users JOIN group_members ON users.uid=group_members.uid WHERE gid=%s", (gid,))
    members = cur.fetchall()
    Desc = expense['description']
    Amt = expense['amount']
    paidBy = expense['payer']
    cur.execute("SELECT amt FROM paid_for WHERE eid=%s", (eid,))
    participants = cur.fetchall()
    ind = []
    ind_amts = []

    #to check if split is equal/unequal
    isEqual = 1
    x = participants[0]['amt']
    for i in participants:
        if i['amt'] != x:
            isEqual = 0

    for i in members:
        uid = i['uid']
        cur.execute("SELECT amt FROM paid_for WHERE eid=%s AND fid=%s", (eid, uid,))
        forexpense = cur.fetchone()
        if forexpense:
            ind_amts.append(forexpense['amt'])
        else:
            ind_amts.append(0)
    
    #deleting previous expense and adding new one
    
    if request.method == 'POST':
        cur.execute("DELETE FROM paid_for WHERE eid=%s", (eid,))
        mysql.connection.commit()
        cur.execute("DELETE FROM paid_by WHERE eid=%s", (eid,))
        mysql.connection.commit()
        description = request.form['description']
        amount = request.form['amount']
        paid_by = request.form.getlist('paid_by[]')
        paid_for = request.form.getlist('paid_for[]')
        per_person = []
        sum = 0
        for i in members:
            amt = request.form[f"ind{i['uid']}"]
            if not amt:
                amt = 0
            sum += float(amt)
            per_person.append(float(amt))
        
        if description and amount and paid_by:
            if paid_for:   #equal
                cur.execute("INSERT INTO paid_by(description, amount, payer, gid) VALUES (%s, %s, %s, %s)", (description, float(amount), int(paid_by[0]), gid))
                mysql.connection.commit()
                cur.execute("SELECT LAST_INSERT_ID()")
                eid_ = cur.fetchone()['LAST_INSERT_ID()']
                paid_for_no = len(paid_for)
                amt1 = float(amount) / paid_for_no
                for i in range(paid_for_no):
                    cur.execute("INSERT INTO paid_for(eid, fid, amt) VALUES (%s, %s, %s)", (eid_, int(paid_for[i]), amt1,))
                    mysql.connection.commit()
                cur.close()
                return redirect(url_for('group_page', gid=gid))
            elif per_person.count(0) != len(members):        #unequal
                if sum != float(amount):
                    error = 'Individual Amounts and Total Amount not Equal'
                    return render_template('edit_expense.html', error=error, gid=gid, members=members)
                cur.execute("INSERT INTO paid_by(description, amount, payer, gid) VALUES (%s, %s, %s, %s)", (description, float(amount), int(paid_by[0]), gid))
                mysql.connection.commit()
                cur.execute("SELECT LAST_INSERT_ID()")
                eid_ = cur.fetchone()['LAST_INSERT_ID()']
                for idx, i in enumerate(members):
                    if per_person[idx] != 0:
                        cur.execute("INSERT INTO paid_for(eid, fid, amt) VALUES (%s, %s, %s)", (eid_, int(i['uid']), per_person[idx]))
                        mysql.connection.commit()
                cur.close()
                return redirect(url_for('group_page', gid=gid))
            else:
                error = 'Please fill all details!'
                return render_template('edit_expense.html', error=error, gid=gid, members=members)
        else:
            error = 'Please fill all details!'
            return render_template('edit_expense.html', error=error, gid=gid, members=members)


    return render_template('edit_expense.html', members=members, gid=gid, eid=eid, Desc=Desc, Amt=Amt, paidBy=paidBy, isEqual=isEqual, ind_amts=ind_amts)

@app.route('/settle/<int:gid>/<int:uid>')
def settle(gid, uid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users JOIN group_members ON users.uid=group_members.uid WHERE gid=%s", (gid,))
    members = cur.fetchall()
    cur.execute("SELECT * FROM users WHERE uid=%s", (uid,))
    hero = cur.fetchone()
    settlements = {}
    balance = 0
    matrix, dic = split(gid)
    for i in members:
        if i['uid'] == hero['uid']:
            continue
        else:
            memberID = i['uid']
            username = i['username']
            amt = matrix[dic[uid]][dic[memberID]] - matrix[dic[memberID]][dic[uid]]
            balance += amt
            if amt != 0:
                settlements[username] = round(amt,2)

    return render_template('settlement.html', settlements=settlements, hero=hero, gid=gid, balance=round(balance,2), colors=colors)

@app.route('/friends')
def friends():  
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM friends JOIN users ON friends.friend_id=users.uid WHERE friends.uid=%s", (session['uid'],))
    friends=cur.fetchall()
    cur.close()

    return render_template('friends.html',friends=friends, name=session['username'])
    
@app.route('/add_friend', methods=['GET', 'POST'])  
def add_friend():
    if request.method=='POST':
        friend_email=request.form['friend_email']

        if not friend_email:
            error='Invalid Email Address'
            return render_template('add_friend.html', error=error)
        
        cur=mysql.connection.cursor()    
        cur.execute("SELECT uid FROM users WHERE email=%s", (friend_email,))
        friend_id=cur.fetchone()

        if not friend_id:
            error2='No User Found'
            return render_template('add_friend.html', error2=error2)
        
        cur.execute("INSERT INTO friends (uid, friend_id) VALUES (%s, %s), (%s, %s)", (session['uid'], friend_id['uid'], friend_id['uid'], session['uid']))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('friends'))
    
    return render_template('add_friend.html')

@app.route('/friend_settle/<int:friend_id>')
def friend_settle(friend_id):
    user=session['uid']
    amt_owes=0
    amt_owed=0
    list_gid={}
    cur=mysql.connection.cursor()
    cur.execute("SELECT username FROM users WHERE uid=%s", (friend_id,))
    name=cur.fetchone()

    cur.execute("SELECT payer,fid,paid_for.amt,paid_by.gid,groups.group_name,description FROM paid_by JOIN paid_for JOIN groups ON paid_by.eid=paid_for.eid AND paid_by.gid=groups.gid WHERE (payer=%s AND fid=%s) OR (payer=%s AND fid=%s)", (friend_id,user,user,friend_id))
    list=cur.fetchall()
    cur.close()
    
    for idx,i in enumerate(list):
        list_gid[list[idx]['gid']]=list[idx]['group_name']
        if list[idx]['payer']==user and list[idx]['fid']==friend_id:
            amt_owed+=list[idx]['amt']
        elif list[idx]['payer']==friend_id and list[idx]['fid']==user:
            amt_owes+=list[idx]['amt'] 

    return render_template('friend_settle.html',amt_owed=amt_owed,amt_owes=amt_owes,name=name,list=list, list_gid=list_gid,user=user, friend_id=friend_id)

@app.route('/account')
def account():
    amt_owes=0
    amt_owed=0
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE uid=%s", (session['uid'],))
    user=cur.fetchone()
    cur.execute("SELECT * FROM paid_by JOIN paid_for ON paid_by.eid=paid_for.eid WHERE payer=%s OR fid=%s", (session['uid'],session['uid']))
    owe=cur.fetchall()
    cur.close()

    for idx,i in enumerate(owe):
        if owe[idx]['payer']==session['uid'] and not owe[idx]['fid']==session['uid']:
            amt_owed+=owe[idx]['amt'] 
        if owe[idx]['fid']==session['uid'] and not owe[idx]['payer']==session['uid']:
            amt_owes+=owe[idx]['amt']

    return render_template('account.html', user=user,amt_owes=amt_owes,amt_owed=amt_owed)

@app.route('/edit_username', methods=['GET','POST'])
def edit_username():
    cur=mysql.connection.cursor()
    cur.execute("SELECT username from users")
    existing= [row['username'] for row in cur.fetchall()] 
    if request.method=='POST':
        new_username=request.form['new_username']

        if new_username in existing:
            error="Username Already Exists"
            return render_template('edit_username.html', error=error)
        
        cur.execute("UPDATE users SET username=%s WHERE uid=%s", (new_username,session['uid']))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('account'))
    return render_template('edit_username.html',existing=existing)

@app.route('/password', methods=['GET','POST'])
def edit_password():
    cur=mysql.connection.cursor()
    cur.execute("SELECT password from users WHERE uid=%s", (session['uid'],))
    password=cur.fetchone()
    if request.method=='POST':
        current_password=request.form['current_password']
        new_password=request.form['new_password']
        re_new_password=request.form['re_new_password']

        if current_password!=password['password']:
            error="Incorrect Password"
            return render_template('edit_password.html', error=error)
        
        if new_password!=re_new_password:
            error2="New Password dosen't match Re-Typed Password"
            return render_template('edit_password.html', error2=error2)
        
        cur.execute("UPDATE users SET password=%s WHERE uid=%s", (new_password,session['uid']))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('account'))
    return render_template('edit_password.html')

@app.route('/dashboard')
def dashboard():
    amt_owes=0
    amt_owed=0
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE uid=%s", (session['uid'],))
    user=cur.fetchone()
    cur.execute("SELECT * FROM paid_by JOIN paid_for ON paid_by.eid=paid_for.eid WHERE payer=%s OR fid=%s", (session['uid'],session['uid']))
    owe=cur.fetchall()
    cur.execute("SELECT * FROM paid_by JOIN groups ON paid_by.gid=groups.gid WHERE payer=%s", (session['uid'],))
    paid=cur.fetchall()
    cur.close()

    for idx,i in enumerate(owe):
        if owe[idx]['payer']==session['uid'] and not owe[idx]['fid']==session['uid']:
            amt_owed+=owe[idx]['amt'] 
        if owe[idx]['fid']==session['uid'] and not owe[idx]['payer']==session['uid']:
            amt_owes+=owe[idx]['amt']
    return render_template('dashboard.html', amt_owed=amt_owed, amt_owes=amt_owes, paid=paid)

@app.route('/payment_chart/<int:gid>')
def payment_chart(gid):
    total_payment=0
    cur=mysql.connection.cursor()
    cur.execute("SELECT * FROM paid_by JOIN users ON paid_by.payer=users.uid WHERE gid=%s", (gid,))
    chart_data=cur.fetchall()
    cur.execute("SELECT group_name FROM groups WHERE gid=%s", (gid,))
    group_name=cur.fetchone()['group_name']
    cur.execute("SELECT invite_code FROM groups WHERE gid=%s", (gid,))
    invite_code=cur.fetchone()['invite_code']
    cur.close()

    for idx,i in enumerate(chart_data):
        total_payment+=chart_data[idx]['amount']
    return render_template('payment_chart.html',chart_data=chart_data,group_name=group_name,gid=gid,total_payment=total_payment,invite_code=invite_code)

if __name__ == '__main__':
    app.run(debug=True, host="192.168.136.11")

# host="192.168.0.164"