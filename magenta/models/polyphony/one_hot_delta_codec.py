# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Converts PolyphonicSequence objects into input features and labels."""

import sequence
import numpy as np
import itertools

def encode(polyphonic_sequence):
  seq = polyphonic_sequence.get_events()

  # TODO: generalize to work with inputs that have different high/low notes
  seq_without_special_events = seq[seq >= 0]
  # TODO: could be more clever about calculating max_delta so we actually find
  # what the largest change between notes is, resulting in a probably-smaller
  # one-hot array.
  max_delta = (
      seq_without_special_events.max() - seq_without_special_events.min())
  one_hot_delta_length = (max_delta * 2) + 1 + sequence.NUM_SPECIAL_EVENTS

  voice_pairings = list(itertools.combinations(range(seq.shape[1]), 2))
  one_hot_voice_relation_length = 12 + max_delta + 1

  one_hot_length = ((one_hot_delta_length * seq.shape[1]) +
    (one_hot_voice_relation_length * len(voice_pairings)))

  # TODO: generalize to work with inputs that have different numbers of voices
  inputs = np.zeros((seq.shape[0], one_hot_length), dtype=float)
  # TODO: should i use pitches for the labels or deltas?
  # labels is steps x voices and holds pitches and special events
  labels = np.zeros((seq.shape[0], seq.shape[1]), dtype=int)

  last_notes = [None] * seq.shape[1]
  active_notes = [None] * seq.shape[1]
  for step in range(seq.shape[0]):
    for voice, pitch in enumerate(seq[step]):
      if pitch == sequence.NO_EVENT:
        active_notes[voice] = None
      elif pitch >= 0:
        active_notes[voice] = pitch

      offset = voice * one_hot_delta_length
      if pitch < 0:
        inputs[step][offset + pitch + sequence.NUM_SPECIAL_EVENTS] = 1
      else:
        delta = 0
        if last_notes[voice] is not None:
          delta = pitch - last_notes[voice]

        last_notes[voice] = pitch
        one_hot_delta = max_delta + delta
        inputs[step][offset + one_hot_delta + sequence.NUM_SPECIAL_EVENTS] = 1

      if step > 0:
        labels[step - 1][voice] = pitch + sequence.NUM_SPECIAL_EVENTS
      if step == seq.shape[0] - 1:
        labels[step][voice] = sequence.NUM_SPECIAL_EVENTS + sequence.NO_EVENT
    for i, voice_pair in enumerate(voice_pairings):
      if not active_notes[voice_pair[0]] or not active_notes[voice_pair[1]]:
        continue
      distance = abs(active_notes[voice_pair[0]] - active_notes[voice_pair[1]])
      offset = ((seq.shape[1] * one_hot_delta_length) +
          (i * one_hot_voice_relation_length))
      # distance ignoring octaves
      inputs[step][offset + (distance % 12)] = 1
      # absolute distance
      inputs[step][offset + 12 + distance] = 1

  return inputs, labels

def as_sequence_example(polyphonic_sequence):
  inputs, labels = encode(polyphonic_sequence)

  input_features = [
      tf.train.Feature(float_list=tf.train.FloatList(value=input_))
      for input_ in inputs]
  label_features = [
      tf.train.Feature(int64_list=tf.train.Int64List(value=[label]))
      for label in labels]
  feature_list = {
      'inputs': tf.train.FeatureList(feature=input_features),
      'labels': tf.train.FeatureList(feature=label_features)
  }
  feature_lists = tf.train.FeatureLists(feature_list=feature_list)
  return tf.train.SequenceExample(feature_lists=feature_lists)

