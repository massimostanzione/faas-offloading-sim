import os
from abc import ABC, abstractmethod
from copy import copy
from typing import List

from mab.contextual.context import Context, ContextInstance
from mab.contextual.features import ContextFeature
from mab.contextual.rtk.rtk_scenarios import RTKContextualScenario, RTKCS_KnowledgeDisjunction, \
    RTKCS_KnowledgeInheritance, RTKCS_KnowledgeInheritance_Total, RTKCS_KnowledgeInheritance2, RTKCS_KnowledgeRefining
from mab.contextual.utils import build_instances_agents_dict, NOPSubAgent
from mab.events import MABEventFlag
from mab.mab import NonContextualMABAgent, MABAgent, NonContextualMABAgent_EpochBased
from typing_extensions import deprecated

class ContextualMAB(MABAgent):

    def __init__(self, simulation, lb_policies, reward_config):
        super().__init__(simulation, lb_policies, reward_config)
        self.current_ctx_instance = None
        self.last_probed_data = None

    def get_context(self) -> Context:
        return self.simulation.context

    def get_context_instances(self) -> List[ContextInstance]:
        return self.simulation.context.instances

    def _probe_context_related_info(self, first_call=False) -> dict:
        # TODO not-hardcoded features
        features = [ContextFeature.ACTIVE_MEMORY_UTILIZATION]
        context_probing = {repr(f): None for f in features}
        for f in features: context_probing[repr(f)] = self.simulation.stats.to_dict(not first_call, not first_call)[repr(f)]
        print("probed:", context_probing)
        self.simulation.tracker.update(os.getpid(), "amu", round(context_probing[repr(ContextFeature.ACTIVE_MEMORY_UTILIZATION)],5))
        return context_probing

    def probe_and_update_context_instance(self):
        self.last_probed_data = self._probe_context_related_info()
        inst = self.simulation.context.pick_instance(self.last_probed_data)
        self.current_ctx_instance = inst

