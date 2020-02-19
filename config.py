# Mercurial user to be used for the commits of the migration
MIGRATION_COMMITS_USER = "Viper Admin <viper-admin@inf.ethz.ch>"

# Github only accepts assignees from valid users. We map those users from bitbucket.
USER_MAPPING = {
    "fpoli_eth": "fpoli",
    "{c2aa01d7-5a75-490b-9af8-c779a5a0d8e8}": "fpoli",
    "{557058:2a067556-b105-4ce3-b3ec-bf9ecac58455}": "fpoli",
    "mueller55": "mueller55",
    "{b724c0a3-39ff-41aa-b1fd-5f56de2abe11}": "mueller55",
    "{557058:bfefff28-2e68-4d1d-b0d5-69e5ce90efa7}": "mueller55",
    "meilers": "marcoeilers",
    "{7f85133f-0a10-4b92-8999-c63c441c5ccd}": "marcoeilers",
    "{557058:c6529106-a880-4ce3-af30-0f1e3c584455}": "marcoeilers",
    "arquintl": "arquintl",
    "{c1e08586-0797-4f40-94f9-6cce84e16840}": "arquintl",
    "{5c7fbff372cb04154791cfc1}": "arquintl",
    "gauravpartha": "gauravpartha",
    "{d31d5389-4b39-46ea-8214-9f3f9a87c500}": "gauravpartha",
    "{5c4ade80dcae4f5d16e79771}": "gauravpartha",
    "gaurav_p": "gauravpartha",
    "{deffc63b-6882-4dda-aa41-bf0851238cbc}": "gauravpartha",
    "{557058:a7f9ad30-ffe0-4a50-afeb-607147624427}": "gauravpartha",
    "Felale": "Felalolf",
    "{2d51ceff-d0c5-4656-b8a1-6147060ead9d}": "Felalolf",
    "{557058:e76ac194-2aec-4301-89de-bf67e80c92d0}": "Felalolf",
    "vakaras": "vakaras",
    "{6ad52865-3508-470f-b76f-d4b777004bd0}": "vakaras",
    "{557058:887dd121-6a5e-47e1-bb06-3d64b8fa29c9}": "vakaras",
    "mschwerhoff": "mschwerhoff",
    "{b28c5356-f751-4ded-a285-0889774978e0}": "mschwerhoff",
    "{557058:10d3684e-4a6c-47c2-84e0-bc1f2579e650}": "mschwerhoff",
    "fabiopakk": "fabiopakk",
    "{8c641d69-0c7a-47f1-aefb-296c96e018dc}": "fabiopakk",
    "{557058:50339889-65da-459d-811e-7532e71d77f6}": "fabiopakk",
    "arshavir": "aterga",
    "{d07d8b38-defa-4eea-91ba-ea6e15e195d3}": "aterga",
    "{557058:77dc96fb-1a0a-400d-b39a-ccabd91c98a0}": "aterga",
    "dohrau": "dohrau",
    "{2e15b3e2-8fde-4c2c-b460-c9e3f71e90ff}": "dohrau",
    "{557058:ea8a9b05-5424-439a-b424-c39ebb31013f}": "dohrau",
    "martin_clochard": "MartinClochard",
    "{bd18d17f-6685-43a9-ab7b-e5ad71669cb3}": "MartinClochard",
    "{5af1bdbc626b42214cd30659}": "MartinClochard",
    "alexander_summers": "alexanderjsummers",
    "{19f8d68f-a7da-4d75-a765-0393770be2de}": "alexanderjsummers",
    "{557058:978738dd-952f-4b9f-8e6f-7982e018475b}": "alexanderjsummers",
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
    "Consistency": "consistency",
    "Parser": "parser",
    "silver-obligations": "silver-obligations",
    "Triggers": "triggers",
    "Examples": "examples",
    "Functions": "functions",
    "Logging, Reporting, IDE": "logging-reporting-ide",
    "Magic Wands": "magic-wands",
    "Permissions": "permissions",
    "Quantified Permissions": "quantified-permissions",
    "Silver": "silver",
    "Z3": "z3"
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
    "viperproject/silver": 301,
    "viperproject/carbon": 296,
    "viperproject/silicon": 407,
    "viperproject/viperserver": 0,
}

KNOWN_CMAP_PATHS = {
    "viperproject/silver": "migration_data/silver_cmap.txt",
    "viperproject/carbon": "migration_data/carbon_cmap.txt",
    "viperproject/silicon": "migration_data/silicon_cmap.txt",
    "viperproject/viperserver": "migration_data/viperserver_cmap.txt",
}
