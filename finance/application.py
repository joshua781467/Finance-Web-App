import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
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

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows=db.execute("SELECT symbol,SUM(shares) AS total_share FROM portfolio WHERE user_id=:user_id GROUP BY symbol HAVING total_share>0;",user_id=session["user_id"])
    user_portfolio=[]
    grand_total=0
    for row in rows:
        stock=lookup(row["symbol"])
        user_portfolio.append({
            "stock":stock["symbol"],
            "symbol":stock["symbol"],
            "name":stock["name"],
            "price":stock["price"],
            "shares":row["total_share"],
            "total":stock["price"]*row["total_share"]

        })
        grand_total=grand_total+stock["price"]*row["total_share"]
    user=db.execute("SELECT cash FROM users WHERE id=:user_id",user_id=session["user_id"])
    cash=user[0]["cash"]
    grand_total=grand_total+cash
    return render_template("index.html",grand_total=grand_total,user_portfolio=user_portfolio,cash=cash)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method=="POST":
        if not request.form.get("symbol") or not request.form.get("shares"):
            return apology("please provide symbol or shares")
        if not request.form.get("shares").isdigit():
            return apology("invalid shares")
        symbol=request.form.get("symbol").upper()
        shares=int(request.form.get("shares"))
        stock=lookup(symbol)
        if not stock:
            return apology("invalid stock")
        cost=float(stock["price"])*float(shares)
        row=db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])
        amount=row[0]["cash"]
        updated_amount=amount-cost
        if updated_amount<0:
            return apology("insufficient amount")
        db.execute("UPDATE users SET cash=:updated_amount WHERE id=:id",id=session["user_id"],updated_amount=updated_amount)
        db.execute("INSERT INTO portfolio (user_id,symbol,shares,price) VALUES(:user_id,:symbol,:shares,:price)",user_id=session["user_id"],symbol=stock["symbol"],shares=shares,price=stock["price"])
        flash("stock bought")
        return redirect("/")
    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history=db.execute("SELECT symbol,shares,price,transacted FROM portfolio WHERE user_id=:user_id",user_id=session["user_id"])
    return render_template("history.html",history=history)


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
    """Get stock quote."""
    if request.method=="POST":
        if not request.form.get("symbol"):
            return apology("Enter stock symbol")
        symbol=request.form.get("symbol").upper()
        stock=lookup(symbol)
        if stock==None:
            return apology("invalid symbol")
        return render_template("quoted.html",stockvar={
            "name":stock["name"],
            "symbol":stock["symbol"],
            "price":stock["price"]
        })
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method=="POST":
        if not request.form.get("username"):
            return apology("No username provided")
        if not request.form.get("password") or not request.form.get("confirm_password"):
            return apology("No password provided")
        if request.form.get("password")!= request.form.get("confirm_password"):
            return apology("Password missmatch")
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if len(rows)>0:
            return apology("username already exist")
        db.execute("INSERT INTO users (username,hash) VALUES (:username, :password)",username=request.form.get("username"),password=generate_password_hash(request.form.get("password")))
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("register.html")







@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method=="POST":
        if not request.form.get("symbol") or not request.form.get("shares"):
            return apology("please provide symbol or shares")
        if not request.form.get("shares").isdigit():
            return apology("invalid shares")
        symbol=request.form.get("symbol").upper()
        shares=int(request.form.get("shares"))
        stock=lookup(symbol)
        if not stock:
            return apology("invalid stock")
        rows=db.execute("SELECT symbol, SUM(shares) AS total_share FROM portfolio WHERE user_id=:user_id GROUP BY symbol HAVING total_share>0",user_id=session["user_id"])
        for row in rows:
            if row["symbol"]==symbol:
                if row["total_share"]< shares:
                    return apology("cannot sell")
        cost=float(stock["price"])*float(shares)
        row=db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])
        amount=row[0]["cash"]
        updated_amount=amount+cost

        db.execute("UPDATE users SET cash=:updated_amount WHERE id=:id",id=session["user_id"],updated_amount=updated_amount)
        db.execute("INSERT INTO portfolio (user_id,symbol,shares,price) VALUES(:user_id,:symbol,:shares,:price)",user_id=session["user_id"],symbol=stock["symbol"],shares= -1*shares,price=stock["price"])
        flash("stock sold")
        return redirect("/")
    else:
        return render_template("sell.html")

@app.route("/cash", methods=["GET", "POST"])
@login_required
def cash():
    if request.method=="POST":
        db.execute("UPDATE users SET cash=:money WHERE id=:user_id",money=request.form.get("cash"),user_id=session["user_id"])
        flash("succesfully added cash")
        return redirect("/")
    else:
        return render_template("cash.html")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
