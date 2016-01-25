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


GPIO.setwarnings(False)

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
dev_values = {}

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
    pin = db.Column(db.Integer)             #pin the device uses
    dtype = db.Column(db.String(20))        #general type of device, output or input
    state = db.Column(db.Boolean)           #only for output devices 0 = false, 1 = true, None for other devices
    module = db.Column(db.String(100))      #path to module of this device, also determines the type of the device
    other1 = db.Column(db.String(100))       #other data depending on the module used
    other2 = db.Column(db.String(100))       #other data depending on the module used

    def __init__(self, name, description, pin, dtype, module, state=None, other1=None, other2=None):
        self.name = name
        self.description = description
        self.pin = pin
        self.dtype = dtype
        self.state = state
        self.module = module
        self.other1 = other1
        self.other2 = other2

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
        db.session.add(Device('Dummy Sensor 1', 'best sensor in the universe', 23, 'input', 'modules/gpio_input.py'))
        db.session.add(Device('Dummy Sensor 2', 'best description in the universe', 24, 'input', 'modules/gpio_input.py'))
        db.session.add(Device('led', 'onboard', 35, 'output', 'modules/gpio_output.py', 0))
        db.session.add(Device('funksetckdose', 'funksetckdose A', 4, 'output', 'modules/gpio_funk.py', 1, '11111', 1))
        db.session.add(Device('arduino', 'arduino leonardo onboard temperature', None, 'i2c', 'modules/gpio_i2c.py', None, 4, 1))
        db.session.add(Device('serial', 'serial demo', None, 'serial', 'modules/gpio_serial.py', None, '/dev/ttyAMA0', 9600))
        db.session.add(Device('spi', 'spi demo', None, 'spi', 'modules/gpio_spi.py', None, 0, 0))
        db.session.commit()

def gpio_callback(pin, value):
    device = Device.query.filter_by(pin=pin).first()
    dev_values[device.id] = value
    print "pin " + str(pin) + " value " + str(value)

def init_devices():
    atexit.register(exit_handler)
    try:
        devices = Device.query.all()
        for device in devices:
            if device.id in imports:
                print "already imported device id: " + str(device.id)
            else:
                to_import = device.module[:-3]
                print "importing: " + device.module
                imports[device.id] = importlib.import_module(to_import.replace("/", "."))

                #module dependend initialization
                if device.module == "modules/gpio_input.py":
                    devicelist[device.id] = imports[device.id].dev(device.pin, gpio_callback)
                    dev_values[device.id] = devicelist[device.id].get_value()
                elif device.module == "modules/gpio_funk.py":
                    devicelist[device.id] = imports[device.id].dev(device.pin, list(device.other1), int(device.other2))
                    devicelist[device.id].write_value(device.state)
                    dev_values[device.id] = device.state
                elif device.module == "modules/gpio_input.py":
                    devicelist[device.id] = imports[device.id].dev(device.pin)
                    devicelist[device.id].write_value(device.state)
                    dev_values[device.id] = device.state
                elif device.module == "modules/gpio_i2c.py":
                    address = int(device.other1)
                    command = int(device.other2)
                    devicelist[device.id] = imports[device.id].dev(address)
                    devicelist[device.id].write_value(command)
                    dev_values[device.id] = devicelist[device.id].get_value()
                elif device.module == "modules/gpio_serial.py":
                    #split = device.other1.split(';')
                    port = device.other1
                    baudrate = int(device.other2)
                    devicelist[device.id] = imports[device.id].dev(port, baudrate)
                    #devicelist[device.id].write_value(device.other1)
                    #dev_values[device.id] = devicelist[device.id].get_value()
                elif device.module == "modules/gpio_spi.py":
                    #split = device.other1.split(';')
                    bus = int(device.other1)
                    sdevice = int(device.other2)
                    devicelist[device.id] = imports[device.id].dev(bus, sdevice)
                    #devicelist[device.id].write_value(device.other1)
                    #dev_values[device.id] = devicelist[device.id].get_value()

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
            dev_values[device.id] = devState

        outputDevices = Device.query.filter_by(dtype='output').all()
        inputDevices = Device.query.filter_by(dtype='input').all()
        i2cDevices = Device.query.filter_by(dtype='i2c').all()
        values = []

        auth = False
        if flask_login.current_user.has_role('user') or flask_login.current_user.has_role('admin'):
            auth = True

        for dev in inputDevices:
            values.append((dev.id, dev.name, dev.description, dev.dtype, dev.pin, dev.state, dev.module, dev_values[dev.id]))#devicelist[dev.id].get_value()))

        i2cValues = []
        for dev in i2cDevices:
            devicelist[dev.id].write_value(dev.other2)
            dev_values[dev.id] = devicelist[dev.id].get_value()
            i2cValues.append((dev.id, dev.name, dev.description, dev.dtype, dev.other1, dev.state, dev.module, dev_values[dev.id]))

        return render_template('overview.html', outputDevices=outputDevices, values=values, i2cValues=i2cValues, auth=auth if hasattr(flask_login.current_user, 'authenticated') else False)
    except Exception, e:
        return "exception " + str(e)

@app.route('/refresh', methods= ['GET'])
def refresh():
    return jsonify(values=dev_values)

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

@app.route('/adddevchooser')
@login_required
@roles_accepted('user', 'admin')
def adddevchooser():
    modules = glob.glob("modules/*.py")
    modules.remove("modules/__init__.py")
    return render_template("adddevchooser.html", modules=modules)

@app.route('/adddev', methods=['POST'])
@login_required
@roles_accepted('user', 'admin')
def adddev():
    to_import = request.form['mod'][:-3]
    imported = importlib.import_module(to_import.replace("/", "."))
    return render_template(imported.get_form(), module=request.form['mod'])

@app.route('/editdev')
@login_required
@roles_accepted('user', 'admin')
def editdev():
    devId = request.args.get("dev")
    device = Device.query.get(devId)
    return render_template(imports[int(devId)].get_form(), dev=device)

@app.route('/deletedev')
@login_required
@roles_accepted('user', 'admin')
def deletedev():
    devId = request.args.get("dev")
    devToDel = Device.query.get(devId)
    db.session.delete(devToDel)
    db.session.commit()
    imports.pop(devId, None)
    return redirect(url_for('homepage'))

@app.route('/edit', methods=['POST'])
@login_required
@roles_accepted('user', 'admin')
def edit_device():
    devId = request.form['id']
    device = Device.query.get(devId)
    device.name = request.form['name']
    device.description = request.form['description']
    if 'other1' in request.form:
        device.other1 = request.form['other1']
    if 'other2' in request.form:
        device.other2 = request.form['other2']
    db.session.commit()
    return redirect(url_for('homepage'))

@app.route('/add', methods=['POST'])
@login_required
@roles_accepted('user', 'admin')
def add_device():
#name, description, pin, dtype, module, state=None, other1=None, other2=None

    to_import = request.form['mod'][:-3]
    imported = importlib.import_module(to_import.replace("/", "."))
    print to_import

    if request.form['mod'] == "modules/gpio_output.py":
        defaultState = 0
    else:
        defaultState = None

    newDev = Device(request.form['name'], request.form['description'], request.form['pin'] if('pin' in request.form) else None, \
        imported.get_dtype(), request.form['mod'], defaultState, \
        request.form['other1'] if('other1' in request.form) else None, request.form['other2'] if('other2' in request.form) else None)

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
