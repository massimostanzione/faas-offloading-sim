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

    # Define functions
    functions = []
    functions.append(faas.Function("f1", 512, 1.0, 1.0, serviceSCV=0.5))
    functions.append(faas.Function("f2", 128, 2.0, 1.0, serviceSCV=0.5))

    # Define classes
    classes = []
    classes.append(faas.QoSClass("default", 1, 1))
    classes.append(faas.QoSClass("premium", 1, 0.2, utility=2.0))

    sim = Simulation(config, edge, cloud, functions, classes)
    sim.run()






if __name__ == "__main__":
    main()
