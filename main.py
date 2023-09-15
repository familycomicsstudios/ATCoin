from flask import Flask
from flask import render_template, redirect, session, request
from requests import get
from os import environ
from base64 import b64encode
import random
from replit import db
import time
from flask_cors import CORS
import datetime

app = Flask('app')
app.secret_key = environ["SECRET_KEY"]
app.static_folder = 'static'
def base64(string):
    return b64encode(string.encode("utf-8")).decode()
    
@app.get("/login/")
def login():
    return redirect(f"https://auth.itinerary.eu.org/auth/?redirect={ base64('https://ATCoin.themadpunter.repl.co/authenticate') }&name=ATCoin")

@app.get("/logout/")
def logout():
    session.clear()
    return redirect('/')

@app.get("/authenticate/")
def handle():
    privateCode = request.args.get("privateCode")

    if privateCode == None:
        return "Bad Request", 400

    resp = get(
        f"https://auth.itinerary.eu.org/api/auth/verifyToken?privateCode={privateCode}"
    ).json()
    if resp["redirect"] == "https://ATCoin.themadpunter.repl.co/authenticate":
        if resp["valid"]:
            session["username"] = resp["username"]
            return redirect("/")
        else:
            return f"Authentication failed - please try again later."
    else:
        return "Invalid Redirect", 400


@app.route('/')
def main_login_page():
    try:
        params = {
            "username": session["username"], "time": datetime.timedelta(seconds=round(db["lastReset"]+3600-time.time())), "balance": _balance(session["username"], "ATC"), "pool": db["pool"], "balances": db["users"][session["username"].lower()].value
        }
    except:
        params = {
            "time": datetime.timedelta(seconds=round(db["lastReset"]+3600-time.time())), "pool": db["pool"]
        }
    return render_template("index.html", **params)

@app.route('/pay/<payee>/')
def paypage(payee):
    try:
        params = {
            "username": session["username"], "balance": balance(session["username"], "ATC"), "payee": payee}
    except:
        params = {
            "payee": payee
        }
    return render_template("pay.html", **params)

@app.route('/authcode/')
def authcode():
    code = random.randint(10000000000,99999999999)
    try:
        db["authCodes"][code] = session['username']
    except:
        return render_template("notLoggedIn.html")
    params = {
        "code": code
    }
    return render_template("authcode.html", **params)

@app.route('/api/v1/auth/<code>/')
def code(code):
    try:
        session["username"] = db["authCodes"][str(code)]
        return db["authCodes"][str(code)]
    except:
        return ""


def _balance(username, token):
    try:
        db["users"][username.lower()]["Testcoin"] = 1
    except:
        db["users"][username.lower()] = {}
    try:
        return db["users"][username.lower()][token]
    except:
        db["users"][username.lower()][token] = 0
        return db["users"][username.lower()][token]

@app.route('/api/v1/balance/<username>/<token>/')
def balance(username, token):
    return str(_balance(username, token))

@app.route('/api/v1/send/<sendto>/<amount>/<token>/')
def send(sendto, amount, token):
    if float(amount) < 0:
        return "Nice try", 401
    if request.args.get("auth") != None:
        try:
            
            if code(request.args.get("auth")) == "":
                return "Invalid code", 401
            session["username"] = code(request.args.get("auth"))
            
        except:
            return "Invalid code", 401
    amount = float(amount)
    try:
        if _balance(session["username"], token) >= amount:
            db["users"][session["username"].lower()][token] -= amount
            db["users"][sendto.lower()][token] = _balance(sendto, token) + amount
            return "Done", 200
        else:
            return "Insufficient funds", 401
    except:
        return "Not logged in", 401

@app.route("/api/v1/mine/")
def mine():
    if request.args.get("auth") != None:
        try:
            
            if code(request.args.get("auth")) == "":
                return "Invalid code", 401
            session["username"] = code(request.args.get("auth"))
            
        except:
            return "Invalid code", 401
    try:
        username = session["username"].lower()
        if time.time() - db["lastReset"] >= 3600:
            db["users"][username]["ATC"] = _balance(username, "ATC") + db["pool"]
            db["pool"] = 1
            db["mined"] = []
            db["lastReset"] = time.time()
        if not username in db["mined"]:
            db["mined"].append(username)
            db["users"][username]["ATC"] = _balance(username, "ATC") + db["pool"]/2
            db["pool"] = db["pool"]/2
            
            return balance(username, "ATC"), 200
        else:
            return "Already mined", 401
    except:
        return "Not logged in", 401

