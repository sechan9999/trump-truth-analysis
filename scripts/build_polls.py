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


if __name__ == "__main__":
    yougov()
    apnorc()
