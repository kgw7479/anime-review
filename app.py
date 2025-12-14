import os
from datetime import datetime

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


def create_app():
    app = Flask(__name__)

    # =========================
    # 1) 환경변수(배포) 우선
    # =========================
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # Render Postgres는 보통 DATABASE_URL로 들어옴
    # SQLAlchemy는 postgres:// 대신 postgresql:// 를 선호하는 경우가 있어 prefix 보정
    database_url = os.environ.get("DATABASE_URL", "sqlite:///anime_reviews.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 관리자 키도 코드에 박지 말고 env로
    app.config["ADMIN_KEY"] = os.environ.get("ADMIN_KEY", "my-admin-key")

    return app


app = create_app()
db = SQLAlchemy(app)


# ---------------------------------------------------
#  모델
# ---------------------------------------------------
class Anime(db.Model):
    __tablename__ = "anime"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer)
    episodes = db.Column(db.Integer)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(300))

    reviews = db.relationship(
        "Review",
        backref="anime",
        cascade="all, delete-orphan"
    )

    @property
    def avg_rating(self):
        if not self.reviews:
            return None
        return sum(r.rating for r in self.reviews) / len(self.reviews)

    @property
    def review_count(self):
        return len(self.reviews)


class Review(db.Model):
    __tablename__ = "review"
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)

    spoiler = db.Column(db.Boolean, default=False)
    like_count = db.Column(db.Integer, default=0)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    anime_id = db.Column(db.Integer, db.ForeignKey("anime.id"), nullable=False)


# ---------------------------------------------------
#  라우트
# ---------------------------------------------------
@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.route("/")
def home():
    return redirect(url_for("anime_list"))


@app.route("/anime")
def anime_list():
    q = request.args.get("q", "", type=str)
    genre = request.args.get("genre", "", type=str)
    sort = request.args.get("sort", "title", type=str)
    page = request.args.get("page", 1, type=int)
    per_page = 6

    query = Anime.query
    if q:
        query = query.filter(Anime.title.contains(q))
    if genre:
        query = query.filter(Anime.genre == genre)

    animes_all = query.all()
    all_genres = sorted({a.genre for a in Anime.query.all()})

    if sort == "title":
        animes_all.sort(key=lambda a: a.title)
    elif sort == "title_desc":
        animes_all.sort(key=lambda a: a.title, reverse=True)
    elif sort == "rating_desc":
        animes_all.sort(key=lambda a: (a.avg_rating or 0), reverse=True)
    elif sort == "rating_asc":
        animes_all.sort(key=lambda a: (a.avg_rating or 0))

    total = len(animes_all)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    animes = animes_all[start:end]

    return render_template(
        "anime_list.html",
        animes=animes,
        q=q,
        genre=genre,
        sort=sort,
        genres=all_genres,
        page=page,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )


@app.route("/anime/<int:anime_id>")
def anime_detail(anime_id):
    anime = Anime.query.get_or_404(anime_id)
    sort = request.args.get("sort", "newest")

    reviews_query = Review.query.filter_by(anime_id=anime_id)

    if sort == "rating_desc":
        reviews = reviews_query.order_by(Review.rating.desc()).all()
    elif sort == "rating_asc":
        reviews = reviews_query.order_by(Review.rating.asc()).all()
    elif sort == "likes":
        reviews = reviews_query.order_by(Review.like_count.desc()).all()
    else:
        reviews = reviews_query.order_by(Review.created_date.desc()).all()

    return render_template("anime_detail.html", anime=anime, reviews=reviews, sort=sort)


@app.route("/anime/<int:anime_id>/review", methods=["POST"])
def add_review(anime_id):
    nickname = (request.form.get("nickname") or "").strip()
    password = (request.form.get("password") or "").strip()
    content = (request.form.get("content") or "").strip()
    rating_raw = request.form.get("rating")
    spoiler = bool(request.form.get("spoiler"))

    if not nickname:
        flash("닉네임을 입력해주세요.")
        return redirect(url_for("anime_detail", anime_id=anime_id))
    if not password:
        flash("비밀번호를 입력해주세요. (리뷰 삭제에 사용됩니다)")
        return redirect(url_for("anime_detail", anime_id=anime_id))
    if not content:
        flash("리뷰 내용을 입력해주세요.")
        return redirect(url_for("anime_detail", anime_id=anime_id))
    if len(content) > 500:
        flash("리뷰는 500자 이내로 작성해주세요.")
        return redirect(url_for("anime_detail", anime_id=anime_id))

    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        flash("별점이 올바르지 않습니다.")
        return redirect(url_for("anime_detail", anime_id=anime_id))

    if rating < 1 or rating > 10:
        flash("별점은 1~10 사이로 선택해주세요.")
        return redirect(url_for("anime_detail", anime_id=anime_id))

    # anime 존재 검증
    Anime.query.get_or_404(anime_id)

    review = Review(
        nickname=nickname,
        password_hash=generate_password_hash(password),
        rating=rating,
        content=content,
        spoiler=spoiler,
        anime_id=anime_id,
    )
    db.session.add(review)
    db.session.commit()

    return redirect(url_for("anime_detail", anime_id=anime_id))


