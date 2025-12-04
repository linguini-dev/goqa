#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
import os
import requests
from rich.table import Table
from rich.console import Console

console = Console()


def parse_rfc3339(time_string: str) -> datetime:
    """
    Constructs and returns a datetime from a string in the rfc3339 time format.
    """
    return datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S")


def parse_since(since: str) -> str:
    """
    Takes input such as "1d" or "37h" and converts it into the rfc3339 time format.
    Substracts the resulting datetime from the current datetime.
    """
    now = datetime.now()
    value = int(since[:-1])
    unit = since[-1]

    if unit == "d":
        delta = timedelta(days=value)
    elif unit == "h":
        delta = timedelta(hours=value)
    else:
        raise ValueError("Invalid time unit. Use 'd' for days or 'h' for hours.")

    return (now - delta).strftime("%Y-%m-%dT%H:%M:%S")


def build_arg_parser():
    """
    Parses commandline arguments at runtime. The arguments are things like a Job's `id`, `group_id` and etc. other arguments by which a Job can be identified.
    """
    parser = argparse.ArgumentParser(description="OpenQA Vibes")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Get jobs command
    get_jobs_parser = subparsers.add_parser("get-jobs", help="Get jobs")
    get_jobs_parser.add_argument("--group-id", type=int, help="Filter by group ID")
    get_jobs_parser.add_argument("--status", type=str, help="Filter by status")
    get_jobs_parser.add_argument("--name", type=str, help="Filter by name")
    get_jobs_parser.add_argument("--since", type=str, help="Filter by time (e.g., '1d', '37h')")

    # Get builds command
    get_builds_parser = subparsers.add_parser("get-builds", help="Get builds")
    get_builds_parser.add_argument("--group-id", type=int, required=True, help="Filter by group ID")

    return parser.parse_args()


class Job:
    """
    Base class for Job-related actions. The class handles getting the Job's `id`, `group_id`, `status`, `name`, `t_finished` and triggering the Job to restart via the `restart` endpoint.
    """

    def __init__(self, client: 'APIClient', job_id: int, group_id: int, status: str, name: str, t_finished: str):
        self.client = client
        self.id = job_id
        self.group_id = group_id
        self.status = status
        self.name = name
        self.t_finished = t_finished

    def __str__(self) -> str:
        return f"Job {self.id}: {self.name} ({self.status})"

    def restart(self) -> dict:
        """
        Restarts the job.
        """
        return self.client.post(f"/api/v1/jobs/{self.id}/restart")


class JobCollection:
    """
    Class that handles grouping of Jobs, like grouping the Jobs by `status` and/or by `group_id`.
    """

    def __init__(self, client: 'APIClient'):
        self.client = client
        self.jobs = []

    def fetch(self, group_id: int = None, status: str = None, name: str = None, since: str = None) -> None:
        """
        Fetches jobs from the API.
        """
        params = {}
        if group_id:
            params["group_id"] = group_id
        if status:
            params["status"] = status
        if name:
            params["name"] = name
        if since:
            params["since"] = since

        data = self.client.get("/api/v1/jobs", params=params)
        for job_data in data.get("jobs", []):
            self.jobs.append(
                Job(
                    client=self.client,
                    job_id=job_data["id"],
                    group_id=job_data["group_id"],
                    status=job_data["result"],
                    name=job_data["name"],
                    t_finished=job_data["t_finished"],
                )
            )


class Build:
    """
    Base class for Build-related actions. The class handles getting the Build's `id` and all Jobs in the Build.
    """

    def __init__(self, build_id: str, status: str, total: int):
        self.id = build_id
        self.status = status
        self.total = total

    def __str__(self) -> str:
        return f"Build {self.id}: {self.status} ({self.total} jobs)"


class BuildCollection:
    """
    Class that handles grouping of Builds.
    """

    def __init__(self, client: 'APIClient'):
        self.client = client
        self.builds = []

    def fetch(self, group_id: int) -> None:
        """
        Fetches builds from the API.
        """
        data = self.client.get(f"/api/v1/job_groups/{group_id}/build_results")
        for build_data in data.get("build_results", []):
            self.builds.append(
                Build(
                    build_id=build_data["build"],
                    status="passed" if build_data["all_passed"] else "failed",
                    total=build_data["total"],
                )
            )


class APIClient:
    """
    Base class for handling all the requests to the API.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.api_key = os.environ.get("OPENQA_KEY")
        self.api_secret = os.environ.get("OPENQA_SECRET")
        if not self.api_key or not self.api_secret:
            raise ValueError("OPENQA_KEY and OPENQA_SECRET environment variables must be set.")

    def get(self, endpoint: str, params: dict = None) -> dict:
        """
        Makes a GET request to the API.
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, auth=(self.api_key, self.api_secret), params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str) -> dict:
        """
        Makes a POST request to the API.
        """
        url = f"{self.base_url}{endpoint}"
        response = requests.post(url, auth=(self.api_key, self.api_secret))
        response.raise_for_status()
        return response.json()


class Renderer:
    """
    Class that handles printing data in a table format. The table has the following data neatly organized: Job names, Job Ids, Builds, URLs to the Jobs, Status and when the Job finished.
    """

    def __init__(self, console: Console):
        self.console = console

    def render_jobs(self, jobs: list[Job]) -> None:
        """
        Renders a table of jobs.
        """
        table = Table(title="Jobs")
        table.add_column("Job ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Finished", style="yellow")
        table.add_column("URL", style="blue")

        for job in jobs:
            url = f"https://openqa.grouse.us/tests/{job.id}"
            table.add_row(
                str(job.id),
                job.name,
                job.status,
                job.t_finished,
                url,
            )

        self.console.print(table)

    def render_builds(self, builds: list[Build]) -> None:
        """
        Renders a table of builds.
        """
        table = Table(title="Builds")
        table.add_column("Build ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Total Jobs", style="yellow")

        for build in builds:
            table.add_row(
                build.id,
                build.status,
                str(build.total),
            )

        self.console.print(table)


def main():
    """
    Main function.
    """
    args = build_arg_parser()
    client = APIClient(base_url="https://openqa.grouse.us")
    renderer = Renderer(console)

    if args.command == "get-jobs":
        job_collection = JobCollection(client)
        since = parse_since(args.since) if args.since else None
        job_collection.fetch(
            group_id=args.group_id,
            status=args.status,
            name=args.name,
            since=since,
        )
        renderer.render_jobs(job_collection.jobs)
    elif args.command == "get-builds":
        build_collection = BuildCollection(client)
        build_collection.fetch(args.group_id)
        renderer.render_builds(build_collection.builds)


if __name__ == "__main__":
    main()
