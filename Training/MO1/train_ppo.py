import random
import torch
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
import gym
from two_services_env.env.routing_env import RoutingEnv
from stable_baselines3.common.callbacks import BaseCallback
import scipy.stats as st

with open("optimal_rewards.txt") as file:
    lines = file.readlines()

optimal_rew = dict()
for line in lines:
    fields = line.strip().split(",")
    optimal_rew[(float(fields[0].strip().split(":")[1]), float(fields[1].strip().split(":")[1]))] = float(
        fields[2].strip().split(":")[1])
    # optimal_rew[(float(fields[0]), float(fields[1]))] = float(fields[2])

class CustomCallback(BaseCallback):
    """
    A custom callback that derives from ``BaseCallback``.

    :param verbose: (int) Verbosity level 0: not output 1: info 2: debug
    """
    def __init__(self, seed: int, verbose=0, eval_every: int = 200):
        super(CustomCallback, self).__init__(verbose)
        self.iter = 0
        self.eval_every = eval_every
        self.seed = seed

    def _on_training_start(self) -> None:
        """
        This method is called before the first rollout starts.
        """
        pass

    def _on_rollout_start(self) -> None:
        """
        A rollout is the collection of environment interaction
        using the current policy.
        This event is triggered before collecting new samples.
        """
        pass

    def _on_step(self) -> bool:
        """
        This method will be called by the model after each call to `env.step()`.

        For child callback (of an `EventCallback`), this will be called
        when the event is triggered.

        :return: (bool) If the callback returns False, training is aborted early.
        """
        return True

    def _on_rollout_end(self) -> None:
        """
        This event is triggered before updating the policy.
        """
        print(f"Training iteration: {self.iter}")
        if self.iter % self.eval_every == 0:
            s = self.training_env.reset()
            N = 1
            max_horizon = 100
            avg_rewards = []
            avg_optimal_rewards = []
            state_actions = []
            for i in range(N):
                done = False
                t = 0
                rewards = []
                optimal_rewards = []
                while not done and t <= max_horizon:
                    # a=self.model.policy.action
                    a, _ = model.predict(s, deterministic=True)
                    state_actions.append((s, a))
                    with open("state_actions.txt",'a') as file:
                        line = str(s) + ":" + str(a)+ "\n"
                        file.write(line)
                    file.close()
                    s, r, done, info = env.step(a)
                    opt_r = optimal_rew[(s[0], s[1])]
                    with open("rewards.txt",'a') as file:
                        line = str(r)+ "\n"
                        file.write(line)
                    file.close()
                    rewards.append(r)
                    optimal_rewards.append(opt_r)
                    t+= 1
                # print(f"R:{R},actions: {actions}, states: {states}")
                avg_rewards.append(np.mean(rewards))
                avg_optimal_rewards.append(np.mean(optimal_rewards))
            avg_R = np.mean(avg_rewards)
            std_R = np.std(avg_rewards)
            avg_optimal_R = np.mean(avg_optimal_rewards)
            (lower, upper) = st.t.interval(alpha=0.95, df=len(avg_rewards) - 1, loc=np.mean(avg_rewards), scale=st.sem(avg_rewards))
            with open(f"avg_reward_{seed}.txt", 'a') as file:
                line = str(avg_R) + ":" + str(std_R) + ":" + str(avg_optimal_R) + "\n"
                file.write(line)
            file.close()
            print(f"[EVAL] Training iteration: {self.iter}, Average R:{avg_R},\n list of (load, action): {state_actions}")
            self.training_env.reset()
            model.save("self_routing_" + str(self.iter))
        self.iter += 1

    def _on_training_end(self) -> None:
        """
        This event is triggered before exiting the `learn()` method.
        """
        pass

if __name__ == '__main__':
    env = gym.make("routing-env-v2")
    env = Monitor(env)

    # Hparams
    num_neurons_per_hidden_layer = 64
    num_layers = 2
    policy_kwargs = dict(net_arch=[num_neurons_per_hidden_layer]*num_layers)
    steps_between_updates = 1024
    learning_rate = 0.001
    batch_size = 64
    device = "cpu"
    gamma = 0
    num_training_timesteps = int(1000000)
    verbose = 0

    # Set seed for reproducibility
    seed = 999
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    cb = CustomCallback(seed=seed, eval_every=10)

    # Train
    model = PPO("MlpPolicy", env, verbose=verbose,
                policy_kwargs=policy_kwargs, n_steps=steps_between_updates,
                batch_size=batch_size, learning_rate=learning_rate, seed=seed,
                device="cpu", gamma=gamma)
    model.learn(total_timesteps=num_training_timesteps, callback=cb)
