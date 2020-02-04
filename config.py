# Github only accepts assignees from valid users. We map those users from bitbucket.
USER_MAPPING = {
    "fpoli_eth": "fpoli",
    "mueller55": "mueller55",
    "meilers": "marcoeilers",
    "arquintl": "arquintl",
    "gauravpartha": "gauravpartha",
    "gaurav_p": "gauravpartha",
    "Felale": "Felalolf",
    "vakaras": "vakaras",
    "mschwerhoff": "mschwerhoff",
    "fabiopakk": "fabiopakk",
    "arshavir": "aterga",
    "dohrau": "dohrau",
    # "alexander_summers": "alexander_summers",  # TODO
    # "martin_clochard": "martin_clochard",  # TODO
}

# We map bitbucket's issue "kind" to github "labels".
KIND_MAPPING = {
    "bug": "bug",
    "enhancement": "enhancement",
    "proposal": "proposal",
    "task": "task",
}

# We map bitbucket's issue "priority" to github "labels".
PRIORITY_MAPPING = {
    "trivial": "trivial",
    "minor": "minor",
    "major": "major",
    "critical": "critical",
    "blocker": "blocker",
}

# We map bitbucket's issue "component" to github "labels".
COMPONENT_MAPPING = {
    "Parser": "parser",
    "Consistency": "consistency",
    "Triggers": "triggers",
    "silver-obligations": "silver-obligations",
}

# The only github states are "open" and "closed".
# Therefore, we map some bitbucket states to github "labels".
STATE_MAPPING = {
    "on hold": "on hold",
    "invalid": "invalid",
    "duplicate": "duplicate",
    "wontfix": "wontfix",
    "resolved": None,
    "new": None,
    "open": None,
    "closed": None,
    "DECLINED": "declined",
    "MERGED": "merged",
    "SUPERSEDED": "superseeded",
    "OPEN": None,
}

# Bitbucket has several issue and pull request states.
# All states that are not listed in this set will be closed.
OPEN_ISSUE_OR_PULL_REQUEST_STATES = {
    "open",
    "new",
    "on hold",
    "OPEN",
}

# Mapping of known Bitbucket to their corresponding GitHub repo
# This information is used to convert links
KNOWN_REPO_MAPPING = {
    "viperproject/silver": "viperproject/silver",
    "viperproject/carbon": "viperproject/carbon",
    "viperproject/silicon": "viperproject/silicon",
    "viperproject/viperserver": "viperproject/viperserver",
}

# Mapping of known Bitbucket repos to their number of issues.
# This information is used to correctly account for the offset
# of PRs' IDs
KNOWN_ISSUES_COUNT_MAPPING = {
    "viperproject/silver": 300,
    "viperproject/carbon": 295,
    "viperproject/silicon": 405,
    "viperproject/viperserver": 0,
}

KNOWN_CMAP_PATHS = {
    "viperproject/silver": "migration_data/silver_cmap.txt",
    "viperproject/carbon": "migration_data/carbon_cmap.txt",
    "viperproject/silicon": "migration_data/silicon_cmap.txt",
    "viperproject/viperserver": "migration_data/viperserver_cmap.txt",
}
