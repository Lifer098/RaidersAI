from attrdict import AttrDict
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


class Wall(Object):
    display_layer = DisplayLayers.PLAYER_BOTTOM_ELEMENT

    def __init__(self, env, pos, max_size, max_health, team):
        super().__init__(env, pos=pos, max_size=max_size, max_health=max_health)
        self.team = team

    @classmethod
    def display(cls, surface, info, pos=None):
        if pos is None:
            pos = info.position

        sprite_surface = cls.render(info)
        rect = sprite_surface.get_rect(center=pos)
        surface.blit(sprite_surface, rect)
    
    def recieveHitObject(self, obj, damage):
        if isinstance(obj, GAMEOBJECTS["Bullet"]):
            self.hit = True
            self.health -= 2
    
    def getInfo(self):
        return ObjectInfo(
            type_ = self.__class__.__name__,
            position = self.pos,
            size = self.size,
            health = self.health,
            hit = self.hit,
        )
    
class WoodWall(Wall):
    sprite_cache = {}
    max_size = 20
    max_health = 25

    brown = (120, 80, 60)
    dark_brown = (104, 70, 52)

    def __init__(self, env, pos, team):
        super().__init__(env, pos, max_size=self.max_size, max_health=self.max_health, team=team)
    
    def recieveHitUpdate(self, obj, damage):
        self.env.addSound("woodhit", self.pos, 0.4)
    
    def onDeath(self, obj, damage):
        if isinstance(obj, GAMEOBJECTS["Player"]):
            player = obj
            player.changeWood(5)
        self.env.addSound("wooddie", self.pos, 0.3)
    
    @staticmethod
    def render(info):
        relevantinfo = (info.hit,)

        if relevantinfo not in WoodWall.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.polygon(surface, WoodWall.dark_brown, polygon(center, 20, 8))
            pygame.draw.polygon(surface, WoodWall.brown, polygon(center, 15, 8))
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            WoodWall.sprite_cache[relevantinfo] = surface

        sprite = WoodWall.sprite_cache[relevantinfo]
        return sprite
    
class StoneWall(Wall):
    sprite_cache = {}
    max_size = 30
    max_health = 75

    dark_grey = (66, 66, 66)
    grey = (84, 84, 84)

    def __init__(self, env, pos, team):
        super().__init__(env, pos, max_size=self.max_size, max_health=self.max_health, team=team)
    
    def recieveHitUpdate(self, obj, damage):
        self.env.addSound("stoneplace", self.pos, 0.4)
    
    def onDeath(self, obj, damage):
        if isinstance(obj, GAMEOBJECTS["Player"]):
            player = obj
            player.changeStone(10)
        self.env.addSound("stonedie", self.pos, 0.3)
    
    @staticmethod
    def render(info):
        relevantinfo = (info.hit, info.team)

        if relevantinfo not in StoneWall.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            pygame.draw.polygon(surface, StoneWall.dark_grey, polygon(center, 30, 8))
            pygame.draw.polygon(surface, CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"], polygon(center, 25, 8))
            pygame.draw.polygon(surface, StoneWall.grey, polygon(center, 21, 8))
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            StoneWall.sprite_cache[relevantinfo] = surface

        sprite = StoneWall.sprite_cache[relevantinfo]
        return sprite
    
    def getInfo(self):
        return ObjectInfo(
            type_ = self.__class__.__name__,
            position = self.pos,
            size = self.size,
            health = self.health,
            hit = self.hit,
            team = self.team,
        )
    