@app.route("/send/<sendto>/<amount>/<token>/")
def sendraw(sendto, amount, token):
    response, code = send(sendto, amount, token)
    if response == "Done":
        return render_template("transComp.html", amount=amount, payto=sendto, token=token)
    elif response == "Insufficient funds":
        return render_template("isf.html", amount=amount, token=token)
    elif response == "Nice try":
        return redirect("https://shattereddisk.github.io/rickroll/rickroll.mp4")
    else:
        return render_template("notLoggedIn.html")

@app.route('/balance/<user>/<token>/')
def balanceraw(user, token):
    balances = balance(user, token)
    return render_template('balance.html', user=user, balances=balances, token=token)
CORS(app)

@app.route('/mine/')
def mineraw():
    try:
        oldBal = _balance(session["username"], "ATC")
    except:
        return render_template("notLoggedIn.html")
    bal, code = mine()
    if bal == "Already mined":
        return render_template("alrMined.html")
    elif bal == "Not logged in":
        return render_template("notLoggedIn.html")
    else:
        print(float(bal)-oldBal)
        return render_template("mine.html", amount=float(bal)-oldBal)

@app.route("/logCode/<codes>/")
def logInWithCode(codes):
    if code(codes) == '':
        return render_template("incorrectCode.html")
    else:
        return render_template("loginSuccess.html", user=code(codes))

@app.route("/api/v1/wallet/<username>/")
def newWallet(username):
    code = random.randint(10000000000,99999999999)
    uname = username
    if not "."+uname in db["authCodes"].values():
        db["authCodes"][code] = "."+str(uname)
        return str(code)
    else:
        return "Taken"
@app.route("/qr/")
def qr():
    return render_template("qr.html")

@app.route('/api/v1/burn/<amount>/<token>/')
def burn(amount, token):
    if float(amount) < 0:
        return "Nice try", 401
    if request.args.get("auth") != None:
        try:
            
            if code(request.args.get("auth")) == "":
                return "Invalid code", 401
            session["username"] = code(request.args.get("auth"))
            
        except:
            return "Invalid code", 401
    amount = float(amount)
    try:
        if _balance(session["username"], token) >= amount:
            db["users"][session["username"].lower()][token] -= amount
            return "Done", 200
        else:
            return "Insufficient funds", 401
    except:
        return "Not logged in", 401

@app.route("/burn/<amount>/<token>/")
def burnraw(amount, token):
    response, code = burn(amount, token)
    if response == "Done":
        return render_template("transComp.html", amount=amount, payto="the burner", token=token)
    elif response == "Insufficient funds":
        return render_template("isf.html", amount=amount)
    elif response == "Nice try":
        return redirect("https://shattereddisk.github.io/rickroll/rickroll.mp4")
    else:
        return render_template("notLoggedIn.html")

@app.route('/api/v1/convert/<token>/<amount>/')
def convert(amount, token):
    if float(amount) < 0:
        return "Nice try", 401
    if request.args.get("auth") != None:
        try:
            
            if code(request.args.get("auth")) == "":
                return "Invalid code", 401
            session["username"] = code(request.args.get("auth"))
            
        except:
            return "Invalid code", 401
    amount = float(amount)
    try:
        if _balance(session["username"], token) >= amount:
            db["users"][session["username"].lower()][token] -= amount
            if token == "ATC":
                db["users"][session["username"].lower()]["CRSC"] += amount / 10
                return "Done", 200, "CRSC"
            if token == "CRSC":
                db["users"][session["username"].lower()]["ATC"] += amount * 10
                return "Done", 200, "ATC"
            return "Cant convert", 401, ""
        else:
            return "Insufficient funds", 401, ""
    except:
        return "Not logged in", 401, ""

@app.route("/convert/<token>/<amount>/")
def convertraw(amount, token):
    response, code, to = convert(amount, token)
    if response == "Done":
        return render_template("convertDone.html", amount=amount, token=token, to=to)
    elif response == "Insufficient funds":
        return render_template("isf.html", amount=amount)
    elif response == "Nice try":
        return redirect("https://shattereddisk.github.io/rickroll/rickroll.mp4")
    elif response == "Nice try":
        return render_template("cantConvert.html")
    else:
        return render_template("notLoggedIn.html")


# CORS Headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers',
                         'Content-Type,Authorization,true')
    response.headers.add('Access-Control-Allow-Methods',
                         'GET,PUT,POST,DELETE,OPTIONS')
    return response

app.run(host='0.0.0.0', port=80, debug=False)
