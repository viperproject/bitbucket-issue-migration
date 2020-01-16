#!/usr/bin/env python3
import sys
import dateutil
import argparse
from github.GithubException import UnknownObjectException
from github import InputFileContent
import config
from migrate.bitbucket import BitbucketExport
from migrate.github import GithubImport


def map_bstatus_to_gstate(bissue):
    bstatus = bissue["status"]
    if bstatus in config.OPEN_ISSUE_STATES:
        return "open"
    else:
        return "closed"


def map_bassignee_to_gassignees(bissue):
    bassignee = bissue["assignee"]
    if bassignee is None:
        return []
    elif bassignee in config.USER_MAPPING:
        return [config.USER_MAPPING[bassignee]]
    else:
        return []


def map_bstatus_to_glabels(bissue, glabels):
    bstatus = bissue["status"]
    if bstatus in config.STATE_MAPPING:
        glabels.add(config.STATE_MAPPING[bstatus])


def map_bkind_to_glabels(bissue, glabels):
    bkind = bissue["kind"]
    if bkind in config.KIND_MAPPING:
        label = config.KIND_MAPPING[bkind]
    else:
        label = bkind
    glabels.add(label)


def time_string_to_date_string(timestring):
    datetime = dateutil.parser.parse(timestring)
    return datetime.strftime("%Y-%m-%d %H:%M")


def construct_gcomment_content(bcomment):
    sb = []
    content = bcomment["content"]
    comment_created_on = time_string_to_date_string(timestring=bcomment["created_on"])
    sb.append("> **@" + bcomment["user"] + "** commented on " + comment_created_on)
    sb.append("\n")
    sb.append("\n")
    sb.append("" if content is None else content)
    return "".join(sb)


def construct_gissue_body(bissue, battachments):
    sb = []

    # Header
    created_on = time_string_to_date_string(timestring=bissue["created_on"])
    updated_on = time_string_to_date_string(timestring=bissue["updated_on"])
    created_on_msg = "Created by **@" + bissue["reporter"] + "** on " + created_on
    if created_on == updated_on:
        sb.append("> " + created_on_msg)
    else:
        sb.append("> " + created_on_msg + ", last updated on " + updated_on)
    sb.append("\n")

    # Content
    sb.append("\n")
    sb.append(bissue["content"])

    # Attachments
    sb.append("\n")
    if battachments:
        sb.append("\n")
        sb.append("\n")
        sb.append("---")
        sb.append("\n")
        sb.append("\n")
        sb.append("Attachments:")
        sb.append("\n")
        for attachment in battachments:
            sb.append("\n")
            sb.append("* [**{}**]({}), uploaded by {}".format(
                attachment["filename"],
                attachment["url"],
                attachment["user"]
            ))
    
    return "".join(sb)


def construct_gissue_labels(bissue):
    glabels = set()
    map_bkind_to_glabels(bissue=bissue, glabels=glabels)
    map_bstatus_to_glabels(bissue=bissue, glabels=glabels)
    return list(glabels)


def update_gissue(gissue, bissue, bexport):
    if gissue.number != bissue["id"]:
        raise ValueError("Inconsistent issues (ids: {} and {})".format(gissue.number, bissue["id"]))
    issue_id = gissue.number
    battachments = bexport.issue_attachments[issue_id]
    bcomments = bexport.issue_comments[issue_id]

    # Update issue
    gissue.edit(
        title=bissue["title"],
        body=construct_gissue_body(bissue, battachments),
        labels=construct_gissue_labels(bissue),
        state=map_bstatus_to_gstate(bissue),
        assignees=map_bassignee_to_gassignees(bissue)
    )

    num_comments = len(bcomments)
    gcomments = list(gissue.get_comments())

    # Delete comments in excess
    gcomments_to_delete = gcomments[num_comments:]
    for i, gcomment in enumerate(gcomments_to_delete):
        print("Delete extra Gituhb comment {}/{} of issue #{}...".format(i + 1, len(gcomments_to_delete), issue_id))
        gcomment.delete()

    # Create missing comments and update them
    for comment_num, bcomment in enumerate(bcomments):
        print("Processing comment {}/{} of issue #{}...".format(comment_num+1, num_comments, issue_id))
        comment_body = construct_gcomment_content(bcomment)
        if comment_num < len(gcomments):
            gcomments[comment_num].edit(comment_body)
        else:
            gissue.create_comment(comment_body)


def get_or_create_gissue(repo, issue_id, bissue):
    try:
        gissue = repo.get_issue(issue_id)
    except UnknownObjectException:
        gissue = repo.create_issue("[issue {}]".format(issue_id))
    assert gissue.number == issue_id
    return gissue


ATTACHMENTS_GIST_DESCRIPTION = "Attachments from the Bitbucket migration"

def bitbucket_to_github(bexport, gimport):
    repo = gimport.repo
    user = gimport.github.get_user()

    # Migrate attachments
    if False:  # TODO: Work in progress
        print("Migrate attachments...")
        attachments_gist = first_or_default = next(
            (
                x for x in user.get_gists()
                if x.description == ATTACHMENTS_GIST_DESCRIPTION
            ),
            None
        )
        if attachments_gist is None:
            attachments_gist = user.create_gist(
                True,
                {"empty.txt": InputFileContent("")},
                ATTACHMENTS_GIST_DESCRIPTION
            )

    # Migrate issues
    print("Migrate issues...")
    bissues = bexport.issues
    old_gissues_num = repo.get_issues(state="all").totalCount
    print("Number of github issues in '{}' before the migration: {}".format(repo.full_name, old_gissues_num))
    print("Number of bitbucket issues in the export:", len(bexport.issues))

    if len(bexport.issues) < old_gissues_num:
        print("Warning: there are too many issues on Github")

    for bissue in bexport.issues:
        issue_id = bissue["id"]
        print("Processing issue #{}... [rate limiting: {}]".format(issue_id, gimport.github.rate_limiting[0]))
        gissue = get_or_create_gissue(repo=repo, bissue=bissue, issue_id=issue_id)
        update_gissue(gissue=gissue, bissue=bissue, bexport=bexport)
    


def create_parser():
    parser = argparse.ArgumentParser(
        prog="migrate",
        description="Migrate Bitbucket issues to Github"
    )
    parser.add_argument(
        "-t", "--access-token",
        help="Github Access Token",
        required=True
    )
    parser.add_argument(
        "-i", "--issues",
        help="Path to the zip file containing the export of Bitbucket issues",
        required=True
    )
    parser.add_argument(
        "-r", "--repository",
        help="Full name or id of the Github repository",
        required=True
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    bexport = BitbucketExport(args.issues)
    gimport = GithubImport(args.access_token, args.repository)
    bitbucket_to_github(bexport=bexport, gimport=gimport)


main()
