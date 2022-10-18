import configparser
import sys

import faas
from simulation import Simulation

def parse_config():
    DEFAULT_CONFIG_FILE = "config.ini"
    config_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_FILE
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def main():
    config = parse_config()
    
    # Nodes
    cloud = faas.Node(30000, 1.3, faas.Region.CLOUD)
    edge = faas.Node(3000, 1.0, faas.Region.EDGE)
    latencies = {(edge.region,cloud.region): 0.040}

    # Read functions from config
    functions = []
    for section in config.sections():
        if section.startswith("fun_"):
            fun = section[4:]
            memory = config.getint(section, "memory", fallback=256)
            arrival = config.getfloat(section, "arrival-rate", fallback=1.0)
            service_mean = config.getfloat(section, "service-time-mean", fallback=1.0)
            service_scv = config.getfloat(section, "service-time-scv", fallback=1.0)
            functions.append(faas.Function(fun, memory, arrival, service_mean, serviceSCV=service_scv))

    # Read classes from config
    classes = []
    for section in config.sections():
        if section.startswith("class_"):
            classname = section[6:]
            arrival_weight = config.getfloat(section, "arrival-weight", fallback=1.0)
            utility = config.getfloat(section, "utility", fallback=1.0)
            deadline = config.getfloat(section, "deadline", fallback=1.0)
            classes.append(faas.QoSClass(classname, deadline, arrival_weight, utility=utility))


    sim = Simulation(config, edge, cloud, latencies, functions, classes)
    sim.run()






if __name__ == "__main__":
    main()
