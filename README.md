# Trump Truth Social Analysis

**한국어** · [English](README.en.md)

트럼프 대통령 2기(2025-01-20~) 트루스소셜 게시물을 임베딩해 주제 군집으로 나누고 월별 추이를 보는 분석.

## 데이터
- 출처: [CNN Truth Social archive](https://ix.cnn.io/data/truth-social/truth_archive.json) (5분 단위 갱신)
- 2026-10-06 기준 12,069건 수집 → 본문 있는 글 6,079건 분석 (이미지·링크 단독, 리트루스, 20자 미만 제외). 매주 갱신

## 실행
```bash
pip install -r requirements.txt
python collect.py       # data/posts.csv, monthly.csv, meta.json
python embed.py 10      # data/clustered.json, clusters_report.json (기본 모델 all-mpnet-base-v2)
```

## 방법
- 정제: HTML 제거, 깨진 인코딩 복구(ftfy), 서명("President DJT") 제거, 소문자화
- 임베딩 `sentence-transformers/all-mpnet-base-v2` → t-SNE(cosine, perplexity 40) → k-means(k=10)
- silhouette(코사인, 전체) 0.095. 군집 경계는 약함. 이전 표기 0.050은 3,000건 표본·유클리드 거리 값(potion-multilingual-128M 0.030 대비 개선)

## 군집 (k=10)
| # | 이름 (라벨 v2) | 건수 | 응집도 |
|---|---|---|---|
| 4 | 지지 선언 | 974 | 0.30 |
| 7 | 축하·감사 | 945 | 0.00 * |
| 1 | 언론·정적 언급 | 764 | 0.01 * |
| 8 | 기사 헤드라인 공유 | 691 | 0.04 * |
| 9 | 공화당·입법 | 658 | 0.03 * |
| 0 | 관세·무역 | 556 | 0.11 |
| 2 | 이란·전쟁 외교 | 538 | 0.15 |
| 6 | 범죄·이민 단속 | 440 | 0.05 * |
| 5 | 백악관 공사 | 264 | 0.14 |
| 3 | 법원·인사 지명 | 249 | 0.14 |

\* 응집도(평균 silhouette, 코사인) 0.05 미만, 페이지에 '해석 주의' 표시.

군집 이름은 c-TF-IDF 키워드와 중심 게시물을 보고 붙인 해석이며, 기술적 명명 원칙(어조·의도는 측정 근거 없이 라벨에 넣지 않음)을 따른다. v2에서 '언론·정적 공격'을 '언론·정적 언급'으로 바꿨다. '기사 헤드라인 공유'는 형식 기준 군집.

## 페이지
https://sechan9999.github.io/trump-truth-analysis/ (한국어/English 토글, `?lang=en`)

## 자동 갱신
GitHub Actions(`.github/workflows/weekly.yml`)가 매주 월요일 09:00(KST) 실행:
1. `collect.py`로 최신 게시물 수집
2. `update.py`로 새 게시물만 임베딩 → 고정 중심점(`state/centroids.npy`)에 배정(원래 k-means 라벨과 97.3% 일치), 지도 좌표는 가장 비슷한 기존 글 5개의 평균 위치
3. `labels.py`·`events.py`·`intervention.py`·`scripts/export_weekly.py`로 파생 데이터 재생성
4. 커밋 → Pages 재배포

군집 번호와 이름이 바뀌지 않도록 k-means·t-SNE는 다시 돌리지 않는다. 전면 재분석은 `python embed.py 10` 후 `python update.py --bootstrap`.

## 라벨 근거와 품질 (`labels.py`)
- `state/labels.json`: 라벨 정의와 버전·변경 이력. 사람이 읽기 쉬운 변경 이력은 [CHANGELOG.md](CHANGELOG.md). 기술적 명명 원칙(어조·의도는 측정 근거 없이 라벨에 넣지 않음)
- `state/cluster_stats.json`: 군집별 c-TF-IDF 키워드 8개(BERTopic `reduce_frequent_words` 방식, 상투어 제외), 중심 게시물 3개, 응집도(평균 silhouette, 코사인), 경계 비율(차순위 군집과 유사도 차 < 0.03)
- 게시물별 소속·차순위 군집 유사도를 페이지 카드에 표시 (확률이 아닌 코사인 유사도)
- 라벨 감사: 고정 표본 300건(`data/audit_sample.csv`, 군집당 30건)에 대한 Y/N 판정(`data/audit/audit_results.csv`). **전체 일치 78.0% (234/300, Wilson 95% CI 73.0–82.3%)**. 군집별 53%(축하·감사)~100%(지지 선언), 응집도와 군집별 일치율의 순위 상관 0.95(군집 10개, 참고용). 집계: `python scripts/audit_summary.py` → `state/audit_summary.json`. 판정 파일의 본문 4행이 공개 표본과 달라(게시물 수정 추정) `text_changed`로 표시하고 본문은 공개 표본 기준 유지

## 허브용 주간 JSON
`docs/weekly.json` (schema `truth-weekly/v1`, 약 45KB): 라벨·군집 통계·월별/주별 주제 건수·급증 이벤트. 게시물 원문과 좌표는 빼서 [US Election Insight Hub](https://github.com/sechan9999/us-election-insight-hub)의 '트럼프 메시지 분석' 탭이 가볍게 불러온다. → https://sechan9999.github.io/trump-truth-analysis/weekly.json

## 허브 메시지 분석 탭 데이터 (`scripts/export_weekly.py`)
`docs/message_index_weekly.json` (schema `message_index_weekly/v1`): 개입 지수(12개 주) + 월별 주제 건수(`topics`) + 주제 라벨·응집도 + 주석(급증 에피소드 상위 6개, 사건 이름 없음). 허브 `app/us/lib/seed-messages.ts`가 사용. 설계안의 `attack_share`는 어조를 측정하지 않으므로 `dem_mention_share`(민주당 후보 이름 언급)로 정의.

## 주제 급증 이벤트 (`events.py`, method v1)
- 주제별 주간 게시 수가 기준선(이미 급증으로 잡힌 주를 뺀 직전 12주 중앙값)의 2배, 중앙값+3×MAD, 8건 중 가장 큰 값 이상이면 급증. 연속된 주는 시작 주 기준으로 하나의 에피소드
- 에피소드마다 그 기간에 두드러진 키워드(같은 주제의 다른 기간 대비)와 대표 게시물 2건(원문 링크). **사건 이름은 붙이지 않음**
- 출력 `state/events.json` → `docs/weekly.json`의 `events`. 허브 '트럼프 메시지 분석' 탭의 이벤트 타임라인이 사용

## 상원 경합주 개입 지수 (`intervention.py`, method v1)
[US Election Insight Hub](https://github.com/sechan9999/us-election-insight-hub)에 넘기는 **기술적 맥락 지표**. 예측 모형 입력이 아니다.
- 출력: `docs/intervention.json` → https://sechan9999.github.io/trump-truth-analysis/intervention.json (주 1회 갱신)
- 대상: 상원 경합주 12곳. 가제티어 `state/gazetteer_senate_2026_v1.json`(후보·별칭·경선 탈락자 `valid_until`·`exclude_aliases`, 원본 그대로 보관)
- 매칭 규칙 `state/matching_rules.json`: 성 단독 별칭은 allowlist만(거부 사유 기록), 동명이인 전체 이름(Mike Rogers 등)은 같은 글에 주 이름이 있을 때만, 경선 탈락·사퇴 후보는 `valid_until` 이후 글에 매핑 안 함
- 매핑 우선순위: 후보명 → 주 전체 이름 → 약어(`R-GA`, `, GA`, `(GA)` 형태만; ME·OH·IN 제외)
- 지지 점유율: 지지 선언 군집 글의 최근 4주 합 기준, 12개 주 합 = 1. 한 글이 여러 주면 1/k 분할
- 민주당 후보 언급 점유율: 지지 선언 외 군집에서 민주당 후보 이름이 나온 횟수. 어조(공격 여부)는 측정하지 않음
- z: 2025-01-20~2026-06-30 기준 4주 점유율 대비. 창 내 경합주 매핑 20건 미만이면 `small_n`, 이때 `surge` 배지 없음
- 커버리지: `mapped_share`(경합주 매핑 비율)와 `any_state_share`(50개 주 언급 비율)를 함께 보고
- 정밀도 감사 표본: `data/intervention_audit.csv` (지수에 쓰인 글 50건, `correct` 칸 수기 판정)
- 한계: 지지 선언은 접전주를 따라가는 내생 변수(인과 불가), 트루스소셜 ≠ 유권자, 가제티어에 없는 후보는 이름으로 안 잡힘, 하원·주의회 지지 선언도 해당 주로 집계됨

## 유권자 이슈 우선순위: 메시지 vs 민심 (`scripts/build_polls.py`)
숫자는 모두 `data/polls/raw/` 원본에서 파싱(수기 입력 없음). 자세한 내용은 [data/polls/README.md](data/polls/README.md).
- `gallup_mip_monthly.csv`: Gallup '가장 중요한 문제'(자유응답, 성인) — 토플라인 PDF 4개에서 파싱, 겹치는 달 불일치 0건. 2025-06·07, 2026-08 결측(보간 없음), 2025-08 범죄만, 2026-09 제외(2차 출처)
- `yougov_economist_mii_*.csv`: YouGov/Economist '가장 중요한 이슈'(등록 유권자), 공식 트래커 다운로드, CC BY-NC 4.0. 2025-06 문항 방식 변경
- `apnorc_priorities.csv`: AP-NORC 연례 12월 우선순위(최대 5개 자유응답), 2024-12·2025-12
- `topic_issue_mapping_v1.csv`: 확정 대응표(비교 4쌍, 제외 6개 사유 기록)

허브 '메시지 vs 민심' 섹션은 쌍마다 **정규화 없이** 각자 원래 %(트럼프 = 그 달 본문 게시물 중 비중, Gallup = 응답자 중 언급 비율, YouGov = 1순위 선택 비율)로 그리고, 최고치 달만 사실로 적는다. 같은 달 동시 상승은 인과의 근거가 아니다.

## 가드레일
- 기술적 서술만: 인과·예측 문장 금지, 예측 모형 입력으로 사용 금지
- 추측성 해석에는 (추정) 표기
- 모든 수치에 출처, 결측은 빈칸(보간 없음)
