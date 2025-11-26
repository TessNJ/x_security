from flask import Flask, request, make_response, render_template, session, redirect, url_for
import mysql.connector
import re
import dictionary
import json
import os
from dotenv import load_dotenv

load_dotenv()

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from functools import wraps

app = Flask(__name__)


from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

python_domain = True if "PYTHONANYWHERE_DOMAIN" in os.environ else False

# UPLOAD_ITEM_FOLDER = './images'
app.config['GMAIL_EMAIL'] = os.getenv('GMAIL_EMAIL')
app.config['GMAIL_KEY'] = os.getenv('GMAIL_KEY')
app.config['DB_HOST'] = os.getenv('DB_HOST')
app.config['DB_USER'] = os.getenv('DB_USER')
app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['DB_DBNAME'] = os.getenv('DB_DBNAME')

allowed_languages = ["english", "danish", "spanish"]
# google_spread_sheet_key = "17zrH7Akox0wKq4PeYWDqA1vyCq7zLBMvrT78YYhEnbQ"
default_language = "english"

def lans(key):

    path = "/home/TereseNJ/mysite/dictionary.json" if python_domain else "dictionary.json"

    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    return data[key][default_language]

##############################
def db():
    try:
        # host = "fullweb.mysql.eu.pythonanywhere-services.com" if python_domain else "mariadb"
        # user = "TereseNJ" if python_domain else "root"
        # password = "MyPasswordForYou" if python_domain else "password"
        # database = "TereseNJ$twitter" if python_domain else "x"

        db = mysql.connector.connect(
            host = app.config['DB_HOST'],
            user = app.config['DB_USER'],
            password = app.config['DB_PASSWORD'],
            database = app.config['DB_DBNAME']
        )
        cursor = db.cursor(dictionary=True)
        return db, cursor
    except Exception as e:
        print(e, flush=True)
        raise Exception(lans('twitter_maintenance'), 500)

##############################
def no_cache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache_view

##############################
REGEX_EMAIL = "^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$"
def validate_user_email():
    user_email = request.form.get("user_email", "").strip()
    if not re.match(REGEX_EMAIL, user_email): raise Exception(lans('invalid_email'), 400)
    return user_email

##############################
USER_USERNAME_MIN = 2
USER_USERNAME_MAX = 20
REGEX_USER_USERNAME = f"^.{{{USER_USERNAME_MIN},{USER_USERNAME_MAX}}}$"
def validate_user_username(lan="english"):
    user_username = request.form.get("user_username", "").strip()
    error = f"{lans('username')}: {USER_USERNAME_MIN} {lans('to')} {USER_USERNAME_MAX} {lans('characters')}"
    if len(user_username) < USER_USERNAME_MIN: raise Exception(error, 400)
    if len(user_username) > USER_USERNAME_MAX: raise Exception(error, 400)
    return user_username

##############################
USER_FIRST_NAME_MIN = 2
USER_FIRST_NAME_MAX = 20
REGEX_USER_FIRST_NAME = f"^.{{{USER_FIRST_NAME_MIN},{USER_FIRST_NAME_MAX}}}$"
def validate_user_first_name(lan="english"):
    user_first_name = request.form.get("user_first_name", "").strip()
    error = f"{lans('first_name')}: {USER_FIRST_NAME_MIN} {lans('to')} {USER_FIRST_NAME_MAX} {lans('characters')}"
    if not re.match(REGEX_USER_FIRST_NAME, user_first_name): raise Exception(error, 400)
    return user_first_name


##############################
USER_PASSWORD_MIN = 6
USER_PASSWORD_MAX = 50
REGEX_USER_PASSWORD = f"^.{{{USER_PASSWORD_MIN},{USER_PASSWORD_MAX}}}$"
def validate_user_password(lan = "english"):
    user_password = request.form.get("user_password", "").strip()
    if not re.match(REGEX_USER_PASSWORD, user_password): raise Exception(lans('invalid_password'), 400)
    return user_password

##############################
def validate_user_password_confirm(lan):
    user_password = request.form.get("user_password_confirm", "").strip()
    if not re.match(REGEX_USER_PASSWORD, user_password): raise Exception(lans('twitter_password'), 400)
    return user_password

##############################
REGEX_UUID4 = "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
def validate_uuid4(uuid4 = "", lan="english"):
    if not uuid4:
        uuid4 = request.values.get("uuid4", "").strip()
    if not re.match(REGEX_UUID4, uuid4): raise Exception(lans('twitter_uuid4_dashes'), 400)
    return uuid4

##############################
REGEX_UUID4_WITHOUT_DASHES = "^[0-9a-f]{8}[0-9a-f]{4}4[0-9a-f]{3}[89ab][0-9a-f]{3}[0-9a-f]{12}$"
def validate_uuid4_without_dashes(uuid4 = "", lan="english"):
    error = lans('twitter_uuid4')
    if not uuid4: raise Exception(error, 400)
    uuid4 = uuid4.strip()
    if not re.match(REGEX_UUID4_WITHOUT_DASHES, uuid4): raise Exception(error, 400)
    return uuid4

##############################
POST_MIN_LEN = 2
POST_MAX_LEN = 250
REGEX_POST = f"^.{{{POST_MIN_LEN},{POST_MAX_LEN}}}$"
def validate_post(post = ""):
    error = f"""post must be {POST_MIN_LEN} to {POST_MAX_LEN} characters"""
    post = post.strip()
    if not re.match(REGEX_POST, post): raise Exception(error, 400)
    return post

##############################
def send_email(to_email, subject, template):
    try:
        # Create a gmail fullflaskdemomail
        # Enable (turn on) 2 step verification/factor in the google account manager
        # Visit: https://myaccount.google.com/apppasswords

        # Email and password of the sender's Gmail account
        sender_email = app.config['GMAIL_EMAIL']
        password = app.config['GMAIL_KEY']

        # Receiver email address
        receiver_email = sender_email

        # Create the email message
        message = MIMEMultipart()
        message["From"] = "X clone"
        message["To"] = to_email
        message["Subject"] = subject

        # Body of the email
        message.attach(MIMEText(template, "html"))

        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        ic("Email sent successfully!")

        return "email sent"

    except Exception as ex:
        ic(ex)
        raise Exception("cannot send email", 500)
    finally:
        pass

##############################
def validate_user_logged():
    if session.get("user", "") : return True
    return False

##############################
def redirect_index_mixhtlm():
    return f"""<browser mix-redirect="/"></browser>"""

##############################
def redirect_index_flask():
    return redirect(url_for("login"))
