from dataclasses import dataclass,field
from enum import Enum

class Region(Enum):
    EDGE = 1
    CLOUD = 2

class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD = 2
    DROP = 3

class Node:

    def __init__ (self, memory, region):
        self.total_memory = memory
        self.curr_memory = memory
        self.region = region

        self.warm_pool = []


@dataclass
class Function:
    name: str
    memory: int
    arrivalRate: float
    serviceMean: float
    serviceSCV: float = 1.0

    def __repr__ (self):
        return self.name


@dataclass
class QoSClass:
    name: str
    max_rt: float
    arrival_weight: float = 1.0
    utility: float = 1.0

    def __repr__ (self):
        return self.name
