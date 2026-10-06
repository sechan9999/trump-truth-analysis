"""유권자 이슈 우선순위 여론조사 → data/polls/*.csv (아이디어 2 '메시지 vs 민심'용).

원본은 data/polls/raw/에 보관하고, 숫자는 원본에서만 파싱한다(수기 입력 없음).
- YouGov/Economist 'Which of these is the most important issue for you?' (주간, 등록 유권자)
  https://yougov.com/en-us/trackers/most-important-issues-facing-the-us  (CC BY-NC 4.0)
- AP-NORC 'problems ... government to be working on in the year {Y}' (연 1회 12월, 자유응답 최대 5개 코딩)
"""
import re
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
POLLS = ROOT / "data" / "polls"
RAW = POLLS / "raw"
START = "2025-01-01"
METHOD_BREAK = "2025-06-01"  # YouGov: 2025년 6월부터 전체 목록 단일 선택으로 질문 방식 변경

YG_URL = "https://yougov.com/en-us/trackers/most-important-issues-facing-the-us"
YG_GROUPS = {"US Registered Voters": "all_rv", "Democrat": "dem", "Independent": "ind", "Republican": "rep"}
YG_DROP = {"Unweighted base", "Base", "Inflation"}  # 'Inflation'은 'Inflation/prices'로 대체된 옛 항목(전 기간 0)

APN = [
    {"file": "apnorc_2024-12_topline.pdf", "fielded": "2024-12-05/2024-12-09", "target_year": 2025, "n": 1251, "moe": 3.7,
     "url": "https://apnorc.org/wp-content/uploads/2025/01/December-2024-topline_with-open-ends_final.pdf",
     "anchor": "12/5-9/2024"},
    {"file": "apnorc_2025-12_topline.pdf", "fielded": "2025-12-04/2025-12-08", "target_year": 2026, "n": 1146, "moe": 4.0,
     "url": "https://apnorc.org/wp-content/uploads/2025/12/AP-NORC-December-2025-Topline-with-MIP-FINAL-2.pdf",
     "anchor": "12/4-8/2025"},
]
APN_TOP = {"Domestic issues", "The economy", "Foreign policy issues", "Foreign policy issues (not including immigration)",
           "Immigration/border wall/family separation/DACA/ICE", "Healthcare/health issues", "Personal financial issues",
           "Politics"}


def yougov() -> None:
    rows = []
    for sheet, group in YG_GROUPS.items():
        df = pd.read_excel(RAW / "yougov_most_important_issues_us.xlsx", sheet_name=sheet, header=None)
        d = df.iloc[1:].set_index(0)
        d.columns = pd.to_datetime(df.iloc[0, 1:].tolist())
        base = d.loc["Base"]
        d = d.loc[[i for i in d.index if i not in YG_DROP], d.columns >= START]
        for week in d.columns:
            for issue, v in d[week].items():
                if pd.notna(v):
                    rows.append({"week": week.strftime("%Y-%m-%d"), "group": group, "issue": issue,
                                 "share": float(v), "weighted_base": float(base[week])})
    w = pd.DataFrame(rows)
    w["method"] = (w["week"] >= METHOD_BREAK).map({True: "single_list", False: "two_step"})
    w["source"] = "YouGov/Economist"
    w["url"] = YG_URL
    w.to_csv(POLLS / "yougov_economist_mii_weekly.csv", index=False, encoding="utf-8-sig")

    w["month"] = w["week"].str[:7]
    m = (w.groupby(["month", "group", "issue", "method"], as_index=False)
         .agg(share=("share", "mean"), n_weeks=("week", "nunique"), weeks=("week", lambda s: ";".join(sorted(s)))))
    m["share"] = m["share"].round(3)
    m["source"] = "YouGov/Economist"
    m["population"] = "US registered voters"
    m["question"] = "Which of these is the most important issue for you?"
    m["url"] = YG_URL
    m["license"] = "CC BY-NC 4.0 (YouGov public data license)"
    m.to_csv(POLLS / "yougov_economist_mii_monthly.csv", index=False, encoding="utf-8-sig")
    print(f"YouGov: weekly {len(w)} rows, monthly {len(m)} rows, {m['month'].min()}~{m['month'].max()}")


