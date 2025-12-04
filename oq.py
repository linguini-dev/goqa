#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
import requests
from rich.table import Table
from rich.console import Console

console = Console()


# ---------------------------------------------------------
#  Utility: RFC3339 parsing + since=Xd/Xh/Xm
# ---------------------------------------------------------
def parse_rfc3339(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def parse_since(expr: str):
    if not expr:
        return None
    units = {"d": "days", "h": "hours", "m": "minutes"}
    number = int(expr[:-1])
    unit = expr[-1]
    return datetime.utcnow() - timedelta(**{units[unit]: number})


# ---------------------------------------------------------
#  Models (Job, Build) + Collections
# ---------------------------------------------------------
class Job:
    def __init__(self, data, base_url, client):
        self.data = data
        self.base_url = base_url
        self.client = client

    @property
    def id(self): return self.data.get("id")

    @property
    def name(self): return self.data.get("name")

    @property
    def status(self): return self.data.get("status")

    @property
    def group_id(self): return self.data.get("group_id")

    @property
    def time_finished(self):
        t = self.data.get("time_finished")
        return parse_rfc3339(t) if t else None

    @property
    def url(self):
        return f"{self.base_url}/api/v1/jobs/{self.id}"

    def restart(self):
        return self.client.job_restart(self.id)


class JobCollection:
    def __init__(self, jobs):
        self.jobs = jobs  # list[Job]

    def filter(self, **filters):
        result = self.jobs

        if "since" in filters:
            cutoff = parse_since(filters.pop("since"))
            result = [j for j in result if j.time_finished and j.time_finished >= cutoff]

        for k, v in filters.items():
            result = [j for j in result if j.data.get(k) == v]

        return JobCollection(result)

    def group_by(self, key="group_id"):
        groups = {}
        for j in self.jobs:
            gid = getattr(j, key)
            groups.setdefault(gid, []).append(j)
        return groups


class Build:
    def __init__(self, data, base_url, client):
        self.data = data
        self.base_url = base_url
        self.client = client

    @property
    def id(self): return self.data.get("id")

    def jobs(self, **filters):
        raw = self.client.build_jobs(self.id, **filters)
        wrapped = [Job(j, self.base_url, self.client) for j in raw]
        return JobCollection(wrapped)


class BuildCollection:
    def __init__(self, builds):
        self.builds = builds


# ---------------------------------------------------------
#  API Client (OOP-friendly)
# ---------------------------------------------------------
class APIClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _req(self, method, path, params=None):
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, params=params)
        resp.raise_for_status()
        return resp.json()

    # JOBS
    def jobs(self, **filters):
        raw = self._req("GET", "/api/v1/jobs", params=filters)
        jobs = [Job(j, self.base_url, self) for j in raw]
        return JobCollection(jobs)

    def job_restart(self, job_id):
        return self._req("POST", f"/api/v1/jobs/{job_id}/restart")

    # BUILDS
    def builds(self, **filters):
        raw = self._req("GET", "/api/v1/builds", params=filters)
        builds = [Build(b, self.base_url, self) for b in raw]
        return BuildCollection(builds)

    def build_jobs(self, build_id, **filters):
        return self._req("GET", f"/api/v1/builds/{build_id}/jobs", params=filters)


# ---------------------------------------------------------
#  Renderer (Rich tables)
# ---------------------------------------------------------
class Renderer:
    @staticmethod
    def jobs_table(job_collection: JobCollection):
        groups = job_collection.group_by("group_id")

        for gid, jobs in groups.items():
            console.print(f"\n[bold cyan]Group {gid}[/bold cyan]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", width=8)
            table.add_column("Status", width=10)
            table.add_column("Name", width=40)
            table.add_column("Finished", width=25)
            table.add_column("URL")

            for job in jobs:
                table.add_row(
                    str(job.id),
                    job.status,
                    job.name,
                    job.data.get("time_finished", ""),
                    job.url,
                )

            console.print(table)


# ---------------------------------------------------------
#  CLI
# ---------------------------------------------------------
def build_arg_parser():
    p = argparse.ArgumentParser()
    p.add_argument("--api", required=True)
    p.add_argument("--token", required=False)

    sub = p.add_subparsers(dest="cmd")

    # get jobs
    g = sub.add_parser("get-jobs")
    g.add_argument("--status")
    g.add_argument("--arch")
    g.add_argument("--build_number")
    g.add_argument("--group_id")
    g.add_argument("--since")

    # restart jobs
    r = sub.add_parser("restart-jobs")
    r.add_argument("--status")
    r.add_argument("--arch")
    r.add_argument("--build_number")
    r.add_argument("--group_id")
    r.add_argument("--since")

    # build jobs
    bj = sub.add_parser("get-build-jobs")
    bj.add_argument("build_id")
    bj.add_argument("--status")
    bj.add_argument("--arch")
    bj.add_argument("--since")

    return p


def main():
    parser = build_arg_parser()
    a = parser.parse_args()

    if not a.cmd:
        parser.print_help()
        return

    client = APIClient(a.api, token=a.token)

    if a.cmd == "get-jobs":
        jc = client.jobs(**{k: v for k, v in vars(a).items()
                            if k in ["status", "arch", "build_number", "group_id", "since"] and v})
        Renderer.jobs_table(jc)
        return

    if a.cmd == "restart-jobs":
        jc = client.jobs(**{k: v for k, v in vars(a).items()
                            if k in ["status", "arch", "build_number", "group_id", "since"] and v})
        for j in jc.jobs:
            j.restart()
            console.print(f"[green]Restarted job {j.id}[/green]")
        return

    if a.cmd == "get-build-jobs":
        jc = client.jobs()  # placeholder, we call via Build
        raw = client.build_jobs(a.build_id,
                                **{k: v for k, v in vars(a).items()
                                   if k in ["status", "arch", "since"] and v})
        wrapped = [Job(j, a.api, client) for j in raw]
        Renderer.jobs_table(JobCollection(wrapped))
        return


if __name__ == "__main__":
    main()
