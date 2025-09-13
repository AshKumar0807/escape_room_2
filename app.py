from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from sqlalchemy import create_engine


app = Flask(__name__)

load_dotenv()
app.secret_key = os.getenv("secret_key")

TURSO_DB_URL = os.getenv("TURSO_DATABASE_URL")  # host like “my-flask-db-xxx.turso.io”, should not include libsql://
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

# Build the URL using "sqlite+libsql://"
db_url = f"sqlite+libsql://{TURSO_DB_URL}?secure=true"

# Provide token via connect_args
engine = create_engine(
    db_url,
    connect_args={
        "auth_token": TURSO_AUTH_TOKEN
    }
)

# Then with Flask-SQLAlchemy,bind the above engine
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {"auth_token": TURSO_AUTH_TOKEN}
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

#db models
class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    #content = db.Column(db.Text, nullable=False) # riddles isme jayenge
    question = db.Column(db.Text, nullable=False)  # agar direct question krna hai toh isme
    answer = db.Column(db.String(100), nullable=False)
    unlock_code = db.Column(db.String(50), nullable=False, unique=True)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)  # new
    last_key = db.Column(db.String(50))
    current_page_id = db.Column(db.Integer, db.ForeignKey("page.id"), nullable=True)
    current_page = db.relationship("Page", foreign_keys=[current_page_id])
    progress = db.relationship("TeamProgress", backref="team", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class TeamProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False)
    page_id = db.Column(db.Integer, db.ForeignKey("page.id", ondelete="CASCADE"), nullable=False)
    page = db.relationship("Page")

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return render_template("index.html", team=session.get("team_name"))

