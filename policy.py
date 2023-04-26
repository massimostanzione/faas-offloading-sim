import statistics
from enum import Enum
import numpy as np

import conf
import optimizer
import optimizer_legacy


class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD = 2
    DROP = 3


class Policy:

    def __init__(self, simulation):
        self.simulation = simulation

    def schedule(self, function, qos_class):
        pass

    def update(self):
        pass

    def can_execute_locally(self, node, f, reclaim_memory=True):
        if f in node.warm_pool or node.curr_memory >= f.memory:
            return True
        if reclaim_memory:
            reclaimed = node.warm_pool.reclaim_memory(f.memory - node.curr_memory)
            node.curr_memory += reclaimed
        return node.curr_memory >= f.memory


class BasicPolicy(Policy):

    def schedule(self, f, c):
        if self.can_execute_locally(self.simulation.edge, f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD

        return sched_decision


class ProbabilisticPolicy(Policy):

    # Probability vector: p_e, p_o, p_d

    def __init__(self, simulation):
        super().__init__(simulation)
        seed = self.simulation.config.getint(conf.SEC_POLICY, "seed", fallback=13)
        self.rng = np.random.default_rng(seed)
        self.stats_snapshot = None
        self.last_update_time = None
        self.arrival_rate_alpha = self.simulation.config.getfloat(conf.SEC_POLICY, conf.POLICY_ARRIVAL_RATE_ALPHA,
                                                                  fallback=1.0)
        self.arrival_rates = {}
        self.rt_percentile = self.simulation.config.getfloat(conf.SEC_POLICY, "rt-percentile", fallback=-1.0)

        self.probs = {(f, c): [0.33, 0.33, 1 - 0.66] for f in simulation.functions for c in simulation.classes}

    def schedule(self, f, c):
        probabilities = self.probs[(f, c)]
        decision = self.rng.choice(list(SchedulerDecision), p=probabilities)
        if decision == SchedulerDecision.EXEC and not self.can_execute_locally(self.simulation.edge, f):
            nolocal_prob = sum(probabilities[1:])
            if nolocal_prob > 0.0:
                decision = self.rng.choice([SchedulerDecision.OFFLOAD, SchedulerDecision.DROP],
                                           p=[probabilities[1] / nolocal_prob, probabilities[2] / nolocal_prob])
            else:
                decision = SchedulerDecision.OFFLOAD

        return decision

    def update(self):
        stats = self.simulation.stats

        estimated_service_time = {}
        estimated_service_time_cloud = {}
        for f in self.simulation.functions:
            if stats.node2completions[(f, self.simulation.edge)] > 0:
                estimated_service_time[f] = stats.execution_time_sum[(f, self.simulation.edge)] / \
                                            stats.node2completions[(f, self.simulation.edge)]
            else:
                estimated_service_time[f] = 0.1
            if stats.node2completions[(f, self.simulation.cloud)] > 0:
                estimated_service_time_cloud[f] = stats.execution_time_sum[(f, self.simulation.cloud)] / \
                                                  stats.node2completions[(f, self.simulation.cloud)]
            else:
                estimated_service_time_cloud[f] = 0.1

        if self.stats_snapshot is not None:
            arrival_rates = {}
            for f, c in stats.arrivals:
                new_arrivals = stats.arrivals[(f, c)] - self.stats_snapshot["arrivals"][repr((f, c))]
                new_rate = new_arrivals / (self.simulation.t - self.last_update_time)
                self.arrival_rates[(f, c)] = self.arrival_rate_alpha * new_rate + \
                                             (1.0 - self.arrival_rate_alpha) * self.arrival_rates[(f, c)]
        else:
            for f, c in stats.arrivals:
                self.arrival_rates[(f, c)] = stats.arrivals[(f, c)] / self.simulation.t

        cold_start_prob = {x: stats.cold_starts[x] / stats.node2completions[x] for x in stats.node2completions if
                           stats.node2completions[x] > 0}
        for x in stats.node2completions:
            if stats.node2completions[x] == 0:
                cold_start_prob[x] = 0.1  # TODO

        new_probs = optimizer.update_probabilities(self.simulation,
                                                   self.arrival_rates,
                                                   estimated_service_time,
                                                   estimated_service_time_cloud,
                                                   self.simulation.init_time[self.simulation.edge],
                                                   2 * self.simulation.latencies[
                                                       (self.simulation.edge.region, self.simulation.cloud.region)],
                                                   cold_start_prob,
                                                   self.rt_percentile)
        if new_probs is not None:
            self.probs = new_probs
        self.stats_snapshot = self.simulation.stats.to_dict()
        self.last_update_time = self.simulation.t



class LegacyProbabilisticPolicy(ProbabilisticPolicy):

    def __init__(self, simulation):
        super().__init__(simulation)

    def update(self):
        stats = self.simulation.stats

        estimated_service_time = {}
        estimated_service_time_cloud = {}
        for f in self.simulation.functions:
            if stats.node2completions[(f, self.simulation.edge)] > 0:
                estimated_service_time[f] = stats.execution_time_sum[(f, self.simulation.edge)] / \
                                            stats.node2completions[(f, self.simulation.edge)]
            else:
                estimated_service_time[f] = 0.1
            if stats.node2completions[(f, self.simulation.cloud)] > 0:
                estimated_service_time_cloud[f] = stats.execution_time_sum[(f, self.simulation.cloud)] / \
                                                  stats.node2completions[(f, self.simulation.cloud)]
            else:
                estimated_service_time_cloud[f] = 0.1

        if self.stats_snapshot is not None:
            arrival_rates = {}
            for f, c in stats.arrivals:
                new_arrivals = stats.arrivals[(f, c)] - self.stats_snapshot["arrivals"][repr((f, c))]
                new_rate = new_arrivals / (self.simulation.t - self.last_update_time)
                self.arrival_rates[(f, c)] = self.arrival_rate_alpha * new_rate + \
                                             (1.0 - self.arrival_rate_alpha) * self.arrival_rates[(f, c)]
        else:
            for f, c in stats.arrivals:
                self.arrival_rates[(f, c)] = stats.arrivals[(f, c)] / self.simulation.t

        new_probs = optimizer_legacy.update_probabilities(self.simulation,
                                                          self.arrival_rates,
                                                          estimated_service_time,
                                                          estimated_service_time_cloud,
                                                          self.simulation.init_time[self.simulation.edge],
                                                          2 * self.simulation.latencies[(
                                                              self.simulation.edge.region,
                                                              self.simulation.cloud.region)])
        if new_probs is not None:
            self.probs = new_probs
        self.stats_snapshot = self.simulation.stats.to_dict()
        self.last_update_time = self.simulation.t


class RandomPolicy(ProbabilisticPolicy):

    def __init__(self, simulation):
        super().__init__(simulation)
        self.probs = {(f, c): [0.33, 0.33, 1 - 0.66] for f in simulation.functions for c in simulation.classes}

    def schedule(self, f, c):
        return super().schedule(f, c)

    def update(self):
        pass


class GreedyPolicy(Policy):

    def __init__(self, simulation):
        super().__init__(simulation)
        self.cold_start_prob = {}
        self.estimated_service_time = {}
        self.estimated_service_time_cloud = {}
        self.estimated_latency = 0

    def schedule(self, f, c):
        latency_local = self.estimated_service_time.get(f, 0) + \
                        self.cold_start_prob.get((f, self.simulation.edge), 1) * \
                        self.simulation.init_time[self.simulation.edge]
        latency_cloud = self.estimated_service_time_cloud.get(f, 0) + 2 * self.simulation.latencies[(
            self.simulation.edge.region, self.simulation.cloud.region)] + \
                        self.cold_start_prob.get((f, self.simulation.cloud), 1) * self.simulation.init_time[
                            self.simulation.cloud]

        if self.can_execute_locally(self.simulation.edge, f) and latency_local < latency_cloud:
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD

        return sched_decision

    def update(self):
        print("Updating estimations")
        stats = self.simulation.stats

        self.cold_start_prob = {x: stats.cold_starts[x] / stats.node2completions[x] for x in stats.node2completions if
                                stats.node2completions[x] > 0}
        for x in stats.node2completions:
            if stats.node2completions[x] == 0:
                self.cold_start_prob[x] = 0.1  # TODO

        for f in self.simulation.functions:
            if stats.node2completions[(f, self.simulation.edge)] > 0:
                self.estimated_service_time[f] = stats.execution_time_sum[(f, self.simulation.edge)] / \
                                                 stats.node2completions[(f, self.simulation.edge)]
            else:
                self.estimated_service_time[f] = 0.1
            if stats.node2completions[(f, self.simulation.cloud)] > 0:
                self.estimated_service_time_cloud[f] = stats.execution_time_sum[(f, self.simulation.cloud)] / \
                                                       stats.node2completions[(f, self.simulation.cloud)]
            else:
                self.estimated_service_time_cloud[f] = 0.1

        for f in self.simulation.functions:
            print(f, self.estimated_service_time[f], self.estimated_service_time_cloud[f])
        print(self.cold_start_prob)


class GreedyPolicyWithCostMinimization(GreedyPolicy):

    def schedule(self, f, c):
        latency_local = self.estimated_service_time.get(f, 0) + \
                        self.cold_start_prob.get((f, self.simulation.edge), 1) * \
                        self.simulation.init_time[self.simulation.edge]

        latency_cloud = self.estimated_service_time_cloud.get(f, 0) + 2 * self.simulation.latencies[(
            self.simulation.edge.region, self.simulation.cloud.region)] + \
                        self.cold_start_prob.get((f, self.simulation.cloud), 1) * self.simulation.init_time[
                            self.simulation.cloud]

        if latency_local < c.max_rt and self.can_execute_locally(self.simulation.edge, f):
            # Choose the configuration with minimum cost (edge execution) if both configuration can execute within
            # the deadline
            sched_decision = SchedulerDecision.EXEC
        elif latency_cloud < c.max_rt:
            sched_decision = SchedulerDecision.OFFLOAD
        elif self.can_execute_locally(self.simulation.edge, f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD

        return sched_decision
