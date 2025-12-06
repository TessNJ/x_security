from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import x
import time
import uuid
import os
import requests
import io
import csv
import json
from dotenv import load_dotenv

load_dotenv()

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)

# Set the maximum file size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024   # 1 MB

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

post_upload_folder = "./static/images"
app.config['POST_UPLOAD_FOLDER'] = post_upload_folder

upload_folder = "/home/TereseNJ/mysite/static/uploads" if x.python_domain else "./static/uploads"
app.config['UPLOAD_FOLDER'] = upload_folder
app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD')
app.config['GOOGLE_SPREADSHEET_KEY'] = os.getenv('GOOGLE_SPREADSHEET_KEY')
app.config['LINK_BASE'] = os.getenv('LINK_BASE')


##############################
##############################
##############################
def _____USER_____(): pass
##############################
##############################
##############################

@app.get("/")
def view_index():
    return render_template("index.html")

##############################
@app.context_processor
def global_variables():
    return dict (
        x = x
    )

##############################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lan>", methods=["GET", "POST"])
@x.no_cache
def login(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan
    
    if session.get("user", ""): return redirect(url_for("home"))

    if request.method == "GET":
        message = session.get("message", "")
        session["message"] = ""

        return render_template("login.html", lan=x.default_language, message=message)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()

            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            if not user: raise Exception(x.lans('user_not_found').capitalize(), 400)

            if not check_password_hash(user["user_password"], user_password):
                raise Exception(x.lans('invalid_credentials').capitalize(), 400)

            if user["user_verification_key"] != "":
                raise Exception(x.lans('user_not_verified').capitalize(), 400)
            
            if user["user_deleted_at"] != 0 :
                raise Exception(x.lans('user_deactivated').capitalize(), 400)

            user.pop("user_password")
            user["user_language"] = x.default_language

            session["user"] = user
            return f"""<browser mix-redirect="/home"></browser>"""

        except Exception as ex:
            ic(ex)

            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-update="#toast">{ toast_error }</browser>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

##############################
@app.get("/logout")
@x.no_cache
def logout():
    try:
        session.clear()
        return redirect(url_for("login"))
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        # System or developer error
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

##############################
@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup/<lan>", methods=["GET", "POST"])
@x.no_cache
def signup(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        return render_template("signup.html", x=x, lan=x.default_language)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            user_username = x.validate_user_username()
            user_first_name = x.validate_user_first_name()
            x.validate_user_password_confirm(user_password)

            # if not user_password_confirm : Exception(x.lans('user_not_found').capitalize(), 400)
            # if not user_password_confirm : Exception("password doesnt match", 400)

            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = "default.jpg"
            user_password_reset = ""
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0
            user_updated_at = 0
            user_deleted_at = 0
            user_is_blocked = 0
            user_total_followers = 0

            user_hashed_password = generate_password_hash(user_password)


            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, user_username,
            user_first_name, user_last_name, user_avatar_path, user_total_followers, user_password_reset, user_verification_key, user_verified_at, user_updated_at, user_deleted_at, user_is_blocked))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key, lan=x.default_language, link=app.config['LINK_BASE'])
            x.send_email(user_email, x.lans("verify_your_account").capitalize(), email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

            # Database errors
            if "Duplicate entry" and user_email in str(ex):
                toast_error = render_template("___toast_error.html", message=x.lans('email_registered').capitalize())
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            if "Duplicate entry" and user_username in str(ex):
                toast_error = render_template("___toast_error.html", message=x.lans('username_registered').capitalize())
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

##############################
@app.route("/verify-account", methods=["GET"])
@x.no_cache
def verify_account():
    try:
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception(x.lans('invalid_key').capitalize(), 400)
        return redirect( url_for('login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        
        if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        # System or developer error
        toast_error = render_template("___toast_error.html", message=x.lans('cannot_verify"').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


#####################
@app.route("/request_password", methods=["GET","POST"])
@app.route("/request_password/<lan>", methods=["GET", "POST"])
@x.no_cache
def request_password(lan="english"):
    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        return render_template("request_password.html", lan=x.default_language, x=x)

    if request.method == "POST":
        try:
            user_email = x.validate_user_email()

            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()

            if not user: raise Exception(x.lans('user_not_found').capitalize(), 400)

            if user["user_verification_key"] != "":
                raise Exception(x.lans('user_not_verified').capitalize(), 400)
            
            if user["user_deleted_at"] != 0 :
                raise Exception(x.lans('user_deactivated').capitalize(), 400)
            
            user_password_reset = uuid.uuid4().hex

            q = "UPDATE users SET user_password_reset = %s WHERE user_email = %s"
            cursor.execute(q, (user_password_reset, user_email))
            db.commit()
            
            email_forgot_password = render_template("_email_forgot_password.html", user_password_reset=user_password_reset, lan=x.default_language, link=app.config['LINK_BASE'])
            
            x.send_email(user_email, x.lans('set_new_password').capitalize(), email_forgot_password)

            toast_ok = render_template("___toast_ok.html", message=x.lans('password_reset_sent').capitalize())

            return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            """
            
        except Exception as ex:
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
        


#####################
@app.route("/change_password", methods=["GET", "POST"])
@x.no_cache
def change_password(lan = "english"):

    lan = request.args.get("lan", "")
    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        try:
            if len(request.args.get("key", "")) != 32: raise Exception(x.lans('link_is_invalid').capitalize(), 400)
            user_password_reset = x.validate_uuid4_without_dashes(request.args.get("key", ""))
            
            db, cursor = x.db()
            q = "SELECT * FROM users WHERE user_password_reset = %s"
            cursor.execute(q, (user_password_reset,))
            user = cursor.fetchone()

            if not user: raise Exception(x.lans('link_is_invalid').capitalize(), 400)

            return render_template("change_password.html", lan=x.default_language, x=x, user_password_reset=user_password_reset)
        except Exception as ex:
            ic(ex)
            if "db" in locals(): db.rollback()
            # User errors

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

    if request.method == "POST":
        try:
            user_password_reset = x.validate_uuid4_without_dashes(request.args.get("key", ""))

            user_new_password = x.validate_user_password()
            x.validate_user_password_confirm(user_new_password)
            
            user_hashed_password = generate_password_hash(user_new_password)

            db, cursor = x.db()
            q = "UPDATE users SET user_password_reset = '', user_password = %s WHERE user_password_reset = %s"
            cursor.execute(q, (user_hashed_password, user_password_reset))
            db.commit()
            if cursor.rowcount != 1: raise Exception(x.lans('link_is_invalid').capitalize(), 400)

            session["message"] = x.lans('updated_password').capitalize()

            return f"""
            <browser mix-redirect="/login"></browser>
            """

        except Exception as ex:
            ic(ex)
            if "db" in locals(): db.rollback()
            # User errors

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally: 
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

##############################
@app.get("/home")
@x.no_cache
# @x.logged
def home(lan="english"):
    if not x.validate_user_logged() : return x.redirect_index_flask()
    try:
        user = session.get("user", "")
        lan = session["user"]["user_language"]

        next_page = 2

        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0 AND user_deleted_at = 0 AND post_is_blocked = 0 AND user_is_blocked = 0 ORDER BY post_created_at DESC LIMIT 0, 5"
        cursor.execute(q)
        tweets = cursor.fetchall()
        
        for tweet in tweets:
            q="SELECT EXISTS(SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s) AS liked"
            cursor.execute(q, (user["user_pk"], tweet["post_pk"]))
            tweet["liked"] = bool(cursor.fetchone()["liked"])

        ic(tweets)
        
        q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()

        user_follower = session.get("user", "")

        q = "SELECT * FROM users WHERE user_pk != %s AND user_is_blocked = 0 AND user_deleted_at = 0 AND users.user_pk NOT IN ( SELECT follows.followed_fk FROM follows WHERE follows.follower_fk = %s ) ORDER BY RAND() LIMIT 3"
        cursor.execute(q, (user_follower["user_pk"], user_follower["user_pk"],))
        suggestions = cursor.fetchall()

        profileInfo = {"name":user["user_first_name"], "handle":user["user_username"], "path":user["user_avatar_path"]}

        lan = session["user"]["user_language"]

        return render_template("home.html", tweets=tweets, trends=trends, suggestions=suggestions, user=user, lan=lan, x=x, profileInfo=profileInfo, next_page=next_page)
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/home-comp")
@x.no_cache
def home_comp():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        user = session.get("user", "")
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0 AND user_deleted_at = 0 AND post_is_blocked = 0 AND user_is_blocked = 0 ORDER BY post_created_at DESC LIMIT 0, 5"
        cursor.execute(q)
        tweets = cursor.fetchall()
        # ic(tweets)
        
        for tweet in tweets:
            q="SELECT EXISTS(SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s) AS liked"
            cursor.execute(q, (user["user_pk"], tweet["post_pk"]))
            tweet["liked"] = bool(cursor.fetchone()["liked"])
        # ic(tweets)

        html = render_template("_home_comp.html", tweets=tweets)
        return f"""
            <mixhtml mix-update="main">{ html }</mixhtml>
            <browser mix-remove="#search_results"></browser>"""
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/profile")
@x.no_cache
def profile():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        user = session.get("user", "")

        q = "SELECT * FROM users WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()

        lan = session["user"]["user_language"]
        profile_html = render_template("_profile.html", x=x, user=user, lan=lan)
        return f"""
            <browser mix-update="main">{ profile_html }</browser>
            <browser mix-remove="#search_results"></browser>
            """
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/api-update-profile", methods=["POST"])
@x.no_cache
def api_update_profile():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:

        user = session.get("user", "")

        ######### img
        uploaded_file = request.files.get('user_avatar_path', "default.jpg")
        _, ext = os.path.splitext(uploaded_file.filename)
        new_name = uuid.uuid4().hex + ext
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_name)
        uploaded_file.save(file_path)

        user_updated_at = int(time.time())

        # Validate
        user_email = x.validate_user_email()
        user_username = x.validate_user_username()
        user_first_name = x.validate_user_first_name()

        # Connect to the database
        q = "UPDATE users SET user_email = %s, user_username = %s, user_first_name = %s, user_avatar_path = %s, user_updated_at = %s WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user_email, user_username, user_first_name, new_name, user_updated_at, user["user_pk"]))
        db.commit()

        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        user_db = cursor.fetchone()
        user_db.pop("user_password")

        user_db["user_language"] = x.default_language
        session["user"] = user_db

        # Response to the browser
        toast_ok = render_template("___toast_ok.html", message=x.lans('update_successful').capitalize())
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-update="#profile_tag .name">{user_first_name}</browser>
            <browser mix-update="#profile_tag .handle">{user_username}</browser>
            <browser mix-replace="#profile_tag img">
            <img src="/static/uploads/{new_name}" alt="Profile">
            </browser>
        """, 200
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        # User errors
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        # Database errors
        if "Duplicate entry" and user_email in str(ex):
            toast_error = render_template("___toast_error.html", message=x.lans('email_registered').capitalize())
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        if "Duplicate entry" and user_username in str(ex):
            toast_error = render_template("___toast_error.html", message=x.lans('username_registered').capitalize())
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        # System or developer error
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintanence').capitalize())
        return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


###################
@app.route("/confirm_delete", methods=["GET", "POST"])
@x.no_cache
def confirm_delete():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    if request.method == "GET":
        confirm_delete = render_template("___confirm_delete.html")

        return f"""
        <browser mix-update="#confirmDelete">{confirm_delete}</browser>
        """
    if request.method == "POST" :
        return f"""
        <browser mix-update="#confirmDelete"></browser>
        """


#####################
@app.get("/delete_user")
@x.no_cache
def delete_user() :
    if not x.validate_user_logged() : return x.redirect_index_flask()
    try:
        user_pk = session["user"]["user_pk"]
        user_email = session["user"]["user_email"]
        user_deleted_at = int(time.time())

        # ic(user_pk)
        db, cursor = x.db()
        q = "UPDATE users SET user_deleted_at = %s WHERE user_pk = %s"
        cursor.execute(q, (user_deleted_at, user_pk))
        db.commit()

        email_user_deleted = render_template("_email_user_deleted.html", lan=x.default_language, link=app.config['LINK_BASE'])
        x.send_email(user_email, x.lans('email_account_is_deleted').capitalize(), email_user_deleted)

        q="UPDATE posts SET post_deleted_at = %s WHERE post_user_fk = %s"
        cursor.execute(q, (user_deleted_at, user_pk))
        
        q="UPDATE comments SET comment_deleted_at = %s WHERE comment_user_fk = %s"
        cursor.execute(q, (user_deleted_at, user_pk))

        q="DELETE FROM follows WHERE follower_fk = %s"
        cursor.execute(q, (user_pk,))
        
        q="DELETE FROM likes WHERE liker_user_fk = %s"
        cursor.execute(q, (user_pk,))
        db.commit()
        
        session.clear()
        return redirect(url_for("login"))

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/api-get-tweets")
def api_get_tweets():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        next_page = int(request.args.get("page", ""))

        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0  ORDER BY post_created_at DESC LIMIT %s, 5"
        cursor.execute(q, ((next_page - 1)*5, ))
        tweets = cursor.fetchall()
        
        container = ""

        for tweet in tweets[:4]:
            html_tweet = render_template("_tweet.html", tweet = tweet)
            container = container + html_tweet

        if len(tweets) == 5:
            new_hyperlink = render_template("___show_more.html", next_page=next_page+1)
        else :
            new_hyperlink = " "

        return f"""
        <mixhtml mix-bottom="#posts">
            {container}
        </mixhtml>
        <mixhtml mix-replace="#show_more">
            {new_hyperlink}
        </mixhtml>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/api-create-post", methods=["POST"])
@x.no_cache
def api_create_post():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        user = session.get("user", "")
        user_pk = user["user_pk"]
        post = x.validate_post(request.form.get("post", ""))

        uploaded_file = request.files.get('post_image_attach', "")
        if uploaded_file:
            _, ext = os.path.splitext(uploaded_file.filename)
            post_image_path = uuid.uuid4().hex + ext
            file_path = os.path.join(app.config['POST_UPLOAD_FOLDER'],  post_image_path)
            uploaded_file.save(file_path)
        else:
            post_image_path = ""

        post_pk = uuid.uuid4().hex
        post_created_at = int(time.time())
        post_updated_at = 0
        post_deleted_at = 0
        post_is_blocked = 0
        post_total_likes = 0
        post_total_comments = 0

        db, cursor = x.db()
        q = "INSERT INTO posts VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(q, (post_pk, user_pk, post, post_image_path, post_total_likes, post_total_comments, post_created_at, post_updated_at, post_deleted_at, post_is_blocked))
        db.commit()

        toast_ok = render_template("___toast_ok.html", message=x.lans('the_world_is_reading').capitalize())
        tweet = {
            "user_first_name": user["user_first_name"],
            "user_last_name": user["user_last_name"],
            "user_username": user["user_username"],
            "user_avatar_path": user["user_avatar_path"],
            "post_message": post,
            "post_total_likes": 0,
            "post_total_comments":0,
            "post_liked": False,
            "post_pk": post_pk,
            "post_image_path" : post_image_path,
            "post_created_at" : post_created_at
        }
        html_post_container = render_template("___post_container.html")
        html_post = render_template("_tweet.html", tweet=tweet)
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-top="#posts">{html_post}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        # User errors
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"{x.lans('post_must_be')} - {x.POST_MIN_LEN} {x.lans('to')} {x.POST_MAX_LEN} {x.lans('characters')}")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.route("/api-update-post", methods=["GET","POST"])
@x.no_cache
def api_update_post():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    if request.method == "GET":
        try:
            post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))

            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            if tweet["post_deleted_at"] != 0 : raise Exception(x.lans('post_is_deleted').capitalize(), 400)

            post_edit_container = render_template("___tweet-edit.html", tweet=tweet)
            return f"""
                <browser mix-replace="#post_{tweet['post_pk']}">{post_edit_container}</browser>
            """
        except Exception as ex:
            ic(ex)

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
    if request.method == "POST":
        try:
            post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
            
            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            if tweet["post_deleted_at"] != 0 : raise Exception(x.lans('post_is_deleted').capitalize(), 400)

            imgState = request.form.get("hidden_"+tweet["post_pk"], "")

            ######### img
            image_path = tweet["post_image_path"]
            uploaded_file = request.files.get('post_image_'+tweet["post_pk"], "default.jpg")

            if imgState == "newIMG" :
                _, ext = os.path.splitext(uploaded_file.filename)
                new_name = uuid.uuid4().hex + ext
                file_path = os.path.join(app.config['POST_UPLOAD_FOLDER'], new_name)
                uploaded_file.save(file_path)
                image_path = new_name
            elif imgState == "deleted":
                image_path = ""
            post_updated_at = int(time.time())

            ##### message
            post_message = x.validate_post(request.form.get("post", ""))
            if not post_message : raise Exception(x.lans('post_couldnt_update').capitalize(), 400)

            q = "UPDATE posts SET post_message = %s, post_image_path = %s, post_updated_at = %s WHERE post_pk = %s"
            cursor.execute(q, (post_message, image_path, post_updated_at, tweet["post_pk"] ))
            db.commit()
            if cursor.rowcount != 1: raise Exception(x.lans('post_couldnt_update').capitalize(), 400)

            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            
            post_edit_container = render_template("___tweet-display.html", tweet=tweet)
            return f"""
                <browser mix-replace="#post_{tweet['post_pk']}">{post_edit_container}</browser>
            """
        except Exception as ex:
            ic(ex)
            if "db" in locals(): db.rollback()

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
        
@app.route("/api-cancel-post", methods=["GET"])
@x.no_cache
def api_cancel_post():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))

        db, cursor = x.db()
        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        tweet = cursor.fetchone()

        if tweet["post_deleted_at"] != 0 : raise Exception(x.lans('post_already_deleted').capitalize(), 400)

        post_edit_container = render_template("___tweet-display.html", tweet=tweet)
        return f"""
            <browser mix-replace="#post_{tweet['post_pk']}">{post_edit_container}</browser>
            <browser mix-update="#delete_post_confirm"></browser>
        """
    except Exception as ex:
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#################3
@app.route("/api-cancel-confirm", methods=["GET"])
@x.no_cache
def api_cancel_confirm():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        return f"""
            <browser mix-update="#delete_post_confirm"></browser>
        """
    except Exception as ex:
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500


@app.route("/api-delete-post", methods=["GET","POST"])
@x.no_cache
def api_delete_post():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    if request.method == "GET":
        try:
            post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))

            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            confirm_delete = render_template("___confirm_delete_post.html", tweet=tweet)
            ic(confirm_delete)

            return f"""
            <browser mix-update="#delete_post_confirm">{confirm_delete}</browser>
            """
        except Exception as ex:
            ic(ex)

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
    if request.method == "POST":
        try:
            post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
            user = session.get("user", "")
            
            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            if tweet["post_deleted_at"] != 0 : raise Exception(x.lans('post_is_deleted').capitalize(), 400)

            post_deleted_at = int(time.time())

            q = "UPDATE posts SET post_deleted_at = %s WHERE post_pk = %s"
            cursor.execute(q, (post_deleted_at, tweet["post_pk"] ))
            db.commit()
            if cursor.rowcount != 1: raise Exception(x.lans('post_couldnt_update').capitalize(), 400)


            q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0 AND user_deleted_at = 0 AND post_is_blocked = 0 AND user_is_blocked = 0 ORDER BY post_created_at DESC LIMIT 0, 5"
            cursor.execute(q)
            tweets = cursor.fetchall()
            
            for tweet in tweets:
                q="SELECT EXISTS(SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s) AS liked"
                cursor.execute(q, (user["user_pk"], tweet["post_pk"]))
                tweet["liked"] = bool(cursor.fetchone()["liked"])

            html = render_template("_home_comp.html", tweets=tweets)
            return f"""<mixhtml mix-update="main">{ html }</mixhtml>"""
                
        except Exception as ex:
            ic(ex)
            if "db" in locals(): db.rollback()

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

###########################
@app.route("/show-comments", methods=["GET"])
@x.no_cache
def show_comments():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))

        db, cursor = x.db()

        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()

        if post["post_deleted_at"] != 0 : raise Exception(x.lans('post_is_deleted').capitalize(), 400)

        q = "SELECT * FROM users JOIN comments ON user_pk = comment_user_fk WHERE comment_deleted_at = 0 AND post_fk = %s ORDER BY comment_created_at DESC LIMIT 0, 5"
        cursor.execute(q, (post_pk,))
        comments = cursor.fetchall()
        ic(comments)

        show_comments = render_template("_comments_container.html", comments=comments, tweet=post)
        change_button = render_template("___hide_comments.html", tweet=post)

        return f"""
        <browser mix-update="#comments_{post_pk}">{show_comments}</browser>
        <browser mix-update="#show_btn_{post_pk}">{change_button}</browser>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

###########################
@app.route("/hide-comments", methods=["GET"])
@x.no_cache
def hide_comments():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        tweet = {
            "post_pk":post_pk
        }

        change_button = render_template("___show_comments.html", tweet=tweet)

        return f"""
        <browser mix-update="#comments_{post_pk}"></browser>
        <browser mix-replace="#show_btn_{post_pk}">{change_button}</browser>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500


#####################
@app.route("/api-add-comments", methods=["POST"])
@x.no_cache
def create_comments():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        
        db, cursor = x.db()
        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()

        if post["post_deleted_at"] != 0 : raise Exception(x.lans('post_is_deleted').capitalize(), 400)

        user = session.get("user", "")
        comment_message = x.validate_comment(request.form.get("comment", ""))

        comment_created_at = int(time.time())
        comment_updated_at = 0
        comment_deleted_at = 0
        comment_pk = uuid.uuid4().hex

        q = "INSERT INTO comments VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(q, (comment_pk, user["user_pk"], comment_message, post_pk, comment_created_at, comment_updated_at, comment_deleted_at))
        db.commit()

        ### update total comments ###
        q="UPDATE posts SET post_total_comments=post_total_comments+1 WHERE post_pk = %s"        
        cursor.execute(q, (post_pk,))
        db.commit()

        comment = {
            "user_first_name": user["user_first_name"],
            "user_last_name": user["user_last_name"],
            "user_username": user["user_username"],
            "user_avatar_path": user["user_avatar_path"],
            "comment_message": comment_message,
            "comment_pk": comment_pk,
            "post_fk": post_pk,
            "comment_user_fk": user["user_pk"],
            "comment_created_at" : comment_created_at,
            "comment_updated_at" : comment_updated_at,
            "comment_deleted_at" : comment_deleted_at
        }

        show_comments = render_template("___comment.html", comment=comment, tweet=post)
        comment_container = render_template("___create_comment.html", tweet=post)

        return f"""
        <browser mix-top="#view_comments_{post_pk}">{show_comments}</browser>
        <browser mix-remove="#no_comments_{post_pk}"></browser>
        <browser mix-replace="#comment_container_{post_pk}">{comment_container}</browser>
        <browser mix-update="#comment_amount_{post_pk}">{post["post_total_comments"]+1}</browser>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


###########################
@app.post("/follow")
@x.no_cache
def create_follow():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        user_followed = x.validate_uuid4_without_dashes(request.args.get("user_pk", ""))

        ### select user ###
        user_follower = session.get("user", "")

        if user_followed == user_follower["user_pk"] : raise Exception(x.lans('user_cannot_follow').capitalize(), 400)
        
        
        ### check follow ###
        db, cursor = x.db()
        q = "SELECT * FROM follows WHERE followed_fk = %s AND follower_fk = %s "
        cursor.execute(q, (user_followed, user_follower["user_pk"]))

        following = cursor.fetchone()


        if following != None : raise Exception(x.lans('follow_already_exists').capitalize(), 400)

        ### create follow ###
        follow_created_at = int(time.time())
        q = "INSERT INTO follows VALUES (%s, %s, %s)"
        cursor.execute(q, (user_followed, user_follower["user_pk"], follow_created_at))
        db.commit()

        ### Send data ###
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_followed, ))
        user_followed_data = cursor.fetchone()
        new_input = render_template("___button_unfollow.html", suggestion=user_followed_data)

        return f"""
            <browser mix-replace="#follow{user_followed}">
                {new_input}
            </browser>
        """     
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


###########################3
@app.post("/unfollow")
@x.no_cache
def remove_follow():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        # get variable
        user_followed = x.validate_uuid4_without_dashes(request.args.get("user_pk", ""))
        
        # select user
        user_follower = session.get("user", "")

        if user_followed == user_follower["user_pk"] : raise Exception(x.lans('user_cannot_follow').capitalize(), 400)
        
        # check follow
        db, cursor = x.db()
        q = "SELECT * FROM follows WHERE followed_fk = %s AND follower_fk = %s "
        cursor.execute(q, (user_followed, user_follower["user_pk"]))

        following = cursor.fetchone()
        if following == None : raise Exception(x.lans('follow_not_found').capitalize(), 400)

        # Delete follow
        q = "DELETE FROM follows WHERE followed_fk = %s AND follower_fk = %s"
        cursor.execute(q, (user_followed, user_follower["user_pk"]))
        db.commit()


        suggestion = {}
        suggestion["user_pk"] = user_followed
        
        new_input = render_template("___button_follow.html", suggestion=suggestion)

        return f"""
            <browser mix-replace="#follow{user_followed}">
                {new_input}
            </browser>
        """


    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/following")
@x.no_cache
def following():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        db, cursor = x.db()
        user_follower = session.get("user", "")
        q = "SELECT * FROM users WHERE user_is_blocked = 0 AND user_deleted_at = 0 AND user_pk != %s AND users.user_pk IN ( SELECT follows.followed_fk FROM follows WHERE follows.follower_fk = %s )"
        cursor.execute(q, (user_follower["user_pk"], user_follower["user_pk"],))
        user_all_following = cursor.fetchall()

        following_html = render_template("_following.html", user_all_following=user_all_following)
        return f"""
            <mixhtml mix-update="main">{ following_html }</mixhtml>
            <browser mix-remove="#search_results"></browser>
            """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/api-search")
@x.no_cache
def api_search():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        user = session.get("user", "")
        search_for = request.form.get("search_for", "")

        if not search_for or len(search_for) < 2:
            return """
            <browser mix-remove="#search_results"></browser>
            """
        
        part_of_query = f"%{search_for}%"
        
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_is_blocked = 0 AND user_deleted_at = 0 AND user_username LIKE %s AND user_username != %s"
        cursor.execute(q, (part_of_query, user["user_username"]))
        users = cursor.fetchall()

        # q = "SELECT * FROM follows WHERE follower_fk = %s"
        # cursor.execute(q, (user["user_pk"],))
        # following = cursor.fetchall()


        for search_user in users:
            q="SELECT EXISTS(SELECT * FROM follows WHERE follower_fk = %s AND followed_fk = %s) AS followed"
            cursor.execute(q, (user["user_pk"], search_user["user_pk"]))
            search_user["followed"] = bool(cursor.fetchone()["followed"])

        orange_box = render_template("_orange_box.html", users=users)
        return f"""
            <browser mix-remove="#search_results"></browser>
            <browser mix-bottom="#search_form">{orange_box}</browser>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

###########################3
@app.post("/like")
@x.no_cache
def create_like():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        like_user_fk = session.get("user","")
        post_liked_pk = x.validate_uuid4_without_dashes(request.args.get("post_pk", ""))
    
        ### check post user ###
        db, cursor = x.db()
        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_liked_pk,))
        post = cursor.fetchone()

        if post["post_user_fk"] == like_user_fk["user_pk"] : raise Exception(x.lans('cannot_own_post').capitalize(), 400)

        ### check like ###
        q="SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s"
        cursor.execute(q, (like_user_fk["user_pk"], post["post_pk"]))
        like = cursor.fetchone()

        if like != None : raise Exception(x.lans('post_already_liked').capitalize(), 400)

        ### create like ###
        like_created_at = int(time.time())
        q = "INSERT INTO likes VALUES (%s, %s, %s)"
        cursor.execute(q, (post_liked_pk, like_user_fk["user_pk"], like_created_at))
        db.commit()

        post["liked"] = bool(True)

        # ### Send data ###
        post_total_likes = post["post_total_likes"]+1
        new_input = render_template("___button_unlike_tweet.html", tweet = post)

        return f"""
            <browser mix-replace="#like{post_liked_pk}">
                {new_input}
            </browser>
            <browser mix-replace="#like_amount_{post_liked_pk}">
                <span id="like_amount_{post_liked_pk}" mix-get>
                    {post_total_likes}
                </span>
            </browser>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


###########################3
@app.post("/unlike")
@x.no_cache
def remove_like():
    if not x.validate_user_logged() : return x.redirect_index_mixhtlm()
    try:
        post_liked_pk = x.validate_uuid4_without_dashes(request.args.get("post_pk", ""))
        like_user_fk = session.get("user", "")

        ### check post user ###
        db, cursor = x.db()
        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_liked_pk,))
        post = cursor.fetchone()

        if post["post_user_fk"] == like_user_fk["user_pk"] : raise Exception(x.lans('cannot_own_post').capitalize(), 400)
        
        # check like
        db, cursor = x.db()
        q="SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s"
        cursor.execute(q, (like_user_fk["user_pk"], post_liked_pk))
        like = cursor.fetchone()

        if like == None : raise Exception(x.lans('post_isnt_liked').capitalize(), 400)

        # Delete like
        q = "DELETE FROM likes WHERE liked_post_fk = %s AND liker_user_fk = %s"
        cursor.execute(q, (post_liked_pk, like_user_fk["user_pk"]))

        ### update total likes ###
        post_total_likes = post["post_total_likes"]-1

        db.commit()
        
        ### Send data ###
        post["liked"] = False
    
        new_input = render_template("___button_like_tweet.html", tweet = post)

        return f"""
            <browser mix-replace="#like{post_liked_pk}">
                {new_input}
            </browser>
            <browser mix-replace="#like_amount_{post_liked_pk}">
                <span id="like_amount_{post_liked_pk}" mix-get>
                    {post_total_likes}
                </span>
            </browser>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


###########################
@app.route("/admin", methods=["GET", "POST"])
@app.route("/admin/<lan>", methods=["GET", "POST"])
@x.no_cache
def admin(lan="english") :
    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan
    if request.method == "GET":
        return render_template("admin.html", x=x, lan=lan)

    if request.method == "POST":
        try : 
            email = x.validate_user_email()
            password = x.validate_user_password()

            if  email != app.config['ADMIN_EMAIL'] : raise Exception(x.lans('invalid_email').capitalize(), 400)
            if  password != app.config['ADMIN_PASSWORD'] : raise Exception(x.lans('invalid_credentials').capitalize(), 400)

            admin = {}
            admin["email"] = app.config['ADMIN_EMAIL']
            admin["password"] = app.config['ADMIN_PASSWORD']
            session["admin"] = admin
            return f"""<browser mix-redirect="/control_panel"></browser>"""
        except Exception as ex:
            ic(ex)

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        
##############################
@app.get("/8152a9ee-1f86-4a7a-9cd7-2f45b4087694ecxx523f7c-b27f-49b7-9fc1-24baaba82a5e")
@x.no_cache
def get_data_from_sheet():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        
        url= f"https://docs.google.com/spreadsheets/d/{app.config['GOOGLE_SPREADSHEET_KEY']}/export?format=csv&id={app.config['GOOGLE_SPREADSHEET_KEY']}"
        res=requests.get(url=url)
        
        csv_text = res.content.decode('utf-8')
        csv_file = io.StringIO(csv_text) # Use StringIO to treat the string as a file

        # Initialize an empty list to store the data
        data = {}

        # Read the CSV data
        reader = csv.DictReader(csv_file)
        ic(reader)
        # Convert each row into the desired structure
        for row in reader:
            item = {
                    'english': row['english'],
                    'danish': row['danish'],
                    'spanish': row['spanish']

            }
            # Append the dictionary to the list
            data[row['key']] = (item)

        # Convert the data to JSON
        json_data = json.dumps(data, ensure_ascii=False, indent=4)

        # Save data to the file
        path = "/home/TereseNJ/mysite/dictionary.json" if x.python_domain else "dictionary.json"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_data)

        # return "ok"
        toast_ok = render_template("___toast_ok.html", message=x.lans('dictionary_updated').capitalize())

        return f"""
        <browser mix-bottom="#toast">{toast_ok}</browser>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500


