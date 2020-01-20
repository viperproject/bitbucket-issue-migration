# Bitbucket To Github Migration

The expected steps are as follows:
1. Migrate code & history of all repositories (using GitHub repo importer)
2. Adapt `config.py` to correctly capture the Bitbucket repos, their GitHub correspondance, and the number of issues
3. Run `migrate.py` to migrate the issues and pull requests (again for all repositories)
4. Run `linking.py` to update links

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
