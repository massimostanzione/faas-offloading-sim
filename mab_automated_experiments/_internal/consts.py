import os
from enum import Enum

DEFAULT_STAT_PRINT_INTERVAL = 360
DEFAULT_MAB_UPDATE_INTERVAL = 300
DEFAULT_EXPIRATION_TIMEOUT = 600

PREFIX_CONFIGFILE = "config"
PREFIX_STATSFILE = "stats"
PREFIX_MABSTATSFILE = "mab-stats"
PREFIX_LOCKFILE = "json-lockfile-"
SUFFIX_INI = ".ini"
SUFFIX_TXT = ".txt"
SUFFIX_JSON = ".json"
SUFFIX_SVG = ".svg"
SUFFIX_YAML = ".yml"
SUFFIX_LOCK = ".lock"
SUFFIX_CONFIGFILE = SUFFIX_INI
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


METASIM_DIR = "./mab_automated_experiments"
METASIM_DIR_INTERNAL = METASIM_DIR + "/_internal"
PIPELINE_FILE = METASIM_DIR + "/PIPELINE"
EXPCONF_FILE = "expconf.ini"
BAYESOPT_OUTPUT_FILE = "bayesopt-report-humanreadable"
STATS_FILES_DIR = "../_stats"
TEMP_FILES_DIR = "../-temp"
TEMP_STATS_LOCATION = TEMP_FILES_DIR
CONFIG_FILE_PATH = TEMP_FILES_DIR
LOCK_FILE_PATH = TEMP_FILES_DIR
DEFAULT_OUTPUT_FOLDER = "output"


def get_expconf_path(experiment_name: str):
    return os.path.join(METASIM_DIR, experiment_name.strip(), EXPCONF_FILE)


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
