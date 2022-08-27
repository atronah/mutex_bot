from datetime import datetime

from telegram import User


class Resource(object):
    def __init__(self, name: str):
        self._name = name
        self._acquired: [datetime, None] = None
        self._user: [User, None] = None

    @property
    def name(self):
        return self._name

    @property
    def user(self):
        return self._user

    @property
    def acquired(self):
        return self._acquired

    @property
    def state_mark(self):
        return '🔴' if self._acquired else '⚪️'

    @property
    def display_name(self) -> str:
        acquiring_info = f'({self._user.name})' if self._acquired else ''
        return f'{self.state_mark} {self.name} {acquiring_info}'

    @property
    def data(self):
        return {
            'name': self.name,
            'acquired': self.acquired,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'fullname': self.user.full_name,
            }
        }

    def acquire(self, user):
        # type: (User) -> tuple[bool, tuple[str, dict] or None]
        if not self._acquired:
            self._acquired = datetime.now()
            self._user = user
            return True, None
        elif self._user == user:
            self._acquired = datetime.now()
            return True, ('common.re_acquired', {})
        return False, ('common.already_acquired_by', dict(username=self.user.name))

    def release(self, user):
        # type: (User) -> tuple[bool, tuple[str, dict] or None]
        if not self.acquired:
            return True, None
        elif self._user == user:
            self._acquired = None
            self._user = None
            return True, None
        return False, ('common.cannot_release_acquired_by', dict(username=self.user.name))

    def change_state(self, user):
        # type: (User) -> tuple[bool, tuple[str, dict] or None]
        return self.release(user) if self.acquired else self.acquire(user)

    def force_cleanup(self):
        self._acquired: [datetime, None] = None
        self._user: [User, None] = None


class Group(dict):
    def __init__(self, name):
        super().__init__()
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        resource_states = ''.join([r.state_mark for r in self.values()])
        return f'{resource_states} [{self._name}]'

    @property
    def resources(self):
        return self.values()

    @property
    def data(self):
        return {
            'name': self.name,
            'resources': dict(self)
        }

    def force_cleanup(self):
        for r in self.resources:
            r.force_cleanup()