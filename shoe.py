
from flask import Flask, render_template, request, redirect, url_for, make_response, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, random

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE CONFIG ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///menu.db"
app.config['SQLALCHEMY_BINDS'] = {
    'user_orders': "sqlite:///user_orders.db"
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- UPLOAD CONFIG ----------------
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- MODELS ----------------
class Menu(db.Model):
    sno= db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255), nullable=False)

class User(db.Model):
    __bind_key__ = 'user_orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    orders = db.relationship('Order', backref='user', lazy=True)

class Order(db.Model):
    __bind_key__ = 'user_orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("home"))
    return redirect(url_for("register"))
from flask import request, render_template, redirect, url_for, session, make_response

@app.route("/register", methods=["GET", "POST"])
def register():
    # 🚫 BLOCK REGISTER PAGE IF USER ALREADY REGISTERED
    if session.get("user_id") or request.cookies.get("registered") == "yes":
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        address = request.form.get("address")

        user = User(customer_name=name, phone=phone, address=address)
        db.session.add(user)
        db.session.commit()

        # ✅ LOGIN / REGISTER SESSION
        session["user_id"] = user.id

        # ✅ COOKIE (OPTIONAL UX HELP)
        resp = make_response(redirect(url_for("home")))
        resp.set_cookie("registered", "yes", max_age=60 * 60 * 24 * 30)
        return resp

    return render_template("register.html")


# ---------- HOME ----------
@app.route("/home")
def home():
    allmenu = Menu.query.all()
    hero_item = random.choice(allmenu) if allmenu else None
    slogan_item = random.choice(allmenu) if allmenu else None
    return render_template(
        "home.html",
        allmenu=allmenu,
        hero_item=hero_item,
        slogan_item=slogan_item
    )

# ---------- ORDER PAGE ----------

@app.route('/order1/<image>')
def order1(image):
    item = Menu.query.filter_by(image=image).first_or_404()
    return render_template('order.html', item=item)

# ---------- BUY ----------
@app.route("/buy", methods=["POST"])
def buy():
    if "user_id" not in session:
        return redirect(url_for("register"))

    order = Order(
        name=request.form.get("name"),
        size=int(request.form.get("size")),
        price=float(request.form.get("price")),
        user_id=session["user_id"]
    )

    db.session.add(order)
    db.session.commit()
    return redirect("/update-profile")
    

# ---------- ALERT ----------
@app.route("/alert2")
def alert2():
    return render_template("alert2.html")

# ---------- MY ORDERS (ONLY MINE) ----------@app.route('/cancel-item/<int:order_id>')
@app.route('/cancel-item/<int:order_id>')
def cancel_item(order_id):
    if "user_id" not in session:
        return redirect(url_for("register"))

    order = Order.query.filter_by(
        id=order_id,
        user_id=session["user_id"]
    ).first_or_404()

    db.session.delete(order)
    db.session.commit()

    return redirect(url_for("my_orders"))

@app.route("/my-orders")
def my_orders():
    if "user_id" not in session:
        return redirect(url_for("register"))

    user = User.query.get_or_404(session["user_id"])
    orders = Order.query.filter_by(user_id=user.id).all()

    return render_template("my_entries.html", user=user, orders=orders)

# ---------- ADMIN LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("name") == "ayush" and request.form.get("password") == "1234":
            return redirect("/edit")
        return render_template("alert1.html")
    return render_template("login.html")

# ---------- ADMIN ADD MENU ----------
@app.route("/edit", methods=["GET", "POST"])
def edit():
    if request.method == "POST":
        image = request.files.get("image")
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(UPLOAD_FOLDER, filename))

            menu = Menu(
                name=request.form.get("name"),
                price=float(request.form.get("price")),
                image=filename
            )
            db.session.add(menu)
            db.session.commit()
            return redirect("/edit")

    return render_template("edit.html", allmenu=Menu.query.all())

@app.route('/update/<int:sno>', methods=["GET", "POST"])
def update(sno):
    menu = Menu.query.get_or_404(sno)
    if request.method == "POST":
        menu.name = request.form.get('name')
        menu.price = int(request.form.get('price'))
        db.session.commit()
        return redirect('/update-item')
    return render_template('update.html', menu=menu)

@app.route('/update-item')
def show():
    allmenu = Menu.query.all()
    return render_template('update-item.html', allmenu=allmenu)

@app.route('/update-profile', methods=["GET", "POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("register"))

    # 🚫 If profile already updated, block page
    if session.get("profile_updated"):
        return redirect(url_for("alert2"))

    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":
        user.phone = request.form.get("phone")
        user.address = request.form.get("address")
        db.session.commit()

        # ✅ mark profile as updated
        session["profile_updated"] = True

        return redirect("/alert2")

    return render_template("change_add.html", user=user)

@app.route('/details')
def details():
    order = Order.query.all()
    user = User.query.all()
    return render_template('user_order.html',order=order,user=user)

@app.route('/delete-item/<int:sno>')
def delete(sno):
    menu = Menu.query.get(sno)
    if menu:
        db.session.delete(menu)
        db.session.commit()
        return redirect('/delete')
 
@app.route('/delete')
def delete_page():
    allmenu = Menu.query.all()
    return render_template("delete.html", allmenu=allmenu)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect(url_for("register")))
    resp.delete_cookie("registered")
    return resp

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

