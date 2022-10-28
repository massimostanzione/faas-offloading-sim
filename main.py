import configparser
import sys

import faas
from simulation import Simulation

def parse_config_file():
    DEFAULT_CONFIG_FILE = "config.ini"
    config_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_FILE
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def init_simulation (config):
    # Nodes
    cloud_memory = config.getint("cloud", "memory", fallback=300000)
    cloud_speedup = config.getfloat("cloud", "speedup", fallback=1.3)
    cloud_cost = config.getfloat("cloud", "cost", fallback=0.0)
    edge_memory = config.getint("edge", "memory", fallback=4096)
    edge_speedup = config.getfloat("edge", "speedup", fallback=1.0)
    edge_cloud_latency = config.getfloat("edge", "cloud-latency", fallback=0.040)
    cloud = faas.Node("cloud", cloud_memory, cloud_speedup, faas.Region.CLOUD, cost=cloud_cost)
    edge = faas.Node("edge", edge_memory, edge_speedup, faas.Region.EDGE)
    latencies = {(edge.region,cloud.region): edge_cloud_latency}

    # Read functions from config
    name2function = {}
    functions = []
    for section in config.sections():
        if section.startswith("fun_"):
            fun = section[4:]
            memory = config.getint(section, "memory", fallback=256)
            arrival = config.getfloat(section, "arrival-rate", fallback=1.0)
            service_mean = config.getfloat(section, "service-time-mean", fallback=1.0)
            service_scv = config.getfloat(section, "service-time-scv", fallback=1.0)
            arrival_trace = config.get(section, "arrival-trace", fallback=None)
            f = faas.Function(fun, memory, arrival, service_mean, serviceSCV=service_scv, arrival_trace=arrival_trace)
            functions.append(f)
            name2function[fun] = f

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
            # Parse invoked functions 
            invoked_functions_str = config.get(section, "functions", fallback="")
            invoked_functions = list(filter(lambda x: len(x) > 0, [x.strip() for x in invoked_functions_str.split(",")]))
            if len(invoked_functions) < 1:
                invoked_functions = functions
            else:
                invoked_functions = [name2function[s] for s in invoked_functions]
            for f in invoked_functions:
                f.add_invoking_class(c)


    sim = Simulation(config, edge, cloud, latencies, functions, classes)
    return sim

def main():
    config = parse_config_file()
    simulation = init_simulation(config)
    final_stats = simulation.run()



if __name__ == "__main__":
    main()
