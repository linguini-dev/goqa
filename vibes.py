#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
import requests
from rich.table import Table
from rich.console import Console

console = Console()


def parse_rfc3339(time_string: str) -> datetime:
    """
    Constructs and returns a datetime from a string in the rfc3339 time format.
    """


def parse_since():
    """
    Takes input such as "1d" or "37h" and converts it into the rfc3339 time format.
    Substracts the resulting datetime from the current datetime.
    """


def build_arg_parser():
  """
  Parses commandline arguments at runtime. The arguments are things like a Job's `id`, `group_id` and etc. other arguments by which a Job can be identified.
  """
  return p


class Job:
    """
    Base class for Job-related actions. The class handles getting the Job's `id`, `group_id`, `status`, `name`, `t_finished` and triggering the Job to restart via the `restart` endpoint.
    """


class JobCollection:
    """
    Class that handles grouping of Jobs, like grouping the Jobs by `status` and/or by `group_id`.
    """


class Build:
    """
    Base class for Build-related actions. The class handles getting the Build's `id` and all Jobs in the Build.
    """


class BuildCollection:
    """
    Class that handles grouping of Builds.
    """

class APIClient:
    """
    Base class for handling all the requests to the API. 
    """


class Renderer:
    """
    Class that handles printing data in a table format. The table has the following data neatly organized: Job names, Job Ids, Builds, URLs to the Jobs, Status and when the Job finished.
    """