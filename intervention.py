"""상원 경합주 12곳 트럼프 개입 지수 v1 → docs/intervention.json (US Election Insight Hub 전달용)."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DATA, STATE, DOCS = ROOT / "data", ROOT / "state", ROOT / "docs"
GAZ = STATE / "gazetteer_2026Q4.json"
ENDORSE = 4  # 지지 선언 군집
WINDOW, MIN_N, Z_BADGE = 4, 20, 2.0
BASELINE = ("2025-01-20", "2026-06-30")  # 선거 국면 이전
METHOD = "v1"
US_STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
             "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
             "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
             "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
             "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
             "West Virginia", "Wisconsin", "Wyoming"]
ANY_STATE = re.compile(r"\b(?:" + "|".join(US_STATES) + r")\b")


def name_re(names: list[str]) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b")


def build_matchers(g: dict):
    m = {}
    for s, v in g["states"].items():
        excl = g["state_name_exclusions"].get(s, [])
        abbr = None if s in g["abbrev_excluded"] else re.compile(rf"(?:\b[RD]-{s}\b|,\s{s}\b|\({s}\))")
        m[s] = {
            "cand": name_re(v["dem"] + v["rep"]),
            "dem": name_re(v["dem"]),
            "name": re.compile(rf"\b{re.escape(v['name'])}\b", re.I),
            "excl": re.compile("|".join(re.escape(x) for x in excl), re.I) if excl else None,
            "abbr": abbr,
        }
    return m


def map_states(text: str, m: dict) -> tuple[list[str], str]:
    """우선순위: 후보명 → 주명 → 약어. 먼저 매칭된 단계에서 중단."""
    hits = [s for s, x in m.items() if x["cand"].search(text)]
    if hits:
        return hits, "candidate"
    for s, x in m.items():
        if x["name"].search(text):
            t = x["excl"].sub("", text) if x["excl"] else text
            if x["name"].search(t):
                hits.append(s)
    if hits:
        return hits, "state_name"
    if not text.isupper():
        hits = [s for s, x in m.items() if x["abbr"] and x["abbr"].search(text)]
    return hits, "abbrev" if hits else "none"


def shares(counts: pd.DataFrame, states: list[str]) -> pd.DataFrame:
    """주차×주 → 4주 이동합 기준 점유율."""
    roll = counts.reindex(columns=states, fill_value=0).rolling(WINDOW, min_periods=WINDOW).sum()
    return roll.div(roll.sum(axis=1).replace(0, np.nan), axis=0)


def main() -> None:
    g = json.loads(GAZ.read_text(encoding="utf-8"))
    states = list(g["states"])
    m = build_matchers(g)
    d = pd.read_json(DATA / "clustered.json", dtype={"id": str})
    d["created_at"] = pd.to_datetime(d["created_at"], utc=True)
    d["week"] = d["created_at"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time
    mapped = d["text"].map(lambda t: map_states(t, m))
    d["states"], d["rule"] = mapped.str[0], mapped.str[1]
    d["dem_hits"] = d["text"].map(lambda t: [s for s, x in m.items() if x["dem"].search(t)])

    weeks = pd.date_range(d["week"].min(), d["week"].max(), freq="7D")
    e = d[d["cluster"] == ENDORSE]
    rows = [(w, s, 1 / len(ss)) for w, ss in zip(e["week"], e["states"]) if ss for s in ss]  # 균등 분할
    E = pd.DataFrame(rows, columns=["week", "state", "w"]).pivot_table(index="week", columns="state", values="w", aggfunc="sum").reindex(weeks, fill_value=0).fillna(0)
    rows = [(w, s, 1 / len(ss)) for w, ss, c in zip(d["week"], d["dem_hits"], d["cluster"]) if ss and c != ENDORSE for s in ss]
    A = pd.DataFrame(rows, columns=["week", "state", "w"]).pivot_table(index="week", columns="state", values="w", aggfunc="sum").reindex(weeks, fill_value=0).fillna(0) if rows else pd.DataFrame(0.0, index=weeks, columns=states)
    E, A = E.reindex(columns=states, fill_value=0), A.reindex(columns=states, fill_value=0)

    sE, sA = shares(E, states), shares(A, states)
    base = sE.loc[BASELINE[0]:BASELINE[1]]
    mu, sd = base.mean(), base.std().replace(0, np.nan)
    last = weeks[-1]
    win = d[(d["week"] > last - pd.Timedelta(weeks=WINDOW)) & (d["cluster"] == ENDORSE)]
    nE, nA = E.iloc[-WINDOW:].sum(), A.iloc[-WINDOW:].sum()
    small = bool(nE.sum() < MIN_N)
    cur = sE.iloc[-1].fillna(0)
    rank = cur.rank(ascending=False, method="min").astype(int)

    out = {
        "week": last.strftime("%Y-%m-%d"),
        "window_weeks": WINDOW,
        "method_version": METHOD,
        "gazetteer_version": g["version"],
        "generated_from": "https://github.com/sechan9999/trump-truth-analysis",
        "coverage": {
            "n_endorse_window": int(len(win)),
            "mapped_share": round(float((win["states"].str.len() > 0).mean()), 3) if len(win) else None,
            "any_state_share": round(float(win["text"].str.contains(ANY_STATE).mean()), 3) if len(win) else None,
            "n_mapped_battleground": round(float(nE.sum()), 2),
            "by_rule": win["rule"].value_counts().to_dict(),
        },
        "small_n": small,
        "states": {
            s: {
                "endorse_share": round(float(cur[s]), 3),
                "dem_mention_share": None if pd.isna(sA.iloc[-1][s]) else round(float(sA.iloc[-1][s]), 3),
                "n_endorse": round(float(nE[s]), 2),
                "n_dem_mention": round(float(nA[s]), 2),
                "z_vs_baseline": None if pd.isna(sd[s]) else round(float((cur[s] - mu[s]) / sd[s]), 2),
                "surge": bool(not pd.isna(sd[s]) and (cur[s] - mu[s]) / sd[s] > Z_BADGE and not small),
                "rank": int(rank[s]),
            } for s in states
        },
        "series": {
            "weeks": [w.strftime("%Y-%m-%d") for w in weeks],
            "endorse_counts": {s: E[s].round(2).tolist() for s in states},
        },
        "notes": {
            "ko": "기술적 맥락 지표이며 예측 모형 입력이 아니다. 지지 선언은 접전주를 따라가는 내생 변수라 인과로 읽을 수 없다. 트루스소셜은 유권자 전체가 아니다. 가제티어에 없는 후보(경선 탈락자 등)는 후보명으로 잡히지 않는다. dem_mention은 민주당 후보 이름 언급 횟수이며 어조(공격 여부)는 측정하지 않는다.",
            "en": "A descriptive context indicator, not a forecast input. Endorsements follow competitive races (endogenous), so no causal reading. Truth Social is not the electorate. Candidates missing from the gazetteer (e.g. primary losers) are not matched by name. dem_mention counts mentions of Democratic candidates by name; tone is not measured.",
        },
    }
    (DOCS / "intervention.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    pool = e[e["states"].str.len() > 0]  # 지수에 쓰인 글만
    audit = pool.sample(n=min(50, len(pool)), random_state=42)
    audit.assign(states=audit["states"].str.join("|"), correct="", note="")[["id", "cluster", "rule", "states", "text", "correct", "note"]] \
        .to_csv(DATA / "intervention_audit.csv", index=False, encoding="utf-8-sig")

    print(f"week {out['week']} · window endorse {len(win)} · mapped {out['coverage']['mapped_share']} · battleground n {nE.sum():.1f} · small_n {small}")
    print(f"전체 지지 선언 {len(e)}건 중 경합주 매핑 {int((e['states'].str.len() > 0).sum())}건, 50개 주 어디든 언급 {int(e['text'].str.contains(ANY_STATE).sum())}건, 규칙별 {e['rule'].value_counts().to_dict()}")
    for s in sorted(states, key=lambda s: rank[s]):
        v = out["states"][s]
        print(s, v["rank"], v["endorse_share"], v["n_endorse"], v["z_vs_baseline"], v["n_dem_mention"])


if __name__ == "__main__":
    main()
