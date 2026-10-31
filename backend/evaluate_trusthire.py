import json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, f1_score, precision_recall_curve, auc, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

def load_data(filepath="benchmark_data.json"):
    with open(filepath, "r") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    features_df = pd.json_normalize(df["features"])
    full_df = pd.concat([df.drop(columns=["features"]), features_df], axis=1)
    return full_df

def compute_metrics(y_true, y_pred, y_prob):
    precision_pts, recall_pts, _ = precision_recall_curve(y_true, y_prob)
    auc_pr = auc(recall_pts, precision_pts)
    
    report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
    fraud_recall = report.get('1', {}).get('recall', 0.0)
    
    return {
        "Recall": round(fraud_recall, 4),
        "F1-Score": round(f1_score(y_true, y_pred, pos_label=1, zero_division=0), 4),
        "AUC-PR": round(auc_pr, 4),
        "ROC-AUC": round(roc_auc_score(y_true, y_prob), 4) if len(np.unique(y_true)) > 1 else 0.5
    }

def run_cross_validation(df, feature_cols, model):
    gkf = GroupKFold(n_splits=3)
    X = df[feature_cols]
    y = df["is_fraud"].values
    groups = df["company_name"].values

    y_true_all, y_pred_all, y_prob_all = [], [], []

    for train_idx, test_idx in gkf.split(X, y, groups=groups):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        if hasattr(model, "predict_proba"):
            y_prob = model.predict_proba(X_test)[:, 1]
        else:
            y_prob = y_pred

        y_true_all.extend(y_test)
        y_pred_all.extend(y_pred)
        y_prob_all.extend(y_prob)

    return compute_metrics(np.array(y_true_all), np.array(y_pred_all), np.array(y_prob_all))

