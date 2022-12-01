"""Integration test for the flattened dataset generation."""

# pylint: disable=unused-import, redefined-outer-name

from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd
import pytest

from timeseriesflattener.feature_spec_objects import (
    OutcomeSpec,
    PredictorGroupSpec,
    PredictorSpec,
    TemporalSpec,
)
from timeseriesflattener.flattened_dataset import TimeseriesFlattener
from timeseriesflattener.testing.load_synth_data import (
    load_synth_prediction_times,
    synth_predictor_binary,
    synth_predictor_float,
)
from timeseriesflattener.testing.utils_for_testing import (
    synth_outcome,
    synth_prediction_times,
)

base_float_predictor_combinations = PredictorGroupSpec(
    values_loader=["synth_predictor_float"],
    interval_days=[365, 730],
    resolve_multiple_fn=["mean"],
    fallback=[np.NaN],
    allowed_nan_value_prop=[0.0],
).create_combinations()

base_binary_predictor_combinations = PredictorGroupSpec(
    values_loader=["synth_predictor_binary"],
    interval_days=[365, 730],
    resolve_multiple_fn=["max"],
    fallback=[np.NaN],
    allowed_nan_value_prop=[0.0],
).create_combinations()


def check_dfs_have_same_contents_by_column(df1, df2):
    """Check that two dataframes have the same contents by column.

    Makes debugging much easier, as it generates a diff df which is easy to read.

    Args:
        df1 (pd.DataFrame): First dataframe.
        df2 (pd.DataFrame): Second dataframe.

    Raises:
        AssertionError: If the dataframes don't have the same contents by column.
    """

    cols_to_test = [c for c in df1.columns if "prediction_time_uuid" not in c]

    for col in cols_to_test:
        # Saving to csv rounds floats, so we need to round here too
        # to avoid false negatives. Otherwise, it thinks the .csv
        # file has different values from the generated_df, simply because
        # generated_df has more decimal places.
        for df in (df1, df2):
            if df[col].dtype not in (np.dtype("O"), np.dtype("<M8[ns]")):
                df[col] = df[col].round(4)

        merged_df = df1.merge(
            df2,
            indicator=True,
            how="outer",
            on=[col, "prediction_time_uuid"],
            suffixes=("_first", "_cache"),
        )

        # Get diff rows
        diff_rows = merged_df[merged_df["_merge"] != "both"]

        # Sort rows and columns for easier comparison
        diff_rows = diff_rows.sort_index(axis=1)
        diff_rows = diff_rows.sort_values(by=[col, "prediction_time_uuid"])

        # Set display options
        pd.options.display.width = 0

        assert len(diff_rows) == 0


def create_flattened_df(
    cache_dir: Path,
    predictor_specs: list[PredictorSpec],
    prediction_times_df: pd.DataFrame,
):
    """Create a dataset df for testing."""
    flat_ds = TimeseriesFlattener(
        prediction_times_df=prediction_times_df,
        n_workers=1,
        feature_cache_dir=cache_dir,
    )

    flat_ds.add_temporal_predictors_from_pred_specs(
        predictor_specs=predictor_specs,
    )

    return flat_ds._df


@pytest.mark.parametrize(
    "predictor_specs",
    [base_float_predictor_combinations, base_binary_predictor_combinations],
)
def test_cache_hitting(
    tmp_path,
    synth_prediction_times,
    predictor_specs,
):
    """Test that cache hits."""

    # Create the cache
    first_df = create_flattened_df(
        cache_dir=tmp_path,
        predictor_specs=predictor_specs.copy(),
        prediction_times_df=synth_prediction_times,
    )

    # Load the cache
    cache_df = create_flattened_df(
        cache_dir=tmp_path,
        predictor_specs=predictor_specs.copy(),
        prediction_times_df=synth_prediction_times,
    )

    # Assert that each column has the same contents
    check_dfs_have_same_contents_by_column(df1=first_df, df2=cache_df)

    # If cache_df doesn't hit the cache, it creates its own files
    # Thus, number of files is an indicator of whether the cache was hit
    assert len(list(tmp_path.glob("*"))) == len(predictor_specs)


if __name__ == "__main__":
    base_float_predictor_combinations = PredictorGroupSpec(
        values_loader=["synth_predictor_float"],
        interval_days=[365, 730],
        resolve_multiple_fn=["mean"],
        fallback=[np.NaN],
        allowed_nan_value_prop=[0.0],
    ).create_combinations()
