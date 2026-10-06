"""군집 근거 통계: c-TF-IDF 키워드, 중심 게시물, 응집도, 경계 비율 + 라벨 감사 표본."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from sklearn.metrics import silhouette_samples

from embed import normalize

ROOT = Path(__file__).parent
DATA, STATE = ROOT / "data", ROOT / "state"
N_KW, N_EX, AUDIT_N, SEED = 8, 3, 30, 42
BOUNDARY = 0.03  # 소속 중심 유사도 - 차순위 중심 유사도 < 0.03 → 경계 게시물
GENERIC = {
    "united", "states", "united states", "america", "american", "president", "trump", "donald",
    "donald trump", "president trump", "president donald", "great", "thank", "just", "new", "people",
    "country", "like", "let", "make", "big", "time", "years", "today", "really", "good", "know",
    "going", "want", "said", "says", "did", "way", "world", "total", "complete", "complete total",
}


def top2(emb: np.ndarray, cent: np.ndarray, own: np.ndarray):
    s = emb @ cent.T
    rows = np.arange(len(s))
    s_own = s[rows, own]
    s[rows, own] = -9
    return s_own, s.argmax(axis=1), s.max(axis=1)


def keywords(df: pd.DataFrame) -> dict:
    docs = df.groupby("cluster")["body"].apply(" ".join)
    cv = CountVectorizer(stop_words=list(ENGLISH_STOP_WORDS | GENERIC), ngram_range=(1, 2))
    X = cv.fit_transform(docs).toarray().astype(float)
    tf = np.sqrt(X)  # BERTopic reduce_frequent_words
    tf /= tf.sum(axis=1, keepdims=True)
    ctfidf = tf * np.log(1 + X.sum() / len(X) / X.sum(axis=0))
    terms = cv.get_feature_names_out()
    out = {}
    for row, k in enumerate(docs.index):
        picked: list[str] = []
        for t in terms[ctfidf[row].argsort()[::-1]]:
            toks = set(t.split())
            if any(toks <= set(p.split()) for p in picked):
                continue
            picked = [p for p in picked if not set(p.split()) <= toks]
            picked.append(t)
            if len(picked) == N_KW:
                break
        out[int(k)] = picked
    return out


def main() -> None:
    df = pd.read_json(DATA / "clustered.json", dtype={"id": str})
    emb = np.load(STATE / "emb.f16.npy").astype(np.float32)
    cent = np.load(STATE / "centroids.npy")
    df["body"] = df["text"].map(normalize)
    labels = json.loads((STATE / "labels.json").read_text(encoding="utf-8"))

    df["sil"] = silhouette_samples(emb, df["cluster"], metric="cosine")
    s_own, c2, s2 = top2(emb, cent, df["cluster"].to_numpy())
    df["boundary"] = (s_own - s2) < BOUNDARY
    kw = keywords(df)

    stats = {"overall_silhouette": round(float(df["sil"].mean()), 3), "boundary_threshold": BOUNDARY, "clusters": {}}
    for k, g in df.groupby("cluster"):
        idx = g.index.to_numpy()
        near, seen = [], set()
        for i in idx[np.argsort(-(emb[idx] @ cent[k]))]:
            key = df.at[i, "body"][:120]
            if key not in seen:
                seen.add(key)
                near.append(i)
            if len(near) == N_EX:
                break
        stats["clusters"][int(k)] = {
            "n": int(len(g)),
            "cohesion": round(float(g["sil"].mean()), 3),
            "boundary_share": round(float(g["boundary"].mean()), 3),
            "keywords": kw[int(k)],
            "exemplars": [[df.at[i, "id"], df.at[i, "text"][:160]] for i in near],
        }
    (STATE / "cluster_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"silhouette(cosine) {stats['overall_silhouette']}, 경계 {df['boundary'].mean():.1%}")
    for k, v in sorted(stats["clusters"].items()):
        print(k, labels["clusters"][str(k)]["ko"][0], v["n"], v["cohesion"], v["boundary_share"], ", ".join(v["keywords"]))

    if (DATA / "audit_sample.csv").exists():  # 감사 표본은 고정
        return
    audit = df.groupby("cluster").sample(n=AUDIT_N, random_state=SEED)
    audit = audit.assign(
        label=audit["cluster"].map(lambda k: labels["clusters"][str(k)]["ko"][0]),
        label_version=labels["version"], fits="", note="",
    )[["id", "cluster", "label", "label_version", "text", "fits", "note"]]
    audit.to_csv(DATA / "audit_sample.csv", index=False, encoding="utf-8-sig")



if __name__ == "__main__":
    main()
