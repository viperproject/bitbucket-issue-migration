#!/usr/bin/env python3
import argparse
import config
import os
from subprocess import check_call
import pathlib
from send2trash import send2trash
from github import Github
from github.GithubException import GithubException
#from getpass import getpass
import datetime

ROOT = os.path.abspath(os.path.dirname(__file__))
MIGRATION_DATA_DIR = os.path.join(ROOT, "migration_data")


def bitbucket_repo_url(repo):
    return "ssh://hg@bitbucket.org/" + repo


def github_repo_url(repo):
    return "git@github.com:" + repo + ".git"


def execute(cmd, *args, **kwargs):
    print("> '{}'".format(cmd))
    check_call(cmd, *args, shell=True, **kwargs)


def step(msg):
    now = datetime.datetime.now()
    time = now.strftime("%Y-%m-%d %H:%M:%S")
    print("\n[{}] === {}...".format(time, msg))


def is_github_repo_empty(github, grepo):
    repo = github.get_repo(grepo)
    try:
        repo.get_contents("/")
        return False
    except GithubException as e:
        return e.args[1]["message"] == "This repository is empty."


def create_parser():
    parser = argparse.ArgumentParser(
        prog="migrate",
        description="Migrate mercurial repositories from Bitbucket to Github"
    )
    parser.add_argument(
        "-t", "--github-access-token",
        help="Github Access Token",
        required=True
    )
    parser.add_argument(
        "--hg-fast-export-path",
        help="Path to the hg-fast-export.sh script",
        required=True
    )
    parser.add_argument(
        "--hg-authors-map",
        help="Path to the author mapping file required by hg-fast-export.sh",
        required=True
    )
    parser.add_argument(
        "--hg-branches-map",
        help="Path to the branch mapping file required by hg-fast-export.sh",
        required=True
    )
    parser.add_argument(
        "--bitbucket-username",
        help="Bitbucket username",
        required=True
    )
    parser.add_argument(
        "--bitbucket-password",
        help="Bitbucket password"
    )
    parser.add_argument(
        "--skip-stuff",
        help="Skip some stuff (development only!)",
        action="store_true"
    )
    parser.add_argument(
        "--skip-attachments",
        help="Skip the migration of attachments (development only!)",
        action="store_true"
    )
    parser.add_argument(
        "bitbucket_repositories",
        nargs="+",
        help="List of the Bitbucket repositories that should migrate to Github"
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    repositories_to_migrate = {
        brepo: config.KNOWN_REPO_MAPPING[brepo]
        for brepo in args.bitbucket_repositories
    }
    print("Bitbucket repositories to be migrated: {}".format(
        ", ".join(repositories_to_migrate.keys())
    ))

    github = Github(args.github_access_token, timeout=30, retry=3, per_page=100)

    args.hg_authors_map = os.path.abspath(args.hg_authors_map)
    while not os.path.isfile(args.hg_authors_map):
        print("Error: The author mapping file '{}' does not exist. Please create it.".format(args.hg_authors_map))
        input("Press Enter to retry...")

    args.hg_branches_map = os.path.abspath(args.hg_branches_map)
    while not os.path.isfile(args.hg_branches_map):
        print("Error: The branch mapping file '{}' does not exist. Please create it.".format(args.hg_branches_map))
        input("Press Enter to retry...")

    #if args.bitbucket_password is None:
    #    args.bitbucket_password = getpass(prompt="Password of Bitbucket's user '{}': ".format(args.bitbucket_username))

    if not args.skip_stuff:
        for brepo, grepo in repositories_to_migrate.items():
            step("Cloning bitbucket repository '{}' to local mercurial repository".format(brepo))
            hg_folder = os.path.join(MIGRATION_DATA_DIR, "bitbucket", brepo)
            brepo_url = bitbucket_repo_url(brepo)
            if os.path.isdir(hg_folder):
                send2trash(hg_folder)
            pathlib.Path(hg_folder).mkdir(parents=True, exist_ok=True)
            execute("hg clone " + brepo_url + " " + hg_folder, cwd=MIGRATION_DATA_DIR)

        for brepo, grepo in repositories_to_migrate.items():
            hg_folder = os.path.join(MIGRATION_DATA_DIR, "bitbucket", brepo)
            step("Importing forks of bitbucket repository '{}' into local mercurial repository".format(brepo))
            execute("./import-forks.py --verbose --repo {} --bitbucket-repository {} {}{}".format(
                hg_folder,
                brepo,
                "--bitbucket-username {} ".format(args.bitbucket_username) if args.bitbucket_username is not None else "",
                "--bitbucket-password {} ".format(args.bitbucket_password) if args.bitbucket_password is not None else "",
            ), cwd=ROOT)

        for brepo, grepo in repositories_to_migrate.items():
            step("Preparing local git repository for '{}'".format(grepo))
            git_folder = os.path.join(MIGRATION_DATA_DIR, "github", grepo)
            if os.path.isdir(git_folder):
                send2trash(git_folder)
            pathlib.Path(git_folder).mkdir(parents=True, exist_ok=True)
            execute("git init", cwd=git_folder)
            execute("git config core.ignoreCase false", cwd=git_folder)

        for brepo, grepo in repositories_to_migrate.items():
            step("Converting local mercurial repository of '{}' to git".format(brepo))
            hg_folder = os.path.join(MIGRATION_DATA_DIR, "bitbucket", brepo)
            git_folder = os.path.join(MIGRATION_DATA_DIR, "github", grepo)
            execute("{} -r {} -A {} -B {} --hg-hash ".format(
                args.hg_fast_export_path,
                hg_folder,
                args.hg_authors_map,
                args.hg_branches_map
            ), cwd=git_folder)

        for brepo, grepo in repositories_to_migrate.items():
            step("Mapping local mercurial commit hashes of '{}' to git".format(brepo))
            git_folder = os.path.join(MIGRATION_DATA_DIR, "github", grepo)
            execute("./hg-git-commit-map.py --repo {} --bitbucket-repository {}".format(
                git_folder,
                brepo
            ), cwd=ROOT)

        for brepo, grepo in repositories_to_migrate.items():
            step("Adding remote github '{}' to local git repository".format(grepo))
            git_folder = os.path.join(MIGRATION_DATA_DIR, "github", grepo)
            execute("git remote add origin {}".format(
                github_repo_url(grepo)
            ), cwd=git_folder)

    for brepo, grepo in repositories_to_migrate.items():
        step("Checking github repository '{}'".format(grepo))
        while not is_github_repo_empty(github, grepo):
            print("Error: Github repository '{}' is non-empty. Please delete and recreate it.".format(grepo))
            input("Press Enter to retry...")

    for brepo, grepo in repositories_to_migrate.items():
        step("Pushing local git repository to github repository '{}'".format(grepo))
        git_folder = os.path.join(MIGRATION_DATA_DIR, "github", grepo)
        execute("git push --set-upstream origin master", cwd=git_folder)
        execute("git push --all origin", cwd=git_folder)
        execute("git push --tags origin", cwd=git_folder)

    for brepo, grepo in repositories_to_migrate.items():
        step("Migrate issues and pull requests of bitbucket repository '{}' to github".format(brepo))
        execute("./migrate-discussions.py {} --github-access-token {} --bitbucket-repository {} --github-repository {}".format(
            "--skip-attachments" if args.skip_attachments else "",
            args.github_access_token,
            brepo,
            grepo
        ), cwd=ROOT)


if __name__ == "__main__":
    main()
