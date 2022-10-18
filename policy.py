from enum import Enum
import conf
import numpy as np


class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD = 2
    DROP = 3

class Policy:

    def __init__ (self, simulation):
        self.simulation = simulation

    def schedule (self, function, qos_class):
        pass

    def update (self):
        pass

    def can_execute_locally (self, node, f, reclaim_memory=True):
        if f in node.warm_pool or node.curr_memory >= f.memory:
            return True
        if reclaim_memory:
            self.node.warm_pool.reclaim_memory(f.memory - node.curr_memory)
        return node.curr_memory >= f.memory



class BasicPolicy(Policy):

    def schedule (self, f, c):
        if c.name == "default":
            sched_decision = SchedulerDecision.OFFLOAD
        elif not self.can_execute_locally(self.simulation.edge, f):
            sched_decision = SchedulerDecision.DROP
        else:
            sched_decision = SchedulerDecision.EXEC

        return sched_decision


class ProbabilisticPolicy (Policy):

    # Probability vector: p_e, p_o, p_d

    def __init__ (self, simulation):
        super().__init__(simulation)
        self.probs = {(f,c): [0.33,0.33,1-0.66] for f in simulation.functions for c in simulation.classes}
        self.probs_nolocal = {(f,c): [0.5,0.5] for f in simulation.functions for c in simulation.classes}
        seed = self.simulation.config.getint(conf.SEC_POLICY,"seed", fallback=13)
        self.rng = np.random.default_rng(seed)

    def schedule (self, f, c):
        decision = self.rng.choice(list(SchedulerDecision), p=self.probs[(f,c)]) 
        if decision == SchedulerDecision.EXEC and not self.can_execute_locally(self.simulation.edge, f):
            decision = self.rng.choice(list(SchedulerDecision)[1:], p=self.probs_nolocal[(f,c)]) 

        return decision

    def update(self):
        pass
