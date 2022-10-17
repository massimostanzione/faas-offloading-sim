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
    cloud = faas.Node(30000, faas.Region.CLOUD)
    edge = faas.Node(3000, faas.Region.EDGE)

    # Define functions
    f1 = faas.Function("f1", 128, 1.0, 1.0, serviceSCV=0.5)
    functions = [f1]

    # Define classes
    classes = [faas.QoSClass("default", 1, 1)]

    sim = Simulation(config, edge, cloud, functions, classes)
    sim.run()






if __name__ == "__main__":
    main()