class ReduceToKMAB(ContextualMAB):

    SCENARIO_MAP = {
        "KD": RTKCS_KnowledgeDisjunction,
        "KI": RTKCS_KnowledgeInheritance, # TODO deprecated
        "KIT": RTKCS_KnowledgeInheritance_Total, # FIXME KI1
        "KI2": RTKCS_KnowledgeInheritance2,
        "KR": RTKCS_KnowledgeRefining,
    }

    def __init__(self, simulation, agents: List[NonContextualMABAgent], scenario_config_str:str):

        lb_policies=agents[0].lb_policies
        reward_config=agents[0].reward_config
        super().__init__(simulation, lb_policies, reward_config)
        # Instances-Agents Pairs
        self.IAPs = build_instances_agents_dict(self, self.simulation.context.instances, agents)
        self.scenario=self._build_scenario(scenario_config_str)
        self.scenario_acted=False
        self._current_iap= None
        self.reset_current_iap()
        self.set_label("super")
    """
    def _associate_instances_agents(self, instances, agents)->dict:
        agents_dict={}
        for i, ctx in enumerate(instances):

            # backlink from the agents to the main contextual MAB
            agents[i].super_rtk_mab = self

            agents_dict[ctx] = agents[i]
        return agents_dict
    """
    def reset_current_iap(self):
        self._current_iap=self.scenario.get_first_iap(self.simulation, self.IAPs)
        self.current_ctx_instance=next(iter(self._current_iap))
    #factory
    def _build_scenario(self, scenario_config_str: str)->RTKContextualScenario:
        scenario_class = self.SCENARIO_MAP.get(scenario_config_str, None)
        if scenario_class is None: raise ValueError(f"Unknown RTK scenario for {scenario_config_str}")
        return scenario_class()

    def get_agent_for_instance(self, inst:ContextInstance)->NonContextualMABAgent:
        return self.IAPs[inst]

    def get_current_instance(self) -> ContextInstance:
        return self.current_ctx_instance

    def get_current_agent(self) -> NonContextualMABAgent:
        #return self.get_agent_for_instance(self.current_ctx_instance)
        #print(self._current_iap, self.get_current_instance())
        return self._current_iap[self.get_current_instance()]

    def probe_and_update_context_instance(self):
        super().probe_and_update_context_instance()
        self._current_iap={self.current_ctx_instance:self.IAPs[self.current_ctx_instance]}

    # print them alongside subagents' ones, in order to avoid useless redudancy
    def unload_occurred_events(self):
        if self.occurred_events:
            agent = self.get_current_agent()
            agent.occurred_events.extend(self.occurred_events)
            self.occurred_events=[]

    def update_model(self, lb_policy: str, mab_stats_file: str, last_update=False)->bool:
        # at first call, choose the first agent based on probed data
        #if self.current_ctx_instance is None:
        #    probed_data = self.simulation._probe_context_related_info(True)
        #    self.update_context_instance(probed_data)

        # PRIMA aggiorno il modello dell'agente corrente...
        # ... e se sono alla prima invocazione, scarto
        agent = self.get_current_agent()
        #print("CORRENTE AGENTE", agent)
        agent.update_model(lb_policy, mab_stats_file, last_update)
        self.unload_occurred_events()
        previous_instance=self.current_ctx_instance
        is_init=isinstance(agent,NOPSubAgent)
        # ... POI scelgo il nuovo agente!

        self.probe_and_update_context_instance()

        # update agents info, if needed by instance switch, based on the RTK scenario
        if not is_init and self.current_ctx_instance != previous_instance:
            # *** INSTANCE SWITCH! ***
            is_instance_changed=True
            previous_iaps=self.IAPs.copy()

            self.IAPs = (self.scenario
                         .handle_context_instance_switch(self,
                                                         previous_instance,
                                                         self.current_ctx_instance,
                                                         self.simulation.t)
                         )

            if len(self.IAPs)!=len(previous_iaps):
                self.scenario_acted=True
            else:
                for inst, ag in self.IAPs.items():
                    if any(x != y for x, y in zip(ag.N, previous_iaps[inst].N)):
                        self.scenario_acted = True
                        break

            self.IAPs[previous_instance].occurred_events.append(MABEventFlag.CONTEXT_INSTANCE_CHANGE_OLD)
            self.IAPs[self.current_ctx_instance].occurred_events.append(MABEventFlag.CONTEXT_INSTANCE_CHANGE_NEW)
        else:
            is_instance_changed=False
        #new_agent=self._choose_new_agent(previous_instance)
        #super().update_model(lb_policy, mab_stats_file, last_update)
        #self.update_context_instance()

        new_agent=self.IAPs[self.current_ctx_instance]
        self._current_iap={self.current_ctx_instance:new_agent}#self.get_current_agent()
        new_agent.set_additional_data_output(self._gather_mab_context_stats())
        return is_instance_changed

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
                for k, v in self.IAPs.items():
                    if v is self.get_current_agent():
                        label=k.label
                        break
                subdict["epochStartTimes_ctx"][label]=self.simulation.t

        if self.scenario_acted:
            subdict["scenario_action"]=self.simulation.t
            self.scenario_acted=False

        dict["context_info"] = subdict
        return dict

    def are_subagents_epoch_based(self):
        return next(iter(self.IAPs.values())).is_epoch_based

    #def update_context_instance(self, probed_data: dict):


    @deprecated
    def _choose_new_agent(self, old_instance:ContextInstance)->NonContextualMABAgent:
        #probed_data = self._probe_context_related_info()
        #self.update_context_instance(probed_data)
        # super().update_context_instance(probed_data)

        # todo queste due righe, così come l'ultima, sono identiche alla super(), vedere se/come unire
        #self.last_probed_data = probed_data
        #inst = self.simulation.context.pick_instance(probed_data)

        # first invocation
        #if self.current_ctx_instance is not None:
            # self.simulation:RTK_Simulation
            if self.current_ctx_instance is not self.current_ctx_instance:
                self.IAPs = self.simulation.rtk_scenario.handle_context_instance_switch(self,
                                                                                        self.current_ctx_instance,
                                                                                        inst,
                                                                                        self.simulation.t)

        #self.current_ctx_instance = inst


class ReduceToKMAB_EpochReset(ReduceToKMAB):

    def __init__(self, simulation, agents: List[NonContextualMABAgent], scenario_config_str:str):
        for agent in agents:
            if not agent.is_epoch_based: raise RuntimeError("cannot")
        super().__init__(simulation, agents, scenario_config_str)

    def select_policy_old(self):
        # advance epochs for all other non-contextual agents, if based on epochs
        current_agent=self.get_current_agent()
        if self.are_subagents_epoch_based():
            for _, agent in self.IAPs.items():
                agent:NonContextualMABAgent_EpochBased
                if agent is not current_agent:
                    if agent.remaining_locked_plays > 0:
                        agent.remaining_locked_plays -= 1
        return current_agent.select_policy()

    def update_model(self, lb_policy: str, mab_stats_file: str, last_update=False):
        is_istance_changed = super().update_model(lb_policy, mab_stats_file, last_update)
        if is_istance_changed:
            new_agent = self.get_current_agent()
            new_agent: NonContextualMABAgent_EpochBased
            if new_agent.is_first_epoch_started():
                if self.simulation.t > new_agent.expected_epoch_end:
                    new_agent.remaining_locked_plays = 0
                    print(
                        f"\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n[MAB] EpochReset: {self.simulation.t - new_agent.expected_epoch_end} s "
                        f"passed since last epoch should have been expired, resetting the counter. "
                        f"A new epoch will forcefully start.")
                    self.occurred_events.append(MABEventFlag.EPOCH_RESET)


class LinUCB(ContextualMAB):
    def __init__(self):
        raise NotImplementedError("LinUCB: future development...")