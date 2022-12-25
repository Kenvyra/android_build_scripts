#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "utils"))

import dataclasses
import json
import subprocess
import urllib.request
from enum import Enum
from functools import lru_cache
from xml.etree import ElementTree

from utils.colors import green, red, yellow


class RebaseResult(Enum):
    Failed = 1
    NothingToDo = 2
    Success = 3


@dataclasses.dataclass
class Remote:
    name: str
    fetch: str | None = None
    revision: str | None = None

    def url_for(self, name: str) -> str:
        if self.name == "aosp":
            name = name.replace("_", "/").replace("android", "platform")

        if self.fetch.endswith("/"):
            return f"{self.fetch}{name}.git"
        else:
            return f"{self.fetch}/{name}.git"


class RemoteForSingleProject(Remote):
    def url_for(self, name: str) -> str:
        return self.fetch


@dataclasses.dataclass
class Project:
    path: str
    name: str
    remote: Remote | None


@lru_cache(maxsize=None)
def parse(file: str) -> ElementTree:
    with open(file, "r") as file:
        return ElementTree.parse(file)


def rebase(*, project: Project, remote: Remote, kenvyra: Remote) -> RebaseResult:
    git_upstream = remote.url_for(project.name)

    # Add a git remote for upstream if it does not exist already
    result = subprocess.run(
        ["git", "remote", "add", remote.name, git_upstream],
        cwd=project.path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0 and b"already exists" not in result.stderr:
        print(red(f"Failed to add remote {remote} in {project.path}. Please verify!"))
        return RebaseResult.Failed

    # Fetch the upstream branch
    result = subprocess.run(
        ["git", "fetch", remote.name, remote.revision],
        cwd=project.path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        print(
            red(
                f"Failed to fetch remote {remote} in {project.path}. Git told me:\n{result.stderr}\nPlease verify!"
            )
        )
        return RebaseResult.Failed

    # Rebase it
    result = subprocess.run(
        ["git", "rebase", "FETCH_HEAD"],
        cwd=project.path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        print(
            red(
                f"Failed to rebase {project.path} onto {remote}. Git told me:\n{result.stderr}\nPlease resolve manually!"
            )
        )
        return RebaseResult.Failed
    elif b"up to date" in result.stdout:
        return RebaseResult.NothingToDo

    # Push it
    result = subprocess.run(
        ["git", "push", "-f", kenvyra.name, f"HEAD:{kenvyra.revision}"],
        cwd=project.path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        print(
            red(
                f"Failed to force-push {project.path} to {kenvyra}. Git told me:\n{result.stderr}\nPlease push manually!"
            )
        )
        return RebaseResult.Failed

    return RebaseResult.Success


def get_kenvyra_projects() -> list[Project]:
    tree = parse(".repo/manifests/kenvyra.xml")

    projects = []

    for elem in tree.findall("project[@remote='kenvyra']"):
        if elem.attrib["path"] == "manifest":
            continue

        path = elem.attrib["path"]
        name = elem.attrib["name"]

        upstream_path = os.path.join(path, ".upstream")
        if os.path.exists(upstream_path):
            with open(upstream_path, "r") as file:
                remote_json = json.load(file)
            remote = RemoteForSingleProject(**remote_json)
        else:
            remote = None

        projects.append(Project(path=path, name=name, remote=remote))

    return projects


def get_aosp() -> Remote:
    tree = parse(".repo/manifests/default.xml")
    remote = tree.find("remote[@name='aosp']")
    revision = tree.find("default[@remote='aosp']")
    return Remote(
        fetch=remote.attrib["fetch"],
        revision=revision.attrib["revision"],
        name=remote.attrib["name"],
    )


def get_arrow() -> Remote:
    elem = parse(".repo/manifests/default.xml").find("remote[@name='arrow']")
    return Remote(
        fetch=elem.attrib["fetch"],
        revision=elem.attrib["revision"],
        name=elem.attrib["name"],
    )


def get_kenvyra() -> Remote:
    elem = parse(".repo/manifests/default.xml").find("remote[@name='kenvyra']")
    return Remote(
        fetch=elem.attrib["fetch"],
        revision=elem.attrib["revision"],
        name=elem.attrib["name"],
    )


def main() -> None:
    print("Parsing ArrowOS revision from manifest")
    arrow = get_arrow()

    print("Parsing Kenvyra revision from manifest")
    kenvyra = get_kenvyra()

    print("Rebasing manifest on ArrowOS")

    match rebase(
        project=Project(path=".repo/manifests", name="android_manifest", remote=None),
        remote=arrow,
        kenvyra=kenvyra,
    ):
        case RebaseResult.Success:
            print(green("Manifest successfully rebased"))
        case RebaseResult.Failed:
            print(red("Rebasing manifest failed. Please resolve and run again!"))
            return
        case RebaseResult.NothingToDo:
            print(green("Manifest is up to date"))

    print("Parsing AOSP revision from manifest")
    aosp = get_aosp()

    possible_upstreams = [arrow, aosp]

    print("Parsing all Kenvyra repositories from manifest")
    projects = get_kenvyra_projects()

    for project in projects:
        if not project.remote:
            print(f"Guessing upstream for {project.name}")

            for remote in possible_upstreams:
                try:
                    with urllib.request.urlopen(remote.url_for(project.name)):
                        project.remote = remote
                        break
                except:
                    continue

        elif project.remote.name == "aosp":
            # AOSP revisions change so often, we will just set the remote to AOSP if forced
            # That way, a .upstream can only contain a name key
            project.remote = aosp

        if project.remote:
            print(f"Found upstream {project.remote.name} for {project.name}")
            match rebase(project=project, remote=project.remote, kenvyra=kenvyra):
                case RebaseResult.Success:
                    print(
                        green(
                            f"Successfully rebased {project.name} on {project.remote.name}"
                        )
                    )
                case RebaseResult.Failed:
                    print(
                        red(
                            f"Failed to rebase {project.name} on {project.remote.name}. Please fix manually and run again!"
                        )
                    )
                case RebaseResult.NothingToDo:
                    print(f"{project.name} is up to date!")
        else:
            print(
                yellow(
                    f"No upstream found for {project.name}! I will skip this project"
                )
            )


if __name__ == "__main__":
    main()
