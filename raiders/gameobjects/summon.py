import math
import pygame

from raiders.gameobjects._gameobject_info import ObjectInfo, CONFIG
from raiders.gameobjects._gameobject_registry import GAMEOBJECTS
from raiders.gameobjects._gameobject_utils import (
    darken, 
    polygon, 
    fill_visible_pixels, 
    DisplayLayers,
)
from raiders.gameobjects.object import Object


class Summon(Object):
    display_layer = DisplayLayers.PLAYER_BOTTOM_ELEMENT

    sprite_cache = {}
    max_size = 10
    max_health = 20

    speed = 3
    max_attack_tick = 30
    damage = 3

    lightgrey = (130, 130, 130)
    brown = (120, 80, 60)

    def __init__(self, env, pos, angle, player):
        super().__init__(env, pos, angle=angle, max_size=self.max_size, max_health=self.max_health)
        self.team = player.team
        self.player = player

        self.attack_tick = 0
    
    def step(self):
        super().step()
        
        nearby_objects = self.env.grid.getNearbyObjects(self.pos)

        # pathinding here

    def moveTowardsPos(self, pos):
        dy, dx = pos[1] - self.pos[1], pos[0] - self.pos[0]
        angle = math.atan2(dy, dx)
        self.pos = self.pos[0] + self.speed*math.cos(angle), self.pos[1] + self.speed*math.sin(angle)

    @staticmethod
    def render(info):
        relevantinfo = (info.angle, info.hit, info.team)

        if relevantinfo not in Summon.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.circle(surface, CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"], center, 8)

            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Summon.sprite_cache[relevantinfo] = surface

        sprite = Summon.sprite_cache[relevantinfo]
        return sprite
     
    def getInfo(self):
        return ObjectInfo(
            type = self.__class__.__name__,
            team = self.team,
            position = self.pos,
            angle = round(self.angle / self.incr) * self.incr,
            size = self.size,
            health = self.health,
            hit = self.hit,
            shake = self.shake,
            offset = self.offset,
            attack_tick = self.attack_tick
        )