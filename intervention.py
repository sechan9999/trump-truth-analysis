"""상원 경합주 12곳 트럼프 개입 지수 v1 → docs/intervention.json (US Election Insight Hub 전달용)."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DATA, STATE, DOCS = ROOT / "data", ROOT / "state", ROOT / "docs"
GAZ = STATE / "gazetteer_senate_2026_v1.json"
RULES = STATE / "matching_rules.json"
ENDORSE = 4  # 지지 선언 군집
WINDOW, MIN_N, Z_BADGE = 4, 20, 2.0
BASELINE = ("2025-01-20", "2026-06-30")  # 선거 국면 이전
METHOD = "v1.1"
US_STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
             "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
             "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
             "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
             "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
             "West Virginia", "Wisconsin", "Wyoming"]
ANY_STATE = re.compile(r"\b(?:" + "|".join(US_STATES) + r")\b")


def load_matchers() -> tuple[dict, list[dict], dict]:
    """가제티어(후보) + 매칭 규칙(별칭 정책·문맥·제외어) → 주명 매처와 후보 매처."""
    g = json.loads(GAZ.read_text(encoding="utf-8"))
    r = json.loads(RULES.read_text(encoding="utf-8"))
    allow = set(r["single_token_allowlist"])
    states, cands = {}, []
    for st, v in g["states"].items():
        excl = r["state_name_exclusions"].get(st, [])
        states[st] = {
            "name": re.compile(rf"\b{re.escape(v['name'])}\b", re.I),
            "excl": re.compile("|".join(re.escape(x) for x in excl), re.I) if excl else None,
            "abbr": None if st in r["abbrev_excluded"] else re.compile(rf"(?:\b[RD]-{st}\b|,\s{st}\b|\({st}\))"),
        }
        for c in v["candidates"]:
            for a in c["aliases"]:
                if " " not in a and a not in allow:
                    continue  # 성 단독 별칭은 allowlist만
                cands.append({
                    "state": st, "name": c["name"], "party": c["party"], "role": c["role"], "alias": a,
                    "re": re.compile(rf"\b{re.escape(a)}\b"),
                    "until": c.get("valid_until"),
                    "ctx": r["context_required"].get(a),
                    "excl": re.compile("|".join(re.escape(x) for x in c.get("exclude_aliases", []))) if c.get("exclude_aliases") else None,
                })
    return g, cands, states


def cand_hits(text: str, date: str, cands: list[dict], states: dict) -> list[dict]:
    out = []
    for c in cands:
        if c["until"] and date > c["until"]:
            continue  # 경선 탈락·사퇴 후 게시물에는 구 후보명 매핑 금지
        t = c["excl"].sub(" ", text) if c["excl"] else text
        if not c["re"].search(t):
            continue
        if c["ctx"] and not states[c["ctx"]]["name"].search(text):
            continue  # 동명이인: 주 이름이 함께 있어야 인정
        out.append(c)
    return out


def map_states(text: str, date: str, cands: list[dict], states: dict) -> tuple[list[str], str]:
    """우선순위: 후보명 → 주명 → 약어. 먼저 매칭된 단계에서 중단."""
    hits = sorted({c["state"] for c in cand_hits(text, date, cands, states)})
    if hits:
        return hits, "candidate"
    for st, x in states.items():
        t = x["excl"].sub(" ", text) if x["excl"] else text
        if x["name"].search(t):
            hits.append(st)
    if hits:
        return hits, "state_name"
    if not text.isupper():
        hits = [st for st, x in states.items() if x["abbr"] and x["abbr"].search(text)]
    return hits, "abbrev" if hits else "none"


def shares(counts: pd.DataFrame, states: list[str]) -> pd.DataFrame:
    """주차×주 → 4주 이동합 기준 점유율."""
    roll = counts.reindex(columns=states, fill_value=0).rolling(WINDOW, min_periods=WINDOW).sum()
    return roll.div(roll.sum(axis=1).replace(0, np.nan), axis=0)


def main() -> None:
    g, cands, smatch = load_matchers()
    states = list(g["states"])
    d = pd.read_json(DATA / "clustered.json", dtype={"id": str})
    d["created_at"] = pd.to_datetime(d["created_at"], utc=True)
    d["week"] = d["created_at"].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time
    d["date"] = d["created_at"].dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d")
    mapped = [map_states(t, dt, cands, smatch) for t, dt in zip(d["text"], d["date"])]
    d["states"], d["rule"] = [x[0] for x in mapped], [x[1] for x in mapped]
    d["dem_hits"] = [sorted({c["state"] for c in cand_hits(t, dt, cands, smatch) if c["party"] in ("D", "DFL")})
                     for t, dt in zip(d["text"], d["date"])]

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
        "gazetteer_version": g["gazetteer_version"],
        "matching_rules_version": json.loads(RULES.read_text(encoding="utf-8"))["version"],
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
