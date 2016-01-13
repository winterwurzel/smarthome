# all the imports
import glob, importlib, atexit
from werkzeug import generate_password_hash, check_password_hash
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, current_app, jsonify
from flask.ext.script import Manager
import flask.ext.login as flask_login
from flask.ext.security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, roles_accepted
from flask.ext.security.utils import encrypt_password
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.orm.exc import UnmappedInstanceError
from flask_mail import Mail
from pprint import pprint
import RPi.GPIO as GPIO

# configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///alchemy.db'
DEBUG = True
SECRET_KEY = 'development key'
SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_PASSWORD_SALT = 'asdfghjkl'
SECURITY_DEFAULT_REMEMBER_ME = True
SECURITY_CHANGEABLE = True
SECURITY_REGISTERABLE = True
SECURITY_CHANGE_URL = '/change'
SECURITY_TRACKABLE = True
SECURITY_EMAIL_SENDER = 'smarthrpi@gmail.com'
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USERNAME = 'smarthrpi@gmail.com'
MAIL_PASSWORD = 'shrpi123'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

db = SQLAlchemy(app)
manager = Manager(app)
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
mail = Mail(app)

imports = {}
devicelist = {}
input_values = {}

# Define models
roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    #username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    authenticated = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(63))
    current_login_ip = db.Column(db.String(63))
    login_count = db.Column(db.Integer())


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))        #pref. name of device
    description = db.Column(db.Text)        #device description, otpional
    dtype = db.Column(db.String(20))         #device type: input or output
    pin = db.Column(db.Integer)             #pin the device uses
    state = db.Column(db.Boolean)           #only for output devices 0 = false, 1 = true, null for other devices
    module = db.Column(db.String(100))      #path to module of this device

    def __init__(self, name, description, dtype, pin, state, module):
        self.name = name
        self.description = description
        self.dtype = dtype
        self.pin = pin
        self.state = state
        self.module = module

    def __str__(self):
        return str(self.id) + ", " + self.name + ", " + self.description + ", " + self.dtype + ", " + str(self.pin) + ", " + str(self.state) + ", " + self.module

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

def exit_handler():
    print "shutting down"
    GPIO.cleanup()

@manager.command
def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        #default values for the db
        user = user_datastore.create_user(email='georg.markowitsch@gmail.com', password=encrypt_password('admin'))
        adminRole = user_datastore.create_role(name='admin', description='admin can add/remove other users, no access restrictions')
        userRole = user_datastore.create_role(name='user', description='basic access')
        user_datastore.add_role_to_user(user, adminRole)
        user_datastore.add_role_to_user(user, userRole)
        db.session.add(Device('Dummy Sensor 1', 'best sensor in the universe', 'input', 18, None, 'modules/gpio_input.py'))
        db.session.add(Device('Dummy Sensor 2', 'best description in the universe', 'input', 16, None, 'modules/gpio_input.py'))
        db.session.add(Device('led', 'bright led', 'output', 11, 0, 'modules/gpio_output.py'))
        db.session.add(Device('led3', 'a zweite led', 'output', 12, 0, 'modules/gpio_output.py'))
        db.session.add(Device('led35', 'onboard', 'output', 35, 0, 'modules/gpio_output.py'))
        db.session.commit()

def gpio_callback(pin, value):
    input_values[pin] = value
    print "pin " + str(pin) + " value " + str(value)


def init_devices():
    atexit.register(exit_handler)
    try:
        devices = Device.query.all()
        for device in devices:
            to_import = device.module[:-3]
            imports[device.id] = importlib.import_module(to_import.replace("/", "."))
            if device.dtype == "input":
                devicelist[device.id] = imports[device.id].gpio(device.pin, gpio_callback)
                input_values[device.pin] = devicelist[device.id].get_value()
            else:
                devicelist[device.id] = imports[device.id].gpio(device.pin)
            if device.dtype == "output":
                devicelist[device.id].write_value(device.state)
    except Exception, e:
        print str(e)

@login_manager.user_loader
def load_user(email):
    # Return an instance of the User model
    return User.query.filter_by(email=email).first()

@app.route('/', methods=['GET', 'POST'])
def homepage():
    try:
        if request.form:
            devNr = int(request.form['device'])
            devState = request.form['state']
            if devState == "true":
                devState = 1
            else:
                devState = 0
            devicelist[devNr].write_value(devState)
            device = Device.query.get(devNr)
            device.state = devState
            db.session.commit()

        outputDevices = Device.query.filter_by(dtype='output').all()
        inputDevices = Device.query.filter_by(dtype='input').all()
        values = []

        auth = False
        if flask_login.current_user.has_role('user') or flask_login.current_user.has_role('admin'):
            auth = True

        for dev in inputDevices:
            values.append((dev.id, dev.name, dev.description, dev.dtype, dev.pin, dev.state, dev.module, input_values[dev.pin]))#devicelist[dev.id].get_value()))
        return render_template('overview.html', outputDevices=outputDevices, values=values, auth=auth if hasattr(flask_login.current_user, 'authenticated') else False)
    except Exception, e:
        return "exception " + str(e)

