import statistics
import numpy as np

import conf
from lp_optimizer import LPOptimizer
from optimizer_iterated_lp import IteratedLPOptimizer
from optimizer_nonlinear import NonlinearOptimizer
from policy import Policy, SchedulerDecision, ColdStartEstimation, COLD_START_PROB_INITIAL_GUESS
from optimization import OptProblemParams, Optimizer
from probabilistic import ProbabilisticPolicy



class CreditBasedPolicy (ProbabilisticPolicy):

    # Probability vector: p_L, p_C, p_E, p_D

    def __init__(self, simulation, node, strict_budget_enforce=False):
        super().__init__(simulation, node, strict_budget_enforce)
        self.probs = {(f, c): [0.5, 0.5, 0., 0.] for f in simulation.functions for c in simulation.classes}

        self.credits = {(f,c): 128 for f,c in self.probs}
        self.credit_rates = {}
        self.credit_per_request = {}
        self.compute_credit_rates()
        self._last_credit_update = 0

    def compute_credit_rates (self):
        for f in self.simulation.functions:
            if not f in self.estimated_service_time:
                self.credit_per_request[f] = 128
            else:
                self.credit_per_request[f] = f.memory*self.estimated_service_time[f]
        for f,c in self.probs:
            probs = self.probs[(f,c)]
            if not (f,c) in self.arrival_rates or not f in self.estimated_service_time:
                self.credit_rates[(f,c)] = 128 # TODO
            else:
                self.credit_rates[(f,c)] = probs[0]*self.arrival_rates[(f,c)]*self.credit_per_request[f]

    def add_credits (self):
        t = self.simulation.t - self._last_credit_update
        for f,c in self.credits:
            self.credits[(f,c)] += t*self.credit_rates[(f,c)]

    def notify_completion (self, f, c, resp_time, duration):
        # Note: we had already tentatively decreased by credit_per_request
        self.credits[(f,c)] -= (f.memory*duration - self.credit_per_request[f]) 


    def schedule(self, f, c, offloaded_from):
        self.add_credits()

        # check if local execution is possible based on credits
        if self.credits[(f,c)] >= self.credit_per_request[f]:
            if self.node.can_execute_or_enqueue(f,c):
                self.credits[(f,c)] -= self.credit_per_request[f]  # TODO: tentative (we don't know the actual duration)
                return SchedulerDecision.EXEC, None
            else:
                return (SchedulerDecision.DROP, None) # TODO: better fallback?

        # if no local, randomly decide what to do based on probs 
        probabilities = self.probs[(f, c)].copy()
        probabilities[SchedulerDecision.EXEC.value-1] = 0
        # If the request has already been offloaded, cannot offload again
        if len(offloaded_from) > 0 and not self.allow_multi_offloading: 
            probabilities[SchedulerDecision.OFFLOAD_EDGE.value-1] = 0
            probabilities[SchedulerDecision.OFFLOAD_CLOUD.value-1] = 0
            s = sum(probabilities)
            if not s > 0.0:
                return (SchedulerDecision.DROP, None)
            else:
                probabilities = [x/s for x in probabilities]

        if self.simulation.stats.cost / self.simulation.t * 3600 > self.budget:
            probabilities[SchedulerDecision.OFFLOAD_CLOUD.value-1] = 0

        s = sum(probabilities)
        if not s > 0.0:
            if c.utility > 0.0 and \
                    self.simulation.stats.cost / self.simulation.t * 3600 < self.budget \
                    and (self.allow_multi_offloading or len(offloaded_from) == 0):
                return (SchedulerDecision.OFFLOAD_CLOUD, None)
            else:
                return (SchedulerDecision.DROP, None)

        probabilities = [x/s for x in probabilities]
        return (self.rng.choice(self.possible_decisions, p=probabilities), None)

        
        if decision == SchedulerDecision.OFFLOAD_CLOUD and self.strict_budget_enforce and\
                self.simulation.stats.cost / self.simulation.t * 3600 > self.budget:
            return (SchedulerDecision.DROP, None)

        return (decision, None)

    def update(self):
        self.update_metrics()

        arrivals = sum([self.arrival_rates.get((f,c), 0.0) for f in self.simulation.functions for c in self.simulation.classes])
        if arrivals > 0.0:
            # trigger the optimizer 
            self.update_probabilities()
            self.compute_credit_rates()

        self.stats_snapshot = self.simulation.stats.to_dict()
        self.last_update_time = self.simulation.t

        # reset counters
        self.curr_local_blocked_reqs = 0
        self.curr_local_reqs = 0


