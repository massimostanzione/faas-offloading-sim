import json

class Stats:

    def __init__ (self, sim, functions, classes, nodes):
        self.sim = sim
        self.functions = functions
        self.classes = classes
        self.nodes = nodes
        fun_classes = [(f,c) for f in functions for c in f.get_invoking_classes()]

        self.arrivals = {x: 0 for x in fun_classes}
        self.offloaded = {x: 0 for x in fun_classes}
        self.dropped_reqs = {c: 0 for c in fun_classes}
        self.completions = {x: 0 for x in fun_classes}
        self.violations = {c: 0 for c in fun_classes}
        self.resp_time_sum = {c: 0.0 for c in fun_classes}
        self.cold_starts = {x: 0 for x in fun_classes}
        self.execution_time_sum = {(f,n): 0 for f in functions for n in nodes}
        self.node2cold_starts = {n: 0 for n in nodes}
        self.node2completions = {(f,n): 0 for n in nodes for f in functions}
        self.utility = 0.0
        self.utility_with_constraints = 0.0

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
        stats["AvgRT"] = avg_rt

        completed_perc = {repr(x): self.completions[x]/self.arrivals[x] for x in self.completions if self.arrivals[x] > 0}
        stats["CompletedPercentage"] = completed_perc

        class_completions = {}
        class_rt = {}
        for c in self.classes:
            class_completions[repr(c)] = sum([self.completions[(f,c)] for f in self.functions if c in f.get_invoking_classes()])
            if class_completions[repr(c)] == 0:
                continue
            rt_sum = sum([self.resp_time_sum[(f,c)] for f in self.functions if c in f.get_invoking_classes()])
            class_rt[repr(c)] = rt_sum/class_completions[repr(c)]
        stats["PerClassCompleted"] = class_completions
        stats["PerClassAvgRT"] = class_rt

        stats["Time"] = self.sim.t

        return stats
    

    def print (self, out_file):
        print(json.dumps(self.to_dict(), indent=4, sort_keys=True), file=out_file)
