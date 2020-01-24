#!/usr/bin/env python3
import re
from dateutil import parser
import argparse
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


def map_buser_to_guser(buser):
    if buser is None:
        return None
    else:
        nickname = buser["nickname"]
        if nickname in config.USER_MAPPING:
            return config.USER_MAPPING[nickname]
        else:
            return None


def map_bstate_to_glabels(bissue):
    bstate = bissue["state"]
    if bstate in config.STATE_MAPPING:
        label = config.STATE_MAPPING[bstate]
        if label is None:
            return []
        else:
            return [label]
    else:
        print("Warning: ignoring bitbucket issue state '{}'".format(bstate))
        return []


def map_bpriority_to_glabels(bissue):
    bpriority = bissue["priority"]
    if bpriority in config.PRIORITY_MAPPING:
        label = config.PRIORITY_MAPPING[bpriority]
        if label is None:
            return []
        else:
            return [label]
    else:
        print("Warning: ignoring bitbucket issue priority '{}'".format(bpriority))
        return []


def map_bkind_to_glabels(bissue):
    bkind = bissue["kind"]
    if bkind in config.KIND_MAPPING:
        label = config.KIND_MAPPING[bkind]
        if label is None:
            return []
        else:
            return [label]
    else:
        print("Warning: ignoring bitbucket issue kind '{}'".format(bkind))
        return []


def map_bcomponent_to_glabels(bissue):
    if bissue["component"] is None:
        return []
    bcomponent = bissue["component"]["name"]
    if bcomponent in config.COMPONENT_MAPPING:
        label = config.COMPONENT_MAPPING[bcomponent]
        if label is None:
            return []
        else:
            return [label]
    else:
        print("Warning: ignoring bitbucket issue component '{}'".format(bcomponent))
        return []


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


def construct_gcomment_body(bcomment, bcomments_by_id, bexport=None, bpull_request=None):
    sb = []
    comment_created_on = time_string_to_date_string(bcomment["created_on"])
    sb.append("> **@" + bcomment["user"]["nickname"] + "** commented on " + comment_created_on + "\n")
    if "inline" in bcomment:
        inline_data = bcomment["inline"]
        file_path = inline_data["path"]
        if inline_data["from"] is None:
            if inline_data["to"] is None:
                sb.append("> Inline comment on `{}`\n".format(
                    file_path
                ))
            else:
                to_line = inline_data["to"]
                sb.append("> Inline comment on line {} of `{}`\n".format(
                    to_line,
                    file_path
                ))
        else:
            from_line = inline_data["from"]
            to_line = inline_data["to"]
            sb.append("> Inline comment on lines {}..{} of `{}`\n".format(
                from_line,
                to_line,
                file_path
            ))
    sb.append("\n")
    if "parent" in bcomment:
        parent_comment = bcomments_by_id[bcomment["parent"]["id"]]
        if parent_comment["content"]["raw"] is not None:
            sb.append("> {}\n\n".format(parent_comment["content"]["raw"]))
    sb.append("" if bcomment["content"]["raw"] is None else bcomment["content"]["raw"])
    return "".join(sb)


def construct_gissue_body(bissue, battachments, attachment_gist_by_issue_id):
    sb = []

    # Header
    created_on = time_string_to_date_string(bissue["created_on"])
    updated_on = time_string_to_date_string(bissue["updated_on"])
    sb.append("> Created by **@" + bissue["reporter"]["nickname"] + "** on " + created_on + "\n")
    if created_on != updated_on:
        sb.append("> Last updated on " + updated_on + "\n")

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
            issue_id = bissue["id"]
            if issue_id in attachment_gist_by_issue_id:
                attachments_gist = attachment_gist_by_issue_id[issue_id]
                sb.append("* [**`{}`**]({})\n".format(
                    name,
                    attachments_gist.files[name].raw_url
                ))
            else:
                print("Error: missing gist for the attachments of issue #{}.".format(issue_id))
                sb.append("* **`{}`** (missing link)\n".format(name))

    return "".join(sb)


