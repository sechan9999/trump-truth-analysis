# 이중 판정(검토자 간 일치도) 안내 / Double-coding instructions

> **상태(2026-10-06):** 300건은 2명이 전체 재검토해 최종 판정에 합의했지만(최종 78.3%), 재검토자 개별 판정이 기록되지 않아 검토자 간 일치도는 아직 측정되지 않았습니다. 이 50건 표본으로 측정할 수 있습니다. 2차 판정은 최종 판정(`final_fits`)과 비교됩니다. / Status: all 300 were re-reviewed by 2 people (final 78.3%), but individual judgments were not recorded, so inter-rater agreement is still unmeasured; this sample can measure it.

라벨 감사(300건)는 검토자 5명이 글을 나눠 1명씩 판정했습니다. 그래서 검토자끼리 기준을 얼마나 같게 적용했는지는 아직 모릅니다. 이 50건을 **처음과 다른 검토자**가 다시 판정해 일치도를 잽니다.

The 300-post label audit was single-coded (5 reviewers, one per post). These 50 posts are re-judged by a **different reviewer** to measure inter-rater agreement.

## 파일
- 판정지: `irr_sample_blind.csv` (50건, 주제당 5건, 순서 섞음)
- 완료 후 저장 이름: `irr_sample_filled.csv` (같은 폴더, UTF-8 CSV)

## 규칙
1. **다른 검토자:** 각 글은 1차 판정을 하지 않은 검토자가 판정합니다. 1차에 누가 어떤 글을 맡았는지 기록을 기준으로 배정해 주세요.
2. **블라인드:** 1차 판정(`audit_results.csv`, GitHub에 공개됨)과 다른 검토자의 판정을 보지 않습니다. 판정 중 서로 상의하지 않습니다.
3. **같은 기준:** "글의 지배적 주제와 라벨이 합리적으로 맞는가?" 맞으면 `Y`, 아니면 `N`. 1차와 같은 루브릭을 씁니다.
4. **칸 채우기:** `reviewer_id`(예: R1~R5), `fits`(Y/N, 빈칸 금지), `note`(선택: `borderline` / `dual-topic` / `unjudgeable`).
5. **다른 칸은 수정하지 않습니다.** 특히 `id`와 `text`.

## 엑셀 사용 시 주의
- `id`는 18자리 숫자라 엑셀이 `1.17E+17`처럼 바꿔 저장할 수 있습니다. 열 형식을 **텍스트**로 두거나, 데이터 가져오기에서 `id` 열을 텍스트로 지정하세요.
- 저장은 **CSV UTF-8(쉼표로 분리)** 형식으로 해 주세요.

## 채점
```bash
python scripts/irr.py score
```
결과는 `state/irr_summary.json`: 일치율, Cohen's κ(부트스트랩 95% 신뢰구간), 1·2차 일치율 비교, 주제별 일치율, 불일치 목록.

50건이라 κ의 신뢰구간이 넓습니다(대략 ±0.2). 결과는 "검토자 간 기준이 대체로 같았는가"를 보는 용도로 씁니다.
