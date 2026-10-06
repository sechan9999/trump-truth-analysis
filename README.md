# Trump Truth Social Analysis

트럼프 대통령 2기(2025-01-20~) 트루스소셜 게시물을 임베딩해 주제 군집으로 나누고 월별 추이를 보는 분석.

## 데이터
- 출처: [CNN Truth Social archive](https://ix.cnn.io/data/truth-social/truth_archive.json) (5분 단위 갱신)
- 수집 2026-10-06 기준 12,068건 → 본문 있는 글 6,078건 분석 (이미지·링크 단독, 리트루스, 20자 미만 제외)

## 실행
```bash
pip install -r requirements.txt
python collect.py       # data/posts.csv, monthly.csv, meta.json
python embed.py 10      # data/clustered.json, clusters_report.json (기본 모델 all-mpnet-base-v2)
```

## 방법
- 정제: HTML 제거, 깨진 인코딩 복구(ftfy), 서명("President DJT") 제거, 소문자화
- 임베딩 `sentence-transformers/all-mpnet-base-v2` → t-SNE(cosine, perplexity 40) → k-means(k=10)
- silhouette 0.050 (potion-multilingual-128M 0.030 대비 개선, 군집 경계는 여전히 약함)

## 군집 (k=10)
| # | 이름 | 건수 |
|---|---|---|
| 4 | 지지 선언 | 974 |
| 7 | 축하·감사 | 945 |
| 1 | 언론·정적 공격 | 764 |
| 8 | 기사 헤드라인 공유 | 691 |
| 9 | 공화당·입법 | 658 |
| 0 | 관세·무역 | 556 |
| 2 | 이란·전쟁 외교 | 538 |
| 6 | 범죄·이민 단속 | 439 |
| 5 | 백악관 공사 | 264 |
| 3 | 법원·인사 지명 | 249 |

군집 이름은 TF-IDF 상위어와 예시 글을 보고 수동으로 붙임.

## 페이지
https://sechan9999.github.io/trump-truth-analysis/ (한국어/English 토글, `?lang=en`)
