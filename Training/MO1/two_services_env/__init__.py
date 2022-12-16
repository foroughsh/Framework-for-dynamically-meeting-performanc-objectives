"""
Register OpenAI Envs
"""
import gym
from gym.envs.registration import register

register(
    id='routing-env-v2',
    entry_point='two_services_env.env.routing_env:RoutingEnv'
)