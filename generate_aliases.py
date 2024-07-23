#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import itertools
import os.path
import sys

try:
    xrange  # Python 2
except NameError:
    xrange = range  # Python 3


def main():
    # (alias, full, allow_when_oneof, incompatible_with)
    cmds = [("k", "kubectl", None, None)]

    globs = [("sys", "--namespace kube-system", None, None)]

    ops = [
        ("a", "apply --recursive -f", None, ["sys"]),
        ("ak", "apply -k", None, ["sys"]),
        ("k", "kustomize", None, ["sys"]),
        ("ex", "exec -i -t", None, None),
        ("ed", "edit", None, None),
        ("L", "logs -f", None, None),
        ("LP", "logs -f -p", None, None),
        # ('p', 'proxy', None, ['sys']),
        # ('pf', 'port-forward', None, ['sys']),
        ("g", "get", None, None),
        ("d", "describe", None, None),
        ("rm", "delete", None, None),
        (
            "run",
            "run --rm --restart Never --image-pull-policy IfNotPresent -i -t",
            None,
            None,
        ),
    ]

    res = [
        ("P", "pods", ["g", "d", "ed", "rm"], None),
        ("j", "jobs", ["g", "d", "ed", "rm"], None),
        ("cj", "cronjobs", ["g", "d", "ed", "rm"], None),
        ("D", "deployment", ["g", "d", "ed", "rm"], None),
        ("sts", "statefulset", ["g", "d", "ed", "rm"], None),
        ("svc", "service", ["g", "d", "ed", "rm"], None),
        ("ing", "ingress", ["g", "d", "ed", "rm"], None),
        ("cm", "configmap", ["g", "d", "ed", "rm"], None),
        ("sec", "secret", ["g", "d", "ed", "rm"], None),
        ("no", "nodes", ["g", "d"], ["sys"]),
        ("ns", "namespaces", ["g", "d", "ed", "rm"], ["sys"]),
        ("e", "events", ["g"], None),
    ]
    res_types = [r[0] for r in res]

    args = [
        # ("oyaml", "-o yaml", ["g"], ["owide", "ojson", "sl"]),
        # ("owide", "-o wide", ["g"], ["oyaml", "ojson"]),
        ("st", "--sort-by='.lastTimestamp'", ["g"], None),
        # ('ojson', '-o json', ['g'], ['owide', 'oyaml', 'sl']),
        # ("all", "--all-namespaces", ["g", "d"], ["rm", "f", "no", "sys"]),
        # ('sl', '--show-labels', ['g'], ['oyaml', 'ojson'], None),
        # ("all", "--all", ["rm"], None),  # caution: reusing the alias
        # ('w', '--watch', ['g'], ['oyaml', 'ojson', 'owide']),
    ]

    # these accept a value, so they need to be at the end and
    # mutually exclusive within each other.
    positional_args = [
        (
            "f",
            "--recursive -f",
            ["g", "d", "ed", "rm"],
            res_types + ["all", "l", "sys"],
        ),
        # ("l", "-l", ["g", "d", "ed", "rm"], ["f", "all"]),
        (
            "n",
            "--namespace",
            ["g", "d", "ed", "rm", "L", "ex", "pf"],
            ["ns", "no", "sys", "all"],
        ),
    ]

    # [(part, optional, take_exactly_one)]
    parts = [
        (cmds, False, True),
        (globs, True, False),
        (ops, True, True),
        (res, True, True),
        (args, True, False),
        (positional_args, True, True),
    ]

    shellFormatting = {
        "bash": "alias {}='{}'",
        "zsh": "alias {}='{}'",
        "fish": 'abbr --add {} "{}"',
    }
    shellFunction = {
        "zsh": """
function {0}() {{
  local fek() {{ echo "usage: {0} requires at least two arguments" >&2; {1} --help ; }}
  [[ -z $# ]] || [[ $# > 1 ]] || {{ fek && return 1; }}
  {1} "${{@:1:$# -1}}" -- "${{@: -1}}"
}}
"""
    }
    shellCompletion = {
        "zsh": """#compdef {0}

CURRENT=$(({2} + CURRENT))
words=("${{words[@]:1}}")
words=({1} "${{words[@]}}")
$_comps[kubectl]
"""
    }

    shell = sys.argv[1] if len(sys.argv) > 1 else "bash"
    if shell not in shellFormatting:
        raise ValueError(
            'Shell "{}" not supported. Options are {}'.format(
                shell, [key for key in shellFormatting]
            )
        )

    out = gen(parts)

    # prepare output
    if not sys.stdout.isatty():
        header_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "license_header"
        )
        with open(header_path, "r") as f:
            print(f.read())

    print(
        """
0="${ZERO:-${${0:#$ZSH_ARGZERO}:-${(%):-%N}}}"
0="${${(M)0:#/*}:-$PWD/$0}"
fpath+="${0:A:h}/completions"

"""
    )

    seen_aliases = set()

    for cmd in out:
        alias = (
            "".join([a[0] for a in cmd])
            .replace("D", "d")
            .replace("P", "p")
            .replace("L", "l")
            .replace("LP", "lp")
        )
        command = " ".join([a[1] for a in cmd])

        if alias in seen_aliases:
            print("Alias conflict detected: {}".format(alias), file=sys.stderr)

        seen_aliases.add(alias)

        if "ex" in alias:
            print(shellFunction[shell].format(alias, command))
            completions_dir = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "completions"
            )

            with open(os.path.join(completions_dir, "_{}".format(alias)), "w") as f:
                f.write(
                    shellCompletion[shell].format(
                        alias, command, len(command.split(" ")) - 1
                    )
                )
        else:
            print(shellFormatting[shell].format(alias, command))


def gen(parts):
    out = [()]
    for items, optional, take_exactly_one in parts:
        orig = list(out)
        combos = []

        if optional and take_exactly_one:
            combos = combos.append([])

        if take_exactly_one:
            combos = combinations(items, 1, include_0=optional)
        else:
            combos = combinations(items, len(items), include_0=optional)

        # permutate the combinations if optional (args are not positional)
        if optional:
            new_combos = []
            for c in combos:
                new_combos += list(itertools.permutations(c))
            combos = new_combos

        new_out = []
        for segment in combos:
            for stuff in orig:
                if is_valid(stuff + segment):
                    new_out.append(stuff + segment)
        out = new_out
    return out


def is_valid(cmd):
    return is_valid_requirements(cmd) and is_valid_incompatibilities(cmd)


def is_valid_requirements(cmd):
    parts = {c[0] for c in cmd}

    for i in range(0, len(cmd)):
        # check at least one of requirements are in the cmd
        requirements = cmd[i][2]
        if requirements and len(parts & set(requirements)) == 0:
            return False

    return True


def is_valid_incompatibilities(cmd):
    parts = {c[0] for c in cmd}

    for i in range(0, len(cmd)):
        # check none of the incompatibilities are in the cmd
        incompatibilities = cmd[i][3]
        if incompatibilities and len(parts & set(incompatibilities)) > 0:
            return False

    return True


def combinations(a, n, include_0=True):
    l = []
    for j in xrange(0, n + 1):
        if not include_0 and j == 0:
            continue

        cs = itertools.combinations(a, j)

        # check incompatibilities early
        cs = (c for c in cs if is_valid_incompatibilities(c))

        l += list(cs)

    return l


def diff(a, b):
    return list(set(a) - set(b))


if __name__ == "__main__":
    main()
