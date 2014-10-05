from flask import Flask, session, redirect, url_for, escape, request, render_template, g, abort, flash, Markup, send_from_directory
import sqlite3
import os
import hashlib
from flask.ext.misaka import markdown
import random
import string
import time
import re
from flask.ext.babel import Babel
from flask.ext.mail import Mail
from requests import ConnectionError
from urlparse import urlparse
from functools import wraps
from flask.ext.user import roles_required
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.user import current_user, login_required, SQLAlchemyAdapter, UserManager, UserMixin
from flask.ext.user.forms import RegisterForm
from wtforms import validators
from wtforms import StringField
from wtforms import SelectField
from wtforms.validators import Required
#import docker
#from docker.errors import *


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'db/webrob.db'),
    SQLALCHEMY_DATABASE_URI = 'sqlite:///webrob.db',
    CSRF_ENABLED = True,
    #DATABASE='/home/adminuser/GIT/docker/user_db/webrob.db',
    DEBUG=True,
    SECRET_KEY='\\\xf8\x12\xdc\xf5\xb2W\xd4Lh\xf5\x1a\xbf"\x05@Bg\xdf\xeb>E\xd8<',
    USERNAME='admin',
    PASSWORD='default',
    USER_ENABLE_USERNAME = True,
    #SERVER_NAME='192.168.100.184:5000'
    MAIL_SERVER   = 'smtp.gmail.com',
    MAIL_PORT     = 465,
    MAIL_USE_SSL  = True,                            # Some servers use MAIL_USE_TLS=True instead
    MAIL_USERNAME = 'email@example.com',
    MAIL_PASSWORD = 'password',
    MAIL_DEFAULT_SENDER = '"Sender" <noreply@example.com>',
    USER_ENABLE_EMAIL           = True,              # Register with email
    USER_ENABLE_CONFIRM_EMAIL   = False		     
))
#app.config.from_envvar('FLASKR_SETTINGS', silent=True)

babel = Babel(app)                              # Initialize Flask-Babel
mail = Mail(app)                                # Initialize Flask-Mail
db = SQLAlchemy(app)                            # Initialize Flask-SQLAlchemy

@babel.localeselector
def get_locale():
    translations = [str(translation) for translation in babel.list_translations()]
    return request.accept_languages.best_match(translations)