def apnorc_table(text: str, anchor: str) -> list[tuple[str, int, int]]:
    """PROB1 단일 조사 열(anchor 날짜 이후 ~ PROB4 이전)에서 '항목 (N=..) %' 행을 파싱."""
    i = text.index("PROB1.")
    j = text.index(anchor, i)
    k = text.index("PROB4.", j)
    lines = [ln.strip() for ln in text[j + len(anchor):k].splitlines() if ln.strip() and not ln.startswith("===")]
    out, buf = [], ""
    pat = re.compile(r"^(.*?)\s*\(N=([\d,]+)\)\s+(\d+)$")
    idx = 0
    while idx < len(lines):
        ln = lines[idx]
        mt = pat.match(ln)
        if mt:
            out.append(((buf + " " + mt.group(1)).strip(), int(mt.group(2).replace(",", "")), int(mt.group(3))))
            buf = ""
        elif idx + 2 < len(lines) and re.fullmatch(r"\d+", lines[idx + 1]) and re.fullmatch(r"\(N=[\d,]+\)", lines[idx + 2]):
            # 줄바꿈된 행: '라벨' / '%' / '(N=..)'
            out.append(((buf + " " + ln).strip(), int(lines[idx + 2][3:-1].replace(",", "")), int(lines[idx + 1])))
            buf, idx = "", idx + 2
        elif ln.startswith("AP-NORC") or re.fullmatch(r"[\d/\- ]+", ln):
            pass
        else:
            buf = (buf + " " + ln).strip()
        idx += 1
    return out


def apnorc() -> None:
    rows = []
    for s in APN:
        with pdfplumber.open(RAW / s["file"]) as p:
            text = "\n".join(pg.extract_text() or "" for pg in p.pages)
        top = None
        for label, n, pct in apnorc_table(text, s["anchor"]):
            level = "category" if label in APN_TOP else "subcategory"
            if level == "category":
                top = label
            rows.append({"fielded": s["fielded"], "month": s["fielded"][:7], "target_year": s["target_year"],
                         "level": level, "category": top, "item": label, "pct": pct, "n_mentions": n,
                         "n_respondents": s["n"], "moe_pts": s["moe"],
                         "source": "AP-NORC", "population": "US adults who named at least one problem",
                         "question": f"Thinking about the problems facing the United States and the world today, which problems would you like the government to be working on in the year {s['target_year']}? (up to 5, open-ended, coded)",
                         "url": s["url"]})
    a = pd.DataFrame(rows)
    a.to_csv(POLLS / "apnorc_priorities.csv", index=False, encoding="utf-8-sig")
    print(f"AP-NORC: {len(a)} rows, surveys {a['fielded'].unique().tolist()}")


GALLUP = [  # 최신 파일 우선: 같은 달이 여러 PDF에 있으면 값이 같은지 검사
    ("gallup_2026-07_topline.pdf", "https://news.gallup.com/file/poll/713027/2026_07_23_ECI%20and%20MIP%20Topline%20and%20Tabs.pdf", "2026-07"),
    ("gallup_2026-03_topline.pdf", "https://news.gallup.com/file/poll/704288/260326Energy.pdf", "2026-03"),
    ("gallup_2025-05_topline.pdf", "https://news.gallup.com/file/poll/691031/2025_05_01%20Values%20and%20Beliefs%20Topline_PDF.pdf", "2025-05"),
    ("gallup_2025-03_topline.pdf", "https://news.gallup.com/file/poll/659009/2025_04_09%20Energy%20Topline%20and%20Tabs_MIP.pdf", "2025-03"),
]
GALLUP_CAT = {
    "economy_general": "Economy in general", "inflation_high_cost": "High cost of living/Inflation",
    "immigration": "Immigration", "crime_violence": "Crime/Violence",
    "govt_poor_leadership": "The government/Poor leadership",
    "foreign_policy_aid": "Foreign policy/Foreign aid/Focus overseas",
    "international_issues": "International issues, problems", "war_middle_east": "War in the Middle East",
    "wars_nonspecific": "Wars/War (nonspecific)/Fear of war", "unifying_country": "Unifying the country",
}
GALLUP_Q = "What do you think is the most important problem facing this country today? [OPEN-ENDED]"
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
# 토플라인 밖에서 확인한 값: Gallup 2025-09 기사 "rising from 3% in August to 8% in September"
GALLUP_EXTRA = [("2025-08", "crime_violence", 3, "partial",
                 "https://news.gallup.com/poll/695519/mood-subdued-crime-unity-concerns-rise.aspx",
                 "Gallup 2025-09 기사 본문의 8월 비교치. 8월 다른 범주는 미공개")]
