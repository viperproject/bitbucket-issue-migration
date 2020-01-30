import re
import config


class CommitMap:
    def __init__(self):
        self.maps = {}
        self.deserialize_re = re.compile(r'(\S+),(\S+)')

    def set_map(self, repo_name, map):
        self.maps[repo_name] = map

    def serialize_entry(self, hg_hash, git_hash):
        return "{},{}\n".format(hg_hash, git_hash)

    def deserialize_line(self, line):
        match = self.deserialize_re.match(line)
        return match.group(1), match.group(2)

    def check_uniqueness(self):
        # all hg as well as git commit hashes should be unique (including their 7 character prefix):
        print("checking uniqueness of hg and git hashes...")
        for repo1 in self.maps:
            for repo2 in self.maps:
                for hg_commit_1 in self.maps[repo1]:
                    short_hg_commit_1 = hg_commit_1[:7]
                    for hg_commit_2 in self.maps[repo2]:
                        if hg_commit_2.startswith(short_hg_commit_1) and not (hg_commit_1 == hg_commit_2 and repo1 == repo2):
                            print("hg commit {} or a prefix of it is not unique".format(hg_commit_1))
                for git_commit_1 in self.maps[repo1].values():
                    short_git_commit_1 = git_commit_1[:7]
                    for git_commit_2 in self.maps[repo2].values():
                        if git_commit_2.startswith(short_git_commit_1) and not (git_commit_1 == git_commit_2 and repo1 == repo2):
                            print("git commit {} or a prefix of it is not unique".format(git_commit_1))
        print("check done")

    def load_from_disk(self):
        self.maps = {}
        for repo_name in config.KNOWN_CMAP_PATHS:
            path = config.KNOWN_CMAP_PATHS[repo_name]
            self.maps[repo_name] = {}
            with open(path, "r") as file:
                lines = file.readlines()
                for line in lines:
                    hg_hash, git_hash = self.deserialize_line(line)
                    self.maps[repo_name][hg_hash] = git_hash
        self.check_uniqueness()

    def store_to_disk(self):
        for repo_name in self.maps:
            if repo_name not in config.KNOWN_CMAP_PATHS:
                print("config.KNOWN_CMAP_PATHS does not specify a path for {}".format(repo_name))
                return
            path = config.KNOWN_CMAP_PATHS[repo_name]
            with open(path, "w") as file:
                for hg_hash, git_hash in self.maps[repo_name].items():
                    file.write(self.serialize_entry(hg_hash, git_hash))

    def get_repo_name(self, hg_hash):
        """Maps the hash of a mercurial commit to the bitbucket repo name.
        """
        for repo_name in self.maps:
            for known_hg_hash in self.maps[repo_name]:
                if known_hg_hash.startswith(hg_hash):
                    return repo_name
        return None

    def convert_commit_hash(self, hg_hash):
        """Maps the hash of a mercurial commit to the corresponding git commit hash.
        Returns None in case no matching has been found.
        """
        for repo_name in self.maps:
            for known_hg_hash in self.maps[repo_name]:
                if known_hg_hash.startswith(hg_hash):
                    return self.maps[repo_name][known_hg_hash]
        return None

    def convert_branch_name(self, branch, repo=None, default_repo=None):
        """Convert a branch of a bitbucket repo to the name of a github branch.
        """
        if repo == default_repo:
            if branch == "default":
                return "master"
            else:
                return branch
        else:
            return repo + "/" + branch
