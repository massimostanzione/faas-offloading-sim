from enum import Enum


class ContextFeature(Enum):
    #MEM = "avgMemoryUtilization_sys_mobileWnd",
    #MEM = "avgActiveMemoryUtilization_sys",
    MEM_MW = "avgMemoryUtilization_sys_MW",
    MEM_ISA = "avgActiveMemoryUtilization_sys_SAMPLES",

    CO2 = "CO2"

    def __str__(self):
        return '%s' % self.value

    def __repr__(self):
        return self.__str__()