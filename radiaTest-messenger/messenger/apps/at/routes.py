import os
import requests

from flask import request, jsonify, current_app
from flask_restful import Resource
from flask_pydantic import validate

from messenger.schema.at import AtSchema
from messenger.utils.response_util import RET
from celeryservice.tasks import run_at
from messenger.utils.yaml_util import YamlUtil


class AtEvent(Resource):
    @validate()
    def post(self, body: AtSchema):
        _body = body.__dict__
        _user_id = _body.pop("user_id")
        try:
            iso_name = _body.get("release_url").split("/")[-1]
            iso_version = iso_name.replace(".iso", "")
            release_src_url = os.path.join(
                current_app.config.get("SOURCE_ISO_ADDR"),
                _body.get("release_url").split("dailybuild")[1].replace("//", "")
            ).replace(iso_name, "")
            resp = requests.get(release_src_url)
            if resp.status_code != 200:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg="release_url is not unreachable:{}".format(release_src_url)
                )
        except IndexError as e:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="release_url is not correct:{}".format(e)
            )

        yaml_util = YamlUtil(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config/at.yaml"
            )
        )
        at_base_info = yaml_util.get_yml_data(iso_version)
        if not at_base_info:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="there is no config in yaml for at"
            )
        _body.update({
            "pxe_repo_path": at_base_info.get("pxe_repo_path"),
            "pxe_tftpboot_path": at_base_info.get("pxe_tftpboot_path"),
            "pxe_efi_path": at_base_info.get("pxe_efi_path"),
            "test_suite": at_base_info.get("test_suite")
        })
        _user = {
            "user_id": _user_id,
            "auth": request.headers.get("authorization"),
        }

        run_at.delay(_body, _user)

        return jsonify(
            error_code=RET.OK,
            error_msg="succeed in creating the job for running at"
        )
