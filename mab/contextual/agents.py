from abc import ABC
from typing import List

from mab.contextual.context import Context, ContextInstance
from mab.mab import NonContextualMABAgent, MABAgent, NonContextualMABAgent_EpochBased


class ContextualMAB(ABC, MABAgent):
    def __init__(self, simulation, lb_policies, reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.current_ctx_instance = None
        self.last_probed_data = None

    def get_context(self) -> Context:
        return self.simulation.context

    def get_context_instances(self) -> List[ContextInstance]:
        return self.simulation.context.instances

    def update_context_instance(self, probed_data: dict):
        self.last_probed_data = probed_data
        inst = self.simulation.context.pick_instance(probed_data)
        self.current_ctx_instance = inst


class ReduceToKMAB(ABC, ContextualMAB):
    def __init__(self, simulation, agents: List[NonContextualMABAgent]):

        lb_policies=agents[0].lb_policies
        reward_config=agents[0].reward_config
        super().__init__(simulation, lb_policies, reward_config)
        self.agents = {}
        for i, ctx in enumerate(self.simulation.context.instances):

            # backlink from the agents to the main contextual MAB
            agents[i].super_rtk_mab = self

            self.agents[ctx] = agents[i]

    def get_current_agent(self) -> NonContextualMABAgent:
        return self.agents[self.current_ctx_instance]

    def update_model(self, lb_policy: str, mab_stats_file: str, last_update=False):
        agent = self.get_current_agent()
        agent.set_additional_data_output(self._gather_mab_context_stats())
        agent.update_model(lb_policy, mab_stats_file, last_update)

    def select_policy(self):
        current_agent=self.get_current_agent()
        policy= current_agent.select_policy()
        return policy

    def _gather_mab_context_stats(self) -> dict:
        dict = {}

        subdict = {}
        subdict["probed_data"] = self.last_probed_data
        subdict["instance_invoked"] = self.current_ctx_instance.label
        # sono già incluse nel dict dell'agente chiamato per lo specifico contesto:
        # subdict["policy"]="yeah"
        # subdict["reward"]="yeah"


        if self.are_subagents_epoch_based():
            if self.get_current_agent().is_new_epoch_started():
                subdict["epochStartTimes_ctx"] = {}
                label="ND"
                for k, v in self.agents.items():
                    if v is self.get_current_agent():
                        label=k.label
                        break
                subdict["epochStartTimes_ctx"][label]=self.simulation.t

        dict["context_info"] = subdict
        return dict

    def are_subagents_epoch_based(self):
        return next(iter(self.agents.values())).is_epoch_based

class ReduceToKMAB_EpochReset(ReduceToKMAB):

    def __init__(self, simulation, agents: List[NonContextualMABAgent]):
        for agent in agents:
            if not agent.is_epoch_based: raise RuntimeError("cannot")
        super().__init__(simulation, agents)

    def select_policy(self):
        # advance epochs for all other non-contextual agents, if based on epochs
        current_agent=self.get_current_agent()
        if self.are_subagents_epoch_based():
            for _, agent in self.agents.items():
                agent:NonContextualMABAgent_EpochBased
                if agent is not current_agent:
                    if agent.remaining_locked_plays > 0:
                        agent.remaining_locked_plays -= 1
        return current_agent.select_policy()

class LinUCB(ContextualMAB):
    def __init__(self):
        raise NotImplementedError("LinUCB: future development...")