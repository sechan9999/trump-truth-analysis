"""주간 증분 갱신: 새 게시물을 고정 군집에 배정하고 지도 좌표를 이웃 평균으로 배치."""
import hashlib
import json
import sys
from pathlib import Path

import ftfy
import numpy as np
import pandas as pd

from embed import MODEL, normalize

ROOT = Path(__file__).parent
DATA, STATE, DOCS = ROOT / "data", ROOT / "state", ROOT / "docs"
START_MONTH = "2025-01"
KNN = 5


def load_clustered() -> pd.DataFrame:
    return pd.read_json(DATA / "clustered.json", dtype={"id": str})


def bootstrap() -> None:
    STATE.mkdir(exist_ok=True)
    df = load_clustered()
    emb = np.load(DATA / f"emb_{MODEL.split('/')[-1]}.npy")
    if len(emb) != len(df):
        sys.exit("임베딩과 군집 결과 건수 불일치")
    cent = np.stack([emb[df["cluster"] == c].mean(axis=0) for c in range(df["cluster"].max() + 1)])
    cent /= np.linalg.norm(cent, axis=1, keepdims=True)
    np.save(STATE / "centroids.npy", cent.astype(np.float32))
    np.save(STATE / "emb.f16.npy", emb.astype(np.float16))
    bounds = {"x": [float(df.x.min()), float(df.x.max())], "y": [float(df.y.min()), float(df.y.max())]}
    (STATE / "bounds.json").write_text(json.dumps(bounds), encoding="utf-8")
    print(f"bootstrap: {len(df)}건, 군집 {len(cent)}개")


def jitter(pid: str) -> np.ndarray:
    h = hashlib.md5(pid.encode()).digest()
    return (np.frombuffer(h[:2], dtype=np.uint8) / 255.0 - 0.5) * 1.5


def add_new() -> int:
    cl = load_clustered()
    posts = pd.read_json(DATA / "posts.json", dtype={"id": str})
    posts = posts[(posts["kind"] == "text") & ~posts["id"].isin(cl["id"])].copy()
    posts["text"] = posts["text"].map(ftfy.fix_text)
    posts["body"] = posts["text"].map(normalize)
    posts = posts[posts["body"].str.len() >= 20].drop(columns=["media"], errors="ignore")
    if posts.empty:
        return 0

    from sentence_transformers import SentenceTransformer
    emb = SentenceTransformer(MODEL, device="cpu").encode(posts["body"].tolist(), batch_size=64, show_progress_bar=False)
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True).clip(1e-9)
    ref = np.load(STATE / "emb.f16.npy").astype(np.float32)
    cent = np.load(STATE / "centroids.npy")

    posts["cluster"] = (emb @ cent.T).argmax(axis=1)
    nn = np.argsort(-(emb @ ref.T), axis=1)[:, :KNN]
    xy = np.stack([cl[["x", "y"]].to_numpy()[idx].mean(axis=0) for idx in nn])
    xy += np.stack([jitter(i) for i in posts["id"]])
    posts["x"], posts["y"] = xy[:, 0], xy[:, 1]

    out = pd.concat([cl, posts[cl.columns.intersection(posts.columns)]], ignore_index=True)
    out.to_json(DATA / "clustered.json", orient="records", force_ascii=False, date_format="iso")
    np.save(STATE / "emb.f16.npy", np.vstack([ref, emb]).astype(np.float16))
    return len(posts)


def build_site() -> None:
    from labels import top2
    d = load_clustered()
    emb = np.load(STATE / "emb.f16.npy").astype(np.float32)
    s1, c2, s2 = top2(emb, np.load(STATE / "centroids.npy"), d["cluster"].to_numpy())
    d["s1"], d["c2"], d["s2"] = s1.round(2), c2, s2.round(2)
    d["created_at"] = pd.to_datetime(d["created_at"], utc=True)
    d = d.sort_values("created_at").reset_index(drop=True)
    b = json.loads((STATE / "bounds.json").read_text(encoding="utf-8"))
    months = pd.period_range(START_MONTH, d["month"].max(), freq="M").strftime("%Y-%m").tolist()
    mi = {m: i for i, m in enumerate(months)}
    for c in "xy":
        lo, hi = b[c]
        d[c] = (3 + 94 * (d[c] - lo) / (hi - lo)).clip(2, 98).round(1)
    et = d["created_at"].dt.tz_convert("America/New_York").dt.strftime("%Y.%m.%d")
    k = int(d["cluster"].max()) + 1
    counts = {c: [0] * len(months) for c in range(k)}
    for c, m in zip(d["cluster"], d["month"]):
        counts[int(c)][mi[m]] += 1
    meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))
    labels = json.loads((STATE / "labels.json").read_text(encoding="utf-8"))
    stats = json.loads((STATE / "cluster_stats.json").read_text(encoding="utf-8"))
    out = {
        "labels": {"version": labels["version"], "date": labels["date"], "clusters": labels["clusters"]},
        "stats": stats,
        "meta": {"collected": meta["collected_at"][:10], "total": meta["total"], "analyzed": len(d),
                 "last": et.iloc[-1]},
        "months": months,
        "counts": counts,
        "pts": [[x, y, int(c), mi[m]] for x, y, c, m in zip(d["x"], d["y"], d["cluster"], d["month"])],
        "posts": [[t, (s[:220] + "…") if len(s) > 220 else s, i, int(c), float(a), float(b)]
                  for t, s, i, c, a, b in zip(et, d["text"], d["id"], d["c2"], d["s1"], d["s2"])],
    }
    (DOCS / "map_data.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"site: {len(d)}건, {months[0]}~{months[-1]}")


if __name__ == "__main__":
    if "--bootstrap" in sys.argv:
        bootstrap()
    else:
        print(f"신규 {add_new()}건")
    import labels
    labels.main()
    build_site()
