from enum import Enum
import numpy as np

import conf
import optimizer


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
            reclaimed = node.warm_pool.reclaim_memory(f.memory - node.curr_memory)
            node.curr_memory += reclaimed
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
        seed = self.simulation.config.getint(conf.SEC_POLICY,"seed", fallback=13)
        self.rng = np.random.default_rng(seed)
        self.stats_snapshot = None

    def schedule (self, f, c):
        probabilities = self.probs[(f,c)]
        decision = self.rng.choice(list(SchedulerDecision), p=probabilities) 
        if decision == SchedulerDecision.EXEC and not self.can_execute_locally(self.simulation.edge, f):
            nolocal_prob = sum(probabilities[1:])
            if nolocal_prob > 0.0:
                decision = self.rng.choice([SchedulerDecision.OFFLOAD,SchedulerDecision.DROP],
                                           p=[probabilities[1]/nolocal_prob,probabilities[2]/nolocal_prob]) 
            else:
                decision = SchedulerDecision.OFFLOAD

        return decision

    def update(self):
        if self.stats_snapshot is not None:
            stats = self.simulation.stats

            arrival_rates = {}
            for f,c in stats.arrivals:
                arrival_rates[(f,c)] = stats.arrivals[(f,c)]/self.simulation.t

            estimated_service_time = {}
            estimated_service_time_cloud = {}
            for f in self.simulation.functions:
                # TODO: use an estimate instead of the true value
                estimated_service_time[f] = f.serviceMean/self.simulation.edge.speedup
                estimated_service_time_cloud[f] = f.serviceMean/self.simulation.cloud.speedup

            self.probs = optimizer.update_probabilities(self.simulation,
                                arrival_rates,
                                estimated_service_time,
                                estimated_service_time_cloud,
                                self.simulation.init_time[self.simulation.edge],
                                2*self.simulation.latencies[(self.simulation.edge.region,self.simulation.cloud.region)])
        self.stats_snapshot = self.simulation.stats.to_dict()

class RandomPolicy (ProbabilisticPolicy):

    def __init__ (self, simulation):
        super().__init__(simulation)
        self.probs = {(f,c): [0.33,0.33,1-0.66] for f in simulation.functions for c in simulation.classes}

    def schedule (self, f, c):
        return super().schedule(f,c)

    def update(self):
        pass
