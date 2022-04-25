"""flask-casbin: Flask module for using Casbin with flask apps
"""
from sqlite3 import adapt
import casbin
from flask import request, jsonify, g
from functools import partial, wraps
from abc import ABC
from abc import abstractmethod
import shlex

from .utils import authorization_decoder, UnSupportedAuthType
from server.utils.response_util import RET


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
            self.e.load_policy()
            if self.e.watcher and self.e.watcher.should_reload():
                self.e.watcher.update_callback()
            # String used to hold the owners user name for audit logging
            owner_audit = ""

            # Check sub, obj act against Casbin polices
            self.app.logger.debug(
                "Enforce Headers Config: %s\nRequest Headers: %s"
                % (self.app.config.get("CASBIN_OWNER_HEADERS"), request.headers)
            )
            # Set resource URI from request
            uri = str(request.path)

            # Get owner from owner_loader
            if self._owner_loader:
                self.app.logger.info("Get owner from owner_loader")
                for owner in self._owner_loader():
                    owner = owner.strip('"') if isinstance(owner, str) else owner
                    
                    if self.e.enforce(owner, uri, request.method):
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
                        if self.e.enforce(owner, uri, request.method):
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
                            if self.e.enforce(owner.strip('"'), uri, request.method):
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

            if request.get_data().decode() == '':
                _api = MessageManager().get_cur_api_msg(uri, str(request.method), request.get_data().decode())
            else:
                _api = MessageManager().get_cur_api_msg(uri, str(request.method), request.get_json())
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
                MessageManager().run(_api)
                return jsonify(error_code=RET.UNAUTHORIZE_ERR, error_msg="Unauthorized, Your request has been sent to the administrator for processing.")

        return wrapper

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
        if delimiter == " " and (
            (headers_str.startswith("'") and headers_str.endswith("'"))
            or (headers_str.startswith('"') and headers_str.endswith('"'))
        ):
            return [
                string.strip() for string in shlex.split(headers_str) if string != ""
            ]
        return [
            string.strip() for string in headers_str.split(delimiter) if string != ""
        ]

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
