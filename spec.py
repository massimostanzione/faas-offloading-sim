import yaml
import tempfile
from scipy.stats import truncnorm
import numpy as np
from numpy.random import uniform, choice
import map as MAP

ARRIVAL_DISTRIBUTIONS = ["exp","mmpp","erlang","hyper"]

# Returns an open NamedTemporaryFile
def generate_temp_spec (n_functions=5, load_coeff=1.0, dynamic_rate_coeff=1.0, arrivals_to_single_node=True,
                   n_classes=4, cloud_cost=0.00005, cloud_speedup=1.0, n_edges=5):

    classes = [{'name': 'critical', 'max_resp_time': 0.5, 'utility': 1.0, 'arrival_weight': 1.0}, {'name': 'standard', 'max_resp_time': 0.5, 'utility': 0.01, 'arrival_weight': 7.0}, {'name': 'batch', 'max_resp_time': 99.0, 'utility': 1.0, 'arrival_weight': 1.0}, {'name': 'criticalP', 'max_resp_time': 0.5, 'utility': 1.0, 'penalty': 0.75, 'arrival_weight': 1.0}]
    nodes = [{'name': 'edge1', 'region': 'edge', 'memory': 4096}, {'name': 'edge2', 'region': 'edge', 'memory': 4096}, {'name': 'edge3', 'region': 'edge', 'memory': 4096}, {'name': 'edge4', 'region': 'edge', 'memory': 4096}, {'name': 'edge5', 'region': 'edge', 'memory': 4096}, {'name': 'cloud1', 'region': 'cloud', 'cost': cloud_cost, 'speedup': cloud_speedup, 'memory': 128000}]
    functions = [{'name': 'f1', 'memory': 512, 'duration_mean': 0.4, 'duration_scv': 1.0, 'init_mean': 0.5}, {'name': 'f2', 'memory': 512, 'duration_mean': 0.2, 'duration_scv': 1.0, 'init_mean': 0.25}, {'name': 'f3', 'memory': 128, 'duration_mean': 0.3, 'duration_scv': 1.0, 'init_mean': 0.6}, {'name': 'f4', 'memory': 1024, 'duration_mean': 0.25, 'duration_scv': 1.0, 'init_mean': 0.25}, {'name': 'f5', 'memory': 256, 'duration_mean': 0.45, 'duration_scv': 1.0, 'init_mean': 0.5}]
   
    #Extend functions list if needed
    if n_functions > len(functions):
        i=0
        while n_functions > len(functions):
            new_f = functions[i].copy()
            new_f["name"] = f"f{len(functions)+1}"
            functions.append(new_f)
            i+=1
    else:
        functions = functions[:n_functions]
    function_names = [f["name"] for f in functions]

    #Extend node list if needed
    if n_edges > len(nodes) - 1:
        i=0
        while n_edges > len(nodes) - 1:
            new_f = nodes[0].copy()
            new_f["name"] = f"nedge{i}"
            nodes.append(new_f)
            i+=1
    elif n_edges < len(nodes) - 1:
        new_nodes = nodes[:n_edges]
        new_nodes.append(nodes[-1])
        nodes = new_nodes

    #Extend class list if needed
    if n_classes > len(classes):
        i=0
        while n_classes > len(classes):
            new_f = classes[i].copy()
            new_f["name"] = f"c{len(classes)+1}"
            classes.append(new_f)
            i+=1
    else:
        classes = classes[:n_classes]

    ntemp = tempfile.NamedTemporaryFile(mode="w")
    write_spec(ntemp, functions, classes, nodes, load_coeff, dynamic_rate_coeff, arrivals_to_single_node)
    return ntemp

