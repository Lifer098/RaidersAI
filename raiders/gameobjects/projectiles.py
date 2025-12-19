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

class Projectile(GameObject):
    display_layer = DisplayLayers.PLAYER_TOP_ELEMENT

    subframes = 12

    transparent_objects = ("Base", "Spike")
    friendly_objects = ("StoneWall", "Player", "Turret")

    def __init__(self, env, pos, angle, team, player, damage, speed, range, size):
        self.env = env
        self.pos = pos
        self.size = size
        self.angle = angle
        self.team = team
        self.player = player
        
        self.damage = damage
        self.speed = speed
        self.lifetime = range / speed
        
        self.transparent_objects, self.friendly_objects = self.getCanHit()
    
    def step(self):
        subframes = self.subframes
        if self.lifetime <= 0:
            self.handleEndOfLifetime()
            return
        self.lifetime -= 1

        self.objects = self.env.grid.getNearbyObjects(self.pos) + self.env.dynamic_objects

        dx, dy = self.speed*math.cos(self.angle)/subframes, self.speed*math.sin(self.angle)/subframes
        for frame in range(subframes):
            self.pos = (self.pos[0]+dx, self.pos[1]+dy)
            if not self.env.grid.withinBounds(self.pos):
                self.handleOutOfBounds()
            
            for obj in self.objects:
                if not isinstance(obj, GAMEOBJECTS["Object"]): continue
                if isinstance(obj, self.transparent_objects): continue
                if isinstance(obj, self.friendly_objects) and obj.team == self.team: continue

                if math.dist(obj.pos, self.pos) > obj.size + self.size - 0.5: continue

                if self.handleCollision(obj): 
                    return

    @classmethod
    def getCanHit(cls):
        return (
            tuple(filter(None, (
                GAMEOBJECTS.get(s) for s in cls.transparent_objects))), 
            tuple(filter(None, (
                GAMEOBJECTS.get(s) for s in cls.friendly_objects)))
        )
    
    def collision(self, obj):
        pass

    def resetState(self):
        pass

    def recieveHit(self, obj, damage):
        pass
    
    def getInfo(self):
        return ObjectInfo(
            type = self.__class__.__name__,
            position = self.pos,
            size = self.size,
            angle = self.angle,
            lifetime = self.lifetime,
        )
    

class Arrow(Projectile):
    damage = 4
    speed = 25
    size = 5
    range = 700

    arrow_sprite = load_asset("arrow.png")
    sprite_cache = {}

    def __init__(self, env, pos, angle, team, player):
        super().__init__(env, pos, angle, team, player, self.damage, self.speed, self.range, self.size)

    def handleCollision(self, obj):
        if isinstance(obj, GAMEOBJECTS["Player"]):
            self.env.addSound("arrowhitplayer", self.pos, 0.3)
        else:
            self.env.addSound("arrowhit", self.pos, 0.3)

        obj.recieveHit(self, self.damage, self.player)
        self.env.removeDynamicObject(self)
        return True

    def handleOutOfBounds(self):
        self.env.removeDynamicObject(self)
    
    def handleEndOfLifetime(self):
        self.env.removeDynamicObject(self)

    @staticmethod
    def render(info):
        relevantinfo = (info.angle,)

        if relevantinfo not in Arrow.sprite_cache:
            surface = pygame.transform.rotate(Arrow.arrow_sprite, -(info.angle)/math.pi*180)
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            Arrow.sprite_cache[relevantinfo] = surface

        sprite = Arrow.sprite_cache[relevantinfo]
        return sprite


class ChargedArrow(Arrow):
    damage = 6
    speed = 45
    size = 5
    range = 800

    subframes = 24

    arrow_sprite = load_asset("arrow.png")
    sprite_cache = {}

    def __init__(self, env, pos, angle, team, player):
        super().__init__(env, pos, angle, team, player)

    @staticmethod
    def render(info):
        relevantinfo = (info.angle,)

        if relevantinfo not in ChargedArrow.sprite_cache:
            surface = pygame.transform.rotate(ChargedArrow.arrow_sprite, -(info.angle)/math.pi*180)
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            ChargedArrow.sprite_cache[relevantinfo] = surface

        sprite = ChargedArrow.sprite_cache[relevantinfo]
        return sprite
    

