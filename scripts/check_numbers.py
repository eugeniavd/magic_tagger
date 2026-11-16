"""
Check of the figures reported in the DHNB 2026 paper (Table 2 and the confidence check).
Run from the root of the magic_tagger repository:

    python check_numbers.py

Needs: pandas, numpy, scikit-learn. Reads data/processed/train.csv, test.csv and
cv_per_example_best_model_with_bands.csv. Nothing is written or changed.
"""
import ast, re, sys, warnings
from collections import Counter
import numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import KFold
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

warnings.filterwarnings("ignore")
ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
K = 3

def parent(code):
    m = re.match(r"^\s*(\d{1,4})", str(code))
    return m.group(1) if m else ""

def load(name):
    d = pd.read_csv(f"{ROOT}/data/processed/{name}.csv")
    d["labels"] = d["labels"].apply(ast.literal_eval)
    d["parents"] = d["labels"].apply(lambda l: sorted({parent(x) for x in l}))
    for c in ("summary_norm", "text_norm"):
        d[c] = d[c].fillna("").astype(str)
    return d

def build(text=True, desc=True):
    parts = []
    if text:
        parts.append(("char", TfidfVectorizer(analyzer="char", ngram_range=(3, 5), max_features=50000,
                                              sublinear_tf=True, lowercase=False), "text_norm"))
    if desc:
        parts.append(("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), max_features=20000,
                                              sublinear_tf=True, lowercase=False), "summary_norm"))
    clf = OneVsRestClassifier(LogisticRegression(solver="liblinear", max_iter=2000, C=2.0,
                                                 class_weight="balanced", random_state=42))
    return Pipeline([("features", ColumnTransformer(parts)), ("clf", clf)])

def score(proba, classes, gold_labels, gold_parents):
    order = np.argsort(-proba, axis=1)
    cp = np.array([parent(c) for c in classes])
    exact3 = sum(bool(set(g) & set(classes[o[:K]])) for o, g in zip(order, gold_labels))
    parent3 = sum(bool(set(g) & set(cp[o[:K]])) for o, g in zip(order, gold_parents))
    top1 = np.array([cp[o[0]] in set(g) for o, g in zip(order, gold_parents)])
    s1 = proba[np.arange(len(order)), order[:, 0]]
    s2 = proba[np.arange(len(order)), order[:, 1]]
    return exact3, parent3, top1, s1, s1 - s2, order

train, test = load("train"), load("test")
mlb = MultiLabelBinarizer()
Y = mlb.fit_transform(train["labels"])
classes = np.asarray(mlb.classes_)
n = len(test)

print(f"Training tales: {len(train)} | test tales: {n}")
print(f"Label columns in the model: {len(classes)} "
      f"(distinct after merging Cyrillic look-alike letters: "
      f"{len({c.replace('С','C').replace('А','A') for c in classes})})")
print(f"Tales with more than one type: train {sum(len(l) > 1 for l in train.labels)}, "
      f"test {sum(len(l) > 1 for l in test.labels)}")
print(f"Codes in the test set: {len({x for l in test.labels for x in l})}\n")

print(f"{'Method':52s} {'Exact@3':>8s} {'Parent@3':>9s} {'Top-1':>6s} {'CV Parent@3':>12s}")
rows = [("LR, text + description (model in the paper)", True, True, False),
        ("LR, text only", True, False, False),
        ("LR, description only", False, True, False),
        ("LR, text + description, description empty at test", True, True, True)]
kept = {}
for name, use_text, use_desc, blank in rows:
    model = build(use_text, use_desc).fit(train, Y)
    X = test.assign(summary_norm="") if blank else test
    e3, p3, top1, s1, delta, order = score(model.predict_proba(X), classes, test.labels, test.parents)
    cv = 0
    for a, b in KFold(5, shuffle=True, random_state=123).split(train):
        m = build(use_text, use_desc).fit(train.iloc[a], Y[a])
        Xv = train.iloc[b].assign(summary_norm="") if blank else train.iloc[b]
        cv += score(m.predict_proba(Xv), classes, train.labels.iloc[b], train.parents.iloc[b])[1]
    print(f"{name:52s} {e3:>5d}/{n} {p3:>6d}/{n} {int(top1.sum()):>3d}/{n} {cv:>9d}/{len(train)}")
    kept[name] = (top1, s1, delta, order)

# Baseline 1: always suggest the three most frequent parent types of the training set
freq = Counter(p for l in train.parents for p in l)
top3 = [p for p, _ in freq.most_common(3)]
print(f"{'Baseline: three most frequent parent types ' + str(top3):52s} {'-':>8s} "
      f"{sum(bool(set(g) & set(top3)) for g in test.parents):>6d}/{n} "
      f"{sum(top3[0] in g for g in test.parents):>3d}/{n}")

# Baseline 2: nearest-neighbour retrieval over character TF-IDF of the full text
vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), sublinear_tf=True, lowercase=False).fit(train.text_norm)
S = cosine_similarity(vec.transform(test.text_norm), vec.transform(train.text_norm))
e3 = p3 = t1 = 0
for i in range(n):
    codes, pars = [], []
    for j in np.argsort(-S[i]):
        for c in train.labels.iloc[j]:
            if c not in codes: codes.append(c)
        for p in train.parents.iloc[j]:
            if p not in pars: pars.append(p)
        if len(pars) >= K and len(codes) >= K: break
    e3 += bool(set(test.labels.iloc[i]) & set(codes[:K]))
    p3 += bool(set(test.parents.iloc[i]) & set(pars[:K]))
    t1 += pars[0] in test.parents.iloc[i]
print(f"{'Baseline: nearest neighbours, char TF-IDF of text':52s} {e3:>5d}/{n} {p3:>6d}/{n} {t1:>3d}/{n}")

# Confidence rule: high if top score >= 0.38 and margin over the second score >= 0.14
print("\nConfidence rule (top score >= 0.38 and margin >= 0.14)")
cv = pd.read_csv(f"{ROOT}/data/processed/cv_per_example_best_model_with_bands.csv")
hi = (cv.score1 >= 0.38) & (cv.delta >= 0.14)
print(f"  cross-validation on the training set: high {hi.sum()} tales, first suggestion correct in {int(cv.correct1[hi].sum())}; "
      f"other {int((~hi).sum())} tales, correct in {int(cv.correct1[~hi].sum())}")
top1, s1, delta, order = kept["LR, text + description (model in the paper)"]
hi = (s1 >= 0.38) & (delta >= 0.14)
print(f"  test set: high {hi.sum()} tales, correct in {int(top1[hi].sum())}; other {int((~hi).sum())} tales, correct in {int(top1[~hi].sum())}")
top1, s1, delta, order = kept["LR, text + description, description empty at test"]
hi = (s1 >= 0.38) & (delta >= 0.14)
print(f"  test set, description empty: high {hi.sum()} tales")

# Worked example in Section 5.5
i = test.index[test.tale_id == "era_vene_12_592_4"]
if len(i):
    i = test.index.get_loc(i[0])
    for name in ("LR, text + description (model in the paper)", "LR, text + description, description empty at test"):
        top1, s1, delta, order = kept[name]
        print(f"\nExample era_vene_12_592_4 | {name}: top-3 {list(classes[order[i][:K]])}, "
              f"top score {s1[i]:.2f}, second {s1[i]-delta[i]:.2f}")