@app.route("/ping")
def ping():
    try:
        db.session.execute("SELECT 1")
        return "✅ Connected to Turso!"
    except Exception as e:
        return f"❌ DB Error: {e}"

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        team_name = request.form["team_name"].strip()
        password = request.form["password"].strip()  # new

        if not team_name or not password:
            flash("Team name and password cannot be empty!")
            return redirect(url_for("signup"))

        existing_team = Team.query.filter_by(name=team_name).first()
        if existing_team:
            flash("Team name already exists!")
            return redirect(url_for("signup"))

        #first page assignment yeha
        first_page = Page.query.order_by(Page.id).first()
        if not first_page:
            flash("No pages available yet. Admin should add pages first.")
            return redirect(url_for("index"))

        team = Team(
            name=team_name,
            current_page_id=first_page.id,
            password_hash=generate_password_hash(password)  # new
        )

        db.session.add(team)
        db.session.commit()

        session["team_name"] = team.name
        session.permanent = True 
        flash(f"Team '{team_name}' registered! Start solving challenges.")
        return redirect(url_for("page"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        team_name = request.form["team_name"].strip()
        password = request.form["password"].strip()
        if not team_name or not password:
            flash("Team name and password are required!")
            return redirect(url_for("login"))

        team = Team.query.filter_by(name=team_name).first()
        if not team or not team.check_password(password):
            flash("Invalid team name or password!")
            return redirect(url_for("login"))

        session["team_name"] = team.name
        session.permanent = True
        flash(f"Welcome back, {team.name}! Continue your challenges.")
        return redirect(url_for("page"))

    return render_template("login.html")

# @app.route("/page", methods=["GET", "POST"])
# def page():
#     team_name = session.get("team_name")
#     if not team_name:
#         flash("Please signup or login first!")
#         return redirect(url_for("signup"))

#     team = Team.query.filter_by(name=team_name).first()
#     if not team:
#         flash("Team not found!")
#         return redirect(url_for("signup"))

#     # Get current page
#     page = None
#     if team.current_page_id:
#         page = Page.query.get(team.current_page_id)

#     if not page:
#         # New team: assign first page
#         first_page = Page.query.order_by(Page.id).first()
#         if first_page:
#             team.current_page_id = first_page.id
#             db.session.commit()
#             page = first_page
#         else:
#             return "All pages completed! 🎉"

#     code_unlocked = False
#     unlock_code = None

#     if request.method == "POST":
#         answer = request.form.get("answer", "").strip().lower()

#         if answer == page.answer.lower():
#             code_unlocked = True
#             unlock_code = page.unlock_code

#             if not TeamProgress.query.filter_by(team_id=team.id, page_id=page.id).first():
#                 db.session.add(TeamProgress(team_id=team.id, page_id=page.id))
#                 db.session.commit()

#             #next page
#             team.last_key = unlock_code
#             next_page = Page.query.filter(Page.id > page.id).order_by(Page.id).first()
#             team.current_page_id = next_page.id if next_page else None
#             db.session.commit()

#             flash(f"✅ Correct!")
#             return redirect(url_for("page"))
#         else:
#             flash("❌ Incorrect! Try again.")

#     return render_template("page.html", page=page, code_unlocked=code_unlocked, unlock_code=unlock_code)

@app.route("/page", methods=["GET", "POST"])
def page():
    team_name = session.get("team_name")
    if not team_name:
        flash("Please signup or login first!")
        return redirect(url_for("signup"))

    team = Team.query.filter_by(name=team_name).first()
    if not team:
        flash("Team not found!")
        return redirect(url_for("signup"))

    # Check if the team has already completed all pages
    if team.current_page_id is None:
        return render_template("completion.html", team_name=team_name)

    # Get current page
    page = Page.query.get(team.current_page_id)

    if not page:
        # New team: assign first page
        first_page = Page.query.order_by(Page.id).first()
        if first_page:
            team.current_page_id = first_page.id
            db.session.commit()
            page = first_page
        else:
            return render_template("completion.html", team_name=team_name)

    code_unlocked = False
    unlock_code = None

    if request.method == "POST":
        answer = request.form.get("answer", "").strip().lower()

        if answer == page.answer.lower():
            code_unlocked = True
            unlock_code = page.unlock_code

            if not TeamProgress.query.filter_by(team_id=team.id, page_id=page.id).first():
                db.session.add(TeamProgress(team_id=team.id, page_id=page.id))
                db.session.commit()

            # Record the last key
            team.last_key = unlock_code
            
            # Find next page
            next_page = Page.query.filter(Page.id > page.id).order_by(Page.id).first()
            
            if next_page:
                team.current_page_id = next_page.id
            else:
                # No more pages - mark as completed
                team.current_page_id = None
            
            db.session.commit()

            if next_page:
                flash("✅ Correct!")
                return redirect(url_for("page"))
            else:
                # All challenges completed!
                return render_template("completion.html", team_name=team_name)
        else:
            flash("❌ Incorrect! Try again.")

    return render_template("page.html", page=page, code_unlocked=code_unlocked, unlock_code=unlock_code)

@app.route("/leaderboard")
def leaderboard():
    teams = Team.query.all()

    leaderboard_data = []
    for team in teams:
        pages_unlocked = team.progress.count()
        last_progress = team.progress.order_by(TeamProgress.id.desc()).first()
        last_progress_id = last_progress.id if last_progress else 0
        leaderboard_data.append({
            "team_name": team.name,
            "pages_unlocked": pages_unlocked,
            "last_progress": last_progress_id,
            "current_page": team.current_page.title if team.current_page else "Completed"
        })

    leaderboard_data.sort(key=lambda x: (-x["pages_unlocked"], x["last_progress"]))

    return render_template("leaderboard.html", leaderboard=leaderboard_data)


@app.route("/logout")
def logout():
    session.pop("team_name", None)
    flash("Logged out successfully.")
    return redirect(url_for("index"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Admin logged in successfully!")
            return redirect(url_for("admin"))
        else:
            flash("Invalid admin credentials!")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out.")
    return redirect(url_for("index"))

@app.route("/admin")
def admin():
    teams = Team.query.all()
    progress_data = []
    for team in teams:
        unlocked_pages = [tp.page.title for tp in team.progress]
        progress_data.append({
            "name": team.name,
            "last_key": team.last_key,
            "current_page": team.current_page.title if team.current_page else "Completed",
            "unlocked_pages": unlocked_pages
        })
    return render_template("admin.html", progress_data=progress_data)


@app.route("/admin/manage_pages")
def manage_pages():
    pages = Page.query.all()
    return render_template("manage_pages.html", pages=pages)

@app.route("/admin/page/add", methods=["GET", "POST"])
def add_page():
    if request.method == "POST":
        new_page = Page(
            title=request.form["title"],
            #content=request.form["content"],
            question=request.form["question"],
            answer=request.form["answer"],
            unlock_code=request.form["unlock_code"]
        )
        db.session.add(new_page)
        db.session.commit()
        flash("Page added successfully!")
        return redirect(url_for("manage_pages"))
    return render_template("page_form.html", page=None)

@app.route("/admin/page/edit/<int:page_id>", methods=["GET", "POST"])
def edit_page(page_id):
    page = Page.query.get_or_404(page_id)
    if request.method == "POST":
        page.title = request.form["title"]
        #page.content = request.form["content"]
        page.question = request.form["question"]
        page.answer = request.form["answer"]
        page.unlock_code = request.form["unlock_code"]
        db.session.commit()
        flash("Page updated successfully!")
        return redirect(url_for("manage_pages"))
    return render_template("page_form.html", page=page)

@app.route("/admin/page/delete/<int:page_id>")
def delete_page(page_id):
    page = Page.query.get_or_404(page_id)
    db.session.delete(page)
    db.session.commit()
    flash("Page deleted successfully!")
    return redirect(url_for("manage_pages"))

if __name__ == "__main__":
    app.run(debug=True)