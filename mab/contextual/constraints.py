from abc import ABC, abstractmethod

from mab.contextual.features import ContextFeature


class ContextConstraint(ABC):
    def __init__(self, feature: ContextFeature):
        self.feature = feature

    @abstractmethod
    def verify_constraint(self, val: any) -> bool:
        pass


class CategoricalContextConstraint(ContextConstraint):
    def __init__(self, feature: ContextFeature, category: str):
        super().__init__(feature)
        self.category = category

    def verify_constraint(self, val: any) -> bool:
        return val == self.category


class NumericalContextConstraint(ContextConstraint):
    def __init__(self, feature: ContextFeature, threshold_min: float, threshold_max: float,
                 include_threshold_max: bool = False):
        super().__init__(feature)
        self.threshold_min = threshold_min
        self.threshold_max = threshold_max

        """
        threshold_max is normally not included in the range,
        while threshold_min is, i.e. the validation range is:
                    [threshold_min, threshold_max)
        set this value to True for the maximum instance, so that
        the upper value of the range is included
        """
        self.include_threshold_max = include_threshold_max

    def verify_constraint(self, val: any) -> bool:
        return self.threshold_min <= val <= self.threshold_max if self.include_threshold_max else self.threshold_min <= val < self.threshold_max
