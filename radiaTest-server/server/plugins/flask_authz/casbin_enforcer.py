# Copyright 2024 Ethan-Zhang.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Original code modified by Ethan-Zhang <ethanzhang55@outlook.com>
#
# Copyright 2017 The casbin Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
flask-casbin: Flask module for using Casbin with flask apps
"""
import re
import shlex
from functools import wraps
from abc import ABC
from abc import abstractmethod

import casbin
from flask import request, jsonify


from server.utils.response_util import RET
from .utils import authorization_decoder, UnSupportedAuthType


class Filter:
    def __init__(self, ptype=None, **kwargs) -> None:
        self.ptype = ptype or []
        self.v0 = kwargs.get("v0") if kwargs.get("v0") else []
        self.v1 = kwargs.get("v1") if kwargs.get("v1") else []
        self.v2 = kwargs.get("v2") if kwargs.get("v2") else []
        self.v3 = kwargs.get("v3") if kwargs.get("v3") else []
        self.v4 = kwargs.get("v4") if kwargs.get("v4") else []
        self.v5 = kwargs.get("v5") if kwargs.get("v5") else []


class CasbinEnforcer:
    """
    Casbin Enforce decorator
    """

    e = None

    def __init__(self, app=None, adapter=None, watcher=None):
        """
        Args:
            app (object): Flask App object to get Casbin Model
            adapter (object): Casbin Adapter
        """
        self.app = app
        self.adapter = adapter
        self.e = None
        self.watcher = watcher
        self._owner_loader = None
        self.user_name_headers = None
        if self.app is not None:
            self.init_app(self.app)

    @staticmethod
    def sanitize_group_headers(headers_str, delimiter=",") -> list:
        """
        Sanitizes group header string so that it is easily parsable by enforcer
        removes extra spaces, and converts comma delimited or white space
        delimited list into a list.

        Default delimiter: "," (comma)

        Returns:
            list
        """
        check_single_quote = (headers_str.startswith("'") and headers_str.endswith("'"))
        check_double_quote = (headers_str.startswith('"') and headers_str.endswith('"'))
        if delimiter == " " and (check_single_quote or check_double_quote):
            return [
                string.strip() for string in shlex.split(headers_str) if string != ""
            ]
        return [
            string.strip() for string in headers_str.split(delimiter) if string != ""
        ]

    def init_app(self, app, adapter):
        self.app = app
        self.adapter = adapter
        self.e = casbin.Enforcer(app.config.get("CASBIN_MODEL"), self.adapter)
        if self.watcher:
            self.e.set_watcher(self.watcher)
        self.user_name_headers = app.config.get("CASBIN_USER_NAME_HEADERS", None)

    def set_watcher(self, watcher):
        """
        Set the watcher to use with the underlying casbin enforcer
        Args:
            watcher (object):
        Returns:
            None
        """
        self.e.set_watcher(watcher)

    def owner_loader(self, callback):
        """
        This sets the callback for get owner. The
        function return a owner object, or ``None``

        :param callback: The callback for retrieving a owner object.
        :type callback: callable
        """
        self._owner_loader = callback
        return callback

    def enforcer(self, func=None, delimiter=","):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from server.utils.message_util import MessageManager

            # Set resource URI from request
            uri = str(request.path)
            # Extract domain fo the resource URI
            pattern = r'^/api/v[0-9]+/([^/]+)(?:/.*)?$'
            result = re.match(pattern, uri)
            if not result:
                return jsonify(error_code=RET.BAD_REQ_ERR, error_msg="resource uri is not valid")
            dom = result.group(1)

            act = str(request.method).upper()

            _all_roles_filter = Filter(ptype=['g'])
            _cur_dom_filter = Filter(ptype=['p'], v2=[act], v4=[dom])
            self.e.load_filtered_policy(_all_roles_filter)
            self.e.load_increment_filtered_policy(_cur_dom_filter)

            if self.e.watcher and self.e.watcher.should_reload():
                self.e.watcher.update_callback()
            # String used to hold the owners user name for audit logging
            owner_audit = ""

            # Check sub, obj act against Casbin polices
            self.app.logger.debug(
                "Enforce Headers Config: %s\nRequest Headers: %s"
                % (self.app.config.get("CASBIN_OWNER_HEADERS"), request.headers)
            )

            # Get owner from owner_loader
            if self._owner_loader:
                self.app.logger.info("Get owner from owner_loader")
                for owner in self._owner_loader():
                    owner = owner.strip('"') if isinstance(owner, str) else owner

                    if self.e.enforce(owner, uri, act, dom):
                        return func(*args, **kwargs)

            for header in list(map(str.lower, self.app.config.get("CASBIN_OWNER_HEADERS"))):
                if header in request.headers:
                    # Make Authorization Header Parser standard
                    if header == "authorization":
                        # Get Auth Value then decode and parse for owner
                        try:
                            owner = authorization_decoder(
                                self.app.config, request.headers.get(header)
                            )
                        except UnSupportedAuthType:
                            # Continue if catch unsupported type in the event of
                            # Other headers needing to be checked
                            self.app.logger.info(
                                "Authorization header type requested for "
                                "decoding is unsupported by flask-casbin at this time"
                            )
                            continue
                        except Exception as e:
                            self.app.logger.info(e)
                            continue

                        if self.user_name_headers and header in map(
                                str.lower, self.user_name_headers
                        ):
                            owner_audit = owner
                        if self.e.enforce(owner, uri, act, dom):
                            self.app.logger.info(
                                "access granted: method: %s resource: %s%s"
                                % (
                                    request.method,
                                    uri,
                                    ""
                                    if not self.user_name_headers and owner_audit != ""
                                    else " to user: %s" % owner_audit,
                                )
                            )
                            return func(*args, **kwargs)
                    else:
                        # Split header by ',' in case of groups when groups are
                        # sent "group1,group2,group3,..." in the header
                        for owner in self.sanitize_group_headers(
                                request.headers.get(header), delimiter
                        ):
                            self.app.logger.debug(
                                "Enforce against owner: %s header: %s"
                                % (owner.strip('"'), header)
                            )
                            if self.user_name_headers and header in map(
                                    str.lower, self.user_name_headers
                            ):
                                owner_audit = owner
                            if self.e.enforce(owner.strip('"'), uri, act, dom):
                                self.app.logger.info(
                                    "access granted: method: %s resource: %s%s"
                                    % (
                                        request.method,
                                        uri,
                                        ""
                                        if not self.user_name_headers
                                           and owner_audit != ""
                                        else " to user: %s" % owner_audit,
                                    )
                                )
                                return func(*args, **kwargs)

            _api = MessageManager().get_cur_api_msg(uri, str(request.method))
            if not _api:
                self.app.logger.error(
                    "Unauthorized attempt: method: %s resource: %s%s"
                    % (
                        request.method,
                        uri,
                        ""
                        if not self.user_name_headers and owner_audit != ""
                        else " by user: %s" % owner_audit,
                    )
                )
                return jsonify(error_code=RET.UNAUTHORIZE_ERR, error_msg="Unauthorized")
            else:
                if request.get_data() == '':
                    _api["body"] = ""
                else:
                    _api["body"] = request.get_data() if not request.get_json() else request.get_json()
                if isinstance(_api["body"], bytes):
                    _api["body"] = str(_api["body"], "utf-8")
                try:
                    return jsonify(error_code=RET.UNAUTHORIZE_ERR, error_msg=MessageManager().run(_api))
                except RuntimeError as e:
                    self.app.logger.error(str(e))
                    return jsonify(error_code=RET.UNAUTHORIZE_ERR, error_msg="Unauthorized")

        return wrapper

    def manager(self, func):
        """Get the Casbin Enforcer Object to manager Casbin"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(self.e, *args, **kwargs)

        return wrapper


class Watcher(ABC):
    """
    Watcher interface as it should be implemented for flask-casbin
    """

    @abstractmethod
    def update(self):
        """
        Watcher interface as it should be implemented for flask-casbin
        Returns:
            None
        """
        pass

    @abstractmethod
    def set_update_callback(self):
        """
        Set the update callback to be used when an update is detected
        Returns:
            None
        """
        pass

    @abstractmethod
    def should_reload(self):
        """
        Method which checks if there is an update necessary for the casbin
        roles. This is called with each flask request.
        Returns:
            Bool
        """
        pass
