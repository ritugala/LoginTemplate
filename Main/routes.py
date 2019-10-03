from flask import render_template, url_for, flash, redirect, request
from Main.models import Student
from Main.forms import LoginForm, AddStudents, UpdateAccountForm, RequestResetForm, ResetPasswordForm
from Main import app, db, bcrypt, mail
from flask_login import login_user, current_user, logout_user, login_required
import secrets, os
from PIL import Image
from flask_mail import Message


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')



@app.route("/studentlogin", methods=['GET', 'POST'])
def studentlogin():
    if current_user.is_authenticated:
        return redirect(url_for('/'))
    form = LoginForm()
    if form.validate_on_submit():
        student = Student.query.filter_by(id = form.id.data).first()
        if student and bcrypt.check_password_hash(student.password, form.password.data):
            login_user(student, remember=form.remember.data)
            next_page = request.args.get('next')

            return redirect(next_page) if next_page else redirect(url_for('studenthome'))
        else:
            flash('Login Unsuccessful. Please check id and password', 'danger')
    return render_template('studentlogin.html', title='Login', form=form)


@app.route('/studenthome')
def studenthome():
    return redirect(url_for('view_posts'))


@app.route('/add/student', methods = ['GET', 'POST'])
def AddStudent():
    form = AddStudents()
    if form.validate_on_submit():
        student = Student(name = form.name.data, id = form.id.data, email = form.email.data, password = bcrypt.generate_password_hash
                                                                                    (form.name.data + str(form.id.data % 100)).decode('utf-8'))
        db.session.add(student)
        db.session.commit()
        flash('Student added!', category="success")
        form.id.data = None
        form.name.data = None
        #next_page = request.args.get('next')
        #return redirect(next_page) if next_page else redirect(url_for('home'))
    else:
        flash('Student couldnt be added', category='success')
    return render_template('adduser.html', form = form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.name = form.name.data
        db.session.commit()
        flash('Your account has been updated', category='success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.name.data = current_user.name
    else:
        flash('unsuccesful', 'danger')
    image_file = url_for('static', filename = 'profile_pics/'+ current_user.image_file)
    return render_template('account.html', title = 'Account', image_file = image_file, form=form)


def send_reset_email(student):
    token = student.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[student.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
    mail.send(msg)


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        student = Student.query.filter_by(email=form.email.data).first()
        send_reset_email(student)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('studentlogin'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    student = Student.verify_reset_token(token)
    if student is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        student.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('studentlogin'))
    return render_template('reset_token.html', title='Reset Password', form=form)