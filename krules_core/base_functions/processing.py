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
import inspect
from collections.abc import Mapping

from krules_core.route.router import DispatchPolicyConst

from krules_core.base_functions import RuleFunctionBase, Filter


class Process(Filter):
    """

    *Extends* **Filter** *but does not return the given expression*
    *The best way to exploit it is to use it in combination with* `Argument Processors <https://intro.krules.io/ArgumentProcessors.html>`_.

    ::

        from krules_core.types import RULE_PROC_EVENT

        #...

        {
            # Supposing we want to store processed events with Django ORM
            rulename: "processed-rules",
            subscibre_to: RULE_PROC_EVENT,
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    Process(
                        lambda payload:(
                            ProcessedEvent.objects.create(
                                rule_name=payload["name"],
                                type=payload["type"],
                                subject=payload["subject"],
                                event_info=payload["event_info"],
                                payload=payload["payload"],
                                time=payload["event_info"].get("time", datetime.now().isoformat()),
                                filters=payload["filters"],
                                processing=payload["processing"],
                                got_errors=payload["got_errors"],
                                processed=payload["processed"],
                                origin_id=payload["event_info"].get("originid", "-")
                            )
                        )
                    ),
                ]
            }
        }

    """
    def execute(self, value):
        """

        """
        super().execute(value)


## PAYLOAD FUNCTIONS ##############################################################


class SetPayloadProperties(RuleFunctionBase):
    """
    *Set the given properties in the payload, if some of that already exist will be overridden*

    ::

        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    SetPayloadProperties(  # Definition with a dictionary
                        **{
                            "has_admin_access": True,
                            "last_login": datetime.now()
                        }
                    )
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    SetPayloadProperties(  # Definition with named arguments
                        has_admin_access=False,
                        last_login=datetime.now()
                    )
                ]
            }
        },
    """

    def execute(self, **kwargs):
        """
        Args:
              **kwargs: Each named paramenter is the key and the value to update with.
        """
        for k, v in kwargs.items():
            self.payload[k] = v


class SetPayloadProperty(SetPayloadProperties):
    """
    *Extends* **SetPayload** *expecting a single property to set*

    ::

        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    SetPayloadProperty(
                        property_name="device_class",
                        value="heather"
                    )
                ]
            }
        },
    """

    def execute(self, property_name, value):
        """
        Args:
            property_name: Name of property which will be to set,
            value: Value to set.
        """
        super().execute(**{property_name: value})


## SUBJECT FUNCTIONS ################################################################


class SetSubjectProperty(RuleFunctionBase):
    """
    *Set a single property of the subject. By default, the property is reactive unless is muted (muted=True) or extended (extended=True)*

    ::

        {
            rulename: "set-device-class",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    SetSubjectProperty(
                        property_name="device_class",
                        value="heather"
                    )
                ]
            }
        },
        {
            rulename: "on-new-checkup-increment-counter",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    SetSubjectProperty(
                        property_name="checkup_cnt",
                        value=lambda x: x is None and 1 or x + 1
                    )
                ]
            }
        }

    """
    def execute(self, property_name, value, extended=False, muted=False, use_cache=True):
        """
        Args:
            property_name: Name of the property to set. It may or may not exist
            value: Value to set. It can be a callable and receives (optionally) the current property value.
                If the property does not exist yet, it receives None.
            extended: If True set an extended property instead a standard one. [default False]
            muted: If True no subject-property-changed will be raised after property setting. Note that extended
                properties are always muted so, if extended is True, this parameter will be ignored. [default False]
            use_cache: If False store the property value immediately on the storage, otherwise wait for the end of rule execution. [default False]
        """
        if extended:
            fn = lambda v: self.subject.set_ext(property_name, v, use_cache)
        else:
            fn = lambda v: self.subject.set(property_name, v, muted, use_cache)

        return fn(value)


class SetSubjectPropertyImmediately(SetSubjectProperty):
    """
    *Extends* **SetSubjectProperty** *setting a property directly to the storage without using the cache.
    This could be very helpful to avoid concurrency issues by avoiding running into inconsistencies during the execution.
    The extension's aim is to made code more readable.*
    """
    def execute(self, property_name, value, extended=False, muted=False, **kwargs):
        """

        """
        return super().execute(property_name, value, extended=extended, muted=muted, use_cache=False)


class SetSubjectExtendedProperty(SetSubjectProperty):
    """
    *Extends* **SetSubjectProperty** *setting an extended property of the subject. Note that* **muted** *is not
    present anymore in the arguments because an extended property is always muted.
    The extension's aim is to made code more readable.*
    """
    def execute(self, property_name, value, use_cache=True, **kwargs):
        """

        """
        return super().execute(property_name, value, extended=True, muted=True, use_cache=use_cache)


