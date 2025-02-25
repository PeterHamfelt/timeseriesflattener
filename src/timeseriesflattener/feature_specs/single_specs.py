from dataclasses import dataclass
from typing import Callable, Optional, Union

import pandas as pd
from timeseriesflattener.aggregation_fns import AggregationFunType, concatenate
from timeseriesflattener.utils.pydantic_basemodel import BaseModel


@dataclass(frozen=True)
class CoercedFloats:
    lookwindow: Union[float, int]
    fallback: Union[float, int]


def can_be_coerced_losslessly_to_int(value: float) -> bool:
    try:
        int_version = int(value)
        return (int_version - value) == 0
    except ValueError:
        return False


def coerce_floats(lookwindow: float, fallback: float) -> CoercedFloats:
    lookwindow = (
        lookwindow
        if not can_be_coerced_losslessly_to_int(lookwindow)
        else int(lookwindow)
    )
    fallback = (
        fallback if not can_be_coerced_losslessly_to_int(fallback) else int(fallback)
    )

    return CoercedFloats(lookwindow=lookwindow, fallback=fallback)


class StaticSpec(BaseModel):
    """Specification for a static feature.

    Args:
        timeseries_df: Dataframe with the values. Should contain columns:
            entity_id (int, float, str): ID of the entity each time series belongs to
            value (int, float, str): The values in the timeseries.
            timestamp (datetime): Timestamps
            NOTE: Column names can be overridden when initialising TimeSeriesFlattener.
        feature_base_name: The name of the feature. Used for column name generation, e.g.
            <prefix>_<feature_baase_name>_<metadata>.
        prefix: The prefix used for column name generation, e.g.
            <prefix>_<feature_name>_<metadata>. Defaults to "pred".
    """

    timeseries_df: pd.DataFrame
    feature_base_name: str
    prefix: str = "pred"

    def get_output_col_name(self) -> str:
        return f"{self.prefix}_{self.feature_base_name}"


def get_temporal_col_name(
    prefix: str,
    feature_base_name: str,
    lookwindow: Union[float, int],
    aggregation_fn: AggregationFunType,
    fallback: Union[float, int],
) -> str:
    """Get the column name for the temporal feature."""
    coerced = coerce_floats(lookwindow=lookwindow, fallback=fallback)
    col_str = f"{prefix}_{feature_base_name}_within_{coerced.lookwindow!s}_days_{aggregation_fn.__name__}_fallback_{coerced.fallback}"
    return col_str


class OutcomeSpec(BaseModel):
    """Specification for an outcome feature.

    Args:
        timeseries_df: Dataframe with the values. Should contain columns:
            entity_id (int, float, str): ID of the entity each time series belongs to
            value (int, float, str): The values in the timeseries.
            timestamp (datetime): Timestamps
            NOTE: Column names can be overridden when initialising TimeSeriesFlattener.
        feature_base_name: The name of the feature. Used for column name generation, e.g.
            <prefix>_<feature_baase_name>_<metadata>.
        lookahead_days: How far ahead from the prediction time to look for outcome values.
        aggregation_fn: How to aggregate multiple values within lookahead days. Should take a grouped dataframe as input and return a single value.
        fallback: Value to return if no values is found within window.
        incident: Whether the outcome is incident or not. E.g. type 2 diabetes is incident because you can only experience it once.
            Incident outcomes can be handled in a vectorised way during resolution, which is faster than non-incident outcomes.
            Requires that each entity only occurs once in the timeseries_df.
        prefix: The prefix used for column name generation, e.g.
            <prefix>_<feature_name>_<metadata>. Defaults to "pred".
    """

    timeseries_df: pd.DataFrame
    feature_base_name: str
    lookahead_days: float
    aggregation_fn: AggregationFunType
    fallback: Union[float, int]
    incident: bool
    prefix: str = "outc"

    def get_output_col_name(self) -> str:
        """Get the column name for the output column."""
        col_str = get_temporal_col_name(
            prefix=self.prefix,
            feature_base_name=self.feature_base_name,
            lookwindow=self.lookahead_days,
            aggregation_fn=self.aggregation_fn,
            fallback=self.fallback,
        )

        if self.is_dichotomous:
            col_str += "_dichotomous"

        return col_str

    def is_dichotomous(self) -> bool:
        """Check if the outcome is dichotomous."""
        return len(self.timeseries_df["value"].unique()) <= 2


