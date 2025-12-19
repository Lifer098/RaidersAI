import random
import numpy as np
import pygame

from raiders.gameobjects._gameobject_registry import GAMEOBJECTS
from raiders.gameobjects._gameobject_utils import DisplayLayers
from raiders.gameobjects._gameobject_info import MinimapInfo

class GameObject:
    display_layer = DisplayLayers.DEFAULT
    minimap_info = None

    def __init__(self):
        self.shake = 0
        self.offset = (0, 0)
        self.frame = 0

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        key = cls.__name__
        GAMEOBJECTS[key] = cls

    def step(self):
        self.shake = max(0, self.shake * 0.8 - 1)
        self.offset = self.offset[0] * 0.8, self.offset[1] * 0.8

    @classmethod
    def displayOnMinimap(cls, surface, info, scale):
        if cls.minimap_info is not None:
            color, r = cls.minimap_info.color, cls.minimap_info.r
            pos = np.multiply(info.position, scale)
            pygame.draw.circle(surface, color, pos, r)

    @classmethod
    def display(cls, surface, info, pos=None):
        if pos is None:
            pos = info.position

        pos = pos[0] + (random.random()-0.5) * info.shake, pos[1] + (random.random()-0.5) * info.shake
        pos = pos[0] + info.offset[0], pos[1] + info.offset[1]

        sprite_surface = cls.render(info)
        rect = sprite_surface.get_rect(center=pos)
        surface.blit(sprite_surface, rect)

    def resetState(self): pass
    def getInfo(self): pass
        
