"""Abstract method that defines a feature cache."""
from abc import ABC, abstractmethod

import pandas as pd

from timeseriesflattener.feature_spec_objects import AnyS, AnySpecpecAnySpec


class FeatureCache(ABC):
    @abstractmethod
    def __init__(self, validate: bool = True):
        """Initialize a feature cache.

        Args:
            validate (bool): Whether to validate the cache. Defaults to True.
        """
        pass

    @abstractmethod
    def feature_exists(self, feature_spec: AnySpec, validate: bool = True) -> bool:
        pass

    @abstractmethod
    def get_feature(self, feature_spec: AnySpec) -> pd.DataFrame:
        pass

    @abstractmethod
    def write_feature(self, feature_spec: AnySpec, df: pd.DataFrame) -> None:
        pass
