#!/usr/bin/env python
import sys
import subprocess
from pathlib import Path

from graphviz import Digraph


def get_dependencies(file_path: Path):
    try:
        result = subprocess.check_output(
            ["readelf", "-a", file_path],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        dependencies = [
            line.split()[-1][1:-1] for line in result.splitlines() if "NEEDED" in line
        ]
        return dependencies
    except subprocess.CalledProcessError:
        return []


def generate_dependency_diagram(base: Path, file_paths: list[str]):
    all_dependencies = {}

    for file_path in file_paths:
        if file_path.endswith(".so"):
            real_file_path = base.joinpath(file_path)
            pretty_name = real_file_path.name
            dependencies = get_dependencies(real_file_path)
            all_dependencies[pretty_name] = dependencies

    for key, libs in all_dependencies.items():
        all_dependencies[key] = [lib for lib in libs if lib in all_dependencies]

    graph = Digraph("Dependency Diagram", format="svg")

    for lib, deps in all_dependencies.items():
        maybe_unused = sum(1 if lib in l else 0 for l in all_dependencies.values()) == 0
        kwargs = {"style": "filled", "fillcolor": "yellow"} if maybe_unused else {}
        graph.node(lib, **kwargs)
        for dep in deps:
            graph.edge(lib, dep)

    graph.render("dependency_diagram")


def get_file_paths(path: Path) -> list[str]:
    with open(path, "r") as file:
        return [line for line in file.read().splitlines() if not line.startswith("#")]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: proprietary-blob-diagram.py [path-to-proprietary-files.txt]")

    path = Path(sys.argv[1]).resolve()

    # Paths are assumed to be something akin to device/vendor/codename/proprietary-files.txt
    device = path.parent
    vendor = device.parent
    rom = vendor.parent.parent

    device_name = device.name
    vendor_name = vendor.name

    vendor_file_tree_base = rom.joinpath(
        "vendor", vendor_name, device_name, "proprietary"
    )

    file_paths = get_file_paths(path)
    diagram = generate_dependency_diagram(vendor_file_tree_base, file_paths)
