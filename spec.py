import yaml
import tempfile

# Returns an open NamedTemporaryFile
def generate_temp_spec (n_functions=5, load_coeff=1.0, dynamic_rate_coeff=1.0, arrivals_to_single_node=True,
                   n_classes=4, cloud_cost=0.00005, cloud_speedup=1.0, n_edges=5):
    ntemp = tempfile.NamedTemporaryFile(mode="w")
    write_spec(ntemp, n_functions, load_coeff, dynamic_rate_coeff, arrivals_to_single_node,
               n_classes, cloud_cost, cloud_speedup, n_edges)
    return ntemp

# Writes a spec file to outf 
def write_spec (outf, n_functions=5, load_coeff=1.0, dynamic_rate_coeff=1.0, arrivals_to_single_node=True,
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

    total_fun_weight = sum([f["duration_mean"]*f["memory"] for f in functions])

    arrivals = []
    if arrivals_to_single_node:
        total_load = 8000*load_coeff
        for f in functions:
            rate = total_load/n_functions/(f["duration_mean"]*f["memory"])
            arrivals.append({"node": "edge1",
                            "function": f["name"],
                            "rate": rate,
                            "dynamic_coeff": dynamic_rate_coeff
                            })
    else:
        edge_nodes = [n for n in nodes if "edge" in n["name"]]
        total_load = 16000*load_coeff
        load_per_node = total_load/len(edge_nodes)
        for n in edge_nodes:
            for f in functions:
                rate = load_per_node/n_functions/(f["duration_mean"]*f["memory"])
                arrivals.append({"node": n["name"],
                                "function": f["name"],
                                "rate": rate,
                                 "dynamic_coeff": dynamic_rate_coeff})

    spec = {'classes': classes, 'nodes': nodes, 'functions': functions, 'arrivals': arrivals}
    outf.write(yaml.dump(spec))
    outf.flush()
