import json
from zipfile import ZipFile


class BitbucketExport:
    def __init__(self, issues_export_path):
        self.issues_export_path = issues_export_path
        
        with ZipFile(issues_export_path) as archive:
            with archive.open("db-1.0.json") as export_file:
                export_data = export_file.read().decode("utf-8")
            export_json = json.loads(export_data)
            print("Load issues...")
            self.issues = load_issues(export_json)
            print("Load comments...")
            self.issue_comments = load_issue_comments(export_json, self.issues)
            print("Load attachments...")
            self.issue_attachments = load_issue_attachments(export_json, archive, self.issues)


def load_issues(export_json):
    issues = sorted(export_json["issues"], key=lambda x: x["id"])

    # Check invariant
    for index, bissue in enumerate(issues, 1):
        if index != bissue["id"]:
            raise ValueError("The Bitbucket export does not contain some issues")

    if len(issues) == 0:
        print("Warning: could not find any issue in the Bitbucket export")

    return issues


def load_issue_comments(export_json, issues):
    comments = export_json["comments"]
    issue_comments = {}

    for issue in issues:
        issue_comments[issue["id"]] = []

    for comment in comments:
        issue_id = comment["issue"]
        issue_comments[issue_id].append(comment)

    for comments in issue_comments.values():
        comments.sort(key=lambda x: x["created_on"])

    return issue_comments


def load_issue_attachments(export_json, archive, issues):
    attachments = export_json["attachments"]
    issue_attachments = {}

    for issue in issues:
        issue_attachments[issue["id"]] = []

    for attachment in attachments:
        issue_id = attachment["issue"]
        path = attachment["path"]
        attachment["hash"] = attachment["path"].split("/")[1]
        with archive.open(path) as attachment_file:
            attachment["data"] = attachment_file.read()
        issue_attachments[issue_id].append(attachment)

    return issue_attachments
