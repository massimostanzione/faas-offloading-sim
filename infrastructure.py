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
        self.node2neighbors = {}

    def get_latency (self, x, y):
        if x == y:
            return 0.0

        if (x, y) in self.latency:
            return self.latency[(x, y)]
        elif (y, x) in self.latency:
            self.latency[(x,y)] = self.latency[(y, x)]
            return self.latency[(x, y)]

        if not isinstance(x, Node) and not isinstance(y, Node):
            raise KeyError(f"no latency specified for {x} and {y}")

        # Try to convert to regions
        if isinstance(x, Node):
            x = x.region
        if isinstance(y, Node):
            y = y.region

        return self.get_latency(x, y)

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

    def get_neighbors (self, node, node_choice_rng, max_peers=3):
        if node in self.node2neighbors:
            peers = self.node2neighbors[node]
        else:
            peers = self.get_region_nodes(node.region).copy()
            peers.remove(node)
            self.node2neighbors[node] = peers

        if max_peers > 0 and len(peers) > max_peers:
            return node_choice_rng.choice(peers, max_peers) # TODO: random selection
        else:
            return peers

    def __repr__ (self):
        s=""
        for r in self.regions:
            s += f"-------- {r} ({r.is_cloud()} - {r.default_cloud}) -------\n"
            for n in self.region_nodes[r]:
                s += repr(n) + "\n"
        return s

