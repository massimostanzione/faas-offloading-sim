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
class Simulation:

    config: configparser.ConfigParser
    edge: Node
    cloud: Node
    functions: [Function]
    classes: [QoSClass]

    def run (self, close_the_door_time=100.0):
        assert(len(self.functions) > 0)
        assert(len(self.classes) > 0)

        # Simulate
        self.close_the_door_time = close_the_door_time
        self.events = []
        self.t = 0.0

        # Seeds
        arrival_seed = 1
        if self.config is not None and "seed.arrival" in self.config:
            arrival_seed = self.config["seed.arrival"]
        self.arrival_rng = np.random.default_rng(arrival_seed)
        self.arrival_rng2 = np.random.default_rng(arrival_seed+1)

        # Stats
        self.arrivals = 0

        self.schedule_first_arrival()

        while len(self.events) > 0:
            t,e = heappop(self.events)
            self.handle(t, e)

        print(f"Arrivals: {self.arrivals}")

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

    def handle_arrival (self, event):
        self.arrivals += 1
        print(f"Arrived {event.function}-{event.qos_class} @ {self.t}")

        # Schedule next
        iat = self.arrival_rng2.exponential(1.0/self.total_arrival_rate)
        if self.t + iat < self.close_the_door_time:
            f,c = self.arrival_rng.choice(self.arrival_entries, p=self.arrival_probs)
            self.schedule(self.t + iat, Arrival(f,c))
