#!/usr/bin/python
import sys
import re
from github import Github
from github.GithubException import UnknownObjectException
import argparse
import difflib
import config


ISSUE_LINK_RE = re.compile(r'https://bitbucket.org/({repos})/issues*/(\d+)[^\s()\[\]{{}}]*'
                           .format(repos="|".join(config.KNOWN_REPO_MAPPING)))
def replace_links_to_issues(body, args):
    # replace links to other issues by #<id> (or <repo>#<id> if it the issue is located in a different repo)
    def replace_issue_link(match):
        brepo = match.group(1)
        issue_nr = match.group(2)
        if brepo not in config.KNOWN_REPO_MAPPING:
            # leave link unchanged:
            return match.group(0)
        grepo = config.KNOWN_REPO_MAPPING[brepo]
        return r'{repo}#{issue_nr}'.format(
            repo=grepo if grepo != args.repository else "", issue_nr=issue_nr)
    return ISSUE_LINK_RE.sub(replace_issue_link, body)


PR_LINK_RE = re.compile(r'https://bitbucket.org/({repos})/pull-requests*/(\d+)[^\s()\[\]{{}}]*'
                           .format(repos="|".join(config.KNOWN_REPO_MAPPING)))
def replace_links_to_prs(body, args):
    # Bitbucket uses separate numbering for issues and pull requests
    # However, GitHub uses the same numbering.
    # Assuming that pull requests get imported after issues, the IDs of pull requests need to be incremented by the
    # number of issues (in the corresponding repo)
    def replace_pr_link(match):
        brepo = match.group(1)
        bpr_nr = int(match.group(2))
        if brepo not in config.KNOWN_REPO_MAPPING or brepo not in config.KNOWN_ISSUES_COUNT_MAPPING:
            # leave link unchanged:
            return match.group(0)
        grepo = config.KNOWN_REPO_MAPPING[brepo]
        issues_count = config.KNOWN_ISSUES_COUNT_MAPPING[brepo]
        gpr_number = bpr_nr + issues_count
        return r'{repo}#{gpr_number}'.format(
            repo=grepo if grepo != args.repository else "", gpr_number=gpr_number)
    return PR_LINK_RE.sub(replace_pr_link, body)


MENTION_RE = re.compile(r'(?:^|(?<=[^\w]))@([a-zA-Z0-9_-]+)\b')
def replace_links_to_users(body, args=None):
    # replace @mentions with users specified in config:
    # TODO: remove the 'disable-' before doing the real migration
    def replace_user(match):
        buser = match.group(1)
        if buser not in config.USER_MAPPING:
            # leave username unchanged:
            return '@' + 'disable-' + buser
        return '@' + 'disable-' + config.USER_MAPPING[buser]
    return MENTION_RE.sub(replace_user, body)


def update_issue_body(body, args):
    tmp = replace_links_to_issues(body, args)
    tmp = replace_links_to_prs(tmp, args)
    return replace_links_to_users(tmp, args)


def update_issue_comment_body(body, args):
    tmp = replace_links_to_issues(body, args)
    tmp = replace_links_to_prs(tmp, args)
    return replace_links_to_users(tmp, args)


def print_diff(title, old, new):
    print('#' * 50)
    print(title)
    diff = difflib.unified_diff(old.splitlines(), new.splitlines())
    for line in diff:
        print(line)
    print('#' * 50)


def update_links_in_comment(comment, args):
    old_body = comment.body
    body = update_issue_comment_body(old_body, args)
    if old_body != body:
        if args.dry_run:
            print_diff("issue comment {} is different:".format(comment.id),
                       old_body, body)
        else:
            comment.edit(body)


def update_links_in_issue(issue, args):
    old_body = issue.body
    body = update_issue_body(old_body, args)
    if old_body != body:
        if args.dry_run:
            print_diff("issue {} is different".format(issue.number),
                       old_body, body)
        else:
            issue.edit(body=body)
    comments = issue.get_comments()
    for comment in comments:
        update_links_in_comment(comment, args)


def update_links_in_issues(repo, args):
    issues = repo.get_issues(state="all")
    for issue in issues:
        update_links_in_issue(issue, args)


def update_links(repo, args):
    # iterate over issues and comments and update them:
    update_links_in_issues(repo, args)


def create_parser():
    parser = argparse.ArgumentParser(
        prog="linking",
        description="A tool to update links in GitHub issues."
    )
    parser.add_argument(
        "-t", "--access-token",
        help="Github Access Token",
        required=True
    )
    parser.add_argument(
        "-r", "--repository",
        help="Full name or id of the Github repository",
        required=True
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help=(
            "Simulate actions of this script by printing actions "
            "instead of performing them on GitHub"
        )
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

    update_links(repo, args)

if __name__ == "__main__":
    main()
