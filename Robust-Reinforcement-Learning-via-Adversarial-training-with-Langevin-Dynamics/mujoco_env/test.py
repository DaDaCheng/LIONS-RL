import argparse
import os
import gym
import numpy as np
import pickle
import copy
import random

import torch
from torch.distributions import uniform

from ddpg import DDPG
from normalized_actions import NormalizedActions
from utils import load_model
import ast

parser = argparse.ArgumentParser()
parser.add_argument('--eval_type', default='model',
                    choices=['model', 'model_noise'])
parser.add_argument('--hidden_size', type=int, default=64, metavar='N',
                    help='number of neurons in the hidden layers (default: 64)')
parser.add_argument("--two_player", type=ast.literal_eval)
parser.add_argument('--env', default="Swimmer-v2")
parser.add_argument('--alpha', default=0)
parser.add_argument("--optimizer")
parser.add_argument("--action_noise")

args = parser.parse_args()

if(args.two_player):
    base_dir = os.getcwd() + '/models/'
else:
    base_dir = os.getcwd() + '/models_OnePlayer/'


def eval_model(_env, alpha):
    total_reward = 0
    with torch.no_grad():
        state = agent.Tensor([_env.reset()])
        while True:
            action = agent.select_action(state, mdp_type='mdp')
            if random.random() < alpha:
                action = noise.sample(action.shape).view(action.shape)

            state, reward, done, _ = _env.step(action.cpu().numpy()[0])
            total_reward += reward

            state = agent.Tensor([state])
            if done:
                break
    return total_reward


test_episodes = 100
for env_name in [args.env]:#os.listdir(base_dir):
    
    env = NormalizedActions(gym.make(env_name))

    agent = DDPG(beta=0.9, epsilon=0, learning_rate=1e-4, gamma=0.99, tau=0.01, hidden_size_dim0=args.hidden_size, hidden_size_dim1=args.hidden_size, num_inputs=env.observation_space.shape[0], action_space=env.action_space, train_mode=False, alpha=0, replay_size=0, optimizer = 0, two_player=args.two_player, normalize_obs=True)
    noise = uniform.Uniform(agent.Tensor([-1.0]), agent.Tensor([1.0]))

    basic_bm = copy.deepcopy(env.env.env.model.body_mass.copy())

    env_dir = base_dir + env_name + '/'
    for optimizer in [args.optimizer]: #['RMSprop', 'SGLD_thermal_0.01', 'SGLD_thermal_0.001', 'SGLD_thermal_0.0001', 'SGLD_thermal_1e-05']:
        for noise_type in [args.action_noise]: 
            noise_dir = env_dir + optimizer + '/' + noise_type + '/nr_mdp_' + str(args.alpha) + '_1/'	
            if os.path.exists(noise_dir):
                for subdir in sorted(os.listdir(noise_dir)):
                    results = {}
                    
                    run_number = 0
                    dir = noise_dir + subdir #+ '/' + str(run_number)
                    print(dir)
                    if os.path.exists(noise_dir + subdir)\
              		and not os.path.isfile(noise_dir + subdir + '/results_' + args.eval_type):
                        while os.path.exists(dir):
                            load_model(agent=agent, basedir=dir)
                            agent.eval()

                            if 'model' in args.eval_type:
                                if 'noise' in args.eval_type:
                                    test_episodes = 10
                                    for mass in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]: #np.linspace(0.8, 1.2, 10):
                                        if mass not in results:
                                            results[mass] = {}
                                        for alpha in [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]: #np.linspace(0, 0.5, 10):
                                            if alpha not in results[mass]:
                                                results[mass][alpha] = []
                                            for _ in range(test_episodes):
                                                r = eval_model(env, alpha)
                                                results[mass][alpha].append(r)
                                else:
                                    for mass in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]: #np.linspace(0.8, 1.2, 20):
                                        if mass not in results:
                                            results[mass] = []
                                        for _ in range(test_episodes):
                                            for idx in range(len(basic_bm)):
                                                env.env.env.model.body_mass[idx] = basic_bm[idx] * mass
                                            r = eval_model(env, 0)
                                            results[mass].append(r)
                            else:
                                for alpha in np.linspace(0, 0.2, 20):
                                    if alpha not in results:
                                        results[alpha] = []
                                    for _ in range(test_episodes):
                                        r = eval_model(env, alpha)
                                        results[alpha].append(r)

                            run_number += 1
                            dir = noise_dir + subdir + '/' + str(run_number)
                        with open(noise_dir + subdir + '/results_' + args.eval_type, 'wb') as f:
                            pickle.dump(results, f)

env.close()
