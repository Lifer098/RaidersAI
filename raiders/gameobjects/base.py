import math
import numpy as np
import pygame

from raiders.gameobjects._gameobject_registry import GAMEOBJECTS
from raiders.gameobjects._gameobject_info import ObjectInfo, CONFIG
from raiders.gameobjects._gameobject_utils import (
    darken, 
    polygon, 
    fill_visible_pixels, 
    scale_contents,
    DisplayLayers,
)
from raiders.gameobjects.object import Object


class Base(Object):
    sprite_cache = {}

    max_size = 40
    max_health = 100
    
    regen = 2

    white = (255, 255, 255)
    lightergrey = (180, 180, 180)
    team_color = CONFIG["team_colors"]["defenders"]

    def __init__(self, env, pos, team):
        super().__init__(env, pos, max_size=self.max_size, max_health=self.max_health, team=team)
    
    def recieveHitUpdate(self, player, damage):
        super().recieveHitUpdate(player, damage)
        
        self.env.addSound("structurehit", self.pos, 0.6)
        self.env.addSound("basehit", self.pos, 0.4)
        self.env.addSound("basedie", self.pos, 0.3)
        
    def onDeath(self, obj, damage):
        self.env.removeDynamicObject(self)
        self.env.addSound("basedie", self.pos, 0.8)
    
    def step(self):
        if self.health > 0:
            self.health = min(100, self.health + 0.01)

    @staticmethod
    def render(info):
        relevantinfo = (info.size, info.health, info.hit)

        if relevantinfo not in Base.sprite_cache:
            image_size = (200, 200)
            center = (100, 100)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            scale = max(info.health, 0) / 100
            if scale:
                pygame.draw.circle(surface, Base.team_color, center, info.size+8)
                pygame.draw.polygon(surface, Base.white, polygon(center, info.size*scale+3, 8))
                pygame.draw.polygon(surface, [Base.lightergrey, Base.white][info.hit], polygon(center, info.size*scale, 8))
            else:
                pygame.draw.circle(surface, (170, 170, 170), center, info.size+8)
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            Base.sprite_cache[relevantinfo] = surface

        sprite = Base.sprite_cache[relevantinfo]
        return sprite