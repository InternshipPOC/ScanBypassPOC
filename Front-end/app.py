from flask import Flask, request, render_template, redirect, make_response
import requests
import json
import os

app = Flask(__name__)

# CouchDB config
COUCHDB_USER = os.environ.get('COUCHDB_USER')
COUCHDB_PASS = os.environ.get('COUCHDB_PASS')

COUCHDB_HOST = 'couchdb'
COUCHDB_PORT = '5984'

COUCHDB_BASE = f"http://{COUCHDB_HOST}:{COUCHDB_PORT}"
COUCHDB_SESSION = f"{COUCHDB_BASE}/_session"
COUCHDB_USERS = f"{COUCHDB_BASE}/_users"

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form['username']
    password = request.form['password']
    payload = {'name': username, 'password': password}

    r = requests.post(COUCHDB_SESSION, data=payload)
    if r.status_code == 200 and 'AuthSession' in r.cookies:
        cookie = r.cookies['AuthSession']
        session_info = requests.get(COUCHDB_SESSION, cookies={'AuthSession': cookie}).json()
        roles = session_info.get('userCtx', {}).get('roles', [])

        resp = make_response(redirect('/admin' if 'admin' in roles else '/user'))
        resp.set_cookie('AuthSession', cookie, httponly=True, samesite='Lax')
        return resp

    return "Login failed", 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    headers = {"Content-Type": "application/json"}

    # 💥 If JSON input (from curl or Postman): accept raw and forward directly
    if request.content_type == "application/json":
        raw_json = request.data
        r = requests.post(COUCHDB_USERS, headers=headers, data=raw_json, auth=(COUCHDB_USER, COUCHDB_PASS))
    else:
        # ✅ Normal browser form: build safe user object
        username = request.form['username']
        password = request.form['password']
        safe_user = {
            "_id": f"org.couchdb.user:{username}",
            "name": username,
            "roles": ["user"],
            "type": "user",
            "password": password
        }
        r = requests.post(COUCHDB_USERS, headers=headers, data=json.dumps(safe_user), auth=(COUCHDB_USER, COUCHDB_PASS))

    if r.status_code in [200, 201]:
        return redirect('/login')
    return f"Registration failed: {r.text}", 400


@app.route('/user')
def user_dashboard():
    auth = request.cookies.get('AuthSession')
    r = requests.get(COUCHDB_SESSION, cookies={'AuthSession': auth})
    user = r.json().get('userCtx', {})
    if 'user' in user.get('roles', []):
        return render_template('user_dashboard.html', name=user['name'])
    return redirect('/login')

@app.route('/admin')
def admin_dashboard():
    auth = request.cookies.get('AuthSession')
    r = requests.get(COUCHDB_SESSION, cookies={'AuthSession': auth})
    user = r.json().get('userCtx', {})
    if 'admin' in user.get('roles', []):
        return render_template('admin_dashboard.html', name=user['name'])
    return redirect('/login')

@app.route('/logout')
def logout():
    resp = make_response(redirect('/login'))
    resp.set_cookie('AuthSession', '', expires=0)
    return resp

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)
