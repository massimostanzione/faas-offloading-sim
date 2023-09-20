import math
from numpy.random import default_rng
from faas import Node

from infrastructure import Infrastructure

vivaldi_error_update_factor = 0.5
vivaldi_update_factor = 0.25

class Point:
    initial_error = 1
    def __init__(self, coordinates: list = []) -> None:
        self.coordinates = coordinates
        self.error = Point.initial_error
        self.num_updates = 0

class Space:
    def __init__(self, dimensionality, rng = default_rng(1024)) -> None:
        self.dimensionality = dimensionality
        self.rng = rng

    def new_point(self, coordinates: list = []) -> Point:
        if len(coordinates) != self.dimensionality:
           raise "Cardinality of point coordinates mismatches the space dimensionality"
        return Point(coordinates) 

    def difference(self, a: Point, b: Point) -> Point:
        if a == None or a == None:
            return None
        np = Point([0] * self.dimensionality)
        for i in range(self.dimensionality):
            np.coordinates[i] = a.coordinates[i] - b.coordinates[i]
        return np

    def norm(self, a: Point) -> float:
        if a == None:
            return float("nan")
        squareSum = 0
        for i in range(self.dimensionality):
            squareSum += a.coordinates[i]**2
        return math.sqrt(squareSum)

    def multiply(self, a: float, b: Point) -> Point:
        if a == None or a == None:
            return None
        np = Point([0] * self.dimensionality)
        for i in range(self.dimensionality):
            np.coordinates[i] = a * b.coordinates[i]
        return np

    def distance(self, a: Point, b: Point) -> float:
        if a == None or a == None:
            return None
        distance = 0
        for i in range(self.dimensionality):
            distance += (a.coordinates[i] - b.coordinates[i]) ** 2
        return math.sqrt(distance)

    def unit_vector(self, a:Point, b:Point) -> list:
        if a == None or a == None:
          return None
        s_sum = 0
        versor = [0] * self.dimensionality
        for i in range(self.dimensionality):
            versor[i] = a.coordinates[i] - b.coordinates[i]
            s_sum += abs(versor[i])
        if s_sum == 0:
            for i in range(self.dimensionality):
              versor[i] = self.rng.random()
              s_sum += versor[i]
        for i in range(self.dimensionality):
            versor[i] = versor[i] / s_sum
        return versor

class NetworkCoordinateSystem:
    def __init__(self, infra:Infrastructure, space: Space, rng = default_rng(1024)) -> None:
        self.infra = infra
        self.space = space
        self.coordinates = {}
        self.rng = rng
        self.__initialize_ncs()

    def __initialize_ncs(self) -> None:
        for node in self.infra.get_nodes():
          # Generate random coordinates for nodes
          random_coordinates = self.rng.random(size=self.space.dimensionality)
          self.coordinates[node] = self.space.new_point(random_coordinates)
        # It is okay to update ncs here, since we are not dynamically moving nodes 
        self.update_ncs()
        
    def get_coordinates(self, node : Node) -> Point:
        return self.coordinates.get(node)
    
    def get_nearest_node(self, position : Point) -> Node: 
        min_distance = float("inf")
        min_node = None
        for node in self.infra.get_nodes():
            node_coord = self.coordinates[node]
            distance = self.space.distance(position, node_coord)
            if min_distance > distance: 
                min_distance = distance
                min_node = node
        return min_node
   
    def __update_i(self, point_i: Point, other: Point, rtt:float) -> bool:
        # Vivaldi algorithm
        if rtt < 0 or rtt > 5 * 60 * 1000:
            return False
        
        if point_i.error + other.error == 0:
            return False

        # Sample weight balances local and remote error. (1)
        w = point_i.error  / (other.error + point_i.error)
        
        # Compute relative error of this sample. (2)
        estimated_latency = self.space.distance(point_i, other)
        es = abs(rtt - estimated_latency) / rtt

        # Update weighted moving average of local error. (3)
        new_error = es * vivaldi_error_update_factor * w + point_i.error * (1 - vivaldi_error_update_factor * w)
        
        # Update local coordinates. (4)
        delta = vivaldi_update_factor * w
        force_direction_on_i  = self.space.unit_vector(point_i, other)
        for i in range(len(force_direction_on_i)):
            point_i.coordinates[i] = delta * (rtt - estimated_latency) * force_direction_on_i[i]

        # Update point additional information
        point_i.error = new_error
        point_i.num_updates += 1

    def update_ncs(self) -> None:
        error = 0
        last_error = Point.initial_error
        convergence = 0.1
        while abs(last_error - error) > convergence:
            last_error = error
            error = 0
            for node_i in self.infra.get_nodes():
              coord_i = self.coordinates[node_i]
              for node_j in self.infra.get_nodes():
                if node_i == node_j:
                    continue
                coord_j = self.coordinates[node_j]
                rtt = self.infra.get_latency(node_i, node_j)
                self.__update_i(coord_i, coord_j, rtt)
              error += coord_i.error
            error /= len(self.infra.get_nodes())
        print(f"Network coordinate system update (average error: {error})")
        

