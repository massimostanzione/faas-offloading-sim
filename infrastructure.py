class Region:

    def __init__ (self, name: str, is_cloud: bool = False):
        self.name = name
        self.is_cloud = is_cloud

    def __eq__ (self, other):
        return self.name == other.name

    def __hash__ (self):
        return hash(self.name)

class Infrastructure:

    def __init__ (self, regions: [Region], network_latency: dict):
        self.regions = regions
        self.latency = network_latency
        self.region_nodes = {r: []  for r in self.regions}
        self.region_dict = {r.name: r for r in self.regions}

    def get_latency (self, reg1: Region, reg2: Region):
        if reg1 == reg2:
            return 0.0
        if (reg1, reg2) in self.latency:
            return self.latency[(reg1, reg2)]
        elif (reg2, reg1) in self.latency:
            self.latency[(reg1,reg2)] = self.latency[(reg2, reg1)]
            return self.latency[(reg1, reg2)]
        else:
            raise KeyError("no latency specified for this pair of regions")

    def get_region (self, reg_name: str) -> Region:
        return self.region_dict[reg_name]

    def add_node (self, node, region: Region):
        self.region_nodes[region].append(node)

    def get_edge_nodes (self):
        nodes = []
        for r in self.regions:
            if not r.is_cloud:
                nodes.extend(self.region_nodes[r])
        return nodes

    def get_cloud_nodes (self):
        nodes = []
        for r in self.regions:
            if r.is_cloud:
                nodes.extend(self.region_nodes[r])
        return nodes

    def __repr__ (self):
        s=""
        for r in self.regions:
            s += f"-------- {r} -------\n"
            for n in self.region_nodes[r]:
                s += repr(n) + "\n"
        return s

