# Github only accepts assignees from valid users. We map those users from bitbucket.
USER_MAPPING = {
}

# We map bitbucket's issue "kind" to github "labels".
KIND_MAPPING = {
    "task": "enhancement",
    "proposal": "suggestion",
}

# The only github states are "open" and "closed".
# Therefore, we map some bitbucket states to github "labels".
STATE_MAPPING = {
    "on hold": "suggestion",
}

# Bitbucket has several issue and pull request states.
# All states that are not listed in this set will be closed.
OPEN_ISSUE_OR_PULL_REQUEST_STATES = {
    "open",
    "new",
    "on hold",
}

# Mapping of known Bitbucket to their corresponding GitHub repo
# This information is used to convert links
KNOWN_REPO_MAPPING = {
    "viperproject/silver": "viperproject/silver",
    #"viperproject/carbon": "viperproject/carbon",
    #"viperproject/silicon": "viperproject/silicon",
    #"viperproject/viperserver": "viperproject/viperserver",
}

# Mapping of known Bitbucket repos to their number of issues.
# This information is used to correctly account for the offset
# of PRs' IDs
KNOWN_ISSUES_COUNT_MAPPING = {
    "viperproject/silver": 300,
    #"viperproject/carbon": ,
    #"viperproject/silicon": ,
    #"viperproject/viperserver": ,
}
