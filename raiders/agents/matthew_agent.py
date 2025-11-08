import pygame
import numpy as np
import random, math, os
import keyboard as k
from attrdict import AttrDict
import math, time
from enum import Enum

from agents.base_agent import BaseAgent

def dist2(v1, v2):
    return (v2[0]-v1[0])**2 + (v2[1]-v1[1])**2

'''
    PLANNING DOCUMENT

    Different State ideas.
    1. Mining nearby resources (Maybe be able to optimize to see the best spot to mine the most resources)
    
    What is powerful in the game and counter play

    Spike trapping oneshots but it needs a condition
    A wall to trap the player against
    Maybe could be achieved to slow down

    All attacks share same cd, placements don't have one.
    Be perma attacking, whether it be with sword, axe, bow, frag, and always be moving or in combat placing stuff.

    When do I want Sword: Attack to stun to make it easier to spike trap
    Bow: Ranged when lower on stone
    Axe: Resource gathering and destroying bases (sieging)
    Frag: If there are enemy structures nearby

    wood wall: Do not use unless low on stone
    stone wall:  Use if have resources, if running or against turrets or maybe for pincer maneuvers.
    spike: If enemy is too close, use spikes
    turret: If many resources and near center (with no enemies around if raider)
    heal: Low on health, face away from enemy maybe and place walls to block path to heal

    
    If close: spam spikes
    
    Turtle: If under 20% and have >30 food then wall up and heal
    Run away: less than 40 of 1 resources
    place walls between enemy and yourself, while shooting them with bow
    specifically run along edge of map and not towards edge of map

    

    Nearby enemy: bow and wall?

    If many resources and near middle: place turret

    Default: gathering
    
    Small percent chance to be afk until a nearby player approaches it and jumpscaring them
    Small percent chance to perma zerg-rush and pincer-maneuver the enemies
'''