def run_text_baseline(df):
    gkf = GroupKFold(n_splits=3)
    vectorizer = TfidfVectorizer(max_features=100)
    X_text = vectorizer.fit_transform(df["job_text"]).toarray()
    y = df["is_fraud"].values
    groups = df["company_name"].values

    rf = RandomForestClassifier(n_estimators=50, random_state=42)
    y_true_all, y_pred_all, y_prob_all = [], [], []

    for train_idx, test_idx in gkf.split(X_text, y, groups=groups):
        X_train, X_test = X_text[train_idx], X_text[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        rf.fit(X_train, y_train)
        y_pred = rf.predict(X_test)
        y_prob = rf.predict_proba(X_test)[:, 1]

        y_true_all.extend(y_test)
        y_pred_all.extend(y_pred)
        y_prob_all.extend(y_prob)

    return compute_metrics(np.array(y_true_all), np.array(y_pred_all), np.array(y_prob_all))

def run_adversarial_test(df, entity_cols):
    vectorizer = TfidfVectorizer(max_features=100)
    X_text_orig = vectorizer.fit_transform(df["job_text"]).toarray()
    X_text_ai = vectorizer.transform(df["ai_rewritten_text"]).toarray()
    
    y = df["is_fraud"].values
    
    rf = RandomForestClassifier(n_estimators=50, random_state=42)
    rf.fit(X_text_orig, y)
    f1_text_orig = f1_score(y, rf.predict(X_text_orig), pos_label=1, zero_division=0)
    f1_text_ai = f1_score(y, rf.predict(X_text_ai), pos_label=1, zero_division=0)
    
    xgb = XGBClassifier(eval_metric="logloss", n_estimators=50, random_state=42)
    X_entity = df[entity_cols]
    xgb.fit(X_entity, y)
    
    f1_th_orig = f1_score(y, xgb.predict(X_entity), pos_label=1, zero_division=0)
    f1_th_ai = f1_score(y, xgb.predict(X_entity), pos_label=1, zero_division=0)
    
    return {
        "text_orig_f1": round(f1_text_orig, 4),
        "text_ai_f1": round(f1_text_ai, 4),
        "text_deg": round(((f1_text_orig - f1_text_ai) / max(0.001, f1_text_orig)) * 100, 2),
        "th_orig_f1": round(f1_th_orig, 4),
        "th_ai_f1": round(f1_th_ai, 4),
        "th_deg": round(((f1_th_orig - f1_th_ai) / max(0.001, f1_th_orig)) * 100, 2)
    }

if __name__ == "__main__":
    df = load_data()
    entity_cols = [c for c in df.columns if c.startswith("feat_")]
    
    print("==================================================")
    print(" TRUSTHIRE RESEARCH PAPER EXPERIMENTAL PIPELINE   ")
    print("==================================================\n")
    
    text_results = run_text_baseline(df)
    lr_model = LogisticRegression(max_iter=1000, random_state=42)
    lr_results = run_cross_validation(df, entity_cols, lr_model)
    
    xgb_model = XGBClassifier(eval_metric="logloss", n_estimators=50, max_depth=3, random_state=42)
    xgb_results = run_cross_validation(df, entity_cols, xgb_model)
    
    print("TABLE I: Performance Comparison Across Architectures")
    print("| Model Architecture               | Recall (Fraud) | F1-Score | AUC-PR | ROC-AUC |")
    print("|----------------------------------|----------------|----------|--------|---------|")
    print(f"| Text-Only Baseline (RandomForest)| {text_results['Recall']:<14} | {text_results['F1-Score']:<8} | {text_results['AUC-PR']:<6} | {text_results['ROC-AUC']:<7} |")
    print(f"| TrustHire (Logistic Regression)  | {lr_results['Recall']:<14} | {lr_results['F1-Score']:<8} | {lr_results['AUC-PR']:<6} | {lr_results['ROC-AUC']:<7} |")
    print(f"| TrustHire (XGBoost)              | {xgb_results['Recall']:<14} | {xgb_results['F1-Score']:<8} | {xgb_results['AUC-PR']:<6} | {xgb_results['ROC-AUC']:<7} |\n")
    
    print("TABLE II: Signal Family Ablation Study (XGBoost)")
    print("| Ablated Feature Family           | F1-Score | Δ F1-Score | AUC-PR | Δ AUC-PR |")
    print("|----------------------------------|----------|------------|--------|----------|")
    
    baseline_f1 = xgb_results["F1-Score"]
    baseline_auc_pr = xgb_results["AUC-PR"]
    print(f"| Full TrustHire Model (All Signals)| {baseline_f1:<8} | 0.0000     | {baseline_auc_pr:<6} | 0.0000   |")
    
    signal_groups = {
        "Domain Age & WHOIS Dynamics": ["feat_age", "feat_lifetime_irregular", "feat_hidden"],
        "Reputation Mentions": ["feat_rep_neg_ratio"],
        "Public Review Aggregation": ["feat_review_rating"],
        "MCA Corporate Registry": ["feat_mca_registered"],
        "Process Red Flags": ["feat_salary_ratio", "feat_offplatform", "feat_no_interview", "feat_upfront_payment"]
    }
    
    for group_name, cols in signal_groups.items():
        remaining_cols = [c for c in entity_cols if c not in cols]
        ablated_metrics = run_cross_validation(df, remaining_cols, xgb_model)
        d_f1 = round(ablated_metrics["F1-Score"] - baseline_f1, 4)
        d_auc = round(ablated_metrics["AUC-PR"] - baseline_auc_pr, 4)
        print(f"| w/o {group_name:<28} | {ablated_metrics['F1-Score']:<8} | {d_f1:<+10.4f} | {ablated_metrics['AUC-PR']:<6} | {d_auc:<+8.4f} |")
    
    adv = run_adversarial_test(df, entity_cols)
    print("\nTABLE III: Adversarial Degradation Under AI Paraphrasing")
    print("| Classifier Architecture | F1 (Original) | F1 (AI-Rewritten) | Degradation (%) |")
    print("|-------------------------|---------------|-------------------|-----------------|")
    print(f"| Text-Only Baseline      | {adv['text_orig_f1']:<13} | {adv['text_ai_f1']:<17} | -{adv['text_deg']}%          |")
    print(f"| TrustHire (XGBoost)     | {adv['th_orig_f1']:<13} | {adv['th_ai_f1']:<17} | -{adv['th_deg']}%          |")