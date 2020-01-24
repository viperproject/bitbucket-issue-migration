#!/usr/bin/env python3
import argparse
import re
import git
from commit_map.map import CommitMap


# creates a map from hg commit hash to git commit hash
def create_map(repo):
    git_commit_hashes = get_all_git_hashes(repo)
    map = {}
    for git_hash in git_commit_hashes:
        map[get_note_content(repo, git_hash)] = git_hash
    return map


def get_note_content(repo, git_commit_hash):
    # The command "git notes --ref refs/notes/hg show <commit hash>" returns the content of the note associated
    # with the commit
    return repo.git.notes("--ref", "refs/notes/hg", "show", git_commit_hash)


def get_all_git_hashes(repo):
    # The command "git notes --ref refs/notes/hg list" returns a list of all notes that are in refs/notes/hg
    # This list shows note objects together with the git commit hash
    # We're only interested in the git commit hash:
    note_list = repo.git.notes("--ref", "refs/notes/hg", "list")
    note_list_re = re.compile(r'(\S+)\s(\S+)')
    matches = note_list_re.finditer(note_list)
    git_commit_hashes = [match.group(2) for match in matches]
    return git_commit_hashes


def create_parser():
    parser = argparse.ArgumentParser(
        prog="hg-git-commit-map",
        description="A tool to extract hg commit hashes from git notes and create a map from hg to git commit hash."
    )
    parser.add_argument(
        "-r", "--repo",
        help="Path to the git repo",
        required=True
    )
    parser.add_argument(
        "-o", "--output",
        help="Path to the mapping file that should be created",
        required=True
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    repo = git.Repo(args.repo)

    map = create_map(repo)
    commit_map = CommitMap(args.output)
    commit_map.set_map(map)
    commit_map.store_to_disk()


if __name__ == "__main__":
    main()
