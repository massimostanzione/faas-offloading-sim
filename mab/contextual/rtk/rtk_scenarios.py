from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from mab.contextual.context import ContextInstance
from mab.contextual.utils import generate_contextinsts_list_exp, build_instances_agents_dict, duplicate_agent, \
    NOPSubAgent, is_super_agent_epoch_reset
from mab.events import MABEventFlag
from mab.mab import NonContextualMABAgent
from typing_extensions import deprecated


class RTKContextualScenario(ABC):

    # the first agent chosen is dependent on the scenario:
    # agent is none at first call and after KR-refining
    # in that case, just discard the first point,
    # because we don't have the agent that actually chose the arm
    # (at first call, we don't know who it is;
    # after KR-refining: we know, but it no longer exists,
    # and the new ones didn't choose the arm)
    def get_first_iap(self, sim, pairs:dict=None) -> dict:
        return {None: NOPSubAgent(sim)}

    @abstractmethod
    def handle_context_instance_switch(self, super_agent,
                                       old_instance: ContextInstance,
                                       new_instance: ContextInstance,
                                       time: float = None) -> dict:
        """
        yee

        Parameters
        ----------
        time
        old_instance
        RTK_agent
        new_instance
        per time dire che è overload accettabile
        """
        pass


class RTKCS_KnowledgeDisjunction(RTKContextualScenario):
    def handle_context_instance_switch(self, super_agent,
                                       old_instance: ContextInstance,
                                       new_instance: ContextInstance,
                                       time: float = None) -> dict:
        # nothing is required, just a check
        #agents = super_agent.agents
        #if not agents[new_instance].is_agent_first_call():
        #    raise RuntimeError("KD first call on a sub-agent that is already initialized!")
        return super_agent.IAPs


@deprecated
class RTKCS_KnowledgeInheritance(RTKContextualScenario):

    def handle_context_instance_switch(self, super_agent,
                                       old_instance: ContextInstance,
                                       new_instance: ContextInstance,
                                       time: float = None) -> dict:
        agents = super_agent.IAPs
        if agents[new_instance].is_agent_first_call():
            print("PRIMA CHIAMATA")
            agents[new_instance].Q = agents[old_instance].Q

            # N array: if old agent has not terminated the init stage, let the
            # new agent inherit the partial knowledge he can obtain, leaving him
            # the duty of continuing the initialization
            if all(n > 0 for n in agents[old_instance].N):
                agents[new_instance].N=[1]*len(agents[new_instance].N)
            else:
                agents[new_instance].N = agents[old_instance].N
        return agents

# TODO KI1
class RTKCS_KnowledgeInheritance_Total(RTKContextualScenario):
    def handle_context_instance_switch(self, super_agent,
                                       old_instance: ContextInstance,
                                       new_instance: ContextInstance,
                                       time: float = None) -> dict:
        agents = super_agent.IAPs
        if agents[new_instance].is_agent_first_call():
            print("PRIMA CHIAMATA")
            agents[new_instance] = duplicate_agent(agents[old_instance], is_super_agent_epoch_reset(super_agent))
            agents[old_instance].occurred_events.append(MABEventFlag.MAB_KNOWLEDGE_INHERITANCE_PREDECESSOR)
            agents[new_instance].occurred_events.append(MABEventFlag.MAB_KNOWLEDGE_INHERITANCE_SUCCESSOR)
        return agents

class RTKCS_KnowledgeInheritance2(RTKCS_KnowledgeInheritance_Total):
    def handle_context_instance_switch(self, super_agent,
                                       old_instance: ContextInstance,
                                       new_instance: ContextInstance,
                                       time: float = None) -> dict:
        agents_supercall = super().handle_context_instance_switch(super_agent, old_instance, new_instance, time)
        agents=super_agent.IAPs
        # if KI1 already did something, keep it (it's the same)
        if agents_supercall[new_instance] is not agents[new_instance]:
               agents = agents_supercall
        else:
            # ... otherwise, act when the new agent is not (fully) initialized
            # and the old instance agent has done more initialization steps than the receiving onr
            if (not agents[new_instance].is_agent_fully_initialized())\
                    and not (agents[new_instance].has_better_knowledge_than(agents[old_instance])):
                agents[new_instance] = duplicate_agent(agents[old_instance], is_super_agent_epoch_reset(super_agent))
                agents[old_instance].occurred_events.append(MABEventFlag.MAB_KNOWLEDGE_INHERITANCE_PREDECESSOR)
                agents[new_instance].occurred_events.append(MABEventFlag.MAB_KNOWLEDGE_INHERITANCE_SUCCESSOR)
        return agents

class KR_RefiningMethod(Enum):
    KRRM_TIME_DELTA = 0,
    KRRM_CONVERGENCE = 1

class RTKCS_KnowledgeRefining(RTKContextualScenario):
    def __init__(self):

        #if refining_method is KR_RefiningMethod.KRRM_TIME_DELTA and time_delta is None:
        #    raise RuntimeError("err")

        #if refining_method is KR_RefiningMethod.KRRM_CONVERGENCE:
        #    raise NotImplementedError("not now!")

        self.refining_method = KR_RefiningMethod.KRRM_TIME_DELTA
        #self.time_delta = time_delta
        self.refining_happened = False  # just a consistency check guard


    def get_first_iap(self, sim, pairs=None) -> dict:
        # TODO scriverlo meglio come docs
        # at first call, we just have the non-contextual case, only one agent is present;
        # after refining, we know who chose the arm - the first agent - but it no longer exists,
        # and the new ones didn't choose the arm
        ret=None
        if not self.refining_happened:
            if pairs is None: raise ValueError("none")
            instance = next(iter(pairs))
            agent = pairs[instance]
            ret={instance:agent}
        else:
            sim=next(iter(pairs.values())).simulation
            ret={None:NOPSubAgent(sim)}
        return ret

    #def __init__(self, refining_method: KR_RefiningMethod, time_delta: float = None):
    def set_refining_method(self, refining_method: KR_RefiningMethod, time_delta: float = None):
        pass


    def handle_context_instance_switch(self, super_agent,
                                       old_instance: ContextInstance,
                                       new_instance: ContextInstance,
                                       time: float = None) -> dict:
        #TODO docs nothing is required
        if time is None: raise ValueError("time none")
        return super_agent.IAPs

    def handle_refine_event(self, super_agent)-> dict:
        # *** si suppone refining_method=time_delta ***
        new_agents_dict = super_agent.IAPs
        #if time >= self.time_delta and not self.refining_happened:
        if self.refining_happened: raise RuntimeError("refining already happened!")
        if not self.refining_happened:
            print("\n\n*** SWITCH! ***\n\n")
            self.refining_happened = True

            if len(super_agent.IAPs) != 1: raise ValueError("none")
            new_instances_list = generate_contextinsts_list_exp(True, True)

            # make each subagent a copy of the main previous agent
            new_agents_list = []
            for i in range(len(new_instances_list)):
                agent = duplicate_agent(next(iter(super_agent.IAPs.values())), is_super_agent_epoch_reset(super_agent))
                new_agents_list.append(agent)
            new_agents_dict = build_instances_agents_dict(super_agent, new_instances_list, new_agents_list)
            super_agent.occurred_events.append(MABEventFlag.MAB_KNOWLEDGE_REFINING)

        return new_agents_dict
