#!/usr/bin/env python3
"""Validate a repo-quake experiment card using only the Python standard library."""
import json
import math
import re
import sys

REQUIRED = (
    "schema_version", "id", "claim", "target", "task", "hosts", "arms", "controls",
    "witness", "grading", "sampling", "invalid_rules", "budget", "isolation", "ethics",
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def text(value):
    return isinstance(value, str) and bool(value.strip())


def require_fields(obj, fields, where, errors):
    if not isinstance(obj, dict):
        errors.append(f"{where} must be an object")
        return False
    for field in fields:
        if field not in obj:
            errors.append(f"{where}.{field} is required")
    return True


def validate(card):
    errors = []
    if not require_fields(card, REQUIRED, "card", errors):
        return errors, 0
    if card.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if not text(card.get("id")):
        errors.append("id must be non-empty text")
    if not text(card.get("claim")):
        errors.append("claim must be non-empty text")

    if require_fields(card.get("target"), {"name", "version"}, "target", errors):
        for field in ("name", "version"):
            if not text(card["target"].get(field)):
                errors.append(f"target.{field} must be non-empty text")
        if "source_sha256" in card["target"] and not HEX64.match(str(card["target"]["source_sha256"])):
            errors.append("target.source_sha256 must be 64 lowercase hex characters")
    if require_fields(card.get("task"), {"prompt_sha256", "path_reachability"}, "task", errors):
        if not HEX64.match(str(card["task"].get("prompt_sha256"))):
            errors.append("task.prompt_sha256 must be 64 lowercase hex characters")
        if not text(card["task"].get("path_reachability")):
            errors.append("task.path_reachability must explain how the task reaches the fault")

    hosts = card.get("hosts")
    host_ids = []
    if not isinstance(hosts, list) or not hosts:
        errors.append("hosts must be a non-empty array")
        hosts = []
    for index, host in enumerate(hosts):
        where = f"hosts[{index}]"
        if require_fields(host, {"id", "name", "version", "model", "effort"}, where, errors):
            if text(host.get("id")):
                host_ids.append(host["id"])
            for field in ("id", "name", "version", "model", "effort"):
                if not text(host.get(field)):
                    errors.append(f"{where}.{field} must be non-empty text")
    if len(set(host_ids)) != len(host_ids):
        errors.append("host ids must be unique")

    arms = card.get("arms")
    arm_ids = []
    roles = []
    arm_roles = {}
    if not isinstance(arms, list) or not arms:
        errors.append("arms must be a non-empty array")
        arms = []
    for index, arm in enumerate(arms):
        where = f"arms[{index}]"
        if require_fields(arm, {"id", "fault", "role"}, where, errors):
            if text(arm.get("id")):
                arm_ids.append(arm["id"])
                arm_roles[arm["id"]] = arm.get("role")
            roles.append(arm.get("role"))
            if not text(arm.get("id")) or not text(arm.get("fault")):
                errors.append(f"{where}.id and fault must be non-empty text")
            if arm.get("role") not in {"treatment", "negative_control", "positive_control"}:
                errors.append(f"{where}.role has an unknown value")
    if len(set(arm_ids)) != len(arm_ids):
        errors.append("arm ids must be unique")
    if "treatment" not in roles:
        errors.append("at least one treatment arm is required")
    if "negative_control" not in roles:
        errors.append("at least one negative-control arm is required")

    if require_fields(card.get("controls"), {"negative"}, "controls", errors):
        for field, role in (("negative", "negative_control"), ("positive", "positive_control")):
            ref = card["controls"].get(field)
            if ref is None:
                continue
            if ref not in arm_ids:
                errors.append(f"controls.{field} references unknown arm '{ref}'")
            elif arm_roles.get(ref) != role:
                errors.append(f"controls.{field} references an arm whose role is not {role}")

    if require_fields(card.get("witness"), {"delivery", "checker", "blind_spots"}, "witness", errors):
        for field in ("delivery", "checker"):
            if not text(card["witness"].get(field)):
                errors.append(f"witness.{field} must be non-empty text")
        blind = card["witness"].get("blind_spots")
        if not isinstance(blind, list) or not blind or not all(text(item) for item in blind):
            errors.append("witness.blind_spots must be a non-empty array (use 'none known after calibration' if appropriate)")

    if require_fields(card.get("grading"), {"rubric", "primary_metric"}, "grading", errors):
        for field in ("rubric", "primary_metric"):
            if not text(card["grading"].get(field)):
                errors.append(f"grading.{field} must be non-empty text")

    runs_per_cell = None
    if require_fields(card.get("sampling"), {"runs_per_cell"}, "sampling", errors):
        runs_per_cell = card["sampling"].get("runs_per_cell")
        if not isinstance(runs_per_cell, int) or isinstance(runs_per_cell, bool) or runs_per_cell < 1:
            errors.append("sampling.runs_per_cell must be a positive integer")
            runs_per_cell = None
    overrides = card["sampling"].get("runs_overrides", {})
    if not isinstance(overrides, dict):
        errors.append("sampling.runs_overrides must be an object when present")
        overrides = {}
    run_counts = []
    for arm_id in arm_ids:
        count = overrides.get(arm_id, runs_per_cell or 0)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            errors.append(f"sampling.runs_overrides.{arm_id} must be a positive integer")
            count = 0
        run_counts.append(count)
    for arm_id in overrides:
        if arm_id not in arm_ids:
            errors.append(f"sampling.runs_overrides references unknown arm '{arm_id}'")
    planned = len(hosts) * sum(run_counts)

    rules = card.get("invalid_rules")
    if not isinstance(rules, list) or not rules or not all(text(rule) for rule in rules):
        errors.append("invalid_rules must be a non-empty array")
    if require_fields(card.get("budget"), {"max_runs"}, "budget", errors):
        max_runs = card["budget"].get("max_runs")
        if not isinstance(max_runs, int) or isinstance(max_runs, bool) or max_runs < 1:
            errors.append("budget.max_runs must be a positive integer")
        elif runs_per_cell is not None and max_runs < planned:
            errors.append(f"budget.max_runs={max_runs} cannot fund planned_runs={planned}")
        if "max_usd" in card["budget"] and (
            not isinstance(card["budget"]["max_usd"], (int, float))
            or isinstance(card["budget"]["max_usd"], bool)
            or not math.isfinite(card["budget"]["max_usd"])
            or card["budget"]["max_usd"] <= 0
        ):
            errors.append("budget.max_usd must be a positive number when present")

    validate_design_and_cost(card, planned, errors)

    if require_fields(card.get("isolation"), {"mode", "pristine_original_unreachable"}, "isolation", errors):
        if not text(card["isolation"].get("mode")):
            errors.append("isolation.mode must be non-empty text")
        pristine = card["isolation"].get("pristine_original_unreachable")
        if not isinstance(pristine, bool):
            errors.append("isolation.pristine_original_unreachable must be boolean")
        elif not pristine and not text(card["isolation"].get("contamination")):
            errors.append("isolation.contamination is required when the pristine original remains reachable")
    if require_fields(card.get("ethics"), {"production_contact", "human_subjects", "blast_radius"}, "ethics", errors):
        ethics = card["ethics"]
        for field in ("production_contact", "human_subjects"):
            if not isinstance(ethics.get(field), bool):
                errors.append(f"ethics.{field} must be boolean")
        if not text(ethics.get("blast_radius")):
            errors.append("ethics.blast_radius must describe the containment boundary")
        if ethics.get("human_subjects") and not text(ethics.get("consent")):
            errors.append("ethics.consent is required when human_subjects is true")
    return errors, planned



def nonnegative_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def validate_design_and_cost(card, planned, errors):
    """Optional v1 extensions; legacy fault-injection cards remain unchanged."""
    design = card.get("design")
    if design is not None:
        if not isinstance(design, dict):
            errors.append("design must be an object when present")
            design = {}
        kind = design.get("kind")
        if kind not in {"paired", "memory", "metamorphic"}:
            errors.append("design.kind must be paired, memory or metamorphic")
        elif kind == "paired":
            paired = design.get("paired")
            if require_fields(paired, {"pairs_planned", "order_schedule", "statistic", "holdout", "proxy_chain"}, "design.paired", errors):
                pairs = paired.get("pairs_planned")
                if not isinstance(pairs, int) or isinstance(pairs, bool) or pairs < 1:
                    errors.append("design.paired.pairs_planned must be a positive integer")
                    pairs = 0
                schedule = paired.get("order_schedule")
                if not isinstance(schedule, list) or len(schedule) != pairs or any(x not in {"AB", "BA"} for x in schedule):
                    errors.append("design.paired.order_schedule must contain one AB/BA entry per pair")
                elif schedule.count("AB") != schedule.count("BA"):
                    errors.append("design.paired.order_schedule must balance AB and BA")
                if paired.get("statistic") != "exact_mcnemar":
                    errors.append("design.paired.statistic must be exact_mcnemar")
                if not text(paired.get("holdout")):
                    errors.append("design.paired.holdout must be non-empty text")
                chain = paired.get("proxy_chain")
                if not isinstance(chain, list) or len(chain) < 2 or not all(text(x) for x in chain):
                    errors.append("design.paired.proxy_chain must name at least two consumption steps")
                if len(card.get("arms", [])) != 2:
                    errors.append("paired design requires exactly two arms")
                if card.get("sampling", {}).get("runs_overrides"):
                    errors.append("paired design does not allow sampling.runs_overrides")
                if pairs and planned != 2 * pairs * len(card.get("hosts", [])):
                    errors.append("design.paired.pairs_planned must equal runs per arm per host")
        elif kind == "memory":
            memory = design.get("memory")
            if require_fields(memory, {"layers", "corpora", "shadow", "write_before_enable", "recall_rerank_split"}, "design.memory", errors):
                layers = memory.get("layers")
                if require_fields(layers, {"write", "retrieval", "acceptance"}, "design.memory.layers", errors):
                    for field in ("write", "retrieval", "acceptance"):
                        if not text(layers.get(field)):
                            errors.append(f"design.memory.layers.{field} must name a witness")
                corpora = memory.get("corpora")
                if not isinstance(corpora, list) or not corpora:
                    errors.append("design.memory.corpora must be a non-empty array")
                    corpora = []
                ids = []
                for index, corpus in enumerate(corpora):
                    if require_fields(corpus, {"id", "gold_shape"}, f"design.memory.corpora[{index}]", errors):
                        if text(corpus.get("id")):
                            ids.append(corpus["id"])
                        if not text(corpus.get("id")) or not text(corpus.get("gold_shape")):
                            errors.append(f"design.memory.corpora[{index}] id/gold_shape must be non-empty text")
                if len(set(ids)) != len(ids):
                    errors.append("design.memory.corpora ids must be unique")
                if not text(memory.get("shadow")):
                    errors.append("design.memory.shadow must describe byte-level identity verification")
                if memory.get("write_before_enable") is not True:
                    errors.append("design.memory.write_before_enable must be true")
                if memory.get("recall_rerank_split") is not True:
                    errors.append("design.memory.recall_rerank_split must be true")
        elif kind == "metamorphic":
            metamorphic = design.get("metamorphic")
            if require_fields(metamorphic, {"source_case", "follow_ups", "outcome_relation", "na_policy"}, "design.metamorphic", errors):
                if not text(metamorphic.get("source_case")):
                    errors.append("design.metamorphic.source_case must be non-empty text")
                follow_ups = metamorphic.get("follow_ups")
                if not isinstance(follow_ups, list) or not follow_ups:
                    errors.append("design.metamorphic.follow_ups must be a non-empty array")
                    follow_ups = []
                ids = []
                for index, follow in enumerate(follow_ups):
                    if require_fields(follow, {"id", "transform", "relation"}, f"design.metamorphic.follow_ups[{index}]", errors):
                        if text(follow.get("id")):
                            ids.append(follow["id"])
                        for field in ("id", "transform", "relation"):
                            if not text(follow.get(field)):
                                errors.append(f"design.metamorphic.follow_ups[{index}].{field} must be non-empty text")
                if len(set(ids)) != len(ids):
                    errors.append("design.metamorphic.follow_ups ids must be unique")
                if not text(metamorphic.get("outcome_relation")):
                    errors.append("design.metamorphic.outcome_relation must be non-empty text")
                if not text(metamorphic.get("na_policy")):
                    errors.append("design.metamorphic.na_policy must be non-empty text")
    cost = card.get("cost_policy")
    if cost is not None:
        if require_fields(cost, {"max_per_run", "max_per_success", "retry_policy", "cache_policy", "billing_alignment", "overrun", "decision_rule"}, "cost_policy", errors):
            for field in ("max_per_run", "max_per_success"):
                if not nonnegative_number(cost.get(field)):
                    errors.append(f"cost_policy.{field} must be a finite non-negative number")
            for field in ("retry_policy", "cache_policy", "billing_alignment", "decision_rule"):
                if not text(cost.get(field)):
                    errors.append(f"cost_policy.{field} must be non-empty text")
            if cost.get("overrun") not in {"invalid", "counted", "stop_and_report"}:
                errors.append("cost_policy.overrun must be invalid, counted or stop_and_report")

def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) != 2:
        print("usage: validate_card.py <experiment-card.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as handle:
            card = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"validate_card: cannot read card: {exc}", file=sys.stderr)
        return 2
    errors, planned = validate(card)
    if errors:
        print("INVALID experiment card", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"VALID {card['id']}: planned_runs={planned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
