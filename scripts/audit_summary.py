"""라벨 감사 집계 → data/audit/audit_results.csv, state/audit_summary.json.

1차 판정: data/audit/audit_sample_filled_raw.csv (검토자 5명 분담, 글당 1명)
재검토:   data/audit/audit_rereview_raw.xlsx (2명이 300건 전체 재검토, 합의 결과 final_fits)
공개 수치는 최종(final_fits) 기준. 재검토 파일에 두 검토자의 개별 판정이 없어 검토자 간 일치도는 계산하지 않고,
1차 판정 대비 재검토 유지율(일치율·Cohen's kappa)만 보고한다.
본문은 공개 표본(data/audit_sample.csv)을 기준으로 유지하고, 판정 파일 본문과 다른 행은 text_changed로 표시한다.
"""
import json
import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "audit" / "audit_sample_filled_raw.csv"
REREVIEW = ROOT / "data" / "audit" / "audit_rereview_raw.xlsx"
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


def kappa(a: pd.Series, b: pd.Series) -> float:
    po = float((a == b).mean())
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in ("Y", "N"))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else float("nan")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("\xa0", " ")).strip()


def main() -> None:
    f = pd.read_csv(RAW, encoding="utf-8-sig", dtype={"id": str})
    s = pd.read_csv(SAMPLE, encoding="utf-8-sig", dtype={"id": str})
    r = pd.read_excel(REREVIEW, dtype=str)
    for name, d in (("1차 판정", f), ("재검토", r)):
        if set(d["id"]) != set(s["id"]):
            raise ValueError(f"{name} 파일과 공개 표본의 id가 다름")
    if not (r.set_index("id")["fits"] == f.set_index("id")["fits"]).all():
        raise ValueError("재검토 파일의 fits가 1차 판정과 다름")
    m = (s.drop(columns=["fits", "note"])
         .merge(f[["id", "fits", "note", "text"]].rename(columns={"fits": "fits_first", "text": "text_judged"}), on="id")
         .merge(r[["id", "final_fits"]], on="id"))
    for col in ("fits_first", "final_fits"):
        if m[col].isna().any() or not set(m[col]) <= {"Y", "N"}:
            raise ValueError(f"{col}는 Y/N만 허용")
    m["changed_on_rereview"] = m["fits_first"] != m["final_fits"]
    m["text_changed"] = m["text"].map(norm) != m["text_judged"].map(norm)
    m["note"] = m["note"].fillna("")
    m.drop(columns=["text_judged"]).to_csv(OUT, index=False, encoding="utf-8-sig")

    def stats(g: pd.DataFrame, col: str = "final_fits") -> dict:
        n, k = len(g), int((g[col] == "Y").sum())
        judgeable = g[g["note"] != "unjudgeable"]
        kj = int((judgeable[col] == "Y").sum())
        return {"n": n, "fit": k, "fit_rate": round(k / n, 3), "ci95": wilson(k, n),
                "unjudgeable": int((g["note"] == "unjudgeable").sum()),
                "fit_rate_judgeable": round(kj / len(judgeable), 3) if len(judgeable) else None,
                "borderline": int(g["note"].isin(["borderline", "dual-topic"]).sum())}

    ch = m[m["changed_on_rereview"]]
    out = {
        "label_version": str(m["label_version"].iloc[0]), "n": len(m),
        "overall": stats(m),  # published figure: final (re-reviewed) judgments
        "first_pass": stats(m, "fits_first"),
        "by_cluster": {str(int(c)): {"label": g["label"].iloc[0], **stats(g)} for c, g in m.groupby("cluster")},
        "rereview": {
            "reviewers": 2,
            "retention": round(float((~m["changed_on_rereview"]).mean()), 3),
            "retained": int((~m["changed_on_rereview"]).sum()),
            "kappa_first_vs_final": kappa(m["fits_first"], m["final_fits"]),
            "changed": int(len(ch)),
            "n_to_y": int(((ch["fits_first"] == "N") & (ch["final_fits"] == "Y")).sum()),
            "y_to_n": int(((ch["fits_first"] == "Y") & (ch["final_fits"] == "N")).sum()),
        },
        "inter_rater_agreement": None,  # not measurable: individual re-reviewer judgments were not recorded
        "text_changed_rows": int(m["text_changed"].sum()),
        "criterion": "Does the label reasonably match the post's dominant topic? (Y/N)",
        "criterion_ko": "글의 지배적 주제와 라벨이 합리적으로 맞는가 (Y/N)",
        "reviewers": 5,
        "coding": "First pass: 5 reviewers split the sample with the same rubric (one per post). Re-review: 2 reviewers re-checked all 300 and agreed final judgments. Inter-rater agreement not measured (individual re-review judgments not recorded); first-pass-to-final retention reported instead.",
        "coding_ko": "1차: 검토자 5명이 같은 루브릭으로 표본을 나눠 판정(글당 1명). 재검토: 2명이 300건 전체를 다시 보고 최종 판정에 합의. 재검토자 개별 판정이 기록되지 않아 검토자 간 일치도는 측정하지 않았고, 대신 1차 판정 대비 재검토 유지율을 보고함",
        "method": "300 posts, 30 per cluster, fixed random sample (seed 42). note: borderline, dual-topic, unjudgeable. CI = Wilson 95%.",
    }
    SUMMARY.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    o, fp, rr = out["overall"], out["first_pass"], out["rereview"]
    print(f"final {o['fit']}/{o['n']} = {o['fit_rate']:.1%} CI {o['ci95']} (1차 {fp['fit_rate']:.1%}) | "
          f"재검토 유지 {rr['retained']}/{o['n']} = {rr['retention']:.1%}, kappa {rr['kappa_first_vs_final']} | "
          f"변경 {rr['changed']} (N→Y {rr['n_to_y']}, Y→N {rr['y_to_n']}) | 본문 변경 {out['text_changed_rows']}행")
    for c, v in sorted(out["by_cluster"].items(), key=lambda x: x[1]["fit_rate"]):
        print(f"  {c} {v['label']}: {v['fit']}/{v['n']} = {v['fit_rate']:.0%} CI {v['ci95']}")


if __name__ == "__main__":
    main()
