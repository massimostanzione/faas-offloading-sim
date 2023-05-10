import json

class Stats:

    def __init__ (self, sim, functions, classes, infra):
        self.sim = sim
        self.infra = infra
        self.functions = functions
        self.classes = classes
        self.nodes = infra.get_nodes()
        fun_classes = [(f,c) for f in functions for c in classes]
        fcn = [(f,c,n) for f in functions for c in classes for n in self.nodes]

        self.arrivals = {x: 0 for x in fcn}
        self.offloaded = {x: 0 for x in fcn}
        self.dropped_reqs = {c: 0 for c in fcn}
        self.completions = {x: 0 for x in fcn}
        self.violations = {c: 0 for c in fcn}
        self.resp_time_sum = {c: 0.0 for c in fcn}
        self.cold_starts = {(f,n): 0 for f in functions for n in self.nodes}
        self.execution_time_sum = {(f,n): 0 for f in functions for n in self.nodes}
        self.node2completions = {(f,n): 0 for n in self.nodes for f in functions}
        self.cost = 0.0
        self.raw_utility = 0.0
        self.utility = 0.0
        self.utility_detail = {x: 0.0 for x in fcn}

    def to_dict (self):
        stats = {}
        raw = vars(self)
        for metric in raw:
            t = type(raw[metric])
            if t is float or t is int:
                # no change required
                stats[metric] = raw[metric]
            if t is dict:
                # replace with a new dict, w reformatted keys
                new_metric = {repr(x): raw[metric][x] for x in raw[metric]}
                stats[metric] = new_metric

        avg_rt = {repr(x): self.resp_time_sum[x]/self.completions[x] for x in self.completions if self.completions[x] > 0}
        stats["avgRT"] = avg_rt
        del(stats["resp_time_sum"])

        avg_exec = {repr(x): self.execution_time_sum[x]/self.node2completions[x] for x in self.node2completions if self.node2completions[x] > 0}
        stats["avgExecTime"] = avg_exec
        del(stats["execution_time_sum"])

        completed_perc = {repr(x): self.completions[x]/self.arrivals[x] for x in self.completions if self.arrivals[x] > 0}
        stats["completedPercentage"] = completed_perc

        violations_perc = {repr(x): self.violations[x]/self.completions[x] for x in self.completions if self.completions[x] > 0}
        stats["violationsPercentage"] = violations_perc

        cold_start_prob = {repr(x): self.cold_starts[x]/self.node2completions[x] for x in self.node2completions if self.node2completions[x] > 0}
        stats["coldStartProb"] = cold_start_prob

        class_completions = {}
        class_rt = {}
        for c in self.classes:
            class_completions[repr(c)] = sum([self.completions[(f,c,n)] for f in self.functions for n in self.infra.get_nodes() if c in self.classes])
            if class_completions[repr(c)] == 0:
                continue
            rt_sum = sum([self.resp_time_sum[(f,c,n)] for f in self.functions for n in self.infra.get_nodes()])
            class_rt[repr(c)] = rt_sum/class_completions[repr(c)]
        stats["perClassCompleted"] = class_completions
        stats["perClassAvgRT"] = class_rt

        stats["_Time"] = self.sim.t

        return stats
    

    def print (self, out_file):
        print(json.dumps(self.to_dict(), indent=4, sort_keys=True), file=out_file)
