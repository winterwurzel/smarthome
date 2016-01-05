# all the imports
import sqlite3, glob, importlib, atexit
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from flask.ext.script import Manager
from contextlib import closing
import RPi.GPIO as GPIO

# configuration
DATABASE = 'smarthome.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

manager = Manager(app)

devicelist = {}
imports = {}

def exit_handler():
    print "shutting down"
    GPIO.cleanup()
    #for dev in devicelist.itervalues():
        #dev.gpio_exit()

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

@manager.command
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


def init_devices():
    atexit.register(exit_handler)
    try:
        db = get_db()
        cur = db.execute('select id, name, description, type, pin, state, module from devices')
        db_devices = cur.fetchall()
        for device in db_devices:
            to_import = device[6][:-3]
            imports[device[0]] = importlib.import_module(to_import.replace("/", "."))
            devicelist[device[0]] = imports[device[0]].gpio(device[4])
            if device[3] == "output":
                devicelist[device[0]].write_value(device[5])
    except Exception, e:
        print str(e)


@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def homepage():
    try:
        if session.get('logged_in'):
            if request.form:
                print request.form['state']
                devNr = int(request.form['device'])
                print devNr
                devState = request.form['state']
                if devState == "true":
                    devState = 1
                else:
                    devState = 0
                print devState
                devicelist[devNr].write_value(devState)
                db = get_db()
                db.execute('update devices set state=? where id=?', [devState, devNr])
                db.commit()

            db = get_db()
            cur = db.execute("select id, name, description, type, pin, state, module from devices where type like 'output'")
            outputDevices = cur.fetchall()
            print outputDevices
            cur = db.execute("select id, name, description, type, pin, state, module from devices where type like 'input'")
            inputDevices = cur.fetchall()
            values = []
            for dev in inputDevices:
                values.append((dev[0], dev[1], dev[2], dev[3], dev[4], dev[5], dev[6], devicelist[dev[0]].get_value()))
            return render_template('overview.html', outputDevices=outputDevices, values=values)
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
    modules = glob.glob("modules/*.py")
    modules.remove("modules/__init__.py")
    return render_template("adddev.html", modules=modules)

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
    db = get_db()
    db.execute('delete from devices where id=?', dev)
    db.commit()
    devicelist.pop(int(dev))
    return redirect(url_for('homepage'))

@app.route('/edit', methods=['POST'])
def edit_device():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('update devices set name=?, description=? where id=?', [request.form['name'], request.form['description'], request.form['id']])
    db.commit()
    flash('Device was successfully edited')
    return redirect(url_for('homepage'))

@app.route('/add', methods=['POST'])
def add_device():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    if request.form['type'] == "output":
        db.execute('insert into devices (name, description, type, pin, module, state) values (?, ?, ?, ?, ?, ?)', [request.form['name'], request.form['description'], request.form['type'], request.form['pin'], request.form['mod'], 0])
    else:
        db.execute('insert into devices (name, description, type, pin, module) values (?, ?, ?, ?, ?)', [request.form['name'], request.form['description'], request.form['type'], request.form['pin'], request.form['mod']])
    db.commit()
    init_devices()
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

@manager.command
def runserver():
    init_devices()
    app.run()

if __name__ == "__main__":
    manager.run()