@app.route('/refresh', methods= ['GET'])
def refresh():
    return jsonify(values=input_values)

@app.route('/users')
@login_required
@roles_accepted('admin')
def users():
    userlist = User.query.outerjoin(roles_users, User.id == roles_users.c.user_id).outerjoin(Role, Role.id == roles_users.c.role_id).all()
    return render_template("users.html", userlist=userlist)

@app.route('/deleteuser')
@login_required
@roles_accepted('admin')
def deleteuser():
    user_id = request.args.get("user_id")
    userToDel = User.query.outerjoin(roles_users, User.id == roles_users.c.user_id).outerjoin(Role, Role.id == roles_users.c.role_id).filter(User.id == user_id).first()
    for role in userToDel.roles:
        if role.name == 'admin':
            flash('admin user can not be deleted')
            return redirect(url_for('users'))
    db.session.delete(userToDel)
    db.session.commit()
    return redirect(url_for('users'))

@app.route('/userinfo')
@login_required
@roles_accepted('admin')
def userinfo():
    user_id = request.args.get("user_id")
    user = User.query.outerjoin(roles_users, User.id == roles_users.c.user_id).outerjoin(Role, Role.id == roles_users.c.role_id).filter(User.id == user_id).first()
    roles = Role.query.all()
    return render_template("userinfo.html", user=user, roles=roles)

@app.route('/changeroles', methods=['POST'])
@login_required
@roles_accepted('admin')
def changeroles():
    user_id = request.form["user_id"]
    #print user_id
    roles = Role.query.all()
    del roles[0]
    for role in roles:
        role_id = request.form.getlist("role" + str(role.id))
        #print role_id
        user = User.query.get(user_id)
        if len(role_id) > 0:
            user_datastore.add_role_to_user(user, role)
            db.session.commit()
            flash('Added Role "' + role.name + '" to User "' + user.email + '"')
        else:
            user_datastore.remove_role_from_user(user, role)
            db.session.commit()
            flash('Removed Role "' + role.name + '" from User "' + user.email + '"')
    return redirect(url_for('users'))

@app.route('/devices')
@login_required
@roles_accepted('user', 'admin')
def devices():
    devices = Device.query.all()
    return render_template("devices.html", devices=devices)

@app.route('/adddev')
@login_required
@roles_accepted('user', 'admin')
def adddev():
    modules = glob.glob("modules/*.py")
    modules.remove("modules/__init__.py")
    return render_template("adddev.html", modules=modules)

@app.route('/editdev')
@login_required
@roles_accepted('user', 'admin')
def editdev():
    devId = request.args.get("dev")
    device = Device.query.get(devId)
    return render_template("editdev.html", dev=device)

@app.route('/deletedev')
@login_required
@roles_accepted('user', 'admin')
def deletedev():
    devId = request.args.get("dev")
    devToDel = Device.query.get(devId)
    db.session.delete(devToDel)
    db.session.commit()
    return redirect(url_for('homepage'))

@app.route('/edit', methods=['POST'])
@login_required
@roles_accepted('user', 'admin')
def edit_device():
    devId = request.form['id']
    device = Device.query.get(devId)
    device.name = request.form['name']
    device.description = request.form['description']
    db.session.commit()
    return redirect(url_for('homepage'))

@app.route('/add', methods=['POST'])
@login_required
@roles_accepted('user', 'admin')
def add_device():
    if request.form['type'] == "output":
        newDev = Device(request.form['name'], request.form['description'], request.form['type'], request.form['pin'], 0, request.form['mod'])
        db.session.add(newDev)
        db.session.commit()
    else:
        newDev = Device(request.form['name'], request.form['description'], request.form['type'], request.form['pin'], None, request.form['mod'])
        db.session.add(newDev)
        db.session.commit()
    init_devices()
    flash('New device was successfully added')
    return redirect(url_for('homepage'))

@app.route('/settings', methods=['POST', 'GET'])
@login_required
@roles_accepted('user', 'admin')
def settings():
    if request.method == 'POST':
        if request.form['submit'] == 'settings':
            return redirect(url_for('security.change_password'))
    return render_template('settings.html')

@flask_login.user_logged_in.connect_via(app)
def on_user_logged_in(sender, user):
    session['logged_in'] = True
    session['email'] = user.email
    flash('Successfully Logged In')

@flask_login.user_logged_out.connect_via(app)
def on_user_logged_out(sender, user):
    session.pop('logged_in', None)
    session.pop('email', None)
    flash('Successfully Logged Out')

@manager.command
def runserver():
    init_devices()
    app.run(host='0.0.0.0')

if __name__ == "__main__":
    manager.run()
