from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import x
import time
import uuid
import os
import dictionary
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
# app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024   # 1 MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024   # 1 MB

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

upload_folder = "./static/uploads"
app.config['UPLOAD_FOLDER'] = upload_folder

post_upload_folder = "./static/images"
app.config['POST_UPLOAD_FOLDER'] = post_upload_folder

upload_folder = "/home/TereseNJ/mysite/static/uploads" if x.python_domain else "./static/uploads"
app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD')
app.config['GOOGLE_SPREADSHEET_KEY'] = os.getenv('GOOGLE_SPREADSHEET_KEY')


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
        dictionary = dictionary,
        x = x
    )

##############################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lan>", methods=["GET", "POST"])
@x.no_cache
def login(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        # message = request.args.get("message", "")
        message = session.get("message", "")
        session["message"] = ""

        if session.get("user", ""): return redirect(url_for("home"))
        return render_template("login.html", lan=lan, message=message)

    if request.method == "POST":
        try:
            # lan = session["user"]["user_language"]

            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()

            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            if not user: raise Exception(x.lans('user_not_found'), 400)

            if not check_password_hash(user["user_password"], user_password):
                raise Exception(x.lans('invalid_credentials'), 400)

            if user["user_verification_key"] != "":
                raise Exception(x.lans('user_not_verified'), 400)
            if user["user_deleted_at"] != 0 :
                # raise Exception(x.lans('user_deleted'), 400)
                raise Exception("user deactivated. Contact support", 400)

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
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
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
        return "error"

##############################
@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup/<lan>", methods=["GET", "POST"])
@x.no_cache
def signup(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        return render_template("signup.html", x=x, lan=lan)

    if request.method == "POST":
        # lan = session["user"]["user_language"]
        try:
            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            user_username = x.validate_user_username()
            user_first_name = x.validate_user_first_name()

            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = "default.jpg"
            user_password_reset = ""
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0
            user_updated_at = 0
            user_deleted_at = 0
            user_is_blocked = 0

            user_hashed_password = generate_password_hash(user_password)


            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, user_username,
            user_first_name, user_last_name, user_avatar_path, user_password_reset, user_verification_key, user_verified_at, user_updated_at, user_deleted_at, user_is_blocked))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key, lan=lan)
            # ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

            # Database errors
            if "Duplicate entry" and user_email in str(ex):
                toast_error = render_template("___toast_error.html", message=x.lans('email_registered'))
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            if "Duplicate entry" and user_username in str(ex):
                toast_error = render_template("___toast_error.html", message=x.lans('username_registered'))
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintenance'))
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

