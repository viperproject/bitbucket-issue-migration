#!/usr/bin/env python3
import argparse
import re
from hg_repo.repo import HgRepo
from src.bitbucket import BitbucketExport


def get_bitbucket_base_url():
    return "ssh://hg@bitbucket.org/"


class ForkCommit:
    def __init__(self, fork, rev_hash):
        self.fork = fork
        self.rev_hash = rev_hash


class BranchHead:
    def __init__(self, branch_name, rev_hash):
        self.branch_name = branch_name
        self.rev_hash = rev_hash


def get_fork_name(pr):
    return pr["source"]["repository"]["full_name"]


def get_fork_rev_hash(pr):
    return pr["source"]["commit"]["hash"]


def get_fork_commit_url(pr):
    return pr["source"]["commit"]["links"]["self"]["href"]


def get_fork_commits(bexport, args):
    def is_open(pr):
        return pr["state"] == "OPEN"
    pull_requests = bexport.get_pulls()
    open_prs = list(filter(is_open, pull_requests))
    fork_commits = []
    for pr in open_prs:
        # check if commit still exists:
        exists = bexport.session.head(get_fork_commit_url(pr)).status_code == 200
        if exists:
            fork_commits.append(ForkCommit(get_fork_name(pr), get_fork_rev_hash(pr)))
        else:
            print("commit {} of fork {} does not exist => skipped".format(get_fork_rev_hash(pr), get_fork_name(pr)))
    return fork_commits


def import_fork_commit(repo, fork_commit, args):
    fork_url = get_bitbucket_base_url() + fork_commit.fork
    if args.verbose:
        print("pull -r {} {}".format(fork_commit.rev_hash, fork_url))
    repo.hg_command("pull", "-r", fork_commit.rev_hash, fork_url)


# returns the ForkCommit with rev_hash (resp. a prefix of rev_hash), otherwise None
def get_fork_commit(fork_commits, rev_hash):
    for fork_commit in fork_commits:
        if rev_hash.startswith(fork_commit.rev_hash):
            return fork_commit
    return None


def create_branch_per_fork_commit(repo, fork_commits, args):
    branch_heads = get_heads(repo)
    # iterate over heads and create a branch for heads that are in fork_commits
    # (except if the original repo was args.bitbucket_repository):
    for branch_head in branch_heads:
        fork_commit = get_fork_commit(fork_commits, branch_head.rev_hash)
        if fork_commit is None:
            continue
        if fork_commit.fork == args.bitbucket_repository:
            if args.verbose:
                print("not creating a new branch for {} because it was already located in this repo".format(fork_commit.rev_hash))
            continue
        branch_name = "{fork_name}/{branch}".format(fork_name=fork_commit.fork, branch=branch_head.branch_name)
        create_branch(repo, fork_commit.rev_hash, branch_name, args)


def unique_branch_per_head(repo, args):
    branch_heads = get_heads(repo)
    # create a dictionary mapping branch_name to a list of heads:
    branch_map = {}
    for branch_head in branch_heads:
        if branch_head.branch_name in branch_map:
            branch_map[branch_head.branch_name].append(branch_head)
        else:
            branch_map[branch_head.branch_name] = [branch_head]
    # in case there are non-unique heads, create a branch for each head with an unique name:
    for branch_name in branch_map:
        if len(branch_map[branch_name]) <= 1:
            continue
        for head in branch_map[branch_name]:
            new_branch_name = get_unique_branch_name(repo, branch_name)
            create_branch(repo, head.rev_hash, new_branch_name, args)


def get_heads(repo):
    res = repo.hg_command("heads", "-t", "-T", "{branch},{node};")
    branch_rev_hash_re = re.compile(r'([^,;]*),([^,;]*);')
    matches = branch_rev_hash_re.finditer(res)
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


def create_branch(repo, rev_hash, branch_name, args):
    if args.verbose:
        print("hg_update {node}".format(node=rev_hash))
        print("hg_branch {branch_name}".format(branch_name=branch_name))
        print("hg_commit \"Creates branch {branch_name}\"".format(branch_name=branch_name))
    repo.hg_update(rev_hash)
    repo.hg_branch(branch_name)
    repo.hg_commit("Creates branch {branch_name}".format(branch_name=branch_name))


def create_master_branch(repo, args):
    # adding a commit creating the branch "master" is already enough such that fast-export picks the commits preceding
    # the master branch creation commit for being on the master branch. It looks like fast-export uses the linear
    # revision numbering and starts at the highest (i.e. latest).
    heads = get_heads(repo)
    default_heads = list(filter(lambda head: head.branch_name == "default", heads))
    if len(default_heads) == 0:
        print("no default head found => skipping master branch creation")
        return
    if len(default_heads) > 1:
        print("multiple default heads found => skipping master branch creation")
        return
    create_branch(repo, default_heads[0].rev_hash, "master", args)


def create_parser():
    parser = argparse.ArgumentParser(
        prog="import-forks",
        description="A tool to pull all commits of forks of which an open pull request exists"
    )
    parser.add_argument(
        "-r", "--repo",
        help="Path to the existing (main) Mercurial repo",
        required=True
    )
    parser.add_argument(
        "-b", "--bitbucket-repository",
        help="Full name of the Bitbucket repository (e.g. viperproject/silver)",
        required=True
    )
    parser.add_argument(
        "-bu", "--bitbucket-username"
    )
    parser.add_argument(
        "-bp", "--bitbucket-password",
        help="App password for Bitbucket account",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Prints all write Hg command to stdout"
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    repo = HgRepo(args.repo)
    bexport = BitbucketExport(args.bitbucket_repository, args.bitbucket_username, args.bitbucket_password)

    fork_commits = get_fork_commits(bexport, args)
    for fork_commit in fork_commits:
        import_fork_commit(repo, fork_commit, args)
    create_branch_per_fork_commit(repo, fork_commits, args)
    unique_branch_per_head(repo, args)
    create_master_branch(repo, args)


if __name__ == "__main__":
    main()
