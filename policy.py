from enum import Enum

class SchedulerDecision(Enum):
    EXEC = 1
    OFFLOAD = 2
    DROP = 3

class Policy:

    def __init__ (self, simulation):
        self.simulation = simulation

    def schedule (self, function, qos_class):
        pass

    def can_execute_locally (self, node, f, reclaim_memory=True):
        if f in node.warm_pool or node.curr_memory >= f.memory:
            return True
        if reclaim_memory:
            self.node.warm_pool.reclaim_memory(f.memory - node.curr_memory)
        return node.curr_memory >= f.memory



class BasicPolicy(Policy):

    def schedule (self, f, c):
        if c.name == "default":
            sched_decision = SchedulerDecision.OFFLOAD
        elif not self.can_execute_locally(self.simulation.edge, f):
            sched_decision = SchedulerDecision.DROP
        else:
            sched_decision = SchedulerDecision.EXEC

        return sched_decision

