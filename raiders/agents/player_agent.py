import pygame
import numpy as np
import random, math, os
import keyboard as k
from attrdict import AttrDict
import math, time
from enum import Enum

from raiders.agents.base_agent import BaseAgent
from raiders.raiders import Actives
from raiders import global_events

class PlayerAgent(BaseAgent):
    def __init__(self):
        pass

    def initialize(self, team):
        self.screen_center = None
        self.observation = None
    
    def registerAgentID(self, id_):
        pass

    def unRegisterAgentID(self, id_):
        pass

    def handleTeamObservation(self, team_observation):
        self.sample_id = tuple(team_observation.keys())[0]
        pass

    def getAction(self, observation, id_):
        self.screen_center = observation.metadata.screen_center
        self.observation = observation

        keys = pygame.key.get_pressed()

        scroll = 0
        for event in global_events.events:
            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    scroll = 1
                elif event.y < 0:
                    scroll = -1

        active = self.observation.self.active
        match active:
            case Actives.TURRET | Actives.SCATTERSHOT | Actives.BIGTURRET:
                choices = [Actives.TURRET, Actives.SCATTERSHOT, Actives.BIGTURRET]
                num_choices = len(choices)
                active_choice = choices.index(active)
                active_choice = (active_choice + scroll) % num_choices
                active = choices[active_choice]

        if keys[pygame.K_1]: active = 1
        if keys[pygame.K_2]: active = 2
        if keys[pygame.K_3]: active = 3
        if keys[pygame.K_4]: active = 4
        if keys[pygame.K_5]: active = 5
        if keys[pygame.K_6]: active = 6
        if keys[pygame.K_q]: active = 7
        if keys[pygame.K_r]: active = 8
        if keys[pygame.K_e]: active = 9



        ax, ay = 1, 1
        if keys[pygame.K_a]: ax -= 1
        if keys[pygame.K_d]: ax += 1
        if keys[pygame.K_s]: ay += 1
        if keys[pygame.K_w]: ay -= 1

        action = False
        if pygame.mouse.get_pressed()[0]:
            action = True
        
        mx, my = pygame.mouse.get_pos()
        cx, cy = self.screen_center
        dx, dy = mx-cx, my-cy
        target_angle = math.atan2(dy, dx)

        player_angle = self.observation.self.angle
        d_angle = (target_angle - player_angle) % (2*math.pi)
        if d_angle < abs(d_angle - 2*math.pi):
            if d_angle < 0.09817: angle = 0
            elif d_angle < 0.09817*4: angle = 1
            else: angle = 2
        else:
            d_angle = abs(d_angle - 2*math.pi)
            if d_angle < 0.09817: angle = 0
            elif d_angle < 0.09817*4: angle = -1
            else: angle = -2
        angle = angle + 2

        view_minimap = False
        if keys[pygame.K_LSHIFT]: view_minimap = True

        if active == self.observation.self.active:
            active = 0

        return (ax, ay, active, action, angle, view_minimap)

    def debug(self, surface, id_):
        pass
    
    def getNames(self):
        return ["player" for i in range(self.n_instances)]