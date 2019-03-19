import math
import random

import matplotlib.pyplot as plt
import numpy as np
import torch

import cv2
from SupportAlgorithm.GlobalLocalPlanner import GlobalLocalPlanner
from SupportAlgorithm.MoveAction import MoveAction
from SupportAlgorithm.NaiveMove import NaiveMove
from util.Grid import Map

class HandAgent():
    def __init__(self):
        self.path = [
            [5.0, 4.5],
            [5.0, 3.0],
            [4.0, 3.0],
            [3.5, 4.7],
            [0.5, 4.5],
            [0.5, 3.0],
            [2.5, 3.0],
            [4.0, 1.5],
            [7.5, 2.0],
            [7.5, 4.5],
        ]
        self.index = 0
        self.target = self.path[self.index]
        self.move = NaiveMove()

    def reset(self):
        self.index = 0
        self.target = self.path[self.index]
        pass

    def select_action(self, state):
        action = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        pos = (state[0], state[1])
        vel = (state[2], state[3])
        angle = state[4]
        if state[-1] > 0 and state[-3] > 0:
            pass
            action[4] = +1.0
            #return action
            #self.target = (state[-4], state[-3])
            #self.move = MoveAction(self.target, pos, vel, angle)
        else:
            action[4] = 0.0
            if ((pos[0]-self.target[0])**2 + (pos[1]-self.target[1])**2 < 0.1):
                self.index = (self.index + 1) % len(self.path)
                self.target = self.path[self.index]

        v, omega = self.move.moveTo(pos, vel, angle, self.target)
        action[0] = v[0] / 2
        action[1] = omega
        action[2] = v[1] / 3
        return action

        return new_action

'''
class HandAgent():
    def __init__(self):
        self.target = (random.random()*8.0, random.random()*5.0)
        self.move = GlobalLocalPlanner()
        self.ctr = 0
        icra_map = Map(40, 25)
        grid = icra_map.getGrid()
        grid = 1 - grid
        self.grid = torch.from_numpy(grid)

    def reset(self):
        self.ctr = 0

    def select_action(self, state):
        action = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        pos = (state[0], state[1])
        vel = (state[2], state[3])
        angle = state[4]
        angular = state[5]
        if state[-1] > 0 and state[-3] > 0:
            action[4] = +1.0
        else:
            action[4] = 0.0
        if self.ctr % 5 == 0:
            if state[-1] > 0 and state[-3] > 0:
                self.target = (state[-4], state[-3])
                if self.move.done or ((pos[0]-self.target[0])**2 + (pos[1]-self.target[1])**2 > 4):
                    self.move.setGoal(pos, self.target)
            else:
                if self.move.done or ((pos[0]-self.target[0])**2 + (pos[1]-self.target[1])**2 < 4):
                    value_map = torch.randn(25, 40).double()
                    value_map *= self.grid
                    # plt.imshow(value_map.numpy())
                    # plt.show()
                    col_max, col_max_indice = value_map.max(0)
                    max_col_max, max_col_max_indice = col_max.max(0)
                    x = max_col_max_indice.item()
                    y = col_max_indice[x].item()
                    x = x/40.0*8.0
                    y = y/25.0*5.0
                    self.target = (x, y)
                    #self.target = (7.5, 0.5)
                    #print(pos, self.target)
                    try:
                        self.move.setGoal(pos, self.target)
                    except:
                        return action
        self.ctr += 1

        new_action = self.move.moveTo(pos, vel, angle, angular, action)

        return new_action
'''