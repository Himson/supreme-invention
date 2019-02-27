import random
import math
import Box2D
import numpy as np
from collections import namedtuple
from itertools import count

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

from ICRAField import ICRAField
from SupportAlgorithm.MoveAction import MoveAction

seed = 233
torch.random.manual_seed(seed)
torch.cuda.random.manual_seed(seed)
np.random.seed(seed)
random.seed(233)

env = ICRAField()

# if gpu is to be used
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

Transition = namedtuple('Transition', ('state', 'action', 'next_state', 'reward'))

class ReplayMemory(object):

    def __init__(self, capacity):
        self.capacity = capacity
        self.memory = []
        self.position = 0

    def push(self, *args):
        """Saves a transition."""
        if len(self.memory) < self.capacity:
            self.memory.append(None)
        self.memory[self.position] = Transition(*args)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)

class DQN(nn.Module):
    def __init__(self):
        super(DQN, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(5, 100),
        )

    def forward(self, s):
        value_map = self.fc(s)
        value_map = value_map.reshape([-1, 10, 10])
        return value_map


BATCH_SIZE = 128
GAMMA = 0.999
EPS_START = 0.9
EPS_END = 0.05
EPS_DECAY = 200
TARGET_UPDATE = 10

policy_net = DQN().to(device).double()
target_net = DQN().to(device).double()
target_net.load_state_dict(policy_net.state_dict())
target_net.eval()

optimizer = optim.RMSprop(policy_net.parameters())
memory = ReplayMemory(10000)

steps_done = 0

def select_goal(state):
    global steps_done
    sample = random.random()
    eps_threshold = EPS_END + (EPS_START - EPS_END) * \
        math.exp(-1. * steps_done / EPS_DECAY)
    steps_done += 1
    if sample > eps_threshold:
        with torch.no_grad():
            value_map = policy_net(state)[0]
            col_max, col_max_indice = value_map.max(dim=0)
            max_col_max, max_col_max_indice = col_max.max(dim=0)
            x = max_col_max_indice.item()
            y = col_max_indice[x].item()
            return x/10.0, y/10.0, value_map[x, y]
    else:
        return random.random(), random.random(), random.random()

episode_durations = []

def optimize_model():
    if len(memory) < BATCH_SIZE:
        return
    transitions = memory.sample(BATCH_SIZE)
    # Transpose the batch (see https://stackoverflow.com/a/19343/3343043 for
    # detailed explanation). This converts batch-array of Transitions
    # to Transition of batch-arrays.
    batch = Transition(*zip(*transitions))

    # Compute a mask of non-final states and concatenate the batch elements
    # (a final state would've been the one after which simulation ended)
    non_final_mask = torch.tensor(tuple(map(lambda s: s is not None,
                                          batch.next_state)), device=device, dtype=torch.uint8)
    non_final_next_states = torch.cat([s for s in batch.next_state
                                                if s is not None])
    state_batch = torch.cat(batch.state)
    action_batch = torch.cat(batch.action)
    reward_batch = torch.cat(batch.reward)

    # Compute Q(s_t, a) - the model computes Q(s_t), then we select the
    # columns of actions taken. These are the actions which would've been taken
    # for each batch state according to policy_net
    state_action_values = policy_net(state_batch)
    state_action_values = state_action_values.reshape([BATCH_SIZE, -1]).max(dim=1)[0]

    # Compute V(s_{t+1}) for all next states.
    # Expected values of actions for non_final_next_states are computed based
    # on the "older" target_net; selecting their best reward with max(1)[0].
    # This is merged based on the mask, such that we'll have either the expected
    # state value or 0 in case the state was final.
    next_state_values = torch.zeros(BATCH_SIZE, device=device).double()
    value = target_net(non_final_next_states)
    value = value.reshape([BATCH_SIZE, -1]).max(dim=1)[0].detach()
    next_state_values[non_final_mask] = value
    # Compute the expected Q values
    expected_state_action_values = (next_state_values * GAMMA) + reward_batch

    # Compute Huber loss
    loss = F.smooth_l1_loss(state_action_values, expected_state_action_values.unsqueeze(1))

    # Optimize the model
    optimizer.zero_grad()
    loss.backward()
    for param in policy_net.parameters():
        param.grad.data.clamp_(-1, 1)
    optimizer.step()

num_episodes = 50
for i_episode in range(num_episodes):
    # Initialize the environment and state
    action = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    env.reset()
    state_dict, reward, done, info = env.step(action)
    state_array = env.get_state_array()
    state = torch.from_numpy(state_array).unsqueeze(0)
    for t in range(7*60*30):
        # Select and perform an action
        x, y, _ = select_goal(state)

        target = Box2D.b2Vec2(x, y)
        move = MoveAction(target, state_dict)
        action = move.MoveTo(state_dict, action)

        state_dict, reward, done, info = env.step(action)
        state_array = env.get_state_array()

        next_state = torch.from_numpy(state_array).to(device).unsqueeze(0)
        reward = torch.tensor([reward], device=device).double()
        goal = torch.tensor([x, y], device=device)

        # Store the transition in memory
        memory.push(state, goal, next_state, reward)

        # Move to the next state
        state = next_state

        # Perform one step of the optimization (on the target network)
        optimize_model()
        if done:
            episode_durations.append(t + 1)
            break
    # Update the target network, copying all weights and biases in DQN
    if i_episode % TARGET_UPDATE == 0:
        target_net.load_state_dict(policy_net.state_dict())

print('Complete')
env.render()
env.close()