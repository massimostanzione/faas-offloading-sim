import statistics
import numpy as np

import conf
import optimizer
import optimizer_legacy
from policy import Policy, SchedulerDecision


class ProbabilisticPolicy(Policy):

    # Probability vector: p_e, p_o, p_d

    def __init__(self, simulation, node):
        super().__init__(simulation, node)
        cloud_region = node.region.default_cloud
        self.cloud = self.simulation.node_choice_rng.choice(self.simulation.infra.get_region_nodes(cloud_region), 1)[0]

        self.rng = self.simulation.policy_rng1
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
        if decision == SchedulerDecision.EXEC and not self.can_execute_locally(f):
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
            if stats.node2completions[(f, self.node)] > 0:
                estimated_service_time[f] = stats.execution_time_sum[(f, self.node)] / \
                                            stats.node2completions[(f, self.node)]
            else:
                estimated_service_time[f] = 0.1
            if stats.node2completions[(f, self.cloud)] > 0:
                estimated_service_time_cloud[f] = stats.execution_time_sum[(f, self.cloud)] / \
                                                  stats.node2completions[(f, self.cloud)]
            else:
                estimated_service_time_cloud[f] = 0.1

        if self.stats_snapshot is not None:
            arrival_rates = {}
            for f, c, n in stats.arrivals:
                if n != self.node:
                    continue
                new_arrivals = stats.arrivals[(f, c, self.node)] - self.stats_snapshot["arrivals"][repr((f, c, n))]
                new_rate = new_arrivals / (self.simulation.t - self.last_update_time)
                self.arrival_rates[(f, c)] = self.arrival_rate_alpha * new_rate + \
                                             (1.0 - self.arrival_rate_alpha) * self.arrival_rates[(f, c)]
        else:
            for f, c, n in stats.arrivals:
                if n != self.node:
                    continue
                self.arrival_rates[(f, c)] = stats.arrivals[(f, c, self.node)] / self.simulation.t

        cold_start_prob = {x: stats.cold_starts[x] / stats.node2completions[x] for x in stats.node2completions if
                           stats.node2completions[x] > 0}
        for x in stats.node2completions:
            if stats.node2completions[x] == 0:
                cold_start_prob[x] = 0.1  # TODO

        print(f"[{self.node}] Arrivals: {self.arrival_rates}")

        new_probs = optimizer.update_probabilities(self.node, self.cloud,
                                                   self.simulation,
                                                   self.arrival_rates,
                                                   estimated_service_time,
                                                   estimated_service_time_cloud,
                                                   self.simulation.init_time[self.node],
                                                   2 * self.simulation.infra.get_latency(self.node, self.cloud.region),
                                                   cold_start_prob,
                                                   self.rt_percentile)
        if new_probs is not None:
            self.probs = new_probs
        self.stats_snapshot = self.simulation.stats.to_dict()
        self.last_update_time = self.simulation.t



#class LegacyProbabilisticPolicy(ProbabilisticPolicy):
#
#    def __init__(self, simulation):
#        super().__init__(simulation)
#
#    def update(self):
#        stats = self.simulation.stats
#
#        estimated_service_time = {}
#        estimated_service_time_cloud = {}
#        for f in self.simulation.functions:
#            if stats.node2completions[(f, self.simulation.edge)] > 0:
#                estimated_service_time[f] = stats.execution_time_sum[(f, self.simulation.edge)] / \
#                                            stats.node2completions[(f, self.simulation.edge)]
#            else:
#                estimated_service_time[f] = 0.1
#            if stats.node2completions[(f, self.simulation.cloud)] > 0:
#                estimated_service_time_cloud[f] = stats.execution_time_sum[(f, self.simulation.cloud)] / \
#                                                  stats.node2completions[(f, self.simulation.cloud)]
#            else:
#                estimated_service_time_cloud[f] = 0.1
#
#        if self.stats_snapshot is not None:
#            arrival_rates = {}
#            for f, c in stats.arrivals:
#                new_arrivals = stats.arrivals[(f, c)] - self.stats_snapshot["arrivals"][repr((f, c))]
#                new_rate = new_arrivals / (self.simulation.t - self.last_update_time)
#                self.arrival_rates[(f, c)] = self.arrival_rate_alpha * new_rate + \
#                                             (1.0 - self.arrival_rate_alpha) * self.arrival_rates[(f, c)]
#        else:
#            for f, c in stats.arrivals:
#                self.arrival_rates[(f, c)] = stats.arrivals[(f, c)] / self.simulation.t
#
#        new_probs = optimizer_legacy.update_probabilities(self.simulation,
#                                                          self.arrival_rates,
#                                                          estimated_service_time,
#                                                          estimated_service_time_cloud,
#                                                          self.simulation.init_time[self.simulation.edge],
#                                                          2 * self.simulation.latencies[(
#                                                              self.simulation.edge.region,
#                                                              self.simulation.cloud.region)])
#        if new_probs is not None:
#            self.probs = new_probs
#        self.stats_snapshot = self.simulation.stats.to_dict()
#        self.last_update_time = self.simulation.t


class RandomPolicy(ProbabilisticPolicy):

    def __init__(self, simulation, node):
        super().__init__(simulation, node)
        self.probs = {(f, c): [0.33, 0.33, 1 - 0.66] for f in simulation.functions for c in simulation.classes}

    def schedule(self, f, c):
        return super().schedule(f, c)

    def update(self):
        pass

