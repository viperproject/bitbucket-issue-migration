#!/usr/bin/env python3
import sys
import re
from dateutil import parser
import argparse
import github
from github.GithubException import UnknownObjectException
from github import InputFileContent
import config
from migrate.bitbucket import BitbucketExport
from migrate.github import GithubImport
from linking import replace_links_to_users


def map_bstate_to_gstate(bissue):
    bstate = bissue["state"]
    if bstate in config.OPEN_ISSUE_OR_PULL_REQUEST_STATES:
        return "open"
    else:
        return "closed"


def map_bassignee_to_gassignees(bissue):
    bassignee = bissue["assignee"]
    if bassignee is None:
        return []
    else:
        nickname = bassignee["nickname"]
        if nickname in config.USER_MAPPING:
            return [config.USER_MAPPING[nickname]]
        else:
            return []


def map_buser_to_guser(buser):
    if buser is None:
        return None
    else:
        nickname = buser["nickname"]
        if nickname in config.USER_MAPPING:
            return config.USER_MAPPING[nickname]
        else:
            return None


def map_bstate_to_glabels(bissue, glabels):
    bstate = bissue["state"]
    if bstate in config.STATE_MAPPING:
        glabels.add(config.STATE_MAPPING[bstate])


def map_bkind_to_glabels(bissue, glabels):
    bkind = bissue["kind"]
    if bkind in config.KIND_MAPPING:
        label = config.KIND_MAPPING[bkind]
    else:
        label = bkind
    glabels.add(label)


def time_string_to_date_string(timestring):
    datetime = parser.parse(timestring)
    return datetime.strftime("%Y-%m-%d %H:%M")


def convert_date(bb_date):
    """Convert the date from Bitbucket format to GitHub format."""
    # '2012-11-26T09:59:39+00:00'
    m = re.search(r'(\d\d\d\d-\d\d-\d\d)T(\d\d:\d\d:\d\d)', bb_date)
    if m:
        return '{}T{}Z'.format(m.group(1), m.group(2))

    raise RuntimeError("Could not parse date: {}".format(bb_date))


def construct_gcomment_body(bcomment):
    sb = []
    content = bcomment["content"]["raw"]
    comment_created_on = time_string_to_date_string(timestring=bcomment["created_on"])
    sb.append("> **@" + bcomment["user"]["nickname"] + "** commented on " + comment_created_on + "\n")
    sb.append("\n")
    sb.append("" if content is None else content)
    return "".join(sb)


def construct_gissue_body(bissue, battachments, attachment_gist_by_issue_id):
    sb = []

    # Header
    created_on = time_string_to_date_string(timestring=bissue["created_on"])
    updated_on = time_string_to_date_string(timestring=bissue["updated_on"])
    created_on_msg = "Created by **@" + bissue["reporter"]["nickname"] + "** on " + created_on
    if created_on == updated_on:
        sb.append("> " + created_on_msg + "\n")
    else:
        sb.append("> " + created_on_msg + ", last updated on " + updated_on + "\n")

    # Content
    sb.append("\n")
    sb.append(bissue["content"]["raw"])
    sb.append("\n")

    # Attachments
    if battachments:
        sb.append("\n")
        sb.append("---\n")
        sb.append("\n")
        sb.append("Attachments:\n")
        for name in battachments.keys():
            attachments_gist = attachment_gist_by_issue_id[bissue["id"]]
            sb.append("* [**{}**]({})\n".format(
                name,
                attachments_gist.files[name].raw_url
            ))

    return "".join(sb)


def construct_gpull_request_body(bpull_request):
    sb = []

    # Header
    created_on = time_string_to_date_string(timestring=bpull_request["created_on"])
    updated_on = time_string_to_date_string(timestring=bpull_request["updated_on"])
    created_on_msg = " **Pull request** :twisted_rightwards_arrows: created by **@" + bpull_request["author"]["nickname"] + "** on " + created_on
    if created_on == updated_on:
        sb.append("> " + created_on_msg + "\n")
    else:
        sb.append("> " + created_on_msg + ", last updated on " + updated_on + "\n")

    if bpull_request["participants"]:
        sb.append(">\n")
        sb.append("> Participants:\n")
        sb.append(">\n")
        for participant in bpull_request["participants"]:
            sb.append("> * [**{}**]".format(participant["user"]["nickname"]))
            if participant["role"] == "REVIEWER":
                sb.append(" (reviewer)")
            if participant["approved"]:
                sb.append(" :heavy_check_mark:")
            sb.append("\n")

    sb.append(">\n")
    source = bpull_request["source"]
    sb.append("> Source: repository {}, hash {}, branch {}\n".format(
        source["repository"]["full_name"],
        source["commit"]["hash"],
        source["branch"]["name"],
    ))

    destination = bpull_request["destination"]
    sb.append("> Destination: repository {}, hash {}, branch {}\n".format(
        destination["repository"]["full_name"],
        destination["commit"]["hash"],
        destination["branch"]["name"],
    ))

    sb.append(">\n")
    destination = bpull_request["destination"]
    sb.append("> State: **{}**\n".format(bpull_request["state"]))

    # Content
    sb.append("\n")
    sb.append(bpull_request["description"])
    sb.append("\n")

    return "".join(sb)


