# Evaluation Metrics

## 1. Strict Hit@3 (primary)

Metric evaluates whether the system’s Top-3 predicted labels contain at least one exact match to the gold typological annotations for a tale. Gold labels are treated as a set (a tale may have multiple gold types recorded in type_code_1…type_code_4), and a hit is registered if the intersection between the gold set and the Top-3 set is non-empty. Importantly, strict matching preserves the full label identity, i.e., base numbers, lettered subtypes, and asterisk refinements are distinct classes (300 ≠ 300A ≠ 300A*). This metric is reported as the main indicator of classification quality in a recommendation-style setting.

## 2. Parent-Relaxed Hit@3 (hierarchy-aware diagnostic)

Parent-Relaxed Hit@3 is a secondary, hierarchy-aware diagnostic that credits predictions landing in the immediate typological neighborhood of the gold label. Using the parent relations encoded in atu_hierarchy.csv, the gold set is expanded to include each gold label’s direct parent (e.g., parent(300A*) = 300A, parent(300A) = 300). A hit is registered if at least one of the Top-3 predictions matches either a gold label or its direct parent. This metric helps distinguish fine-grained refinement errors (e.g., predicting 300A instead of 300A*) from substantively different misclassifications across unrelated types.

## 3. Root-Relaxed Hit@3 (base-type relaxation)

Root-Relaxed Hit@3 measures whether the model identifies the correct base ATU family, ignoring subtype refinements. Both gold and predicted labels are projected to their numeric base component (e.g., base(300A*) = 300, base(510B) = 510), and a hit is registered if any base number in the Top-3 predictions matches any base number in the gold set. This metric is particularly informative in small or heterogeneous corpora, where supervision for lettered subtypes and asterisk refinements is sparse or inconsistently applied, and it provides an estimate of performance at the level of broader narrative clusters.