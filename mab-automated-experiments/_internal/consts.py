from enum import Enum

DEFAULT_STAT_PRINT_INTERVAL = 360
DEFAULT_MAB_UPDATE_INTERVAL = 300
DEFAULT_EXPIRATION_TIMEOUT = 600

PREFIX_STATSFILE = "stats"
PREFIX_MABSTATSFILE = "mab-stats"
PREFIX_LOCKFILE = "json-lockfile-"
SUFFIX_TXT = ".txt"
SUFFIX_JSON = ".json"
SUFFIX_SVG = ".svg"
SUFFIX_YAML = ".yml"
SUFFIX_LOCK = ".lock"
SUFFIX_STATSFILE = SUFFIX_TXT
SUFFIX_MABSTATSFILE = SUFFIX_JSON
SUFFIX_GRAPHFILE = SUFFIX_SVG
SUFFIX_SPECSFILE = SUFFIX_YAML
SUFFIX_LOCKFILE = SUFFIX_LOCK

DELIMITER_COMMA = ','
DELIMITER_COMMASPACE = ', '
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
    COLD_STARTS = "cold_starts"

RewardFnAxis_HumanReadable = {
    RewardFnAxis.LOADIMB.value: "Load imbalance",
    RewardFnAxis.RESPONSETIME.value: "Response time",
    RewardFnAxis.COST.value: "Cost",
    RewardFnAxis.UTILITY.value: "Utility",
    RewardFnAxis.VIOLATIONS.value: "Violations",
    RewardFnAxis.COLD_STARTS.value: "Cold starts",
}


def get_axis_name_hr(axis:str):
    return RewardFnAxis_HumanReadable[axis]

PIPELINE_FILE = "pipeline.txt"
EXPCONF_FILE = "expconf.ini"
CONFIG_FILE = "config.ini"
BAYESOPT_OUTPUT_FILE = "bayesopt-report-humanreadable"
STATS_FILES_DIR = "../_stats"
TEMP_FILES_DIR = "../-temp"
TEMP_STATS_LOCATION = TEMP_FILES_DIR
CONFIG_FILE_PATH = TEMP_FILES_DIR
LOCK_FILE_PATH = TEMP_FILES_DIR
DEFAULT_OUTPUT_FOLDER="output"


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