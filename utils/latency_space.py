import math
import random

class Point:
    def __init__(self, coordinates: list = []) -> None:
        self.coordinates = coordinates

class Space:
    def __init__(self, dimensionality) -> None:
        self.dimensionality = dimensionality

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


class Force:
    def __init__(self, space: Space, ) -> None:
        super().__init__()
        self.space = space
        self.versor = [0] * space.dimensionality
        self.magnitude = 0
    
    def _compute_versor(self, a: Point, b: Point) -> []:
        s_sum = 0
        versor = [0] * self.space.dimensionality
        for i in range(self.space.dimensionality):
            versor[i] = b.coordinates[i] - a.coordinates[i]
            s_sum += abs(versor[i])
        if s_sum == 0:
            for i in range(self.space.dimensionality):
              versor[i] = random.uniform(0, 1)
              s_sum += versor[i]
        for i in range(self.space.dimensionality):
            versor[i] = versor[i] / s_sum
        return versor
    
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

    def __get_versor(self, step: float = 1.0) -> []:
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

    def compute_utilization_component(self, curr:Point, other:Point, datarate: float) -> float:
        distance = self.space.distance(curr, other)
        return distance * datarate
    