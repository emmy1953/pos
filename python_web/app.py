from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from models import (
    ensure_default_data,
    USER_STORE,
    CONTACT_STORE,
)
import io

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'

ensure_default_data()

def current_user():
    if 'username' in session:
        return {'username': session['username'], 'role': session.get('role','user')}
    return None

def login_required(f):
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapped.__name__ = f.__name__
    return wrapped

def admin_required(f):
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None or user.get('role') != 'admin':
            flash('Administrator access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    wrapped.__name__ = f.__name__
    return wrapped

@app.route('/')
def index():
    if current_user():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        user_node = USER_STORE.authenticate(username, password)
        if user_node:
            session['username'] = user_node.username
            session['role'] = user_node.role
            flash('Signed in successfully.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        if not username or not password:
            flash('Username and password are required.', 'warning')
        elif USER_STORE.find(username) is not None:
            flash('Username already exists.', 'danger')
        else:
            USER_STORE.add(username, password, 'user')
            flash('Account created. Please sign in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Signed out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user()
    contacts = CONTACT_STORE.list_all()
    return render_template('dashboard.html', user=user, count=len(contacts))

@app.route('/contacts')
@login_required
def contacts_view():
    user = current_user()
    q = request.args.get('q','').strip()
    if q:
        contacts = CONTACT_STORE.search(q)
    else:
        contacts = CONTACT_STORE.list_all()
    return render_template('contacts.html', user=user, contacts=contacts, q=q)

@app.route('/contacts/add', methods=['GET','POST'])
@login_required
def add_contact_view():
    user = current_user()
    if request.method == 'POST':
        data = {k: request.form.get(k,'').strip() for k in ['first_name','last_name','phone','email','address','notes']}
        if CONTACT_STORE.add(data, user['username']):
            flash('Contact added.', 'success')
            return redirect(url_for('contacts_view'))
        flash('A duplicate contact already exists.', 'danger')
    return render_template('contact_form.html', action='Add', contact={})

@app.route('/contacts/edit/<int:cid>', methods=['GET','POST'])
@login_required
def edit_contact_view(cid):
    contact = CONTACT_STORE.find(cid)
    if not contact:
        flash('Contact not found.', 'warning')
        return redirect(url_for('contacts_view'))
    if request.method == 'POST':
        data = {k: request.form.get(k,'').strip() for k in ['first_name','last_name','phone','email','address','notes']}
        if CONTACT_STORE.update(cid, data, current_user()['username']):
            flash('Contact updated.', 'success')
            return redirect(url_for('contacts_view'))
        flash('A duplicate contact already exists.', 'danger')
    return render_template('contact_form.html', action='Edit', contact=contact)

@app.route('/contacts/delete/<int:cid>', methods=['POST'])
@login_required
def delete_contact_view(cid):
    CONTACT_STORE.delete(cid, current_user()['username'])
    flash('Contact deleted.', 'info')
    return redirect(url_for('contacts_view'))

@app.route('/contacts/export')
@login_required
def export_view():
    csv_text = CONTACT_STORE.export_csv()
    return send_file(io.BytesIO(csv_text.encode('utf-8')), download_name='contacts.csv', mimetype='text/csv')

@app.route('/contacts/import', methods=['GET','POST'])
@login_required
def import_view():
    if request.method == 'POST':
        f = request.files.get('file')
        if f and f.filename.endswith('.csv'):
            text = f.stream.read().decode('utf-8')
            duplicates = CONTACT_STORE.import_csv(text)
            flash('Imported (some duplicates may have been skipped).', 'info' if duplicates else 'success')
            return redirect(url_for('contacts_view'))
        flash('Please upload a CSV file.', 'warning')
    return render_template('import.html')

@app.route('/users')
@login_required
@admin_required
def users_view():
    users = USER_STORE.list_users()
    return render_template('users.html', user=current_user(), users=users)

@app.route('/users/add', methods=['GET','POST'])
@login_required
@admin_required
def add_user_view():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        role = request.form.get('role','user')
        if USER_STORE.add(username, password, role):
            flash('User created.', 'success')
            return redirect(url_for('users_view'))
        flash('Failed to create user (exists or invalid role).', 'danger')
    return render_template('user_form.html', user=current_user())

if __name__ == '__main__':
    app.run(debug=True)