@app.route("/control_panel", methods=["GET"])
@x.no_cache
def control_panel():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        return render_template("control_panel.html")
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

@app.get("/temp")
@x.no_cache
def temp_route():
    admin = {}
    admin["email"] = "a@a.com"
    admin["password"] = "passwordwrong"
    session["admin"] = admin
    return "ok"
            
########################
@app.route("/control_panel/posts", methods=["GET"])
@x.no_cache
def admin_posts():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    if request.method == "GET":
        try:
            
            db, cursor = x.db()
            q="CALL get_posts(%s)"
            cursor.execute(q,(0,))
            all_posts = cursor.fetchall()


            if len(all_posts)== 11 :
                next_page = 1
                all_posts.pop()
            else :
                next_page = 0


            return render_template("control_panel_posts.html", tweets=all_posts, next_page=next_page)
        except Exception as ex:
            ic(ex)

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
 
##############################
@app.get("/api-get-tweets-admin")
def api_get_tweets_admin():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        next_page = int(request.args.get("page", ""))
        ic(next_page)
        db, cursor = x.db()
        
        q="CALL get_posts(%s)"
        cursor.execute(q,(10*next_page,))
        tweets = cursor.fetchall()
        ic(len(tweets))
        container = ""

        for tweet in tweets[:10]:
            html_tweet = render_template("_tweet_admin.html", tweet = tweet)
            container = container + html_tweet

        # ic(container)
        if len(tweets) == 11:
            new_hyperlink = render_template("___show_more_posts_admin.html", next_page=next_page+1)
        else :
            new_hyperlink = " "

        return f"""
        <mixhtml mix-bottom="#posts">
            {container}
        </mixhtml>
        <mixhtml mix-replace="#show_more">
            {new_hyperlink}
        </mixhtml>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#############
@app.route("/confirm_block_post", methods=["POST"])
@x.no_cache
def confirm_block_post():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try: 
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        username = x.validate_check_user_username(request.args.get("username", ""))

        tweet = {}
        tweet["post_pk"] = post_pk
        tweet["user_username"] = username
        confirm_block_post = render_template("___confirm_block_post.html", tweet=tweet)

        return f"""
        <browser mix-update="#block_confirm">{confirm_block_post}</browser>
        """
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    
#############
@app.route("/confirm_unblock_post", methods=["POST"])
@x.no_cache
def confirm_unblock_post():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try: 
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        username = x.validate_check_user_username(request.args.get("username", ""))

        tweet = {}
        tweet["post_pk"] = post_pk
        tweet["user_username"] = username
        confirm_unblock_post = render_template("___confirm_unblock_post.html", tweet=tweet)

        return f"""
        <browser mix-update="#block_confirm">{confirm_unblock_post}</browser>
        """
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

#############
@app.route("/confirm_post_cancel", methods=["GET"])
@x.no_cache
def confirm_post_cancel():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try: 
        return f"""
        <browser mix-update="#block_confirm"></browser>
        """
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500


#########################      
@app.post("/api-block-post")
def block_post():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        tweet = cursor.fetchone()

        if tweet["post_deleted_at"] != 0 : raise Exception(x.lans('post_is_deleted').capitalize(), 400)
        if tweet["post_is_blocked"] != 0 : raise Exception(x.lans('post_already_blocked').capitalize(), 400)

        q="UPDATE posts SET post_is_blocked = 1 WHERE post_pk = %s"
        cursor.execute(q, (post_pk, ))
        db.commit()
        if cursor.rowcount != 1: raise Exception(f"{x.lans('post_couldnt_be').capitalize()} {x.lans('blocked')}", 400)

        new_input = render_template("___button_unblock_post.html", tweet=tweet)
        ic(tweet)

        post_image = tweet["post_image_path"]

        email_post_blocked = render_template("_email_post_blocked.html", tweet=tweet, lan=x.default_language, link=app.config['LINK_BASE'])
        # ic(email_verify_account)
        x.send_email_post(tweet["user_email"], f"{x.lans('a_post_has_been').capitalize()} {x.lans('blocked')}", email_post_blocked, post_image) 
       
        toast_ok = render_template("___toast_ok.html", message=x.lans('email_sent_success').capitalize())

        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#post_block_{post_pk}">
                {new_input}
            </browser>
            <browser mix-update="#block_confirm"></browser>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#########################      
@app.post("/api-unblock-post")
def unblock_post():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        
        post_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        tweet = cursor.fetchone()

        if tweet["post_deleted_at"] != 0 : raise Exception(x.lans('post_is_deleted').capitalize(), 400)
        if tweet["post_is_blocked"] == 0 : raise Exception(f"{x.lans('post_isnt').capitalize()} {x.lans('blocked')}" , 400)

        q="UPDATE posts SET post_is_blocked = 0 WHERE post_pk = %s"
        cursor.execute(q, (post_pk, ))
        db.commit()
        if cursor.rowcount != 1: raise Exception(f"{x.lans('post_couldnt_be').capitalize()} {x.lans('unblocked')}", 400)

        new_input = render_template("___button_block_post.html", tweet=tweet)
        post_image = tweet["post_image_path"]

        email_post_unblocked = render_template("_email_post_unblocked.html", tweet=tweet, lan=x.default_language, link=app.config['LINK_BASE'])
        # ic(email_verify_account)
        x.send_email_post(tweet["user_email"], f"{x.lans('a_post_has_been').capitalize()} {x.lans('unblocked')}", email_post_unblocked, post_image) 
       
        toast_ok = render_template("___toast_ok.html", message=x.lans('email_sent_success').capitalize())

        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#post_block_{post_pk}">
                {new_input}
            </browser>
            <browser mix-update="#block_confirm"></browser>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


########################
@app.route("/control_panel/users", methods=["GET"])
@x.no_cache
def admin_user():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        db, cursor = x.db()
        q="CALL get_users(%s)"
        cursor.execute(q,(0,))
        all_users = cursor.fetchall()

        ic(all_users)
        if len(all_users)== 11 :
            next_page = 1
            all_users.pop()
        else :
            next_page = 0
        ic(next_page)

        return render_template("control_panel_users.html", users=all_users, next_page=next_page)
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/api-get-users-admin")
def api_get_users_admin():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        next_page = int(request.args.get("page", ""))
        ic(next_page)
        db, cursor = x.db()
        
        q="CALL get_users(%s)"
        cursor.execute(q,(10*next_page,))
        users = cursor.fetchall()
        ic(users)
        container = ""

        for user in users[:10]:
            html_user = render_template("_user_admin.html", user=user)
            container = container + html_user

        # ic(container)
        if len(users) == 11:
            new_hyperlink = render_template("___show_more_users_admin.html", next_page=next_page+1)
        else :
            new_hyperlink = " "

        return f"""
        <mixhtml mix-bottom="#users">
            {container}
        </mixhtml>
        <mixhtml mix-replace="#show_more">
            {new_hyperlink}
        </mixhtml>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


