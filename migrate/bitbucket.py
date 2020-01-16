import json
from zipfile import ZipExtFile
import requests


def get_request_content(url):
    res = requests.get(url)
    if not res.ok:
        res.raise_for_status()
    return res.text


def get_request_json(url):
    res = requests.get(url)
    if not res.ok:
        res.raise_for_status()
    return res.json()


def get_paginated_json(url):
    next_url = url

    while next_url is not None:
        result = get_request_json(next_url)
        next_url = result.get("next", None)
        for value in result["values"]:
            yield value


class BitbucketExport:
    def __init__(self, repository_name):
        self.repository_name = repository_name
        self.repo_url = "https://api.bitbucket.org/2.0/repositories/" + repository_name

    def get_issues(self):
        print("Get all issues from '{}' on Bitbucket...".format(self.repository_name))
        issues = list(get_paginated_json(self.repo_url + "/issues"))
        issues.sort(key=lambda x: x["id"])
        return issues

    def get_issue_comments(self, issue_id):
        comments = list(get_paginated_json(self.repo_url + "/issues/" + str(issue_id) + "/comments"))
        comments.sort(key=lambda x: x["id"])
        return comments

    def get_issue_attachments(self, issue_id):
        attachments_query = get_paginated_json(self.repo_url + "/issues/" + str(issue_id) + "/attachments")
        attachments = { attachment["name"]: attachment for attachment in attachments_query }
        return attachments

    def get_issue_attachment_content(self, issue_id, attachment_name):
        print("get_issue_attachment_content({}, {})".format(issue_id, attachment_name))
        data = get_request_content(self.repo_url + "/issues/" + str(issue_id) + "/attachments/" + attachment_name)
        return data

    def get_pull_requests(self):
        print("Get all pull requests from '{}' on Bitbucket...".format(self.repository_name))
        issues = list(get_paginated_json(self.repo_url + "/pullrequests"))
        issues.sort(key=lambda x: x["id"])
        return issues

    def get_pull_requests_comments(self, pull_requests_id):
        comments = list(get_paginated_json(self.repo_url + "/pullrequests/" + str(pull_requests_id) + "/comments"))
        comments.sort(key=lambda x: x["id"])
        return comments
