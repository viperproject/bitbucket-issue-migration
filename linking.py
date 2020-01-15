#!/usr/bin/python
import sys
import re
from github import Github
from github.GithubException import UnknownObjectException
import argparse
import difflib
import config


def replace_links_to_issues(body, args):
    # replace links to other issues by #<id> (or <repo>#<id> if it the issue is located in a different repo)
    new_body = body
    for brepo in config.KNOWN_REPO_MAPPING:
        grepo = config.KNOWN_REPO_MAPPING[brepo]
        # parenthesis and square brackets are not considered part of the url, because they could belong to outer markdown
        # "{{}}" escapes the curly brackets and results in "{}" after calling format on it.
        pattern = r'https://bitbucket.org/{repo}/issues*/(\d+)[^\s()\[\]{{}}]*'.format(repo=brepo)
        # the following distinction is optional, because the else method works in the same repo as well
        if grepo == args.repository:
            # it's a link to an issue in the current (i.e. args.repository) repo
            new_body = re.sub(pattern, r'#\1', new_body)
        else:
            # it's a link to an issue in another repo that is known as well
            new_body = re.sub(pattern, r'{repo}#\1'.format(repo=grepo), new_body)
    return new_body


def update_issue_body(body, args):
    return replace_links_to_issues(body, args)


def update_issue_comment_body(body, args):
    return replace_links_to_issues(body, args)


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


main()
