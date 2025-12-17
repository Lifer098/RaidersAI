import pygame
import math

from raiders.gameobjects._gameobject_info import ObjectInfo, CONFIG
from raiders.gameobjects._gameobject_registry import GAMEOBJECTS
from raiders.gameobjects._gameobject_utils import (
    DisplayLayers,
    darken, 
    polygon, 
    fill_visible_pixels, 
    scale_contents,
    load_asset,
)

from raiders.gameobjects.gameobject import GameObject

class Object(GameObject):
    shake_scale = 0
    move_scale = 0

    def __init__(self, env, pos, max_health, max_size, min_size=None, team=-1):
        self.env = env
        self.pos = tuple(pos)
        self.max_size = max_size
        self.min_size = min_size if min_size is not None else max_size
        self.max_health = max_health
        self.team = team

        self.health = max_health
        self.size = max_size

        self.shake = 0
        self.offset = (0, 0)
        self.hit = False

    def recieveHit(self, obj, damage, player):
        pre_hit_health = self.health
        if isinstance(obj, GAMEOBJECTS["Player"]):
            self.hit = True
            damage = min(self.health, damage)
            self.health -= damage
            self.recieveHitPlayer(obj, damage)
        elif isinstance(obj, GAMEOBJECTS["Explosion"]):
            self.hit = True
            damage = min(self.health, damage)
            self.health -= damage
        else:
            self.recieveHitObject(obj, damage)
        
        if self.health != pre_hit_health:
            damage = pre_hit_health - self.health
            self.recieveHitUpdate(obj, damage)
        
        if self.health <= 0:
            self.env.removeObject(self)
            self.onDeath(obj, damage)
    
    def recieveHitUpdate(self, player, damage):
        ratio = self.health / self.max_health
        self.size = self.max_size * ratio + self.min_size * (1 - ratio)
        self.shake = damage * self.shake_scale

        dy, dx = self.pos[1] - player.pos[1], self.pos[0] - player.pos[0]
        angle = math.atan2(dy, dx)
        self.offset = self.offset[0] + damage * self.move_scale * math.cos(angle), self.offset[1] + damage * self.move_scale * math.sin(angle)
    
    def resetState(self): 
        self.hit = False

    def recieveHitObject(self, obj, damage): pass
    def recieveHitPlayer(self, obj, damage): pass
    def onDeath(self, obj, damage): pass

    def getInfo(self):
        return ObjectInfo(
            type_ = self.__class__.__name__,
            position = self.pos,
            size = self.size,
            health = self.health,
            hit = self.hit,
            shake = self.shake,
            offset = self.offset
        )

