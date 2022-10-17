from dataclasses import dataclass,field
from enum import Enum

class Region(Enum):
    EDGE = 1
    CLOUD = 2

class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD = 2
    DROP = 3

class ContainerPool:

    def __init__ (self):
        self.pool = []

    def append (self, e):
        self.pool.append(e)

    def remove (self, f):
        for entry in self.pool:
            if f.name == entry[0].name:
                self.pool.remove(entry)
                return

    def __len__ (self):
        return len(self.pool)

    def front (self):
        return self.pool[0]

    def __contains__ (self, f):
        if not isinstance(f, Function):
            return False
        for entry in self.pool:
            if f.name == entry[0].name:
                return True
        return False

class Node:

    def __init__ (self, memory, speedup, region):
        self.total_memory = memory
        self.curr_memory = memory
        self.speedup = speedup
        self.region = region

        self.warm_pool = ContainerPool()


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
class Container:
    function: Function
    expiration_time: float

    def __eq__ (self, other):
        if not isinstance(other, Container) and not isinstance(other, Function):
            return False
        elif isinstance(other, Function):
            return self.function == other.name
        else:
            return self.function == other.function



@dataclass
class QoSClass:
    name: str
    max_rt: float
    arrival_weight: float = 1.0
    utility: float = 1.0

    def __repr__ (self):
        return self.name

    def __hash__ (self):
        return hash(self.name)
