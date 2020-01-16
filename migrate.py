#!/usr/bin/env python3
import sys
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


def construct_gcomment_body(bcomment):
    sb = []
    content = bcomment["content"]["raw"]
    comment_created_on = time_string_to_date_string(timestring=bcomment["created_on"])
    sb.append("> **@" + bcomment["user"]["nickname"] + "** commented on " + comment_created_on + "\n")
    sb.append("\n")
    sb.append("" if content is None else content)
    return "".join(sb)


def construct_gissue_body(gimport, bissue, battachments):
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
            attachments_gist = gimport.get_issue_attachments_gist(bissue["id"])
            sb.append("* [**{}**]({})\n".format(
                name,
                attachments_gist.files[name].raw_url
            ))

    return "".join(sb)


def construct_gpull_request_body(gimport, bpull_request):
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


def update_gissue_comments(gissue, bcomments):
    issue_id = gissue.number
    num_comments = len(bcomments)
    gcomments = list(gissue.get_comments())

    # Create missing comments and update them
    for comment_num, bcomment in enumerate(bcomments):
        print("Processing comment {}/{} of issue #{}...".format(comment_num+1, num_comments, issue_id))
        comment_body = replace_links_to_users(construct_gcomment_body(bcomment))
        if comment_num < len(gcomments):
            gcomments[comment_num].edit(comment_body)
        else:
            gissue.create_comment(comment_body)

    # Delete comments in excess
    gcomments_to_delete = gcomments[num_comments:]
    for i, gcomment in enumerate(gcomments_to_delete):
        print("Delete extra Gituhb comment {}/{} of issue #{}...".format(i + 1, len(gcomments_to_delete), issue_id))
        gcomment.delete()


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
    update_gissue_comments(gissue, bcomments)


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
    update_gissue_comments(gissue, bcomments)


def bitbucket_to_github(bexport, gimport, args):
    repo_full_name = gimport.get_repo_full_name()
    gissues = {}

    # Retrieve data
    bissues = bexport.get_issues()
    bpull_requests = bexport.get_pull_requests()
    print("Number of bitbucket issues:", len(bissues))
    print("Number of bitbucket pull requests:", len(bpull_requests))
    print("Number of github issues before the migration: {}".format(gimport.get_issue_count()))
    assert repo_full_name in config.KNOWN_ISSUES_COUNT_MAPPING
    assert config.KNOWN_ISSUES_COUNT_MAPPING[repo_full_name] == len(bissues)
    pull_requests_id_offset = config.KNOWN_ISSUES_COUNT_MAPPING[repo_full_name]

    # Prepare issues
    print("Prepare issues...")
    for issue_id in range(1, len(bissues) + 1):
        print("Preparing issue #{}... [rate limiting: {}]".format(issue_id, gimport.get_remaining_rate_limit()))
        gissue = gimport.get_or_create_gissue(issue_id, bissue[issue_id]["title"])
        gissues[issue_id] = gissue

    for issue_id in range(len(bissues) + 1, len(bissues) + len(bpull_requests) + 1):
        print("Preparing issue #{} for pull request... [rate limiting: {}]".format(issue_id, gimport.get_remaining_rate_limit()))
        bpull_request = bpull_requests[issue_id - pull_requests_id_offset]
        title = construct_gissue_title_for_pull_request(bpull_request)
        gissue = gimport.get_or_create_gissue(issue_id, title)
        gissues[issue_id] = gissue

    # Migrate issues
    if not args.skip_issues:
        print("Migrate issues...")
        for bissue in bissues:
            issue_id = bissue["id"]
            print("Migrating issue #{}... [rate limiting: {}]".format(issue_id, gimport.get_remaining_rate_limit()))
            gissue = gissues[issue_id]
            update_gissue(gimport=gimport, bexport=bexport, gissue=gissue, bissue=bissue)

    # Migrate pull requests
    print("Migrate pull requests...")
    for pull_request in bpull_requests:
        pull_request_id = pull_request["id"]
        issue_id = pull_request_id + pull_requests_id_offset
        print("Migrating pull-request #{}... [rate limiting: {}]".format(pull_request_id, gimport.get_remaining_rate_limit()))
        gissues[issue_id] = gissue
        update_gissue_for_pull_request(gimport=gimport, bexport=bexport, gissue=gissue, bpull_request=pull_request)

    # Final checks
    if len(bissues) + len(bpull_requests) != repo.get_issues(state="all").totalCount:
        print("Warning: the number of Github issues seems to be wrong")


def create_parser():
    parser = argparse.ArgumentParser(
        prog="migrate",
        description="Migrate Bitbucket issues to Github"
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
        help="Skip the migration of issues",
        action='store_true'
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    bexport = BitbucketExport(args.bitbucket_repository)
    gimport = GithubImport(args.github_access_token, args.github_repository)
    bitbucket_to_github(bexport=bexport, gimport=gimport, args=args)


if __name__ == "__main__":
    main()
