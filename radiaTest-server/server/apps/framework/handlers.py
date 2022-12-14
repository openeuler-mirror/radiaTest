from flask import jsonify

from server.model.framework import GitRepo
from server.utils.response_util import RET


class GitRepoHandler:
    @staticmethod
    def get_git_repo(query, filter_params: list):
        if query.name:
            filter_params.append(
                GitRepo.name.like(f'%{query.name}%')
            )
        if query.git_url:
            filter_params.append(
                GitRepo.git_url.like(f'%{query.git_url}%')
            )
        if query.sync_rule:
            filter_params.append(
                GitRepo.sync_rule == query.sync_rule
            )
        if query.framework_id:
            filter_params.append(
                GitRepo.framework_id == query.framework_id
            )

        git_repos = GitRepo.query.filter(*filter_params).all()
        if not git_repos:
            return jsonify(error_code=RET.OK, error_msg="OK", data=[])

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[
                _git_repo.to_json() for _git_repo in git_repos
            ]
        )