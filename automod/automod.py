#!/usr/bin/env python

from .moderator import ModClient as Mod
from .audio import AudioClient as Audio
from .chat import ChatClient as Chat

set_interval = Mod.set_interval


class AutoModClient(Mod, Chat, Audio):

    def __init__(self):
        super().__init__()

