"""주제별 주간 급증 에피소드 탐지 → state/events.json (허브 이벤트 주석 타임라인용).

사건 이름은 붙이지 않는다. 각 에피소드는 그 기간에 두드러진 키워드와 대표 게시물(원문 링크)만 제공한다.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

from embed import normalize
from labels import GENERIC

ROOT = Path(__file__).parent
DATA, STATE = ROOT / "data", ROOT / "state"
TRAIL, MIN_COUNT, RATIO, MAD_K = 12, 8, 2.0, 3.0
N_KW, N_EX = 6, 2
METHOD = "v1"


def threshold(hist: np.ndarray) -> tuple[float, float]:
    base = float(np.median(hist))
    mad = float(np.median(np.abs(hist - base))) * 1.4826
    return base, max(base + MAD_K * max(mad, 1.0), RATIO * base, MIN_COUNT)


def episodes(v: np.ndarray) -> list[tuple[int, int, float]]:
    """기준선 = 이미 급증으로 잡힌 주를 뺀 직전 12주. 급증 시작 주의 기준을 고정하고, 넘는 동안 에피소드를 이어간다."""
    out, quiet, i = [], [], 0
    while i < len(v):
        if len(quiet) >= TRAIL:
            base, thr = threshold(v[quiet[-TRAIL:]])
            if v[i] >= thr:
                j = i
                while j + 1 < len(v) and v[j + 1] >= thr:
                    j += 1
                out.append((i, j, base))
                i = j + 1
                continue
        quiet.append(i)
        i += 1
    return out


def distinct_terms(ep: list[str], rest: list[str]) -> list[str]:
    cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | GENERIC), ngram_range=(1, 2), min_df=1)
    X = cv.fit_transform([" ".join(ep), " ".join(rest)]).toarray().astype(float)
    tf = np.sqrt(X) / np.sqrt(X).sum(axis=1, keepdims=True)
    score = tf[0] * np.log(1 + X.sum() / 2 / X.sum(axis=0))
    score[X[0] < 2] = 0  # 에피소드 안에서 2회 이상 나온 말만
    picked: list[str] = []
    for t in cv.get_feature_names_out()[score.argsort()[::-1]]:
        toks = set(t.split())
        if any(toks <= set(p.split()) for p in picked):
            continue
        picked = [p for p in picked if not set(p.split()) <= toks]
        picked.append(t)
        if len(picked) == N_KW:
            break
    return picked


def main() -> None:
    d = pd.read_json(DATA / "clustered.json", dtype={"id": str})
    emb = np.load(STATE / "emb.f16.npy").astype(np.float32)
    d["body"] = d["text"].map(normalize)
    et = pd.to_datetime(d["created_at"], utc=True).dt.tz_convert("America/New_York")
    d["date"] = et.dt.strftime("%Y-%m-%d")
    d["week"] = et.dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time
    weeks = pd.date_range(d["week"].min(), d["week"].max(), freq="7D")
    wc = pd.crosstab(d["week"], d["cluster"]).reindex(index=weeks, fill_value=0)

    events = []
    for k in sorted(d["cluster"].unique()):
        v = wc[k].to_numpy(dtype=float)
        for a, b, base in episodes(v):
            w0, w1 = weeks[a], weeks[b]
            m = (d["cluster"] == k) & (d["week"] >= w0) & (d["week"] <= w1)
            idx = d.index[m].to_numpy()
            rest = d.loc[(d["cluster"] == k) & ~m, "body"].tolist()
            c = emb[idx].mean(axis=0)
            ex, seen = [], set()
            for i in idx[np.argsort(-(emb[idx] @ c))]:
                key = d.at[i, "body"][:120]
                if key in seen:
                    continue
                seen.add(key)
                ex.append([d.at[i, "id"], d.at[i, "date"], d.at[i, "text"][:180]])
                if len(ex) == N_EX:
                    break
            n_weeks = b - a + 1
            events.append({
                "cluster": int(k),
                "start": w0.strftime("%Y-%m-%d"),
                "end": (w1 + pd.Timedelta(days=6)).strftime("%Y-%m-%d"),
                "weeks": n_weeks,
                "peak_week": weeks[a + int(np.argmax(v[a:b + 1]))].strftime("%Y-%m-%d"),
                "count": int(v[a:b + 1].sum()),
                "peak": int(v[a:b + 1].max()),
                "baseline_weekly": round(base, 1),
                "ratio": round(float(v[a:b + 1].mean() / max(base, 1.0)), 1),
                "keywords": distinct_terms(d.loc[m, "body"].tolist(), rest),
                "examples": ex,
            })
    events.sort(key=lambda e: e["start"])
    out = {
        "method_version": METHOD,
        "rule": {"trailing_weeks": TRAIL, "min_count": MIN_COUNT, "ratio": RATIO, "mad_k": MAD_K,
                 "ko": f"주간 게시 수가 직전 {TRAIL}주 중앙값의 {RATIO:g}배, 중앙값+{MAD_K:g}×MAD, {MIN_COUNT}건 중 가장 큰 값 이상인 주. 연속된 주는 시작 시점 기준선으로 하나의 에피소드로 묶음",
                 "en": f"Weeks at or above the largest of {RATIO:g}x the trailing {TRAIL}-week median, median + {MAD_K:g}xMAD, and {MIN_COUNT} posts. Consecutive weeks merge into one episode using the start-week baseline"},
        "events": events,
    }
    (STATE / "events.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"events: {len(events)}건")
    for e in events[-12:]:
        print(e["start"], e["cluster"], e["weeks"], e["count"], e["baseline_weekly"], e["ratio"], ", ".join(e["keywords"]))


if __name__ == "__main__":
    main()
