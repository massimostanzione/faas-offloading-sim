import configparser
from dataclasses import dataclass, field
from heapq import heappop, heappush
import numpy as np

from faas import *

@dataclass
class Event:
    canceled: bool = field(default=False, init=False)


@dataclass
class Arrival(Event):
    function: Function
    qos_class: QoSClass

@dataclass
class CheckExpiredContainers(Event):
    node: Node

@dataclass
class Completion(Event):
    arrival: float
    function: Function
    qos_class: QoSClass
    node: Node
    cold: bool


INIT_TIME_DURATION = 0.75
CLOUD_INIT_TIME_DURATION = 0.7
cloud_rtt = 0.06
EXPIRATION_TIMEOUT = 600

@dataclass
class Simulation:

    config: configparser.ConfigParser
    edge: Node
    cloud: Node
    functions: [Function]
    classes: [QoSClass]

    def run (self, close_the_door_time=500.0):
        assert(len(self.functions) > 0)
        assert(len(self.classes) > 0)

        # Simulate
        self.close_the_door_time = close_the_door_time
        self.events = []
        self.t = 0.0

        # Seeds
        arrival_seed = 1
        if self.config is not None and "seed.arrival" in self.config:
            arrival_seed = self.config.getint("seed.arrival")
        self.arrival_rng = np.random.default_rng(arrival_seed)
        self.arrival_rng2 = np.random.default_rng(arrival_seed+1)
        # ---
        service_seed = 10
        if self.config is not None and "seed.service" in self.config:
            service_seed = self.config.getint("seed.service")
        self.service_rng = np.random.default_rng(service_seed)

        #self.init_rng = np.random.default_rng(service_seed+1)

        # Stats
        self.arrivals = {c: 0 for c in self.classes}
        self.offloaded = {c: 0 for c in self.classes}
        self.dropped_reqs = {c: 0 for c in self.classes}
        self.completions = {c: 0 for c in self.classes}
        self.violations = {c: 0 for c in self.classes}
        self.rt_area = {c: 0.0 for c in self.classes}
        self.cold_starts = 0
        self.utility = 0.0
        self.utility_with_constraints = 0.0

        self.schedule_first_arrival()

        while len(self.events) > 0:
            t,e = heappop(self.events)
            self.handle(t, e)

        completed_perc = {}
        for c in self.completions:
            completed_perc[c] = self.completions[c]/self.arrivals[c]*100.0

        print(f"TotArrivals: {sum(self.arrivals.values())}")
        print(f"Arrivals: {self.arrivals}")
        print(f"Offloaded: {self.offloaded}")
        print(f"Dropped: {self.dropped_reqs}")
        print(f"RT Violations: {self.violations}")
        print(f"Completed: {self.completions}")
        print(f"CompletedP: {completed_perc}")
        print(f"Cold starts: {self.cold_starts}")
        for c in self.classes:
            try:
                print(f"Avg RT-{c}: {self.rt_area[c]/self.completions[c]}")
            except:
                pass
        print(f"Utility: {self.utility}")
        print(f"UtilityWC: {self.utility_with_constraints}")

    def schedule_first_arrival (self):
        # Compute arrival probabilities
        self.arrival_entries = [(f,c) for f in self.functions for c in self.classes]
        total_rate = sum([f.arrivalRate*c.arrival_weight for f,c in self.arrival_entries])
        self.arrival_probs = [f.arrivalRate*c.arrival_weight/total_rate for f,c in self.arrival_entries]
        self.total_arrival_rate = sum([f.arrivalRate for f in self.functions])

        f,c = self.arrival_rng.choice(self.arrival_entries, p=self.arrival_probs)
        t = self.arrival_rng2.exponential(1.0/self.total_arrival_rate)
        self.schedule(t, Arrival(f,c))



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
        elif isinstance(event, CheckExpiredContainers):
            if len(event.node.warm_pool) == 0:
                return
            f,timeout = event.node.warm_pool.front()
            if timeout < t:
                event.node.warm_pool.pool = event.node.warm_pool.pool[1:]
        else:
            raise RuntimeError("")

    def handle_completion (self, event):
        rt = self.t - event.arrival
        f = event.function
        c = event.qos_class
        n = event.node
        #print(f"Completed {f}-{c}: {rt}")

        self.rt_area[c] += rt
        self.completions[c] += 1
        self.utility += c.utility
        if rt <= c.max_rt:
            self.utility_with_constraints += c.utility
        else:
            self.violations[c] += 1

        n.warm_pool.append((f, self.t + EXPIRATION_TIMEOUT))
        self.schedule(self.t + EXPIRATION_TIMEOUT, CheckExpiredContainers(n)) 


    def handle_offload (self, f, c):
        if not f in self.cloud.warm_pool and self.edge.curr_memory < f.memory:
            # TODO: try to reclaim memory
            self.dropped_reqs[c] += 1
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
            self.cold_starts += 1
            init_time = CLOUD_INIT_TIME_DURATION
        self.schedule(self.t + cloud_rtt + init_time + duration, Completion(self.t, f,c, self.cloud, init_time > 0))

    def handle_arrival (self, event):
        f = event.function
        c = event.qos_class
        self.arrivals[c] += 1
        #print(f"Arrived {f}-{c} @ {self.t}")

        # Schedule
        # TODO
        if c.name == "default":
            sched_decision = SchedulerDecision.OFFLOAD
        elif not f in self.edge.warm_pool and self.edge.curr_memory < f.memory:
            # TODO: try to reclaim memory
            sched_decision = SchedulerDecision.DROP
        else:
            sched_decision = SchedulerDecision.EXEC

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
                self.cold_starts += 1
                init_time = INIT_TIME_DURATION
            self.schedule(self.t + init_time + duration, Completion(self.t, f,c, self.edge, init_time > 0))
        elif sched_decision == SchedulerDecision.DROP:
            self.dropped_reqs[c] += 1
        elif sched_decision == SchedulerDecision.OFFLOAD:
            self.offloaded[c] += 1
            self.handle_offload(f,c)

        # Schedule next
        iat = self.arrival_rng2.exponential(1.0/self.total_arrival_rate)
        if self.t + iat < self.close_the_door_time:
            f,c = self.arrival_rng.choice(self.arrival_entries, p=self.arrival_probs)
            self.schedule(self.t + iat, Arrival(f,c))
        else:
            # Little hack: remove all expiration from the event list (we do not
            # need to wait for them)
            for item in self.events:
                if isinstance(item[1], CheckExpiredContainers):
                    item[1].canceled = True