##############################
@app.route("/verify-account", methods=["GET"])
@x.no_cache
def verify_account():
    if not x.validate_user_logged() : return x.redirect_index_flask()
    try:
        lan = request.args.get("lan", "")
        # lan = "en"
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""),lan)
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception("Invalid key", 400)
        return redirect( url_for('login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        
        if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        # System or developer error
        toast_error = render_template("___toast_error.html", message="Cannot verify user")
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

            if not user: raise Exception(x.lans('user_not_found'), 400)

            if user["user_verification_key"] != "":
                raise Exception(x.lans('user_not_verified'), 400)
            
            if user["user_deleted_at"] != 0 :
                raise Exception("user deleted", 400)
            
            user_password_reset = uuid.uuid4().hex

            q = "UPDATE users SET user_password_reset = %s WHERE user_email = %s"
            cursor.execute(q, (user_password_reset, user_email))
            db.commit()
            
            email_forgot_password = render_template("_email_forgot_password.html", user_password_reset=user_password_reset, lan=x.default_language)
            # ic(email_forgot_password)
            x.send_email(user_email, "Set a new password", email_forgot_password)

            toast_ok = render_template("___toast_ok.html", message="A password reset has been sent to your email")

            return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            """
            
        except Exception as ex:
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
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
            if len(request.args.get("key", "")) != 32: raise Exception("Link is invalid. Request a new link", 400)
            user_password_reset = x.validate_uuid4_without_dashes(request.args.get("key", ""),lan)
            
            db, cursor = x.db()
            q = "SELECT * FROM users WHERE user_password_reset = %s"
            cursor.execute(q, (user_password_reset,))
            user = cursor.fetchone()

            if not user: raise Exception("Link is invalid. Request a new link", 400)

        
            return render_template("change_password.html", lan=lan, x=x, user_password_reset=user_password_reset)
        except Exception as ex:
            ic(ex)
            if "db" in locals(): db.rollback()
            # User errors

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

    if request.method == "POST":
        try:
            user_new_password = x.validate_user_password()
            
            user_password_reset = x.validate_uuid4_without_dashes(request.args.get("key", ""),x.default_language)
            user_hashed_password = generate_password_hash(user_new_password)

            db, cursor = x.db()
            q = "UPDATE users SET user_password_reset = '', user_password = %s WHERE user_password_reset = %s"
            cursor.execute(q, (user_hashed_password, user_password_reset))
            db.commit()
            if cursor.rowcount != 1: raise Exception("Link is invalid. Request a new link", 400)

            session["message"] = "Your password has been changed"

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
            toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        # ic(user["user_pk"])

        next_page = 2

        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0 ORDER BY post_created_at DESC LIMIT 0, 5"
        cursor.execute(q)
        tweets = cursor.fetchall()
        # ic(tweets)
        
        for tweet in tweets:
            q="SELECT EXISTS(SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s) AS liked"
            cursor.execute(q, (user["user_pk"], tweet["post_pk"]))
            tweet["liked"] = bool(cursor.fetchone()["liked"])

        ic(tweets)
        
        q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()
        # ic(trends)

        user_follower = session.get("user", "")

        q = "SELECT * FROM users WHERE user_pk != %s AND users.user_pk NOT IN ( SELECT follows.followed_fk FROM follows WHERE follows.follower_fk = %s ) ORDER BY RAND() LIMIT 3"
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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        lan = session["user"]["user_language"]
        if not user: return "error" #maybe not needed
        db, cursor = x.db()
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0 ORDER BY post_created_at DESC LIMIT 0, 5"
        cursor.execute(q)
        tweets = cursor.fetchall()
        # ic(tweets)
        
        for tweet in tweets:
            q="SELECT EXISTS(SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s) AS liked"
            cursor.execute(q, (user["user_pk"], tweet["post_pk"]))
            tweet["liked"] = bool(cursor.fetchone()["liked"])
        # ic(tweets)

        html = render_template("_home_comp.html", tweets=tweets)
        return f"""<mixhtml mix-update="main">{ html }</mixhtml>"""
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        lan = session["user"]["user_language"]

        if not user: return "error"

        q = "SELECT * FROM users WHERE user_pk = %s"
        db, cursor = x.db()
        cursor.execute(q, (user["user_pk"],))
        user = cursor.fetchone()

        profileInfo = {"name":user["user_first_name"], "handle":user["user_username"], "path":user["user_avatar_path"]}

        lan = session["user"]["user_language"]
        profile_html = render_template("_profile.html", x=x, user=user, lan=lan, profileInfo=profileInfo)
        return f"""<browser mix-update="main">{ profile_html }</browser>"""
    except Exception as ex:
        ic(ex)
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        if not user: return "invalid user"

        lan = session["user"]["user_language"]

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

        # lan = session["user"]["user_language"]

        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        user_db = cursor.fetchone()
        user_db.pop("user_password")

        user_db["user_language"] = x.default_language
        session["user"] = user_db

        # Response to the browser
        toast_ok = render_template("___toast_ok.html", message=x.lans('update_successful'))
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
        ic(ex)
        if "db" in locals(): db.rollback()

        # User errors
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        # Database errors
        if "Duplicate entry" and user_email in str(ex):
            toast_error = render_template("___toast_error.html", message=x.lans('email_registered'))
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        if "Duplicate entry" and user_username in str(ex):
            toast_error = render_template("___toast_error.html", message=x.lans('username_registered'))
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        # System or developer error
        toast_error = render_template("___toast_error.html", message=x.lans('system_under_maintanence'))
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

        email_user_deleted = render_template("_email_user_deleted.html", lan=x.default_language, x=x)
        x.send_email(user_email, "Your account has been deleted", email_user_deleted)

        # TODO: Delete post from user
        # TODO: Delete follows from user
        # TODO: Delete likes from user

        session.clear()
        return redirect(url_for("login"))


    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/api-get-tweets")
def api_get_tweets():
    try:
        next_page = int(request.args.get("page", ""))
        # ic(next_page)
        db, cursor = x.db()
        # q = "SELECT * FROM posts LIMIT %s, 3"
        q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0  ORDER BY post_created_at DESC LIMIT %s, 5"
        cursor.execute(q, ((next_page - 1)*5, ))
        tweets = cursor.fetchall()
        ic(len(tweets))
        container = ""

        for tweet in tweets[:4]:
            html_tweet = render_template("_tweet.html", tweet = tweet)
            container = container + html_tweet

        # ic(container)
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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        lan = session["user"]["user_language"]
        if not user: return "invalid user"
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
        # post_image_path = ""
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

        toast_ok = render_template("___toast_ok.html", message="The world is reading your post !")
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
            toast_error = render_template("___toast_error.html", message=f"Post - {x.POST_MIN_LEN} to {x.POST_MAX_LEN} characters")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.route("/api-update-post", methods=["GET","POST"])
@x.no_cache
def api_update_post():
    if request.method == "GET":
        try:
            post_pk = request.args.get("key", "")

            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            if tweet["post_deleted_at"] != 0 : raise Exception("post is deleted", 400)
                # toast_error = render_template("___toast_error.html", message="post is deleted")
                # return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

            post_edit_container = render_template("___tweet-edit.html", tweet=tweet)
            return f"""
                <browser mix-replace="#post_{tweet['post_pk']}">{post_edit_container}</browser>
            """
        except Exception as ex:
            ic(ex)

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
    if request.method == "POST":
        try:
            post_pk = request.args.get("key", "")
            
            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            if tweet["post_deleted_at"] != 0 : raise Exception("post is deleted", 400)

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
                ic(" default or none")
                ic(uploaded_file)
            elif imgState == "deleted":
                image_path = ""
                ic(" from file")
            post_updated_at = int(time.time())
            # ic(image_path)

            ##### message
            post_message = x.validate_post(request.form.get("post", ""))
            if not post_message : raise Exception("Error", 400)

            q = "UPDATE posts SET post_message = %s, post_image_path = %s, post_updated_at = %s WHERE post_pk = %s"
            cursor.execute(q, (post_message, image_path, post_updated_at, tweet["post_pk"] ))
            db.commit()
            if cursor.rowcount != 1: raise Exception("post couldnt update", 400)

            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            # ic(tweet)
            # return "ok"
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

            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
        
@app.route("/api-cancel-post", methods=["GET"])
@x.no_cache
def api_cancel_post():
    try:
        post_pk = request.args.get("key", "")

        db, cursor = x.db()
        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        tweet = cursor.fetchone()

        if tweet["post_deleted_at"] != 0 : raise Exception("post is already deleted", 400)

        post_edit_container = render_template("___tweet-display.html", tweet=tweet)
        return f"""
            <browser mix-replace="#post_{tweet['post_pk']}">{post_edit_container}</browser>
            <browser mix-update="#delete_{tweet['post_pk']}"></browser>
        """
    except Exception as ex:
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#################3
@app.route("/api-cancel-confirm", methods=["GET"])
@x.no_cache
def api_cancel_confirm():
    try:
        post_pk = request.args.get("key", "")

        return f"""
            <browser mix-update="#delete_{post_pk}"></browser>
        """
    except Exception as ex:
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500


@app.route("/api-delete-post", methods=["GET","POST"])
@x.no_cache
def api_delete_post():
    if request.method == "GET":
        try:
            post_pk = request.args.get("key", "")

            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            confirm_delete = render_template("___confirm_delete_post.html", tweet=tweet)
            ic(confirm_delete)

            return f"""
            <browser mix-update="#delete_{post_pk}">{confirm_delete}</browser>
            """
        except Exception as ex:
            ic(ex)

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
    if request.method == "POST":
        try:
            post_pk = request.args.get("key", "")
            
            db, cursor = x.db()
            q="SELECT * FROM posts WHERE post_pk = %s"
            cursor.execute(q, (post_pk,))
            tweet = cursor.fetchone()

            if tweet["post_deleted_at"] != 0 : raise Exception("post is deleted", 400)

            post_deleted_at = int(time.time())

            q = "UPDATE posts SET post_deleted_at = %s WHERE post_pk = %s"
            cursor.execute(q, (post_deleted_at, tweet["post_pk"] ))
            db.commit()
            if cursor.rowcount != 1: raise Exception("post couldnt update", 400)

            user = session.get("user", "")
            # lan = session["user"]["user_language"]
            if not user: return "error" #maybe not needed
            # db, cursor = x.db()
            q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0 ORDER BY post_created_at DESC LIMIT 0, 5"
            cursor.execute(q)
            tweets = cursor.fetchall()
            # ic(tweets)
            
            for tweet in tweets:
                q="SELECT EXISTS(SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s) AS liked"
                cursor.execute(q, (user["user_pk"], tweet["post_pk"]))
                tweet["liked"] = bool(cursor.fetchone()["liked"])
            # ic(tweets)

            html = render_template("_home_comp.html", tweets=tweets)
            return f"""<mixhtml mix-update="main">{ html }</mixhtml>"""
            
            # return f"""
            # <browser mix-update="#delete_{tweet['post_pk']}"></browser>
            # <browser mix-remove="#post_full_{tweet['post_pk']}"></browser>
            # """
            # return f"""
            # <browser mix-redirect="/home"></browser>
            # """
                
        except Exception as ex:
            ic(ex)
            if "db" in locals(): db.rollback()

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

###########################
@app.route("/show-comments", methods=["GET"])
@x.no_cache
def show_comments():
    try:
        post_pk = request.args.get("key", "")

        db, cursor = x.db()

        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()

        if post["post_deleted_at"] != 0 : raise Exception("post is deleted", 400)

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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

###########################
@app.route("/hide-comments", methods=["GET"])
@x.no_cache
def hide_comments():
    try:
        post_pk = request.args.get("key", "")
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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500


#####################
@app.route("/api-add-comments", methods=["POST"])
@x.no_cache
def create_comments():
    try:
        post_pk = request.args.get("key", "")
        
        db, cursor = x.db()
        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()

        if post["post_deleted_at"] != 0 : raise Exception("post is deleted", 400)

        user = session.get("user", "")
        comment_message = x.validate_post(request.form.get("comment", ""))

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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        # ic(user_followed)

        ### select user ###
        user_follower = session.get("user", "")

        if user_followed == user_follower["user_pk"] : return ""
        
        
        ### check follow ###
        db, cursor = x.db()
        q = "SELECT * FROM follows WHERE followed_fk = %s AND follower_fk = %s "
        cursor.execute(q, (user_followed, user_follower["user_pk"]))

        following = cursor.fetchone()


        if following != None : return ""

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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        
        # check follow
        db, cursor = x.db()
        q = "SELECT * FROM follows WHERE followed_fk = %s AND follower_fk = %s "
        cursor.execute(q, (user_followed, user_follower["user_pk"]))

        following = cursor.fetchone()

        if following == None : return ""

        # Delete follow
        q = "DELETE FROM follows WHERE followed_fk = %s AND follower_fk = %s"
        cursor.execute(q, (user_followed, user_follower["user_pk"]))
        db.commit()
        
        ### Send data ###
        # ------------------ Alternative???
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_followed, ))
        user_followed_data = cursor.fetchone()
        
        new_input = render_template("___button_follow.html", suggestion=user_followed_data)

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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        q = "SELECT * FROM users WHERE user_pk != %s AND users.user_pk IN ( SELECT follows.followed_fk FROM follows WHERE follows.follower_fk = %s )"
        cursor.execute(q, (user_follower["user_pk"], user_follower["user_pk"],))
        user_all_following = cursor.fetchall()

        # ic(user_all_following)
        following_html = render_template("_following.html", user_all_following=user_all_following)
        return f"""<mixhtml mix-update="main">{ following_html }</mixhtml>"""
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/api-search")
@x.no_cache
def api_search():
    lan = session["user"]["user_language"]
    try:
        # TODO: The input search_for must be validated
        search_for = request.form.get("search_for", "")
        if not search_for: return """empty search field""", 400
        part_of_query = f"%{search_for}%"
        # ic(search_for)
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_username LIKE %s"
        cursor.execute(q, (part_of_query,))
        users = cursor.fetchall()
        return jsonify(users)
    except Exception as ex:
        ic(ex)
        return str(ex)
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

        if post["post_user_fk"] == like_user_fk["user_pk"] : return ""

        ### check like ###
        q="SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s"
        cursor.execute(q, (like_user_fk["user_pk"], post["post_pk"]))
        like = cursor.fetchone()

        if like != None : return ""

        ### create like ###
        like_created_at = int(time.time())
        # q = "INSERT INTO likes (liked_post_fk, liker_user_fk, like_created_at) VALUES (%s, %s, %s)"
        q = "INSERT INTO likes VALUES (%s, %s, %s)"
        cursor.execute(q, (post_liked_pk, like_user_fk["user_pk"], like_created_at))
        

        ### update total likes ###
        # q="UPDATE posts SET post_total_likes=post_total_likes+1 WHERE post_pk = %s"        
        # cursor.execute(q, (post["post_pk"],))
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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
        # get variable
        post_liked_pk = x.validate_uuid4_without_dashes(request.args.get("post_pk", ""))
        # select user
        like_user_fk = session.get("user", "")

        ### check post user ###
        db, cursor = x.db()
        q="SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_liked_pk,))
        post = cursor.fetchone()

        if post["post_user_fk"] == like_user_fk["user_pk"] : return ""
        
        # check like
        db, cursor = x.db()
        q="SELECT * FROM likes WHERE liker_user_fk = %s AND liked_post_fk = %s"
        cursor.execute(q, (like_user_fk["user_pk"], post_liked_pk))
        like = cursor.fetchone()

        if like == None : return ""

        # Delete like
        q = "DELETE FROM likes WHERE liked_post_fk = %s AND liker_user_fk = %s"
        cursor.execute(q, (post_liked_pk, like_user_fk["user_pk"]))

        ### update total likes ###
        post_total_likes = post["post_total_likes"]-1
        # q="UPDATE posts SET post_total_likes=%s WHERE post_pk = %s"        
        # cursor.execute(q, (post_total_likes, post_liked_pk,))
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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
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
            correct_email = app.config['ADMIN_EMAIL']
            correct_password  = app.config['ADMIN_PASSWORD']
            email = request.form.get("user_email", "")
            password = request.form.get("user_password", "")

            if correct_email != email : return "error"

            if correct_password != password : return "incorrect"

            admin = {}
            admin["email"] = correct_email
            admin["password"] = correct_password
            session["admin"] = admin
            return f"""<browser mix-redirect="/control_panel"></browser>"""
        except Exception as ex :
            ic(ex)
            return "error"
        
