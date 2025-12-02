from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# -----------------------
#  DB 설정
# -----------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///anime_reviews.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# -----------------------
#  모델 정의
# -----------------------
class Anime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    # static/images/ 안의 경로 (예: "images/haikyuu.jpg")
    image_url = db.Column(db.String(300))

    reviews = db.relationship(
        "Review",
        backref="anime",
        cascade="all, delete-orphan",
    )

    @property
    def avg_rating(self):
        """리뷰들의 평균 별점 (없으면 None)."""
        if not self.reviews:
            return None
        return sum(r.rating for r in self.reviews) / len(self.reviews)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)

    anime_id = db.Column(
        db.Integer,
        db.ForeignKey("anime.id"),
        nullable=False,
    )


# -----------------------
#  라우트
# -----------------------
@app.route("/")
def home():
    # 메인 → 목록으로 리다이렉트
    return redirect(url_for("anime_list"))


@app.route("/anime")
def anime_list():
    # 검색/필터/정렬 파라미터
    q = request.args.get("q", "", type=str)         # 제목 검색
    genre = request.args.get("genre", "", type=str) # 장르 필터
    sort = request.args.get("sort", "title", type=str)

    # 1) 제목이 정확히 같으면 바로 상세 페이지로 이동
    if q:
        exact = Anime.query.filter(Anime.title == q).first()
        if exact:
            return redirect(url_for("anime_detail", anime_id=exact.id))

    # 2) 목록용 쿼리
    query = Anime.query

    if q:
        query = query.filter(Anime.title.contains(q))

    if genre:
        query = query.filter(Anime.genre == genre)

    animes = query.all()

    # 정렬
    if sort == "title":
        animes.sort(key=lambda a: a.title)
    elif sort == "title_desc":
        animes.sort(key=lambda a: a.title, reverse=True)
    elif sort == "rating_desc":
        animes.sort(key=lambda a: (a.avg_rating or 0), reverse=True)
    elif sort == "rating_asc":
        animes.sort(key=lambda a: (a.avg_rating or 0))

    # 화면에 보여줄 장르 목록
    all_genres = sorted({a.genre for a in Anime.query.all()})

    return render_template(
        "anime_list.html",
        animes=animes,
        q=q,
        genre=genre,
        sort=sort,
        genres=all_genres,
    )


@app.route("/anime/<int:anime_id>")
def anime_detail(anime_id):
    anime = Anime.query.get_or_404(anime_id)

    # 리뷰 정렬 기준 (기본: 최신순)
    sort = request.args.get("sort", "newest")

    reviews_query = Review.query.filter_by(anime_id=anime_id)

    if sort == "rating_desc":
        reviews = reviews_query.order_by(Review.rating.desc()).all()
    elif sort == "rating_asc":
        reviews = reviews_query.order_by(Review.rating.asc()).all()
    else:
        # newest
        reviews = reviews_query.order_by(Review.id.desc()).all()

    return render_template(
        "anime_detail.html",
        anime=anime,
        reviews=reviews,
        anime_id=anime_id,
        sort=sort,
    )


@app.route("/anime/<int:anime_id>/review", methods=["POST"])
def add_review(anime_id):
    content = request.form.get("content")
    rating = request.form.get("rating")

    if content and rating:
        new_review = Review(
            anime_id=anime_id,
            rating=int(rating),
            content=content,
        )
        db.session.add(new_review)
        db.session.commit()

    return redirect(url_for("anime_detail", anime_id=anime_id))


@app.route(
    "/anime/<int:anime_id>/review/<int:review_id>/delete",
    methods=["POST"],
)
def delete_review(anime_id, review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()

    return redirect(url_for("anime_detail", anime_id=anime_id))


# -----------------------
#  DB 초기화
# -----------------------
def init_db():
    db.create_all()

    # 1) 애니 데이터가 하나도 없으면 기본 데이터 넣기
    if Anime.query.count() == 0:
        seed = [
            Anime(
                title="하이큐!!",
                genre="스포츠",
                image_url="images/haikyuu.jpg",
            ),
            Anime(
                title="블루록",
                genre="스포츠",
                image_url="images/bluelock.jpg",
            ),
            Anime(
                title="진격의 거인",
                genre="다크 판타지",
                image_url="images/aot.jpg",
            ),
            Anime(
                title="도쿄 리벤져스",
                genre="액션",
                image_url="images/tokyo_revengers.jpg",
            ),
            Anime(
                title="귀멸의 칼날",
                genre="판타지",
                image_url="images/demon_slayer.jpg",
            ),
            Anime(
                title="주술회전",
                genre="판타지",
                image_url="images/jjk.jpg",
            ),
        ]
        db.session.bulk_save_objects(seed)
        db.session.commit()

    # 2) 예전 DB에서 image_url 비어있을 경우 채워주기
    title_to_image = {
        "하이큐!!": "images/haikyuu.jpg",
        "블루록": "images/bluelock.jpg",
        "진격의 거인": "images/aot.jpg",
        "도쿄 리벤져스": "images/tokyo_revengers.jpg",
        "귀멸의 칼날": "images/demon_slayer.jpg",
        "주술회전": "images/jjk.jpg",
    }

    updated = False
    for anime in Anime.query.all():
        if not anime.image_url and anime.title in title_to_image:
            anime.image_url = title_to_image[anime.title]
            updated = True

    if updated:
        db.session.commit()


# -----------------------
#  실행
# -----------------------

# 서버가 시작될 때(로컬, Render 둘 다) DB 초기화 + 시드 데이터 삽입
with app.app_context():
    init_db()

# 로컬에서 python app.py 로 실행할 때만 개발 서버 띄우기
if __name__ == "__main__":
    app.run(debug=True)