def construct_gissue_labels(bissue):
    glabels = set()
    map_bkind_to_glabels(bissue=bissue, glabels=glabels)
    map_bstate_to_glabels(bissue=bissue, glabels=glabels)
    return list(glabels)


def construct_gissue_title_for_pull_request(bpull_request):
    return "[PR] " + bpull_request["title"]


def construct_gissue_comments(bcomments):
    comments = []

    for comment_num, bcomment in enumerate(bcomments):
        comment = {
            "body": replace_links_to_users(construct_gcomment_body(bcomment)),
            "created_at": convert_date(bcomment["created_on"])
        }
        comments.push(comment)
    
    comments.sort(key=lambda x: x["created_at"])
    return comments


def construct_gist_description_for_issue_attachments(bissue, bexport):
    return "Attachments for issue #{} of bitbucket repo {}".format(
        bissue["id"],
        bexport.get_repo_full_name()
    )


def construct_gist_from_bissue_attachments(bissue, bexport):
    issue_id = bissue["id"]
    battachments = bexport.get_issue_attachments(issue_id)
    
    if not battachments:
        return None

    gist_description = construct_gist_description_for_issue_attachments(bissue, bexport)
    gist_files = {"# README.md": InputFileContent(gist_description)}

    for name in battachments.keys():
        content = bexport.get_issue_attachment_content(issue_id, name)
        gist_files[name] = InputFileContent(content)

    return {
        "description": gist_description,
        "files": gist_files
    }


def construct_gissue_from_bissue(bissue, bexport, attachment_gist_by_issue_id):
    issue_id  = bissue["id"]
    bcomments = bexport.get_issue_comments(issue_id)

    issue_body = replace_links_to_users(
        construct_gissue_body(bissue, battachments, attachment_gist_by_issue_id)
    )

    return {
        "issue" : {
            "title": bissue["title"],
            "body": issue_body,
            "created_at": convert_date(bissue["created_on"]),
            "updated_at": convert_date(bissue["updated_on"]),
            "assignee": map_buser_to_guser(bissue["assignee"]),
            "closed": map_bstate_to_gstate(bissue) == "closed",
            "labels": construct_gissue_labels(bissue),
        },
        "comments": construct_gissue_comments(bcomments)
    }


def construct_gissue_from_bpull_request(bpull_request, bexport):
    pull_requests_id_offset = config.KNOWN_ISSUES_COUNT_MAPPING[bexport.get_repo_full_name()]
    pull_request_id = bpull_request["id"]
    bcomments = bexport.get_pull_request_comments(pull_request_id)

    issue_body = replace_links_to_users(
        construct_gpull_request_body(bpull_request)
    )

    return {
        "issue": {
            "title": construct_gissue_title_for_pull_request(bpull_request),
            "body": issue_body,
            "created_at": convert_date(bpull_request["created_on"]),
            "updated_at": convert_date(bpull_request["updated_on"]),
            "assignee": map_buser_to_guser(bpull_request["author"]),
            "closed": map_bstate_to_gstate(bpull_request) == "closed",
            "labels": construct_gissue_labels(bpull_request),
        },
        "comments": construct_gissue_comments(bcomments)
    }