class Bullet(Projectile):
    sprite_cache = {}

    lightgrey = (130, 130, 130)

    def __init__(self, env, pos, angle, team, player, damage, speed, size, range):
        super().__init__(env, pos, angle, team, player, damage, speed, range, size)

    def handleCollision(self, obj):
        self.env.addSound("bullethit", self.pos, 0.5)

        obj.recieveHit(self, self.damage, self.player)
        self.env.removeDynamicObject(self)
        return True

    def handleOutOfBounds(self):
        self.env.removeDynamicObject(self)
    
    def handleEndOfLifetime(self):
        self.env.removeDynamicObject(self)

    @staticmethod
    def render(info):
        relevantinfo = (info.size,)

        if relevantinfo not in Bullet.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.circle(surface, darken(Bullet.lightgrey, 0.85), center, info.size)
            pygame.draw.circle(surface, Bullet.lightgrey, center, info.size-4)

            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            Bullet.sprite_cache[relevantinfo] = surface

        sprite = Bullet.sprite_cache[relevantinfo]
        return sprite


class Frag(Projectile):
    sprite_cache = {}

    damage = 8
    speed = 8
    friction = 0.93
    size = 12
    lifetime = 40

    transparent_objects = ("Base", )
    friendly_objects = ("Spike", "StoneWall", "Player", "Turret")

    shake_scale = 15

    white = (255, 255, 255)

    def __init__(self, env, pos, angle, team, player):
        super().__init__(env, pos, angle, team, player, self.damage, self.speed, 0, self.size)
        self.lifetime = 40 # override lifetime calculation by projectile
        self.shake = 0

    def handleCollision(self, obj):
        if isinstance(obj, Projectile):
            return False
        self.speed = 0
        return False
    
    def handleOutOfBounds(self):
        self.speed = 0
    
    def handleEndOfLifetime(self):
        self.env.removeDynamicObject(self)
        explosion = GAMEOBJECTS["Explosion"](self.env, self.team, self.player)
        explosion.pos = self.pos
        self.env.addDynamicObject(explosion)

    def step(self):
        self.shake = self.shake_scale/(max(1, self.lifetime)**0.75)
        
        if self.lifetime <= 0:
            self.handleEndOfLifetime()
            return
        self.lifetime -= 1

        self.speed *= self.friction
        self.objects = self.env.grid.getNearbyObjects(self.pos) + self.env.dynamic_objects

        subframes = self.subframes
        dx, dy = self.speed*math.cos(self.angle)/subframes, self.speed*math.sin(self.angle)/subframes
        for frame in range(subframes):
            self.pos = (self.pos[0]+dx, self.pos[1]+dy)
            if not self.env.grid.withinBounds(self.pos):
                self.handleOutOfBounds()
            
            for obj in self.objects:
                if not isinstance(obj, GAMEOBJECTS["Object"]): continue
                if isinstance(obj, self.transparent_objects): continue
                if isinstance(obj, self.friendly_objects) and obj.team == self.team: continue

                if math.dist(obj.pos, self.pos) > obj.size + self.size - 0.5: continue

                self.handleCollision(obj)

    @staticmethod
    def render(info):
        relevantinfo = (info.size,)

        if relevantinfo not in Frag.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.circle(surface, Frag.white, center, info.size)

            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            Frag.sprite_cache[relevantinfo] = surface

        sprite = Frag.sprite_cache[relevantinfo]
        return sprite

    def getInfo(self):
        return ObjectInfo(
            type = self.__class__.__name__,
            position = self.pos,
            size = self.size,
            angle = self.angle,
            lifetime = self.lifetime,
            shake = self.shake,
        )