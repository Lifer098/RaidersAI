import pygame

import numpy as np
import random, math, time
from attrdict import AttrDict
import os, yaml
from enum import IntEnum

from raiders.gameobjects._gameobject_registry import GAMEOBJECTS
from raiders.gameobjects.object import Object
from raiders.gameobjects.resources import (
    Resource,
    Bush,
    Tree,
    Stone,
)
from raiders.gameobjects.walls import (
    Wall,
    WoodWall,
    StoneWall,
)
from raiders.gameobjects.spike import (
    Spike,
)
from raiders.gameobjects.projectiles import (
    Projectile,
    Arrow,
    ChargedArrow,
    Frag,
    Bullet,
)
from raiders.gameobjects.effects import (
    Effect,
    Heal,
    Explosion,
)
from raiders.gameobjects.turrets import (
    Turret,
    BigTurret,
    Scattershot,
)
from raiders.gameobjects.base import (
    Base,
)

from raiders.sound_utils import SoundUtils
from raiders.config_loader import load_config
CONFIG = load_config()

pygame.init()
pygame.display.set_mode((1, 1))  # Minimal dummy window

WHITE = (255,255,255)

def darken(color, scale=0.8):
    return tuple(c*scale for c in color)

def polygon(center, radius, n, flip=1):
    radius = radius/math.cos(math.pi/n)
    cx,cy = center
    points = []
    for i in range(n):
        angle = 2*math.pi * (i+0.5)/n
        x = radius * math.cos(angle) * flip
        y = radius * math.sin(angle)
            
        points.append((x+cx, y+cy))
    return points

def cast(value: str):
    value = value.strip()

    # Try boolean first
    if value.lower() == 'true':
        return True
    elif value.lower() == 'false':
        return False

    # Try integer
    try:
        return int(value)
    except ValueError:
        return value  # Return original string if no match


def loadAsset(file):
    base_dir = os.path.dirname(__file__)
    assets_dir = os.path.join(base_dir, "assets")

    if ".png" == file[-4:]:
        return pygame.image.load(os.path.join(assets_dir, "images", file))
    else:
        print("Cannot load asset {file}")

base_dir = os.path.dirname(__file__)
assets_dir = os.path.join(base_dir, "assets")
cache_folder = os.path.join(base_dir, "assets", "images")

image_files = [f for f in os.listdir(cache_folder) if f.endswith((".png", ".jpg", ".jpeg"))]
keys = [tuple(cast(v) for v in info[:-4].split('_')) for info in image_files]

sprites = {
    "raider": loadAsset("raider.png"),
    "defender": loadAsset("defender.png"),
    "sword": loadAsset("sword.png"),
    "bow": loadAsset("bow.png"),
    "axe": loadAsset("axe.png"),
    "arrow": loadAsset("arrow.png"),
}
for key, path in zip(keys, image_files):
    surf = pygame.image.load(os.path.join(cache_folder, path)).convert()
    surf.set_colorkey((0,0,0))
    sprites[key] = surf


class DUMMYPLAYER():
    def __init__(self):
        self.food = 0
        self.wood = 0
        self.stone = 0
        self.team = -1
        self.events = AttrDict({
            "change_food": 0,
            "change_wood": 0,
            "change_stone": 0,
            "change_health": 0,
            "change_health_enemy_player": 0,
            "damage_dealt_enemy_structure": 0,
            "change_health_team_player": 0,
            "damage_dealt_team_structure": 0,
            "killed_enemy_player": 0,
            "died": 0,
            "self_damage_dealt_base": 0,
            "damage_dealt_base": 0,
        })
    
    def changeHealth(self, v): pass
    def changeFood(self, v): pass
    def changeWood(self, v): pass
    def changeStone(self, v): pass


class Actives(IntEnum):
    SWORD = 1
    BOW = 2
    AXE = 3
    FRAG = 4
    WOODWALL = 5
    STONEWALL = 6
    SPIKE = 7
    TURRET = 8
    HEAL = 9
    SCATTERSHOT = 10
    BIGTURRET = 11


