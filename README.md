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

## 자동 갱신
GitHub Actions(`.github/workflows/weekly.yml`)가 매주 월요일 09:00(KST) 실행:
1. `collect.py`로 최신 게시물 수집
2. `update.py`로 새 게시물만 임베딩 → 고정 중심점(`state/centroids.npy`)에 배정, 지도 좌표는 가장 비슷한 기존 글 5개의 평균 위치
3. `docs/map_data.json` 갱신 후 커밋 → Pages 재배포

군집 번호와 이름이 바뀌지 않도록 k-means·t-SNE는 다시 돌리지 않는다. 전면 재분석은 `python embed.py 10` 후 `python update.py --bootstrap`.

## 라벨 근거와 품질 (`labels.py`)
- `state/labels.json`: 라벨 정의와 버전·변경 이력. 기술적 명명 원칙(어조·의도는 측정 근거 없이 라벨에 넣지 않음)
- `state/cluster_stats.json`: 군집별 c-TF-IDF 키워드 8개(BERTopic `reduce_frequent_words` 방식, 상투어 제외), 중심 게시물 3개, 응집도(평균 silhouette, 코사인), 경계 비율(차순위 군집과 유사도 차 < 0.03)
- 게시물별 소속·차순위 군집 유사도를 페이지 카드에 표시 (확률이 아닌 코사인 유사도)
- `data/audit_sample.csv`: 라벨 감사용 고정 표본(군집당 30건, 총 300건). `fits`(Y/N)·`note` 칸을 사람이 채운 뒤 일치율을 공개할 예정
