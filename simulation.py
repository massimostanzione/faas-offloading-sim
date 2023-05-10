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
    arrival_proc: ArrivalProcess = None
    offloaded_from: [Node] = field(default_factory=list)

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
    offloaded_from: [Node] = None


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

        self.stats = Stats(self, self.functions, self.classes, self.infra)

        self.first_stat_print = True
        self.external_arrivals_allowed = True

        # Seeds
        seed = self.config.getint(conf.SEC_SIM, conf.SEED, fallback=1)
        ss = SeedSequence(seed)
        n_arrival_processes = sum([len(arrival_procs) for arrival_procs in self.node2arrivals.values()])
        # Spawn off child SeedSequences to pass to child processes.
        child_seeds = ss.spawn(3 + 2*n_arrival_processes)
        self.service_rng = default_rng(child_seeds[0])
        self.node_choice_rng = default_rng(child_seeds[1])
        self.policy_rng1 = default_rng(child_seeds[2])

        i = 3
        for n,arvs in self.node2arrivals.items():
            for arv in arvs:
                arv.init_rng(default_rng(child_seeds[i]), default_rng(child_seeds[i+1]))
                i += 2


    def new_policy (self, configured_policy, node):
        if configured_policy == "basic":
            return policy.BasicPolicy(self, node)
        if configured_policy == "cloud":
            return policy.CloudPolicy(self, node)
        elif configured_policy == "probabilistic":
            return probabilistic.ProbabilisticPolicy(self, node)
        elif configured_policy == "probabilistic-legacy":
            return probabilistic.LegacyProbabilisticPolicy(self, node)
        elif configured_policy == "greedy":
            return policy.GreedyPolicy(self, node)
        elif configured_policy == "greedy-min-cost":
            return policy.GreedyPolicyWithCostMinimization(self, node)
        elif configured_policy == "random":
            return probabilistic.RandomPolicy(self, node)
        else:
            raise RuntimeError(f"Unknown policy: {configured_policy}")


    def run (self):
        # Simulate
        self.close_the_door_time = self.config.getfloat(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, fallback=100)
        self.events = []
        self.t = 0.0
        self.node2policy = {}

        # Policy
        policy_name = self.config.get(conf.SEC_POLICY, conf.POLICY_NAME, fallback="basic")
        for n in self.infra.get_edge_nodes():
            self.node2policy[n] = self.new_policy(policy_name, n)
        for n in self.infra.get_cloud_nodes():
            self.node2policy[n] = self.new_policy("cloud", n)

        self.policy_update_interval = self.config.getfloat(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, fallback=-1)
        self.stats_print_interval = self.config.getfloat(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, fallback=-1)
        self.stats_file = sys.stdout


        # Other params
        self.init_time = {}
        for node in self.infra.get_nodes():
            self.init_time[node] = self.config.getfloat(conf.SEC_CONTAINER, conf.BASE_INIT_TIME, fallback=0.7)/node.speedup
        self.expiration_timeout = self.config.getfloat(conf.SEC_CONTAINER, conf.EXPIRATION_TIMEOUT, fallback=600)


        if not self.config.getboolean(conf.SEC_SIM, conf.PLOT_RESP_TIMES, fallback=False):
            self.resp_time_samples = {}
        else:
            self.resp_time_samples = {(f,c): [] for f in self.functions for c in f.get_invoking_classes()}

        for n, arvs in self.node2arrivals.copy().items():
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
        if not self.external_arrivals_allowed:
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
            self.external_arrivals_allowed = False


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
        #print(event)
        #print(t)
        if isinstance(event, Arrival):
            self.handle_arrival(event)
        elif isinstance(event, Completion):
            self.handle_completion(event)
        elif isinstance(event, PolicyUpdate):
            for p in self.node2policy.values():
                p.update()
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

        # Account for the time needed to send back the result
        if event.offloaded_from != None:
            curr_node = n
            for remote_node in reversed(event.offloaded_from):
                rt += self.infra.get_latency(curr_node, remote_node)
                curr_node = remote_node

        self.stats.resp_time_sum[(f,c,n)] += rt
        if (f,c,n) in self.resp_time_samples:
            self.resp_time_samples[(f,c,n)].append(rt)
        self.stats.completions[(f,c,n)] += 1
        self.stats.node2completions[(f,n)] += 1
        self.stats.execution_time_sum[(f,n)] += duration
        self.stats.raw_utility += c.utility
        if c.max_rt <= 0.0 or rt <= c.max_rt:
            self.stats.utility += c.utility
        else:
            self.stats.violations[(f,c,n)] += 1

        if n.cost > 0.0:
            self.stats.cost += duration * f.memory/1024 * n.cost

        n.warm_pool.append((f, self.t + self.expiration_timeout))
        if self.external_arrivals_allowed:
            self.schedule(self.t + self.expiration_timeout, CheckExpiredContainers(n)) 


    def do_offload (self, arrival, target_node):
        latency = self.infra.get_latency(arrival.node, target_node)
        remote_arv = Arrival(target_node, arrival.function, arrival.qos_class, offloaded_from=arrival.offloaded_from.copy())
        remote_arv.offloaded_from.append(arrival.node)

        self.schedule(self.t + latency + OFFLOADING_OVERHEAD, remote_arv)

    def handle_arrival (self, event):
        n = event.node 
        external = len(event.offloaded_from) == 0
        arv_proc = event.arrival_proc
        f = event.function
        c = event.qos_class
        if external:
            self.stats.arrivals[(f,c,n)] += 1
        #print(f"Arrived {f}-{c} @ {self.t}")

        # Policy
        sched_decision = self.node2policy[n].schedule(f,c)

        if sched_decision == SchedulerDecision.EXEC:
            speedup = n.speedup
            duration = self.service_rng.gamma(1.0/f.serviceSCV, f.serviceMean*f.serviceSCV/speedup) 
            # check warm or cold
            if f in n.warm_pool:
                n.warm_pool.remove(f)
                init_time = 0
            else:
                assert(n.curr_memory >= f.memory)
                n.curr_memory -= f.memory
                self.stats.cold_starts[(f,n)] += 1
                init_time = self.init_time[n]
            self.schedule(self.t + init_time + duration, Completion(self.t, f,c, n, init_time > 0, duration, event.offloaded_from))
        elif sched_decision == SchedulerDecision.DROP:
            self.stats.dropped_reqs[(f,c,n)] += 1
        elif sched_decision == SchedulerDecision.OFFLOAD:
            self.stats.offloaded[(f,c,n)] += 1
            remote_node = self.infra.get_cloud_nodes()[0]
            self.do_offload(event, remote_node)  # TODO pick the node

        # Schedule next (if this is an external arrival)
        if external:
            self.__schedule_next_arrival(n, arv_proc)