class SetSubjectProperties(RuleFunctionBase):
    """
    *Set multiple properties in subject from dictionary. This is allowed only by using cache and not for
    extended properties. Each property set in that way is muted but it is possible to unmute some of that using*
    **unmuted** *parameter*

    ::

        {
            rulename: "...",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    SetSubjectProperties(
                        props= lambda: {
                            "device_class": "heather",
                            "on_boarding_tm": datetime.now(),
                        },
                        unmuted=["heather"]
                    )
                    # Thanks to ArgumentProcessor we can use a lambda, without that on_boarding_tm
                    # would be always equal to the Rule instantiation's datetime while we need the execution's one.
                ]
            }
        }
    """

    def execute(self, props, unmuted=[]):
        """
        Args:
            props: The properties to set
            unmuted: List of property names for which emit property changed events
        """
        for name, value in props.items():
            self.subject.set(name, value, muted=name not in unmuted)


class StoreSubject(RuleFunctionBase):
    """
    *Flush the cache. Usually the cache is flushed at the end of the rules execution.*
    """

    def execute(self):
        self.subject.store()


class FlushSubject(RuleFunctionBase):
    """
    *Remove all subject's properties. It is important tho recall that a subject exists while it has at least a property,
    so* **remove all its properties means remove the subject itself**.

    ::

        {
            rulename: "on-user-unsubscribe-delete-subject",
            subscibre_to: "...",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    FlushSubject()
                ]
            }
        },

    """

    def execute(self):
        self.subject.flush()


#####################################################################################


class Route(RuleFunctionBase):
    """
    *Produce an event inside and/or outside the ruleset, for "sending outside" the event we mean to deliver it to the
    dispatcher component.
    By default an event is dispatched outside only if there is no handler defined in the current ruleset.
    However it is possible to change this behavior using* **dispatch_policy**.
    *Available choices are defined in* **krules_core.route.router.DispatchPolicyConst** *as:*
        - **DEFAULT**: *Dispatched outside only when no handler is found in current ruleset;*
        - **ALWAYS**: *Always dispatched outside even if an handler is found and processed in the current ruleset;*
        - **NEVER**: *Never dispatched outside;*
        - **DIRECT**: *Skip to search for a local handler and send outside directly.*

    ::

        from krules_core.route.router.DispatchPolicyConst import DEFAULT, ALWAYS, NEVER, DIRECT
        from krules_core.types import SUBJECT_PROPERTY_CHANGED

        # ...

        {
            rulename: "...",
            subscibre_to: "device-uploaded",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    Route(
                        subject=lambda payload: payload["device_id"],
                        payload=lambda payload: payload["device_data"],
                        type="device-added",
                        # no dispatch_policy is provided so will be used the DEFAULT one
                    ),
                ]
            }
        },
        {
            rulename: "...",
            subscibre_to: "device-upload-got-errors",
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    Route(
                        type="device-uploaded",
                        payload=lambda payload: payload["payload"]
                        dispatch_policy=NEVER
                        # no subject is provided so will be used the current one
                    )
                ]
            }
        },
        {
            rulename: "on-temp-change-propagate-event",
            subscibre_to: SUBJECT_PROPERTY_CHANGED,
            ruledata: {
                filters: [
                    ...
                ]
                processing: [
                    Route(
                        dispatch_policy=DIRECT
                        # In this case we don't specify neither type, nor subject, nor payload.
                        # We use dispatch_policy DIRECT to propagate the received event outside.
                    )
                ]
            }
        }

        # ...
        {
            rulename: "on-resource-event-switch-subject",
            subscribe_to: [
                "dev.knative.apiserver.resource.add",
                "dev.knative.apiserver.resource.update",
                "dev.knative.apiserver.resource.delete",
            ],
            ruledata: {
                processing: [
                    Route(
                        subject=lambda subject: "k8s:{}".format(subject.name),
                        type=lambda self: "k8s.resource.{}".format(self.type.split(".")[-1]),
                        dispatch_policy=DispatchPolicyConst.ALWAYS
                        # no payload is provided so will be used the current one
                    )
                ]
            }
        },
    """

    def execute(self, type=None, subject=None, payload=None, dispatch_policy=DispatchPolicyConst.DEFAULT):
        """
        Args:
            type: The event type. If None use current processing event type [default None]
            subject: The event subject. If None use the current subject [default None]
            payload: The event payload. If None use the current payload [default None]
            dispatch_policy: Define the event dispatch policy as explained before. [default DispatchPolicyConst.DEFAULT]
        """

        from krules_core.providers import event_router_factory
        if type is None:
            type = self.type
        if subject is None:
            subject = self.subject
        if payload is None:
            payload = self.payload

        event_router_factory().route(type, subject, payload, dispatch_policy=dispatch_policy)


class RaiseException(RuleFunctionBase):
    """
    *Force the given exception raising*

    ::

        from .my_custom_exceptions import UnexpectedPayload # supposing we defined a module with custom exceptions

        {
            rulename: "on-unexpected-payload-raise-exception",
            subscibre_to: "device-onboarded",
            ruledata: {
                filters: [
                    Return(lambda payload: "device_id" not in payload)
                ]
                processing: [
                    RaiseException(
                        UnexpectedPayload("device_id missing!")
                    )
                ]
            }
        },

    """

    def execute(self, ex):
        """
        Args:
            ex: The exception to be raised
        """

        raise ex

