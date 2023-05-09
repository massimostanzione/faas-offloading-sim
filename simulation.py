import configparser
from dataclasses import dataclass, field
from heapq import heappop, heappush
import numpy as np
from numpy.random import SeedSequence, default_rng
import sys

import conf
import utils.plot
from policy import SchedulerDecision
import policy
import probabilistic
from faas import *
from arrivals import ArrivalProcess
from infrastructure import *
from statistics import Stats

@dataclass
class Event:
    canceled: bool = field(default=False, init=False)

    # XXX: ugly workaround to avoid issues with the heapq (in case of events
    # scheduled at the same time)
    def __lt__(self, other):
        return True

    def __le__(self,other):
        return True


@dataclass
class Arrival(Event):
    node: Node
    function: Function
    qos_class: QoSClass
    arrival_proc: ArrivalProcess

@dataclass
class CheckExpiredContainers(Event):
    node: Node

@dataclass
class PolicyUpdate(Event):
    pass

@dataclass
class StatPrinter(Event):
    pass

@dataclass
class Completion(Event):
    arrival: float
    function: Function
    qos_class: QoSClass
    node: Node
    cold: bool
    exec_time: float


OFFLOADING_OVERHEAD = 0.005
ARRIVAL_TRACE_PERIOD = 60.0



