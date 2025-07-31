from abc import ABC
from typing import List

from mab.contextual.constraints import ContextConstraint
from mab.contextual.features import ContextFeature


class ContextInstance:
    label: str
    constraints: List[ContextConstraint]

    def __init__(self, label: str = "", constraints: List[ContextConstraint] = None):
        self.label = label
        self.constraints = constraints

    def probed_data_belongs_here(self, probed_dict: dict) -> bool:
        matched = 0
        for k, v in probed_dict.items():
            c = next((c for c in self.constraints if str(c.feature) == str(k)), None)
            if c is None:
                print("Cannot find a corresponding feature for", k, "in this instance (available features:" , [c.feature for c in self.constraints], ")")
                exit(1)
            if c.verify_constraint(v):
                matched += 1
        return matched == len(self.constraints)


class Context(ABC):
    features: List[ContextFeature]
    instances: List[ContextInstance]

    def __init__(self, features: List[ContextFeature]):
        self.features = []
        for f in features: self.add_feature(f)

        self.instances = []
        self.moving_averages = {}

    def add_feature(self, f: ContextFeature):
        self.features.append(f)

    def add_instances(self, instances: List[ContextInstance]):
        for i in instances:
            self.instances.append(i)

    def pick_instance(self, probed_data: dict):
        ctx_found = None
        for ctx in self.instances:
            # for k in data:
            if ctx.probed_data_belongs_here(probed_data):
                ctx_found = ctx
                break
        if not ctx_found:
            print("Context not found for features =", probed_data)
            exit(1)
        return ctx_found
