"""Reproduce the notebook's 31-feature logistic regression and save it once."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from model_features import FEATURES


def train(csv_path, output):
    import joblib
    import numpy as np
    import pandas as pd
    import sklearn
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    frame = pd.read_csv(csv_path)
    raw = frame[FEATURES].apply(pd.to_numeric, errors='raise')
    if np.isinf(raw.to_numpy()).any():
        raise ValueError('Training inputs contain infinite values')
    # Preserve the notebook's full-data median fill and original 80/20 split.
    # This reproduces its evaluation; it is not a new leakage-free benchmark.
    medians = raw.median()
    if medians.isna().any():
        raise ValueError('A training feature has no observed values')
    X = raw.fillna(medians)
    y = frame['win_check']
    if set(y.unique()) != {0, 1}:
        raise ValueError('win_check must contain only 0 and 1, with both present')
    X_train, X_test, y_train, y_test = train_test_split(
        X, y.astype(int), test_size=0.2, random_state=42, stratify=y)
    scaler = StandardScaler()
    scaled_train = scaler.fit_transform(X_train)
    model = LogisticRegression(max_iter=1000, solver='lbfgs', C=0.1, random_state=42)
    model.fit(scaled_train, y_train)
    scaled_test = scaler.transform(X_test)
    metrics = {
        'test_accuracy': accuracy_score(y_test, model.predict(scaled_test)),
        'test_auc': roc_auc_score(y_test, model.predict_proba(scaled_test)[:, 1]),
    }
    metadata = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'training_csv_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        'sklearn_version': sklearn.__version__, 'rows': len(frame),
        'train_rows': len(X_train), 'test_rows': len(X_test),
        'training_date_min': str(frame['game_date'].min()),
        'training_date_max': str(frame['game_date'].max()),
        'evaluation': 'Notebook reproduction: random stratified 80/20; full-data median fill',
        **metrics,
    }
    artifact = dict(format_version=1, features=FEATURES, medians=medians,
                    scaler=scaler, model=model, metadata=metadata)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + '.tmp')
    joblib.dump(artifact, temporary)
    temporary.replace(output)
    output.with_suffix('.metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata, indent=2))
    print(f'Saved {output.resolve()}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('model.joblib'))
    args = parser.parse_args()
    try:
        train(args.csv, args.output)
    except Exception as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
