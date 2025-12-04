from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
app.secret_key = "secret-key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///anime_reviews.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------------
# Models
# -------------------------
class Anime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    episodes = db.Column(db.Integer)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(300))

    reviews = db.relationship("Review", backref="anime", cascade="all, delete-orphan")

    @property
    def avg_rating(self):
        if not self.reviews:
            return None
        return sum(r.rating for r in self.reviews) / len(self.reviews)

    @property
    def review_count(self):
        return len(self.reviews)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    spoiler = db.Column(db.Boolean, default=False)
    like_count = db.Column(db.Integer, default=0)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    anime_id = db.Column(db.Integer, db.ForeignKey('anime.id'), nullable=False)


# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    print("### DEPLOY TEST: {{ 나기웅 }} ###")

    return redirect(url_for("anime_list"))


@app.route("/anime")
def anime_list():
    sort = request.args.get("sort", "title")

    animes = Anime.query.all()

    if sort == "title":
        animes.sort(key=lambda a: a.title)
    elif sort == "rating_desc":
        animes.sort(key=lambda a: (a.avg_rating or 0), reverse=True)

    return render_template("anime_list.html", animes=animes, sort=sort)


@app.route("/anime/<int:anime_id>")
def anime_detail(anime_id):
    anime = Anime.query.get_or_404(anime_id)
    sort = request.args.get("sort", "newest")

    query = Review.query.filter_by(anime_id=anime_id)

    if sort == "rating_desc":
        reviews = query.order_by(Review.rating.desc()).all()
    elif sort == "rating_asc":
        reviews = query.order_by(Review.rating.asc()).all()
    elif sort == "likes":
        reviews = query.order_by(Review.like_count.desc()).all()
    else:
        reviews = query.order_by(Review.created_date.desc()).all()

    return render_template("anime_detail.html", anime=anime, reviews=reviews, sort=sort)


@app.route("/anime/<int:anime_id>/review", methods=["POST"])
def add_review(anime_id):
    content = (request.form.get("content") or "").strip()
    rating = int(request.form.get("rating"))
    spoiler = bool(request.form.get("spoiler"))

    if not content:
        flash("리뷰 내용을 입력하세요.")
        return redirect(url_for("anime_detail", anime_id=anime_id))

    if len(content) > 500:
        flash("리뷰는 500자 이내로 작성해주세요.")
        return redirect(url_for("anime_detail", anime_id=anime_id))

    review = Review(
        content=content,
        rating=rating,
        spoiler=spoiler,
        anime_id=anime_id
    )
    db.session.add(review)
    db.session.commit()

    return redirect(url_for("anime_detail", anime_id=anime_id))


@app.route("/anime/<int:anime_id>/review/<int:review_id>/delete", methods=["POST"])
def delete_review(anime_id, review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    return redirect(url_for("anime_detail", anime_id=anime_id))


# AJAX 좋아요 요청
@app.route("/review/<int:review_id>/like", methods=["POST"])
def like_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.like_count += 1
    db.session.commit()
    return jsonify({"likes": review.like_count})


# -------------------------
# Initialize DB
# -------------------------
def init_db():
    db.create_all()

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
