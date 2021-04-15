from requests.packages.urllib3.util.retry import Retry
from github import Github, enable_console_debug_logging
from github.GithubException import UnknownObjectException
from time import sleep
import requests
from .utils import get_request_json
from copy import deepcopy


class GithubImport:
    def __init__(self, access_token, repository, debug=False):
        if debug:
            enable_console_debug_logging()
        self.access_token = access_token
        retry = Retry(
            total=30,
            connect=5,
            read=5,
            backoff_factor=0.5,
            status_forcelist=(500, 502, 503, 504)
        )
        self.github = Github(access_token, timeout=30, retry=retry, per_page=300)
        try:
            self.repo = self.github.get_repo(repository)
        except UnknownObjectException:
            raise Exception("Failed to get the repository '{}'".format(repository))

    def get_repo_full_name(self):
        return self.repo.full_name

    def get_remaining_rate_limit(self):
        return self.github.rate_limiting[0]

    def get_issues_count(self):
        return self.repo.get_issues(state="all").totalCount

    def get_pulls_count(self):
        return self.repo.get_pulls(state="all").totalCount

    def get_issues(self):
        issues = self.repo.get_issues(state="all")
        return {x.number: x for x in issues}

    def get_pulls(self):
        pulls = self.repo.get_pulls(state="all")
        return {x.number: x for x in pulls}

    def get_gist_by_description(self, description):
        return next(
            (
                x for x in self.github.get_user().get_gists()
                if x.description == description
            ),
            None
        )

    def get_or_create_gist_by_description(self, gist_data):
        gist = self.get_gist_by_description(gist_data["description"])
        if gist is None:
            gist = self.github.get_user().create_gist(
                False,
                gist_data["files"],
                gist_data["description"]
            )
        else:
            gist.edit(gist_data["description"], gist_data["files"])
        return gist

    def create_issue_with_comments(self, issue_data):
        """
        Push a single issue to GitHub.
        Importing via GitHub's normal Issue API quickly triggers anti-abuse rate
        limits. So we use their dedicated Issue Import API instead:
        https://gist.github.com/jonmagic/5282384165e0f86ef105
        https://github.com/nicoddemus/bitbucket_issue_migration/issues/1
        """
        url = "https://api.github.com/repos/{repo}/import/issues".format(
            repo=self.get_repo_full_name())
        headers = {
            "Authorization": "token {}".format(self.access_token),
            "Accept": "application/vnd.github.golden-comet-preview+json"
        }
        res = requests.post(url, json=issue_data, headers=headers)
        if not res.ok:
            res.raise_for_status()
        import_data = res.json()
        import_status = import_data["status"]
        delay = 1
        while import_status == "pending":
            print("Waiting...")
            sleep(delay)
            delay = min(5, delay + 1)
            import_data = get_request_json(import_data["url"], headers=headers)
            import_status = import_data["status"]

        if import_status != "imported":
            print("Warning: import status is '{}'.".format(import_status))
        if import_status == "failed":
            print("Retrying...".format(import_status))
            self.slow_create_issue_with_comments(issue_data)

    def update_issue_comments(self, issue, comments_data):
        issue_id = issue.number
        num_comments = len(comments_data)
        existing_comments = list(issue.get_comments())

        # Create or update comments
        for comment_num, comment_data in enumerate(comments_data):
            print("Set comment {}/{} of github issue #{}...".format(comment_num + 1, num_comments, issue_id))
            comment_body = comment_data["body"]
            if comment_num < len(existing_comments):
                existing_comments[comment_num].edit(comment_body)
            else:
                issue.create_comment(comment_body)

        # Delete comments in excess
        comments_to_delete = existing_comments[num_comments:]
        for i, gcomment in enumerate(comments_to_delete):
            print("Delete extra gituhb comment {}/{} of issue #{}...".format(i + 1, len(comments_to_delete), issue_id))
            gcomment.delete()

    def update_issue_with_comments(self, issue, issue_data):
        meta = issue_data["issue"]
        issue.edit(
            title=meta["title"],
            body=meta["body"],
            labels=meta["labels"],
            state="closed" if meta["closed"] else "open",
            assignees=[] if meta["assignee"] is None else [meta["assignee"]]
        )
        self.update_issue_comments(issue, issue_data["comments"])

    def slow_create_issue_with_comments(self, issue_data):
        meta = issue_data["issue"]
        issue = self.repo.create_issue(
            title=meta["title"],
            body=meta["body"],
            labels=meta["labels"],
            assignees=[] if meta["assignee"] is None else [meta["assignee"]]
        )
        issue.edit(state="closed" if meta["closed"] else "open")
        self.update_issue_comments(issue, issue_data["comments"])

    def update_pull_comments(self, pull, comments_data):
        pull_id = pull.number
        num_comments = len(comments_data)
        existing_comments = list(pull.get_issue_comments())

        # Create or update comments
        for comment_num, comment_data in enumerate(comments_data):
            print("Set comment {}/{} of github pull request #{}...".format(comment_num + 1, num_comments, pull_id))
            comment_body = comment_data["body"]
            if comment_num < len(existing_comments):
                existing_comments[comment_num].edit(comment_body)
            else:
                pull.create_comment(comment_body)

        # Delete comments in excess
        comments_to_delete = existing_comments[num_comments:]
        for i, gcomment in enumerate(comments_to_delete):
            print("Delete extra gituhb comment {}/{} of pull request #{}...".format(i + 1, len(comments_to_delete), pull_id))
            gcomment.delete()

    def update_pull_with_comments(self, pull, pull_data):
        meta = pull_data["pull"]
        assert meta["head"] == pull.head.ref
        pull.edit(
            title=meta["title"],
            body=meta["body"],
            state=meta["state"],
            base=meta["base"],
        )
        pull.set_labels(*meta["labels"])
        pull.remove_from_assignees(*[
            x.name for x in pull.assignees
            if x.name not in meta["assignees"]
        ])
        pull.add_to_assignees(*meta["assignees"])
        (reviewers, team_reviewers) = pull.get_review_request()
        pull.delete_review_request(
            reviewers=[u.name for u in reviewers],
            team_reviewers=[u.name for u in team_reviewers]
        )
        pull.create_review_request(reviewers=meta["reviewers"])
        self.update_pull_comments(pull, pull_data["comments"])

    def create_pull_with_comments(self, pull_data):
        meta = pull_data["pull"]
        pull = self.repo.create_pull(
            title=meta["title"],
            body=meta["body"],
            base=meta["base"],
            head=meta["head"],
        )
        pull.set_labels(*meta["labels"])
        # Workaround for bug https://github.com/PyGithub/PyGithub/issues/1406
        deepcopy(pull).add_to_assignees(*meta["assignees"])
        if meta["reviewers"]:
            pull.create_review_request(reviewers=meta["reviewers"])
        for comment in pull_data["comments"]:
            pull.create_issue_comment(comment["body"])
