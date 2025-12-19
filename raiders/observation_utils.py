from collections import defaultdict
from raiders.gameobjects._gameobject_registry import GAMEOBJECTS


class TeamObservations:
    def __init__(self):
        self.defenders_observations = {}
        self.raiders_observations = {}
    
    def getObservations(self, team):
        if team in (1, "defender", "defenders"):
            return self.defenders_observations
        elif team in (2, "raider", "raiders"):
            return self.raiders_observations
        raise ValueError

class ObservationView:
    def __init__(self, objects, me, metadata):
        self._objects = objects
        self.me = me
        self.metadata = metadata

        # concrete type -> list of objects
        self._by_type = defaultdict(list)
        for obj in objects:
            self._by_type[obj.type].append(obj)

        # requested class -> cached flattened list (includes subclasses)
        self._cache = {}

    def _get_for_cls(self, type_):
        cached = self._cache.get(type_)
        if cached is not None:
            return cached

        out = []
        for t, objs in self._by_type.items():
            if issubclass(GAMEOBJECTS[t], GAMEOBJECTS[type_]):
                out.extend(objs)

        self._cache[type_] = out
        return out
    
    def _lookup(self, name: str):
        if name == "all":
            return self._objects
        
        if name == "self":
            return self.me

        cls = GAMEOBJECTS.get(name)
        if cls is not None:
            return self._get_for_cls(cls)
        
        for cls in GAMEOBJECTS.keys():
            if cls.lower() == name.lower():
                return self._get_for_cls(cls)
        
        raise AttributeError(name)

    # attribute access: obs.enemy
    def __getattr__(self, name):
        try:
            return self._lookup(name)
        except KeyError:
            raise AttributeError(name) from None
    
    # dict-style access: obs["enemy"]
    def __getitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("obs[...] key must be a string")
        return self._lookup(key)

    # common dict method people use
    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default

    # optional, but helps if old code does `if "enemy" in obs:`
    def __contains__(self, key):
        try:
            _ = self[key]
            return True
        except (KeyError, AttributeError, TypeError):
            return False

