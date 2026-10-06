"""허브 '메시지 분석' 탭용 message_index_weekly.json (schema v1) export.

입력: docs/intervention.json(개입 지수), docs/weekly.json(주제 월별 건수·라벨·이벤트). 출력: docs/message_index_weekly.json.
조인 키: 허브 race id 앞자리(NC-SEN → NC) = states 키.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS, STATE = ROOT / "docs", ROOT / "state"

# 주제 군집 → 안정적인 영문 키 (라벨 이름이 바뀌어도 키는 유지)
SLUG = {
    "0": "tariffs_trade", "1": "media_opponents", "2": "iran_war", "3": "courts_nominations",
    "4": "endorsements", "5": "white_house_construction", "6": "crime_immigration",
    "7": "thanks_greetings", "8": "shared_headlines", "9": "gop_legislation",
}
CAUTION = 0.05
N_ANNOTATIONS = 6


def main() -> None:
    iv = json.loads((DOCS / "intervention.json").read_text(encoding="utf-8"))
    wk = json.loads((DOCS / "weekly.json").read_text(encoding="utf-8"))
    rules = json.loads((STATE / "matching_rules.json").read_text(encoding="utf-8"))
    small = iv["small_n"]

    months = wk["months"]
    topics = [{"month": m, **{SLUG[k]: wk["monthly"][k][i] for k in SLUG}} for i, m in enumerate(months)]
    month_total = [sum(wk["monthly"][k][i] for k in SLUG) for i in range(len(months))]

    # 주석: 이벤트 에피소드 중 건수 상위 N개 (사건 이름 없이 주제·건수·비중만)
    ann = []
    for e in sorted(wk["events"]["events"], key=lambda e: -e["count"])[:N_ANNOTATIONS]:
        m = e["peak_week"][:7]
        i = months.index(m)
        k = str(e["cluster"])
        n = wk["monthly"][k][i]
        ann.append({"month": m, "topic": SLUG[k], "n_month": n, "share_month": round(n / month_total[i], 3),
                    "episode_start": e["start"], "episode_end": e["end"], "episode_count": e["count"],
                    "ratio": e["ratio"], "keywords": e["keywords"][:4]})
    ann.sort(key=lambda a: a["month"])

    out = {
        "schema": "message_index_weekly/v1",
        "week": iv["week"],
        "window_weeks": iv["window_weeks"],
        "method_version": iv["method_version"],
        "gazetteer_version": iv["gazetteer_version"],
        "matching_rules_version": rules["version"],
        "labels_version": wk["labels"]["version"],
        "collected": wk["meta"]["collected"],
        "n_posts_total": wk["meta"]["total"],
        "n_posts_analyzed": wk["meta"]["analyzed"],
        "silhouette_cosine": wk["stats"]["overall_silhouette"],
        "site": wk["site"],
        "coverage": {
            "mapped_share": iv["coverage"]["mapped_share"],
            "any_state_share": iv["coverage"].get("any_state_share"),
            "n_endorse_window": iv["coverage"]["n_endorse_window"],
            "n_mapped_battleground": iv["coverage"]["n_mapped_battleground"],
        },
        "small_n": small,
        # attack_share 대신 dem_mention_share: 어조(공격 여부)를 측정하지 않으므로 이름 언급 횟수로만 정의
        "states": {s: {"endorse_share": v["endorse_share"], "dem_mention_share": v["dem_mention_share"],
                       "n_endorse": v["n_endorse"], "n_dem_mention": v["n_dem_mention"],
                       "z_vs_baseline": v["z_vs_baseline"], "rank": v["rank"], "surge": v["surge"],
                       "small_n": small}
                   for s, v in iv["states"].items()},
        "topic_labels": {SLUG[k]: {"ko": v["ko"][0], "en": v["en"][0], "color": v["c"],
                                   "cohesion": wk["stats"]["clusters"][k]["cohesion"],
                                   "caution": wk["stats"]["clusters"][k]["cohesion"] < CAUTION,
                                   "keywords": wk["stats"]["clusters"][k]["keywords"][:5]}
                         for k, v in wk["labels"]["clusters"].items()},
        "topics": topics,
        "annotations": ann,
        "notes": iv["notes"],
    }
    (DOCS / "message_index_weekly.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"message_index_weekly: week {out['week']}, {len(topics)}개월, 주석 {len(ann)}개")
    for a in ann:
        print(" ", a["month"], a["topic"], a["n_month"], a["share_month"])


if __name__ == "__main__":
    main()
