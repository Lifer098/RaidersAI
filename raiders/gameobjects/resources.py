import pygame
import math
import random

from raiders.gameobjects._gameobject_info import MinimapInfo, ObjectInfo, CONFIG
from raiders.gameobjects._gameobject_registry import GAMEOBJECTS
from raiders.gameobjects._gameobject_utils import (
    DisplayLayers,
    darken, 
    polygon, 
    fill_visible_pixels, 
    scale_contents,
    load_asset,
)

from raiders.gameobjects.object import Object


class Resource(Object):
    display_layer = DisplayLayers.BOTTOM_RESOURCE

    def __init__(self, env, pos, max_health, max_size):
        angle = random.uniform(0, 2*math.pi)
        super().__init__(env, pos=pos, angle=angle, max_health=max_health, max_size=max_size, min_size=0.5*max_size)


class Bush(Resource):
    minimap_info = MinimapInfo(color=(200, 40, 60, 100), r=4)

    sprite_cache = {}
    max_size = 20
    max_health = 15

    shake_scale = 2
    move_scale = 1.2

    green = (100, 170, 70)
    darkgreen = (92, 135, 52)
    mutedred = (180, 120, 90)

    def __init__(self, env, pos):
        super().__init__(env, pos=pos, max_size=Bush.max_size, max_health=Bush.max_health)

    def recieveHitPlayer(self, player, damage):
        player.changeFood(damage)
    
    def recieveHitUpdate(self, obj, damage):
        super().recieveHitUpdate(obj, damage)
        self.env.addSound("bushhit", self.pos, 1)

    @staticmethod
    def render(info):
        relevantinfo = (info.angle, info.size, info.hit)

        if relevantinfo not in Bush.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            for p in polygon(center, 10, 6): # outline
                pygame.draw.circle(surface, darken(Bush.darkgreen, 0.89), p, 18)
            for p in polygon(center, 6, 6): # fill
                pygame.draw.circle(surface, darken(Bush.darkgreen, 1.02), p, 16)
            for p in polygon(center, 7, 3): # berries
                pygame.draw.circle(surface, darken(Bush.mutedred, 0.9), p, 7)
            
            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)

            scale = info.size / Bush.max_size
            surface = scale_contents(surface, scale)
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Bush.sprite_cache[relevantinfo] = surface

        sprite = Bush.sprite_cache[relevantinfo]
        return sprite


class Tree(Resource):
    display_layer = DisplayLayers.TOP_RESOURCE
    minimap_info = MinimapInfo(color=(50, 190, 40, 100), r=4)

    sprite_cache = {}
    max_size = 30
    max_health = 25

    shake_scale = 2.5
    move_scale = 1.5

    green = (100, 170, 70)
    darkgreen = (92, 135, 52)

    def __init__(self, env, pos):
        super().__init__(env, pos=pos, max_size=Tree.max_size, max_health=Tree.max_health)

    def recieveHitPlayer(self, player, damage):
        player.changeWood(damage)
    
    def recieveHitUpdate(self, obj, damage):
        super().recieveHitUpdate(obj, damage)
        self.env.addSound("woodhit", self.pos, 0.8)
        self.env.addSound("bushhit", self.pos, 0.4)
    
    @staticmethod
    def render(info):
        relevantinfo = (info.angle, info.size, info.hit)

        if relevantinfo not in Tree.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            p1 = polygon(center, 22.5, 3)
            p2 = polygon(center, 22.5, 3, flip=-1)
            pygame.draw.polygon(surface, Tree.darkgreen, p1, width=13)
            pygame.draw.polygon(surface, Tree.darkgreen, p2, width=13)
            for p in (p1 + p2):
                pygame.draw.circle(surface, Tree.darkgreen, p, 7)
            pygame.draw.polygon(surface, darken(Tree.darkgreen, scale=1.1), polygon(center, 20.5, 3))
            pygame.draw.polygon(surface, darken(Tree.darkgreen, scale=1.1), polygon(center, 20.5, 3, flip=-1))

            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)
            
            scale = info.size / Tree.max_size
            surface = scale_contents(surface, scale)
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Tree.sprite_cache[relevantinfo] = surface

        sprite = Tree.sprite_cache[relevantinfo]
        return sprite
    

class Stone(Resource):
    minimap_info = MinimapInfo(color=(160, 160, 160, 100), r=4)

    sprite_cache = {}
    max_size = 40
    max_health = 50

    shake_scale = 0.5
    move_scale = 0.5

    lightgrey = (130, 130, 130)
    lightergrey = (180, 180, 180)

    def __init__(self, env, pos):
        super().__init__(env, pos=pos, max_size=self.max_size, max_health=self.max_health)

    def recieveHitPlayer(self, player, damage):
        player.changeStone(damage)
    
    def recieveHitUpdate(self, obj, damage):
        super().recieveHitUpdate(obj, damage)
        self.env.addSound("stonehit", self.pos, 1)

    @staticmethod
    def render(info):
        relevantinfo = (info.angle, info.size, info.hit)

        if relevantinfo not in Stone.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.polygon(surface, darken(Stone.lightgrey, scale=0.9), polygon(center, 40, 8))
            pygame.draw.polygon(surface, Stone.lightgrey, polygon(center, 32, 7))
            pygame.draw.polygon(surface, darken(Stone.lightgrey, scale=1.15), polygon(center, 20, 6))

            surface = pygame.transform.rotate(surface, -(info.angle)/math.pi*180)
            
            scale = info.size / Stone.max_size
            surface = scale_contents(surface, scale)
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Stone.sprite_cache[relevantinfo] = surface

        sprite = Stone.sprite_cache[relevantinfo]
        return sprite
