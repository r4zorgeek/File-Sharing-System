import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from cs50 import SQL
from werkzeug.utils import secure_filename
from helpers import *

UPLOAD_FOLDER = os.getcwd() + '/uploads'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    """ Index Page of User. """

    # ensure if user reached via route GET
    if request.method == "GET":
        fileList = list()
        # check if directory for the user exists
        check_path = os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"] + "/{}".format(session['user_id'])))
        # if directory does not exist; make a new directory
        if not check_path:
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], "{}/".format(session["user_id"])))
        # list all files in the user directory
        for filename in os.listdir(UPLOAD_FOLDER + "/{}".format(session['user_id'])):
            fileList.append(filename)
        return render_template("index.html", filenames = fileList)


@app.route('/index_stud')
@login_required
def index_stud():

    # get shared folder
    result = db.execute('SELECT folder_id from shared_folder WHERE shared_user_id = :user_id', user_id = session['user_id'])
    if not result:
        return render_template('index_stud.html')
    else:
        result = result[0]['folder_id']
        session['folder_id'] = result
        fileList = list()
        # list all files in the directory
        for filename in os.listdir(UPLOAD_FOLDER + "/{}".format(result)):
            fileList.append(filename)

    return render_template('index_stud.html', filenames = fileList)

@app.route('/register_student', methods=["GET", "POST"])
def register_student():
    """ Register User in Database. """

    # if user reached via route POST
    if request.method == "POST":
       email_id = request.form.get('email_id')
       stud_name = request.form.get('stud_name')
       stud_roll_no = request.form.get('stud_roll_no')
       yofstudy = request.form.get('yofstudy')
       passw = request.form.get("password")

       # insert into students registrants to table.
       rows = db.execute("INSERT \
                         INTO stud_registrants (stud_email, stud_name, stud_roll_no, stud_yofstudy , hash) \
                         VALUES (:email, :stud_name, :stud_roll_no, :stud_yofstudy , :hash)", email = email_id, stud_name=stud_name, stud_roll_no=stud_roll_no, stud_yofstudy=yofstudy , hash = pwd_context.hash(passw))

       if not rows:
           return None
       else:
           get_id = db.execute("SELECT id FROM stud_registrants WHERE stud_email = :email", email = email_id)[0]["id"]
           session["user_id"] = get_id
           return redirect(url_for('index_stud'))

    else:
        return render_template('register.html')


@app.route('/login_teacher', methods=["GET", "POST"])
def login_teacher():
    """ Login User and redirect to index page. """

    # forget any user
    session.clear()

    # if user reached via route POST
    if request.method == "POST":
        # check user credentials
        email_id = request.form.get("email_id")
        passw = request.form.get("password")

        result = db.execute("SELECT * FROM registrants WHERE email_id = :email", email = email_id)
        if len(result) != 1 or not pwd_context.verify(passw, result[0]['hash']):
            return "INVALID USERNAME/PASSWORD"

        else:
            folder_id = db.execute('SELECT folder_id FROM shared_folder WHERE user_id = :user_id', user_id = result[0]['id'])
            print(folder_id)
            session["user_id"] = result[0]["id"]
            session['folder_id'] = folder_id[0]['folder_id']
            return redirect(url_for('index'))

    else:
        return render_template('login.html')


@app.route('/login_student', methods=["GET", "POST"])
def login_student():
    if request.method == "GET":
        return render_template('login_students.html')

    else:
        # check user credentials
        email_id = request.form.get("email_id")
        passw = request.form.get("password")

        result = db.execute("SELECT * FROM stud_registrants WHERE stud_email = :email", email = email_id)
        if len(result) != 1 or not pwd_context.verify(passw, result[0]['hash']):
            return "INVALID USERNAME/PASSWORD"

        else:
            session["user_id"] = result[0]["id"]
            return redirect(url_for('index_stud'))



@app.route('/upload_file', methods=["GET", "POST"])
def upload_file():
    """ Upload File on Server. """

    # ensure if user reached via route POST
    if request.method == "POST":
        # get file from the form
        file = request.files["fileToUpload"]
        # check if file is selected
        if not file:
            return "Please Select file to upload"

        filename = secure_filename(file.filename)
        # check if user directory exists
        result = os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'] + "/{}".format(session["user_id"])))
        # if user directory exists save in filesystem; or make new directory and save file
        if result:
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], "{}/{}".format(session["user_id"], filename)))
        else:
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], "{}/".format(session["user_id"])))
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], "{}/{}".format(session["user_id"], filename)))
        return redirect(url_for('index'))


@app.route('/uploads')
def uploads():
    """ Show the uploaded files. """
    fileList = list()
    # list all files in the directory
    for filename in os.listdir(UPLOAD_FOLDER + "/{}".format(session['user_id'])):
        fileList.append(filename)
    return render_template("uploads.html", filenames=fileList)


@app.route('/delete_file', methods=["GET", "POST"])
def delete_file():
    """ Delete User Requested File. """
    # ensure if user reached via POST
    if request.method == "POST":
        # remove requested file from the directory
        os.remove(os.path.join(app.config["UPLOAD_FOLDER"] + "/{}".format(session['user_id']), request.form.get('fileName')))
        return redirect(url_for('index'))


@app.route('/send_file/<filename>')
def send(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"] + "/{}".format(session['user_id']), filename)

@app.route('/download_file', methods=["GET", "POST"])
def download_file():
    """ Download Requested File. """

    # ensure if user reached via POST
    if request.method == "POST":
        # get file name
        fileName = request.form.get('fileName')
        # send file to the client
        return send_from_directory(app.config["UPLOAD_FOLDER"] + "/{}".format(session['folder_id']), fileName, as_attachment=True)


@app.route('/shareFolder', methods=["GET", "POST"])
def shareFolder():
    if request.method == "POST":

        # get user credentials
        email_id = request.form.get('email_id')

        # get shared_user_id
        shared_user_id = db.execute('SELECT id from stud_registrants WHERE stud_email = :email', email = email_id)[0]['id']

        # insert into shareFolder table
        result = db.execute("INSERT \
                             INTO shared_folder (user_id, shared_email, shared_user_id, folder_id) \
                             VALUES (:user_id, :shared_email, :shared_user_id, :folder_id)", user_id = session["user_id"] ,shared_user_id = shared_user_id, shared_email=email_id, folder_id=session['user_id'])

        return redirect(url_for('index'))



@app.route("/logout")
def logout():
    """ Logout Current User. """

    # clear user id
    session.clear()

    return redirect(url_for('index'))
