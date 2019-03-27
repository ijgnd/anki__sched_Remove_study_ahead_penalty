# -*- coding: utf-8 -*-

# minimal fork by ijgnd of the add-on
#   Remove "study ahead" penalty (and sort by earliness) ×
#   https://ankiweb.net/shared/info/1607819937
# I just added one line for print-debugging to feel the difference to the built-in function. also renamed for 2.1.
# All credit for the add-on goes to the original author of the version for 2.0:
#   Anki user rjgoif
#   License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# ############### The purpose of this addon is to fix the way Anki handles late/early cards in filtered decks
# The default Anki algorithm penalizes studying a card early for whatever reason
#     (studying 1-year card a SINGLE day early can shorten the interval by >200 days!)
# It also can penalize studying a card late, again for unknown reasons
#     (depending on how late; strangely, after a certain "lateness" the penalty disappears)

# This addon fixes 3 things with filtered decks:
# 1. It eliminates the study-ahead penalty.
#     Study a card ahead and its new interval is either the old interval OR a new interval scaled to the number of days ahead, whichever is greater.
# 2. cards studied late are advanced by the ease × the old interval PLUS a bonus, i.e.
#     interval = oldInterval × ease + daysLate × mean(ease,120%)
# 3. sorts by relative overdueness AND relative-earliness when selected from the sort menu
#     Most-overdue (rel. to their interval) cards are first, then least-early (relative to their interval) cards are next.

# ################################
# regarding 2 above: the problem is in theory based on my analysis of the code, but I haven't seen the problem manifest IRL.
# there's likely some other nuance in the source that I missed so the problem doesn't really manifest.
# at any rate, Anki default behavior and this addon appear to behave the same way.
# I wrote the code before I realized this so it's staying for now as I think my formula is more intuitive


import time
import random
import itertools
from operator import itemgetter
from heapq import *

from anki.utils import ids2str, intTime, fmtTimeSpan
from anki.lang import _
from anki.consts import *
from anki.hooks import wrap

from anki.sched import Scheduler


def my_dynIvlBoost(self, card, _old):
    builtinivl = _old(self,card)
    assert card.odid and card.type == 2
    assert card.factor
    elapsed = card.ivl - (card.odue - self.today)
    if elapsed < card.ivl:
        # if you are studying the card early, base the new interval on the number of days that have passed.
        factor = card.factor/1000
        ivl = int(max(card.ivl, elapsed * factor, 1))
    else:
        # if studying the card on time or late, give a bonus for extra days that scales with ease
        factor = card.factor/1000
        bonusFactor = ((card.factor/1000)+1.2)/2
        ivl = int(card.ivl * factor + bonusFactor * (elapsed - card.ivl), 1)
    conf = self._revConf(card)
    ahead_addon_mod_ivl =  min(conf['maxIvl'], ivl)
    print('builtinivl: ' + str(builtinivl) + '   ahead_addon_mod_ivl: ' + str(ahead_addon_mod_ivl))
    return ahead_addon_mod_ivl


def my_dynOrder(self, o, l):
    if o == DYN_OLDEST:
        t = "c.mod"
    elif o == DYN_RANDOM:
        t = "random()"
    elif o == DYN_SMALLINT:
        t = "ivl"
    elif o == DYN_BIGINT:
        t = "ivl desc"
    elif o == DYN_LAPSES:
        t = "lapses desc"
    elif o == DYN_ADDED:
        t = "n.id"
    elif o == DYN_REVADDED:
        t = "n.id desc"
    elif o == DYN_DUE:
        t = "c.due"
    elif o == DYN_DUEPRIORITY:
        print('due priori')
        t = "(case when queue=2 and due <= %d then (ivl / cast(%d-due+0.001 as real)) else (100000 + ivl / cast(%d-due+0.001 as real)) end)" % (
                self.today, self.today, self.today)
    else:
        # if we don't understand the term, default to due order
        t = "c.due"
    return t + " limit %d" % l


Scheduler._dynIvlBoost = wrap(Scheduler._dynIvlBoost, my_dynIvlBoost, "around")
Scheduler._dynOrder = wrap(Scheduler._dynOrder, my_dynOrder)
