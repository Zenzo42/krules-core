# Copyright 2019 The KRules Authors
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import socket

logger = logging.getLogger("__router__")


class DispatchPolicyConst:
    DEFAULT = "default"
    ALWAYS = "always"
    NEVER = "never"
    DIRECT = "direct"


class MessageRouter(object):

    def __init__(self):
        self._callables = {}

    def register(self, rule, type):
        logger.debug("register {0} for {1}".format(rule, type))
        if type not in self._callables:
            self._callables[type] = []
        self._callables[type].append(rule._process)

    def unregister(self, type):
        logger.debug("unregister event {}".format(type))
        count = 0
        if type in self._callables:
            for r in self._callables[type]:
                count += 1
            del self._callables[type]
        return count

    def unregister_all(self):
        count = 0
        types = tuple(self._callables.keys())
        for type in types:
            count += self.unregister(type)
        return count

    def route(self, type, subject, payload, dispatch_policy=DispatchPolicyConst.DEFAULT):

        if isinstance(subject, str):
            # NOTE: this should have already happened if we want to take care or event info
            from krules_core.providers import subject_factory
            subject = subject_factory(subject)

        from ..providers import message_dispatcher_factory

        _callables = self._callables.get(type, None)

        #        try:
        if not dispatch_policy == DispatchPolicyConst.DIRECT:
            if _callables is not None:
                for _callable in _callables:
                    _callable(type, subject, payload)
        #        finally:
        #            subject.store()

        # TODO: unit test (policies)
        if dispatch_policy != DispatchPolicyConst.NEVER and _callables is None \
                and dispatch_policy == DispatchPolicyConst.DEFAULT \
                or dispatch_policy == DispatchPolicyConst.ALWAYS \
                or dispatch_policy == DispatchPolicyConst.DIRECT:
            logger.debug("dispatch {} to {} with payload {}".format(type, subject, payload))
            return message_dispatcher_factory().dispatch(type, subject, payload)
