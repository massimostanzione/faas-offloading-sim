from dataclasses import dataclass,field
from enum import Enum

class Region(Enum):
    EDGE = 1
    CLOUD = 2

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

    def reclaim_memory (self, required_mem):
        mem = [entry[0].memory for entry in self.pool]
        if sum(mem) < required_mem:
            return 0.0
        s = sorted([e[0] for e in self.pool], reverse=True, key = lambda x: x.memory)
        reclaimed = 0
        while reclaimed < required_mem:
            f = s[0]
            s = s[1:]
            self.remove(f)
            reclaimed += f.memory
        return reclaimed

    def __contains__ (self, f):
        if not isinstance(f, Function):
            return False
        for entry in self.pool:
            if f.name == entry[0].name:
                return True
        return False

class Node:

    def __init__ (self, name, memory, speedup, region):
        self.name = name
        self.total_memory = memory
        self.curr_memory = memory
        self.speedup = speedup
        self.region = region

        self.warm_pool = ContainerPool()

    def __repr__ (self):
        return self.name



@dataclass
class QoSClass:
    name: str
    max_rt: float
    arrival_weight: float = 1.0
    utility: float = 1.0
    min_completion_percentage: float = 0.0

    
    def __repr__ (self):
        return self.name

    def __hash__ (self):
        return hash(self.name)

    def __lt__(self, other):
        return self.name <  other.name

    def __le__(self,other):
        return self.name <= other.name

@dataclass
class Function:
    name: str
    memory: int
    arrivalRate: float
    serviceMean: float
    serviceSCV: float = 1.0
    arrival_trace: str = field(default=None)
    __invoking_classes: [QoSClass] = field(default=None, init=False)

    def add_invoking_class (self, c: QoSClass):
        if self.__invoking_classes is None:
            self.__invoking_classes = []
        if not c in self.__invoking_classes:
            self.__invoking_classes.append(c)

    def get_invoking_classes (self):
        return self.__invoking_classes

    def __repr__ (self):
        return self.name

    def __hash__ (self):
        return hash(self.name)

    def __lt__(self, other):
        return self.name <  other.name

    def __le__(self,other):
        return self.name <= other.name

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



if __name__ == "__main__":
    pool = ContainerPool()
    f = Function("a", 200, 1, 1, 1)
    f2 = Function("b", 100, 1, 1, 1)
    pool.append((f,1))
    pool.append((f2,1))
    print(pool.pool)
    pool.reclaim_memory(500)
    print(pool.pool)
    pool.reclaim_memory(10)
    print(pool.pool)