GALLUP_MISSING = {
    "2025-06": "MIP 미확보(해당 월 토플라인에 문항 없음, 사용자 조사). 보간 금지",
    "2025-07": "MIP 미확보(해당 월 토플라인에 문항 없음, 사용자 조사). 보간 금지",
    "2026-08": "MIP 미확보(해당 월 토플라인에 문항 없음, 사용자 조사). 보간 금지",
    "2026-09": "제외: USA Today 칼럼 인용 2차 출처뿐이고 Gallup 원본 미확인, 인용 수치도 출처마다 엇갈림",
}


def gallup() -> None:
    vals: dict[tuple[str, str], tuple] = {}
    for fname, url, fielded in GALLUP:
        with pdfplumber.open(RAW / fname) as p:
            t = "\n".join(pg.extract_text() or "" for pg in p.pages)
        m = re.search(r"\n((?:[A-Z][a-z]{2} ){6}[A-Z][a-z]{2})\nRecent Trend: ((?:\d{4} ){6}\d{4})", t)
        months = [f"{y}-{MON[mo]:02d}" for mo, y in zip(m.group(1).split(), m.group(2).split())]
        tail = t[m.end():]
        for key, label in GALLUP_CAT.items():
            mm = re.search(r"\n" + re.escape(label) + r"((?: (?:\d+|\*|-))+)\n", tail)
            if not mm:
                continue
            for mo, v in zip(months, mm.group(1).split()):
                if mo < START[:7] or v == "-":
                    continue
                pct, lt = (0, True) if v == "*" else (int(v), False)
                quality = "primary" if mo == fielded else "trend"
                if (mo, key) in vals:
                    if vals[(mo, key)][0] != pct:
                        raise ValueError(f"Gallup 불일치 {mo} {key}: {vals[(mo, key)][0]} vs {pct} ({fname})")
                    continue
                vals[(mo, key)] = (pct, lt, quality, url, fname)
    fielded_months = {f: (u, n) for n, u, f in GALLUP}
    for (mo, k), v in list(vals.items()):  # 그 달 조사 토플라인이 있으면 primary로 승격
        if mo in fielded_months:
            vals[(mo, k)] = (v[0], v[1], "primary", *fielded_months[mo])
    rows = [{"month": mo, "category": k, "label": GALLUP_CAT[k], "pct": v[0], "lt_half": v[1], "data_quality": v[2],
             "source_url": v[3], "note": f"{v[4]} Recent Trend 표" + (" ('*' = 0.5% 미만, 0으로 기록)" if v[1] else "")}
            for (mo, k), v in vals.items()]
    for mo, k, pct, q, url, note in GALLUP_EXTRA:
        rows.append({"month": mo, "category": k, "label": GALLUP_CAT[k], "pct": pct, "lt_half": False,
                     "data_quality": q, "source_url": url, "note": note})
    for mo, note in GALLUP_MISSING.items():
        rows.append({"month": mo, "category": "", "label": "", "pct": None, "lt_half": False,
                     "data_quality": "excluded" if mo == "2026-09" else "missing", "source_url": "", "note": note})
    g = pd.DataFrame(rows).sort_values(["month", "category"])
    g["question"] = GALLUP_Q
    g["population"] = "US adults"
    g.to_csv(POLLS / "gallup_mip_monthly.csv", index=False, encoding="utf-8-sig")
    got = sorted(g.loc[g["pct"].notna(), "month"].unique())
    print(f"Gallup: {len(g)} rows, 값 있는 달 {len(got)}개 {got[0]}~{got[-1]}")


if __name__ == "__main__":
    yougov()
    apnorc()
    gallup()
