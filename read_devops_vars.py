#!/usr/bin/env python3
"""
Read variables from Azure DevOps Variable Groups (Pipeline Library).

Authentication: Personal Access Token (PAT) with at least
  - Variable Groups: Read scope
  - Project: Read scope

Usage:
  python read_devops_vars.py                                    # list all variable groups
  python read_devops_vars.py --group "MyGroup"                  # show vars in a specific group
  python read_devops_vars.py --group "MyGroup" --key MY_VAR     # get a single value
  python read_devops_vars.py --group "MyGroup" --output out.tsv             # save as TSV
  python read_devops_vars.py --group "MyGroup" --output out.env --env-format # save as KEY=VALUE
  python read_devops_vars.py --compare "backend-uat" "backend-prod"          # compare two groups
"""

import argparse
import os
import sys

from azure.devops.connection import Connection
from azure.devops.v7_1.task_agent.models import TaskAgentPoolReference
from dotenv import load_dotenv
from msrest.authentication import BasicAuthentication

load_dotenv()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"ERROR: environment variable '{name}' is not set.", file=sys.stderr)
        sys.exit(1)
    return value


def build_connection() -> Connection:
    org_url = get_required_env("AZDO_ORG_URL")       # e.g. https://dev.azure.com/myorg
    pat     = get_required_env("AZDO_PAT")            # Personal Access Token

    credentials = BasicAuthentication("", pat)
    return Connection(base_url=org_url, creds=credentials)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def list_variable_groups(project: str) -> list:
    """Return all variable groups in a project."""
    connection = build_connection()
    client = connection.clients.get_task_agent_client()
    groups = client.get_variable_groups(project=project)
    return groups or []


def get_variable_group(project: str, group_name: str):
    """Return a single variable group by name, or None."""
    groups = list_variable_groups(project)
    for g in groups:
        if g.name == group_name:
            return g
    return None


def print_groups(groups: list) -> None:
    if not groups:
        print("No variable groups found.")
        return
    print(f"{'ID':<6} {'Name':<40} {'Type':<20} Variables")
    print("-" * 80)
    for g in groups:
        var_count = len(g.variables) if g.variables else 0
        print(f"{g.id:<6} {g.name:<40} {g.type:<20} {var_count}")


def print_variables(group, show_secrets: bool = False) -> None:
    if not group.variables:
        print("No variables found in this group.")
        return

    print(f"\nVariable Group: {group.name}  (id={group.id})\n")
    print(f"{'Variable':<40} {'Value'}")
    print("-" * 70)

    for name, var in sorted(group.variables.items()):
        is_secret = getattr(var, "is_secret", False)
        if is_secret and not show_secrets:
            value = "****** (secret)"
        else:
            value = var.value if var.value is not None else ""
        print(f"{name:<40} {value}")


def get_single_value(group, key: str) -> str | None:
    if not group.variables:
        return None
    var = group.variables.get(key)
    if var is None:
        return None
    is_secret = getattr(var, "is_secret", False)
    if is_secret:
        print(f"WARNING: '{key}' is marked as secret; its value may be masked.", file=sys.stderr)
    return var.value


def save_variables(group, output_path: str, show_secrets: bool = False) -> None:
    """Write group variables to a tab-separated file (name<TAB>value)."""
    import csv
    variables = group.variables or {}
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["variable", "value", "is_secret"])
        for name, var in sorted(variables.items()):
            is_secret = getattr(var, "is_secret", False)
            if is_secret and not show_secrets:
                value = ""
            else:
                value = var.value if var.value is not None else ""
            writer.writerow([name, value, str(is_secret).lower()])
    print(f"Saved {len(variables)} variable(s) to '{output_path}'.")


def save_env(group, output_path: str, show_secrets: bool = False) -> None:
    """Write group variables to a KEY=VALUE .env-style file, sorted for diffing."""
    variables = group.variables or {}
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Variable group: {group.name}\n")
        for name, var in sorted(variables.items()):
            is_secret = getattr(var, "is_secret", False)
            if is_secret and not show_secrets:
                value = ""  # masked
            else:
                value = var.value if var.value is not None else ""
            # Quote values that contain spaces or special characters
            if any(c in value for c in (" ", "\t", "#", "'", '"')):
                value = f'"{value}"'
            f.write(f"{name}={value}\n")
    print(f"Saved {len(variables)} variable(s) to '{output_path}'.")


