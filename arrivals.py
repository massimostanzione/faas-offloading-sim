from faas import Function, QoSClass

class ArrivalProcess:

    def __init__ (self, function: Function, classes: [QoSClass]):
        self.function = function
        self.classes = classes

    def next (self):
        raise RuntimError("Not implemented")

class PoissonArrivalProcess (ArrivalProcess):

    def __init__ (self, function: Function, classes: [QoSClass], rate: float):
        super().__init__(function, classes) 
        self.rate = rate

    def next (self):
        raise RuntimError("Not implemented")
