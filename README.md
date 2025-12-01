# 🎌 Anime Review

간단한 **Flask 애니 리뷰 웹사이트**입니다.  
좋아하는 애니메이션의 상세 정보와 리뷰를 작성할 수 있습니다.

---

## ⭐ 주요 기능

- 애니 목록 보기
- 이미지와 장르 표시
- 리뷰 작성 및 삭제
- 별점 평균 자동 계산
- 리뷰 정렬 기능 (최신순 / 높은 별점 / 낮은 별점)

---

## 📁 프로젝트 구조

```
anime-review/
│
├── app.py               # Flask 메인 서버 코드
├── requirements.txt     # 필요한 패키지 목록
├── static/
│   └── images/          # 애니 이미지 파일
│       └── *.jpg
└── templates/
    ├── anime_list.html
    └── anime_detail.html
```

---

## 🚀 실행 방법

```bash
# 가상 환경 실행 (Windows)
venv\Scripts\activate

# 서버 실행
python app.py
```

브라우저에서 아래 주소로 접속:

```
http://127.0.0.1:5000
```

---

## 📌 추가 예정 기능

- 전체 검색
- 태그 기반 필터링
- 관리자 페이지
- 반응형 UI 개선

---

Made with ❤️ by 나기웅