#############
@app.route("/confirm_block_user", methods=["POST"])
@x.no_cache
def confirm_block_user():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try: 
        user_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        username = x.validate_check_user_username(request.args.get("username", ""))

        user = {}
        user["user_pk"] = user_pk
        user["user_username"] = username
        confirm_block_user = render_template("___confirm_block_user.html", user=user)

        return f"""
        <browser mix-update="#block_confirm">{confirm_block_user}</browser>
        """
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    
#############
@app.route("/confirm_unblock_user", methods=["POST"])
@x.no_cache
def confirm_unblock_user():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try: 
        user_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        username = x.validate_check_user_username(request.args.get("username", ""))

        user = {}
        user["user_pk"] = user_pk
        user["user_username"] = username

        confirm_unblock_user = render_template("___confirm_unblock_user.html", user=user)

        return f"""
        <browser mix-update="#block_confirm">{confirm_unblock_user}</browser>
        """
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

#############
@app.route("/confirm_user_cancel", methods=["GET"])
@x.no_cache
def confirm_user_cancel():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try: 
        return f"""
        <browser mix-update="#block_confirm"></browser>
        """
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500


#########################      
@app.post("/api-block-user")
def block_user():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:        
        user_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))

        db, cursor = x.db()
        q="SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()

        if user["user_deleted_at"] != 0 : raise Exception(x.lans('user_is_deleted').capitalize(), 400)
        if user["user_is_blocked"] != 0 : raise Exception(f"{x.lans('user_is_already').capitalize()} {x.lans('blocked')}", 400)

        q="UPDATE users SET user_is_blocked = 1 WHERE user_pk = %s"
        cursor.execute(q, (user_pk, ))
        db.commit()
        if cursor.rowcount != 1: raise Exception(f"{x.lans('user_couldnt_be').capitalize()} {x.lans('blocked')}", 400)

        new_input = render_template("___button_unblock_user.html", user=user)
        
        email_user_blocked = render_template("_email_user_blocked.html", lan=x.default_language, link=app.config['LINK_BASE'])
        
        x.send_email(user["user_email"], f"{x.lans('account_has_been').capitalize()} {x.lans('blocked')}", email_user_blocked) 
       
        toast_ok = render_template("___toast_ok.html", message=x.lans('email_sent_success').capitalize())

        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#user_block_{user_pk}">
                {new_input}
            </browser>
            <browser mix-update="#block_confirm"></browser>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#########################      
