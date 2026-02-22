import json
import os

import pandas as pd
import redis
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import text

from backend.db.connection import get_engine
from backend.training.features import FEATURES


def load_data(engine) -> pd.DataFrame:

    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM player_session_snapshots WHERE churned IS NOT NULL"))
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def train():

    engine = get_engine()
    df = load_data(engine)

    print(f"  {len(df)} rows — churn rate: {df['churned'].mean():.1%}")

    X = df[FEATURES].astype(float)
    y = df["churned"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    r = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)
    overrides = json.loads(r.get("config:train_params") or "{}")

    params = {
        "n_estimators": 500,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 5,
        "scale_pos_weight": scale_pos_weight,
        "eval_metric": "auc",
        "random_state": 42,
        **overrides,
    }

    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False, early_stopping_rounds=20)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    print(f"  AUC: {auc:.3f} | trees: {model.best_iteration}")

    os.makedirs("models", exist_ok=True)
    model.save_model("models/churn_v1.json")

    importances = dict(zip(FEATURES, model.feature_importances_.tolist()))
    metrics = {"auc": round(auc, 4), "trees": model.best_iteration, "feature_importances": importances}
    with open("models/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"  Saved → models/churn_v1.json + metrics.json")


if __name__ == "__main__":
    train()