##############################
@app.get("/8152a9ee-1f86-4a7a-9cd7-2f45b4087694ecxx523f7c-b27f-49b7-9fc1-24baaba82a5e")
@x.no_cache
def get_data_from_sheet():
    try:
        # Check if the admin is running this end-point, else show error
        if not x.validate_admin_logged() :
            session.clear()
            return redirect(url_for("view_index"))


        # flaskwebmail
        # Create a google sheet
        # share and make it visible to "anyone with the link"
        # In the link, find the ID of the sheet. 
        # Replace the ID in the 2 places bellow
        url= f"https://docs.google.com/spreadsheets/d/{app.config['GOOGLE_SPREADSHEET_KEY']}/export?format=csv&id={app.config['GOOGLE_SPREADSHEET_KEY']}"
        res=requests.get(url=url)
        # ic(res.text) # contains the csv text structure
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
        toast_ok = render_template("___toast_ok.html", message="Dictionary updated")

        return f"""
        <browser mix-bottom="#toast">{toast_ok}</browser>
        """
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        pass


@app.route("/control_panel", methods=["GET"])
@x.no_cache
def control_panel():
    try:
        if not x.validate_admin_logged() :
            session.clear()
            return redirect(url_for("view_index"))

        # correct_email = "admin@x.com"
        # correct_password  = "password"

        # if admin["email"] != correct_email : 
        #     session.clear()
        #     return redirect(url_for("view_index"))
        # if admin["password"] != correct_password : 
        #     session.clear()
        #     return redirect(url_for("view_index"))

        return render_template("control_panel.html")
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.get("/temp")
@x.no_cache
def temp_route():
    admin = {}
    admin["email"] = "a@a.com"
    admin["password"] = "passwordwrong"
    session["admin"] = admin
    return "ok"
            

