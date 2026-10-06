"""라벨 감사 집계: data/audit/audit_sample_filled_raw.csv(판정) → data/audit/audit_results.csv, state/audit_summary.json.

본문은 공개 표본(data/audit_sample.csv)을 기준으로 유지하고, 판정 파일의 본문과 다른 행은 text_changed로 표시한다.
"""
import json
import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "audit" / "audit_sample_filled_raw.csv"
SAMPLE = ROOT / "data" / "audit_sample.csv"
OUT = ROOT / "data" / "audit" / "audit_results.csv"
SUMMARY = ROOT / "state" / "audit_summary.json"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("\xa0", " ")).strip()


def main() -> None:
    f = pd.read_csv(RAW, encoding="utf-8-sig", dtype={"id": str})
    s = pd.read_csv(SAMPLE, encoding="utf-8-sig", dtype={"id": str})
    if set(f["id"]) != set(s["id"]):
        raise ValueError("판정 파일과 공개 표본의 id가 다름")
    m = s.drop(columns=["fits", "note"]).merge(f[["id", "fits", "note", "text"]].rename(columns={"text": "text_judged"}), on="id")
    if (m["fits"].isna()).any() or not set(m["fits"]) <= {"Y", "N"}:
        raise ValueError("fits는 Y/N만 허용")
    m["text_changed"] = m["text"].map(norm) != m["text_judged"].map(norm)
    m["note"] = m["note"].fillna("")
    m.drop(columns=["text_judged"]).to_csv(OUT, index=False, encoding="utf-8-sig")

    def stats(g: pd.DataFrame) -> dict:
        n, k = len(g), int((g["fits"] == "Y").sum())
        judgeable = g[g["note"] != "unjudgeable"]
        kj = int((judgeable["fits"] == "Y").sum())
        return {"n": n, "fit": k, "fit_rate": round(k / n, 3), "ci95": wilson(k, n),
                "unjudgeable": int((g["note"] == "unjudgeable").sum()),
                "fit_rate_judgeable": round(kj / len(judgeable), 3) if len(judgeable) else None,
                "borderline": int(g["note"].isin(["borderline", "dual-topic"]).sum())}

    out = {"label_version": str(m["label_version"].iloc[0]), "n": len(m), "overall": stats(m),
           "by_cluster": {str(int(c)): {"label": g["label"].iloc[0], **stats(g)} for c, g in m.groupby("cluster")},
           "text_changed_rows": int(m["text_changed"].sum()),
           "criterion": "Does the label reasonably match the post's dominant topic? (Y/N)",
           "criterion_ko": "글의 지배적 주제와 라벨이 합리적으로 맞는가 (Y/N)",
           "reviewers": 5,
           "coding": "single-coded: 5 reviewers split the sample using the same rubric; each post judged by one reviewer; inter-rater agreement not measured",
           "coding_ko": "검토자 5명이 같은 루브릭으로 표본을 나눠 판정(글당 1명). 검토자 간 일치도는 측정하지 않음",
           "method": "300 posts, 30 per cluster, fixed random sample (seed 42). note: borderline, dual-topic, unjudgeable. CI = Wilson 95%."}
    SUMMARY.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    o = out["overall"]
    print(f"overall {o['fit']}/{o['n']} = {o['fit_rate']:.1%} CI {o['ci95']} | 판정 가능분만 {o['fit_rate_judgeable']:.1%} | 본문 변경 {out['text_changed_rows']}행")
    for c, v in sorted(out["by_cluster"].items(), key=lambda x: x[1]["fit_rate"]):
        print(f"  {c} {v['label']}: {v['fit']}/{v['n']} = {v['fit_rate']:.0%} CI {v['ci95']} unjudgeable {v['unjudgeable']} borderline {v['borderline']}")


if __name__ == "__main__":
    main()
