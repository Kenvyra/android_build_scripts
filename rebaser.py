#!/usr/bin/env python3
import os
import sys
from typing import Iterator

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "utils"))

import dataclasses
import json
import subprocess
import urllib.request
from enum import Enum
from functools import lru_cache
from glob import glob
from itertools import chain
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
            # Hack for special case
            name = name.replace("platform/testing", "platform_testing")

        if self.fetch.endswith("/"):
            return f"{self.fetch}{name}.git"
        else:
            return f"{self.fetch}/{name}.git"

    def url_for_revision(self, name: str) -> str:
        if self.name == "aosp":
            name = name.replace("_", "/").replace("android", "platform")
            # Hack for special case
            name = name.replace("platform/testing", "platform_testing")

        if self.fetch.endswith("/"):
            base = f"{self.fetch}{name}"
        else:
            base = f"{self.fetch}/{name}"

        if self.name == "aosp":
            return f"{base}/+/{self.revision}"
        else:
            return f"{base}/tree/{self.revision}"


class RemoteForSingleProject(Remote):
    def url_for(self, name: str) -> str:
        return self.fetch


@dataclasses.dataclass
class Project:
    path: str
    name: str
    remote: Remote | None
    kenvyra: Remote


@lru_cache(maxsize=None)
def parse(file: str) -> ElementTree:
    with open(file, "r") as file:
        return ElementTree.parse(file)


def rebase(project: Project) -> RebaseResult:
    git_upstream = project.remote.url_for(project.name)

    # Add a git remote for upstream if it does not exist already
    result = subprocess.run(
        ["git", "remote", "add", project.remote.name, git_upstream],
        cwd=project.path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0 and b"already exists" not in result.stderr:
        print(
            red(
                f"Failed to add remote {project.remote} in {project.path}. Please verify!"
            )
        )
        return RebaseResult.Failed

    # Fetch the upstream branch
    result = subprocess.run(
        ["git", "fetch", project.remote.name, project.remote.revision],
        cwd=project.path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        print(
            red(
                f"Failed to fetch remote {project.remote} in {project.path}. Git told me:\n{result.stderr}\nPlease verify!"
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
                f"Failed to rebase {project.path} onto {project.remote}. Git told me:\n{result.stderr}\nPlease resolve manually!"
            )
        )
        return RebaseResult.Failed
    elif b"up to date" in result.stdout:
        return RebaseResult.NothingToDo

    # Push it
    result = subprocess.run(
        ["git", "push", "-f", project.kenvyra.name, f"HEAD:{project.kenvyra.revision}"],
        cwd=project.path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        print(
            red(
                f"Failed to force-push {project.path} to {project.kenvyra}. Git told me:\n{result.stderr}\nPlease push manually!"
            )
        )
        return RebaseResult.Failed

    return RebaseResult.Success


def get_kenvyra_projects() -> Iterator[Project]:
    for file in glob(".repo/manifests/**/*.xml", recursive=True):
        # Device trees should be updated manually
        if file.endswith("devices.xml"):
            continue

        tree = parse(file)

        for elem in chain(
            tree.findall("project[@remote='kenvyra']"),
            tree.findall("project[@remote='kenvyra-gitlab']"),
        ):
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

            if elem.attrib["remote"] == "kenvyra":
                kenvyra = get_kenvyra()
            else:
                kenvyra = get_kenvyra_gitlab()

            yield Project(path=path, name=name, remote=remote, kenvyra=kenvyra)


def get_aosp() -> Remote:
    tree = parse(".repo/manifests/default.xml")
    remote = tree.find("remote[@name='aosp']")
    return Remote(
        fetch=remote.attrib["fetch"],
        revision=remote.attrib["revision"],
        name=remote.attrib["name"],
    )


def get_lineage() -> Remote:
    # The linage remote is a tricky one
    # They use a remote called "github" and reference it
    # in the default revision
    elem = parse(".repo/manifests/default.xml").find("default")
    return Remote(
        fetch="https://github.com/LineageOS/",
        revision=elem.attrib["revision"],
        name="lineage",
    )


def get_kenvyra() -> Remote:
    elem = parse(".repo/manifests/default.xml").find("remote[@name='kenvyra']")
    return Remote(
        fetch=elem.attrib["fetch"],
        revision=elem.attrib["revision"],
        name=elem.attrib["name"],
    )


def get_kenvyra_gitlab() -> Remote:
    elem = parse(".repo/manifests/default.xml").find("remote[@name='kenvyra-gitlab']")
    return Remote(
        fetch=elem.attrib["fetch"],
        revision=elem.attrib["revision"],
        name=elem.attrib["name"],
    )


def main() -> None:
    print("Parsing LineageOS revision from manifest")
    lineage = get_lineage()

    print("Parsing Kenvyra revision from manifest")
    kenvyra = get_kenvyra()

    print("Rebasing manifest on LineageOS")

    match rebase(
        Project(
            path=".repo/manifests",
            name="android_manifest",
            remote=RemoteForSingleProject(
                name="lineage",
                fetch="https://github.com/LineageOS/android",
                revision="refs/heads/lineage-20.0",
            ),
            kenvyra=kenvyra,
        )
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

    possible_upstreams = [lineage, aosp]

    print("Parsing all Kenvyra repositories from manifest")
    projects = get_kenvyra_projects()

    for project in projects:
        if not project.remote:
            print(f"Guessing upstream for {project.name}")

            for remote in possible_upstreams:
                try:
                    with urllib.request.urlopen(remote.url_for_revision(project.name)):
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
            match rebase(project):
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
