import environments.raiders.env_utils as env_utils

agent_scripts = [
    (env_utils.AgentScripts.PlayerAgent(), 1, "defender"),
    (env_utils.AgentScripts.BasicAgent(), 3, "defender"),
    (env_utils.AgentScripts.BasicAgent(), 6, "raider")
]

env = env_utils.RaiderEnvironmentWrapper(mode="god")
env.loadAgentScripts(agent_scripts)
env.reset()
c = 0
while True:
    if c == 0:
        env.reset()
        c = -1
    elif c > 0:
        c -= 1
    obs, reward, done, term, info = env.step(display=True, sounds=False, debug=False)
    if done:
        c = 5*30
