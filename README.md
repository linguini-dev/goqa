# OpenQA Vibes

OpenQA Vibes is a command-line tool for interacting with the OpenQA API. It can be used to fetch and display information about jobs and builds, and it can also be used to restart jobs.

## Installation

To install the dependencies, run the following command:

```
pip install -r requirements.txt
```

## Configuration

The script uses environment variables to authenticate with the OpenQA API. You will need to set the following environment variables:

- `OPENQA_KEY`: Your OpenQA API key.
- `OPENQA_SECRET`: Your OpenQA API secret.

## Usage

### Get Jobs

To get a list of jobs, use the `get-jobs` subcommand. You can filter the jobs by group ID, status, name, and time.

```
./vibes.py get-jobs --group-id 123 --status failed --name "my-job" --since 1d
```

### Get Builds

To get a list of builds, use the `get-builds` subcommand. You will need to provide a group ID.

```
./vibes.py get-builds --group-id 123
```
