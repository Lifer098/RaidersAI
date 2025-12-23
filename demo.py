import raiders.env_utils as env_utils
from raiders import global_events

import pygame
print(env_utils.AgentScripts)
agent_scripts = [
    #(env_utils.AgentScripts.PlayerAgent(), 1, "raider"),
    (env_utils.AgentScripts.MatthewAgent(), 8, "raider"),
    (env_utils.AgentScripts.MatthewAgent(), 8, "defender")
]

env = env_utils.RaiderEnvironmentWrapper(mode="god")
env.loadAgentScripts(agent_scripts)
#env.addAgent(team="defender")
env.reset()
c = 0
scores = [0,0]

while True:
    global_events.events = pygame.event.get()
    if c == 0:
        env.reset()
        c = -1
    elif c > 0:
        c -= 1
    obs, winning_team, done, term, info = env.step(display=True, sounds=True, debug=False)
    if done and c == -1:
        c = 5*30

        if winning_team == "defender":
            scores[0] += 1
        else:
            scores[1] += 1
        print(f"Defenders: {scores[0]}, Raiders: {scores[1]}")