def generate_random_temp_spec (rng, n_functions=5, load_coeff=1.0, dynamic_rate_coeff=1.0, arrivals_to_single_node=True,
                   n_classes=4, cloud_cost=0.00005, cloud_speedup=1.0, n_edges=5):

    classes = [{'name': 'critical', 'max_resp_time': 0.5, 'utility': 1.0, 'arrival_weight': 1.0}, {'name': 'standard', 'max_resp_time': 0.5, 'utility': 0.01, 'arrival_weight': 7.0}, {'name': 'batch', 'max_resp_time': 99.0, 'utility': 1.0, 'arrival_weight': 1.0}, {'name': 'criticalP', 'max_resp_time': 0.5, 'utility': 1.0, 'penalty': 0.75, 'arrival_weight': 1.0}]
    nodes = [{'name': 'edge1', 'region': 'edge', 'memory': 4096}, {'name': 'edge2', 'region': 'edge', 'memory': 4096}, {'name': 'edge3', 'region': 'edge', 'memory': 4096}, {'name': 'edge4', 'region': 'edge', 'memory': 4096}, {'name': 'edge5', 'region': 'edge', 'memory': 4096}, {'name': 'cloud1', 'region': 'cloud', 'cost': cloud_cost, 'speedup': cloud_speedup, 'memory': 128000}]
    functions = [{'name': 'f1', 'memory': 512, 'duration_mean': 0.4, 'duration_scv': 1.0, 'init_mean': 0.5}, {'name': 'f2', 'memory': 512, 'duration_mean': 0.2, 'duration_scv': 1.0, 'init_mean': 0.25}, {'name': 'f3', 'memory': 128, 'duration_mean': 0.3, 'duration_scv': 1.0, 'init_mean': 0.6}, {'name': 'f4', 'memory': 1024, 'duration_mean': 0.25, 'duration_scv': 1.0, 'init_mean': 0.25}, {'name': 'f5', 'memory': 256, 'duration_mean': 0.45, 'duration_scv': 1.0, 'init_mean': 0.5}]
   
    #Extend functions list if needed
    if n_functions > len(functions):
        i=0
        while n_functions > len(functions):
            new_f = functions[i].copy()
            new_f["name"] = f"f{len(functions)+1}"
            functions.append(new_f)
            i+=1
    else:
        functions = functions[:n_functions]
    function_names = [f["name"] for f in functions]

    #Extend node list if needed
    if n_edges > len(nodes) - 1:
        i=0
        while n_edges > len(nodes) - 1:
            new_f = nodes[0].copy()
            new_f["name"] = f"nedge{i}"
            nodes.append(new_f)
            i+=1
    elif n_edges < len(nodes) - 1:
        new_nodes = nodes[:n_edges]
        new_nodes.append(nodes[-1])
        nodes = new_nodes

    #Extend class list if needed
    if n_classes > len(classes):
        i=0
        while n_classes > len(classes):
            new_f = classes[i].copy()
            new_f["name"] = f"c{len(classes)+1}"
            classes.append(new_f)
            i+=1
    else:
        classes = classes[:n_classes]



    # Randomly set specs
    for f in functions:
        f["duration_mean"] = float(rng.uniform(0.1,0.5))
        f["init_mean"] = float(rng.uniform(0.25,0.75))
        f["memory"] = float(rng.uniform(128,1024))
        f["duration_scv"] = float(rng.choice([1,0.5,0.25]))

        myclip_a = 100
        myclip_b = 1024*1024*5
        loc = 1024
        scale = 10**3
        a, b = (myclip_a - loc) / scale, (myclip_b - loc) / scale
        f["input_mean"] = float(truncnorm.rvs(a, b, loc=loc, scale=scale, size=1))

    if dynamic_rate_coeff > 1.0:
        print("Forcing Poisson arrivals")
        functions_arrival_distributions = {f["name"]: "exp" for f in functions}
    else:
        functions_arrival_distributions = rng.choice(ARRIVAL_DISTRIBUTIONS, size=n_functions)
        functions_arrival_distributions = {f["name"]: d for f,d in zip(functions, functions_arrival_distributions)}


    ntemp = tempfile.NamedTemporaryFile(mode="w")
    write_spec(ntemp, functions, classes, nodes, load_coeff, dynamic_rate_coeff, arrivals_to_single_node, functions_arrival_distributions=functions_arrival_distributions)
    return ntemp

# Writes a spec file to outf 
def write_spec (outf, functions, classes, nodes, load_coeff=1.0, dynamic_rate_coeff=1.0, arrivals_to_single_node=True, functions_arrival_distributions=None):

    total_fun_weight = sum([f["duration_mean"]*f["memory"] for f in functions])

    def make_arrival_dict (_node, _func, _dynamic_coeff, _rate=None, _map=None):
        if _rate is not None:
            return {"node": _node, "function": _func, "rate": _rate, "dynamic_coeff": _dynamic_coeff }
        elif _map is not None:
            D0,D1=_map
            mapstr=""
            for x in np.nditer(D0):
                mapstr = mapstr + f"{x};"
            for x in np.nditer(D1):
                mapstr = mapstr + f"{x};"
            mapstr=mapstr[:-1]
            return {"node": _node, "function": _func, "map": mapstr, "dynamic_coeff": _dynamic_coeff }

    if functions_arrival_distributions is None:
        functions_arrival_distributions={}

    arrivals = []
    if arrivals_to_single_node:
        rate = 10*load_coeff
        for f in functions:
            distr = functions_arrival_distributions.get(f["name"], "exp")
            if distr == "exp":
                arv = make_arrival_dict("edge1", f["name"], dynamic_rate_coeff, _rate=rate)
            else:
                if distr == "erlang":
                    D0,D1 = MAP.make_erlang2(rate)
                elif distr == "hyper":
                    D0,D1 = MAP.make_hyper(rate)
                elif distr == "mmpp":
                    D0,D1 = MAP.make_mmpp2(rate)
                else:
                    raise ValueError(f"unknow distr: {distr}")
                #arv = make_arrival_dict("edge1", f["name"], dynamic_rate_coeff, _map=(D0,D1))
                arv = make_arrival_dict("lb1", f["name"], dynamic_rate_coeff, _map=(D0,D1))
            arrivals.append(arv)

    else:
        edge_nodes = [n for n in nodes if "edge" in n["name"]]
        rate = 10*load_coeff/len(edge_nodes)
        for f in functions:
            distr = functions_arrival_distributions.get(f["name"], "exp")
            for n in edge_nodes:
                if distr == "exp":
                    arv = make_arrival_dict(n["name"], f["name"], dynamic_rate_coeff, _rate=rate)
                else:
                    if distr == "erlang":
                        D0,D1 = MAP.make_erlang2(rate)
                    elif distr == "hyper":
                        D0,D1 = MAP.make_hyper(rate)
                    elif distr == "mmpp":
                        D0,D1 = MAP.make_mmpp2(rate)
                    else:
                        raise ValueError(f"unknow distr: {distr}")
                    arv = make_arrival_dict(n["name"], f["name"], dynamic_rate_coeff, _map=(D0,D1))
                arrivals.append(arv)

    spec = {'classes': classes, 'nodes': nodes, 'functions': functions, 'arrivals': arrivals}
    outf.write(yaml.dump(spec))
    #print(yaml.dump(spec))
    outf.flush()

# use this function if you have your own, pre-fixed list of {functions, classes, nodes, arrivals}
def write_spec_custom(outf, functions, classes, nodes, arrivals):
    spec = {'classes': classes, 'nodes': nodes, 'functions': functions, 'arrivals': arrivals}
    outf.write(yaml.dump(spec))

if __name__ == "__main__":
    with open("spec.yml", "w") as outf:
        write_spec(outf, load_coeff=4, cloud_cost=0.001)