@app.route("/anime/<int:anime_id>/review/<int:review_id>/delete", methods=["POST"])
def delete_review(anime_id, review_id):
    review = Review.query.get_or_404(review_id)
    password = (request.form.get("password") or "").strip()

    if not password:
        flash("리뷰를 삭제하려면 비밀번호를 입력해야 합니다.")
        return redirect(url_for("anime_detail", anime_id=anime_id))

    if not check_password_hash(review.password_hash, password):
        flash("비밀번호가 일치하지 않습니다.")
        return redirect(url_for("anime_detail", anime_id=anime_id))

    db.session.delete(review)
    db.session.commit()
    flash("리뷰가 삭제되었습니다.")
    return redirect(url_for("anime_detail", anime_id=anime_id))


@app.route("/review/<int:review_id>/like", methods=["POST"])
def like_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.like_count += 1
    db.session.commit()
    return jsonify({"likes": review.like_count})


# ---------------------------------------------------
#  관리자
# ---------------------------------------------------
def _check_admin():
    key = request.args.get("key") or request.form.get("key")
    if key != app.config["ADMIN_KEY"]:
        abort(403)


@app.route("/admin/anime/new", methods=["GET", "POST"])
def admin_new_anime():
    _check_admin()

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        genre = (request.form.get("genre") or "").strip()
        year = request.form.get("year", type=int)
        episodes = request.form.get("episodes", type=int)
        description = (request.form.get("description") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()

        if not title or not genre:
            flash("제목과 장르는 필수입니다.")
            return redirect(url_for("admin_new_anime", key=app.config["ADMIN_KEY"]))

        anime = Anime(
            title=title,
            genre=genre,
            year=year,
            episodes=episodes,
            description=description,
            image_url=image_url or "images/default.jpg",
        )
        db.session.add(anime)
        db.session.commit()

        flash("새 애니가 등록되었습니다.")
        return redirect(url_for("anime_detail", anime_id=anime.id))

    return render_template("admin_anime_form.html", admin_key=app.config["ADMIN_KEY"])


# ---------------------------------------------------
#  DB 초기화 / 시드
# ---------------------------------------------------
def init_db():
    db.create_all()

    if Anime.query.count() == 0:
        seed = [
            Anime(title="하이큐!!", genre="스포츠", year=2014, episodes=25,
                  description="배구에 모든 것을 거는 영춘고 배구부의 성장기.",
                  image_url="images/haikyuu.jpg"),
            Anime(title="블루록", genre="스포츠", year=2022, episodes=24,
                  description="세계 최고의 스트라이커를 만들기 위한 블루록 프로젝트.",
                  image_url="images/bluelock.jpg"),
            Anime(title="진격의 거인", genre="다크 판타지", year=2013, episodes=25,
                  description="거인에게 잠식된 벽 안의 세계, 인류의 생존 전쟁.",
                  image_url="images/aot.jpg"),
            Anime(title="도쿄 리벤져스", genre="액션", year=2021, episodes=24,
                  description="과거로 돌아가 인생을 다시 쓰려는 한 남자의 갱단 타임리프.",
                  image_url="images/tokyo_revengers.jpg"),
            Anime(title="귀멸의 칼날", genre="판타지", year=2019, episodes=26,
                  description="혈귀가 된 여동생을 인간으로 되돌리기 위한 탄지로의 여정.",
                  image_url="images/demon_slayer.jpg"),
            Anime(title="주술회전", genre="판타지", year=2020, episodes=24,
                  description="저주를 둘러싼 주술사들의 격렬한 싸움.",
                  image_url="images/jjk.jpg"),
        ]
        db.session.bulk_save_objects(seed)
        db.session.commit()


with app.app_context():
    init_db()


if __name__ == "__main__":
    # 로컬 실행용
    app.run(debug=True)
