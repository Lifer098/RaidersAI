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

class Spike(Object):
    display_layer = DisplayLayers.PLAYER_BOTTOM_ELEMENT

    sprite_cache = {}
    max_size = 17
    max_health = 35

    max_attack_tick = 5
    damage = 3

    shake_scale = .75
    move_scale = .75

    lightgrey = (130, 130, 130)
    brown = (120, 80, 60)

    def __init__(self, env, pos, angle, player):
        super().__init__(env, pos, angle=angle, max_size=self.max_size, max_health=self.max_health)
        self.team = player.team
        self.player = player

        self.attack_tick = 0

    def recieveHitUpdate(self, obj, damage):
        super().recieveHitUpdate(obj, damage)
        self.env.addSound("structurehit", self.pos, 0.6)
    
    def onDeath(self, obj, damage):
        if isinstance(obj, GAMEOBJECTS["Player"]):
            player = obj
            player.changeWood(4)
            player.changeStone(4)
        self.env.removeDynamicObject(self)
        self.env.addSound("wooddie", self.pos, 0.3)
    
    def step(self):
        super().step()
        self.attack_tick -= 1
        if self.attack_tick <= 0:
            for player in self.env.getPlayers():
                if player.team != self.team and math.dist(player.pos, self.pos) < player.size + self.size + 2:
                    player.recieveHit(self, self.damage, self.player)
            self.attack_tick = self.max_attack_tick

    @staticmethod
    def render(info):
        relevantinfo = (info.angle, info.hit, info.team)

        if relevantinfo not in Spike.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.polygon(surface, darken(Spike.lightgrey, scale=0.9), polygon(center, 15, 3, 1))
            pygame.draw.polygon(surface, darken(Spike.lightgrey, scale=0.9), polygon(center, 15, 3, -1))
            pygame.draw.polygon(surface, Spike.lightgrey, polygon(center, 12, 3, 1))
            pygame.draw.polygon(surface, Spike.lightgrey, polygon(center, 12, 3, -1))
            pygame.draw.circle(surface, darken(Spike.brown, scale=0.94), center, 18.5)
            pygame.draw.circle(surface, darken(Spike.brown, scale=1.1), center, 15)
            pygame.draw.circle(surface, CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"], center, 8)

            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Spike.sprite_cache[relevantinfo] = surface

        sprite = Spike.sprite_cache[relevantinfo]
        return sprite
     
    def getInfo(self):
        return ObjectInfo(
            type = self.__class__.__name__,
            team = self.team,
            position = self.pos,
            angle = self.angle,
            size = self.size,
            health = self.health,
            hit = self.hit,
            shake = self.shake,
            offset = self.offset,
            attack_tick = self.attack_tick
        )