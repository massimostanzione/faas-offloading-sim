import sys
import yaml

import faas
import conf
from arrivals import PoissonArrivalProcess, TraceArrivalProcess
from simulation import Simulation
from infrastructure import *


def read_spec_file (spec_file_name, infra, config):
    peer_exposed_memory_fraction = config.getfloat(conf.SEC_SIM, conf.EDGE_EXPOSED_FRACTION, fallback=0.5)

    with open(spec_file_name, "r") as stream:
        spec = yaml.safe_load(stream)

        classname2class={}
        classes = []
        for c in spec["classes"]:
            classname = c["name"]
            arrival_weight = c.get("arrival_weight", 1.0)
            utility = c.get("utility", 1.0)
            deadline = c.get("max_resp_time", 1.0)
            newclass = faas.QoSClass(classname, deadline, arrival_weight, utility=utility)
            classes.append(newclass)
            classname2class[classname]=newclass

        node_names = {}
        nodes = spec["nodes"]
        for n in nodes:
            node_name = n["name"]
            reg_name = n["region"]
            reg = infra.get_region(reg_name)
            memory = n["memory"] if "memory" in n else 1024
            speedup = n["speedup"] if "speedup" in n else 1.0
            cost = n["cost"] if "cost" in n else 0.0
            custom_policy = n["policy"] if "policy" in n else None
            node = faas.Node(node_name, memory, speedup, reg, cost=cost,
                             custom_sched_policy=custom_policy,
                             peer_exposed_memory_fraction=peer_exposed_memory_fraction)
            node_names[node_name] = node
            infra.add_node(node, reg)

        functions = []
        function_names = {}
        for f in spec["functions"]:
            fname = f["name"]
            memory = f["memory"] if "memory" in f else 128
            duration_mean = f["duration_mean"] if "duration_mean" in f else 1.0
            duration_scv = f["duration_scv"] if "duration_scv" in f else 1.0
            init_mean = f["init_mean"] if "init_mean" in f else 0.500
            input_mean = f["input_mean"] if "input_mean" in f else 1024
            fun = faas.Function(fname, memory, serviceMean=duration_mean, serviceSCV=duration_scv, initMean=init_mean, inputSizeMean=input_mean)
            function_names[fname] = fun
            functions.append(fun)

        node2arrivals = {}
        for f in spec["arrivals"]:
            node = node_names[f["node"]]
            fun = function_names[f["function"]]
        
            if not "classes" in f:
                invoking_classes = classes
            else:
                invoking_classes = [classname2class[qcname] for qcname in f["classes"]]

            if "trace" in f:
                arv = TraceArrivalProcess(fun, invoking_classes, f["trace"])
            elif "rate" in f:
                arv = PoissonArrivalProcess(fun, invoking_classes, float(f["rate"]))

            if not node in node2arrivals:
                node2arrivals[node] = []
            node2arrivals[node].append(arv)

    return classes, functions, node2arrivals


def init_simulation (config):
    # Regions
    reg_cloud = Region("cloud")
    reg_edge = Region("edge", reg_cloud)
    regions = [reg_edge, reg_cloud]
    # Latency
    latencies = {(reg_edge,reg_cloud): 0.100}
    bandwidth_mbps = {(reg_edge,reg_edge): 100.0, (reg_cloud,reg_cloud): 1000.0,\
            (reg_edge,reg_cloud): 10.0}
    # Infrastructure
    infra = Infrastructure(regions, latencies, bandwidth_mbps)

    # Read spec file
    spec_file_name = config.get(conf.SEC_SIM, conf.SPEC_FILE, fallback=None)
    classes, functions, node2arrivals  = read_spec_file (spec_file_name, infra, config)


    sim = Simulation(config, infra, functions, classes, node2arrivals)
    return sim

def main():
    DEFAULT_CONFIG_FILE = "config.ini"
    config_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_FILE
    config = conf.parse_config_file(config_file)
    simulation = init_simulation(config)
    final_stats = simulation.run()



if __name__ == "__main__":
    main()
