import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():

    symbolshare = {} # dict of symbol-share
    symbolprice = {} # dict of symbol-price
    sharesvalue = {} # dict of share-value
    symbolname = {} # dict of symbol-name
    userstocklist = [] # list of stock-symbol user bought

    username = db.execute("SELECT username From users where id = ':theid'", theid=session["user_id"])[0]["username"]

    usercash = float(db.execute("SELECT cash FROM users where id = ':theid'", theid=session["user_id"])[0]["cash"])
    assets = usercash

    # shares = db.execute("SELECT shares FROM 'transaction' where userid = ':theid'", theid=session["user_id"])

    allstock = db.execute("SELECT symbol FROM 'transaction' where userid = ':theid'", theid=session["user_id"])

    # add in list without duplicate
    for i in range(len(allstock)):
        if allstock[i]["symbol"] not in userstocklist:
            userstocklist.append(allstock[i]["symbol"])

    # count shares for each symbol in the list
    for i in userstocklist:
        countshare = 0
        part = db.execute("SELECT shares FROM 'transaction' where userid = ':theid' AND symbol = :i", theid=session["user_id"], i=i)
        for j in range(len(part)):
            countshare += part[j]["shares"]
        symbolshare[i] = int(countshare)


    # lookup the current price of owned share
    for i in userstocklist:
        detail = lookup(i)
        currentprice = float(detail["price"])
        name = detail["name"]
        symbolname[i] = name
        symbolprice[i] = usd(currentprice)
        # estimate the shares value by current price
        value = symbolshare[i] * currentprice
        sharesvalue[i] = usd(value)
        assets += value
    assets = usd(assets)
    usercash = usd(usercash)

    """Show portfolio of stocks"""
    return render_template("profile.html", username=username, usercash=usercash, userstocklist=userstocklist, symbolname=symbolname, symbolshare=symbolshare, symbolprice=symbolprice, sharesvalue=sharesvalue, assets=assets)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    # GET means when entering the quote page
    if request.method == "GET":
        return render_template("buy.html")

    # if method is POST means submit bottom
    else:
        # give user input a name, symbol.
        symbol = request.form.get("symbol")
        # function "lookup(symbol)" search for the stock by its symbol
        # return a dictionary{name: XXX, price: XXX, symbol: XXX}
        quote = lookup(symbol)


        if quote == None:
            return apology("Can't find symbol")

        price = float(quote["price"]) # float

        share = request.form.get("shares") # str

        symbol = quote["symbol"]


        try:
            # turn share into a float type to calculate
            share = int(share)
        except TypeError:
            return apology("Invalid input share", 400)
        except ValueError:
            return apology("Invalid input share", 400)

        if share <= 0:
            return apology("Invalid input share", 400)


        rows = db.execute("SELECT cash FROM users where id = ':theid'", theid = session["user_id"])
        cash = float(rows[0]["cash"]) # rows[0]["cash"] is int type

        total = price * share


        if cash < total:
            return apology("Can't afford")


        # after catching all the invalid input and error
        else:

            # check for this user's previous history
            # exsist = db.execute("SELECT * FROM 'transaction' where userid = ':theid'", theid = session["user_id"])

            # if exsist == None:

                # creat a new SQL table for user transaction
            db.execute(f"INSERT INTO 'transaction' ('userid', 'symbol', 'inprice', 'shares') VALUES (':theid', '{symbol}', '{price}', '{share}')", theid=session["user_id"])
            # else:
                # db.execute(f"INSERT INTO 'transaction' ('userid', 'symbol', 'inprice', 'shares') VALUES (':theid', '{symbol}', '{price}', '{share}')", theid=session["user_id"])
                # db.execute("UPDATE")
            # update user's cash

            db.execute("UPDATE users SET cash = ':new_cash' where id = ':theid'", new_cash = cash - total, theid = session["user_id"])

            return redirect("/")