class Force:
    def __init__(self, space: Space) -> None:
        super().__init__()
        self.space = space
        self.versor = [0] * space.dimensionality
        self.magnitude = 0
    
    def _compute_versor(self, a: Point, b: Point) -> list:
        return self.space.unit_vector(b, a)
    
    def _compute_magnitude(self, a: Point, b: Point, datarate: float) -> float:
        return self.space.distance(a, b) * datarate

class SpringForce(Force):
    def __init__(self, space: Space, p_from: Point = None, p_to: Point = None, datarate: float = 1.0) -> None:
        super().__init__(space)
        if p_from != None and p_to != None:
            self.versor = self._compute_versor(p_from, p_to)
            self.magnitude = self._compute_magnitude(p_from, p_to, datarate)

    def multiply(self, factor: float) -> None:
        self.magnitude = self.magnitude * factor

    def add(self, other: type[Force]) -> None:
        if other == None:
            return None
        sum = 0
        s_sum = 0
        for i in range(len(self.versor)):
            self.versor[i] = self.versor[i] * self.magnitude + \
                other.versor[i] * other.magnitude
            sum += abs(self.versor[i])
            s_sum += self.versor[i] ** 2
        if s_sum == 0:
            self.magnitude = 0
        else:
            self.magnitude = math.sqrt(s_sum)
        if sum > 0:
            for i in range(len(self.versor)):
                self.versor[i] = self.versor[i] / sum

    def lt(self, threshold: float) -> bool:
        return self.magnitude < threshold

    def gt(self, threshold: float) -> bool:
        return self.magnitude > threshold

    def is_null(self) -> bool:
        return self.magnitude == 0

    def move_point(self, p: Point, time: float) -> Point:
        if p == None:
            return None
        if len(p.coordinates) != len(self.versor):
            return None
        np = Point([0] * len(p.coordinates))
        for i in range(len(p.coordinates)):
            np.coordinates[i] = p.coordinates[i] + \
                time * self.magnitude * self.versor[i]
        return np

    def __str__(self) -> str:
        return "SPRING FORCE!"

class GradientEstimate(Force):
    def __init__(self, space: Space) -> None:
        super().__init__(space)
        self.gradient = None
    
    def add(self, curr: Point, other:Point, datarate:float) -> None:
        ''' Alg 2, line 5 '''
        if other == None:
            return None
        
        gradient_component = self._compute_versor(curr, other)
        if self.gradient == None:
            self.gradient = [0] * len(gradient_component)

        for i in range(len(gradient_component)):
            self.gradient[i] += gradient_component[i] * datarate

    def __get_versor(self, step: float = 1.0) -> list:
        ''' Alg 2, step x u(vect{f}) '''
        sum = 0
        versor = [0] * len(self.gradient)
        if step == 0:
            return versor
        for i in range(len(self.gradient)):
            sum += abs(self.gradient[i])
        if sum > 0:
            for i in range(len(versor)):
                versor[i] = step * (self.gradient[i] / sum)
        return versor
    
    def new_point_position(self, curr:Point, step: float = 1.0) -> Point:
        versor = self.__get_versor(step)
        if len(versor) != len(curr.coordinates) or len(versor) != self.space.dimensionality:
            raise "Invalid dimensionality"
        new_point = self.space.new_point([0] * len(curr.coordinates))
        for i in range(len(curr.coordinates)):
            new_point.coordinates[i] = curr.coordinates[i] + versor[i]
        return new_point

    def compute_utilization_component(self, curr:Point, other_points:[(Node, Point, float)]) -> float:
        distance = 0
        for (_, other_point, datarate) in other_points:
            distance += datarate * self.space.distance(curr, other_point)
        return distance
    