import math
import numpy as np
from enum import IntEnum

import pygame

from raiders.gameobjects._gameobject_info import MinimapInfo, PlayerInfo, CONFIG
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

PLACEABLE_ACTIVE_MAP = {
    Actives.WOODWALL:   "WoodWall",
    Actives.STONEWALL:  "StoneWall",
    Actives.SPIKE:      "Spike",
    Actives.TURRET:     "Turret",
    Actives.SCATTERSHOT:"Scattershot",
    Actives.BIGTURRET:  "BigTurret",
}

def round_to_5625(x):
    return (round(x / 5.625) * 5.625) % 360

class Player(Object):
    display_layer = DisplayLayers.PLAYER
    minimap_info = MinimapInfo(color=None, r=6)

    sprite_cache = {}

    max_health = 50
    max_size = 15
    speed = 4
    slow_speed = 2
    slow_duration = 15
    knockback_duration = 3

    attack_size = 20

    sword_damage = 5
    sword_resource_damage = 2
    sword_wall_damage = 3
    axe_damage = 6
    axe_resource_damage = 6
    axe_wall_damage = 12

    max_dead_tick = 20

    def __init__(self, env, pos, team, id_):
        super().__init__(env, pos, self.max_health, self.max_size, team=team)
        self.id_ = id_
        self.name = f"Player {id_}"
        self.env = env
        self.pos = list(pos)
        self.team = team
        self.team_color = CONFIG["team_colors"]["defenders" if team==1 else "raiders"]

        self.dead_tick = 0

        self.attack_tick = 0
        self.attack_frames = None
        self.attacking = False
        self.frames = [0,0,0]
        
        self.slow_tick = 0
        self.knockback_dir = (0,0)
        self.knockback_tick = 0

        self.active = 1
        self.active_attack = -1
        self.last_active = 1

        self.view_minimap = 0    

        self.food = 0
        self.wood = 0
        self.stone = 0

        self.hit = False
        self.buffer = False

        self.hit_objects = set()
        self.kills = 0

    def changeFood(self, food):
        self.food += food

    def changeWood(self, wood):
        self.wood += wood

    def changeStone(self, stone):
        self.stone += stone

    def haveEnoughResources(self, required_resouces):
        if self.wood < required_resouces[0]: return False
        if self.stone < required_resouces[1]: return False
        if self.food < required_resouces[2]: return False
        return True
    
    @staticmethod
    def haveEnoughResources_(info, required_resouces):
        if info.wood < required_resouces[0]: return False
        if info.stone < required_resouces[1]: return False
        if info.food < required_resouces[2]: return False
        return True

    def useResources(self, required_resources):
        self.wood -= required_resources[0]
        self.stone -= required_resources[1]
        self.food -= required_resources[2]

    def step(self, ax, ay, active, action, angle, view_minimap=0):
        self.view_minimap = view_minimap

        if self.health <= 0:
            self.dead_tick = min(self.dead_tick+1, self.max_dead_tick)
            return
        else:
            self.dead_tick = 0
        
        self.objects = self.env.grid.getNearbyObjects(self.pos)
        
        if active:
            if active == Actives.HEAL and self.active != Actives.HEAL:
                self.last_active = self.active 
            self.active = active
        self.angle = round_to_5625((self.angle + angle)/math.pi*180)/180*math.pi

        if self.buffer:
            action = 0
            self.buffer = False

        if action:
            match self.active:
                case Actives.SWORD:
                    if self.active_attack == -1:
                        self.active_attack = Actives.SWORD
                        self.startAttack(damage=5, frames=CONFIG["player"]["frames"]["sword"])
                case Actives.BOW:
                    cost = CONFIG["costs"]["Arrow"]
                    if self.active_attack == -1 and self.haveEnoughResources(cost):
                        self.useResources(cost)
                        self.active_attack = Actives.BOW
                        self.startAttack(damage=4, frames=CONFIG["player"]["frames"]["bow"])
                case Actives.AXE:
                    if self.active_attack == -1:
                        self.active_attack = Actives.AXE
                        self.startAttack(damage=6, frames=CONFIG["player"]["frames"]["axe"])
                case Actives.FRAG:
                    cost = CONFIG["costs"]["Frag"]
                    if self.active_attack == -1 and self.haveEnoughResources(cost):
                        self.useResources(cost)
                        self.active_attack = Actives.FRAG
                        self.startAttack(damage=8, frames=CONFIG["player"]["frames"]["frag"])
                case active if active in PLACEABLE_ACTIVE_MAP:
                    key = PLACEABLE_ACTIVE_MAP[active]
                    cost = CONFIG["costs"][key]
                    if self.haveEnoughResources(cost):
                        obj = GAMEOBJECTS[key](self.env, self.pos, self.angle, self)
                        if self.place(obj):
                            self.useResources(cost)
                case Actives.HEAL:
                    cost = CONFIG["costs"]["Heal"]
                    if self.haveEnoughResources(cost):
                        self.place(GAMEOBJECTS["Heal"](self.env, (-1, -1), self))
                        self.useResources(cost)
                        self.active = self.last_active
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

        if self.attack_tick and (self.frames[2] < self.attack_tick <= self.frames[1]):
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
                if isinstance(obj, (Player, GAMEOBJECTS["Base"])) and obj.team == self.team:
                    continue
                if obj not in self.hit_objects and \
                   isinstance(obj, Object) and \
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

        if self.active_attack == Actives.BOW:
            obj = GAMEOBJECTS["Arrow"](self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
            self.place(obj)
        if self.active_attack == Actives.FRAG:
            obj = GAMEOBJECTS["Frag"](self.env, np.add(self.pos, (dx,dy)), self.angle, self.team, self)
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

    def recieveHitObject(self, obj, damage):
        damage = min(self.health, damage)
        self.health -= damage

    def recieveHitUpdate(self, obj, damage):
        super().recieveHitUpdate(obj, damage)

        knockback = 3
        dx, dy = self.pos[0]-obj.pos[0], self.pos[1]-obj.pos[1]
        mag = max(0.5, math.sqrt(dx*dx + dy*dy))
        dx, dy = dx * knockback / mag, dy * knockback / mag
        self.pos = (self.pos[0]+dx, self.pos[1]+dy)

        self.slow_tick = self.slow_duration
        self.knockback_dir = (dx, dy)
        self.knockback_tick = self.knockback_duration
        
        self.env.addSound("playerhurt", self.pos, 0.2)
    
    def onDeath(self, obj, damage):
        if isinstance(obj, Player):
            player = obj
            player.changeFood(20 + self.food//6)
            player.changeWood(20 + self.wood//6)
            player.changeStone(20 + self.stone//6)
            player.kills += 1
        self.env.removeDynamicObject(self)
        self.env.addSound("playerdie", self.pos, 0.8)

    def place(self, obj, place=True):
        dist = self.size + 1.4*obj.size + 10
        dx, dy = dist*math.cos(self.angle), dist*math.sin(self.angle)
        obj.pos = np.add(self.pos, (dx,dy))

        if not place:
            return False

        if isinstance(obj, Object):
            for obj2 in self.objects + self.env.dynamic_objects:
                if isinstance(obj2, Object) and not isinstance(obj2, (GAMEOBJECTS["Base"], GAMEOBJECTS["Player"])):
                    if math.dist(obj.pos, obj2.pos) <= obj.size + obj2.size - 0.5:
                        return False
        
        if isinstance(obj, GAMEOBJECTS["Projectile"]):
            self.env.addDynamicObject(obj)
        elif isinstance(obj, GAMEOBJECTS["Effect"]):
            dist = self.size + 1.4*obj.size
            dx, dy = dist*math.cos(self.angle), dist*math.sin(self.angle)
            obj.pos = np.add(self.pos, (0.5*dx,0.5*dy))
            self.env.addDynamicObject(obj)
        else:
            self.env.addObject(obj)
            
        for cls in CONFIG["sounds"]:
            if isinstance(obj, GAMEOBJECTS[cls]):
                self.env.addSound(CONFIG["sounds"][cls], obj.pos, 0.4)


        return True

    def updateMove(self):
        for obj in self.objects + self.env.dynamic_objects:
            if obj is self:
                continue
            if isinstance(obj, Object) and not isinstance(obj, GAMEOBJECTS["Base"]):
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

    @classmethod
    def displayOnMinimap(cls, surface, info, scale):
        if cls.minimap_info is not None:
            color, r = CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"] + [200,], cls.minimap_info.r
            pos = np.multiply(info.position, scale)
            pygame.draw.circle(surface, color, pos, r)

    @staticmethod
    def render(info):
        relevantinfo = (info.team, info.size, info.hit, info.angle, info.active, info.attack_tick)

        dx, dy = 14*math.cos(info.angle), 14*math.sin(info.angle)

        windup = -40
        strike = 140
        rest = 0
        anticipation = 2
        attack_offset = 0

        if info.active == Actives.BIGTURRET:
            composite_image_size = (400, 400)
            composite_center = (200, 200)
        else:
            composite_image_size = (200, 200)
            composite_center = (100, 100)
        composite_surface = pygame.Surface(composite_image_size)
        composite_surface.set_colorkey((0,0,0))

        match info.active:
            case Actives.SWORD:
                if info.attack_tick:
                    if info.attack_tick <= info.frames[2]:
                        scale = (info.frames[2] - info.attack_tick) / info.frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif info.attack_tick <= info.frames[1]+anticipation:
                        scale = (info.frames[1]+anticipation - info.attack_tick) / (info.frames[1]+anticipation-info.frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (info.frames[0] - info.attack_tick) / (info.frames[0]-info.frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                #rotated_image = pygame.transform.rotate(info.env.sprites.sword, -(info.angle)/math.pi*180+attack_offset)
                _angle = round_to_5625(-(info.angle)/math.pi*180+attack_offset)
                _active = info.frames[2] < info.attack_tick < info.frames[1]+anticipation
                weapon_sprite = WeaponDisplay.render(("sword", _angle, _active))
                weapon_rect = weapon_sprite.get_rect()
                weapon_rect.center = composite_center
                composite_surface.blit(weapon_sprite, weapon_rect)
            case Actives.BOW:
                _angle = round_to_5625(-(info.angle)/math.pi*180+attack_offset)
                _active = False
                weapon_sprite = WeaponDisplay.render(("bow", _angle, _active))
                weapon_rect = weapon_sprite.get_rect()
                weapon_rect.center = composite_center
                composite_surface.blit(weapon_sprite, weapon_rect)
            case Actives.AXE:
                if info.attack_tick:
                    if info.attack_tick <= info.frames[2]:
                        scale = (info.frames[2] - info.attack_tick) / info.frames[2]
                        attack_offset = strike*(1-scale) + rest*scale
                    elif info.attack_tick <= info.frames[1]+anticipation:
                        scale = (info.frames[1]+anticipation - info.attack_tick) / (info.frames[1]+anticipation-info.frames[2])
                        attack_offset = windup*(1-scale) + strike*scale
                    else:
                        scale = (info.frames[0] - info.attack_tick) / (info.frames[0]-info.frames[1]-anticipation)
                        attack_offset = rest*(1-scale) + windup*scale
                _angle = round_to_5625(-(info.angle)/math.pi*180+attack_offset)
                _active = info.frames[2] < info.attack_tick < info.frames[1]+anticipation
                weapon_sprite = WeaponDisplay.render(("axe", _angle, _active))
                weapon_rect = weapon_sprite.get_rect()
                weapon_rect.center = composite_center
                composite_surface.blit(weapon_sprite, weapon_rect)
            case active if active in PLACEABLE_ACTIVE_MAP:
                key = PLACEABLE_ACTIVE_MAP[active]
                cost = CONFIG["costs"][key]

                obj = GAMEOBJECTS[key](None, (-1,-1), info.angle, info)

                dist = info.size + 1.4*obj.size + 10
                dx, dy = dist*math.cos(info.angle), dist*math.sin(info.angle)                
                obj.display(composite_surface, obj.getInfo(), np.add(composite_center, (dx,dy)))
                if info.wood is not None and not Player.haveEnoughResources_(info, cost):
                    fill_visible_pixels(composite_surface, (220, 60, 80), scale=0.35)
            case Actives.HEAL:
                dist = info.size + 5
                offset = 60 / 180 * math.pi
                dx, dy = dist*math.cos(info.angle+offset), dist*math.sin(info.angle+offset)
                pygame.draw.circle(composite_surface, (220,120,80), np.add(composite_center, (dx,dy)), info.size*0.6)
            case Actives.FRAG:
                dist = info.size + 5
                offset = 60 / 180 * math.pi
                dx, dy = dist*math.cos(info.angle+offset), dist*math.sin(info.angle+offset)
                pygame.draw.circle(composite_surface, (255,255,255), np.add(composite_center, (dx,dy)), info.size*0.6)

        if relevantinfo not in Player.sprite_cache:
            image_size = (100, 100)
            center = (50, 50)
            surface = pygame.Surface(image_size, pygame.SRCALPHA)

            team_color = CONFIG["team_colors"]["defenders" if info.team==1 else "raiders"]
            border_color = darken(team_color)

            offset = 60 / 180 * math.pi
            attack_offset = -attack_offset / 180 * math.pi
            dx2, dy2 = 14*math.cos(info.angle+offset+attack_offset), 14*math.sin(info.angle+offset+attack_offset)
            dx3, dy3 = 14*math.cos(info.angle-offset+attack_offset), 14*math.sin(info.angle-offset+attack_offset)

            pygame.draw.circle(surface, border_color, np.add(center, (dx2,dy2)), info.size/2)
            pygame.draw.circle(surface, border_color, np.add(center, (dx3,dy3)), info.size/2)
            pygame.draw.circle(surface, team_color, np.add(center, (dx2,dy2)), info.size/2-1.5)
            pygame.draw.circle(surface, team_color, np.add(center, (dx3,dy3)), info.size/2-1.5)
            pygame.draw.circle(surface, border_color, center, info.size)
            pygame.draw.circle(surface, team_color, center, info.size-1.5)
            
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if info.hit:
                fill_visible_pixels(surface)

            Player.sprite_cache[relevantinfo] = surface

        sprite = Player.sprite_cache[relevantinfo]
        sprite_rect = sprite.get_rect()
        sprite_rect.center = composite_center
        composite_surface.blit(sprite, sprite_rect)
        return composite_surface
                    
    def getInfo(self):
        return PlayerInfo(
            type = self.__class__.__name__,
            id_ = self.id_,
            food = self.food,
            wood = self.wood,
            stone = self.stone,
            active = self.active,
            frames = self.frames,
            kills = self.kills,
            position = self.pos,
            size = self.size,
            health = self.health,
            angle = self.angle,
            hit = self.hit,
            team = self.team,
            attack_tick = self.attack_tick,
            shake = self.shake,
            offset = self.offset,
        )
    
    def getInfoHidden(self):
        return PlayerInfo(
            type = self.__class__.__name__,
            id_ = self.id_,
            active = self.active,
            frames = self.frames,
            kills = self.kills,
            position = self.pos,
            size = self.size,
            health = self.health,
            angle = self.angle,
            hit = self.hit,
            team = self.team,
            attack_tick = self.attack_tick,
            shake = self.shake,
            offset = self.offset,
        )
    

class WeaponDisplay:
    sprite_cache = {}

    sprites = {
        "sword": load_asset("sword.png"),
        "bow": load_asset("bow.png"),
        "axe": load_asset("axe.png"),
    }

    @staticmethod
    def render(info):
        weapon, angle, active = info
        relevantinfo = (weapon, angle, active)

        if relevantinfo not in WeaponDisplay.sprite_cache:
            surface = pygame.transform.rotate(WeaponDisplay.sprites[weapon], angle)
            surface = surface.convert()
            surface.set_colorkey((0, 0, 0))

            if active:
                fill_visible_pixels(surface, scale=0.8)

            WeaponDisplay.sprite_cache[relevantinfo] = surface

        sprite = WeaponDisplay.sprite_cache[relevantinfo]
        return sprite