def update_gissue(bissue, gissue, bexport, gimport):
    assert gissue.number == bissue["id"]
    issue_id = gissue.number

    # Create or update attachments
    battachments = bexport.get_issue_attachments(issue_id)
    if battachments:
        gist_description = "Attachments for issue #{} of {}".format(
            issue_id,
            gimport.repo.full_name
        )
        gist_files = {"# README.md": InputFileContent(gist_description)}
        for name in battachments.keys():
            content = bexport.get_issue_attachment_content(issue_id, name)
            gist_files[name] = InputFileContent(content)
        attachments_gist = gimport.get_gist_by_description(gist_description)
        if attachments_gist is None:
            attachments_gist = gimport.github.get_user().create_gist(True, gist_files, gist_description)
        else:
            attachments_gist.edit(gist_description, gist_files)
        gimport.set_issue_attachments_gist(issue_id, attachments_gist)

    # Update issue
    issue_body = replace_links_to_users(
        construct_gissue_body(gimport, bissue, battachments)
    )
    gissue.edit(
        title=bissue["title"],
        body=issue_body,
        labels=construct_gissue_labels(bissue),
        state=map_bstate_to_gstate(bissue),
        assignees=map_bassignee_to_gassignees(bissue)
    )

    # Update comments
    bcomments = bexport.get_issue_comments(issue_id)
    gimport.update_issue_comments(gissue, construct_gissue_comments(bcomments))


def update_gissue_for_pull_request(gimport, bexport, gissue, bpull_request):
    pull_requests_id_offset = config.KNOWN_ISSUES_COUNT_MAPPING[gimport.repo.full_name]
    assert gissue.number == bpull_request["id"] + pull_requests_id_offset
    pull_request_id = bpull_request["id"]

    # Update issue
    issue_body = replace_links_to_users(
        construct_gpull_request_body(gimport, bissue, battachments)
    )
    gissue.edit(
        title=construct_gissue_title_for_pull_request(bpull_request),
        body=issue_body,
        labels=construct_gissue_labels(bissue),
        state=map_bstate_to_gstate(bissue),
        assignees=map_bassignee_to_gassignees(bissue)
    )

    # Update comments
    bcomments = bexport.get_pull_request_comments(pull_request_id)
    gimport.update_issue_comments(gissue, construct_gissue_comments(bcomments))


def bitbucket_to_github(bexport, gimport, args):
    repo_full_name = gimport.get_repo_full_name()
    issues_data = []
    attachment_gist_by_issue_id = {}

    # Retrieve data
    bissues = bexport.get_issues()
    bpull_requests = bexport.get_pull_requests()
    assert repo_full_name in config.KNOWN_ISSUES_COUNT_MAPPING
    assert config.KNOWN_ISSUES_COUNT_MAPPING[repo_full_name] == len(bissues)
    pull_requests_id_offset = config.KNOWN_ISSUES_COUNT_MAPPING[repo_full_name]

    # Migrate attachments
    print("Migrate bitbucket attachments to github...")
    for bissue in bissues:
        issue_id = bissue["id"]
        battachments = bexport.get_issue_attachments(issue_id)
        if battachments:
            gist_data = construct_gist_from_bissue_attachments(bissue, bexport)
            gist = gimport.get_or_create_gist_by_description(gist_data)
            attachment_gist_by_issue_id[issue_id] = gist

    # Prepare issues
    print("Prepare github issues...")
    for bissue in bissues:
        issue_id = bissue["id"]
        print("Prepare github issue #{} from bitbucket issue...".format(issue_id))
        gissue = construct_gissue_from_bissue(bissue)
        issues_data.append(gissue)

    for bpull_request in bpull_requests:
        issue_id = bpull_request["id"] + pull_requests_id_offset
        print("Prepare github issue #{} from bitbucket pull request...".format(issue_id))
        gissue = construct_gissue_from_bpull_requests(bpull_requests)
        issues_data.append(gissue)

    # Upload github issues
    print("Upload github issues...")
    existing_gissues = gimport.get_issues()
    for existing_gissue in existing_gissues:
        issue_id = existing_gissue.id
        print("Upload github issue #{}... [rate limiting: {}]".format(issue_id, gimport.get_remaining_rate_limit()))
        if issue_id > len(issues_data):
            print("Error: existing github issue #{} should not exist.")
        else:
            gimport.update_issue_with_comments(issues_data[issue_id - 1])
    
    for issue_id in range(existing_gissues.totalCount, len(issues_data) + 1):
        print("Create github issue #{}...".format(issue_id))
        gissue_data = issues_data[issue_id - 1]
        gimport.create_issue_with_comments(gissue_data)

    # Final checks
    if len(bissues) + len(bpull_requests) != gimport.get_issues_count():
        print("Error: the number of Github issues seems to be wrong.")


