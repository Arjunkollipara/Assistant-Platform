"""
File: backend/ml/services/training_pipeline.py
Purpose: Core tabular training pipeline using scikit-learn/XGBoost with evaluation metrics.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor


SUPPORTED_TASK_TYPES = {"auto", "classification", "regression"}
SUPPORTED_ALGORITHMS = {
    "auto",
    "xgboost",
    "random_forest",
    "logistic_regression",
    "linear_regression",
}


@dataclass
class TrainingArtifacts:
    """
    Container with trained model objects and evaluation outputs.
    """

    pipeline: Pipeline
    task_type: str
    algorithm: str
    feature_columns: list[str]
    metrics: dict[str, float]
    class_labels: list[str]
    label_encoder: LabelEncoder | None
    row_count: int


def train_tabular_model(
    dataframe: pd.DataFrame,
    target_column: str,
    requested_task_type: str,
    algorithm: str,
) -> TrainingArtifacts:
    """
    Train and evaluate a tabular model from an input dataframe.
    """
    if target_column not in dataframe.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset.")

    normalized_task_type = requested_task_type.strip().lower()
    if normalized_task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError(
            "Invalid task_type. Allowed values: auto, classification, regression."
        )

    normalized_algorithm = algorithm.strip().lower()
    if normalized_algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            "Invalid algorithm. Allowed values: auto, xgboost, random_forest, "
            "logistic_regression, linear_regression."
        )

    working_dataframe = dataframe.copy()
    working_dataframe = working_dataframe.drop_duplicates().dropna(how="all")
    if len(working_dataframe) < 3:
        raise ValueError("Dataset is too small. Provide at least 3 non-empty rows.")

    target_series = working_dataframe[target_column]
    feature_dataframe = working_dataframe.drop(columns=[target_column])

    # Normalize string features so categorical encoding is stable.
    for column_name in feature_dataframe.select_dtypes(include=["object"]).columns:
        feature_dataframe[column_name] = (
            feature_dataframe[column_name].astype("string").str.strip()
        )

    resolved_task_type = _resolve_task_type(target_series, normalized_task_type)
    resolved_algorithm = _resolve_algorithm(resolved_task_type, normalized_algorithm)

    if resolved_task_type == "classification":
        return _train_classification_model(
            feature_dataframe=feature_dataframe,
            target_series=target_series,
            algorithm=resolved_algorithm,
        )
    return _train_regression_model(
        feature_dataframe=feature_dataframe,
        target_series=target_series,
        algorithm=resolved_algorithm,
    )


def _resolve_task_type(target_series: pd.Series, requested_task_type: str) -> str:
    """
    Infer task type if set to auto; otherwise return user-selected value.
    """
    if requested_task_type != "auto":
        return requested_task_type

    if pd.api.types.is_bool_dtype(target_series):
        return "classification"

    if pd.api.types.is_numeric_dtype(target_series):
        unique_values = int(target_series.nunique(dropna=True))
        total_rows = int(target_series.notna().sum())
        if unique_values <= min(20, max(2, int(total_rows * 0.2))):
            return "classification"
        return "regression"

    return "classification"


def _resolve_algorithm(task_type: str, algorithm: str) -> str:
    """
    Resolve 'auto' algorithm and validate task-specific compatibility.
    """
    if algorithm == "auto":
        return "xgboost"

    if task_type == "classification" and algorithm == "linear_regression":
        raise ValueError(
            "linear_regression is incompatible with classification tasks."
        )
    if task_type == "regression" and algorithm == "logistic_regression":
        raise ValueError(
            "logistic_regression is incompatible with regression tasks."
        )
    return algorithm


def _build_preprocessor(feature_dataframe: pd.DataFrame) -> ColumnTransformer:
    """
    Build a robust feature preprocessor for mixed numeric/categorical data.
    """
    numeric_features = list(
        feature_dataframe.select_dtypes(include=["number", "bool"]).columns
    )
    categorical_features = [
        column_name
        for column_name in feature_dataframe.columns
        if column_name not in numeric_features
    ]

    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric_features:
        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )
        transformers.append(("numeric", numeric_pipeline, numeric_features))

    if categorical_features:
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "encoder",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical_features))

    if not transformers:
        raise ValueError("No usable feature columns found for training.")

    return ColumnTransformer(transformers=transformers, remainder="drop")


def _build_estimator(task_type: str, algorithm: str):
    """
    Construct estimator object for the selected task/algorithm pair.
    """
    if task_type == "classification":
        if algorithm == "xgboost":
            return XGBClassifier(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                eval_metric="logloss",
            )
        if algorithm == "random_forest":
            return RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                n_jobs=-1,
            )
        return LogisticRegression(max_iter=1000)

    if algorithm == "xgboost":
        return XGBRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            objective="reg:squarederror",
            eval_metric="rmse",
        )
    if algorithm == "random_forest":
        return RandomForestRegressor(
            n_estimators=300,
            random_state=42,
            n_jobs=-1,
        )
    return LinearRegression()


def _train_classification_model(
    feature_dataframe: pd.DataFrame,
    target_series: pd.Series,
    algorithm: str,
) -> TrainingArtifacts:
    """
    Train classification model and return standard classification metrics.
    """
    normalized_target = target_series.astype("string").str.strip()
    valid_rows_mask = normalized_target.notna() & (normalized_target != "")
    features = feature_dataframe.loc[valid_rows_mask].copy()
    labels = normalized_target.loc[valid_rows_mask].astype(str)

    if len(features) < 3:
        raise ValueError("Not enough labeled rows to train a classification model.")
    if labels.nunique() < 2:
        raise ValueError(
            "Classification target must contain at least two distinct classes."
        )

    label_encoder = LabelEncoder()
    encoded_labels = label_encoder.fit_transform(labels)

    preprocessor = _build_preprocessor(features)
    estimator = _build_estimator(task_type="classification", algorithm=algorithm)
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])

    x_train, x_test, y_train, y_test = _train_test_split_with_optional_stratify(
        features=features,
        labels=encoded_labels,
        task_type="classification",
    )

    pipeline.fit(x_train, y_train)
    predicted_labels_encoded = pipeline.predict(x_test)

    y_test_decoded = label_encoder.inverse_transform(y_test.astype(int))
    y_pred_decoded = label_encoder.inverse_transform(
        predicted_labels_encoded.astype(int)
    )

    metrics = {
        "accuracy": float(accuracy_score(y_test_decoded, y_pred_decoded)),
        "precision_weighted": float(
            precision_score(
                y_test_decoded,
                y_pred_decoded,
                average="weighted",
                zero_division=0,
            )
        ),
        "recall_weighted": float(
            recall_score(
                y_test_decoded,
                y_pred_decoded,
                average="weighted",
                zero_division=0,
            )
        ),
        "f1_weighted": float(
            f1_score(
                y_test_decoded,
                y_pred_decoded,
                average="weighted",
                zero_division=0,
            )
        ),
    }

    if hasattr(pipeline, "predict_proba") and len(label_encoder.classes_) == 2:
        try:
            probabilities = pipeline.predict_proba(x_test)[:, 1]
            metrics["roc_auc"] = float(roc_auc_score(y_test, probabilities))
        except ValueError:
            # Binary AUC can fail if test split has only one class; skip gracefully.
            pass

    return TrainingArtifacts(
        pipeline=pipeline,
        task_type="classification",
        algorithm=algorithm,
        feature_columns=list(features.columns),
        metrics=metrics,
        class_labels=label_encoder.classes_.tolist(),
        label_encoder=label_encoder,
        row_count=int(len(features)),
    )


def _train_regression_model(
    feature_dataframe: pd.DataFrame,
    target_series: pd.Series,
    algorithm: str,
) -> TrainingArtifacts:
    """
    Train regression model and return standard regression metrics.
    """
    numeric_target = pd.to_numeric(target_series, errors="coerce")
    valid_rows_mask = numeric_target.notna()
    features = feature_dataframe.loc[valid_rows_mask].copy()
    labels = numeric_target.loc[valid_rows_mask].astype(float)

    if len(features) < 3:
        raise ValueError("Not enough numeric rows to train a regression model.")

    preprocessor = _build_preprocessor(features)
    estimator = _build_estimator(task_type="regression", algorithm=algorithm)
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])

    x_train, x_test, y_train, y_test = _train_test_split_with_optional_stratify(
        features=features,
        labels=labels,
        task_type="regression",
    )

    pipeline.fit(x_train, y_train)
    predicted = pipeline.predict(x_test)

    rmse = float(np.sqrt(mean_squared_error(y_test, predicted)))
    mae = float(mean_absolute_error(y_test, predicted))
    r2 = float(r2_score(y_test, predicted))

    return TrainingArtifacts(
        pipeline=pipeline,
        task_type="regression",
        algorithm=algorithm,
        feature_columns=list(features.columns),
        metrics={"rmse": rmse, "mae": mae, "r2": r2},
        class_labels=[],
        label_encoder=None,
        row_count=int(len(features)),
    )


def _train_test_split_with_optional_stratify(
    features: pd.DataFrame,
    labels,
    task_type: str,
):
    """
    Perform train/test split while avoiding stratification failures on tiny datasets.
    """
    row_count = len(features)
    if row_count <= 4:
        test_size = 0.5
    else:
        test_size = 0.2

    if task_type != "classification":
        return train_test_split(
            features,
            labels,
            test_size=test_size,
            random_state=42,
        )

    unique_labels, counts = np.unique(labels, return_counts=True)
    can_stratify = len(unique_labels) > 1 and int(np.min(counts)) >= 2
    stratify_arg = labels if can_stratify else None

    return train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=42,
        stratify=stratify_arg,
    )