@dataclass
class Simulation:

    config: configparser.ConfigParser
    infra: Infrastructure
    functions: [Function]
    classes: [QoSClass]
    node2arrivals: dict

    def __post_init__ (self):
        assert(len(self.functions) > 0)
        assert(len(self.classes) > 0)
        # TODO: legacy compatibility
        self.edge = self.infra.get_edge_nodes()[0]
        self.cloud = self.infra.get_cloud_nodes()[0]

        self.stats = Stats(self, self.functions, self.classes, [self.edge,self.cloud])
        #self.function_classes = [(f,c) for f in self.functions for c in f.get_invoking_classes()]


        self.first_stat_print = True
        self.arrivals_allowed = True

    def new_policy (self, configured_policy):
        if configured_policy == "basic":
            return policy.BasicPolicy(self)
        elif configured_policy == "probabilistic":
            return probabilistic.ProbabilisticPolicy(self)
        elif configured_policy == "probabilistic-legacy":
            return probabilistic.LegacyProbabilisticPolicy(self)
        elif configured_policy == "greedy":
            return policy.GreedyPolicy(self)
        elif configured_policy == "greedy-min-cost":
            return policy.GreedyPolicyWithCostMinimization(self)
        elif configured_policy == "random":
            return probabilistic.RandomPolicy(self)
        else:
            raise RuntimeError(f"Unknown policy: {configured_policy}")


    def run (self):
        # Simulate
        self.close_the_door_time = self.config.getfloat(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, fallback=100)
        self.events = []
        self.t = 0.0

        # Policy
        policy_name = self.config.get(conf.SEC_POLICY, conf.POLICY_NAME, fallback="basic")
        self.policy = self.new_policy(policy_name)
        self.policy_update_interval = self.config.getfloat(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, fallback=-1)
        self.stats_print_interval = self.config.getfloat(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, fallback=-1)
        self.stats_file = sys.stdout


        # Seeds
        seed = self.config.getint(conf.SEC_SIM, conf.SEED, fallback=1)
        ss = SeedSequence(seed)
        n_arrival_processes = sum([len(arrival_procs) for arrival_procs in self.node2arrivals.values()])
        # Spawn off child SeedSequences to pass to child processes.
        child_seeds = ss.spawn(2 + 2*n_arrival_processes)
        self.service_rng = default_rng(child_seeds[0])
        self.latency_rng = default_rng(child_seeds[1])

        i = 2
        for n,arvs in self.node2arrivals.items():
            for arv in arvs:
                arv.init_rng(default_rng(child_seeds[i]), default_rng(child_seeds[i+1]))
                i += 2

        # Other params
        self.init_time = {}
        for node in [self.edge, self.cloud]:
            self.init_time[node] = self.config.getfloat(conf.SEC_CONTAINER, conf.BASE_INIT_TIME, fallback=0.7)/node.speedup
        self.expiration_timeout = self.config.getfloat(conf.SEC_CONTAINER, conf.EXPIRATION_TIMEOUT, fallback=600)


        if not self.config.getboolean(conf.SEC_SIM, conf.PLOT_RESP_TIMES, fallback=False):
            self.resp_time_samples = {}
        else:
            self.resp_time_samples = {(f,c): [] for f in self.functions for c in f.get_invoking_classes()}

        for n, arvs in self.node2arrivals.items():
            for arv in arvs:
                self.__schedule_next_arrival(n, arv)

        if len(self.events) == 0:
            # No arrivals
            print("No arrivals configured.")
            exit(1)

        if self.policy_update_interval > 0.0:
            self.schedule(self.policy_update_interval, PolicyUpdate())
        if self.stats_print_interval > 0.0:
            self.schedule(self.stats_print_interval, StatPrinter())
            stats_print_filename = self.config.get(conf.SEC_SIM, conf.STAT_PRINT_FILE, fallback="")
            if len(stats_print_filename) > 0:
                self.stats_file = open(stats_print_filename, "w")

        while len(self.events) > 0:
            t,e = heappop(self.events)
            self.handle(t, e)

        if self.stats_print_interval > 0:
            self.print_periodic_stats()
            print("]", file=self.stats_file)
            if self.stats_file != sys.stdout:
                self.stats_file.close()
                self.stats.print(sys.stdout)
        else:
            self.stats.print(sys.stdout)

        if len(self.resp_time_samples) > 0:
            plot.plot_rt_cdf(self.resp_time_samples)

        for n, arvs in self.node2arrivals.items():
            for arv in arvs:
                arv.close()

        return self.stats


    
    def __schedule_next_arrival(self, node, arrival_proc):
        if not self.arrivals_allowed:
            return

        c = arrival_proc.next_class()
        iat = arrival_proc.next_iat()
        f = arrival_proc.function

        if iat >= 0.0 and self.t + iat < self.close_the_door_time:
            self.schedule(self.t + iat, Arrival(node,f,c, arrival_proc))
        else:
            arrival_proc.close()
            self.node2arrivals[node].remove(arrival_proc)
            if len(self.node2arrivals[node]) == 0:
                del(self.node2arrivals[node])

        if len(self.node2arrivals) == 0:
            # Little hack: remove all expiration from the event list (we do not
            # need to wait for them)
            for item in self.events:
                if isinstance(item[1], CheckExpiredContainers) \
                   or isinstance(item[1], PolicyUpdate) \
                   or isinstance(item[1], StatPrinter):
                    item[1].canceled = True
            self.arrivals_allowed = False


    def schedule (self, t, event):
        heappush(self.events, (t, event))

    def print_periodic_stats (self):
        of = self.stats_file if self.stats_file is not None else sys.stdout
        if not self.first_stat_print:
            print(",", end='', file=of)
        else:
            print("[", file=of)
        self.stats.print(of)
        self.first_stat_print = False

    def handle (self, t, event):
        if event.canceled:
            return
        self.t = t
        if isinstance(event, Arrival):
            self.handle_arrival(event)
        elif isinstance(event, Completion):
            self.handle_completion(event)
        elif isinstance(event, PolicyUpdate):
            self.policy.update()
            self.schedule(t + self.policy_update_interval, event)
        elif isinstance(event, StatPrinter):
            self.print_periodic_stats()
            self.schedule(t + self.stats_print_interval, event)
        elif isinstance(event, CheckExpiredContainers):
            if len(event.node.warm_pool) == 0:
                return
            f,timeout = event.node.warm_pool.front()
            if timeout < t:
                event.node.curr_memory += f.memory
                event.node.warm_pool.pool = event.node.warm_pool.pool[1:]
        else:
            raise RuntimeError("")

    def handle_completion (self, event):
        rt = self.t - event.arrival
        f = event.function
        c = event.qos_class
        n = event.node
        duration = event.exec_time
        #print(f"Completed {f}-{c}: {rt}")

        self.stats.resp_time_sum[(f,c)] += rt
        if (f,c) in self.resp_time_samples:
            self.resp_time_samples[(f,c)].append(rt)
        self.stats.completions[(f,c)] += 1
        self.stats.node2completions[(f,n)] += 1
        self.stats.execution_time_sum[(f,n)] += duration
        self.stats.raw_utility += c.utility
        if c.max_rt <= 0.0 or rt <= c.max_rt:
            self.stats.utility += c.utility
        else:
            self.stats.violations[(f,c)] += 1

        if n.cost > 0.0:
            self.stats.cost += duration * f.memory/1024 * n.cost

        n.warm_pool.append((f, self.t + self.expiration_timeout))
        if self.arrivals_allowed:
            self.schedule(self.t + self.expiration_timeout, CheckExpiredContainers(n)) 


    def handle_offload (self, f, c):
        if not f in self.cloud.warm_pool and self.cloud.curr_memory < f.memory:
            reclaimed = self.cloud.warm_pool.reclaim_memory(f.memory - self.cloud.curr_memory)
            self.cloud.curr_memory += reclaimed
            if self.cloud.curr_memory < f.memory:
                self.stats.dropped_reqs[(f,c)] += 1
                return

        speedup = self.cloud.speedup
        duration = self.service_rng.gamma(1.0/f.serviceSCV, f.serviceMean*f.serviceSCV/speedup) # TODO: check
        # check warm or cold
        if f in self.cloud.warm_pool:
            self.cloud.warm_pool.remove(f)
            init_time = 0
        else:
            self.cloud.curr_memory -= f.memory
            assert(self.cloud.curr_memory >= 0)
            self.stats.cold_starts[(f,self.cloud)] += 1
            init_time = self.init_time[self.cloud]
        rtt = self.infra.get_latency(self.edge.region,self.cloud.region) +\
                self.infra.get_latency(self.cloud.region, self.edge.region)

        self.schedule(self.t + rtt + OFFLOADING_OVERHEAD + init_time + duration, Completion(self.t, f,c, self.cloud, init_time > 0, duration))

    def handle_arrival (self, event):
        n = event.node # TODO !!!
        arv_proc = event.arrival_proc
        f = event.function
        c = event.qos_class
        self.stats.arrivals[(f,c)] += 1
        #print(f"Arrived {f}-{c} @ {self.t}")

        # Policy
        sched_decision = self.policy.schedule(f,c)

        if sched_decision == SchedulerDecision.EXEC:
            speedup = self.edge.speedup
            duration = self.service_rng.gamma(1.0/f.serviceSCV, f.serviceMean*f.serviceSCV/speedup) # TODO: check
            # check warm or cold
            if f in self.edge.warm_pool:
                self.edge.warm_pool.remove(f)
                init_time = 0
            else:
                self.edge.curr_memory -= f.memory
                assert(self.edge.curr_memory >= 0)
                self.stats.cold_starts[(f,self.edge)] += 1
                init_time = self.init_time[self.edge]
            self.schedule(self.t + init_time + duration, Completion(self.t, f,c, self.edge, init_time > 0, duration))
        elif sched_decision == SchedulerDecision.DROP:
            self.stats.dropped_reqs[(f,c)] += 1
        elif sched_decision == SchedulerDecision.OFFLOAD:
            self.stats.offloaded[(f,c)] += 1
            self.handle_offload(f,c)

        # Schedule next
        self.__schedule_next_arrival(n, arv_proc)