def construct_gpull_request_body(bpull_request, bexport):
    sb = []

    # Header
    created_on = time_string_to_date_string(bpull_request["created_on"])
    updated_on = time_string_to_date_string(bpull_request["updated_on"])
    if bpull_request["author"] is None:
        author_msg = ""
    else:
        author_msg = "by **@" + bpull_request["author"]["nickname"] + "** "
    sb.append(">  **Pull request** :twisted_rightwards_arrows: created " + author_msg + "on " + created_on + "\n")
    if created_on != updated_on:
        sb.append("> Last updated on " + updated_on + "\n")

    if bpull_request["participants"]:
        sb.append(">\n")
        sb.append("> Participants:\n")
        sb.append(">\n")
        for participant in bpull_request["participants"]:
            sb.append("> * **@{}**".format(participant["user"]["nickname"]))
            if participant["role"] == "REVIEWER":
                sb.append(" (reviewer)")
            if participant["approved"]:
                sb.append(" :heavy_check_mark:")
            sb.append("\n")

    sb.append(">\n")
    source = bpull_request["source"]
    if source["repository"] is None and source["commit"] is None:
        sb.append("> Source: branch [`{branch}`](https://bitbucket.org/{repo}/src/{branch})\n".format(
            branch=source["branch"]["name"],
            repo=bexport.get_repo_full_name()
        ))
    else:
        sb.append("> Source: [`{repo}`](https://bitbucket.org/{repo}), [`{branch}`](https://bitbucket.org/{repo}/src/{branch}), [{hash}](https://bitbucket.org/{repo}/commits/{hash})\n".format(
            repo=source["repository"]["full_name"],
            branch=source["branch"]["name"],
            hash=source["commit"]["hash"]
        ))

    destination = bpull_request["destination"]
    sb.append("> Destination: branch [`{branch}`](https://bitbucket.org/{repo}/src/{branch}), [{hash}](https://bitbucket.org/{repo}/commits/{hash})\n".format(
            repo=destination["repository"]["full_name"],
            branch=destination["branch"]["name"],
            hash=destination["commit"]["hash"]
        ))

    if bpull_request["merge_commit"] is not None:
        sb.append("> Marge commit: [{hash}](https://bitbucket.org/{repo}/commits/{hash})\n".format(
            repo=bexport.get_repo_full_name(),
            hash=bpull_request["merge_commit"]["hash"]
        ))

    sb.append(">\n")
    sb.append("> State: **`{}`**\n".format(bpull_request["state"]))

    # Content
    sb.append("\n")
    sb.append(bpull_request["description"])
    sb.append("\n")

    return "".join(sb)


def construct_gcomment_body_for_change(bchange):
    created_on = time_string_to_date_string(bchange["created_on"])
    sb = []
    blacklist = ["content", "title", "assignee_account_id"]
    for changed_key, change in bchange["changes"].items():
        if changed_key not in blacklist:
            sb.append("> **@{}** changed `{}` from `{}` to `{}` on {}\n".format(
                bchange["user"]["nickname"],
                changed_key,
                change["old"] if change["old"] else "(none)",
                change["new"] if change["new"] else "(none)",
                created_on
            ))
    return "".join(sb)


def construct_gcomment_body_for_update_activity(update_activity):
    on_date = time_string_to_date_string(update_activity["date"])
    if update_activity["author"] is None:
        return "> the status has been changed to `{}` on {}".format(
            update_activity["state"],
            on_date
        )
    else:
        return "> **@{}** changed the status to `{}` on {}".format(
            update_activity["author"]["nickname"],
            update_activity["state"],
            on_date
        )


def construct_gcomment_body_for_approval_activity(approval_activity):
    on_date = time_string_to_date_string(approval_activity["date"])
    return "> **@{}** approved :heavy_check_mark: the pull request on {}".format(
        approval_activity["user"]["nickname"],
        on_date
    )


def construct_gissue_title_for_pull_request(bpull_request):
    return "[PR] " + bpull_request["title"]


def construct_gissue_comments(bcomments, bexport=None, bpull_request=None):
    comments = []

    for comment_id, bcomment in bcomments.items():
        # Skip empty comments
        if bcomment["content"]["raw"] is None:
            continue
        # Skip deleted comments
        if "deleted" in bcomment and bcomment["deleted"]:
            continue
        # Constrct comment
        comment = {
            "body": replace_links_to_users(construct_gcomment_body(bcomment, bcomments, bexport, bpull_request)),
            "created_at": convert_date(bcomment["created_on"])
        }
        comments.append(comment)

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


