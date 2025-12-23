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

class Effect(GameObject):
    display_layer = DisplayLayers.BOTTOM_EFFECT

    def __init__(self, env, pos, player, lifetime):
        self.env = env
        self.pos = pos
        self.player = player

        self.lifetime = lifetime

        self.effect_tick = 0
    
    def step(self):
        if self.effect_tick == 0:
            for player in self.env.getPlayers():
                if player.health <= 0: continue
                if math.dist(player.pos, self.pos) <= self.size: 
                    self.effectPlayer(player)
            self.effect_tick = self.effect_speed
        
        self.effect_tick -= 1
        self.lifetime -= 1
        if self.lifetime == 0:
            self.env.removeDynamicObject(self)
        
    def effectPlayer(self, player): pass


class Heal(Effect):
    sprite_cache = {}

    size = 40
    effect_speed = 5
    max_lifetime = 80

    healing = 0.5
    initial_healing = 3

    mutedlightred = (220, 125, 80, 120)

    def __init__(self, env, pos, player):
        super().__init__(env, pos, player, lifetime=self.max_lifetime)
    
    def effectPlayer(self, player):
        if self.lifetime == 80:
            healing = min(player.health + self.initial_healing, player.max_health) - player.health
        else:
            healing = min(player.health + self.healing, player.max_health) - player.health
        player.health += healing
        
    @staticmethod
    def render(info):
        relevantinfo = (info.size,)

        if relevantinfo not in Heal.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.circle(surface, Heal.mutedlightred, center, Heal.size-5)

            Heal.sprite_cache[relevantinfo] = surface

        sprite = Heal.sprite_cache[relevantinfo]
        return sprite
    
    def getInfo(self):
        return ObjectInfo(
            type = self.__class__.__name__,
            position = self.pos,
            size = self.size,
            attack_tick = self.effect_tick,
            lifetime = self.lifetime,
        )
    
class Explosion(Effect):
    display_layer = DisplayLayers.TOP_EFFECT
    sprite_cache = {}

    size = 60
    effect_speed = 1
    max_lifetime = 1

    damage = 8
    explodable_objects = ("Player", "Turret", "Spike", "Base", "Wall", "Resource")

    white = (255, 255, 255, 180)

    def __init__(self, env, pos, player):
        super().__init__(env, pos, player, lifetime=self.max_lifetime)
        self.explodable_objects = self.getCanHit()

    def getCanHit(self):
        return tuple(filter(None, (
                GAMEOBJECTS.get(s) for s in self.explodable_objects)))
    
    def step(self):
        if self.lifetime == 0:
            self.env.removeDynamicObject(self)
            return
        elif self.lifetime == self.max_lifetime:
            self.env.addSound("explosion", self.pos, 0.5)
        self.lifetime -= 1

        self.objects = self.env.grid.getNearbyObjects(self.pos) + self.env.dynamic_objects
        for obj in self.objects:
            if isinstance(obj, self.explodable_objects) and (math.dist(obj.pos, self.pos) <= obj.size + self.size - 0.5):
                obj.recieveHit(self, self.damage, self.player)
        
    @staticmethod
    def render(info):
        relevantinfo = (info.size,)

        if relevantinfo not in Explosion.sprite_cache:
            image_size = (200, 200)
            center = (100, 100)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.circle(surface, Explosion.white, center, Explosion.size)

            Explosion.sprite_cache[relevantinfo] = surface

        sprite = Explosion.sprite_cache[relevantinfo]
        return sprite
    
    def getInfo(self):
        return ObjectInfo(
            type = self.__class__.__name__,
            position = self.pos,
            size = self.size,
            attack_tick = self.effect_tick,
            lifetime = self.lifetime,
        )