import configparser
import sys
import yaml

import faas
import conf
from arrivals import PoissonArrivalProcess, TraceArrivalProcess
from simulation import Simulation
from infrastructure import *

def parse_config_file():
    DEFAULT_CONFIG_FILE = "config.ini"
    config_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_FILE
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def read_spec_file (spec_file_name, infra):
    with open(spec_file_name, "r") as stream:
        spec = yaml.safe_load(stream)

        classname2class={}
        classes = []
        for c in spec["classes"]:
            classname = c["name"]
            arrival_weight = c.get("arrival-weight", 1.0)
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
            node = faas.Node(node_name, memory, speedup, reg, cost=cost)
            node_names[node_name] = node
            infra.add_node(node, reg)

        functions = []
        function_names = {}
        for f in spec["functions"]:
            fname = f["name"]
            memory = f["memory"] if "memory" in f else 128
            duration_mean = f["duration_mean"] if "duration_mean" in f else 1.0
            duration_scv = f["duration_scv"] if "duration_scv" in f else 1.0
            fun = faas.Function(fname, memory, serviceMean=duration_mean, serviceSCV=duration_scv)
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
    # Infrastructure
    infra = Infrastructure(regions, latencies)

    # Read spec file
    spec_file_name = config.get(conf.SEC_SIM, conf.SPEC_FILE, fallback=None)
    classes, functions, node2arrivals  = read_spec_file (spec_file_name, infra)


    sim = Simulation(config, infra, functions, classes, node2arrivals)
    return sim

def main():
    config = parse_config_file()
    simulation = init_simulation(config)
    final_stats = simulation.run()



if __name__ == "__main__":
    main()
