"""라벨 감사 검토자 간 일치도(IRR): 50건 이중 판정 표본 생성(make)과 채점(score).

make : data/audit/audit_results.csv(1차 판정 300건)에서 주제당 5건 층화 추출 → 순서를 섞은 블라인드 판정지
score: 2차 판정이 채워진 파일과 1차 판정을 비교 → 일치율, Cohen's kappa(부트스트랩 95% CI), 불일치 목록
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "audit"
FIRST = AUDIT / "audit_results.csv"
BLIND = AUDIT / "irr_sample_blind.csv"
FILLED = AUDIT / "irr_sample_filled.csv"
RESULT = ROOT / "state" / "irr_summary.json"
PER_TOPIC, SEED = 5, 2026


def make() -> None:
    first = pd.read_csv(FIRST, encoding="utf-8-sig", dtype={"id": str})
    s = first.groupby("cluster").sample(n=PER_TOPIC, random_state=SEED)
    s = s.sample(frac=1, random_state=SEED).reset_index(drop=True)  # 주제별로 몰리지 않게 섞기
    blind = pd.DataFrame({
        "item": range(1, len(s) + 1),
        "id": s["id"],
        "label": s["label"],
        "label_version": s["label_version"],
        "text": s["text"],
        "reviewer_id": "",  # 2차 검토자 ID (1차 판정자와 달라야 함)
        "fits": "",  # Y / N
        "note": "",  # borderline / dual-topic / unjudgeable (선택)
    })
    blind.to_csv(BLIND, index=False, encoding="utf-8-sig")
    print(f"blind sample: {len(blind)} posts → {BLIND.relative_to(ROOT)}")
    print(s.groupby("label").size().to_string())
    print(f"1차 판정 중 Y: {(s['fits'] == 'Y').sum()}/{len(s)}")


def kappa(a: np.ndarray, b: np.ndarray) -> float:
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in ("Y", "N"))
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def score() -> None:
    first = pd.read_csv(FIRST, encoding="utf-8-sig", dtype={"id": str})[["id", "label", "fits", "note"]]
    second = pd.read_csv(FILLED, encoding="utf-8-sig", dtype={"id": str})
    blind = pd.read_csv(BLIND, encoding="utf-8-sig", dtype={"id": str})
    if set(second["id"]) != set(blind["id"]):
        raise ValueError("2차 판정 파일의 id가 블라인드 표본과 다름")
    bad = second[~second["fits"].isin(["Y", "N"])]
    if len(bad):
        raise ValueError(f"fits가 Y/N이 아닌 행 {len(bad)}개: item {bad['item'].tolist()}")
    m = second.merge(first, on="id", suffixes=("_2", "_1"))
    a, b = m["fits_1"].to_numpy(), m["fits_2"].to_numpy()
    rng = np.random.default_rng(SEED)
    boots = [kappa(a[i], b[i]) for i in (rng.integers(0, len(m), len(m)) for _ in range(5000))]
    boots = [x for x in boots if not np.isnan(x)]
    out = {
        "n": len(m),
        "percent_agreement": round(float((a == b).mean()), 3),
        "cohen_kappa": round(kappa(a, b), 3),
        "kappa_ci95_bootstrap": [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)],
        "first_fit_rate": round(float((a == "Y").mean()), 3),
        "second_fit_rate": round(float((b == "Y").mean()), 3),
        "reviewers_second": sorted(m["reviewer_id"].dropna().astype(str).unique().tolist()),
        "by_topic_agreement": {lab: round(float((g["fits_1"] == g["fits_2"]).mean()), 2) for lab, g in m.groupby("label_1")},
        "disagreements": m.loc[a != b, ["item", "id", "label_1", "fits_1", "fits_2", "note_1", "note_2"]].to_dict("records"),
    }
    RESULT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"agreement {out['percent_agreement']:.0%}, kappa {out['cohen_kappa']} (95% CI {out['kappa_ci95_bootstrap']}), "
          f"fit rate 1st {out['first_fit_rate']:.0%} vs 2nd {out['second_fit_rate']:.0%}, disagreements {len(out['disagreements'])}")


if __name__ == "__main__":
    {"make": make, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "make"]()
