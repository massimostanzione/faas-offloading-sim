from enum import Enum, StrEnum, auto
from pacsltk import perfmodel

import conf

COLD_START_PROB_INITIAL_GUESS = 0.0

class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD_CLOUD = 2
    OFFLOAD_EDGE = 3
    DROP = 4

class ColdStartEstimation(StrEnum):
    NO = auto()
    NAIVE = auto()
    NAIVE_PER_FUNCTION = "naive-per-function"
    PACS = auto()
    FULL_KNOWLEDGE = "full-knowledge"




class Policy:

    def __init__(self, simulation, node):
        self.simulation = simulation
        self.node = node
        self.__edge_peers = None

    def schedule(self, function, qos_class, offloaded_from):
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

    def _get_edge_peers (self):
        if self.__edge_peers is None:
            # TODO: need to refresh over time?
            self.__edge_peers = self.simulation.infra.get_neighbors(self.node, self.simulation.node_choice_rng, self.simulation.max_neighbors)
        return self.__edge_peers

    def _get_edge_peers_probabilities (self):
        peers = self._get_edge_peers()
        total_memory = sum([x.curr_memory for x in peers])
        if total_memory > 0.0:
            probs = [x.curr_memory/total_memory for x in peers]
        else:
            n = len(peers)
            probs = [1.0/n for x in peers]
        return probs, peers

    # Picks a node for Edge offloading
    def pick_edge_node (self, fun, qos):
        # Pick peers based on resource availability
        probs, peers = self._get_edge_peers_probabilities()
        return self.simulation.node_choice_rng.choice(peers, p=probs)



