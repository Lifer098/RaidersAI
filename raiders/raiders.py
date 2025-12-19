import pygame

import numpy as np
import random, math, time
from attrdict import AttrDict
from collections import namedtuple
import os, yaml
from enum import IntEnum

from raiders.observation_utils import TeamObservations, ObservationView
from raiders.gameobjects._gameobject_utils import DisplayLayers

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
from raiders.gameobjects.player import (
    Player,
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
        frame.fill((80, 80, 80))
        
        world_rect = surface.get_rect()
        overlap = self.frame_rect.clip(world_rect)

        if overlap.width > 0 and overlap.height > 0:
            x = overlap.x - self.frame_rect.x
            y = overlap.y - self.frame_rect.y
            frame.blit(surface, (x,y), overlap)
            
        return frame
        


class RaiderEnvironment():
    def __init__(self):
        self.font = pygame.font.Font(None, 30) 
        self.font2 = pygame.font.Font(None, 40) 
        self.font3 = pygame.font.SysFont("Consolas", 10) 
        self.font4 = pygame.font.SysFont("Consolas", 7)

        self.resources = {Bush, Tree, Stone}
        self.walls = {WoodWall, StoneWall, Spike}
        
        self.map_size = [4000, 4000]
        self.center = [self.map_size[0]//2, self.map_size[1]//2]
        self.screen_size = 800, 800
        self.screen_center = [self.screen_size[0]//2, self.screen_size[1]//2]

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
        self.surface_to_minimap_scale = self.minimap_surface.get_width() / self.surface.get_width()
        
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.t = 0

        self.metadata = AttrDict({
            "map_size": self.map_size,
            "center": self.center,
            "screen_size": self.screen_size,
            "screen_center": self.screen_center,
            "time": self.t,
            "storm_size": self.max_storm_size,
        })

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

    def reset(self):
        self.storm_surface.fill((0,0,0,0))
        self.grid = Grid(self, 200)
        self.base = Base(self, (self.map_size[0]/2, self.map_size[1]/2), 1)
        self.storm_size = self.max_storm_size
        self.t = 0

        self.metadata.time = self.t
        self.metadata.storm_size = self.storm_size

        self.objects = []
        self.dynamic_objects = []
        self.effects = []
        self.sounds = []
        self.display_layers = [[] for layer in range(max(DisplayLayers).value)]

        self.addDeposits()
        
        for id_, player in self.players.items():
            team = player.team
            name = player.name
            player = Player(self, (-1,-1), team, id_)
            player.name = name
            self.initializePlayer(player, team)
            self.players[id_] = player
        
        for player in self.players.values():
            self.addDynamicObject(player)
        self.addDynamicObject(self.base)

        team_observations = TeamObservations()
        for id_, player in self.players.items():
            team = "defender" if player.team==1 else "raider"
            obs = self.getObservation(id_)
            if player.team == 1:
                team_observations.defenders_observations[id_] = obs
            else:
                team_observations.raiders_observations[id_] = obs

        return team_observations, {}
    
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
        for _ in range(bushes[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Bush(self, (x,y)))

        for _ in range(stones[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Stone(self, (x,y)))
            
        for _ in range(trees[0]):
            x, y = self.getSpawnLoc()
            self.addObject(Tree(self, (x,y)))

        for _ in range(bushes[1]):
            x, y = self.getSpawnLoc2(400)
            self.addObject(Bush(self, (x,y)))

        for _ in range(stones[1]):
            x, y = self.getSpawnLoc2(400)
            self.addObject(Stone(self, (x,y)))
            
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

    def removeFromDisplay(self, obj):
        display_layer = self.display_layers[obj.display_layer]
        if obj in display_layer:
            display_layer.remove(obj)
    
    def addToDisplay(self, obj):
        display_layer = self.display_layers[obj.display_layer]
        display_layer.append(obj)

    def addObject(self, obj):
        obj.env = self
        self.objects.append(obj)
        self.grid.addObject(obj)
        self.addToDisplay(obj)

    def removeObject(self, obj):
        if self.removeDynamicObject(obj):
            return True
        if obj not in self.objects:
            return False
        self.objects.remove(obj)
        self.grid.removeObject(obj)
        self.removeFromDisplay(obj)
        return True
    
    def addDynamicObject(self, obj):
        obj.env = self
        self.dynamic_objects.append(obj)
        self.addToDisplay(obj)
    
    def removeDynamicObject(self, obj):
        if obj not in self.dynamic_objects:
            return False
        self.dynamic_objects.remove(obj)
        self.removeFromDisplay(obj)
        return True
    
    def addEffect(self, obj):
        self.effects.append(obj)
        self.addToDisplay(obj)
    
    def removeEffect(self, obj):
        self.removeFromDisplay(obj)
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
        self.surface.fill((100, 170, 70))
        self.minimap_surface.fill((35, 35, 35, 50))

        for display_layer in self.display_layers:
            for obj in display_layer:
                obj.display(self.surface, obj.getInfo())
                obj.displayOnMinimap(self.minimap_surface, obj.getInfo(), self.surface_to_minimap_scale)

        if self.storm_size != self.max_storm_size:
            if self.storm_size != self.min_storm_size:
                pygame.draw.circle(self.storm_surface, (100, 0, 30), self.center, int(self.storm_size), width=3)  # transparent center
            self.surface.blit(self.storm_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        for player in self.getPlayers():
            if player.health <= 0:
                continue
            bar_width = 40
            health_ratio = player.health / 25
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

        team_observations = TeamObservations()
        for id_, player in self.players.items():
            team = "defender" if player.team==1 else "raider"
            obs = self.getObservation(id_)
            if player.team == 1:
                team_observations.defenders_observations[id_] = obs
            else:
                team_observations.raiders_observations[id_] = obs

        term = False

        if display:
            frame = self.camera.getFrame(self.surface)
            pygame.transform.scale(frame, self.screen_size, self.screen)
            pygame.display.flip()
            self.clock.tick(20)
        else:
            pygame.event.pump()

        return team_observations, winning_team, done, term, {}

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

    def getObservation(self, id_):
        player = self.players[id_]

        objects = self.grid.getNearbyObjects(player.pos, size=2) + self.dynamic_objects + self.effects
        object_infos = []
        for obj in objects:
            dx, dy = obj.pos[0]-player.pos[0], obj.pos[1]-player.pos[1]
            if abs(dx) > 510 or abs(dy) > 510:
                continue

            obj_info = obj.getInfo()
            obj_info = obj_info._replace(relative_position=(dx,dy))
            object_infos.append(obj_info)

        observation = ObservationView(
            objects=object_infos,
            me=player.getInfo(),
            metadata=self.metadata,
        )

        return observation

