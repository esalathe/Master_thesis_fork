#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import math
from matplotlib import pyplot as plt
from custom_message.msg import FullState, Path, MultiplePaths, MultiState
import message_filters
import numpy as np
import time

# For the parameter file
import pathlib
import json

path = pathlib.Path('/home/giacomo/thesis_ws/src/bumper_cars/params.json')
# Opening JSON file
with open(path, 'r') as openfile:
    # Reading from json file
    json_object = json.load(openfile)


robot_num = json_object["robot_num"]

class Config:
    """
    simulation parameter class
    """

    def __init__(self):
        self.robot_width = 1.45  # [m] for collision check
        self.robot_length = 2.9  # [m] for collision check
        # obstacles [x(m) y(m), ....]

        self.trail_length = 5

config = Config()
controller_type = json_object["Controller"]["controller_type"]
debug = False
plot_traj = True

class Plotter(Node):

    def __init__(self):
        super().__init__("plotter")

        multi_state_sub = message_filters.Subscriber(self, MultiState, "/multi_fullstate")
        self.multi_path_sub = message_filters.Subscriber(self, MultiplePaths, "/robot_multi_traj")

        self.state1_buf = np.array([0,0])
        self.state2_buf = np.array([0,0])
        self.state3_buf = np.array([0,0])

        self.states_x_buf = np.zeros((robot_num, 1))
        self.states_y_buf = np.zeros((robot_num, 1))

        # TODO: Pass it from parameters file
        self.controller_type = controller_type

        self.width = 100
        self.heigth = 100

        if self.controller_type == "random_walk":
            ts = message_filters.ApproximateTimeSynchronizer([multi_state_sub], 10, 1, allow_headerless=True)
            ts.registerCallback(self.plotter_callback)
        else:
            ts = message_filters.ApproximateTimeSynchronizer([multi_state_sub, self.multi_path_sub], 10, 1, allow_headerless=True)
            ts.registerCallback(self.complete_plotter_callback)

        self.get_logger().info("Plotter has been started")

    def plotter_callback(self, multi_state: MultiState):
        
        plt.cla()
        # for stopping simulation with the esc key.
        plt.gcf().canvas.mpl_connect(
            'key_release_event',
            lambda event: [exit(0) if event.key == 'escape' else None])

        for i in range(robot_num):
            self.plot_robot(multi_state.multiple_state[i])
            if debug:
                self.get_logger().info("robot" + str(i) + ", x: " + str(multi_state.multiple_state[i].x) + ", " +
                                    "y: " + str(multi_state.multiple_state[i].y) + ", " +
                                    "yaw: " + str(multi_state.multiple_state[i].yaw) + ", " +
                                    "linear velocity: " + str(multi_state.multiple_state[i].v))

        self.plot_map()
        plt.axis("equal")
        plt.pause(0.000001)

    def complete_plotter_callback(self, multi_state: MultiState, multi_traj: MultiplePaths):

        buf = np.zeros((robot_num, 2))
        for i in range(robot_num):
            buf[i, 0] = multi_state.multiple_state[i].x
            buf[i, 1] = multi_state.multiple_state[i].y

        self.states_x_buf = np.concatenate((self.states_x_buf, buf[:,0].reshape(robot_num,1)), axis=1)
        self.states_y_buf = np.concatenate((self.states_y_buf, buf[:,1].reshape(robot_num,1)), axis=1)

        if len(self.states_x_buf[0, :]) > config.trail_length or len(self.states_y_buf[0, :]) > config.trail_length:
            self.states_x_buf = np.delete(self.states_x_buf, 0, 1)
            self.states_y_buf = np.delete(self.states_y_buf, 0, 1)
        
        plt.cla()
        # for stopping simulation with the esc key.
        plt.gcf().canvas.mpl_connect(
            'key_release_event',
            lambda event: [exit(0) if event.key == 'escape' else None])
        
        for i in range(robot_num):

            self.plot_situation(multi_state.multiple_state[i], multi_traj.multiple_path[i], 
                                self.states_x_buf[i, :], self.states_y_buf[i, :])
            if debug:
                self.get_logger().info("robot" + str(i) + ", x: " + str(multi_state.multiple_state[i].x) + ", " +
                                    "y: " + str(multi_state.multiple_state[i].y) + ", " +
                                    "yaw: " + str(multi_state.multiple_state[i].yaw) + ", " +
                                    "linear velocity: " + str(multi_state.multiple_state[i].v))

        self.plot_map()
        plt.axis("equal")
        plt.pause(0.000001)
            
        # print(time.time()-debug_time)
        # debug_time = time.time()

    def plot_situation(self, state: FullState, trajectory, state_buf_x, state_buf_y):
        if plot_traj:
            self.plot_path(trajectory)
            plt.scatter(state_buf_x[:], state_buf_y[:], marker='.', s=4)
            plt.plot(state.x, state.y, 'b.')
        self.plot_robot(state)


    def plot_robot(self, fullstate: FullState):
        self.plot_rect(fullstate.x, fullstate.y, fullstate.yaw, config)
        self.plot_cs_robot(fullstate.x, fullstate.y, fullstate.yaw, length=2)
        self.plot_arrow(fullstate.x, fullstate.y, fullstate.yaw + fullstate.delta, length=4)

    def plot_map(self):
        corner_x = [-self.width/2.0, self.width/2.0, self.width/2.0, -self.width/2.0, -self.width/2.0]
        corner_y = [self.heigth/2.0, self.heigth/2.0, -self.heigth/2.0, -self.heigth/2.0, self.heigth/2.0]

        plt.plot(corner_x, corner_y)

    def plot_path(self, path: Path):
        x = []
        y = []
        for coord in path.path:
            x.append(coord.x)
            y.append(coord.y)
        plt.scatter(x, y, marker='.', s=10)
        plt.scatter(x[0], y[0], marker='x', s=20)


    def plot_arrow(self, x, y, yaw, length=0.5, width=0.1):  # pragma: no cover
        plt.arrow(x, y, length * math.cos(yaw), length * math.sin(yaw),
                head_length=width, head_width=width)
    
    def plot_cs_robot(self, x, y, yaw, length=1, width=0.1):  # pragma: no cover
        plt.arrow(x, y, length * math.cos(yaw), length * math.sin(yaw),
                head_length=width, head_width=width)
        plt.arrow(x, y, length * -math.sin(yaw), length * math.cos(yaw),
                head_length=width, head_width=width)
        
    def plot_rect(self, x, y, yaw, config):  # pragma: no cover
        outline = np.array([[-config.robot_length / 2, config.robot_length / 2,
                                (config.robot_length / 2), -config.robot_length / 2,
                                -config.robot_length / 2],
                            [config.robot_width / 2, config.robot_width / 2,
                                - config.robot_width / 2, -config.robot_width / 2,
                                config.robot_width / 2]])
        Rot1 = np.array([[math.cos(yaw), math.sin(yaw)],
                            [-math.sin(yaw), math.cos(yaw)]])
        outline = (outline.T.dot(Rot1)).T
        outline[0, :] += x
        outline[1, :] += y
        plt.plot(np.array(outline[0, :]).flatten(),
                    np.array(outline[1, :]).flatten(), "-k")
        
def main(args=None):
    rclpy.init(args=args)

    node = Plotter()
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()

# colcon build --symlink-install to be able to run the node without building it
# or
# colcon build in the source file and the source ~/.bashrc !!!