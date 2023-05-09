from faas import Function, QoSClass

class ArrivalProcess:

    def __init__ (self, function: Function, classes: [QoSClass]):
        self.function = function
        self.classes = classes

        self.class_rng = None
        self.iat_rng = None

        total_weight = sum([c.arrival_weight for c in classes])
        self.class_probs = [c.arrival_weight/total_weight for c in classes]

    def init_rng (self, class_rng, iat_rng):
        self.class_rng = class_rng
        self.iat_rng = iat_rng

    def next_iat (self):
        raise RuntimeError("Not implemented")

    def next_class (self):
        return self.class_rng.choice(self.classes, p=self.class_probs)

    def close(self):
        pass


class PoissonArrivalProcess (ArrivalProcess):

    def __init__ (self, function: Function, classes: [QoSClass], rate: float):
        super().__init__(function, classes) 
        self.rate = rate

    def next_iat (self):
        return self.iat_rng.exponential(1.0/self.rate)
