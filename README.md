# Anime Review

Flask로 만든 간단한 **애니 리뷰 웹 사이트**입니다.  
내가 좋아하는 작품들을 모아서 별점과 간단한 감상을 남길 수 있고,
각 작품의 평균 별점도 확인할 수 있습니다.

---

## 🧩 주요 기능

- **애니 목록 페이지**
  - 작품 썸네일 이미지
  - 제목, 장르 표시
  - 각 작품의 **평균 별점(★ x.x / 10)** 표시

- **작품 상세 페이지**
  - 작품 썸네일, 제목, 장르
  - 리뷰 작성 (별점 1~10점 + 텍스트)
  - 리뷰 삭제
  - 리뷰 정렬
    - 최신순
    - 별점 높은 순
    - 별점 낮은 순

- **기본 검색 / 필터 (진행 중이면 여기서 계속 확장 가능)**

---

## 🛠 기술 스택

- **Backend**: Python, Flask
- **Database**: SQLite, SQLAlchemy
- **Frontend**: HTML, CSS (간단한 커스텀 스타일)
- **Dev Tools**: VS Code, Git, GitHub

---

## 📁 프로젝트 구조

```text
anime-review/
├── app.py                  # Flask 메인 애플리케이션
├── requirements.txt        # 파이썬 의존성 목록
├── templates/              # HTML 템플릿 (Jinja2)
│   ├── anime_list.html     # 애니 목록 페이지
│   └── anime_detail.html   # 작품 상세 + 리뷰 페이지
├── static/
│   ├── style.css           # 전체 사이트 스타일
│   └── images/             # 각 애니 썸네일 이미지
└── .gitignore              # venv, DB 등 Git에서 제외할 파일들
