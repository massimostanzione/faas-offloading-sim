from enum import Enum


class ContextFeature(Enum):
    MEM = "avgMemoryUtilization_sys_mobileWnd",
    CO2 = "CO2"

    def __str__(self):
        return '%s' % self.value

    def __repr__(self):
        return self.__str__()