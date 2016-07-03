from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from flask_login import login_user, logout_user, current_user, login_required, LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from datetime import datetime
import calendar as cal

# Config
DATABASE_PATH = 'sqlite:///templeotrunks.db'
DEBUG = True
SECRET_KEY = 'development key'
NORMAL_USER = 0
SUPER_USER = 1
POST_DATE_FORMAT = '%A, %m/%d%/%Y'

# Create the application
app = Flask(__name__)
app.config.from_object(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'loging'

def connect_db():
    """
    Connects to the website's database
    :return:
    """
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_PATH
    return app.config['SQLALCHEMY_DATABASE_URI']

# Initialize the web database
connect_db()
db = SQLAlchemy(app)


# Database relationships
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120), unique=False)
    email = db.Column(db.String(120), unique=True)
    role = db.Column(db.Integer, unique=False)

    def __init__(self, username, password, email, role=None):
        self.username = username
        self.password = password
        self.email = email

        if role is None:
            role = NORMAL_USER

        self.role = role

    def __repr__(self):
        return "<User '{}'>".format(self.username)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def get_id(self):
        return self.id

    def is_anonymous(self):
        return False


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    body = db.Column(db.Text)
    pub_date = db.Column(db.DateTime)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref=db.backref('posts', lazy='dynamic'))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref=db.backref('posts', lazy='dynamic'))

    def __init__(self, title, body, category, user, pub_date=None):
        self.title = title
        self.body = body
        if pub_date is None:
            pub_date = datetime.utcnow()

        self.pub_date = pub_date
        self.category = category
        self.user = user

    def __repr__(self):
        return "<Post '{}'>".format(self.title)

    def post_date(self):
        return self.pub_date.strftime(POST_DATE_FORMAT)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Category '{}'>".format(self.name)


# Default Users
DEFAULT_USER_1 = User('admin', 'password', 'admin@example.com', SUPER_USER)
DEFAULT_USER_2 = User('user', 'security', 'user@example')


# Webpage functions
@login_manager.user_loader
def load_user(id):
    """
    Loads a user with the given ID
    :param id: ID of user to be loaded
    :return:
    """
    return User.query.get(int(id))

@app.before_request
def before_request():
    """
    Before each request is made, sets references to the user making the request
    """
    g.user = current_user

@app.route('/')
def show_posts():
    """
    Default page; Displays all posts
    :return: main page
    """
    user_level = NORMAL_USER

    posts = Post.query.order_by(Post.pub_date)

    if g.user.is_authenticated and g.user.role == SUPER_USER:
        user_level = SUPER_USER

    return render_template('show_posts.html', posts=posts, admin=(user_level == SUPER_USER))


@app.route('/add', methods=['POST'])
def add_post():
    """
    Adds a post, if the user has that privlege
    :return: main page
    """
    if not session.get('logged_in'):
        abort(401)

    elif g.user.role != SUPER_USER:
        flash('You are not authorized to add a post')

    else:
        post = Post(request.form['title'], request.form['text'], Category('Uncategorized'), g.user)
        db.session.add(post)
        db.session.commit()
        flash('New post was successfully posted')

    return redirect(url_for('show_posts'))

@app.route('/main')
def tot_homepage():
    """
    Returns the
    :return: main page
    """
    user_level = NORMAL_USER

    posts = Post.query.order_by(desc(Post.pub_date))

    if g.user.is_authenticated and g.user.role == SUPER_USER:
        user_level = SUPER_USER

    return render_template('tot_main_page_flask.html', posts=posts, admin=(user_level == SUPER_USER),
                           date_format=POST_DATE_FORMAT)

@app.route('/past')
def past_updates():
    """
    Returns the past updates page
    :return: past updates page
    """

    posts = Post.query.order_by(desc(Post.pub_date))

    return render_template('tot_past_updates_flask.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_page(post_id):
    """
    Displays the post with the given ID
    :param post_id: ID of displayed post
    :return:
    """

    if Post.query.filter_by(id=post_id).count() == 0:
        flash('Post not found.')
        return redirect(url_for('show_posts'))

    post = Post.query.get(post_id)

    return render_template('post_page.html', post=post)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Logs in an approved user
    :return:
    """
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).count() == 0:
            error = 'Invalid username'
        elif password != User.query.filter_by(username=username).first().password:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            login_user(User.query.filter_by(username=username).first())
            flash('You were successfully logged in')
            return redirect(url_for('show_posts'))

    return render_template('login.html',error=error)

@app.route('/logout')
def logout():
    """
    Logs out a logged in user
    :return:
    """
    session.pop('logged_in', None)
    logout_user()
    flash('You have been logged out')

    return redirect(url_for('show_posts'))


# Custom filters
@app.template_filter('posting_date')
def format_post_date(date):
    date_string = cal.day_name[date.weekday()] + ', ' + str(date.month) + '/' + str(date.day) + '/' + str(date.year)

    return date_string

if __name__ == '__main__':
    # Set up the database
    db.create_all()

    # Make sure initial users are in the database
    if User.query.count() == 0:
        db.session.add(DEFAULT_USER_1)
        db.session.add(DEFAULT_USER_2)

    # Commit to the database and launch
    db.session.commit()
    app.run(debug=True)