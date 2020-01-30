import re


class CommitMap:
    def __init__(self, path):
        self.path = path
        self.map = None
        self.deserialize_re = re.compile(r'(\S+),(\S+)')

    def set_map(self, map):
        self.map = map

    def serialize_entry(self, hg_hash, git_hash):
        return "{},{}\n".format(hg_hash, git_hash)

    def deserialize_line(self, line):
        match = self.deserialize_re.match(line)
        return match.group(1), match.group(2)

    def load_from_disk(self):
        self.map = {}
        with open(self.path, "r") as file:
            lines = file.readlines()
            for line in lines:
                hg_hash, git_hash = self.deserialize_line(line)
                self.map[hg_hash] = git_hash

    def store_to_disk(self):
        with open(self.path, "w") as file:
            for hg_hash, git_hash in self.map.items():
                file.write(self.serialize_entry(hg_hash, git_hash))

    def convert_commit_hash(self, hash):
        """Maps the hash of a mercurial commit to the corresponding git commit hash.
        Returns None in case no matching has been found.
        """
        try:
            return self.map[hash]
        except KeyError:
            return None

    def convert_branch_name(self, branch_name, repo_name=None):
        """Convert a branch of a bitbucket repo to the name of a github branch.
        """
        if repo_name is None:
            return branch_name
        else:
            # TODO
            repo_name + "/" + branch_name