class OfflineCreditBasedPolicy (CreditBasedPolicy):


    def __init__(self, simulation, node, strict_budget_enforce=False):
        super().__init__(simulation, node, strict_budget_enforce)

        if not self.edge_enabled:
            # probably redundant, just to be sure
            self.aggregated_edge_memory = 0

        if not self.node in self.simulation.node2arrivals:
            # No arrivals here... just skip
            self.probs = {(f, c): [0.5, 0.5, 0., 0.] for f in simulation.functions for c in simulation.classes}
            return

        self.update_metrics()

        params = OptProblemParams(self.node, 
                self.cloud, 
                self.simulation.functions,
                self.simulation.classes,
                self.arrival_rates, 
                self.estimated_service_time, 
                self.estimated_service_time_cloud, 
                self.init_time_local, 
                self.init_time_cloud, 
                self.cold_start_prob_local,
                self.cold_start_prob_cloud,
                self.cloud_rtt, 
                self.cloud_bw,
                1.0,
                self.local_budget,
                self.aggregated_edge_memory,
                self.estimated_service_time_edge, 
                self.edge_rtt,
                self.cold_start_prob_edge, 
                self.init_time_edge, 
                self.edge_bw)

        self.probs, obj_value = self.optimizer.optimize_probabilities(params)
        self.simulation.stats.optimizer_obj_value[self.node] = obj_value

        # TODO: credits

    def update(self):
        pass

    def update_metrics(self):

        self.estimated_service_time = {}
        self.estimated_service_time_cloud = {}

        for f in self.simulation.functions:
            self.estimated_service_time[f] = f.serviceMean / self.node.speedup
            self.estimated_service_time_cloud[f] = f.serviceMean / self.cloud.speedup
        
        for arv_proc in self.simulation.node2arrivals[self.node]:
            f = arv_proc.function
            # NOTE: this only works for some arrival processes (e.g., not for
            # trace-driven)
            rate_per_class = arv_proc.get_per_class_mean_rate()
            for c,r in rate_per_class.items():
                self.arrival_rates[(f, c)] = r

        self.estimate_cold_start_prob(self.simulation.stats) # stats are empty at this point...

        self.cloud_rtt = 2 * self.simulation.infra.get_latency(self.node, self.cloud)
        self.cloud_bw = self.simulation.infra.get_bandwidth(self.node, self.cloud)

        if self.edge_enabled:
            neighbor_probs, neighbors = self._get_edge_peers_probabilities()
            if len(neighbors) == 0:
                self.aggregated_edge_memory = 0
            else:
                self.aggregated_edge_memory = max(1,sum([x.curr_memory*x.peer_exposed_memory_fraction for x in neighbors]))

            self.edge_rtt = sum([self.simulation.infra.get_latency(self.node, x)*prob for x,prob in zip(neighbors, neighbor_probs)])
            self.edge_bw = sum([self.simulation.infra.get_bandwidth(self.node, x)*prob for x,prob in zip(neighbors, neighbor_probs)])

            self.estimated_service_time_edge = {}
            for f in self.simulation.functions:
                inittime = 0.0
                servtime = 0.0
                for neighbor, prob in zip(neighbors, neighbor_probs):
                    servtime += prob*f.serviceMean/neighbor.speedup
                    inittime += prob*self.simulation.init_time[(f,neighbor)]
                if servtime == 0.0:
                    servtime = self.estimated_service_time[f]
                self.estimated_service_time_edge[f] = servtime
                self.init_time_edge[f] = inittime

            self.estimate_edge_cold_start_prob(self.simulation.stats, neighbors, neighbor_probs)

