# Copyright 2014 Google.
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
"""
Optimizer module.

It contains functions that allow to find and score encodings that will
perform highly on the score function.
"""

import encoder
import os
import score_tools

class Optimizer(object):
  """Optimizer class.

  An optimizer object contains:
  - A codec.
  - A video file set, with associated target bitrates.
  - A set of pre-executed encodings (the cache).
  - A score function.

  One should be able ask an optimizer to find the parameters that give the
  best result on the score function for that codec."""
  def __init__(self, codec, file_set=None,
               cache_class=None, score_function=None):
    self.context = encoder.Context(codec,
                                   cache_class or encoder.EncodingDiskCache)
    self.file_set = file_set
    self.score_function = score_function or score_tools.ScorePsnrBitrate

  def Score(self, encoding, scoredir=None):
    if scoredir is None:
      result = encoding.result
    else:
      result = self.context.cache.ReadEncodingResult(encoding,
          scoredir=scoredir)
    # Temporary hack because there are so many stored clips without cliptime
    # information:
    if encoding.result and not 'cliptime' in encoding.result:
      encoding.result['cliptime'] = encoding.videofile.ClipTime()
    return self.score_function(encoding.bitrate, result)

  def BestEncoding(self, bitrate, videofile):
    encodings = self.AllScoredEncodings(bitrate, videofile)
    if encodings:
      return max(encodings, key=self.Score)
    else:
      return self.context.codec.StartEncoder(self.context).Encoding(bitrate,
                                                                    videofile)

  def AllScoredEncodings(self, bitrate, videofile):
    return self.context.cache.AllScoredEncodings(bitrate, videofile)

  def BestUntriedEncoding(self, bitrate, videofile):
    """Attempts to guess the best untried encoding for this file and rate."""
    # Randomly vary some parameters and see if things improve.
    # This is the final fallback.
    encodings = self.BestEncoding(bitrate, videofile).SomeUntriedVariants()
    for encoding in encodings:
      if not encoding.Result():
        return encoding
    return None


class FileAndRateSet(object):
  def __init__(self):
    self.rates_and_files = set()

  def AddFilesAndRates(self, filenames, rates, basedir=None):
    for rate in rates:
      for filename in filenames:
        if basedir:
          self.rates_and_files.add((rate, os.path.join(basedir, filename)))
        else:
          self.rates_and_files.add((rate, filename))

  def AllFilesAndRates(self):
    """Returns all rate/file pairs"""
    return list(self.rates_and_files)

  def AllRatesForFile(self, filename_to_find):
    """Returns a list of all rates for a specific filename."""
    rates = set()
    for rate, filename in self.AllFilesAndRates():
      if filename == filename_to_find:
        rates.add(rate)
    return list(rates)
