import os, datetime, getpass
from chat_forms import LoginForm, MessageForm
from flask import Flask, render_template, url_for, redirect, request, flash, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, current_user, LoginManager, login_required, login_user, \
AnonymousUserMixin, fresh_login_required
from flask_bootstrap import Bootstrap

app = Flask(__name__)

app.config[ 'SECRET_KEY' ] = 'jsbcfsbfjefebw237u3gdbdc' # encrypts messages

#################################
### SQL DATABASE SECTION ###########
###################################

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['POSTS_PER_PAGE'] = 30

db = SQLAlchemy(app)
Migrate(app,db)
login = LoginManager()
login.init_app(app)
bootstrap = Bootstrap(app)


##########################
### MODELS#################
#####################

class User(UserMixin, db.Model, AnonymousUserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, index=True, unique=True, default="Guest")
    last_seen = db.Column(db.DateTime, default = datetime.datetime.now())
    posts = db.relationship('Post', backref='author', lazy='dynamic')

    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime, default = datetime.datetime.now())

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    def __init__(self,username):
        self.username = username

    # def to_dict(self):
    #     data = {
    #         'id': self.id,
    #         'username': self.username,
    #         'last_seen': self.last_seen.isoformat() + 'Z',
    #     }
    #     return data
    #
    # def from_dict(self, data):
    #     for field in ['username']:
    #         if field in data:
    #             setattr(self, field, data[field])

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# @login.unauthorized_handler
# def unauthorized():
#

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.now())

    def __repr__(self):
        return '<Message {}>'.format(self.body)


class Post(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return 'Post {}>'.format(self.body)

############################
####### ROUTES ############
###########################

@app.route( '/' ) # home page
def index():
  return render_template( './chat_site_home.html' ) #using html file for this page

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if current_user.is_authenticated:
            current_user.last_seen = datetime.datetime.now()

        # "should not use login_user if user is None. And when you're creating
        # a user, this newly created user is never assigned to the user variable"
        # login_user(user,remember=form.username.data)


        if user is None:
            user = User(username=form.username.data)
            # , user.last_seen = datetime.datetime
            # flash('Invalid username')
            # return redirect(url_for('login'))
        db.session.add(user)
        db.session.commit()

        login_user(user, force=True, fresh=True)
        flash('logged in successfully')

        return redirect(url_for('chat'))
    return render_template('cs_login.html', title='Sign In', form=form)

@app.route('/signup')
def signup():
    pass

@app.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        # flash('Your message has been sent.')
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=('Send Message'),
                           form=form, recipient=recipient)


@app.route('/messages', methods=['GET', 'POST'])
@login_required  # without login ?
def chat():

    current_user.last_message_read_time = datetime.datetime.now()
    db.session.commit()

    form = MessageForm()
    message = 'form not working'
    if form.validate_on_submit():
        user = current_user
        message = Message(author=current_user,
                      recipient=form.recipient.data,
                      msg=form.body.data)
        db.session.add(message.format)
        db.session(commit)

    print(message)

    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None

    return render_template('messages.html', messages=messages.items, form=form,
                           next_url=next_url, prev_url=prev_url)


if __name__ == '__main__':
  app.run(debug = True) #opens debug traceback
  # and with debug pin from console, gives a debugging console