class MatthewAgent(BaseAgent):
    class States(Enum): # basic agent states
        IDLE = 0
        PANIC = 1
        TURTLE = 2
        RETREAT = 3
        COMBAT = 4
        GATHER = 5
        EXPLORE = 6

    class AgentState():
        DEFAULT_ACTION = [1, 1, 0, 0, 2]

        def __init__(self, agent_script, agent_id):
            self.agent_script = agent_script
            self.agent_id = agent_id
            self.state = self.agent_script.States.IDLE
            self.action = self.DEFAULT_ACTION[:]
            self.target_pos = None
            self.patience = -1
            self.base_is_objective = False
            self.home = (1000+random.random()*300-150,1000+random.random()*300-150)
        
        def changeState(self, state):
            self.state = state
            self.target_pos = None
            self.patience = -1

    def __init__(self):
        self.solid_objects = ("spike", "stonewall", "woodwall", "turret", "stone", "tree", "bush")
        self.structures = ("spike", "stonewall", "woodwall", "turret")

        self.font = pygame.font.Font(None, 20)
        self.state_texts = {
            s: pygame.transform.flip(
                self.font.render("a" * random.randint(1,12), True, (255,255,255)), False, True)
            for s in self.States
        }

    def initialize(self, team):
        self.team = 1 if team=="defender" else 2
        self.agent_states = {}
        self.agent_ids = []

    def addAgent(self, id_):
        self.agent_states[id_] = self.AgentState(self, id_)
        self.agent_ids.append(id_)
        
        return f"MatthewAgent{id_}"

    def removeAgent(self, id_):
        self.agent_states.remove(id_)
        self.agent_ids.remove(id_)

    def teamStr(self, team):
        return "defender" if team == 1 else "raider"

    def getAction(self, observation, id_):
        # each agent outputs an action when step is called
        '''
        Observation is defined as nested AttrDicts
        observation:
            metadata: 
                colors: color information
                map_size: map size
                center: map center x,y
                screen_size: screen size
                screen_center: screen center x,y
                time: current game timestep
                storm_size: current storm size
            vector_obs:
                [0]: player team
                [1]: player health scaled
                [2]: player food scaled
                [3]: player wood scaled
                [4]: player stone scaled
            self:
                player_info
            <object type>:
                list of infos of nearby object of type <object type>


        Action is defined as 5 ints:
        action:
            [0]: action_x (0: left, 1: none, 2: right)
            [1]: action_y (0: down, 1: none, 2: up)
            [2]: select_active
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
            [3]: place/attack (0: none, 1: action)
            [4]: action_angle
                    0: rotate 22.5° clockwise
                    1: rotate 5.625° clockwise
                    2: no rotation
                    3: rotate 5.625° counterclockwise
                    4: rotate 22.5° counterclockwise
        '''

        self.obs = observation
        self.state = self.agent_states[id_]

        state = self.state.state

        
        resource_list = ("bush", "tree", "stone")
        nearby_resources = []
        for rl in resource_list:
            for resource in self.obs[rl]:
                nearby_resources.append(resource)
        teammates, enemies = self.nearbyPlayers()
        closest_enemy, enemy_distance = self.getClosestObject(enemies)
        nearby_turrets = self.nearbyStructuresofType("turret","enemy")
        
        nearby_threats = nearby_turrets + enemies
        viable_threats = [threat for threat in nearby_threats if not self.objectsInWay(threat.position, pov = "enemy")] # Check to see if there's a clear line between threat and ally
        attackable_threats = [threat for threat in nearby_threats if not self.objectsInWay(threat.position, pov = "ally")]
        
        closest_target, target_distance = self.getClosestObject(attackable_threats)
        closest_threat, threat_distance = self.getClosestObject(viable_threats)
        closest_turret, turret_distance = self.nearestStructureofType("turret","enemy")
        
        closest_resource, resource_distance = self.getClosestObject(nearby_resources)
        resource_position = self.state.home
        if(closest_resource):
            resource_position = closest_resource.position
        
        

        self.state.action[2] = 3
        self.pointToTarget(resource_position)
        self.moveTowardsPos(resource_position)
        self.spamClick()
        
        
        
        
        
        if(target_distance < 500 and self.enoughResourcesFor("bow") and closest_target.type == "player"):
            self.state.action[2] = 2 # ADD A METHOD TO CHECK IF A BLOCK IS PLACEABLE OR INCREMENTAL ROTATIONS
            self.pointToTarget(closest_target.position)
        if(closest_target and closest_target.type == "turret" and target_distance < 350 and target_distance > 50): # If there's a nearby turret threat
            if(self.enoughResourcesFor("frag")):
                self.state.action[2] = 4
                self.pointToTarget(closest_target.position)
                self.moveTowardsPos(resource_position)
            elif(self.canPlaceWall()):
                self.state.action[2] = self.canPlaceWall()
                self.pointToTarget(closest_target.position)
                self.moveTowardsPos(resource_position)
            else:
                self.state.action[2] = 3
                self.pointToTarget(resource_position)
                self.moveTowardsPos(closest_target.position, away = True)
        if(((self.obs.self.health<10) or (self.lowOnResources())) and threat_distance < 120): # Run away
            if(self.enoughResourcesFor("bow")):
                self.state.action[2] = 2 # ADD A METHOD TO CHECK IF A BLOCK IS PLACEABLE OR INCREMENTAL ROTATIONS
                self.pointToTarget(closest_threat.position)
            elif(self.canPlaceWall()):
                self.state.action[2] = self.canPlaceWall()
                self.pointToTarget(closest_threat.position)
            else:
                self.state.action[2] = 3
                self.pointToTarget(resource_position)
            self.moveTowardsPos(closest_threat.position, away = True)
        if(threat_distance < 300 and self.canPlaceWall()):
            self.state.action[2] = self.canPlaceWall()
            self.pointToTarget(closest_threat.position)
            self.moveTowardsPos(resource_position)
        if((enemy_distance<80) and ((not self.lowOnResources()) or (closest_enemy.health<5))): # Attack and follow enemy if gets into range
            # If low on resources, it should only follow if enemy is low on health
            self.state.action[2] = 1
            self.pointToTarget(closest_enemy.position)
            self.moveTowardsPos(closest_enemy.position)
        if((enemy_distance < 45) and (self.enoughResourcesFor("spike")) and self.canPlaceObject()): #  and  # Spike panic if nearby enemies
            self.state.action[2] = 7
            self.pointToTarget(closest_enemy.position)
            self.moveTowardsPos(closest_enemy.position)
        if(self.obs.self.health < 15 and self.enoughResourcesFor("heal")):
            self.state.action[2] = 9
        

        if(self.insideStorm()):
            self.moveTowardsPos(self.obs.metadata.center)


        match state: # basic agent operates on a Finite State Automaton
            case self.States.IDLE:
                self.handleIdle()
            case self.States.PANIC:
                self.handlePanic()
            case self.States.TURTLE:
                self.handleTurtle()
            case self.States.RETREAT:
                self.handleRetreat()
            case self.States.COMBAT:
                self.handleCombat()
            case self.States.GATHER:
                self.handleGather()
            case self.States.EXPLORE:
                self.handleExplore()
        

        return self.agent_states[id_].action
    
    def insideStorm(self):
        return self.obs.metadata.storm_size**2<dist2(self.obs.metadata.center,self.obs.self.position)
    
    def canPlaceWall(self):
        if(not self.canPlaceObject()):
            return 0
        if(self.enoughResourcesFor("stonewall")):
            return 6
        if(self.enoughResourcesFor("woodwall")):
            return 5
        return 0
    
    def canPlaceObject(self):
        dist = 15 + 1.4*17 + 10
        dx, dy = dist*math.cos(self.obs.self.angle), dist*math.sin(self.obs.self.angle)
        spike_pos = np.add(self.obs.self.position, (dx,dy))
        for obj in self.obs.bush + self.obs.tree + self.obs.stone + self.obs.woodwall + self.obs.stonewall + self.obs.turret:
            if math.dist(obj.position, spike_pos) <= obj.size + 30:
                return False
        return True

    def enoughResourcesFor(self, action):
        food, wood, stone = self.obs.self.food, self.obs.self.wood, self.obs.self.stone
        if(action == "bow"):
            return wood>2
        if(action == "frag"):
            return stone > 10
        if(action == "woodwall"):
            return wood > 10
        if(action == "stonewall"):
            return stone > 20
        if(action == "spike"):
            return (wood > 12) and (stone > 12)
        if(action == "turret"):
            return (wood > 45) and (stone > 30)
        if(action == "heal"):
            return food > 15

    def lowOnResources(self):
        if self.obs.self.food < 40: return True
        if self.obs.self.wood < 40: return True
        if self.obs.self.stone < 40: return True
        return False

    def handleTeamObservation(self, team_observation):
        '''
        handle any macro team-wide decision making
        '''
        self.observations = team_observation
        pass

    def spamClick(self):
        self.state.action[3] = 1 - self.state.action[3]

    def handleTeamObservationsRaider(self, team_observations):
        pass


    def handleTeamObservationsDefender(self, team_observations):
        # handle defender decision making
        pass
            

    def handleIdle(self):
        '''
        transition, decision-making
        '''
        pass

    def handlePanic(self):
        '''
        wandering the map
        '''

        pass

    def handleTurtle(self):
        '''
        collecting resources within vicinity
        '''

        pass

    def handleRetreat(self):
        '''
        group with other teammates
        '''
        pass

    def handleCombat(self):
        '''
        advance on enemies and deal damage
        '''
        pass

    def handleGather(self):
        '''
        run away from enemies
        '''
        pass


    def handleExplore(self):
        '''
        hold a position and clear a path forward
        '''
        pass

    def objectsInWay(self, target_pos, size=None, pov=""):
        if size is None:
            size = self.obs.self.size

        self_pos = self.obs.self.position
        dx, dy = target_pos[0] - self_pos[0], target_pos[1] - self_pos[1]
        
        A = -dy
        B = dx
        C = 0
        denom = max(0.0000001, math.sqrt(A*A + B*B))

        objects_in_way = []
        for obj in sum([self.obs[type_] for type_ in self.solid_objects], []):
            if obj.type in ("spike", "stonewall", "turret") and obj.team == self.team and pov == "ally":
                continue
            if obj.type in ("spike", "stonewall", "turret") and obj.team != self.team and pov == "enemy":
                continue
            x, y = obj.relative_position
            d = abs(A*x + B*y + C) / denom
            if d < obj.size + size and dx*x + dy*y > 0 and d >0.01:
                objects_in_way.append(obj)

        return objects_in_way
    
    def nearestStructureofType(self, structure_name, team = ""):
        structures = self.nearbyStructuresofType(structure_name,team)
        return self.getClosestObject(structures)
        
    def nearbyStructuresofType(self, structure_name, team = ""):
        structures = []
        for obj in self.obs[structure_name]:
            if((team == "ally") and (obj.team == self.team)):
                structures.append(obj)
            elif((team == "enemy") and (obj.team != self.team)):
                structures.append(obj)
            elif(not team):
                structures.append(obj)
        return structures

    
    def nearbyEnemyStructures(self):
        enemy_structures = []
        for obj in self.obs.spike + self.obs.turret:
            if obj.team != self.team:
                enemy_structures.append(obj)
        return enemy_structures

    def averagePositionOfObjects(self, objects, distance_threshold=999):
        x_positions = []
        y_positions = []
        for obj in objects:
            if math.dist(obj.relative_position, (0,0)) >= distance_threshold:
                continue
            x_positions.append(obj.position[0])
            y_positions.append(obj.position[1])
        n = len(x_positions)
        return (sum(x_positions) / max(1,n), sum(y_positions) / max(1,n))

    def pointToTarget(self, target_pos, away=False):
        self_pos = self.obs.self.position
        dx, dy = target_pos[0] - self_pos[0], target_pos[1] - self_pos[1]
        if away:
            dx, dy = -dx, -dy
        target_angle = math.atan2(dy, dx)
        self.pointToAngle(target_angle)
    
    def pointToAngle(self, target_angle):
        self_angle = self.obs.self.angle
        d_angle = (target_angle - self_angle) % (2*math.pi)
        if d_angle < abs(d_angle - 2*math.pi):
            if d_angle < 0.09817: angle = 0
            elif d_angle < 0.09817*4: angle = 1
            else: angle = 2
        else:
            d_angle = abs(d_angle - 2*math.pi)
            if d_angle < 0.09817: angle = 0
            elif d_angle < 0.09817*4: angle = -1
            else: angle = -2
        a_angle = angle + 2
        self.state.action[4] = a_angle
    
    def getClosestObject(self, objects):
        self_pos = self.obs.self.position

        min_dist = math.inf
        closest_object = None
        for obj in objects:
            obj_pos = obj.position
            dist = math.dist(self_pos, obj_pos)
            if dist < min_dist:
                min_dist = dist
                closest_object = obj
        
        return closest_object, min_dist

    def nearbyPlayers(self):
        teammates, enemies = [], []
        for player_info in self.obs.player:
            if player_info.team == self.team:
                if player_info.id_ in self.agent_ids:
                    teammates.append(player_info)
            else:
                enemies.append(player_info)
        return teammates, enemies

    def moveTowardsPos(self, pos, move_threshold=5, away=False):
        self_pos = self.obs.self.position
        dx, dy = pos[0] - self_pos[0], pos[1] - self_pos[1]

        if math.dist(self_pos, pos) < 1.4*move_threshold:
            return True
        
        if away: dx, dy = -dx, -dy
        final_dx = 2 * int(dx>0)
        final_dy = 2 * int(dy>0)
        self.state.action[0] = final_dx
        self.state.action[1] = final_dy

        return
    
        angle = math.atan2(dy, dx)
        self.moveTowardsAngle(angle)
        return
    
    def moveTowardsAngle(self, angle, rad=True):
        for spike in self.obs.spike:
            if math.dist(self.obs.self.position, spike.position) < 55:
                dx, dy = spike.position[0] - self.obs.self.position[0], spike.position[1] - self.obs.self.position[1]
                angle2 = math.atan2(dy, dx)
                da = min(0.05, angle2 - angle)
                if abs(da) < math.pi/2:
                    angle = da / abs(da) * math.pi * 0.44 + angle2
                    break


        # law of large numbers
        if rad==False: 
            angle_rad = angle / 180 * math.pi
        else:
            angle_rad = angle
        dx, dy = math.cos(angle_rad), math.sin(angle_rad)
        if dx > dy:
            ax = 2 if dx > 0 else 0
            if random.random() < abs(dy):
                ay = 2 if dy > 0 else 0
            else:
                ay = 1
        else:
            ay = 2 if dy > 0 else 0
            if random.random() < abs(dx):
                ax = 2 if dx > 0 else 0
            else:
                ax = 1
        self.state.action[0] = ax
        self.state.action[1] = ay
    
    def debug(self, surface, id_):
        agent_id = id_
        obs = self.observations[agent_id]
        state = self.agent_states[agent_id]


        text_surf = pygame.transform.flip(
                self.font.render("a" * random.randint(1,600), True, (1,0,255)), False, True)
        # display name for demo purposes
        #text_surf = pygame.transform.flip(self.font.render("NewAgent", True, (255,255,255)), False, True)
        text_rect = text_surf.get_rect(center=(obs.self.position[0], obs.self.position[1]+30))
        surface.blit(text_surf, text_rect)
    
    def getNames(self):
        return ["a" * random.randint(1,12)]
