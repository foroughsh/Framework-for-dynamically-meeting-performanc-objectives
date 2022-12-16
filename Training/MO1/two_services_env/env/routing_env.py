from typing import Tuple
import gym
import numpy as np
import math
from two_services_env.env.routing_middle_ware import RoutingMiddleWare


class RoutingEnv(gym.Env):

    def __init__(self):
        # State (load)
        self.num_loads = 4
        self.load_indexes = {5: 0, 10: 1, 15: 2, 20: 3}
        self.action_indexes = {0: 0, 0.2: 1, 0.4: 2, 0.6: 3, 0.8: 4, 1.0: 5}
        # self.observation_space = gym.spaces.Box(low=np.array([0,0,0,0,0,0]), dtype=np.float32, high=np.array([1,1,1,1,1,1]),
        #                                         shape=(6,))
        self.observation_space = gym.spaces.Box(low=np.array([0,0]), dtype=np.float32, high=np.array([1,1]),
                                                shape=(2,))
        # self.action_space = gym.spaces.Discrete(5)
        self.action_space = gym.spaces.MultiDiscrete([5,5,5,5])
        self.middleware = RoutingMiddleWare()
        self.load = [5,5]

        self.s = self.load

        self.l1 = 0
        self.lc1 = 0

        self.l2 = 0
        self.lc2 = 0

        self.d11 = 0
        self.d12 = 0
        self.d21 = 0
        self.d22 = 0

        self.p11 = 0
        self.p21 = 0
        self.b1 = 0
        self.b2 = 0

        self.reset()

    def step(self, a: gym.spaces.MultiDiscrete) -> Tuple[np.ndarray, int, bool, dict]:
        done = False
        info = {}
        next_state, l1, l2, lc1, lc2, d11, d12, d21, d22, b1, b2, p11, p21 = self.middleware.read_state_from_system(a)

        s1_delay = max(round(d11, 4), round(d12, 4))
        s2_delay = max(round(d21, 3), round(d22, 3))
        th1 = 0.035
        th2 = 0.110

        s1_delay = max(round(d11, 4), round(d12, 4))
        s2_delay = max(round(d21, 3), round(d22, 3))
        th1 = 0.035
        th2 = 0.110

        if (s1_delay <= th1):
            re1 = lc1
        else:
            re1 = lc1 / (1 + np.exp(200 * (s1_delay - 0.05)))

        if (s2_delay <= th2):
            re2 = lc2
        else:
            re2 = lc2 / (1 + np.exp(200 * (s2_delay - 0.113)))

        reward = re1 + re2

        info["d11"] = d11
        info["d12"] = d12
        info["d21"] = d21
        info["d22"] = d22
        info["cl1"] = lc1
        info["cl2"] = lc2

        # update state
        self.load = next_state[0]

        self.l1 = l1
        self.l2 = l2

        self.lc1 = lc1
        self.lc2 = lc2

        self.d11 = d11
        self.d12 = d12
        self.d21 = d21
        self.d22 = d22

        self.b1 = b1
        self.b2 = b2
        self.s = next_state
        # self.s = self.load_to_state()
        s_prime =self.s

        info["r"] = reward
        info["p11"] = self.p11
        info["p21"] = self.p21
        info["b1"] = self.b1
        info["b2"] = self.b2


        return s_prime, reward, done, info

    def reset(self) -> np.ndarray:
        self.middleware.reset()

        # self.state, self.l2, self.l1, self.lc1, self.lc2, self.d11, self.d12, self.d21, self.d22, \
        # round(self.b1, 1), round(self.b2, 1), round(self.p11, 1), round(self.p21, 1)

        state, l1, l2, lc1, lc2, d11, d12, d21, d22, b1, b2, p11, p21 = self.middleware.read_state_from_system([0,0,0,0])
        self.load = state

        self.l2 = l2
        self.l1 = l1

        self.lc1 = lc1
        self.lc2 = lc2

        self.d11 = d11
        self.d12 = d12
        self.d21 = d21
        self.d22 = d22

        self.b1 = b1
        self.b2 = b2

        self.s = state

        return self.s

    def load_to_state(self):
        s = np.zeros(self.num_loads)
        s[self.load_indexes[self.load]] = 1
        return s


