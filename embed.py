"""본문 게시물 임베딩 → t-SNE 2D → k-means 군집."""
import json
import re
import sys
from pathlib import Path

import ftfy
import numpy as np
import pandas as pd
from model2vec import StaticModel
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score

DATA = Path(__file__).parent / "data"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 10
MODEL = sys.argv[2] if len(sys.argv) > 2 else "sentence-transformers/all-mpnet-base-v2"
SEED = 42


SIGNOFF = re.compile(r"(president\s+)?(donald\s+j\.?\s+trump|djt)\s*[!.]*\s*$", re.I)


def normalize(t: str) -> str:
    t = re.sub(r"https?://\S+", "", t)
    t = SIGNOFF.sub("", t.strip()).strip()
    return t.lower()


def main() -> None:
    df = pd.read_json(DATA / "posts.json", dtype={"id": str})
    df = df[df["kind"] == "text"].copy()
    df["text"] = df["text"].map(ftfy.fix_text)
    df["body"] = df["text"].map(normalize)
    df = df[df["body"].str.len() >= 20].reset_index(drop=True)
    print(f"분석 대상 {len(df)}건")

    cache = DATA / f"emb_{MODEL.split('/')[-1]}.npy"
    if cache.exists():
        emb = np.load(cache)
    elif MODEL.startswith("minishlab/"):
        emb = StaticModel.from_pretrained(MODEL).encode(df["body"].tolist(), show_progress_bar=False)
    else:
        from sentence_transformers import SentenceTransformer
        emb = SentenceTransformer(MODEL, device="cpu").encode(df["body"].tolist(), batch_size=64, show_progress_bar=False)
    emb = emb / np.linalg.norm(emb, axis=1, keepdims=True).clip(1e-9)
    np.save(cache, emb)

    for k in range(7, 14):
        lab = KMeans(k, n_init=10, random_state=SEED).fit_predict(emb)
        print(f"k={k} silhouette={silhouette_score(emb, lab, sample_size=3000, random_state=SEED):.4f}")

    df["cluster"] = KMeans(K, n_init=20, random_state=SEED).fit_predict(emb)
    xy = TSNE(2, perplexity=40, init="pca", metric="cosine", random_state=SEED).fit_transform(emb)
    df["x"], df["y"] = xy[:, 0], xy[:, 1]
    df.drop(columns=["media"]).to_json(DATA / "clustered.json", orient="records", force_ascii=False, date_format="iso")

    tf = TfidfVectorizer(stop_words="english", max_features=20000, ngram_range=(1, 2), min_df=3)
    X = tf.fit_transform(df["body"])
    terms = np.array(tf.get_feature_names_out())
    report = {}
    for c in range(K):
        m = (df["cluster"] == c).to_numpy()
        top = terms[np.asarray(X[m].mean(axis=0)).ravel().argsort()[::-1][:15]].tolist()
        samples = df[m].sample(min(6, m.sum()), random_state=SEED)["body"].str[:160].tolist()
        report[c] = {"n": int(m.sum()), "top": top, "samples": samples,
                     "by_month": df[m].groupby("month").size().to_dict()}
        print(f"\n## C{c} ({m.sum()}건) {', '.join(top)}")
        for s in samples:
            print("  -", re.sub(r"\s+", " ", s))
    (DATA / "clusters_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
