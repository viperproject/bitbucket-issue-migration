
# Change this to your own target repo.
TARGET_REPO = 'fpoli/viper-silver'

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

# Bitbucket has several issue states.
# All states that are not listed in this set will be closed.
OPEN_ISSUE_STATES = {
    "open",
    "new",
    "on hold",
}
