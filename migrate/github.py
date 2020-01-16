from github import Github
from github.GithubException import UnknownObjectException


class GithubImport:
    def __init__(self, access_token, repository):
        self.github = Github(access_token)
        self.issue_attachments_gist = {}
        try:
            self.repo = self.github.get_repo(repository)
        except UnknownObjectException:
            raise Exception("Failed to get the repository '{}'".format(args.repository))

    def get_remaining_rate_limit(self):
        return self.github.rate_limiting[0]

    def get_gist_by_description(self, description):
        return next(
            (
                x for x in self.github.get_user().get_gists()
                if x.description == description
            ),
            None
        )

    def set_issue_attachments_gist(self, issue_id, gist):
        self.issue_attachments_gist[issue_id] = gist

    def get_issue_attachments_gist(self, issue_id):
        return self.issue_attachments_gist[issue_id]

    def get_or_create_gissue(self, issue_id):
        try:
            gissue = self.repo.get_issue(issue_id)
        except UnknownObjectException:
            gissue = self.repo.create_issue("[issue #{}]".format(issue_id))
        assert gissue.number == issue_id
        return gissue
