# all the imports
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from contextlib import closing

# configuration
DATABASE = 'smarthome.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/')
def homepage():
    try:
        if session.get('logged_in'):
            db = get_db()
            cur = db.execute('select id, name, description, type, pin, state from devices')
            devices = cur.fetchall()
            return render_template('overview.html')
        else:
            return render_template("index.html")
    except Exception, e:
        return str(e)

@app.route('/devices')
def devices():
    db = get_db()
    cur = db.execute('select id, name, description, type, pin from devices')
    devices = cur.fetchall()
    return render_template("devices.html", devices=devices)

@app.route('/adddev')
def adddev():
    return render_template("adddev.html")

@app.route('/editdev')
def editdev():
    dev = request.args.get("dev")
    db = get_db()
    cur = db.execute('select id, name, description, type, pin from devices where id=?', dev)
    dev = cur.fetchall()
    return render_template("editdev.html", dev=dev)

@app.route('/deletedev')
def deletedev():
    dev = request.args.get("dev")
    print dev
    db = get_db()
    db.execute('delete from devices where id=?', dev)
    db.commit()
    return redirect(url_for('homepage'))

@app.route('/edit', methods=['POST'])
def edit_device():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('update devices set name=?, description=?, type=?, pin=? where id=?', [request.form['name'], request.form['description'], request.form['type'], request.form['pin'], request.form['id']])
    db.commit()
    flash('Device was successfully edited')
    return redirect(url_for('homepage'))

@app.route('/add', methods=['POST'])
def add_device():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    if request.form['type'] is "output":
        db.execute('insert into devices (name, description, type, pin, state=0) values (?, ?, ?, ?)', [request.form['name'], request.form['description'], request.form['type'], request.form['pin']])
    else:
        db.execute('insert into devices (name, description, type, pin) values (?, ?, ?, ?)', [request.form['name'], request.form['description'], request.form['type'], request.form['pin']])
    db.commit()
    flash('New device was successfully added')
    return redirect(url_for('homepage'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('You were logged in')
            return redirect(url_for('homepage'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You were logged out')
    return redirect(url_for('homepage'))

if __name__ == "__main__":
	app.run()
