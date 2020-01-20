# Github only accepts assignees from valid users. We map those users from bitbucket.
USER_MAPPING = {
    #"Felale": "Felale"
    #"a_helfenstein": "a_helfenstein"
    #"mnovacek": "mnovacek"
    #"brotobia": "brotobia"
    #"gishors": "gishors"
    #"User a29c9": "User a29c9"
    #"OmerSakar": "OmerSakar"
    #"evolutics": "evolutics"
    #"abdelzaher": "abdelzaher"
    #"maurobringolf": "maurobringolf"
    #"flurischt": "flurischt"
    #"Korbinian Breu": "Korbinian Breu"
    #"wuestholz": "wuestholz"
    #"pgruntz": "pgruntz"
    #"martin_clochard": "martin_clochard"
    #"smbe19": "smbe19"
    #"stefanheule": "stefanheule"
    #"aurecchia": "aurecchia"
    #"bbrodowsky": "bbrodowsky"
    #"moknuese": "moknuese"
    #"Soothsilver": "Soothsilver"
    #"severinh": "severinh"
    #"caterinaurban": "caterinaurban"
    #"gaurav_p": "gaurav_p"
    #"rukaelin": "rukaelin"
    #"arshavir": "arshavir"
    #"a2scale": "a2scale"
    #"fabiopakk": "fabiopakk"
    #"meilers": "meilers"
    #"vakaras": "vakaras"
    #"alexander_summers": "alexander_summers"
    #"RKor": "RKor"
    #"mousam05": "mousam05"
    #"tierriminator": "tierriminator"
    #"streun": "streun"
    #"juhaszu": "juhaszu"
    #"seraiah": "seraiah"
    #"fpoli_eth": "fpoli_eth"
    #"robinsierra": "robinsierra"
    #"fhahn": "fhahn"
    #"nilsbecker_": "nilsbecker_"
    #"ntruessel": "ntruessel"
    #"mueller55": "mueller55"
    #"mschwerhoff": "mschwerhoff"
    #"klauserc": "klauserc"
    #"arquintl": "arquintl"
    #"sahil_rishi": "sahil_rishi"
    #"dohrau": "dohrau"
    #"krantikiran": "krantikiran"
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
