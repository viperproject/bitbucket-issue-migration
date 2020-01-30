import os
import subprocess
import re

class HgRepo:
    def __init__(self, path):
        self.path = path
        self.env = os.environ
        self.env[str('LANG')] = str('en_US')

    def hg_command(self, *args):
        cmd = ["hg", "--cwd", self.path, "--encoding", "UTF-8"] + list(args)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
        out, err = [x.decode("utf-8") for x in proc.communicate()]
        if proc.returncode:
            raise RuntimeError("cmd {} resulted in exit code {} ({})".format(" ".join(cmd), proc.returncode, err))
        return out


    def get_branch_names(self):
        res = self.hg_command("branches", "--template", "{branch};")
        branch_name_re = re.compile(r'([^;]*);')
        matches = branch_name_re.finditer(res)
        return [match.group(1) for match in matches]


    def hg_update(self, rev):
        self.hg_command("update", str(rev))


    def hg_branch(self, branch_name=None):
        args = ["branch"]
        if branch_name:
            args.append(branch_name)
        self.hg_command(*args)


    def hg_commit(self, msg):
        self.hg_command("commit", "-m", msg)
