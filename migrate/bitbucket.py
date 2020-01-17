from zipfile import ZipExtFile
from .utils import get_request_content, get_request_json

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

    def get_repo_full_name(self):
        return self.repository_name

    def get_issues(self):
        print("Get all bitbucket issues...")
        issues = list(get_paginated_json(self.repo_url + "/issues"))
        issues.sort(key=lambda x: x["id"])
        return issues

    def get_issue_comments(self, issue_id):
        comments = list(get_paginated_json(self.repo_url + "/issues/" + str(issue_id) + "/comments"))
        comments.sort(key=lambda x: x["id"])
        return comments

    def get_issue_activity(self, issue_id):
        activity = list(get_paginated_json(self.repo_url + "/issues/" + str(issue_id) + "/activity"))
        activity.sort(key=lambda x: x["id"])
        return activity

    def get_issue_attachments(self, issue_id):
        attachments_query = get_paginated_json(self.repo_url + "/issues/" + str(issue_id) + "/attachments")
        attachments = { attachment["name"]: attachment for attachment in attachments_query }
        return attachments

    def get_issue_attachment_content(self, issue_id, attachment_name):
        data = get_request_content(self.repo_url + "/issues/" + str(issue_id) + "/attachments/" + attachment_name)
        return data

    def get_simplified_pull_requests(self):
        print("Get all simplified bitbucket pull requests...")
        pull_requests = list(get_paginated_json(self.repo_url + "/pullrequests?state=MERGED&state=SUPERSEDED&state=OPEN&state=DECLINED"))
        pull_requests.sort(key=lambda x: x["id"])
        return pull_requests

    def get_pull_requests_count(self):
        pull_requests_page = get_request_json(self.repo_url + "/pullrequests?state=MERGED&state=SUPERSEDED&state=OPEN&state=DECLINED")
        return pull_requests_page["size"]

    def get_pull_request(self, pull_requests_id):
        pull_request = get_request_json(self.repo_url + "/pullrequests/" + str(pull_requests_id))
        return pull_request

    def get_pull_requests(self):
        pull_requests_count = self.get_pull_requests_count()
        print("Get all {} detailed bitbucket pull requests...".format(pull_requests_count))
        pull_requests = []
        for pull_request_id in range(1, pull_requests_count + 1):
            if pull_request_id % 10 == 0:
                print("{}/{}...".format(pull_request_id, pull_requests_count))
            pull_requests.append(self.get_pull_request(pull_request_id))
        return pull_requests

    def get_pull_request_comments(self, pull_requests_id):
        comments = list(get_paginated_json(self.repo_url + "/pullrequests/" + str(pull_requests_id) + "/comments"))
        comments.sort(key=lambda x: x["id"])
        return comments

    def get_pull_request_activity(self, pull_requests_id):
        activity = list(get_paginated_json(self.repo_url + "/pullrequests/" + str(pull_requests_id) + "/activity"))
        activity.sort(key=lambda x: x["id"])
        return activity
