# coding=utf-8
# Copyright 2018 The Tensor2Tensor Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for openai gym."""

# Dependency imports

import gym

import numpy as np

import six

from tensor2tensor.data_generators import image_utils
from tensor2tensor.rl.envs import simulated_batch_env


class WarmupWrapper(gym.Wrapper):
  """Warmup wrapper."""

  def __init__(self, env, warm_up_examples=0):
    gym.Wrapper.__init__(self, env)
    self.warm_up_examples = warm_up_examples
    self.warm_up_action = 0
    self.observation_space = gym.spaces.Box(
        low=0, high=255, shape=(210, 160, 3), dtype=np.uint8)

  def get_starting_data(self):
    self.reset()
    starting_observations, starting_actions, starting_rewards = [], [], []
    for _ in range(
        simulated_batch_env.SimulatedBatchEnv.NUMBER_OF_HISTORY_FRAMES):
      observation, rew, _, _ = self.env.step(self.warm_up_action)
      starting_observations.append(observation)
      starting_rewards.append(rew)
      starting_actions.append(self.warm_up_action)

    return starting_observations, starting_actions, starting_rewards

  def step(self, ac):
    action = ac
    return self.env.step(action)

  def reset(self, **kwargs):
    self.env.reset()
    observation = None
    for _ in range(self.warm_up_examples):
      observation, _, _, _ = self.env.step(self.warm_up_action)

    return observation


class PongWrapper(WarmupWrapper):
  """Pong Wrapper."""

  def __init__(self, env, warm_up_examples=0,
               action_space_reduction=False,
               reward_skip_steps=0,
               big_ball=False):
    super(PongWrapper, self).__init__(env, warm_up_examples=0)
    self.action_space_reduction = action_space_reduction
    if self.action_space_reduction:
      self.action_space = gym.spaces.Discrete(2)
    self.warm_up_examples = warm_up_examples
    self.observation_space = gym.spaces.Box(
        low=0, high=255, shape=(210, 160, 3), dtype=np.uint8)
    self.reward_skip_steps = reward_skip_steps
    self.big_ball = big_ball

  def step(self, ac):
    action = ac
    if self.action_space_reduction:
      action = 2 if int(ac) == 0 else 5
    ob, rew, done, info = self.env.step(action)
    ob = self.process_observation(ob)
    if rew != 0 and self.reward_skip_steps != 0:
      for _ in range(self.reward_skip_steps):
        self.env.step(0)
    return ob, rew, done, info

  def reset(self, **kwargs):
    observation = super(PongWrapper, self).reset(**kwargs)
    observation = self.process_observation(observation)
    return observation

  def process_observation(self, obs):
    if self.big_ball:
      pos = PongWrapper.find_ball(obs)
      if pos is not None:
        x, y = pos
        obs[x-5:x+5, y-5:y+5, :] = 255

    return obs

  @staticmethod
  def find_ball(obs, default=None):
    ball_area = obs[37:193, :, 0]
    res = np.argwhere(ball_area == 236)
    if not res:
      return default
    else:
      x, y = res[0]
      x += 37
      return x, y


def wrapped_pong_factory(warm_up_examples=0, action_space_reduction=False,
                         reward_skip_steps=0, big_ball=False):
  env = gym.make("PongDeterministic-v4")
  env = env.env  # Remove timelime wrapper.
  env = PongWrapper(env, warm_up_examples=warm_up_examples,
                    action_space_reduction=action_space_reduction,
                    reward_skip_steps=reward_skip_steps,
                    big_ball=big_ball)
  return env


gym.envs.register(id="T2TPongWarmUp20RewSkip1000Steps-v1",
                  entry_point=lambda: wrapped_pong_factory(  # pylint: disable=g-long-lambda
                      warm_up_examples=20, reward_skip_steps=15),
                  max_episode_steps=200)


def encode_image_to_png(image):
  encoded = six.next(
      image_utils.encode_images_as_png([image]))
  return encoded
