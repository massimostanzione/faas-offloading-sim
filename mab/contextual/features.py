from enum import Enum


class ContextFeature(Enum):
    MEM = "avgMemoryUtilization",
    CO2 = "CO2"

    def __str__(self):
        return '%s' % self.value
