# Trump Truth Social Analysis

[한국어](README.md) · **English**

An analysis of President Trump's second-term (from 2025-01-20) Truth Social posts: posts are embedded, grouped into topic clusters, and tracked over time. It also feeds a descriptive "Message analysis" tab on the [US Election Insight Hub](https://github.com/sechan9999/us-election-insight-hub).

**Site:** https://sechan9999.github.io/trump-truth-analysis/ (Korean/English toggle, `?lang=en`)

This is a count of what gets posted and how often. It does not fact-check posts or judge whether claims are true.

## Data
- Source: [CNN Truth Social archive](https://ix.cnn.io/data/truth-social/truth_archive.json) (updated every 5 minutes)
- As of 2026-10-06: 12,069 posts collected. 6,079 text posts are analyzed; image-only, link-only, ReTruths and posts under 20 characters are excluded.
- Refreshed weekly (see [Weekly update](#weekly-update)).

## Run
```bash
pip install -r requirements.txt
python collect.py           # data/posts.csv, monthly.csv, meta.json
python embed.py 10          # full re-analysis: data/clustered.json, clusters_report.json (default model all-mpnet-base-v2)
python update.py --bootstrap  # freeze centroids / map bounds after a full re-analysis
python update.py            # weekly incremental update (new posts only) + labels.py + events.py + site data
python intervention.py      # battleground intervention index
python scripts/build_polls.py   # voter issue-priority polls from data/polls/raw/
python scripts/export_weekly.py # hub export (message_index_weekly.json)
```

## Method
- Cleaning: strip HTML, repair broken encoding (ftfy), remove sign-offs ("President DJT"), lowercase.
- Embeddings: `sentence-transformers/all-mpnet-base-v2`, then t-SNE (cosine, perplexity 40) for the map and k-means (k = 10) for the clusters.
- Silhouette (cosine, all posts): 0.095. Cluster boundaries are weak. An earlier 3,000-post sample with Euclidean distance gave 0.050; the switch from potion-multilingual-128M (0.030) to mpnet improved this.

## Clusters (k = 10, labels v2)
| # | Topic | Posts | Cohesion |
|---|---|---|---|
| 4 | Endorsements | 974 | 0.30 |
| 7 | Thanks & greetings | 945 | 0.00 * |
| 1 | Media & opponents | 764 | 0.01 * |
| 8 | Shared headlines | 691 | 0.04 * |
| 9 | GOP & legislation | 658 | 0.03 * |
| 0 | Tariffs & trade | 556 | 0.11 |
| 2 | Iran & war diplomacy | 538 | 0.15 |
| 6 | Crime & immigration | 440 | 0.05 * |
| 5 | White House construction | 264 | 0.14 |
| 3 | Courts & nominations | 249 | 0.14 |

\* Cohesion (mean cosine silhouette) under 0.05, flagged "interpret with care" on the site.

Topic names are interpretations based on keywords and central posts, and they follow a descriptive naming rule: a label says what a post is about, never its tone or intent, unless that is measured. v2 renamed "Attacks on media & rivals" to "Media & opponents" for this reason. "Shared headlines" is grouped by format, not by subject.

## Label evidence and quality (`labels.py`)
- `state/labels.json`: label definitions with version and changelog. A readable changelog is in [CHANGELOG.md](CHANGELOG.md).
- `state/cluster_stats.json`: for each cluster, the top 8 c-TF-IDF keywords (BERTopic-style `reduce_frequent_words`, boilerplate removed), the 3 posts closest to the centroid, cohesion (mean cosine silhouette), and the boundary share (posts whose similarity to the next-closest cluster is within 0.03).
- Each post card on the site shows the cosine similarity to its own cluster and to the runner-up. These are similarities, not probabilities.
- `data/audit_sample.csv`: a fixed audit sample (30 posts per cluster, 300 total). The `fits` (Y/N) and `note` columns are for human review; the agreement rate will be published once they are filled in.

## Weekly update
GitHub Actions (`.github/workflows/weekly.yml`) runs every Monday at 00:00 UTC:
1. `collect.py` fetches the latest posts.
2. `update.py` embeds new posts only. Each one is assigned to the nearest frozen centroid (`state/centroids.npy`) and placed on the map at the mean position of its 5 most similar existing posts.
3. `labels.py`, `events.py`, `intervention.py` and `scripts/export_weekly.py` regenerate the derived data.
4. The changes are committed and GitHub Pages is rebuilt.

k-means and t-SNE are **not** re-run each week, so cluster numbers and names stay stable. Frozen centroids agree with the original k-means labels on 97.3% of posts. For a full re-analysis, run `python embed.py 10` and then `python update.py --bootstrap`; cluster numbers can change, so the labels must be reviewed.

## Topic spike events (`events.py`, method v1)
- A week counts as a spike for a topic when its post count is at least the largest of: 2× the baseline, the baseline median + 3×MAD, or 8 posts. The baseline is the median of the previous 12 weeks, excluding weeks already flagged as spikes. Consecutive spike weeks merge into one episode, using the baseline from the episode's first week.
- Each episode lists its distinctive terms (compared with the same topic in other periods) and 2 representative posts linked to the originals. **Episodes are not given event names.**
- Output: `state/events.json`, also included as `events` in `docs/weekly.json`.

## Senate battleground intervention index (`intervention.py`, method v1.1)
A **descriptive context indicator** for the [US Election Insight Hub](https://github.com/sechan9999/us-election-insight-hub). It is not a forecast input.
- Output: `docs/intervention.json` → https://sechan9999.github.io/trump-truth-analysis/intervention.json (weekly)
- Scope: the 12 Senate battlegrounds.
- Gazetteer: `state/gazetteer_senate_2026_v1.json`, kept as received. It lists candidates, aliases, `valid_until` dates for primary losers and withdrawals, and `exclude_aliases`.
- Matching rules: `state/matching_rules.json`.
  - Surname-only aliases are used only if they are on an allowlist; rejected surnames are listed with the reason.
  - Ambiguous full names (e.g. Mike Rogers, who shares a name with a sitting Alabama congressman) count only when the state is named in the same post.
  - Primary losers and withdrawn candidates are not matched after their `valid_until` date.
- Mapping priority: candidate name → full state name → abbreviation (`R-GA`, `, GA`, `(GA)` forms only; ME, OH and IN excluded).
- Endorsement share: endorsement-cluster posts in the last 4 weeks, split across states (12 states sum to 1). A post naming k states counts 1/k for each.
- Democratic-candidate mention share: how often Democratic candidates are named outside the endorsement cluster. Tone is **not** measured, so this is not an "attack" share.
- z-score: compared with 4-week shares from 2025-01-20 to 2026-06-30. If fewer than 20 battleground-mapped posts fall in the window, the result is flagged `small_n` and no `surge` badge is shown.
- Coverage is reported two ways: `mapped_share` (share mapped to a battleground) and `any_state_share` (share naming any of the 50 states).
- Precision audit sample: `data/intervention_audit.csv` (50 posts used in the index; the `correct` column is filled in by hand).
- Limits:
  - Endorsements follow competitive races, so they cannot be read causally.
  - Truth Social is not the electorate.
  - Candidates missing from the gazetteer are not matched by name.
  - House and state-legislature endorsements are counted toward their state.

## Voter issue priorities: message vs. public (`scripts/build_polls.py`)
Every figure is parsed from source files kept in `data/polls/raw/`; nothing is typed in by hand. Details are in [data/polls/README.md](data/polls/README.md).

| File | Source |
|---|---|
| `gallup_mip_monthly.csv` | Gallup "most important problem" (open-ended, US adults), parsed from 4 Gallup topline PDFs. Months that appear in more than one PDF were checked for agreement (0 conflicts). |
| `yougov_economist_mii_weekly.csv`, `_monthly.csv` | YouGov/Economist "most important issue for you" (registered voters), from the official tracker download. CC BY-NC 4.0. |
| `apnorc_priorities.csv` | AP-NORC annual December priorities (up to 5 open-ended mentions, coded). 2024-12 and 2025-12 only; this question is asked once a year. |
| `topic_issue_mapping_v1.csv` | Final topic ↔ issue mapping: 4 pairs compared, 6 topics excluded with reasons. |

Notes on comparing these sources:
- Gallup missing months: 2025-06, 2025-07 and 2026-08 have no data and are not interpolated. 2025-08 has the crime figure only, taken from a Gallup article. 2026-09 is excluded because only a secondary source was found.
- YouGov changed the question format in June 2025, so the May→June change mixes in a method effect.
- YouGov is a single choice (sums to 100%), while AP-NORC allows up to 5 mentions (sums to more than 100%). Compare ranks and trends, not levels.

The hub's "Message vs. public" section shows each mapped pair **without normalization**, each series in its own percentage:
- Trump: share of that month's text posts.
- Gallup: share of respondents naming the problem (mapped categories summed).
- YouGov: share choosing it as their top issue.

It reports only the month in which each series peaked. Rising in the same month is co-occurrence, not evidence of influence in either direction.

## Exports for the hub
| File | Contents |
|---|---|
| [`docs/message_index_weekly.json`](https://sechan9999.github.io/trump-truth-analysis/message_index_weekly.json) | schema `message_index_weekly/v1`: intervention index, monthly topic counts, topic labels and cohesion, spike annotations, `message_vs_public` |
| [`docs/weekly.json`](https://sechan9999.github.io/trump-truth-analysis/weekly.json) | schema `truth-weekly/v1` (~45 KB): labels, cluster stats, monthly and weekly topic counts, spike events. Post text and map coordinates are left out. |
| [`docs/intervention.json`](https://sechan9999.github.io/trump-truth-analysis/intervention.json) | intervention index only |
| `docs/map_data.json` | full map data for this site (~1.7 MB) |

The join key with the hub is the race-id prefix (`NC-SEN` → `NC`).

## Guardrails
- Descriptive only: no causal or predictive statements, and no use as a forecast-model input.
- Speculative readings are labeled "(inferred)".
- Every figure carries its source. Missing data is shown as a gap, never filled in.
