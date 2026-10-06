# Changelog / 변경 이력

Versioned parts of the analysis. Weekly data refreshes (new posts) are not listed; they run every Monday via GitHub Actions.
분석의 버전이 붙은 요소만 기록합니다. 매주 자동으로 새 게시물이 반영되는 데이터 갱신은 따로 적지 않습니다.

## Topic labels / 주제 라벨 (`state/labels.json`)

| Version | Date | Change |
|---|---|---|
| v2 | 2026-10-06 | "언론·정적 공격 / Attacks on media & rivals" → "언론·정적 언급 / Media & opponents". Tone (attack or not) is not measured, so it should not be in the label. Cluster assignments unchanged. 어조를 측정하지 않으므로 라벨에서 '공격'을 뺌. 군집 배정은 그대로 |
| v1 | 2026-10-06 | First names for the 10 clusters of all-mpnet-base-v2 + k-means (k = 10). 10개 군집 첫 명명 |

Naming rule: a label says what a post is about, never its tone or intent, unless that is measured.
명명 원칙: 무엇에 관한 글인지만 적고, 측정 근거 없이 어조·의도를 라벨에 넣지 않는다.

## Clustering / 군집

| Date | Change |
|---|---|
| 2026-10-06 | Embedding model switched from potion-multilingual-128M to all-mpnet-base-v2 (silhouette 0.030 → 0.050 on a 3,000-post Euclidean sample; 0.095 cosine on all posts). Encoding repair, sign-off removal, lowercasing added. 임베딩 모델 교체, 정제 단계 추가 |
| 2026-10-06 | Weekly updates assign new posts to frozen centroids instead of re-running k-means (97.3% agreement with the original labels). 주간 갱신은 고정 중심점에 배정 |

## Battleground intervention index / 경합주 개입 지수 (`intervention.py`)

| Version | Date | Change |
|---|---|---|
| v1.1 | 2026-10-06 | Senate gazetteer v1 adopted (`gazetteer_senate_2026_v1.json`) with matching rules v2: surname-only aliases limited to an allowlist, ambiguous full names (e.g. Mike Rogers) need the state named in the same post, primary losers matched only until `valid_until`. 가제티어 v1 + 매칭 규칙 v2 |
| v1 | 2026-10-06 | First version: 4-week endorsement share across 12 Senate battlegrounds, z vs 2025-01-20–2026-06-30, small-sample flag under 20 posts. "Attack share" defined as Democratic-candidate *mention* share (tone not measured). 첫 버전 |

## Topic spike events / 주제 급증 이벤트 (`events.py`)

| Version | Date | Change |
|---|---|---|
| v1 | 2026-10-06 | Spike = at least max(2× baseline, median + 3×MAD, 8) where the baseline excludes weeks already flagged; consecutive weeks merge into episodes. Episodes are not named. 첫 버전 |

## Topic ↔ issue mapping / 주제-이슈 대응표 (`data/polls/topic_issue_mapping_v1.csv`)

| Version | Date | Change |
|---|---|---|
| v1 | 2026-10-06 | 4 pairs compared (tariffs & trade, crime & immigration, Iran & war, GOP & legislation); 6 topics excluded with reasons. 4쌍 비교, 6개 제외 |

## Poll data / 여론조사 데이터 (`data/polls/`)

| Date | Change |
|---|---|
| 2026-10-06 | Gallup MIP parsed directly from 4 topline PDFs (0 cross-file conflicts). A user-compiled CSV was kept for reference only: rows 2025-01 to 2025-05 were shifted by one column and 2026 "Unifying the country" values were missing. Gallup은 PDF에서 직접 파싱, 사용자 집계본은 참고 보관 |
| 2026-10-06 | YouGov/Economist weekly tracker (2025-01 to 2026-09) and AP-NORC December priorities (2024-12, 2025-12) added. YouGov·AP-NORC 추가 |

## Label audit / 라벨 감사

| Date | Result |
|---|---|
| 2026-10-06 | Labels v2 audited on the fixed 300-post sample: 234/300 fit = 78.0% (Wilson 95% CI 73.0–82.3%). Lowest: Thanks & greetings 53%, GOP & legislation 60%, Media & opponents 70%; highest: Endorsements 100%. 3 posts marked unjudgeable, 12 borderline/dual-topic. Criterion: does the label reasonably match the post's dominant topic. 5 reviewers, same rubric, one reviewer per post (inter-rater agreement not measured). 기준: 지배적 주제와 라벨이 합리적으로 맞는가, 검토자 5명 분담 판정. Results: `data/audit/audit_results.csv`. 라벨 v2 감사 결과 |

| 2026-10-06 | Re-review: 2 reviewers re-checked all 300 and agreed final judgments → **78.3% (235/300, Wilson 95% CI 73.3–82.6%)**. 7 changed (4 N→Y, 3 Y→N); first-pass retention 97.7%, κ 0.93. Inter-rater agreement not measured (individual re-review judgments not recorded). 재검토 후 최종 78.3%, 검토자 간 일치도 미측정 |

## Not yet done / 미완료
- Intervention precision audit: 50-post sample (`data/intervention_audit.csv`) not yet reviewed. 매핑 정밀도 감사 미실시
