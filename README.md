# Bitbucket To Github Issues Migration

The expected steps are as follows:
1. Migrate code & history of all repositories (using GitHub repo importer)
2. Adapt `config.py` to correctly capture the Bitbucket repos, their GitHub correspondance, and the number of issues
3. Run `migrate.py` to migrate the issues and pull requests (again for all repositories)
4. Run `linking.py` to update links

This project reuses some code from https://github.com/jeffwidman/bitbucket-issue-migration and https://github.com/fkirc/bitbucket-issues-to-github

## Install dependencies

`pip3 install -r requirements.pip`
