import random
import numpy as np
import joblib

foro_dict = {}
for i in range(0, 6):
    foro_dict[i] = round(i / 5, 1)

def action_to_probability(action):
    return foro_dict[int(action)]

path = "/Users/foro/PycharmProjects/MO1/"

loads_path = ""

# loads1 = []
# loads2 = []
# with open(loads_path+"l1_sin.txt") as file:
#     lines = file.readlines()
# file.close()
# for line in lines:
#     loads1.append(float(line))
#
# with open(loads_path+"l2_sin.txt") as file:
#     lines = file.readlines()
# file.close()
# for line in lines:
#     loads2.append(float(line))

load = np.arange(5, 21, 5)


# load = [20]


class RoutingMiddleWare():

    def __init__(self):
        self.state_size = 2#6
        self.state = np.zeros(self.state_size, dtype=float)
        ######actions#######################
        self.b1 = round(random.randint(0, 5) / 5, 1)
        self.b2 = round(random.randint(0, 5) / 5, 1)

        ######services offered loads########
        self.l1 = 10
        self.l2 = 15

        ######services carried loads########
        self.lc1 = round(self.l1 * (1 - self.b1), 1)
        self.lc2 = round(self.l2 * (1 - self.b2), 1)

        #######response times##############
        self.d11 = random.random()
        self.d12 = random.random()
        self.d21 = random.random()
        self.d22 = random.random()

        #######state######################
        self.state[0] = self.l1
        self.state[1] = self.l2
        # self.state[2] = self.d11
        # self.state[3] = self.d12
        # self.state[4] = self.d21
        # self.state[5] = self.d22

        self.state_counter = 0
        self.LD_counter = 0

        self.delay_models = joblib.load(path + "delays_RF_model.joblib")

    def get_state(self):
        return self.state

    def read_state_from_system(self, action):
        action = np.array(action)
        action = np.squeeze(action)
        # print("Received action:", action)
        self.p11 = action_to_probability(action[0])
        self.p21 = action_to_probability(action[1])
        self.b1 = action_to_probability(action[2])
        self.b2 = action_to_probability(action[3])
        self.p12 = 1 - self.p11
        self.p22 = 1 - self.p21

        self.lc11 = round(self.l1 * (1 - self.b1) * self.p11, 1)
        self.lc12 = round(self.l1 * (1 - self.b1) * self.p12, 1)
        self.lc21 = round(self.l2 * (1 - self.b2) * self.p21, 1)
        self.lc22 = round(self.l2 * (1 - self.b2) * self.p22, 1)

        self.lc1 = self.lc11 + self.lc12
        self.lc2 = self.lc21 + self.lc22

        # print("Parameters passed to model are: ", self.p11*100, self.p21*100, self.b1, self.b2, self.l1, self.l2)
        [[self.d11, self.d12, self.d21, self.d22]] = self.delay_models.predict([[self.p11*100, self.p21*100, self.b1, self.b2, self.l1, self.l2]])
        # print("The produced delays are: ", self.d11, self.d12, self.d21, self.d22)
        # #if (self.LD_counter % 10 == 0):
        # self.l1 = loads1[self.LD_counter] #load[random.randint(0, len(load) - 1)]
        # self.l2 = loads2[self.LD_counter] #load[random.randint(0, len(load) - 1)]

        if (self.LD_counter % 1 == 0):
            self.l1 = load[random.randint(0, len(load) - 1)]
            self.l2 = load[random.randint(0, len(load) - 1)]

        self.state[0] = self.l1
        self.state[1] = self.l2
        # self.state[2] = self.d11
        # self.state[3] = self.d12
        # self.state[4] = self.d21
        # self.state[5] = self.d22

        self.state_counter += 1
        self.LD_counter += 1
        return self.state, self.l1, self.l2, self.lc1, self.lc2, self.d11, self.d12, self.d21, self.d22,\
               round(self.b1, 1), round(self.b2, 1), round(self.p11, 1), round(self.p21, 1)

    def reset(self):
        self.state_counter = 0
        return self.state

# print(action_to_probability(10))
# test_routing = RoutingMiddleWare()
# print(test_routing.read_state_from_system(10))