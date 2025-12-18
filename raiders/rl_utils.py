import pygame
import numpy as np
import random, math, os
import importlib
import inspect
import keyboard as k
from attrdict import AttrDict
import math, time
from enum import Enum

from raiders.env_utils import RaiderEnvironmentWrapper

import numpy as np
import cv2
from gym import Env, spaces

class RaiderRLEnv(Env):
    def __init__(self, teams, agent_ids=None, resolution=(64, 64), shaped_reward=False, shuffle=True, frameskip=4, visible=False):
        self.shuffle = shuffle
        self.frameskip = frameskip
        self.visible = visible
        if not self.visible:
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        self.teams = teams
        self.resolution = resolution
        self.shaped_reward = shaped_reward

        if agent_ids is None:
            self.ids = [id_ for id_ in range(sum(self.teams))]
        else:
            self.ids = agent_ids
        self.n_agents = len(self.ids)

        self.env = RaiderEnvironmentWrapper()
        self.env.speedup = True
        self.env.camera_mode = "hover_player"
        for team, agents in zip(("defender", "raider"), teams):
            for agent in range(agents):
                self.env.addAgent(team)
        self.reset()
    
    def reset(self):
        if self.shuffle:
            random.shuffle(self.ids)

        obs, info = self.env.reset()
        if self.n_agents == 1:
            self.last_obs = np.array(
                cv2.resize(obs[self.ids[0]].image_obs, self.resolution, cv2.INTER_NEAREST),
                dtype=np.float32
            )
        else:
            self.last_obs = np.array(
                [cv2.resize(obs[id_].image_obs, self.resolution, cv2.INTER_NEAREST) for id_ in self.ids],
                dtype=np.float32
            )
        return self.last_obs, info

    def calculateReward(self, player_info, winning_team):
        player_events = player_info.events
        r = 0

        #r += player_info.wood * 0.001
        
        if self.shaped_reward:
            r += player_events.change_food * 0.001
            r += player_events.change_wood * 0.00065
            r += player_events.change_stone * 0.00065
            r += player_events.change_health * 0.003
            r += player_events.change_health_enemy_player * 0.0015
            #r += player_events.damage_dealt_enemy_structure * 0.00005
            #r += player_events.change_health_team_player * 0.001
            #r += player_events.damage_dealt_team_structure * -0.00005
            r += player_events.killed_enemy_player * 2
            r += player_events.died * -5
            r += player_events.self_damage_dealt_base * 0.01
            r += player_events.damage_dealt_base * 0.002        

        if winning_team is None: pass
        elif ["defender", "raider"][player_info.team-1] == winning_team: r += 20
        else: r -= 20

        return r
    
    def step(self, actions, display=True):
        if self.n_agents == 1:
            self.env.actions[self.ids[0]] = actions
        else:
            for id_ in self.ids:
                self.env.actions[id_] = actions[id_]

        if self.n_agents == 1:
            rewards = np.array(0, dtype=np.float32)
        else:
            rewards = np.zeros(self.n_agents, dtype=np.float32)
        
        for i in range(self.frameskip-1):
            obs, winning_team, terminated, truncated, info = \
                self.env.step(display=display, debug=False)
            rewards += np.array(
                self.calculateReward(obs[self.ids[0]].self, winning_team),
                dtype=np.float32
            )

        obs, winning_team, terminated, truncated, info = \
            self.env.step(display=display, debug=False)
        
        if self.n_agents == 1:
            self.last_obs = np.array(
                cv2.resize(obs[self.ids[0]].image_obs, self.resolution, cv2.INTER_NEAREST),
                dtype=np.float32
            )
            rewards += np.array(
                self.calculateReward(obs[self.ids[0]].self, winning_team),
                dtype=np.float32
            )
        else:
            self.last_obs = np.array(
                [cv2.resize(obs[id_].image_obs, self.resolution, cv2.INTER_NEAREST) for id_ in self.ids],
                dtype=np.float32
            )
            rewards += np.array(
                [self.calculateReward(obs[id_].self, winning_team) for id_ in self.ids],
                dtype=np.float32
            )

        done = terminated or truncated

        return self.last_obs, rewards, done, False, info


pygame.init()

# example usage
if __name__ == "__main__":

    env = RaiderRLEnv(teams=(5,5))
    env.reset()
    c = 0
    while True:
        if c == 0:
            env.reset()
            c = -1
        elif c > 0:
            c -= 1
        obs, reward, done, term, info = env.step(display=True)
        if done:
            c = 5*30
