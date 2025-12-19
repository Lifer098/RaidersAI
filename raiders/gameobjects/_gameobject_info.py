import yaml, os
from collections import namedtuple

base_dir = os.path.dirname(__file__)
config_path = os.path.join(base_dir, "..", "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

infos = [
    ("type", None),
    ("position", None),
    ("size", None),
    ("health", None),
    ("angle", None),
    ("hit", None),
    ("team", None),
    ("attack_tick", None),
    ("lifetime", None),
    ("shake", 0),
    ("offset", (0,0)),
    ("relative_position", None),
]
player_infos = [
    ("id_", None),
    ("food", None),
    ("wood", None),
    ("stone", None),
    ("active", None),
    ("frames", None),
    ("kills", None),
]

ObjectInfo = namedtuple("ObjectInfo", 
    [info[0] for info in infos]
)
ObjectInfo.__new__.__defaults__ = tuple(
    info[1] for info in infos
)

PlayerInfo = namedtuple("PlayerInfo", 
    [info[0] for info in infos+player_infos]
)
PlayerInfo.__new__.__defaults__ = tuple(
    info[1] for info in infos+player_infos
)