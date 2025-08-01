from mab.contextual.constraints import NumericalContextConstraint
from mab.contextual.context import ContextInstance
from mab.contextual.features import ContextFeature


# custom-made for the experiment
def generate_contextinsts_list_exp():
    instances_list = []
    context_no = 3
    threshold_min = 0
    threshold_max = 1
    min = -999
    max = -999
    include_last = False
    for i in range(context_no):
        features = []

        min = threshold_min if len(instances_list) == 0 else max  # instances_list[i - 1].constraints.threshold_max
        min = round(min, 3)

        increment = threshold_max / context_no
        if len(instances_list) == 0:
            max = increment
        else:
            if i == context_no - 1:
                # last feature - make threshold_max the upper bound
                # thus avoiding rounding errors
                max = threshold_max
                include_last = True
            else:
                max = min + increment
        max = round(max, 3)
        print(min, max)
        label = "MEM"
        constraint = NumericalContextConstraint(ContextFeature.ACTIVE_MEMORY_UTILIZATION, min, max, include_last)
        inst = ContextInstance(f"ctx-{label}-{min}-{max}", [constraint])
        instances_list.append(inst)
    return instances_list
