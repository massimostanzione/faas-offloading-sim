import configparser
from dataclasses import dataclass
from heapq import heappop, heappush
import numpy as np

from faas import *

@dataclass
class Arrival:
    function: Function
    qos_class: QoSClass

@dataclass
class Completion:
    arrival: float
    function: Function
    qos_class: QoSClass

INIT_TIME_DURATION = 0.75

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
        self.arrivals = 0
        self.dropped_reqs = 0
        self.completions = 0
        self.rt_area = 0
        self.cold_starts = 0

        self.schedule_first_arrival()

        while len(self.events) > 0:
            t,e = heappop(self.events)
            self.handle(t, e)

        print(f"Arrivals: {self.arrivals}")
        print(f"Dropped: {self.dropped_reqs}")
        print(f"Completed: {self.completions}")
        print(f"Avg RT: {self.rt_area/self.completions}")
        print(f"Cold starts: {self.cold_starts}")

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
        self.t = t
        if isinstance(event, Arrival):
            self.handle_arrival(event)
        elif isinstance(event, Completion):
            self.handle_completion(event)
        else:
            raise RuntimeError("")


    def handle_completion (self, event):
        rt = self.t - event.arrival
        f = event.function
        c = event.qos_class
        print(f"Completed {f}-{c}: {rt}")

        self.completions += 1
        self.rt_area += rt

        self.edge.warm_pool.append(f)

    def handle_arrival (self, event):
        self.arrivals += 1
        f = event.function
        c = event.qos_class
        print(f"Arrived {f}-{c} @ {self.t}")

        # Schedule
        # TODO
        if not f in self.edge.warm_pool and self.edge.curr_memory < f.memory:
            sched_decision = SchedulerDecision.DROP
        else:
            sched_decision = SchedulerDecision.EXEC

        if sched_decision == SchedulerDecision.EXEC:
            duration = self.service_rng.gamma(1.0/f.serviceSCV, f.serviceMean*f.serviceSCV) # TODO: check
            # check warm or cold
            if f in self.edge.warm_pool:
                self.edge.warm_pool.remove(f)
                init_time = 0
            else:
                self.edge.curr_memory -= f.memory
                assert(self.edge.curr_memory >= 0)
                self.cold_starts += 1
                init_time = INIT_TIME_DURATION
            self.schedule(self.t + init_time + duration, Completion(self.t, f,c))
        elif sched_decision == SchedulerDecision.DROP:
            self.dropped_reqs += 1
        elif sched_decision == SchedulerDecision.OFFLOAD:
            pass # TODO

        # Schedule next
        iat = self.arrival_rng2.exponential(1.0/self.total_arrival_rate)
        if self.t + iat < self.close_the_door_time:
            f,c = self.arrival_rng.choice(self.arrival_entries, p=self.arrival_probs)
            self.schedule(self.t + iat, Arrival(f,c))
