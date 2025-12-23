import math
import numpy as np
import pygame

from raiders.gameobjects._gameobject_registry import GAMEOBJECTS
from raiders.gameobjects._gameobject_info import MinimapInfo, ObjectInfo, CONFIG
from raiders.gameobjects._gameobject_utils import (
    darken, 
    polygon, 
    fill_visible_pixels, 
    scale_contents,
    DisplayLayers,
)
from raiders.gameobjects.object import Object


class Turret(Object):
    display_layer = DisplayLayers.PLAYER_BOTTOM_ELEMENT
    minimap_info = MinimapInfo(color=None, r=4)

    incr = math.radians(10)

    sprite_cache = {}

    max_size = 20
    max_health = 25

    max_attack_tick = 50
    initial_attack_tick = 30
    range = 750
    damage = 5

    grey = (70, 70, 70)
    lightgrey = (130, 130, 130)
    brown = (120, 80, 60)
    lightbrown = (210, 170, 130)

    def __init__(self, env, pos, angle, player):
        super().__init__(env, pos, max_size=self.max_size, max_health=self.max_health)
        self.team = player.team
        self.player = player
        self.angle = angle

        self.attack_tick = self.initial_attack_tick
    
    def step(self):
        closest_player = None
        closest_distance = math.inf
        for player in self.env.getPlayers():
            if player.health <= 0: continue
            if player.team != self.team and math.dist(player.pos, self.pos) < closest_distance:
                closest_player = player
                closest_distance = math.dist(player.pos, self.pos)

        if closest_distance > self.range:
            closest_player = None
        
        if closest_player is None: 
            closest_obj = None
            for obj in self.env.dynamic_objects:
                if not isinstance(obj, Turret): continue
                if obj.team != self.team and math.dist(obj.pos, self.pos) < closest_distance:
                    closest_obj = obj
                    closest_distance = math.dist(obj.pos, self.pos)

            if closest_distance > self.range:
                closest_obj = None
        else:
            closest_obj = closest_player

        if closest_obj is None: return

        x2, y2 = closest_obj.pos
        dx, dy = x2-self.pos[0], y2-self.pos[1]

        self.angle = math.atan2(dy, dx)
        if self.attack_tick == 0:
            self.attack()
        else:
            self.attack_tick -= 1
    
    def recieveHitObject(self, obj, damage):
        if isinstance(obj, GAMEOBJECTS["Bullet"]):
            self.health = max(0, self.health-damage)

    def recieveHitUpdate(self, obj, damage):
        super().recieveHitUpdate(obj, damage)
        self.env.addSound("structurehit", self.pos, 0.6)

    def onDeath(self, obj, damage):
        if isinstance(obj, GAMEOBJECTS["Player"]):
            player = obj
            player.changeWood(30)
            player.changeStone(15)
        self.env.addSound("stonedie", self.pos, 0.5)
    
    def attack(self):
        dx, dy = 20*math.cos(self.angle), 20*math.sin(self.angle)
        obj = GAMEOBJECTS["Bullet"](self.env, np.add(self.pos, (dx, dy)), self.angle, self.team, self.player, damage=8, speed=20, size=10, range=self.range)
        self.env.addDynamicObject(obj)
        self.attack_tick = self.max_attack_tick
        self.env.addSound("turretfire", self.pos, 0.4)

    @classmethod
    def displayOnMinimap(cls, surface, info, scale):
        if cls.minimap_info is not None:
            color, r = CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"] + [170,], cls.minimap_info.r
            pos = np.multiply(info.position, scale)
            pygame.draw.circle(surface, color, pos, r)

    @staticmethod
    def render(info):
        relevantinfo = (info.size, info.hit, info.team, info.angle)

        if relevantinfo not in Turret.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            team_color = CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"]
            s = info.size

            pygame.draw.circle(surface, darken(Turret.brown, scale=0.85), center, info.size)
            pygame.draw.circle(surface, Turret.brown, center, info.size-3)

            pygame.draw.polygon(surface, darken(Turret.grey), 
                                [
                                    (center[0], center[1] + 0.5 * s),
                                    (center[0], center[1] - 0.5 * s),
                                    (center[0] + 1.35 * s, center[1] - 0.5 * s),
                                    (center[0] + 1.35 * s, center[1] + 0.5 * s),
                                 ])
            pygame.draw.polygon(surface, Turret.grey, 
                                [
                                    (center[0], center[1] + 0.4 * s),
                                    (center[0], center[1] - 0.4 * s),
                                    (center[0] + 1.25 * s, center[1] - 0.4 * s),
                                    (center[0] + 1.25 * s, center[1] + 0.4 * s),
                                 ])

            pygame.draw.circle(surface, darken(Turret.grey, scale=1.2), center, info.size/2+3)
            pygame.draw.circle(surface, darken(Turret.grey, scale=1.7), center, info.size/2)
            pygame.draw.circle(surface, team_color, center, info.size/2-4)

            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Turret.sprite_cache[relevantinfo] = surface

        sprite = Turret.sprite_cache[relevantinfo]
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
    
    

