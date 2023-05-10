import configparser
import sys
import yaml

import faas
import conf
from arrivals import PoissonArrivalProcess
from simulation import Simulation
from infrastructure import *

def parse_config_file():
    DEFAULT_CONFIG_FILE = "config.ini"
    config_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_FILE
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def read_spec_file (spec_file_name, infra, classes):
    classname2class = {}
    for qc in classes:
        classname2class[qc.name] = qc
        
    with open(spec_file_name, "r") as stream:
        node_names = {}
        spec = yaml.safe_load(stream)
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
            node_name = f["node"]
            node = node_names[node_name]
            if not "functions" in f:
                arriving_functions = functions
                invoking_classes = {f: classes for f in arriving_functions}
            else:
                arriving_functions = []
                invoking_classes = {}
                for fun_block in f["functions"]:
                    fname = fun_block["name"]
                arriving_functions.append(function_names[fname])
                if not "classes" in fun_block:
                    invoking_classes[function_names[fname]] = classes
                else:
                    invoking_classes[function_names[fname]] = [classname2class[qcname] for qcname in fun_block["classes"]]
            if "trace" in f:
                raise RuntimeError("Not implemented yet")
            elif "rate" in f:
                for fun in arriving_functions:
                    arv = PoissonArrivalProcess(fun, invoking_classes[fun], float(f["rate"]))
            if not node in node2arrivals:
                node2arrivals[node] = []
            node2arrivals[node].append(arv)

    return functions, node2arrivals


def init_simulation (config):
    # Regions
    reg_cloud = Region("cloud")
    reg_edge = Region("edge", reg_cloud)
    regions = [reg_edge, reg_cloud]
    # Latency
    edge_cloud_latency = config.getfloat("edge", "cloud-latency", fallback=0.050)
    latencies = {(reg_edge,reg_cloud): edge_cloud_latency}
    # Infrastructure
    infra = Infrastructure(regions, latencies)

    # Read classes from config
    classes = []
    for section in config.sections():
        if section.startswith("class_"):
            classname = section[6:]
            arrival_weight = config.getfloat(section, "arrival-weight", fallback=1.0)
            utility = config.getfloat(section, "utility", fallback=1.0)
            deadline = config.getfloat(section, "deadline", fallback=1.0)
            c = faas.QoSClass(classname, deadline, arrival_weight, utility=utility)
            classes.append(c)
    
    # Read spec file
    spec_file_name = config.get(conf.SEC_SIM, conf.SPEC_FILE, fallback=None)
    functions, node2arrivals  = read_spec_file (spec_file_name, infra, classes)


    sim = Simulation(config, infra, functions, classes, node2arrivals)
    return sim

def main():
    config = parse_config_file()
    simulation = init_simulation(config)
    final_stats = simulation.run()



if __name__ == "__main__":
    main()
