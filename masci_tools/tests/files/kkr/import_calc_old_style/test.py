#!/usr/bin/env python

from __future__ import absolute_import
from masci_tools.io.kkr_params import kkrparams

p = kkrparams(params_type='kkr')
p.read_keywords_from_inputcard()
