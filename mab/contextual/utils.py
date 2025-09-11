from copy import copy
from typing import List

import numpy as np

from mab.contextual.constraints import NumericalContextConstraint
from mab.contextual.context import ContextInstance
from mab.contextual.features import ContextFeature
from mab.events import MABEventFlag
from mab.mab import NonContextualMABAgent, UCBTuned, UCB2, KLUCB, KLUCBsp


# custom-made for the experiment
def generate_contextinsts_list_exp(is_RTK_KR:bool, rtk_kr_refining_call=False):
    INSTANCES_NO=3 # TODO docs: hardcoded!
    context_no = 1 if (is_RTK_KR and not rtk_kr_refining_call) else INSTANCES_NO
    instances_list = []
    threshold_min = 0
    threshold_max = 1
    min = -999
    max = -999
    include_last = False
    for i in range(context_no):
        features = []

        min = threshold_min if len(instances_list) == 0 else max  # instances_list[i - 1].constraints.threshold_max
        min = round(min, INSTANCES_NO)

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
        max = round(max, INSTANCES_NO)
        print(min, max)
        #label = "MEM" if not is_RTK_KR else "___MAIN-CONTEXT___"
        label = "MAIN-CONTEXT-INSTANCE" if (is_RTK_KR and not rtk_kr_refining_call) else "ActiveMemUtil"

        constraint = NumericalContextConstraint(ContextFeature.ACTIVE_MEMORY_UTILIZATION, min, max, include_last)
        inst = ContextInstance(f"ctx-{label}-{min}-{max}", [constraint])
        instances_list.append(inst)
    return instances_list


def build_instances_agents_dict(super_agent, instances: List[ContextInstance],
                                sub_agents: List[NonContextualMABAgent]) -> dict:
    agents_dict = {}
    for i, ctx in enumerate(instances):
        # backlink from the agents to the main contextual MAB
        sub_agents[i].super_rtk_mab = super_agent

        agents_dict[ctx] = sub_agents[i]
    return agents_dict


def duplicate_agent(old_agent: NonContextualMABAgent, epoch_reset:bool=False) -> NonContextualMABAgent:
    new_agent = None
    if isinstance(old_agent, UCBTuned):
        new_agent = UCBTuned(old_agent.simulation, old_agent.lb_policies, old_agent.exploration_factor,
                             old_agent.reward_config)
        new_agent.M2 = copy(old_agent.M2)
    elif isinstance(old_agent, UCB2):
        new_agent = UCB2(old_agent.simulation, old_agent.lb_policies, old_agent.exploration_factor,
                         old_agent.reward_config, old_agent.alpha)
        new_agent.R = np.zeros(len(old_agent.R))
        new_agent.remaining_locked_plays = 0
        #new_agent.R = copy(old_agent.R)
        #if epoch_reset:
        #    new_agent.remaining_locked_plays = 0
        #else:
        #    new_agent.remaining_locked_plays = copy(old_agent.remaining_locked_plays)
    elif isinstance(old_agent, KLUCB):
        new_agent = KLUCB(old_agent.simulation, old_agent.lb_policies, old_agent.exploration_factor,
                          old_agent.reward_config, old_agent.c)
        new_agent.c = old_agent.c
        new_agent.cumQ = copy(old_agent.cumQ)
    elif isinstance(old_agent, KLUCBsp):
        new_agent = KLUCBsp(old_agent.simulation, old_agent.lb_policies, old_agent.reward_config, old_agent.c)
        new_agent.c = old_agent.c
        #new_agent.cumQ = copy(old_agent.cumQ)
        new_agent.cumQ = np.zeros(len(old_agent.cumQ))
    else:
        raise ValueError("nooo")
    new_agent.simulation.stats = old_agent.simulation.stats
    new_agent.is_epoch_based=old_agent.is_epoch_based
    new_agent.first_call=copy(old_agent.first_call)
    new_agent.additional_data_output=old_agent.additional_data_output
    new_agent.super_rtk_mab=old_agent.super_rtk_mab
    if old_agent.is_agent_fully_initialized():
        new_agent.N = np.ones(len(old_agent.N))
    else:
        # a partialy copy is better than an empty one
        # also, the ".has_better_knowledge" check is done outside this scope,
        # before calling this function
        new_agent.N=copy(old_agent.N)
    new_agent.Q = copy(old_agent.Q)
    new_agent.invocations_no = old_agent.invocations_no
    new_agent.curr_lb_policy=None#old_agent.curr_lb_policy
    new_agent.set_label(old_agent.label)
    return new_agent


def hours_to_secs(hours:float)->float: return hours*60*60

def is_strategy_RTK(strategy:str)->bool:
    return "RTK-" in strategy

def is_super_agent_epoch_reset(super_agent)->bool:
    from mab.contextual.agents import ReduceToKMAB_EpochReset
    return isinstance(super_agent, ReduceToKMAB_EpochReset)


# TODO docs: questo per distinguere da None (failsafe) - citare Null Object Pattern
class NOPSubAgent(NonContextualMABAgent):
    def __init__(self, simulation):
        from simulation import RewardConfig
        dummy_conf=RewardConfig(1,0,0,0,0,0,0,0,0,0,0,1)
        #self.simulation=simulation
        super().__init__(None, ["placeholder"], dummy_conf)

    def update_model(self, lb_policy: str, mab_stats_file: str, last_update=False):
        print("first call, or RTK-refine: current agent is temporarily not defined")
        self.occurred_events.append(MABEventFlag.DISCARDED_REWARD)


    def select_policy(self) -> str:
        raise RuntimeError("This method should not be called!")

def equals_failproof(a, b)->bool:
    THRESHOLD=1e-9
    return abs(a-b)<THRESHOLD