class Player(Object):
    type_ = "Player"

    def __init__(self, env, pos, team, id_):
        self.costs = AttrDict({
            "arrow": 2,
            "frag": 15,
            "woodwall": 10,
            "stonewall": 20,
            "spike": (12, 12),
            "turret": (90, 70),
            "scattershot": (40, 30),
            "bigturret": (200, 160),
            "heal": 15,
        })

        self.id_ = id_
        self.name = f"Player {id_}"
        self.env = env
        self.pos = list(pos)
        self.team = team
        self.angle = 0
        self.size = 15
        self.color = self.env.colors[f"team{self.team}"]

        self.dead_tick = 0
        self.max_dead_tick = 20

        self.health = 30
        self.attack_tick = 0
        self.attack_frames = None
        self.attacking = False
        self.attack_size = 20
        self.frames = [0,0,0]
        
        self.speed = 4
        self.slow_speed = 2
        self.slow_duration = 15
        self.slow_tick = 0
        self.knockback_dir = (0,0)
        self.knockback_duration = 3
        self.knockback_tick = 0

        self.active = 1
        self.active_attack = -1

        self.sword_resource_damage = 2
        self.sword_wall_damage = 3
        self.axe_resource_damage = 6
        self.axe_wall_damage = 12

        self.view_minimap = 0    

        self.food = 100
        self.wood = 200
        self.stone = 200

        self.hit = False
        self.consec_held = 0
        self.buffer = False

        self.last_active = 1

        self.hit_objects = set()
        self.kills = 0
        self.resetEvents()

    def resetEvents(self):
        self.events = AttrDict({
            "change_food": 0,
            "change_wood": 0,
            "change_stone": 0,
            "change_health": 0,
            "change_health_enemy_player": 0,
            "damage_dealt_enemy_structure": 0,
            "change_health_team_player": 0,
            "damage_dealt_team_structure": 0,
            "killed_enemy_player": 0,
            "died": 0,
            "self_damage_dealt_base": 0,
            "damage_dealt_base": 0,
        })
    
    def changeHealth(self, health):
        if health < 0:
            self.env.addSound("playerhurt", self.pos, 0.2)
        self.events.change_health += health
        self.health += health

    def changeFood(self, food):
        self.events.change_food += food
        self.food += food

    def changeWood(self, wood):
        self.events.change_wood += wood
        self.wood += wood

    def changeStone(self, stone):
        self.events.change_stone += stone
        self.stone += stone

    def step(self, ax, ay, active, action, angle, view_minimap=0):
        '''
        0: don't switch
        1: sword
        2: bow
        3: hammer
        4: frag
        5: wood wall
        6: stone wall
        7: spike
        8: turret
        9: heal
        '''
        self.view_minimap = view_minimap

        if self.health <= 0:
            self.dead_tick = min(self.dead_tick+1, self.max_dead_tick)
            return
        else:
            self.dead_tick = 0
        
        self.objects = self.env.grid.getNearbyObjects(self.pos)
        
        if active:
            if active == 9 and self.active != 9:
                self.last_active = self.active 
            self.active = active
        self.angle = (self.angle + angle) % (2*math.pi)

        if self.buffer:
            action = 0
            self.buffer = False

        if action:
            self.consec_held += 1
            match self.active:
                case Actives.SWORD:
                    if self.active_attack == -1:
                        self.active_attack = 1
                        self.startAttack(damage=5, frames=(15,10,7))
                case Actives.BOW:
                    if self.active_attack == -1 and self.wood >= self.costs.arrow:
                        self.changeWood(-self.costs.arrow)
                        self.active_attack = 2
                        self.startAttack(damage=4, frames=(25,18,17))
                case Actives.AXE:
                    if self.active_attack == -1:
                        self.active_attack = 3
                        self.startAttack(damage=6, frames=(25,17,14))
                case Actives.FRAG:
                    if self.active_attack == -1 and self.stone >= self.costs.frag:
                        self.changeStone(-self.costs.frag)
                        self.active_attack = 4
                        self.startAttack(damage=5, frames=(12,11,10))
                case Actives.WOODWALL:
                    if self.wood >= self.costs.woodwall:
                        valid = self.place(WoodWall(self.env, (-1, -1), self.team))
                        if valid:
                            self.changeWood(-self.costs.woodwall)
                case Actives.STONEWALL:
                    if self.stone >= self.costs.stonewall:
                        valid = self.place(StoneWall(self.env, (-1, -1), self.team))
                        if valid:
                            self.changeStone(-self.costs.stonewall)
                case Actives.SPIKE:
                    if self.wood >= self.costs.spike[0] and self.stone >= self.costs.spike[1]:
                        valid = self.place(Spike(self.env, (-1, -1), self.team, self))
                        if valid:
                            self.changeWood(-self.costs.spike[0])
                            self.changeStone(-self.costs.spike[1])
                case Actives.TURRET:
                    if self.wood >= self.costs.turret[0] and self.stone >= self.costs.turret[1]:
                        valid = self.place(Turret(self.env, (-1, -1), self.angle, self.team, self))
                        if valid:
                            self.changeWood(-self.costs.turret[0])
                            self.changeStone(-self.costs.turret[1])
                case Actives.SCATTERSHOT:
                    if self.wood >= self.costs.scattershot[0] and self.stone >= self.costs.scattershot[1]:
                        valid = self.place(Scattershot(self.env, (-1, -1), self.angle, self.team, self))
                        if valid:
                            self.changeWood(-self.costs.scattershot[0])
                            self.changeStone(-self.costs.scattershot[1])
                case Actives.BIGTURRET:
                    if self.wood >= self.costs.bigturret[0] and self.stone >= self.costs.bigturret[1]:
                        valid = self.place(BigTurret(self.env, (-1, -1), self.angle, self.team, self))
                        if valid:
                            self.changeWood(-self.costs.bigturret[0])
                            self.changeStone(-self.costs.bigturret[1])
                case Actives.HEAL:
                    if self.food >= self.costs.heal:
                        self.place(Heal(self.env, (-1, -1), self))
                        self.changeFood(-self.costs.heal)
                        self.active = self.last_active
                        action = 0
                        self.buffer = True                        
        else:
            self.consec_held = 0

        speed = [self.slow_speed, self.speed][self.slow_tick == 0]
        dx, dy = ax*speed, ay*speed
        self.pos = (self.pos[0]+self.knockback_dir[0]+dx, self.pos[1]+self.knockback_dir[1]+dy)
        self.updateMove()
        if self.slow_tick:
            self.slow_tick -= 1
        if self.knockback_tick:
            self.knockback_tick -= 1
        else:
            self.knockback_dir = (0,0)

        if self.attack_tick:
            self.attack_tick -= 1
        else:
            self.active_attack = -1

        if self.attack_tick \
           and self.frames[2] < self.attack_tick <= self.frames[1]:
            self.attacking = True
            self.attack()
        else:
            self.attacking = False
            self.hit_objects = set()
        

    def startAttack(self, damage, frames):
        self.damage = damage
        self.frames = frames
        self.attack_tick = frames[0]

    def attack(self):
        dx, dy = self.size*math.cos(self.angle), self.size*math.sin(self.angle)

        if self.active_attack in (1,3):
            p1 = np.add(self.pos, (dx,dy))
            p2 = np.add(self.pos, (2*dx,2*dy))
            p3 = np.add(self.pos, (3*dx,3*dy))
            for obj in self.objects + self.env.dynamic_objects:
                if isinstance(obj, Player) and obj.team == self.team:
                    continue
                if obj not in self.hit_objects and \
                   (isinstance(obj, Object) or isinstance(obj, Turret) or (type(obj) in {Player, Base} and obj.team != self.team)) and \
                   (math.dist(obj.pos, p1) <= obj.size + self.attack_size or \
                   math.dist(obj.pos, p2) <= obj.size + self.attack_size or \
                   math.dist(obj.pos, p3) <= obj.size + self.attack_size):
                    if self.active_attack == 1: # sword
                        if type(obj) in self.env.resources: 
                            obj.recieveHit(self, self.sword_resource_damage, self)
                        elif type(obj) in self.env.walls:
                            obj.recieveHit(self, self.sword_wall_damage, self)
                        else:
                            obj.recieveHit(self, self.damage, self)
                    elif self.active_attack == 3: # axe has damage bonuses against objects
                        if type(obj) in self.env.resources: 
                            obj.recieveHit(self, self.axe_resource_damage, self)
                        elif type(obj) in self.env.walls:
                            obj.recieveHit(self, self.axe_wall_damage, self)
                        else:
                            obj.recieveHit(self, self.damage, self)
                    else:
                        obj.recieveHit(self, self.damage, self)
                    self.hit_objects.add(obj)

        if self.active_attack == 2:
            if self.consec_held >= 7 and self.wood >= 4:
                obj = ChargedArrow(self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
                self.changeWood(-4)
            else:
                obj = Arrow(self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
            self.place(obj)
        if self.active_attack == 4:
            obj = Frag(self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
            self.place(obj)
        
        if self.attack_tick == self.frames[1]:
            match self.active:
                case 1:
                    self.env.addSound("lightattack", self.pos, 0.2)
                case 2:
                    self.env.addSound("bowshoot", self.pos, 0.35)
                case 3:
                    self.env.addSound("heavyattack", self.pos, 0.2)
                case 4:
                    self.env.addSound("frag", self.pos, 0.4)

    
    def recieveHit(self, obj, damage, player):
        if self.health <= 0:
            return 
        self.hit = True
        damage = min(self.health, damage)
        self.changeHealth(-damage)

        if player.team == -1: pass
        elif self.team == player.team:
            player.events.change_health_team_player -= damage
        else:
            player.events.change_health_enemy_player -= damage

        if self.health <= 0:
            self.health = 0
            if self.team != player.team and player.team != -1:
                player.events.killed_enemy_player += 1
                player.changeFood(20 + self.food//6)
                player.changeWood(20 + self.wood//6)
                player.changeStone(20 + self.stone//6)
                player.kills += 1
            self.events.died = 1
            self.env.removeDynamicObject(self)
            self.env.addSound("playerdie", self.pos, 0.8)

        if player.team != -1:
            knockback = 3
            dx, dy = self.pos[0]-obj.pos[0], self.pos[1]-obj.pos[1]
            mag = max(0.5, math.sqrt(dx*dx + dy*dy))
            dx, dy = dx * knockback / mag, dy * knockback / mag
            self.pos = (self.pos[0]+dx, self.pos[1]+dy)

            self.slow_tick = self.slow_duration
            self.knockback_dir = (dx, dy)
            self.knockback_tick = self.knockback_duration


    def place(self, obj, place=True):
        dist = self.size + 1.4*obj.size + 10
        dx, dy = dist*math.cos(self.angle), dist*math.sin(self.angle)
        obj.pos = np.add(self.pos, (dx,dy))

        if not place:
            return False

        if type(obj) in {WoodWall, StoneWall, Turret, Scattershot, BigTurret, Spike}:
            for obj2 in self.objects + self.env.dynamic_objects:
                if type(obj2) not in self.env.resources | self.env.walls | {Turret, Scattershot, BigTurret}:
                    continue
                if math.dist(obj.pos, obj2.pos) <= obj.size + obj2.size - 0.5:
                    return False


        if type(obj) in {Arrow, ChargedArrow, Frag, Spike}:
            self.env.addDynamicObject(obj)
            if isinstance(obj, Spike):
                self.env.addSound("turretplace", obj.pos, 0.6)
        elif isinstance(obj, Turret):
            self.env.addDynamicObject(obj)
            self.env.addSound("turretplace", obj.pos, 0.6)
        elif type(obj) in {WoodWall, StoneWall}:
            self.env.addObject(obj)
            if isinstance(obj, WoodWall):
                self.env.addSound("woodplace", obj.pos, 0.6)
            if isinstance(obj, StoneWall):
                self.env.addSound("stoneplace", obj.pos, 0.6)
        elif type(obj) in {Heal}:
            dist = self.size + 1.4*obj.size
            dx, dy = dist*math.cos(self.angle), dist*math.sin(self.angle)
            obj.pos = np.add(self.pos, (0.5*dx,0.5*dy))
            self.env.addDynamicObject(obj)
        else:
            print(type(obj))

        return True

    def updateMove(self):
        for obj in self.objects + self.env.dynamic_objects:
            if obj is self:
                continue
            if type(obj) not in {Player, Turret, Scattershot, BigTurret} | self.env.resources | self.env.walls:
                continue
            if (d:=math.dist(obj.pos, self.pos)) <= obj.size + self.size - 0.5:
                d = max(0.1, d)
                mag = d
                d /= obj.size
                dx, dy = self.pos[0]-obj.pos[0], self.pos[1]-obj.pos[1]
                f = min(8/mag, 8/(mag*d*d))
                dx, dy = f*dx, f*dy
                newpos = (self.pos[0]+dx, self.pos[1]+dy)
                self.pos = newpos
        
        buffer = 100
        dx, dy = 0, 0
        if self.pos[0] < buffer:
            dx += 5
        if self.pos[0] > self.env.map_size[0] - buffer - 1:
            dx -= 5
        if self.pos[1] < buffer:
            dy += 5
        if self.pos[1] > self.env.map_size[1] - buffer - 1:
            dy -= 5
        self.pos = (self.pos[0]+dx, self.pos[1]+dy)

    def resetState(self):
        self.resetEvents()
        self.hit = False

    def display(self):
        # TODO: blits in this
        if self.team == 2:
            self.env.drawOnMinimap(self.pos, self.color, 6, 255)
        else:
            self.env.drawOnMinimap(self.pos, (100, 180, 240), 6, 255)

        dx, dy = 14*math.cos(self.angle), 14*math.sin(self.angle)

        windup = -40
        strike = 140
        rest = 0
        anticipation = 2
        attack_offset = 0

        def round_to_5625(x):
            return (round(x / 5.625) * 5.625) % 360

        match self.active:
            case 1:
                if self.attack_tick:
                    if self.attack_tick <= self.frames[2]:
                        scale = (self.frames[2] - self.attack_tick) / self.frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif self.attack_tick <= self.frames[1]+anticipation:
                        scale = (self.frames[1]+anticipation - self.attack_tick) / (self.frames[1]+anticipation-self.frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (self.frames[0] - self.attack_tick) / (self.frames[0]-self.frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                #rotated_image = pygame.transform.rotate(self.env.sprites.sword, -(self.angle)/math.pi*180+attack_offset)
                _angle = round_to_5625(-(self.angle)/math.pi*180+attack_offset)
                _active = self.frames[2] < self.attack_tick < self.frames[1]+anticipation
                rotated_image = self.env.sprites[("sword", _angle, _active)]
                image_rect = rotated_image.get_rect()
                image_rect.center = self.pos
                self.env.surface.blit(rotated_image, image_rect)
                #pygame.draw.circle(self.env.surface, self.env.colors.white, self.pos, self.size/2)
            case 2:
                _angle = round_to_5625(-(self.angle)/math.pi*180+attack_offset)
                rotated_image = self.env.sprites[("bow",_angle, False)]
                image_rect = rotated_image.get_rect()
                image_rect.center = self.pos
                self.env.surface.blit(rotated_image, image_rect)
                #pygame.draw.circle(self.env.surface, self.env.colors.brown, self.pos, self.size/2)
            case 3:
                if self.attack_tick:
                    if self.attack_tick <= self.frames[2]:
                        scale = (self.frames[2] - self.attack_tick) / self.frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif self.attack_tick <= self.frames[1]+anticipation:
                        scale = (self.frames[1]+anticipation - self.attack_tick) / (self.frames[1]+anticipation-self.frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (self.frames[0] - self.attack_tick) / (self.frames[0]-self.frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                _angle = round_to_5625(-(self.angle)/math.pi*180+attack_offset)
                _active = self.frames[2] < self.attack_tick < self.frames[1]+anticipation
                rotated_image = self.env.sprites[("axe", _angle, _active)]
                image_rect = rotated_image.get_rect()
                image_rect.center = self.pos
                self.env.surface.blit(rotated_image, image_rect)
                #pygame.draw.circle(self.env.surface, self.env.colors.lightgrey, self.pos, self.size/2)
            case 5:
                obj = WoodWall(self.env, (-1, -1), self.team)
                self.place(obj, place=False)
                obj.display(self.env.surface, obj.getInfo())
            case 6:
                obj = StoneWall(self.env, (-1, -1), self.team)
                self.place(obj, place=False)
                obj.display(self.env.surface, obj.getInfo())
            case 7:
                obj = Spike(self.env, (-1, -1), self.team, self)
                self.place(obj, place=False)
                obj.display(self.env.surface, obj.getInfo())
            case 8:
                obj = Turret(self.env, (-1, -1), self.angle, self.team, self)
                self.place(obj, place=False)
                obj.display(self.env.surface, obj.getInfo())
            case 10:
                obj = Scattershot(self.env, (-1, -1), self.angle, self.team, self)
                self.place(obj, place=False)
                obj.display(self.env.surface, obj.getInfo())
            case 11:
                obj = BigTurret(self.env, (-1, -1), self.angle, self.team, self)
                self.place(obj, place=False)
                obj.display(self.env.surface, obj.getInfo())
            case Actives.HEAL:
                dist = self.size + 5
                offset = 60 / 180 * math.pi
                dx, dy = dist*math.cos(self.angle+offset), dist*math.sin(self.angle+offset)
                pygame.draw.circle(self.env.surface, (220, 120, 80), np.add(self.pos, (dx,dy)), self.size*0.6)
            case Actives.FRAG:
                dist = self.size + 5
                offset = 60 / 180 * math.pi
                dx, dy = dist*math.cos(self.angle+offset), dist*math.sin(self.angle+offset)
                pygame.draw.circle(self.env.surface, WHITE, np.add(self.pos, (dx,dy)), self.size*0.6)
        
        offset = 60 / 180 * math.pi
        attack_offset = -attack_offset / 180 * math.pi
        dx2, dy2 = 14*math.cos(self.angle+offset+attack_offset), 14*math.sin(self.angle+offset+attack_offset)
        dx3, dy3 = 14*math.cos(self.angle-offset+attack_offset), 14*math.sin(self.angle-offset+attack_offset)

        border_color = darken(self.color)

        pygame.draw.circle(self.env.surface, [border_color, WHITE][self.hit], np.add(self.pos, (dx2,dy2)), self.size/2)
        pygame.draw.circle(self.env.surface, [border_color, WHITE][self.hit], np.add(self.pos, (dx3,dy3)), self.size/2)
        pygame.draw.circle(self.env.surface, [self.color, WHITE][self.hit], np.add(self.pos, (dx2,dy2)), self.size/2-1.5)
        pygame.draw.circle(self.env.surface, [self.color, WHITE][self.hit], np.add(self.pos, (dx3,dy3)), self.size/2-1.5)

        pygame.draw.circle(self.env.surface, [border_color, WHITE][self.hit], self.pos, self.size)
        pygame.draw.circle(self.env.surface, [self.color, WHITE][self.hit], self.pos, self.size-1.5)
                    
    def getInfo(self):
        return AttrDict({
            "id_": self.id_,
            "name": self.name,
            "type": "player",
            "position": self.pos,
            "size": self.size,
            "angle": self.angle,
            "team": self.team,
            "health": self.health,
            "food": self.food,
            "wood": self.wood,
            "stone": self.stone,
            "active": self.active,
            "attacking": bool(self.attack_tick),
            "attack_state": [-1, [0, 1][self.frames[2] < self.attack_tick <= self.frames[1]]][bool(self.attack_tick)],
            "events": self.events,
        })

    def __str__(self):
        return (f'''
health: {self.health}
food: {self.food}
wood: {self.wood}
stone: {self.stone}
''')
        


class GridCell():
    def __init__(self, idx, gridsize):
        self.idx = idx
        self.x, self.y = idx[0]*gridsize, idx[1]*gridsize
        self.gridsize = gridsize
        self.objects = []

    def withinBounds(self, pos):
        x2, y2 = pos
        return self.x <= x2 < self.x+self.gridsize and self.y <= y2 < self.y+self.gridsize

    def addObject(self, obj):
        self.objects.append(obj)

    def removeObject(self, obj):
        # start search from back
        for i in range(len(self.objects)-1, -1, -1):
            if self.objects[i] == obj:
                del self.objects[i]
                return
        raise ValueError(f"{obj} not in gridcell {self.idx}")
        

class Grid():
    def __init__(self, env, gridsize):
        self.env = env
        self.gridsize = gridsize

        self.grid = {
            (x,y) : GridCell((x,y), gridsize) for
             x in range(math.ceil(self.env.map_size[0]/gridsize)) for
             y in range(math.ceil(self.env.map_size[1]/gridsize))
        }

        self.DUMMYCELL = GridCell((-1, -1), gridsize)

    def withinBounds(self, pos):
        x, y = pos
        return (0 <= x <= self.env.map_size[0]-1) and (0 <= y <= self.env.map_size[1]-1)
        
    def getNeighboringCells(self, idx, size=1):
        x,y = idx
        neighboring_cells = []
        for dx in range(-size, size+1):
            for dy in range(-size, size+1):
                cell_idx = (x+dx, y+dy)
                if cell_idx in self.grid:
                    cell = self.grid[cell_idx]
                else:
                    cell = self.DUMMYCELL
                neighboring_cells.append(cell)

        return tuple(neighboring_cells)

    def getNearbyObjects(self, pos, size=1):
        idx = pos[0]//self.gridsize, pos[1]//self.gridsize
        return sum((cell.objects for cell in self.getNeighboringCells(idx, size)), start=[])

    def addObject(self, obj):
        pos = obj.pos
        x,y = pos[0]//self.gridsize, pos[1]//self.gridsize
        self.grid[(x,y)].addObject(obj)

    def removeObject(self, obj):
        pos = obj.pos
        x,y = pos[0]//self.gridsize, pos[1]//self.gridsize
        self.grid[(x,y)].removeObject(obj)


class Camera():
    def __init__(self, env):
        self.env = env
        self.pos = env.center
        self.scale = env.map_size[0]/2
        
        x,y = self.pos
        s = self.scale
        self.frame_rect = pygame.Rect(x-s, y-s, 2*s, 2*s)

    def getFrame(self, surface):
        center = self.frame_rect.center
        self.frame_rect.width = 2*self.scale
        self.frame_rect.height = 2*self.scale
        self.frame_rect.center = center

        frame = pygame.Surface(self.frame_rect.size)
        frame.fill((self.env.colors.grey))
        
        world_rect = surface.get_rect()
        overlap = self.frame_rect.clip(world_rect)

        if overlap.width > 0 and overlap.height > 0:
            x = overlap.x - self.frame_rect.x
            y = overlap.y - self.frame_rect.y
            frame.blit(surface, (x,y), overlap)
            
        return frame
        

class RaiderEnvironment():
    def __init__(self):
        self.colors = AttrDict({
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "orange": (170, 120, 55),
            "brown": (120, 80, 60),
            "lightbrown": (210, 170, 130),
            "green": (100, 170, 70),
            "darkgreen": (92, 135, 52),
            "grey": (70, 70, 70),
            "lightgrey": (130, 130, 130),
            "lightergrey": (180, 180, 180),
            "mutedred": (180, 120, 90),
            "mutedlightred": (190, 145, 100),
            "team2": (240, 140, 80),
            "team1": (140, 190, 240),
        })

        self.resources = {Bush, Tree, Stone}
        self.walls = {WoodWall, StoneWall, Spike}
        
        self.map_size = [4000, 4000]
        self.center = [self.map_size[0]//2, self.map_size[1]//2]
        self.screen_size = 800, 800
        self.screen_center = [self.screen_size[0]//2, self.screen_size[1]//2]
        self.sounds = []

        self.max_storm_size = math.sqrt(2) * (self.map_size[0] // 2)
        self.min_storm_size = math.sqrt(2) * (self.map_size[0] // 2) / 2 

        self.camera = Camera(self)
        self.dummy_player = DUMMYPLAYER()

        self.surface = pygame.Surface(self.map_size, pygame.SRCALPHA)
        self.scaled_surface = pygame.Surface((860,860), pygame.SRCALPHA)
        self.minimap_surface = pygame.Surface((300,300), pygame.SRCALPHA)
        self.defender_mask_surface = pygame.Surface((300,300), pygame.SRCALPHA)
        self.raider_mask_surface = pygame.Surface((300,300), pygame.SRCALPHA)
        self.storm_surface = pygame.Surface(self.map_size)
        self.background_surface = pygame.Surface(self.map_size, pygame.SRCALPHA)
        
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.t = 0

        self.metadata = AttrDict({
            "colors": self.colors,
            "map_size": self.map_size,
            "center": self.center,
            "screen_size": self.screen_size,
            "screen_center": self.screen_center,
            "time": self.t,
            "storm_size": self.max_storm_size,
        })
        
        initialized = False
        while not initialized:
            try:
                self.initializeSprites()
                initialized = True
            except:
                time.sleep(random.randint(1,5))

        self.players = {}
        self.reset()

    def getPlayers(self):
        return tuple(self.players.values())

    def addPlayer(self, id_, team, name=None):
        team = 1 if team=="defender" else 2
        player = Player(self, (-1,-1), team, id_)
        if name is not None:
            player.name = name
        self.initializePlayer(player, team)
        self.players[id_] = player
        self.dynamic_objects.append(player)

    def removePlayer(self, id_):
        player = self.players[id_]
        if player in self.dynamic_objects:
            self.dynamic_objects.remove(player)
        del self.players[id_]

    def prerender_rotations(self, names=("sword","bow","axe"), step=1, cutoff=250):
        def _binarize_alpha(surf, cutoff):
            s = surf.convert_alpha()
            a = pygame.surfarray.pixels_alpha(s)
            a[:] = (a >= cutoff) * 255
            del a
            return s
        
        # step=1 → 360 frames; use step=2/3 to save memory
        for name in names:
            base = self.sprites[name]  # assumes already loaded
            for deg in range(0, 64):
                deg *= 5.625
                rot = pygame.transform.rotate(base, deg)
                rot = _binarize_alpha(rot, cutoff=cutoff)
                # store: ('sword','rot',deg) etc.
                opaque = rot.convert()
                opaque.set_colorkey((0, 0, 0))
                self.sprites[(name, deg, False)] = opaque
                opaque = rot.convert()
                opaque.set_colorkey((0, 0, 0))
                self.fill_visible_pixels(opaque)
                self.sprites[(name, deg, True)] = opaque

    def initializeSprites(self):
        self.font = pygame.font.Font(None, 30) 
        self.font2 = pygame.font.Font(None, 40) 
        self.font3 = pygame.font.SysFont("Consolas", 10) 
        self.font4 = pygame.font.SysFont("Consolas", 7)
        self.sprites = AttrDict({
            "raider": loadAsset("raider.png"),
            "defender": loadAsset("defender.png"),
            "sword": loadAsset("sword.png").convert_alpha(),
            "bow": loadAsset("bow.png").convert_alpha(),
            "axe": loadAsset("axe.png").convert_alpha(),
            "arrow": loadAsset("arrow.png").convert_alpha(),
            "food_icon": loadAsset("food.png").convert_alpha(),
            "wood_icon": loadAsset("wood.png").convert_alpha(),
            "stone_icon": loadAsset("stone.png").convert_alpha(),
        })
        self.sprites["food_icon_scaled"] = pygame.transform.scale(self.sprites.food_icon, (9,9))
        self.sprites["wood_icon_scaled"] = pygame.transform.scale(self.sprites.wood_icon, (9,9))
        self.sprites["stone_icon_scaled"] = pygame.transform.scale(self.sprites.stone_icon, (9,9))
        
        self.prerender_rotations()

        image_size = (100, 100)
        center = (50, 50)

        # draw bush
        bush_instance = Bush(self, (0,0))
        self.bush_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        points = polygon(center, bush_instance.size-5, 6)
        for i in range(6):
            pygame.draw.circle(self.bush_surface, darken(self.colors.darkgreen, 0.89), points[i], 18)
        points = polygon(center, bush_instance.size-10, 6)
        for i in range(6):
            pygame.draw.circle(self.bush_surface, darken(self.colors.darkgreen, 1.02), points[i], 16)
        points = polygon(center, bush_instance.size*0.4+1, 3)
        for i in range(3):
            pygame.draw.circle(self.bush_surface, darken(self.colors.mutedred, 0.9), points[i], 9*(bush_instance.size/20)**0.8)

        self.generateHealthLookups('bush', self.bush_surface, bush_instance)

        # draw tree
        tree_instance = Tree(self, (0,0))
        self.tree_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        pygame.draw.polygon(self.tree_surface, self.colors.darkgreen, (p1:=polygon(center, tree_instance.size*.75, 3)), width=13)
        pygame.draw.polygon(self.tree_surface, self.colors.darkgreen, (p2:=polygon(center, tree_instance.size*.75, 3, flip=-1)), width=13)
        for p in p1+p2:
            pygame.draw.circle(self.tree_surface, self.colors.darkgreen, p, 7)
        pygame.draw.polygon(self.tree_surface, darken(self.colors.darkgreen, scale=1.1), polygon(center, tree_instance.size*.75-2, 3))
        pygame.draw.polygon(self.tree_surface, darken(self.colors.darkgreen, scale=1.1), polygon(center, tree_instance.size*.75-2, 3, flip=-1))

        self.generateHealthLookups('tree', self.tree_surface, tree_instance)

        # draw stone
        stone_instance = Stone(self, (0,0))
        self.stone_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        pygame.draw.polygon(self.stone_surface, darken(self.colors.lightgrey, scale=0.9), polygon(center, stone_instance.size, 8))
        pygame.draw.polygon(self.stone_surface, self.colors.lightgrey, polygon(center, stone_instance.size-8, 7))
        pygame.draw.polygon(self.stone_surface, darken(self.colors.lightgrey, scale=1.15), polygon(center, stone_instance.size/2, 6))

        self.generateHealthLookups('stone', self.stone_surface, stone_instance)

        spike_instance = Spike(self, (0,0), 1, self.dummy_player)
        self.spike_surface = pygame.Surface(image_size, pygame.SRCALPHA)
        for team,color in zip(["spike1", "spike2"], [self.colors.team1, self.colors.team2]):
            size = spike_instance.size
            pygame.draw.polygon(self.spike_surface, darken(self.colors.lightgrey, scale=0.9), polygon(center, size-2, 3, 1))
            pygame.draw.polygon(self.spike_surface, darken(self.colors.lightgrey, scale=0.9), polygon(center, size-2, 3, -1))
            pygame.draw.polygon(self.spike_surface, self.colors.lightgrey, polygon(center, size-5, 3, 1))
            pygame.draw.polygon(self.spike_surface, self.colors.lightgrey, polygon(center, size-5, 3, -1))
            pygame.draw.circle(self.spike_surface, darken(self.colors.brown, scale=0.94), center, size+1.5)
            pygame.draw.circle(self.spike_surface, darken(self.colors.brown, scale=1.1), center, size-1.5)
            pygame.draw.circle(self.spike_surface, color, center, size-9)

            opaque = self.spike_surface.convert()
            opaque.set_colorkey((0, 0, 0))
            self.sprites[(team, False)] = opaque
            opaque = self.spike_surface.convert()
            opaque.set_colorkey((0, 0, 0))
            self.fill_visible_pixels(opaque)
            self.sprites[(team, True)] = opaque
        
        for name, surf in self.sprites.items():
            if isinstance(name, tuple):
                pygame.image.save(surf, os.path.join(cache_folder, f"{'_'.join(str(s) for s in name)}.png"))

    
    def generateHealthLookups(self, type, surface, instance):
        image_size = (100, 100)
        center = (50, 50)
        s = instance.health

        self.sprites[type] = {}
        for i in range(instance.health):
            scale = (s - s*0.4 * (1-i/s)) / s
            scaled_image = pygame.transform.scale(surface, (int(image_size[0]*scale), int(image_size[1]*scale)))
            scaled_image_rect = scaled_image.get_rect(center=center)
            canvas = pygame.Surface(image_size, pygame.SRCALPHA)
            canvas.blit(scaled_image, scaled_image_rect)
            opaque = canvas.convert()

            opaque = canvas.convert()
            opaque.set_colorkey((0, 0, 0))
            self.sprites[(type, i+1, False)] = opaque
            opaque = canvas.convert()
            opaque.set_colorkey((0, 0, 0))
            self.fill_visible_pixels(opaque)
            self.sprites[(type, i+1, True)] = opaque

    def fill_visible_pixels(self, surface, fill_color=(255, 255, 255)):
        colorkey = surface.get_colorkey()
        if colorkey is None:
            raise ValueError("Surface must have a colorkey set")

        surface.lock()
        width, height = surface.get_size()

        for x in range(width):
            for y in range(height):
                if surface.get_at((x, y))[:3] != colorkey[:3]:
                    surface.set_at((x, y), fill_color)
        surface.unlock()
    
    def drawSprite(self, sprite, pos, health, hit):
        if health == -1:
            sprite_surface = self.sprites[(sprite, hit)]
        else:
            sprite_surface = self.sprites[(sprite, health, hit)]
        rect = sprite_surface.get_rect(center=pos)
        self.surface.blit(sprite_surface, rect)

    def reset(self):
        self.storm_surface.fill((0,0,0,0))
        self.grid = Grid(self, 200)
        self.base = Base(self, (self.map_size[0]/2, self.map_size[1]/2), 1)
        self.storm_size = self.max_storm_size
        self.t = 0

        self.metadata.time = self.t
        self.metadata.storm_size = self.storm_size

        self.objects = []
        self.addDeposits()
        self.effects = []
        self.sounds = []
        
        for id_, player in self.players.items():
            team = player.team
            name = player.name
            player = Player(self, (-1,-1), team, id_)
            player.name = name
            self.initializePlayer(player, team)
            self.players[id_] = player
        
        self.dynamic_objects = [player for player in self.players.values()]
        self.addDynamicObject(self.base)

        observations = {}
        info = {"team_observations": {"defender": {}, "raider": {}} }
        for id_, player in self.players.items():
            team = "defender" if player.team==1 else "raider"
            obs = self.getInputs(id_)
            info["team_observations"][team][id_] = obs
            observations[id_] = obs
        info = AttrDict(info)
        return observations, info
    
    def initializePlayer(self, player, team):
        player.food, player.wood, player.stone = (50, 120, 120) if team==1 else (80, 60, 60)
        self.setSpawnLoc(self.map_size[0] * [0.12, 0.4][team-1], player)
    
    def getTeamCounts(self):
        teams = [0,0]
        for id_, player in self.players.items():
            if player.health <= 0: continue
            team = player.team
            teams[team-1] += 1
        return teams
    
    def addSound(self, sound, pos, scale):
        self.sounds.append((SoundUtils.encodeSoundID(sound), *pos, scale))

    def addDeposits(self, bushes=(160,20), trees=(200,20), stones=(80,12)):        
        for _ in range(stones[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Stone(self, (x,y)))

        for _ in range(bushes[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Bush(self, (x,y)))
            
        for _ in range(trees[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Tree(self, (x,y)))

        for _ in range(stones[1]):
            x, y = self.getSpawnLoc2(400)
            self.addObject(Stone(self, (x,y)))

        for _ in range(bushes[1]):
            x, y = self.getSpawnLoc2(400)
            self.addObject(Bush(self, (x,y)))
            
        for _ in range(trees[1]):
            x, y = self.getSpawnLoc2(400)
            self.addObject(Tree(self, (x,y)))

    def setSpawnLoc(self, r, obj=None):
        check = False
        count = 15
        while not check and count:
            theta = random.random()*2*math.pi
            if obj is None:
                return r*math.cos(theta) + self.map_size[0]/2, r*math.sin(theta) + self.map_size[1]/2
            obj.pos = (r*math.cos(theta) + self.map_size[0]/2, r*math.sin(theta) + self.map_size[1]/2)
            check = True
            for obj2 in self.objects:
                if math.dist(obj.pos, obj2.pos) <= obj.size + obj2.size - 0.5:
                    check = False
            count -= 1
        
    def getSpawnLoc2(self, r):
        theta = random.random()*2*math.pi
        r = r * math.sqrt(random.random())
        return r * math.cos(theta) + self.center[0], r * math.sin(theta) + self.center[1]

    def getSpawnLoc(self):
        x, y = self.map_size[0]/2, self.map_size[1]/2
        while (x > 0.25*self.map_size[0] and x < 0.75*self.map_size[0] and \
               y > 0.25*self.map_size[1] and y < 0.75*self.map_size[1]):
            x, y = random.randint(50, self.map_size[0]-50), random.randint(50, self.map_size[1]-50)
        return x, y

    def addObject(self, obj):
        self.objects.append(obj)
        self.grid.addObject(obj)

    def removeObject(self, obj):
        if obj not in self.objects:
            return
        self.objects.remove(obj)
        self.grid.removeObject(obj)
    
    def addDynamicObject(self, obj):
        self.dynamic_objects.append(obj)
    
    def removeDynamicObject(self, obj):
        if obj not in self.dynamic_objects:
            return
        self.dynamic_objects.remove(obj)
    
    def addEffect(self, obj):
        self.effects.append(obj)
    
    def removeEffect(self, obj):
        self.effects.remove(obj)
    
    def drawOnMinimap(self, pos, color, r=4, opacity=100):
        scale = self.minimap_surface.get_width() / self.surface.get_width()
        minimap_pos = self.scale(pos, scale)
        pygame.draw.circle(self.minimap_surface, tuple(color)+(opacity,), minimap_pos, r)

    def step(self, actions, display=False, get_inputs=False):
        self.t += 1
        self.storm_size = max(0, min(1, (self.t - 180*20) / (300*20 - 180*20))) * (self.min_storm_size - self.max_storm_size) + self.max_storm_size
        self.metadata.time = self.t
        self.metadata.storm_size = self.storm_size
        self.sounds = []

        for obj in self.objects + self.dynamic_objects:
            obj.resetState()

        for n, action in actions.items():
            # check to see if actions are valid
            action = tuple(int(_) for _ in action)
            ax, ay, active, action_, angle = action[:5]
            assert (0 <= ax <= 2) and (int(ax) == ax), f"Invalid Action[0]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= ay <= 2) and (int(ay) == ay), f"Invalid Action[1]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= active) and (int(active) == active), f"Invalid Action[2]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= action_ <= 1) and (int(action_) == action_), f"Invalid Action[3]: {ax}, {ay}, {active}, {action_}, {angle}"
            assert (0 <= angle <= 4) and (int(angle) == angle), f"Invalid Action[4]: {ax}, {ay}, {active}, {action_}, {angle}"
            dx = action[0] - 1
            dy = action[1] - 1
            active = action[2]
            attack = action[3]
            angle = 0.0981747704247 * (action[4]-2) * (abs(action[4]-2))
            action = (dx, dy, active, action_, angle) + tuple(action[5:])
            self.players[n].step(*action)

        for obj in self.dynamic_objects + self.objects:
            if isinstance(obj, Player):
                continue
            obj.step()
        
        for obj in self.effects:
            obj.step()

        if self.t % 20 == 0:
            for player in self.getPlayers():
                if math.dist(player.pos, self.center) > self.storm_size:
                    player.recieveHit(self.dummy_player, 5, self.dummy_player)


        pygame.event.pump()
        self.surface.fill(self.colors.green)
        self.minimap_surface.fill((35, 35, 35, 50))

        for obj in self.effects:
            obj.display(self.surface, obj.getInfo())
        
        self.base.display(self.surface, self.base.getInfo())

        for obj in self.objects:
            if isinstance(obj, Tree):
                continue
            obj.display(self.surface, obj.getInfo())
        for obj in self.dynamic_objects:
            if isinstance(obj, Player) or isinstance(obj, Base):
                continue
            obj.display(self.surface, obj.getInfo()) 
        for obj in self.getPlayers():
            if obj.health <= 0: 
                continue
            obj.display()
        for obj in self.objects:
            if not isinstance(obj, Tree):
                continue
            obj.display(self.surface, obj.getInfo())
        
        if self.storm_size != self.max_storm_size:
            if self.storm_size != self.min_storm_size:
                pygame.draw.circle(self.storm_surface, (100, 0, 30), self.center, int(self.storm_size), width=3)  # transparent center
            self.surface.blit(self.storm_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        for player in self.getPlayers():
            if player.health <= 0:
                continue
            bar_width = 40
            health_ratio = player.health / 20
            pygame.draw.rect(self.surface, (40,40,40), (player.pos[0]-bar_width/2, player.pos[1]+20, bar_width, 6))
            pygame.draw.rect(self.surface, (140,210,100), (player.pos[0]-(bar_width-3)/2, player.pos[1]+21, (bar_width-3)*min(1, health_ratio), 3))
            if health_ratio > 1:
                absorption_ratio = health_ratio - 1
                pygame.draw.rect(self.surface, (255,220,90), (player.pos[0]+(bar_width-3)*(0.5-absorption_ratio), player.pos[1]+21, (bar_width-3)*absorption_ratio, 3))

        # --- Build masks directly ---

        self.raider_mask_surface.fill((0, 0, 0, 50))
        self.defender_mask_surface.fill((0, 0, 0, 50))
        
        scale = self.minimap_surface.get_width() / self.surface.get_width()

        for player in self.getPlayers():
            if player.dead_tick == player.max_dead_tick:
                continue

            # Compute the minimap rectangle
            x = int(player.pos[0] - 500)
            y = int(player.pos[1] - 500)

            x = int(self.clamp(x, 0, self.map_size[0] - 1000) * scale)
            y = int(self.clamp(y, 0, self.map_size[1] - 1000) * scale)

            w = int(1000 * scale)
            h = int(1000 * scale)

            # Vectorized fill: no loops at all
            if player.team == 1:
                pygame.draw.rect(self.defender_mask_surface, (255,255,255,255), pygame.Rect(x,y,w,h))
            elif player.team == 2:
                pygame.draw.rect(self.raider_mask_surface, (255,255,255,255), pygame.Rect(x,y,w,h))

        # Create masked minimaps
        self.defender_minimap = self.minimap_surface.copy()
        self.defender_minimap.blit(self.defender_mask_surface, (0,0), special_flags=pygame.BLEND_RGBA_MIN)

        self.raider_minimap = self.minimap_surface.copy()
        self.raider_minimap.blit(self.raider_mask_surface, (0,0), special_flags=pygame.BLEND_RGBA_MIN)
        
        if not get_inputs:
            return

        done, winning_team = self.gameIsDone()

        observations = {}
        info = {"team_observations": {"defender": {}, "raider": {}} }
        for id_, player in self.players.items():
            team = "defender" if player.team==1 else "raider"
            obs = self.getInputs(id_)
            info["team_observations"][team][id_] = obs
            observations[id_] = obs
        info = AttrDict(info)

        term = False

        if display:
            frame = self.camera.getFrame(self.surface)
            pygame.transform.scale(frame, self.screen_size, self.screen)
            pygame.display.flip()
            self.clock.tick(20)
        else:
            pygame.event.pump()

        return observations, winning_team, done, term, info

    def gameIsDone(self):
        if self.base.health <= 0:
            return True, "raider"
        teams = [0,0]
        for player in self.getPlayers():
            if player.health <= 0: continue
            teams[player.team-1] += 1
        if teams[0] == 0:
            return True, "raider"
        if teams[1] == 0:
            return True, "defender"
        if self.t >= 10*60*20:
            return True, "defender"
        return False, None

        #((self.base.health <= 0) or (self.t > 10*60*20) or \
        #        (0 == sum([max(0, p.health) for p in self.players[:self.teams[0]]])) or (0 == sum([max(0, p.health) for p in self.players[self.teams[0]:]])))

    
    def clamp(self, x, min_, max_):
        return min(max_, max(min_, x))
    
    def scale(self, x, s, round_=False):
        if round_:
            return [round(v * s) for v in x]
        else:
            return [v * s for v in x]

    def getInputs(self, id_):
        player = self.players[id_]

        info = AttrDict({
            "metadata": self.metadata,
            "self": player.getInfo(),
        })

        for type_ in ["player", "bush", "tree", "stone", "turret", "woodwall", "stonewall", "spike", "base", "arrow", "chargedarrow", "frag", "heal", "explosion", "", "", "", "", ]:
            info[type_] = []

        objects = self.grid.getNearbyObjects(player.pos, size=2) + self.dynamic_objects + self.effects
        for obj in objects:
            dx, dy = obj.pos[0]-player.pos[0], obj.pos[1]-player.pos[1]
            if abs(dx) > 510 or abs(dy) > 510:
                continue

            obj_info = obj.getInfo()
            #if obj_info["type"] == "player" and obj_info["team"] != player.team: # hide resource information of opponents
            #    del obj_info["food"]
            #    del obj_info["wood"]
            #    del obj_info["stone"]
            #obj_info["relative_position"] = (dx, dy)

            #info[obj_info["type"]].append(obj_info)

        return info