# Define the User-Roles pivot table
user_roles = db.Table('user_roles',
    db.Column('id', db.Integer(), primary_key=True),
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE')))

# Define Role model
class Role(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

# Define User model. Make sure to add flask.ext.user UserMixin!!
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column(db.Boolean(), nullable=False, default=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())
    password = db.Column(db.String(255), nullable=False, default='')
    reset_password_token = db.Column(db.String(100), nullable=False, default='')
    container_id = db.Column(db.String(255), nullable=False, default='')

    # Relationships
    roles = db.relationship('Role', secondary=user_roles,
            backref=db.backref('users', lazy='dynamic'))

#class MyRegisterForm(RegisterForm):
    #roles = SelectField('Rolle', validators=[Required('Rolle erforderlich')])

# Reset all the database tables
db.create_all()

# Setup Flask-User
db_adapter = SQLAlchemyAdapter(db,  User)
user_manager = UserManager(db_adapter, app)#, register_form=MyRegisterForm)

if not User.query.filter(User.username=='user007').first():
    user1 = User(username='user007', email='user007@example.com', active=True,
        password=user_manager.hash_password('Password1'))
    user1.roles.append(Role(name='secret'))
    user1.roles.append(Role(name='agent'))
    db.session.add(user1)
    db.session.commit()


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Docker stuff
"""
def docker_connect():
    c = docker.Client(base_url='unix://var/run/docker.sock', version='1.12',timeout=10)
    return c
    

#def create_data_containers():

    #try:
        #c = docker_connect()

        #session['user_data_container_name'] = session['username'] + "_data"
        #session['common_data_container_name'] = "knowrob_data"

        #if(c is not None):
            #c.create_container('knowrob/user_data', detach=True, tty=True, name=session['user_data_container_name'])

    #except ConnectionError:
        #flash("Error: Connection to your KnowRob instance failed.")
        #return None


def start_container():

    try:
        c = docker_connect()

        if(c is not None):

            all_containers = c.containers(all=True)

            # check if containers exist:
            user_cont_exists=False
            user_data_cont_exists=False
            common_data_exists=False
            mongo_cont_exists=False

            for cont in all_containers:
              if "/"+session['user_container_name'] in cont['Names']:
                user_cont_exists=True
              if "/"+session['user_data_container_name'] in cont['Names']:
                user_data_cont_exists=True
              if "/"+session['common_data_container_name'] in cont['Names']:
                common_data_exists=True
              if "/mongo_db" in cont['Names']:
                mongo_cont_exists=True


            # Create containers if they do not exist yet
            if not user_cont_exists:
                print('Creating container for ' + session['username'])
                c.create_container('knowrob/hydro-knowrob-daemon', detach=True, tty=True, name=session['user_container_name'])

            if not user_data_cont_exists:
                c.create_container('knowrob/user_data', detach=True, tty=True, name=session['user_data_container_name'], entrypoint='true')
                c.start(session['user_data_container_name'])

            if not common_data_exists:
                c.create_container('knowrob/knowrob_data', detach=True, name=session['common_data_container_name'], entrypoint='true')
                c.start(name=session['common_data_container_name'])

            if not mongo_cont_exists:
                c.create_container('busybox', detach=True, name='mongo_data', volumes=['/data/db'], entrypoint='true')
                c.create_container('mongo',   detach=True,ports=[27017], name='mongo_db')
                c.start('mongo', port_bindings={27017:27017}, volumes_from=['mongo_data'])
                
            session['user_container_id'] = c.start(session['user_container_name'],
                                                   publish_all_ports=True,
                                                   links={('mongo_db', 'mongo')},
                                                   volumes_from=[session['user_data_container_name'],
                                                                 session['common_data_container_name']])
            session['port_1111'] = c.port(session['username'], 1111)[0]['HostPort']
            session['port_9090'] = c.port(session['username'], 9090)[0]['HostPort']

    except APIError, e:
        if "Conflict" in str(e.message):
            flash("Name conflict: Container for this user already exists")
        else:
            flash(e.message)
        return None
    except ConnectionError:
        flash("Error: Connection to your KnowRob instance failed.")
        return None


def stop_container():

    try:
        c = docker_connect()

        if(c is not None):
            all_containers = c.containers(all=True)

            # check if containers exist:
            user_cont_exists=False

            for cont in all_containers:
                if "/"+session['user_container_name'] in cont['Names']:
                    user_cont_exists=True

            if user_cont_exists:
          
                print("Stopping container " + session['user_container_name'] + "...\n")
                c.stop(session['user_container_name'], timeout=5)

                print("Removing container " + session['user_container_name'] + "...\n")
                c.remove_container(session['user_container_name'])


            session.pop('user_container_name')

    except ConnectionError:
        flash("Error: Connection to your KnowRob instance failed.")
        return None
"""
    
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Web stuff

"""
def roles_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if get_role(session['username']) not in roles:
		return "You are not authorized to access this page :("
	        #return render_template('knowrob.html', **locals())
	    return f(*args, **kwargs)
    	return decorated_function
    return wrapper
"""		 

@app.route('/')
@login_required
def show_user_data():
    if not current_user.is_authenticated():
        return redirect(url_for('user.login'))
    #if not session.get('logged_in'):
        #return redirect(url_for('login'))
    #get_user_data(current_user.username)
    print request.host

    
    overlay = None
    if(session.get('show_loading_overlay') == True):
        overlay = True
        
        print "set overlay"
        session.pop('show_loading_overlay')
    
    return render_template('show_user_data.html', overlay=overlay)

@app.route('/pr2_description/meshes/<path:filename>')
def download_file(filename):
    return send_from_directory('/opt/webapp/pr2_description/meshes/', filename, as_attachment=True)
    

@app.route('/login/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if (request.form['username'] != "" and request.form['password'] != ""):
            if is_valid_user(request.form['username'], request.form['password']):
              
                session['username'] = request.form['username']

                session['user_container_name'] = session['username']
                session['user_data_container_name'] = session['username'] + "_data"
                session['common_data_container_name'] = "knowrob_data"
                
		session['role'] = get_role(request.form['username'])
                session['logged_in'] = True
                session['rosauth_mac'] = generate_mac()
                flash('You were logged in')

                session['show_loading_overlay'] = True
                
                #start_container()
                return redirect(url_for('show_user_data'))
            else :
                error = 'Invalid user data'
    return render_template('login.html', error=error, action="login")

@app.route('/logout')
def logout():
    if not current_user.is_authenticated():
        return redirect(url_for('user.login'))
    session.pop('logged_in', None)
    #stop_container()
    flash('You were logged out')
    return redirect(url_for('show_user_data'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':

        if (request.form['username'] == ""):
            error = 'Please specify a user name.'

        elif (request.form['password'] == ""):
            error = 'Please specify a password'

        elif(request.form['email'] == ""):
            error = 'Please specify an email address.'

        elif(user_exists(request.form['username'])):
            error = 'This username already exists. Please choose another username.'
            
        else:
            insert_user(request.form['username'], request.form['password'], request.form['email'], request.form['role'])
            session['username'] = request.form['username']
	    session['role'] = request.form['role']
            session['user_container_name'] = session['username']
            session['user_data_container_name'] = session['username'] + "_data"
            session['common_data_container_name'] = "knowrob_data"
            
            session['logged_in'] = True
            session['rosauth_mac'] = generate_mac()
            #create_data_containers()
            #start_container()
            
            session['show_loading_overlay'] = True
            return redirect(url_for('show_user_data'))

    return render_template('login.html', error=error, action="register")



@app.route('/tutorials/')
@app.route('/tutorials/<cat_id>/')
@app.route('/tutorials/<cat_id>/<page>')
@login_required
def tutorials(cat_id='getting_started', page=1):
  
    #if not session.get('logged_in'):
    #    return redirect(url_for('login'))

    # determine hostname/IP we are currently using
    # (needed for accessing container)
    host_url = urlparse(request.host_url).hostname

    tut = read_tutorial_page(cat_id, page)
    content = markdown(tut['text'], fenced_code=True)

    # automatically add "ask as query" links after code blocks
    content = re.sub('</code>(\s)?</pre>', "</code></pre><div class='show_code'><a href='#' class='show_code'>Ask as query</a></div>", str(content))
    content = Markup(content)

    # check whether there is another tutorial in this category
    nxt  = read_tutorial_page(cat_id, int(page)+1)
    prev = read_tutorial_page(cat_id, int(page)-1)

    return render_template('knowrob_tutorial.html', **locals())

@app.route('/knowrob')
@app.route('/exp/<exp_id>')
@roles_required('secret')
def knowrob(exp_id=None):
    #if not current_user.is_authenticated():
    #    return redirect(url_for('user.login'))
    error=""

    # determine hostname/IP we are currently using
    # (needed for accessing container)
    host_url = urlparse(request.host_url).hostname

    if exp_id is not None and os.path.isfile('static/queries-' + exp_id + '.json'):
        exp_query_file='queries-' + exp_id + '.json'
    
    return render_template('knowrob_simple.html', **locals())

    

@app.route('/editor')
@app.route('/editor/<filename>/')
@roles_required('admin')
def editor(filename=""):
    #if not current_user.is_authenticated():
       # return redirect(url_for('user.login'))
        
    error=""
    sandbox = '/home/tenorth/sandbox/'
    glob = sandbox + filename

    # check if still in sandbox
    if not str(os.path.abspath(glob)).startswith(sandbox):
        error = "Access denied to folders outside of sandbox"
        filename = ""

    files = os.listdir(glob)


    #poem = open("ad_lesbiam.txt").read()
    return render_template('editor.html', error=error, files=files)



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# DB stuff

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context. """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def user_exists(username):

    # username blacklist
    if username=="knowrob":
      return True
    elif username=="mongo":
      return True
    elif username=="tenorth":
      return True
      
  
    db = get_db()
    cur = db.execute('select username from users where username=?', [username])
    entries = cur.fetchall()

    if len(entries)>0:
        return True
    else:
        return False

"""
def role_exists(role_name):
    db = get_db()
    cur = db.execute('select name from roles where name = ?' [role_name])
    entries = cur.fetchall()

    return len(entries)>0
"""

def is_valid_user(username, password):
    db = get_db()
    pwd_hash = hashlib.sha256(password).hexdigest()
    cur = db.execute('select username from users where username=? and passwd=?', [username, pwd_hash])
    entries = cur.fetchall()

    if len(entries)>0:
        return True
    else:
        return False


def insert_user(username, password, email, role):
    db = get_db()
    pwd_hash = hashlib.sha256(password).hexdigest()
    cur = db.execute('insert into users (username, passwd, email, container_id) values (?,?,?,"")', [username, pwd_hash, email])
    db.commit()
    #insert_role(role)
    #insert_user_role(username,role)
    flash('New user was successfully created')
    return redirect(url_for('show_user_data'))

"""
def insert_role(role_name):
    db = get_db()
    cur = db.execute('insert into roles (name) values (?)', [role_name])
    db.commit()


def insert_user_role(username,role_name):
    db = get_db()
    cur = db.execute('select id from users where username = ?', [username])

    userid = cur.fetchone()

    cur = db.execute('select id from roles where name = ?', [role_name])

    roleid = cur.fetchone()

    cur = db.execute('insert into user_roles (user_id,role_id) values (?,?)', [userid['id'],roleid['id']])
    db.commit()

def get_role(username):
    db = get_db()
    cur = db.execute('select id from users where username = ?', [username])

    userid = cur.fetchone()
    cur = db.execute('select name from roles where id in (select role_id from user_roles where user_id = ?)', [userid['id']])
    roledata = cur.fetchone()
    return roledata['name']
"""

def get_user_data(username):
    db = get_db()
    cur = db.execute('select * from users where username=?', [username])
    data = cur.fetchone()

    if data is not None:
        session['pwd_has'] = data['passwd']
        session['email'] = data['email']
        session['user_container_id'] = data['container_id']
	
	#cur = db.execute('select id from users where username = ?', [username])
	#userid = cur.fetchone()
	#cur = db.execute('select name from roles where id in (select role_id from user_roles where user_id = ?)', [userid['id']])
	#roledata = cur.fetchone()
	#if len(roledata)>0:
	#    session['role'] = roledata['name']
	#    return data
	#else:
	#    return False

        return data

    else:
        return False


def read_tutorial_page(cat, page):
    db = get_db()
    cur = db.execute('select * from tutorial where cat_id=? and page=?', [cat, page])
    tut = cur.fetchone()
    return tut


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def generate_mac():

    secret = "RW6WZ2yp67ETMdj2"
    client = request.remote_addr
    dest   = request.host_url # TODO: find out the actual IP; this will return the hostname

    rand = "".join([random.choice(string.ascii_letters + string.digits) for n in xrange(30)])

    t = int(time.time())
    level = "user"
    end = int(t + 3600)

    mac = hashlib.sha512(secret + client + dest + rand + str(t) + level + str(end) ).hexdigest()

    return "ros.authenticate(" + mac + ", " + client + ", " + dest + ", " + rand + ", " + str(t) + ", " + level + ", " + str(end) + ")"
    
#init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0')
