from faas import Node

class Region:

    def __init__ (self, name: str, default_cloud = None):
        self.name = name
        self.default_cloud = default_cloud

    def is_cloud (self):
        return self.default_cloud is None

    def __eq__ (self, other):
        return self.name == other.name

    def __hash__ (self):
        return hash(self.name)

    def __repr__ (self):
        return self.name

class Infrastructure:

    def __init__ (self, regions: [Region], network_latency: dict):
        self.regions = regions
        self.latency = network_latency
        self.region_nodes = {r: []  for r in self.regions}
        self.region_dict = {r.name: r for r in self.regions}

    def get_latency (self, x, y):
        if x == y:
            return 0.0

        if (x, y) in self.latency:
            return self.latency[(x, y)]
        elif (y, x) in self.latency:
            self.latency[(x,y)] = self.latency[(y, x)]
            return self.latency[(x, y)]

        # Try to convert to regions
        if isinstance(x, Node):
            x = x.region
        if isinstance(y, Node):
            y = y.region

        if (x, y) in self.latency:
            return self.latency[(x, y)]
        elif (y, x) in self.latency:
            self.latency[(x,y)] = self.latency[(y, x)]
            return self.latency[(x, y)]
        else:
            raise KeyError(f"no latency specified for {x} and {y}")

    def get_region (self, reg_name: str) -> Region:
        return self.region_dict[reg_name]

    def add_node (self, node, region: Region):
        self.region_nodes[region].append(node)

    def get_edge_nodes (self):
        nodes = []
        for r in self.regions:
            if not r.is_cloud():
                nodes.extend(self.region_nodes[r])
        return nodes

    def get_cloud_nodes (self):
        nodes = []
        for r in self.regions:
            if r.is_cloud():
                nodes.extend(self.region_nodes[r])
        return nodes

    def get_nodes (self):
        nodes = []
        for r in self.regions:
            nodes.extend(self.region_nodes[r])
        return nodes

    def get_region_nodes (self, reg):
        return self.region_nodes[reg]

    def __repr__ (self):
        s=""
        for r in self.regions:
            s += f"-------- {r} ({r.is_cloud()} - {r.default_cloud}) -------\n"
            for n in self.region_nodes[r]:
                s += repr(n) + "\n"
        return s