def compare_groups(group_a, group_b) -> bool:
    """Print a comparison of two variable groups. Returns True if identical."""
    vars_a = set(group_a.variables.keys()) if group_a.variables else set()
    vars_b = set(group_b.variables.keys()) if group_b.variables else set()

    only_in_a = sorted(vars_a - vars_b)
    only_in_b = sorted(vars_b - vars_a)
    in_both   = sorted(vars_a & vars_b)

    print(f"\nComparing:  [{group_a.name}]  vs  [{group_b.name}]\n")

    if only_in_a:
        print(f"  Only in '{group_a.name}' ({len(only_in_a)} key(s)):")
        for k in only_in_a:
            print(f"    - {k}")
    if only_in_b:
        print(f"  Only in '{group_b.name}' ({len(only_in_b)} key(s)):")
        for k in only_in_b:
            print(f"    + {k}")

    value_diffs = []
    for k in in_both:
        val_a = group_a.variables[k].value or ""
        val_b = group_b.variables[k].value or ""
        sec_a = getattr(group_a.variables[k], "is_secret", False)
        sec_b = getattr(group_b.variables[k], "is_secret", False)
        if sec_a or sec_b:
            continue  # skip secret comparisons — values are masked
        if val_a != val_b:
            value_diffs.append(k)

    if value_diffs:
        print(f"  Keys present in both but with different values ({len(value_diffs)}):")
        for k in value_diffs:
            print(f"    ~ {k}")

    identical = not only_in_a and not only_in_b and not value_diffs
    if identical:
        print("  Groups are identical (non-secret keys and values match).")
    else:
        total = len(only_in_a) + len(only_in_b) + len(value_diffs)
        print(f"\n  {total} difference(s) found.")

    return identical


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read variables from Azure DevOps Variable Groups."
    )
    parser.add_argument(
        "--project",
        default=os.getenv("AZDO_PROJECT"),
        help="Azure DevOps project name (or set AZDO_PROJECT env var).",
    )
    parser.add_argument(
        "--group",
        metavar="GROUP_NAME",
        help="Variable group name to inspect. Omit to list all groups.",
    )
    parser.add_argument(
        "--key",
        metavar="VAR_NAME",
        help="Print only this variable's value (useful for scripting).",
    )
    parser.add_argument(
        "--show-secrets",
        action="store_true",
        help="Attempt to display secret variable values (requires elevated PAT scope).",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save variables to a file (requires --group). Format depends on --env-format.",
    )
    parser.add_argument(
        "--env-format",
        action="store_true",
        help="Write output as KEY=VALUE lines (ideal for VS Code diff). Default is TSV.",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("GROUP_A", "GROUP_B"),
        help="Compare keys and values between two variable groups.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.project:
        print("ERROR: project not specified. Use --project or set AZDO_PROJECT.", file=sys.stderr)
        sys.exit(1)

    # --- Compare two groups ---
    if args.compare:
        name_a, name_b = args.compare
        group_a = get_variable_group(args.project, name_a)
        if group_a is None:
            print(f"ERROR: variable group '{name_a}' not found.", file=sys.stderr)
            sys.exit(1)
        group_b = get_variable_group(args.project, name_b)
        if group_b is None:
            print(f"ERROR: variable group '{name_b}' not found.", file=sys.stderr)
            sys.exit(1)
        identical = compare_groups(group_a, group_b)
        sys.exit(0 if identical else 1)

    # --- List all groups ---
    if not args.group:
        groups = list_variable_groups(args.project)
        print_groups(groups)
        return

    # --- Inspect a specific group ---
    group = get_variable_group(args.project, args.group)
    if group is None:
        print(f"ERROR: variable group '{args.group}' not found in project '{args.project}'.", file=sys.stderr)
        sys.exit(1)

    # --- Save to file ---
    if args.output:
        if args.env_format:
            save_env(group, args.output, show_secrets=args.show_secrets)
        else:
            save_variables(group, args.output, show_secrets=args.show_secrets)
        return

    # --- Single key ---
    if args.key:
        value = get_single_value(group, args.key)
        if value is None:
            print(f"ERROR: variable '{args.key}' not found in group '{args.group}'.", file=sys.stderr)
            sys.exit(1)
        print(value)
        return

    print_variables(group, show_secrets=args.show_secrets)


if __name__ == "__main__":
    main()
