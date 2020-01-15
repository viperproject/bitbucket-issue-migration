# Bitbucket To Github Issues Migration

The expected steps are as follows:
1. Migrate code & history of all repositories (using GitHub repo importer)
2. Run `migrate.py` to migrate the issues (again for all repositories)
3. Migrate pull requests (for all repositories)
4. Adapt `config.py` to correctly capture the Bitbucket repos, their GitHub correspondance, and the number of issues
5. Run `linking.py` to update links

Step 3 has to be performed after step 2, because GitHub uses the same enumeration for issues as well as PRs.
This ordering therefore enforces that PRs are offset by the number of issues.

This project reuses some code from https://github.com/jeffwidman/bitbucket-issue-migration

## Install dependencies
`pip3 install -r requirements.pip`
