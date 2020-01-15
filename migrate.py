#!/usr/bin/python
import json
import sys
import os
from dateutil import parser
import requests
from requests import Request
from requests_toolbelt.utils import dump
import requests_toolbelt
import config

from zipfile import ZipFile
from github import Github
from github.GithubException import UnknownObjectException
import argparse
from collections import namedtuple


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
    datetime = parser.parse(timestring)
    return datetime.strftime("%Y-%m-%d")


def append_time_label(sb, timestring, label):
    sb.append("\n[" + label + ": " + timestring + "]")


def construct_gcomment_content(bcomment):
    sb = []
    content = bcomment["content"]
    sb.append("\n")
    comment_label = "Comment created by " + bcomment["user"]
    comment_created_on = time_string_to_date_string(timestring=bcomment["created_on"])
    append_time_label(sb=sb, timestring=comment_created_on, label=comment_label)
    sb.append("\n")
    sb.append("" if content is None else content)
    return "".join(sb)


def construct_gissue_content(bissue):
    sb = [bissue["content"], "\n"]
    created_on = time_string_to_date_string(timestring=bissue["created_on"])
    updated_on = time_string_to_date_string(timestring=bissue["updated_on"])
    append_time_label(sb=sb, timestring=created_on, label="Issue created by " + bissue["reporter"])
    if created_on != updated_on:
        append_time_label(sb=sb, timestring=updated_on, label="Last updated on bitbucket")
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

    gissue.edit(
        title=bissue["title"],
        body=construct_gissue_content(bissue=bissue),
        labels=construct_gissue_labels(bissue=bissue),
        state=map_bstatus_to_gstate(bissue=bissue),
        assignees=map_bassignee_to_gassignees(bissue=bissue)
    )

    bcomments = bexport.bcomments[issue_id]
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
    

def get_or_create_gissue(repo, issue_id):
    try:
        gissue = repo.get_issue(issue_id)
    except UnknownObjectException:
        gissue = repo.create_issue("[issue {}]".format(issue_id))
    assert gissue.number == issue_id
    return gissue


def bitbucket_to_github(bexport, repo):
    bissues = bexport.bissues
    old_gissues = repo.get_issues(state="all")

    print("Number of github issues in '{}' before the : {}".format(repo.full_name, old_gissues.totalCount))
    print("Number of bitbucket issues in the export:", len(bexport.bissues))

    if len(bexport.bissues) < old_gissues.totalCount:
        print("Warning: there are too many issues on Github")

    for bissue in bexport.bissues:
        issue_id = bissue["id"]
        print("Processing issue #{}...".format(issue_id))
        gissue = get_or_create_gissue(repo=repo, issue_id=issue_id)
        update_gissue(gissue=gissue, bissue=bissue, bexport=bexport)


BitbucketExport = namedtuple("BitbucketExport", "bissues bcomments")


def parse_bitbucket_export(bexport_json):
    bissues = bexport_json["issues"]
    
    # Sort by id
    bissues.sort(key=lambda x: x["id"])
    
    # Check invariant
    for index, bissue in enumerate(bissues, 1):
        if index != bissue["id"]:
            raise ValueError("The Bitbucket export does not contain some issues")

    if len(bissues) == 0:
        raise ValueError("Could not find any issue in the Bitbucket export")
    
    # Load comments
    comments = bexport_json["comments"]
    bcomments = {}

    for bissue in bissues:
        bcomments[bissue["id"]] = []
    
    for comment in comments:
        bissue_idx = comment["issue"]
        bcomments[bissue_idx].append(comment)
    
    for comments in bcomments.values():
        comments.reverse()  # FIXME: why this reverse?
    
    return BitbucketExport(bissues=bissues, bcomments=bcomments)


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

    g = Github(args.access_token)

    try:
        repo = g.get_repo(args.repository)
    except UnknownObjectException:
        print("Failed to get the repository '{}'".format(args.repository))
        sys.exit(1)

    with ZipFile(args.issues) as archive:
        with archive.open("db-1.0.json") as bitbucket_export:
            # Read file
            export_data = bitbucket_export.read().decode("utf-8")
            # Parse JSON
            export_json = json.loads(export_data)
            # Parse structure
            bexport = parse_bitbucket_export(export_json)
            # Migrate to Github
            bitbucket_to_github(bexport=bexport, repo=repo)


main()