def check(bexport, gimport, args):
    # Retrieve data
    bissues = bexport.get_issues()
    bpull_requests = bexport.get_pull_requests()
    gissues_count = gimport.get_issues_count()
    print("Number of bitbucket issues:", len(bissues))
    print("Number of bitbucket pull requests:", len(bpull_requests))
    print("Number of github issues: {}".format(gissues_count))

    if gissues_count != 0:
        print("Warning: the github repository has existing issues, so the migration can't preserve the creation date of issues and pull requests.")
    if gissues_count > len(bissues) + len(bpull_requests):
        print("Error: the github repository has {} issues, but the maximum should be {} because the bitbucket repository only has {} issues and {} pull requests.".format(
            gissues_count,
            len(bissues) + len(bpull_requests),
            len(bissues),
            len(bpull_requests)
        ))

    brepo_full_name = bexport.get_repo_full_name()
    grepo_full_name = gimport.get_repo_full_name()
    if brepo_full_name not in config.KNOWN_ISSUES_COUNT_MAPPING:
        print("Error: bitbucket repository '{}' is not configured in KNOWN_ISSUES_COUNT_MAPPING.".format(brepo_full_name))
    if brepo_full_name not in config.KNOWN_REPO_MAPPING:
        print("Error: bitbucket repository '{}' is not configured in KNOWN_REPO_MAPPING.".format(brepo_full_name))

    if config.KNOWN_ISSUES_COUNT_MAPPING[brepo_full_name] != len(bissues):
        print("Error: bitbucket repository '{}' in KNOWN_ISSUES_COUNT_MAPPING maps to '{}', but the actual number of issues is '{}'.".format(
            brepo_full_name,
            config.KNOWN_ISSUES_COUNT_MAPPING[brepo_full_name],
            len(bissues)
        ))
    if config.KNOWN_REPO_MAPPING[brepo_full_name] != grepo_full_name:
        print("Error: bitbucket repository '{}' in KNOWN_REPO_MAPPING maps to '{}', but the github repository passed by command line is '{}'.".format(
            brepo_full_name,
            config.KNOWN_REPO_MAPPING[brepo_full_name],
            grepo_full_name
        ))

    # Check authors
    bnicknames = set()
    for bissue in bissues:
        bissue_id = bissue["id"]
        if bissue_id % 10 == 0:
            print("Checking bitbucket issue #{}...".format(bissue_id))
        if bissue["assignee"] is not None:
            bnicknames.add(bissue["assignee"]["nickname"])
        for bcomment in bexport.get_issue_comments(bissue_id):
            bnicknames.add(bcomment["user"]["nickname"])
    for bpull_request in bpull_requests:
        bpull_request_id = bpull_request["id"]
        if bpull_request_id % 10 == 0:
            print("Checking bitbucket pull request #{}...".format(bpull_request_id))
        bnicknames.add(bpull_request["author"]["nickname"])
        for bparticipant in bpull_request["participants"]:
            bnicknames.add(bparticipant["user"]["nickname"])
        for breviewer in bpull_request["reviewers"]:
            bnicknames.add(breviewer["nickname"])
        for bcomment in bexport.get_issue_comments(bissue_id):
            bnicknames.add(bcomment["user"]["nickname"])
    for nickname in bnicknames:
        if nickname not in config.USER_MAPPING:
            print("Warning: bitbucket user '{}' is not configured in USER_MAPPING.".format(brepo_full_name))


def create_parser():
    parser = argparse.ArgumentParser(
        prog="migrate",
        description="Migrate Bitbucket issues and pull requests to Github"
    )
    parser.add_argument(
        "-t", "--github-access-token",
        help="Github Access Token",
        required=True
    )
    parser.add_argument(
        "-b", "--bitbucket-repository",
        help="Full name of the Bitbucket repository (e.g. viperproject/silver)",
        required=True
    )
    parser.add_argument(
        "-g", "--github-repository",
        help="Full name of the Github repository (e.g. viperproject/silver)",
        required=True
    )
    parser.add_argument(
        "--skip-issues",
        help="Skip the migration of issues (development only)",
        action='store_true'
    )
    parser.add_argument(
        "--check",
        help="Check the configuration",
        action='store_true'
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    bexport = BitbucketExport(args.bitbucket_repository)
    gimport = GithubImport(args.github_access_token, args.github_repository)
    if args.check:
        check(bexport=bexport, gimport=gimport, args=args)
    else:
        bitbucket_to_github(bexport=bexport, gimport=gimport, args=args)


if __name__ == "__main__":
    main()
