# 유권자 이슈 우선순위 여론조사 (아이디어 2: 메시지 vs 민심)

`python scripts/build_polls.py`로 `raw/` 원본에서 다시 만든다. 숫자는 모두 원본 파일에서 파싱했고 수기 입력은 없다.

| 파일 | 내용 |
|---|---|
| `yougov_economist_mii_weekly.csv` | YouGov/Economist 주간, 2025-01-07 ~ 2026-09-28, 등록 유권자 전체·민주·무당·공화 |
| `yougov_economist_mii_monthly.csv` | 위 주간 값의 월 평균(`n_weeks`, 포함 주 `weeks` 명시) |
| `apnorc_priorities.csv` | AP-NORC 연례 우선순위(자유응답 최대 5개 코딩), 2024-12·2025-12 두 회차, 범주·세부 항목 |
| `issue_crosswalk_draft.csv` | 트럼프 주제 ↔ 여론조사 이슈 대응표 **초안**(확정 전) |
| `raw/` | 원본: YouGov 트래커 엑셀, AP-NORC topline PDF |

## 출처
- YouGov/Economist: "Which of these is the most important issue for you?" — https://yougov.com/en-us/trackers/most-important-issues-facing-the-us (다운로드: 트래커 페이지의 공개 다운로드 엔드포인트). 라이선스 CC BY-NC 4.0, 출처 표시 필요
- AP-NORC 2024-12 (2024-12-05~09, 성인 1,251명, ±3.7%p): https://apnorc.org/wp-content/uploads/2025/01/December-2024-topline_with-open-ends_final.pdf
- AP-NORC 2025-12 (2025-12-04~08, 성인 1,146명, ±4.0%p): https://apnorc.org/wp-content/uploads/2025/12/AP-NORC-December-2025-Topline-with-MIP-FINAL-2.pdf
- Gallup "Most Important Problem"(월간 자유응답): 별도 제공 예정

## 비교 시 주의
- **YouGov 질문 방식 변경(2025년 6월)**: 이전에는 이슈별 중요도를 먼저 묻고 동률 중에서 하나를 고르게 했고, 6월부터는 전체 목록에서 하나를 고른다. `method` 열(`two_step`/`single_list`)로 구분. 5월→6월 변화에는 방식 변경 효과가 섞여 있다
- **YouGov는 단일 선택(합계 100%)**, **AP-NORC는 최대 5개 자유응답(합계 100% 초과)**이라 수치 크기를 직접 비교하지 않는다. 순위·추세만 비교
- **AP-NORC는 연 1회(12월)**뿐이라 월별 시계열이 아니다. 2026-03, 2026-09 topline에도 같은 문항이 없음을 확인
- AP-NORC 2024-12은 이민을 '외교 정책' 범주 안에, 2025-12은 별도 범주로 집계(범주 정의 변경)
- YouGov 'Inflation' 행은 'Inflation/prices'로 대체된 옛 항목이라 제외
