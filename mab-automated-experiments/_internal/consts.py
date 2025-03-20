from enum import Enum

PREFIX_STATSFILE = "stats"
PREFIX_MABSTATSFILE = "mab-stats"
SUFFIX_TXT = ".txt"
SUFFIX_JSON = ".json"
SUFFIX_SVG = ".svg"
SUFFIX_YAML = ".yml"
SUFFIX_STATSFILE = SUFFIX_TXT
SUFFIX_MABSTATSFILE = SUFFIX_JSON
SUFFIX_GRAPHFILE = SUFFIX_SVG
SUFFIX_SPECSFILE = SUFFIX_YAML

DELIMITER_COMMA = ', '
DELIMITER_HYPHEN = '-'
DELIMITER_AXIS = '>'
DELIMITER_PARAMS = '='

class ExecMode(Enum):
    NONE = 'none'
    AUTOMATED = 'automated'

class RundupBehavior(Enum):
    NO = "no"
    ALWAYS = "always"
    SKIP_EXISTENT = "skip-existent"

class RewardFnAxis(Enum):
    LOADIMB = "load_imb"
    RESPONSETIME = "rt"
    COST = "cost"
    UTILITY = "utility"
    VIOLATIONS = "violations"

RewardFnAxis_HumanReadable = {
    RewardFnAxis.LOADIMB.value: "Load imbalance",
    RewardFnAxis.RESPONSETIME.value: "Response time",
    RewardFnAxis.COST.value: "Cost",
    RewardFnAxis.UTILITY.value: "Utility",
    RewardFnAxis.VIOLATIONS.value: "Violations",
}


def get_axis_name_hr(axis:str):
    return RewardFnAxis_HumanReadable[axis]

PIPELINE_FILE = "pipeline.txt"
EXPCONF_FILE = "expconf.ini"
CONFIG_FILE = "config.ini"

class WorkloadIdentifier(Enum):
    NONE = "none"
    BASE = "base"
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    LINEAR = "linear"
    GAUSSIAN = "gaussian"