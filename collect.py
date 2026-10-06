"""Truth Social @realDonaldTrump 수집·정제 (출처: CNN 아카이브)."""
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

SRC = "https://ix.cnn.io/data/truth-social/truth_archive.json"
START = "2025-01-20"  # 2기 취임일
OUT = Path(__file__).parent / "data"


def clean(text: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>", "\n", text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def kind(text: str, media: list) -> str:
    if text.startswith("RT @") or text.startswith("RT: "):
        return "retruth"
    if not text and media:
        return "media_only"
    if re.fullmatch(r"https?://\S+", text):
        return "link_only"
    return "text"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    try:
        r = requests.get(SRC, timeout=120)
        r.raise_for_status()
        raw = r.json()
    except (requests.RequestException, ValueError) as e:
        sys.exit(f"수집 실패: {e}")
    (OUT / "raw.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    df = pd.DataFrame(raw)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["created_at"]).drop_duplicates("id")
    df = df[df["created_at"] >= pd.Timestamp(START, tz="UTC")]
    df["text"] = df["content"].map(clean)
    df["media"] = df["media"].apply(lambda m: m if isinstance(m, list) else [])
    df["kind"] = [kind(t, m) for t, m in zip(df["text"], df["media"])]
    df["created_et"] = df["created_at"].dt.tz_convert("America/New_York")
    df["month"] = df["created_et"].dt.strftime("%Y-%m")
    df["hour_et"] = df["created_et"].dt.hour
    df = df.sort_values("created_at")

    cols = ["id", "created_at", "month", "hour_et", "kind", "text", "url", "media",
            "replies_count", "reblogs_count", "favourites_count"]
    df[cols].to_json(OUT / "posts.json", orient="records", force_ascii=False, date_format="iso")
    df[cols].to_csv(OUT / "posts.csv", index=False, encoding="utf-8-sig")

    monthly = df.pivot_table(index="month", columns="kind", values="id", aggfunc="count", fill_value=0)
    monthly["total"] = monthly.sum(axis=1)
    days = df.groupby("month")["created_et"].agg(lambda s: s.dt.date.nunique())
    monthly["daily_avg"] = (monthly["total"] / days).round(2)
    monthly["late_night_pct"] = (df[df["hour_et"] < 5].groupby("month")["id"].count()
                                 .reindex(monthly.index, fill_value=0) / monthly["total"] * 100).round(1)
    monthly.to_csv(OUT / "monthly.csv", encoding="utf-8-sig")

    meta = {
        "source": SRC,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "range": [df["created_at"].min().isoformat(), df["created_at"].max().isoformat()],
        "total": int(len(df)),
        "by_kind": df["kind"].value_counts().to_dict(),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(monthly.to_string())


if __name__ == "__main__":
    main()