########
@app.route("/control_panel/users", methods=["GET"])
@x.no_cache
def admin_user():
    try:
        if not x.validate_admin_logged() :
            session.clear()
            return redirect(url_for("view_index"))


        db, cursor = x.db()
        # q="CALL get_all_users()"
        q="CALL get_users(%s)"
        # q="SELECT * FROM users LIMIT 10 offset %s"
        cursor.execute(q,(0,))
        all_users = cursor.fetchall()

        ic(all_users)

        return render_template("control_panel_users.html", users=all_users)
    except Exception as ex:
        ic(ex)
        pass
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

########
@app.route("/control_panel/posts", methods=["GET", "POST"])
@x.no_cache
def admin_posts():
    if request.method == "GET":
        try:
            if not x.validate_admin_logged() :
                session.clear()
                return redirect(url_for("view_index"))
            
            db, cursor = x.db()
            q="CALL get_posts(%s)"
            # q="SELECT * FROM posts LIMIT 10 OFFSET %s"
            cursor.execute(q,(0,))
            all_posts = cursor.fetchall()

            # ic(len(all_posts))

            next_page = 1
            if len(all_posts) : all_posts.pop()


            ic(all_posts)

            return render_template("control_panel_posts.html", tweets=all_posts, next_page=next_page)
        except Exception as ex:
            ic(ex)
            pass
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
    # if request.method == "POST":    
    #     try:
    #         db, cursor = x.db()
    #         q="CALL get_posts(%s)"
    #         # q="SELECT * FROM posts LIMIT 10 OFFSET %s"
    #         cursor.execute(q,(0,))
    #         all_posts = cursor.fetchall()

    #         # ic(all_posts)

    #         return render_template("control_panel_posts.html", tweets=all_posts)
    #     except Exception as ex:
    #         ic(ex)
    #         pass
    #     finally:
    #         if "cursor" in locals(): cursor.close()
    #         if "db" in locals(): db.close() 
    # 
 
##############################
@app.get("/api-get-tweets-admin")
def api_get_tweets_admin():
    try:
        next_page = int(request.args.get("page", ""))
        ic(next_page)
        db, cursor = x.db()
        
        q="CALL get_posts(%s)"
        cursor.execute(q,(10*next_page,))
        # q = "SELECT * FROM users JOIN posts ON user_pk = post_user_fk WHERE post_deleted_at = 0  ORDER BY post_created_at DESC LIMIT %s, 5"
        # cursor.execute(q, ((next_page - 1)*5, ))
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

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


#########################      
@app.get("/api-block-post")
def block_post():
    try:
        pass
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#########################      
@app.get("/api-unblock-post")
def unblock_post():
    try:
        pass
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#########################      
@app.get("/api-block-user")
def block_user():
    try:
        pass
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

#########################      
@app.get("/api-unblock-user")
def unblock_user():
    try:
        pass
    except Exception as ex:
        ic(ex)

        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400        

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
