def construct_gissue_comments_for_changes(bchanges):
    comments = []
    for bchange in bchanges:
        body = replace_links_to_users(construct_gcomment_body_for_change(bchange))
        # Skip empty comments
        if body:
            comment = {
                "body": body,
                "created_at": convert_date(bchange["created_on"])
            }
            comments.append(comment)
    return comments


def construct_gissue_comments_for_activity(bactivity):
    comments = []
    for single_activity in bactivity:
        if "approval" in single_activity:
            if "approval" in single_activity:
                approval_activity = single_activity["approval"]
                activity_date = approval_activity["date"]
                body = construct_gcomment_body_for_approval_activity(approval_activity)
            else:
                # comment activityor update
                continue
            comment = {
                "body": replace_links_to_users(body),
                "created_at": convert_date(activity_date)
            }
            comments.append(comment)
    return comments


def construct_gissue_from_bissue(bissue, bexport, attachment_gist_by_issue_id):
    issue_id = bissue["id"]
    battachments = bexport.get_issue_attachments(issue_id)
    bcomments = bexport.get_issue_comments(issue_id)
    bchanges = bexport.get_issue_changes(issue_id)

    issue_body = replace_links_to_users(
        construct_gissue_body(bissue, battachments, attachment_gist_by_issue_id)
    )

    # Construct comments
    comments = []
    comments += construct_gissue_comments(bcomments)
    comments += construct_gissue_comments_for_changes(bchanges)
    comments.sort(key=lambda x: x["created_at"])

    # Construct labels
    labels = (
        map_bkind_to_glabels(bissue) +
        map_bstate_to_glabels(bissue) +
        map_bpriority_to_glabels(bissue) +
        map_bcomponent_to_glabels(bissue)
    )

    return {
        "issue": {
            "title": bissue["title"],
            "body": issue_body,
            "created_at": convert_date(bissue["created_on"]),
            "updated_at": convert_date(bissue["updated_on"]),
            "assignee": map_buser_to_guser(bissue["assignee"]),
            "closed": map_bstate_to_gstate(bissue) == "closed",
            "labels": list(set(labels)),
        },
        "comments": comments
    }


def construct_gissue_from_bpull_request(bpull_request, bexport):
    pull_request_id = bpull_request["id"]
    bcomments = bexport.get_pull_request_comments(pull_request_id)
    bactivity = bexport.get_pull_request_activity(pull_request_id)

    issue_body = replace_links_to_users(
        construct_gpull_request_body(bpull_request, bexport)
    )

    # Construct comments
    comments = []
    comments += construct_gissue_comments(bcomments, bexport, bpull_request)
    comments += construct_gissue_comments_for_activity(bactivity)
    comments.sort(key=lambda x: x["created_at"])

    # Construct labels
    labels = ["pull request"] + map_bstate_to_glabels(bpull_request)

    return {
        "issue": {
            "title": construct_gissue_title_for_pull_request(bpull_request),
            "body": issue_body,
            "created_at": convert_date(bpull_request["created_on"]),
            "updated_at": convert_date(bpull_request["updated_on"]),
            "assignee": map_buser_to_guser(bpull_request["author"]),
            "closed": map_bstate_to_gstate(bpull_request) == "closed",
            "labels": list(set(labels)),
        },
        "comments": comments
    }