@app.post("/api-unblock-user")
def unblock_user():
    if not x.validate_admin_logged() :
        session.clear()
        return redirect(url_for("view_index"))
    try:
        
        user_pk = x.validate_uuid4_without_dashes(request.args.get("key", ""))

        db, cursor = x.db()
        q="SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()

        if user["user_deleted_at"] != 0 : raise Exception(x.lans('user_is_deleted').capitalize(), 400)
        if user["user_is_blocked"] == 0 : raise Exception(f"{x.lans('user_isnt').capitalize()} {x.lans('blocked')}", 400)

        q="UPDATE users SET user_is_blocked = 0 WHERE user_pk = %s"
        cursor.execute(q, (user_pk, ))
        db.commit()
        if cursor.rowcount != 1: raise Exception(f"{x.lans('user_couldnt_be').capitalize()} {x.lans('unblocked')}", 400)

        new_input = render_template("___button_block_user.html", user=user)
        
        email_user_unblocked = render_template("_email_user_unblocked.html", lan=x.default_language, link=app.config['LINK_BASE'])
        # ic(email_verify_account)
        x.send_email(user["user_email"], f"{x.lans('account_has_been').capitalize()} {x.lans('unblocked')}", email_user_unblocked) 
       
        toast_ok = render_template("___toast_ok.html", message=x.lans('email_sent_success').capitalize())

        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#user_block_{user_pk}">
                {new_input}
            </browser>
            <browser mix-update="#block_confirm"></browser>
        """
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance').capitalize())
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()