@app.route("/check", methods=["GET"])
def check():

    # search database for username
    username = request.args.get("username")
    rows = db.execute(f"SELECT * FROM users WHERE username = '{username}'")
    # SQL will show up nothing if it doeen't exist, len(row) == 0

    # if username does not exist
    # which means it is not available
    if len(rows) != 0:
        return jsonify(False)

    else:
        return jsonify(True)

    """Return true if username available, else false, in JSON format"""
    # return jsonify("TODO")


@app.route("/history")
@login_required
def history():

    data = db.execute("SELECT * FROM 'transaction' where userid = ':theid'", theid=session["user_id"])



    return render_template("history.html", data=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    # GET means when entering the quote page
    if request.method == "GET":
        return render_template("quote.html")

    # if method is POST means submit bottom
    else:
        # give user input a name, symbol.
        symbol = request.form.get("symbol")
        # function "lookup(symbol)" search for the stock by its symbol
        # return a dictionary{name: XXX, price: XXX, symbol: XXX}
        quote = lookup(symbol)

        # if user input any invalid strings
        if quote == None:
            return apology("invalid symbol")
        else:
            symbol = quote["symbol"]
            price = usd(float(quote["price"]))
            return render_template("quoted.html", quote=quote, symbol=symbol, price=price)


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # check for valid username
        if check() == jsonify(False):
            return apology("Please change username")

        elif not username:
            return apology("must provide username", 400)

        elif not password:
            return apology("must provide password", 400)

        elif not confirmation:
            return apology("please confirm your password", 400)

        elif not password == confirmation:
            return apology("password and confirmation aren't same", 400)


        else:
            rows = db.execute(f"SELECT * FROM users WHERE username = :un", un = username)

            if len(rows) != 0:
                return apology("username already exist")


            hash_password = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

            rows = db.execute(f"INSERT INTO users ('id', 'username', 'hash') VALUES (NULL, :un, '{hash_password}')", un = username)

            rows = db.execute("SELECT * FROM users WHERE username = :un", un = username)

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")

    else:
        return render_template("register.html")

    """Register user"""
    #return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    userstocklist = [] # list of stock-symbol user bought
    usersharelist = {}


    # usercash = usd(db.execute("SELECT cash FROM users where id = ':theid'", theid=session["user_id"])[0]["cash"])

    shares = db.execute("SELECT shares FROM 'transaction' where userid = ':theid'", theid=session["user_id"])

    allstock = db.execute("SELECT symbol FROM 'transaction' where userid = ':theid'", theid=session["user_id"])

    # add in list without duplicate
    for i in range(len(allstock)):
        if allstock[i]["symbol"] not in userstocklist:
            userstocklist.append(allstock[i]["symbol"])

    # count shares for each symbol in the list
    for i in userstocklist:
        countshare = 0
        part = db.execute("SELECT shares FROM 'transaction' where userid = ':theid' AND symbol = :i", theid=session["user_id"], i=i)
        for j in range(len(part)):
            countshare += part[j]["shares"]
        usersharelist[i] = countshare


    if request.method == "GET":
        return render_template("sell.html" , userstocklist=userstocklist)

    else:
        symbol = request.form.get("symbol")
        share = request.form.get("shares")

        if not symbol or not share:
            return apology("Fill in both please")
        elif int(share) > int(usersharelist[symbol]):
            return apology("Exceed shares")
        else:
            symbol = lookup(symbol)["symbol"] # standarize the symbol
            share = int(request.form.get("shares"))
            usercash = db.execute("SELECT cash FROM users where id =':theid'", theid=session["user_id"])[0]["cash"]
            price = lookup(symbol)["price"]
            income = share * price
            usercash += income
            # update users cash in table: users
            db.execute("UPDATE users SET cash = ':usercash' where id = ':theid'", theid=session["user_id"], usercash=usercash)
            # update transaction
            db.execute(f"INSERT INTO 'transaction' ('userid', 'symbol', 'inprice', 'shares') VALUES (':theid', '{symbol}', '{price}', '-{share}')", theid=session["user_id"])
        return redirect("/")




def errorhandler(e):
    """Handle error"""
    return apology("e.name, e.code")


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