def bitbucket_to_github(bexport, gimport, args):
    brepo_full_name = bexport.get_repo_full_name()
    issues_data = []
    attachment_gist_by_issue_id = {}

    # Retrieve data
    bissues = bexport.get_issues()
    bpull_requests = bexport.get_pull_requests()
    assert brepo_full_name in config.KNOWN_ISSUES_COUNT_MAPPING
    assert config.KNOWN_ISSUES_COUNT_MAPPING[brepo_full_name] == len(bissues)
    pull_requests_id_offset = config.KNOWN_ISSUES_COUNT_MAPPING[brepo_full_name]

    # Migrate attachments
    if not args.skip_attachments:
        print("Migrate bitbucket attachments to github...")
        for bissue in bissues:
            issue_id = bissue["id"]
            print("Migrate attachments for bitbucket issue #{}... [rate limiting: {}]".format(issue_id, gimport.get_remaining_rate_limit()))
            battachments = bexport.get_issue_attachments(issue_id)
            if battachments:
                gist_data = construct_gist_from_bissue_attachments(bissue, bexport)
                gist = gimport.get_or_create_gist_by_description(gist_data)
                attachment_gist_by_issue_id[issue_id] = gist
    else:
        print("Warning: migration of bitbucket attachments to github has been skipped.")

    # Prepare issues
    print("Prepare github issues...")
    for bissue in bissues:
        issue_id = bissue["id"]
        print("Prepare github issue #{} from bitbucket issue...".format(issue_id))
        gissue = construct_gissue_from_bissue(bissue, bexport, attachment_gist_by_issue_id)
        issues_data.append(gissue)

    for bpull_request in bpull_requests:
        issue_id = bpull_request["id"] + pull_requests_id_offset
        print("Prepare github issue #{} from bitbucket pull request...".format(issue_id))
        gissue = construct_gissue_from_bpull_request(bpull_request, bexport)
        issues_data.append(gissue)

    # Upload github issues
    print("Upload github issues...")
    existing_gissues = gimport.get_issues()
    for issue_id in range(1, len(existing_gissues) + 1):
        existing_gissue = existing_gissues[issue_id - 1]
        assert existing_gissue.number == issue_id
        print("Upload github issue #{}... [rate limiting: {}]".format(issue_id, gimport.get_remaining_rate_limit()))
        if issue_id > len(issues_data):
            print("Error: existing github issue #{} should not exist.".format(issue_id))
            existing_gissue.edit(state="closed")
        else:
            gimport.update_issue_with_comments(existing_gissue, issues_data[issue_id - 1])

    for issue_id in range(len(existing_gissues) + 1, len(issues_data) + 1):
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
        for bcomment in bexport.get_issue_comments(bissue_id).values():
            bnicknames.add(bcomment["user"]["nickname"])
    for bpull_request in bpull_requests:
        bpull_request_id = bpull_request["id"]
        if bpull_request_id % 10 == 0:
            print("Checking bitbucket pull request #{}...".format(bpull_request_id))
        if bpull_request["author"] is not None:
            bnicknames.add(bpull_request["author"]["nickname"])
        for bparticipant in bpull_request["participants"]:
            bnicknames.add(bparticipant["user"]["nickname"])
        for breviewer in bpull_request["reviewers"]:
            bnicknames.add(breviewer["nickname"])
        for bcomment in bexport.get_issue_comments(bissue_id).values():
            bnicknames.add(bcomment["user"]["nickname"])
        if (bpull_request["source"]["repository"] is None) != (bpull_request["source"]["commit"] is None):
            print("Info: source repository is '{}', but commit is '{}'".format(
                bpull_request["source"]["repository"],
                bpull_request["source"]["commit"]
            ))
        if (bpull_request["destination"]["repository"] is None) != (bpull_request["destination"]["commit"] is None):
            print("Info: destination repository is '{}', but commit is '{}'".format(
                bpull_request["destination"]["repository"],
                bpull_request["destination"]["commit"]
            ))
        if bpull_request["destination"]["repository"] is None:
            print("Info: destination repository is None")
        if bpull_request["source"]["branch"] is None:
            print("Info: source branch is None")
        if bpull_request["destination"]["branch"] is None:
            print("Info: destination branch is None")
    for nickname in bnicknames:
        if nickname not in config.USER_MAPPING:
            print("Warning: bitbucket user '{}' is not configured in USER_MAPPING.".format(nickname))


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
        "--skip-attachments",
        help="Skip the migration of attachments (development only)",
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
    gimport = GithubImport(args.github_access_token, args.github_repository, debug=False)
    if args.check:
        check(bexport=bexport, gimport=gimport, args=args)
    else:
        bitbucket_to_github(bexport=bexport, gimport=gimport, args=args)


if __name__ == "__main__":
    main()
