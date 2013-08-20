class ActionResult(object):
    def __init__(self, slave, action, state="pending"):
        self.slave = slave
        self.action = action
        self._state = state
        self._msg = "in progress"

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    @property
    def msg(self):
        return self._msg

    @msg.setter
    def msg(self, msg):
        self._msg = msg