from typing import List

from mab.contextual.context import Context, ContextInstance
from mab.mab import NonContextualMABAgent, MABAgent


class ContextualMAB(MABAgent):
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


class ReduceToKMAB(ContextualMAB):
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
        agent.set_additional_data_output(self._raccogli_stats())
        agent.update_model(lb_policy, mab_stats_file, last_update)

    def select_policy(self):
        return self.get_current_agent().select_policy()

    def _raccogli_stats(self) -> dict:
        dict = {}

        subdict = {}
        subdict["probed_data"] = self.last_probed_data
        subdict["instance_invoked"] = self.current_ctx_instance.label
        # sono già incluse nel dict dell'agente chiamato per lo specifico contesto:
        # subdict["policy"]="yeah"
        # subdict["reward"]="yeah"

        dict["context_info"] = subdict
        return dict