class BasicPolicy(Policy):

    def schedule(self, f, c, offloaded_from):
        if self.can_execute_locally(f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD_CLOUD

        return sched_decision

class BasicEdgePolicy(Policy):

    def schedule(self, f, c, offloaded_from):
        if self.can_execute_locally(f):
            sched_decision = SchedulerDecision.EXEC
        elif len(offloaded_from) == 0:
            sched_decision = SchedulerDecision.OFFLOAD_EDGE
        else:
            sched_decision = SchedulerDecision.DROP

        return sched_decision

class CloudPolicy(Policy):

    def schedule(self, f, c, offloaded_from):
        if self.can_execute_locally(f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.DROP

        return sched_decision



class GreedyPolicy(Policy):

    def __init__(self, simulation, node):
        super().__init__(simulation, node)
        self.cold_start_prob = {}
        self.cold_start_prob_cloud = {}
        self.estimated_service_time = {}
        self.estimated_service_time_cloud = {}
        self.estimated_latency = 0

        self.local_cold_start_estimation = ColdStartEstimation(self.simulation.config.get(conf.SEC_POLICY, conf.LOCAL_COLD_START_EST_STRATEGY, fallback=ColdStartEstimation.NAIVE))
        self.cloud_cold_start_estimation = ColdStartEstimation(self.simulation.config.get(conf.SEC_POLICY, conf.CLOUD_COLD_START_EST_STRATEGY, fallback=ColdStartEstimation.NAIVE))

        cloud_region = node.region.default_cloud
        self.cloud = self.simulation.node_choice_rng.choice(self.simulation.infra.get_region_nodes(cloud_region), 1)[0]

    def schedule(self, f, c, offloaded_from):
        if self.local_cold_start_estimation == ColdStartEstimation.FULL_KNOWLEDGE:
            if f in self.node.warm_pool:
                self.cold_start_prob[(f, self.node)] = 0
            else:
                self.cold_start_prob[(f, self.node)] = 1
        if self.cloud_cold_start_estimation == ColdStartEstimation.FULL_KNOWLEDGE:
            if f in self.cloud.warm_pool:
                self.cold_start_prob[(f, self.cloud)] = 0
            else:
                self.cold_start_prob[(f, self.cloud)] = 1

        latency_local = self.estimated_service_time.get(f, 0) + \
                        self.cold_start_prob.get((f, self.node), 1) * \
                        self.simulation.init_time[(f,self.node)]

        latency_cloud = self.estimated_service_time_cloud.get(f, 0) +\
                2 * self.simulation.infra.get_latency(self.node, self.cloud) + \
                        self.cold_start_prob.get((f, self.cloud), 1) * self.simulation.init_time[(f,self.cloud)]

        if self.can_execute_locally(f) and latency_local < latency_cloud:
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD_CLOUD

        return sched_decision

    def update_cold_start (self, stats):
        #
        # LOCAL NODE
        #
        if self.local_cold_start_estimation == ColdStartEstimation.PACS:
            for f in self.simulation.functions:
                total_arrival_rate = max(0.001, sum([stats.arrivals.get((f,x,self.node), 0.0) for x in self.simulation.classes])/self.simulation.t)
                props1, _ = perfmodel.get_sls_warm_count_dist(total_arrival_rate,
                                                            self.estimated_service_time[f],
                                                            self.estimated_service_time[f] + self.simulation.init_time[self.node],
                                                            self.simulation.expiration_timeout)
                self.cold_start_prob[(f, self.node)] = props1["cold_prob"]
        elif self.local_cold_start_estimation == ColdStartEstimation.NAIVE:
            # Same prob for every function
            node_compl = sum([stats.node2completions[(_f,self.node)] for _f in self.simulation.functions])
            node_cs = sum([stats.cold_starts[(_f,self.node)] for _f in self.simulation.functions])
            for f in self.simulation.functions:
                if node_compl > 0:
                    self.cold_start_prob[(f, self.node)] = node_cs / node_compl
                else:
                    self.cold_start_prob[(f, self.node)] = COLD_START_PROB_INITIAL_GUESS
        elif self.local_cold_start_estimation == ColdStartEstimation.NAIVE_PER_FUNCTION:
            for f in self.simulation.functions:
                if stats.node2completions.get((f,self.node), 0) > 0:
                    self.cold_start_prob[(f, self.node)] = stats.cold_starts.get((f,self.node),0) / stats.node2completions.get((f,self.node),0)
                else:
                    self.cold_start_prob[(f, self.node)] = COLD_START_PROB_INITIAL_GUESS
        elif self.local_cold_start_estimation == ColdStartEstimation.NO: 
            for f in self.simulation.functions:
                self.cold_start_prob[(f, self.node)] = 0

        # CLOUD
        #
        if self.cloud_cold_start_estimation == ColdStartEstimation.PACS:
            for f in self.simulation.functions:
                total_arrival_rate = max(0.001, sum([stats.arrivals.get((f,x,self.cloud), 0.0) for x in self.simulation.classes])/self.simulation.t)
                props1, _ = perfmodel.get_sls_warm_count_dist(total_arrival_rate,
                                                            self.estimated_service_time[f],
                                                            self.estimated_service_time[f] + self.simulation.init_time[self.cloud],
                                                            self.simulation.expiration_timeout)
                self.cold_start_prob[(f, self.cloud)] = props1["cold_prob"]
        elif self.cloud_cold_start_estimation == ColdStartEstimation.NAIVE:
            # Same prob for every function
            node_compl = sum([stats.node2completions[(_f,self.cloud)] for _f in self.simulation.functions])
            node_cs = sum([stats.cold_starts[(_f,self.cloud)] for _f in self.simulation.functions])
            for f in self.simulation.functions:
                if node_compl > 0:
                    self.cold_start_prob[(f, self.cloud)] = node_cs / node_compl
                else:
                    self.cold_start_prob[(f, self.cloud)] = COLD_START_PROB_INITIAL_GUESS
        elif self.cloud_cold_start_estimation == ColdStartEstimation.NAIVE_PER_FUNCTION:
            for f in self.simulation.functions:
                if stats.node2completions.get((f,self.cloud), 0) > 0:
                    self.cold_start_prob[(f, self.cloud)] = stats.cold_starts.get((f,self.cloud),0) / stats.node2completions.get((f,self.cloud),0)
                else:
                    self.cold_start_prob[(f, self.cloud)] = COLD_START_PROB_INITIAL_GUESS
        elif self.cloud_cold_start_estimation == ColdStartEstimation.NO: 
            for f in self.simulation.functions:
                self.cold_start_prob[(f, self.cloud)] = 0

        print(f"Cold start prob: {self.cold_start_prob}")

    def update(self):
        print("Updating estimations")
        stats = self.simulation.stats


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

        self.update_cold_start(stats)


class GreedyPolicyWithCostMinimization(GreedyPolicy):

    def __init__ (self, simulation, node):
        super().__init__(simulation, node)
        cloud_region = node.region.default_cloud
        assert(cloud_region is not None)
        self.cloud = self.simulation.node_choice_rng.choice(self.simulation.infra.get_region_nodes(cloud_region), 1)[0]

    def schedule(self, f, c, offloaded_from):
        if self.local_cold_start_estimation == ColdStartEstimation.FULL_KNOWLEDGE:
            if f in self.node.warm_pool:
                self.cold_start_prob[(f, self.node)] = 0
            else:
                self.cold_start_prob[(f, self.node)] = 1
        if self.cloud_cold_start_estimation == ColdStartEstimation.FULL_KNOWLEDGE:
            if f in self.cloud.warm_pool:
                self.cold_start_prob[(f, self.cloud)] = 0
            else:
                self.cold_start_prob[(f, self.cloud)] = 1

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
            sched_decision = SchedulerDecision.OFFLOAD_CLOUD
        elif self.can_execute_locally(f):
            sched_decision = SchedulerDecision.EXEC
        else:
            sched_decision = SchedulerDecision.OFFLOAD_CLOUD

        return sched_decision

