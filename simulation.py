import configparser
from dataclasses import dataclass, field
from heapq import heappop, heappush
import numpy as np
import sys

import conf
import plot
from policy import SchedulerDecision
import policy
from faas import *
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
    function: Function
    qos_class: QoSClass

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
    edge: Node
    cloud: Node
    latencies: dict
    functions: [Function]
    classes: [QoSClass]

    def __post_init__ (self):
        assert(len(self.functions) > 0)
        assert(len(self.classes) > 0)
        assert((self.edge.region,self.cloud.region) in self.latencies)
        self.stats = Stats(self, self.functions, self.classes, [self.edge,self.cloud])
        self.function_classes = [(f,c) for f in self.functions for c in f.get_invoking_classes()]


    def run (self):
        # Simulate
        self.close_the_door_time = self.config.getfloat(conf.SEC_SIM, conf.CLOSE_DOOR_TIME, fallback=100)
        self.events = []
        self.t = 0.0

        # Policy
        policy_name = self.config.get(conf.SEC_POLICY, conf.POLICY_NAME, fallback="basic")
        if policy_name == "basic":
            self.policy = policy.BasicPolicy(self)
        elif policy_name == "probabilistic":
            self.policy = policy.ProbabilisticPolicy(self)
        elif policy_name == "random":
            self.policy = policy.RandomPolicy(self)
        else:
            raise RuntimeError(f"Unknown policy: {policy_name}")
        self.policy_update_interval = self.config.getfloat(conf.SEC_POLICY, conf.POLICY_UPDATE_INTERVAL, fallback=-1)
        if self.policy_update_interval > 0.0:
            self.schedule(self.policy_update_interval, PolicyUpdate())
        self.stats_print_interval = self.config.getfloat(conf.SEC_SIM, conf.STAT_PRINT_INTERVAL, fallback=-1)
        self.stats_file = sys.stdout
        if self.stats_print_interval > 0.0:
            self.schedule(self.stats_print_interval, StatPrinter())
            stats_print_filename = self.config.get(conf.SEC_SIM, conf.STAT_PRINT_FILE, fallback="")
            if len(stats_print_filename) > 0:
                self.stats_file = open(stats_print_filename, "w")


        # Seeds
        arrival_seed = self.config.getint(conf.SEC_SEED,conf.SEED_ARRIVAL, fallback=1)
        self.arrival_rng = np.random.default_rng(arrival_seed)
        self.arrival_rng2 = np.random.default_rng(arrival_seed+1)
        # ---
        service_seed = self.config.getint(conf.SEC_SEED, conf.SEED_SERVICE, fallback=10)
        self.service_rng = np.random.default_rng(service_seed)

        #self.init_rng = np.random.default_rng(service_seed+1)

        # Other params
        self.init_time = {}
        for node in [self.edge, self.cloud]:
            self.init_time[node] = self.config.getfloat(conf.SEC_CONTAINER, conf.BASE_INIT_TIME, fallback=0.7)/node.speedup
        self.expiration_timeout = self.config.getfloat(conf.SEC_CONTAINER, conf.EXPIRATION_TIMEOUT, fallback=600)


        if not self.config.getboolean(conf.SEC_SIM, conf.PLOT_RESP_TIMES, fallback=False):
            self.resp_time_samples = {}
        else:
            self.resp_time_samples = {(f,c): [] for f in self.functions for c in f.get_invoking_classes()}

        self.__schedule_first_arrival()

        while len(self.events) > 0:
            t,e = heappop(self.events)
            self.handle(t, e)

        self.stats.print(self.stats_file)
        if self.stats_file != sys.stdout:
            self.stats_file.close()
            self.stats.print(sys.stdout)

        if len(self.resp_time_samples) > 0:
            plot.plot_rt_cdf(self.resp_time_samples)

        self.__close_trace_files()

        return self.stats

    def __compute_class_probs (self):
        self.class_probs = {}
        for f in self.functions:
            total_weight = sum([c.arrival_weight for c in f.get_invoking_classes()])
            self.class_probs[f] = [c.arrival_weight/total_weight for c in f.get_invoking_classes()]

    def __close_trace_files (self):
        for f in self.fun2tracefile.values():
            f.close()

    def __schedule_first_arrival (self):
        self.arriving_functions = set(self.functions)
        self.fun2tracefile = {}
        for f in self.functions:
            if f.arrival_trace is not None:
                self.fun2tracefile[f] = open(f.arrival_trace, "r")

        self.__compute_class_probs()

        for f in self.functions:
            self.__schedule_next_arrival(f)


    
    def __schedule_next_arrival(self, f):
        c = self.arrival_rng.choice(f.get_invoking_classes(), p=self.class_probs[f])
        if not f in self.fun2tracefile:
            iat = self.arrival_rng2.exponential(1.0/f.arrivalRate)
            if self.t + iat < self.close_the_door_time:
                self.schedule(self.t + iat, Arrival(f,c))
            else:
                self.arriving_functions.remove(f)
        else:
            trace = self.fun2tracefile[f]
            line = trace.readline().strip()
            if len(line) < 1:
                # EOF
                self.arriving_functions.remove(f)
            else:
                iat = float(line)
                if self.t + iat < self.close_the_door_time:
                    self.schedule(self.t + iat, Arrival(f,c))
                else:
                    self.arriving_functions.remove(f)

        if len(self.arriving_functions) == 0:
            # Little hack: remove all expiration from the event list (we do not
            # need to wait for them)
            for item in self.events:
                if isinstance(item[1], CheckExpiredContainers) \
                   or isinstance(item[1], PolicyUpdate) \
                   or isinstance(item[1], StatPrinter):
                    item[1].canceled = True


    def schedule (self, t, event):
        heappush(self.events, (t, event))

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
            of = self.stats_file if self.stats_file is not None else sys.stdout
            self.stats.print(of)
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
        if self.close_the_door_time < 0 or self.t < self.close_the_door_time:
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
        rtt = self.latencies[(self.edge.region,self.cloud.region)]*2
        self.schedule(self.t + rtt + OFFLOADING_OVERHEAD + init_time + duration, Completion(self.t, f,c, self.cloud, init_time > 0, duration))

    def handle_arrival (self, event):
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
        self.__schedule_next_arrival(f)