class PredictorSpec(BaseModel):
    """Specification for predictor feature.

    Args:
        timeseries_df: Dataframe with the values. Should contain columns:
            entity_id (int, float, str): ID of the entity each time series belongs to
            value (int, float, str): The values in the timeseries.
            timestamp (datetime): Timestamps
            NOTE: Column names can be overridden when initialising TimeSeriesFlattener.
        feature_base_name: The name of the feature. Used for column name generation, e.g.
            <prefix>_<feature_baase_name>_<metadata>.
        lookbehind_days: How far behind from the prediction time to look for predictor values.
        aggregation_fn: How to aggregate multiple values within lookahead days. Should take a grouped dataframe as input and return a single value.
        fallback: Value to return if no values is found within window.
        incident: Whether the outcome is incident or not. E.g. type 2 diabetes is incident because you can only experience it once.
            Incident outcomes can be handled in a vectorised way during resolution, which is faster than non-incident outcomes.
            Requires that each entity only occurs once in the timeseries_df.
        prefix: The prefix used for column name generation, e.g.
            <prefix>_<feature_name>_<metadata>. Defaults to "pred".
    """

    timeseries_df: pd.DataFrame
    feature_base_name: str
    aggregation_fn: AggregationFunType
    fallback: Union[float, int]
    lookbehind_days: float
    prefix: str = "pred"

    def get_output_col_name(self) -> str:
        """Generate the column name for the output column."""
        return get_temporal_col_name(
            prefix=self.prefix,
            feature_base_name=self.feature_base_name,
            lookwindow=self.lookbehind_days,
            aggregation_fn=self.aggregation_fn,
            fallback=self.fallback,
        )


class TextPredictorSpec(BaseModel):
    """Specification for a text predictor, where the df has been resolved.

    Args:
        timeseries_df: Dataframe with the values.
        feature_base_name: The name of the feature. Used for column name generation, e.g.
            <prefix>_<feature_baase_name>_<metadata>.
        aggregation_fn: How to aggregate multiple values within a window. Can be a string, a function, or a list of functions.
        fallback: Value to return if no values is found within window.
        lookbehind_days: How far behind to look for values.
        prefix: The prefix used for column name generation, e.g.
            <prefix>_<feature_name>_<metadata>. Defaults to "pred".
        embedding_fn: A function used for embedding the text. Should take a
            pandas series of strings and return a pandas dataframe of embeddings.
        embedding_fn_kwargs: Optional kwargs passed onto the embedding_fn.
            Defaults to None.
        aggregation_fn: A function used for resolving multiple
            values within a window. Defaults to concatenate.

    """

    timeseries_df: pd.DataFrame
    feature_base_name: str
    fallback: Union[float, int]
    embedding_fn: Callable
    embedding_fn_kwargs: Optional[dict] = None
    lookbehind_days: float
    prefix: str = "pred"

    aggregation_fn: AggregationFunType = concatenate

    def get_output_col_name(self, additional_feature_name: Optional[str] = None) -> str:
        """Generate the column name for the output column.
        If interval days is a float, the decimal point is changed to an underscore.

        Args:
            additional_feature_name (Optional[str]): additional feature name to
                append to the column name.
        """
        feature_name = self.feature_base_name
        if additional_feature_name is not None:
            feature_name += f"-{additional_feature_name}"

        col_str = col_str = get_temporal_col_name(
            prefix=self.prefix,
            feature_base_name=feature_name,
            lookwindow=self.lookbehind_days,
            aggregation_fn=self.aggregation_fn,
            fallback=self.fallback,
        )

        return col_str


TemporalSpec = Union[PredictorSpec, OutcomeSpec, TextPredictorSpec]
AnySpec = Union[StaticSpec, TemporalSpec]
