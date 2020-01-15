from github import Github
from github.GithubException import UnknownObjectException


class GithubImport:
    def __init__(self, access_token, repository):
        self.github = Github(access_token)
        try:
            self.repo = self.github.get_repo(repository)
        except UnknownObjectException:
            raise Exception("Failed to get the repository '{}'".format(args.repository))
        
