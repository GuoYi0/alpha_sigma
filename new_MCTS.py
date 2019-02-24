import numpy as np
import random
import sys
import utils
from five_stone_game import main_process as five_stone_game
import time

num2char = {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f", 6: "g", 7: "h", 8: "i", 9: "j", 10: "k", 11: "l", 12: "m",
            13: "n", 14: "o", 15: "p", 16: "q", 17: "r", 18: "s", 19: "t", 20: "u"}

distrib_calculater = utils.distribution_calculater(utils.board_size)

class edge:
    def __init__(self, action, parent_node, priorP):
        self.action = action
        self.counter = 1.0
        self.parent_node = parent_node
        self.priorP = priorP
        self.child_node = None # self.search_and_get_child_node()

        self.action_value = 0.0

    def backup(self, v):
        self.action_value += v
        self.counter += 1
        self.parent_node.backup(-v)

    def get_child(self):
        if self.child_node is None:
            self.counter += 1
            self.child_node = node(self, -self.parent_node.node_player)
            return self.child_node, True
        else:
            self.counter += 1
            return self.child_node, False

    def UCB_value(self):
        if self.action_value:
            Q = self.action_value / self.counter
        else:
            Q = 0
        return Q + utils.Cpuct * self.priorP * np.sqrt(self.parent_node.counter) / (1 + self.counter)

class node:
    def __init__(self, parent, player):
        self.parent = parent
        self.counter = 0.0
        self.child = {}
        self.node_player = player

    def add_child(self, action, priorP):
        action_name = utils.move_to_str(action)
        self.child[action_name] = edge(action=action, parent_node=self, priorP=priorP)

    def get_child(self, action):
        return self.child[action].get_child()

    def eval_or_not(self):
        return len(self.child)==0

    def backup(self, v):
        self.counter += 1
        if self.parent:
            self.parent.backup(v)

    def get_distribution(self): ## used to get the step distribution of current
        for key in self.child.keys():
            distrib_calculater.push(key, self.child[key].counter)
        return distrib_calculater.get()


    def UCB_sim(self):
        UCB_max = -sys.maxsize
        UCB_max_key = None
        for key in self.child.keys():
            if self.child[key].UCB_value() > UCB_max:
                UCB_max_key = key
                UCB_max = self.child[key].UCB_value()
        this_node, expand = self.child[UCB_max_key].get_child()
        return this_node, expand, self.child[UCB_max_key].action


class MCTS:
    def __init__(self, board_size=11, simulation_per_step=400, neural_network=None):

        self.board_size = board_size
        self.s_per_step = simulation_per_step
        # self.database = {0: {"":node(init_node, 1, self)}}  # here we haven't complete a whole database that can be
        # self.current_node = self.database[0][""]                   # used to search the exist node
        self.current_node = node(None, 1)
        self.NN = neural_network
        self.game_process = five_stone_game(board_size=board_size)
        self.simulate_game = five_stone_game(board_size=board_size)

        self.distribution_calculater = utils.distribution_calculater(self.board_size)

    def renew(self):
        self.current_node = node(None, 1)
        self.game_process.renew()

    def MCTS_step(self, action):
        try:
            next_node = self.current_node.get_child(action)
            next_node.parent = None
        except:
            print("here we are")
        return next_node

    def simulation(self):
        for _ in range(self.s_per_step):
            expand, game_continue = False, True
            this_node = self.current_node
            self.simulate_game.simulate_reset(self.game_process.current_board_state(True))
            state = self.simulate_game.current_board_state()
            while game_continue and not expand:
                if this_node.eval_or_not():
                    state_prob, _ = self.NN.eval(state)
                    valid_move = utils.valid_move(state)
                    for move in valid_move:
                        this_node.add_child(action=move, priorP=state_prob[0, move[0]*self.board_size + move[1]])

                this_node, expand, action = this_node.UCB_sim()
                game_continue, state = self.simulate_game.step(action)

            if not game_continue:
                this_node.backup(1)
            elif expand:
                _, state_v = self.NN.eval(state)
                this_node.backup(state_v)

    def game(self):
        game_continue = True
        game_record = []
        begin_time = int(time.time())
        step = 1
        while game_continue:
            begin_time1 = int(time.time())
            self.simulation()
            action, distribution = self.current_node.get_distribution()
            game_continue, state = self.game_process.step(utils.str_to_move(action))
            self.current_node = self.MCTS_step(action)
            game_record.append({"distribution": distribution, "action":action})
            end_time1 = int(time.time())
            print("step:{}, we cost {} seconds".format(step, end_time1-begin_time1))
            print(" ")
            step += 1
        self.renew()
        end_time = int(time.time())
        min = int((end_time - begin_time)/60)
        second = (end_time - begin_time) % 60
        print("In last game, we cost {}:{}".format(min, second))
        return game_record