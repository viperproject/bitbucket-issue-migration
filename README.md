# Bitbucket To Github Migration

The expected steps are as follows:
1. Migrate code & history of all repositories (using GitHub repo importer)
1.1. `python3 import-forks.py --repo <path to hg repo> --bitbucket-repository <e.g. viperproject/silver> --bitbucket-username <Bitbucket username> --bitbucket-password <Bitbucket app password>`
1.2. Create folder, `git init`, and `git config core.ignoreCase false`
1.3. Run `<path to hg-fast-export.sh> -r <path to hg repo> --hg-hash` in the git folder
1.4. Adapt `config.py` to have an entry for the bitbucket-repository in `KNOWN_CMAP_PATHS`
1.5. Run `python3 hg-git-commit-map.py --repo <path to git folder> --bitbucket-repository <e.g. viperproject/silver>`
2. Adapt `config.py` to correctly capture the Bitbucket repos, their GitHub correspondance, and the number of issues
3. Run `python3 migrate-discussions.py --github-access-token <GitHub access token> --bitbucket-repository <e.g. viperproject/silver> --github-repository <e.g. fpoli/viper-silver>` to migrate the issues and pull requests (again for all repositories)

This project reuses some code from https://github.com/jeffwidman/bitbucket-issue-migration and https://github.com/fkirc/bitbucket-issues-to-github


## Features

This script migrates:

* Bitbucket's attachments to Github's gists
* Bitbucket's issues `#1..#n` to Github's issues `#1..#n`
  * Bitbucket's issue changes and comments to Github's comments
  * Bitbucket's issue state, kind, priority and component to Github's labels
* Bitbucket's pull requests `#1..#m` to Github's issues `#(n+1)..#(n+m)`
  * Bitbucket's pull request activity and comments to Github's comments
  * Bitbucket's pull request state to Github's labels

Within a comment:

* Bitbucket's user mentions to Github's user mentions
* Bitbucket's issue and pull request links to Github's issue links
* ...


## Install dependencies

`pip3 install -r requirements.pip`
