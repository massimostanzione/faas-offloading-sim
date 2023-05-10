from enum import Enum

import conf


class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD = 2
    DROP = 3


class Policy:

    def __init__(self, simulation, node):
        self.simulation = simulation
        self.node = node

    def schedule(self, function, qos_class):
        pass

    def update(self):
        pass

    def can_execute_locally(self, f, reclaim_memory=True):
        if f in self.node.warm_pool or self.node.curr_memory >= f.memory:
            return True
        if reclaim_memory:
            reclaimed = self.node.warm_pool.reclaim_memory(f.memory - self.node.curr_memory)
            self.node.curr_memory += reclaimed
        return self.node.curr_memory >= f.memory



class BasicPolicy(Policy):

    def schedule(self, f, c):
        if self.can_execute_locally(f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD

        return sched_decision

class CloudPolicy(Policy):

    def schedule(self, f, c):
        if self.can_execute_locally(f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.DROP

        return sched_decision



class GreedyPolicy(Policy):

    def __init__(self, simulation, node):
        super().__init__(simulation, node)
        self.cold_start_prob = {}
        self.estimated_service_time = {}
        self.estimated_service_time_cloud = {}
        self.estimated_latency = 0

        cloud_region = node.region.default_cloud
        self.cloud = self.simulation.node_choice_rng.choice(self.simulation.infra.get_region_nodes(cloud_region), 1)[0]

    def schedule(self, f, c):
        latency_local = self.estimated_service_time.get(f, 0) + \
                        self.cold_start_prob.get((f, self.node), 1) * \
                        self.simulation.init_time[self.node]

        latency_cloud = self.estimated_service_time_cloud.get(f, 0) +\
                2 * self.simulation.infra.get_latency(self.node, self.cloud) + \
                        self.cold_start_prob.get((f, self.cloud), 1) * self.simulation.init_time[self.cloud]

        if self.can_execute_locally(f) and latency_local < latency_cloud:
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
            if stats.node2completions[(f, self.node)] > 0:
                self.estimated_service_time[f] = stats.execution_time_sum[(f, self.node)] / \
                                                 stats.node2completions[(f, self.node)]
            else:
                self.estimated_service_time[f] = 0.1
            if stats.node2completions[(f, self.cloud)] > 0:
                self.estimated_service_time_cloud[f] = stats.execution_time_sum[(f, self.cloud)] / \
                                                       stats.node2completions[(f, self.cloud)]
            else:
                self.estimated_service_time_cloud[f] = 0.1

        for f in self.simulation.functions:
            print(f, self.estimated_service_time[f], self.estimated_service_time_cloud[f])
        print(self.cold_start_prob)


class GreedyPolicyWithCostMinimization(GreedyPolicy):

    def __init__ (self, simulation, node):
        super().__init__(simulation, node)
        cloud_region = node.region.default_cloud
        assert(cloud_region is not None)
        self.cloud = self.simulation.node_choice_rng.choice(self.simulation.infra.get_region_nodes(cloud_region), 1)[0]

    def schedule(self, f, c):
        latency_local = self.estimated_service_time.get(f, 0) + \
                        self.cold_start_prob.get((f, self.node), 1) * \
                        self.simulation.init_time[self.node]

        latency_cloud = self.estimated_service_time_cloud.get(f, 0) + 2 * self.simulation.infra.get_latency(self.node, self.cloud) + \
                        self.cold_start_prob.get((f, self.cloud), 1) * self.simulation.init_time[
                            self.cloud]

        if latency_local < c.max_rt and self.can_execute_locally(f):
            # Choose the configuration with minimum cost (edge execution) if both configuration can execute within
            # the deadline
            sched_decision = SchedulerDecision.EXEC
        elif latency_cloud < c.max_rt:
            sched_decision = SchedulerDecision.OFFLOAD
        elif self.can_execute_locally(f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD

        return sched_decision
