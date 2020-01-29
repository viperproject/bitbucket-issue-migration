#!/usr/bin/python3
import argparse
import re
from hg_repo.repo import HgRepo

# This script takes a Mercurial repo and checks (using "hg heads -t") whether a branch has two or more heads and fixes
# that by creating a uniquely named branch per head

class BranchHead:
    def __init__(self, branch_name, rev):
        self.branch_name = branch_name
        self.rev = rev

def unique_branch_per_head(repo, args):
    branch_heads = get_heads(repo)
    # create a dictionary mapping branch_name to a list of heads:
    branch_map = {}
    for branch_head in branch_heads:
        if branch_head.branch_name in branch_map:
            branch_map[branch_head.branch_name].append(branch_head)
        else:
            branch_map[branch_head.branch_name] = [branch_head]
    #iterate over branch names and create a new branch with an unique name:
    for branch_name in branch_map:
        if len(branch_map[branch_name]) <= 1:
            continue
        for head in branch_map[branch_name]:
            new_branch_name = get_unique_branch_name(repo, branch_name)
            create_branch(repo, head.rev, new_branch_name, args)


def get_heads(repo):
    res = repo.hg_command("heads", "-t", "-T", "{branch},{rev};")
    branch_rev_re = re.compile(r'([^,;]*),([^,;]*);')
    matches = branch_rev_re.finditer(res)
    branch_heads = [BranchHead(match.group(1), match.group(2)) for match in matches]
    return branch_heads


# append "_<id>" to branch_name and increase it until it is unique
def get_unique_branch_name(repo, branch_name):
    id = 0
    is_unique = False
    existing_branches = repo.get_branch_names()
    new_name = None
    while not is_unique:
        new_name = "{branch_name}_{id}".format(branch_name=branch_name, id=id)
        is_unique = new_name not in existing_branches
        id += 1
    return new_name


def create_branch(repo, rev, branch_name, args):
    if args.dry_run:
        print("hg_update {rev}".format(rev=rev))
        print("hg_branch {branch_name}".format(branch_name=branch_name))
        print("hg_commit \"Creates branch {branch_name}\"".format(branch_name=branch_name))
    else:
        repo.hg_update(rev)
        repo.hg_branch(branch_name)
        repo.hg_commit("Creates branch {branch_name}".format(branch_name=branch_name))


def create_parser():
    parser = argparse.ArgumentParser(
        prog="fix-repo",
        description="A tool to check and prepare a Mercurial repo before converting it to git."
    )
    parser.add_argument(
        "-r", "--repo",
        help="Path to the existing Mercurial repo",
        required=True
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help=(
            "Simulate actions of this script by printing actions "
            "instead of performing them"
        )
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    repo = HgRepo(args.repo)

    unique_branch_per_head(repo, args)


if __name__ == "__main__":
    main()