class BigTurret(Turret):
    sprite_cache = {}

    max_size = 35
    max_health = 120

    max_attack_tick = 40
    initial_attack_tick = 30
    range = 900
    damage = 2
    middle_bullet_damage = 4
    
    def attack(self):
        dx, dy = 20*math.cos(self.angle), 20*math.sin(self.angle)
        for i in range(9):
            angle = self.angle + 6/180*math.pi*(i-4)
            dx, dy = 20*math.cos(angle), 20*math.sin(angle)
            if i == 4:
                obj = GAMEOBJECTS["Bullet"](self.env, np.add(self.pos, (dx, dy)), angle, self.team, self.player, damage=4, speed=19.5, size=15, range=self.range)
            else:
                obj = GAMEOBJECTS["Bullet"](self.env, np.add(self.pos, (dx, dy)), angle, self.team, self.player, damage=2, speed=20-1*abs(i-4), size=10, range=self.range)
            self.env.addDynamicObject(obj)
        self.attack_tick = self.max_attack_tick
        self.env.addSound("turretfire", self.pos, 0.4)

    @staticmethod
    def render(info):
        relevantinfo = (info.size, info.hit, info.team, info.angle)

        if relevantinfo not in BigTurret.sprite_cache:
            image_size = (200, 200)
            center = (100, 100)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            team_color = CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"]
            s = info.size

            pygame.draw.circle(surface, darken(Turret.brown, scale=0.85), center, info.size)
            pygame.draw.circle(surface, Turret.brown, center, info.size-3)

            pygame.draw.polygon(surface, darken(Turret.grey, 0.9), 
                                [
                                    (center[0], center[1] + 0.45 * s),
                                    (center[0], center[1] - 0.45 * s),
                                    (center[0] + 1.5 * s, center[1] - 0.45 * s),
                                    (center[0] + 1.5 * s, center[1] + 0.45 * s),
                                 ])
            pygame.draw.polygon(surface, darken(Turret.grey, 1.1), 
                                [
                                    (center[0], center[1] + 0.45 * s),
                                    (center[0], center[1] - 0.45 * s),
                                    (center[0] + 1.4 * s, center[1] - 0.45 * s),
                                    (center[0] + 1.4 * s, center[1] + 0.45 * s),
                                 ])
            pygame.draw.polygon(surface, Turret.grey, 
                                [
                                    (center[0], center[1] + s),
                                    (center[0], center[1] + 0.4 * s),
                                    (center[0] + 1.8 * s, center[1] + 0.4 * s),
                                    (center[0] + 1.2 * s, center[1] + s),
                                 ])
            pygame.draw.polygon(surface, Turret.grey, 
                                [
                                    (center[0], center[1] - s),
                                    (center[0], center[1] - 0.4 * s),
                                    (center[0] + 1.8 * s, center[1] - 0.4 * s),
                                    (center[0] + 1.2 * s, center[1] - s),
                                 ])
                                 
            
            pygame.draw.circle(surface, darken(Turret.grey, scale=1.2), center, s/2+3)
            pygame.draw.circle(surface, darken(Turret.grey, scale=1.7), center, s/2)
            pygame.draw.circle(surface, team_color, center, s/2-4)
            pygame.draw.circle(surface, darken(Turret.grey, scale=1.7), center, s/2-6)
            pygame.draw.circle(surface, team_color, center, s/2-8)

            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            BigTurret.sprite_cache[relevantinfo] = surface

        sprite = BigTurret.sprite_cache[relevantinfo]
        return sprite


class Scattershot(Turret):
    sprite_cache = {}

    max_size = 17
    max_health = 20

    max_attack_tick = 40
    initial_attack_tick = 30
    range = 300
    damage = 1.5
    
    def attack(self):
        dx, dy = 20*math.cos(self.angle), 20*math.sin(self.angle)
        da = 4/180*math.pi
        for i in range(5):
            i = i-2
            obj = GAMEOBJECTS["Bullet"](self.env, np.add(self.pos, (dx, dy)), self.angle+da*(i*abs(i)), self.team, self.player, damage=1.5, speed=20, size=6, range=300)
            self.env.addDynamicObject(obj)
        self.attack_tick = self.max_attack_tick
        self.env.addSound("turretfire", self.pos, 0.4)

    @staticmethod
    def render(info):
        relevantinfo = (info.size, info.hit, info.team, info.angle)

        if relevantinfo not in Turret.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            team_color = CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"]
            s = info.size

            pygame.draw.circle(surface, darken(Turret.lightbrown, scale=0.45), center, info.size)
            pygame.draw.circle(surface, darken(Turret.lightbrown, scale=0.6), center, info.size-3)

            pygame.draw.polygon(surface, darken(Turret.grey), 
                                [
                                    (center[0], center[1] + 0.5 * s),
                                    (center[0], center[1] - 0.5 * s),
                                    (center[0] + 1.35 * s, center[1] - 0.5 * s),
                                    (center[0] + 1.35 * s, center[1] + 0.5 * s),
                                 ])
            pygame.draw.polygon(surface, Turret.grey, 
                                [
                                    (center[0], center[1] + 0.4 * s),
                                    (center[0], center[1] + 0.1 * s),
                                    (center[0] + 1.25 * s, center[1] + 0.1 * s),
                                    (center[0] + 1.25 * s, center[1] + 0.4 * s),
                                 ])
            pygame.draw.polygon(surface, Turret.grey, 
                                [
                                    (center[0], center[1] - 0.4 * s),
                                    (center[0], center[1] - 0.1 * s),
                                    (center[0] + 1.25 * s, center[1] - 0.1 * s),
                                    (center[0] + 1.25 * s, center[1] - 0.4 * s),
                                 ])

            pygame.draw.circle(surface, darken(Turret.grey, scale=1.2), center, info.size/2+3)
            pygame.draw.circle(surface, darken(Turret.grey, scale=1.7), center, info.size/2)
            pygame.draw.circle(surface, team_color, center, info.size/2-4)

            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Turret.sprite_cache[relevantinfo] = surface

        sprite = Turret.sprite_cache[relevantinfo]
        return sprite
