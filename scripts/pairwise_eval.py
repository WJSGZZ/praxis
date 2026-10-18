"""Prepare anonymous comparisons and analyse sealed, manually returned judgments.

No command calls a model, reads Praxis judging references, or infers a preference
from mechanical findings. See evals/PAIRWISE.md for the input contracts and limits.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re
import secrets
import shutil
import sys
import unicodedata

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import spearmanr


SEED = 20261016
BOOTSTRAPS = 1000
QUESTION = ("Which manuscript is closer to the O level for this problem and contest year? "
            "Choose left, right, or explicitly abstain; state confidence from 0.5 to 1. "
            "Give exactly three reasons, each locating evidence in both manuscripts. "
            "Record mathematical or mechanical findings separately; a finding does not "
            "automatically determine preference. Do not load Praxis references or seek "
            "paper identities, award labels, other papers, or an answer key.")


def read_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def write_json(path, value):
    Path(path).write_text(json_text(value), encoding="utf-8")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def text_sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _within(path, directory):
    return Path(path).resolve().is_relative_to(Path(directory).resolve())


def _file(root, item, label):
    if not isinstance(item, dict) or not item.get("path") or not item.get("sha256"):
        raise ValueError(f"{label}: explicit path and sha256 required; pending preparation")
    path = Path(item["path"])
    path = path if path.is_absolute() else Path(root) / path
    if not path.is_file() or sha256(path) != item["sha256"]:
        raise ValueError(f"{label}: missing file or SHA256 mismatch")
    return path


def _contexts(path, workspace, problems):
    data = read_json(path)
    if data.get("schema") != 1 or not isinstance(data.get("problems"), list):
        raise ValueError("contexts requires schema:1 and problems array")
    items = {}
    for entry in data["problems"]:
        problem = entry.get("problem")
        if problem in items:
            raise ValueError("Duplicate problem context")
        items[problem] = entry
    result, private, pending_rules = {}, {}, []
    for problem in sorted(problems):
        if problem not in items:
            raise ValueError(f"{problem}: missing original statement/rules/anchor; pending preparation")
        entry = items[problem]
        year = int(problem.split("-")[1])
        if entry.get("year") != year:
            raise ValueError(f"{problem}: context year mismatch")
        texts, bindings, resource_metadata, attachment = {}, {}, {}, None
        for kind in ("statement", "rules", "anchor"):
            item = entry.get(kind)
            if not isinstance(item, dict) or item.get("year") != year:
                raise ValueError(f"{problem}/{kind}: original-year binding required")
            if kind == "rules":
                if item.get("contest") != "MCM":
                    raise ValueError(f"{problem}/rules: contest mismatch")
            elif item.get("problem") != problem:
                raise ValueError(f"{problem}/{kind}: problem mismatch")
            resource = _file(workspace, item, f"{problem}/{kind}")
            text = resource.read_text(encoding="utf-8").strip()
            if not text:
                raise ValueError(f"{problem}/{kind}: empty resource")
            if kind == "anchor" and item.get("anchor_level") not in {"generic", "official", "member"}:
                raise ValueError(f"{problem}/anchor: explicit anchor_level required")
            if item.get("completeness") not in {"complete", "partial"}:
                raise ValueError(f"{problem}/{kind}: explicit completeness required")
            if not isinstance(item.get("limitations"), list) or any(not isinstance(v, str) or not v.strip() for v in item["limitations"]):
                raise ValueError(f"{problem}/{kind}: limitations must be an explicit text array")
            if kind in {"statement", "rules"} and item["completeness"] != "complete":
                pending_rules.append(f"{problem}/{kind}")
            texts[kind] = text
            bindings[kind] = dict(item)
            resource_metadata[kind] = {k: item[k] for k in ("completeness", "limitations", "source_url", "source_sha256") if k in item}
            if kind == "statement" and item.get("source_file"):
                source_path = Path(item["source_file"])
                source_scope = item.get("source_scope")
                single_problem = (source_scope == "single_problem" and item.get("source_problem", problem) == problem
                                  or source_scope is None and item.get("source_problem") == problem)
                if source_path.suffix.lower() == ".pdf" and single_problem:
                    original = _file(workspace, {"path": item["source_file"], "sha256": item.get("source_sha256")},
                                     f"{problem}/original statement PDF")
                    attachment = {"path": str(original.resolve()), "sha256": item["source_sha256"], "problem": problem}
                    resource_metadata[kind]["original_pdf"] = {"available": True, "path": "problem-original.pdf",
                        "sha256": item["source_sha256"], "scope": "single_problem",
                        "purpose": "Original statement maps/figures; does not change declared rules/data completeness"}
                else:
                    resource_metadata[kind]["original_pdf"] = {"available": False,
                        "reason": "Source is not a PDF" if source_path.suffix.lower() != ".pdf" else "Source is multi-problem or its single-problem scope is unverified; not copied"}
        result[problem] = {"problem": problem, "year": year, **texts,
                           "resource_metadata": resource_metadata}
        private[problem] = {"anchor_level": entry["anchor"]["anchor_level"],
                            "bindings": bindings}
        if attachment:
            private[problem]["statement_attachment"] = attachment
    incomplete = {name.rsplit("/", 1)[0] for name in pending_rules}
    readiness = {"ready_for_formal_eval": not pending_rules, "selected_problems": len(problems),
                 "complete_context_problems": len(problems) - len(incomplete),
                 "blockers": [{"problem": problem, "incomplete_resources": [name.rsplit("/", 1)[1] for name in pending_rules if name.startswith(problem + "/")],
                               "reason": "Original-year context is partial; preparation only, user must review limitations before approving any formal evaluation"}
                              for problem in sorted(incomplete)]}
    return result, private, readiness


def _team_pattern(team):
    digits = re.sub(r"\D", "", unicodedata.normalize("NFKC", str(team)))
    if not digits:
        raise ValueError("paper team must contain digits")
    return re.compile(r"(?<!\d)" + r"[\s.·_\-‐‑–—\u200b\u200c\u200d\ufeff]*".join(digits) + r"(?!\d)")


def anonymize_pages(pages, team, schools=()):
    """Conservative text redaction; report losses rather than claiming perfect anonymity."""
    normalized = [[re.sub(r"[ \t]+", " ", unicodedata.normalize("NFKC", line)).strip()
                   for line in page["text"].splitlines()] for page in pages]
    edges = Counter()
    for lines in normalized:
        edges.update(set(line for line in lines[:3] + lines[-3:] if line))
    repeated = {line for line, count in edges.items() if count >= 2}
    number = _team_pattern(team)
    schools = [unicodedata.normalize("NFKC", str(s)).strip() for s in schools if str(s).strip()]
    counts, output = Counter(), []
    acknowledging = False
    for page_no, lines in enumerate(normalized, 1):
        output.append(f"[page {page_no:03d}]")
        for line in lines:
            line, found = re.subn(r"校苑数模|微信公众号|获取更多资讯", "", line)
            counts["publisher_markers"] += found
            line = line.strip()
            if not line:
                continue
            if re.match(r"^(?:\d+(?:\.\d+)*[.\s]+)?(?:acknowledg(?:e)?ments?|致谢)\b", line, re.I):
                acknowledging = True
            elif acknowledging and re.match(r"^(?:\d+(?:\.\d+)*[.\s]+\S|references\b|bibliography\b|appendi[xc]\b|参考文献)", line, re.I):
                acknowledging = False
            if acknowledging:
                counts["acknowledgment_lines"] += 1
                continue
            if line in repeated or re.match(r"^(?:page\s*\d+(?:\s*of\s*\d+)?\b|team\s*(?:control\s*)?(?:number\b|#|no\b)|authors?\s*[:：]|submitted by\b|队号|参赛队号|作者\s*[:：])", line, re.I):
                counts["header_lines"] += 1
                continue
            if any(s.casefold() in line.casefold() for s in schools) or re.search(r"\b(?:university|college|institute of technology|school of)\b|大学|学院", line, re.I):
                counts["institution_lines"] += 1
                continue
            if re.search(r"\b(?:outstanding(?:\s+winner)?|meritorious|honou?rable mention|successful participant)\b|(?:特等|一等|二等|三等|优秀)奖", line, re.I) or re.match(r"^(?:(?:MCM|ICM)\s*)?(?:[OFMHS][\s\-]*awards?\b|award(?:\s+level)?\s*[:=]\s*[OFMHS]\b)", line, re.I):
                counts["award_lines"] += 1
                continue
            line, found = number.subn("[redacted identity]", line)
            counts["team_variants"] += found
            output.append(f"L{len(output) + 1:05d}: {line}")
    text = "\n".join(output) + "\n"
    if number.search(text) or any(s.casefold() in text.casefold() for s in schools):
        raise ValueError("Residual identifying token after redaction")
    # Markers and location labels are not counted as manuscript words.
    body = re.sub(r"\[.*?\]|\bL\d+:?", " ", text)
    words = re.findall(r"\b\w+\b", body, re.UNICODE)
    if not words:
        raise ValueError("No manuscript text remains; image/empty or over-redacted PDF")
    return text, {"word_count": len(words), "redactions": dict(counts),
                  "limitations": ["Text extraction loses figures, layout and some mathematics; no OCR was performed.",
                                  "Heuristic identity/header redaction may remove relevant content or miss names; human anonymity audit required."],
                  "sparse_pages": [i for i, p in enumerate(pages, 1) if len(p["text"].split()) < 20]}


def make_pairs(index, contexts, packet, key, workspace, seed=SEED):
    packet, key, workspace = Path(packet).resolve(), Path(key).resolve(), Path(workspace).resolve()
    if _within(key, packet):
        raise ValueError("Answer key must be outside the judge packet workspace")
    if packet.exists() or key.exists():
        raise ValueError("Refuse to overwrite a packet or key; choose fresh paths")
    data = read_json(index)
    if data.get("schema") != 1 or not isinstance(data.get("papers"), list):
        raise ValueError("index requires schema:1 and papers array")
    papers = [dict(p) for p in data["papers"]
              if p.get("use") == "evaluation_candidate" and p.get("award") in {"O", "M", "H"}]
    groups = defaultdict(list)
    identities = set()
    for p in papers:
        problem = p.get("problem", "")
        match = re.fullmatch(r"MCM-(\d{4})-([ABC])", problem)
        if not match or p.get("year") != int(match[1]):
            raise ValueError("Candidate problem/year must identify an MCM A/B/C problem")
        identity = (problem, str(p.get("team")))
        if identity in identities:
            raise ValueError("Duplicate candidate identity")
        identities.add(identity)
        if not str(p.get("team", "")).isdigit() or p.get("version") not in {"original_submission", "journal_edited", "unknown"}:
            raise ValueError("Candidate team/version missing or invalid")
        groups[problem].append(p)
    letters = Counter(problem[-1] for problem in groups)
    if len(groups) < 8 or any(letters[x] < 2 for x in "ABC"):
        raise ValueError("Corpus minimum: 8 problems, at least two each of A/B/C")
    for problem, group in groups.items():
        if sum(p["award"] == "O" for p in group) < 2 or sum(p["award"] in {"M", "H"} for p in group) < 2:
            raise ValueError(f"{problem}: minimum two O and two M/H candidates required")
    # Check every context before opening any manuscript body.
    context_text, context_key, readiness = _contexts(contexts, workspace, groups)
    statement_attachments = {problem: ctx["statement_attachment"] for problem, ctx in context_key.items()
                             if "statement_attachment" in ctx}
    for p in papers:
        source = {"path": p.get("local_path"), "sha256": p.get("sha256")}
        p["_path"] = _file(workspace, source, "candidate paper")
        if p["_path"].suffix.lower() != ".pdf":
            raise ValueError("Candidate manuscript must be a PDF")
    from scripts.pdf_text import extract_pages
    # Statistical sampling seeds are public. Blinding decisions must never be
    # reconstructable from one; the actual choices are sealed in the key.
    rng = random.SystemRandom()
    papers.sort(key=lambda p: (p["problem"], str(p["team"])))
    rng.shuffle(papers)
    bodies, private_papers = {}, {}
    for p in papers:
        pid = "D" + secrets.token_hex(16)
        p["_id"] = pid
        schools = list(p.get("school_aliases", []))
        schools.extend(p[k] for k in ("school", "institution") if p.get(k))
        pages = extract_pages(p["_path"], text_backend="pdfium")
        actual_backends = sorted({page["text_backend"] for page in pages})
        if actual_backends != ["pdfium"]:
            raise ValueError("Uniform PDFium extraction required for every candidate page; no mixed-backend fallback")
        text, record = anonymize_pages(pages, p["team"], schools)
        record["text_extraction"] = {"requested_backend": "pdfium", "actual_backends": actual_backends,
                                     "pages": len(pages),
                                     "limitations": ["PDFium text may still misorder content or misdecode glyphs; inspect extraction quality.",
                                                     "No OCR or alternate-backend fallback; figures/layout and some mathematics are not preserved."]}
        bodies[pid] = text
        private_papers[pid] = {k: p[k] for k in ("problem", "team", "award", "version", "sha256", "local_path")}
        private_papers[pid].update(record)
        private_papers[pid].update(pdf_features(p["_path"], pages))
        private_papers[pid]["anonymous_sha256"] = text_sha256(text)
        private_papers[pid]["anchor_level"] = context_key[p["problem"]]["anchor_level"]
    pairs, private_pairs = [], {}
    for problem, group in sorted(groups.items()):
        high = sorted((p["_id"] for p in group if p["award"] == "O"))
        low = sorted((p["_id"] for p in group if p["award"] in {"M", "H"}))
        choices = [(a, b, "O_vs_MH") for a in high for b in low]
        choices += [(*rng.choice(list(itertools.combinations(high, 2))), "O_vs_O"),
                    (*rng.choice(list(itertools.combinations(low, 2))), "MH_vs_MH")]
        for left, right, kind in choices:
            if rng.randrange(2):
                left, right = right, left
            pairs.append({"problem": problem, "left": left, "right": right, "_kind": kind})
    rng.shuffle(pairs)
    for pair in pairs:
        pid = "Q" + secrets.token_hex(16)
        kind = pair.pop("_kind")
        pair["pair_id"] = pid
        # A/B are local to this pair, never reusable manuscript identifiers.
        # The two presentation tokens are unrelated to side, award or order.
        pair["presentations"] = {"normal": secrets.token_hex(16), "swapped": secrets.token_hex(16)}
        private_pairs[pid] = {**pair, "kind": kind,
                              "aliases": {"A": pair["left"], "B": pair["right"]}}
    external_selection = {"seed": seed, "pair_ids": stratified_sample(pairs, 16, seed),
                          "method": "problem-stratified round-robin without replacement from all pairs",
                          "selected_before_review": True}
    extraction_receipt = {"requested_backend": "pdfium", "actual_backend_papers": dict(Counter(
        backend for p in private_papers.values() for backend in p["text_extraction"]["actual_backends"])),
        "limitations": ["Uniform backend reduces backend-selection differences between award groups; it does not certify faithful text.",
                        "PDFium may still misorder text or misdecode glyphs; no OCR/fallback; human extraction audit required."]}
    secret = {"schema": 1, "statistical_seed": seed, "papers": private_papers,
              "text_extraction": extraction_receipt,
              "pairs": private_pairs, "contexts": context_key, "readiness": readiness,
              "planned_judgments_per_pair": 2, "planned_family": "GPT",
              "external_selection": external_selection,
              "blinding": {"method": "SystemRandom and cryptographic opaque tokens", "reproduction": "Replay the sealed choices, never the public statistical seed"},
              "limitations": ["Packet directory separation is not OS access isolation.",
                              "No model review or calibration has been run by this command."]}
    key.parent.mkdir(parents=True, exist_ok=True)
    write_json(key, secret)
    try:
        packet.mkdir(parents=True)
        (packet / "papers").mkdir()
        (packet / "contexts").mkdir()
        if statement_attachments:
            (packet / "statement-original").mkdir()
            for problem, resource in statement_attachments.items():
                shutil.copyfile(resource["path"], packet / "statement-original" / f"{problem}.pdf")
        for pid, text in bodies.items():
            (packet / "papers" / f"{pid}.txt").write_text(text, encoding="utf-8")
        for problem, ctx in context_text.items():
            write_json(packet / "contexts" / f"{problem}.json", ctx)
        bundle = {"schema": 1, "key_sha256": sha256(key), "statistical_seed": seed,
                "coordinator_only": True, "external_selection": external_selection,
                "question": QUESTION, "pairs": pairs, "readiness": readiness,
                "papers": {pid: {"path": f"papers/{pid}.txt", "word_count": private_papers[pid]["word_count"],
                                 "sha256": text_sha256(bodies[pid])}
                           for pid in bodies},
                "contexts": {p: {"path": f"contexts/{p}.json", "sha256": text_sha256(json_text(context_text[p]))} for p in groups},
                "statement_attachments": {p: {"path": f"statement-original/{p}.pdf", "sha256": resource["sha256"]}
                                          for p, resource in statement_attachments.items()},
                "limitations": secret["limitations"] + ["Anonymous text requires a human leakage audit before review."]}
        write_json(packet / "pairs.json", bundle)
        (packet / "COORDINATOR-ONLY.txt").write_text("This bundle reveals the complete comparison graph. Never give it to a judge. Export exactly one pair per judge context.\n", encoding="utf-8")
    except Exception:
        # Retain partial output and key for diagnosis; never silently erase a failure.
        raise
    manuscript_words = sum(private_papers[p[side]]["word_count"] for p in pairs for side in ("left", "right"))
    context_words = sum(len(re.findall(r"\b\w+\b", context_text[p["problem"]][kind]))
                        for p in pairs for kind in ("statement", "rules", "anchor"))
    return {"status": "prepared_not_reviewed", "problems": len(groups), "papers": len(papers),
            "pairs": len(pairs), "pair_kinds": dict(Counter(p["kind"] for p in private_pairs.values())),
            "packet": str(packet), "coordinator_only": True, "key_sha256": sha256(key), "readiness": readiness,
            "text_extraction": extraction_receipt,
            "anonymous_word_count": sum(p["word_count"] for p in private_papers.values()),
            "pair_manuscript_words_one_pass": manuscript_words,
            "pair_context_words_one_pass": context_words,
            "pair_total_words_two_judges": 2 * (manuscript_words + context_words),
            "budget_limitations": "Word counts are not tokens; include prompt/output overhead and actual tokenizer/model before user budget approval."}


def _packet(path):
    root = Path(path).resolve()
    data = read_json(root / "pairs.json")
    allowed = {"schema", "key_sha256", "statistical_seed", "coordinator_only", "external_selection", "question", "pairs", "papers", "contexts", "statement_attachments", "limitations", "readiness"}
    if set(data) != allowed or data.get("coordinator_only") is not True or data.get("schema") != 1 or not re.fullmatch(r"[0-9a-f]{64}", data.get("key_sha256", "")):
        raise ValueError("Invalid coordinator-only bundle schema or unexpected label-bearing metadata")
    seen = set()
    for pair in data["pairs"]:
        if set(pair) != {"pair_id", "problem", "left", "right", "presentations"} or pair["pair_id"] in seen or pair["left"] == pair["right"]:
            raise ValueError("Invalid or duplicate anonymous pair")
        seen.add(pair["pair_id"])
        for pid in (pair["left"], pair["right"]):
            if pid not in data["papers"] or set(data["papers"][pid]) != {"path", "word_count", "sha256"}:
                raise ValueError("Invalid anonymous paper metadata")
    resources = list(data["papers"].values()) + list(data["contexts"].values()) + list(data["statement_attachments"].values())
    for resource in resources:
        if not isinstance(resource, dict) or not resource.get("path") or not _within(root / resource["path"], root) or not (root / resource["path"]).is_file():
            raise ValueError("Packet reference escapes packet workspace or is missing")
        if sha256(root / resource["path"]) != resource.get("sha256"):
            raise ValueError("Packet content SHA256 mismatch")
    return root, data


def _check_context(ctx):
    if set(ctx) != {"problem", "year", "statement", "rules", "anchor", "resource_metadata"}:
        raise ValueError("Unexpected context metadata; paper source/award labels cannot be exported")
    if set(ctx["resource_metadata"]) != {"statement", "rules", "anchor"}:
        raise ValueError("Incomplete resource metadata")
    allowed = {"completeness", "limitations", "source_url", "source_sha256", "original_pdf"}
    for kind, meta in ctx["resource_metadata"].items():
        if not isinstance(meta, dict) or set(meta) - allowed or meta.get("completeness") not in {"complete", "partial"} or not isinstance(meta.get("limitations"), list):
            raise ValueError("Unexpected resource metadata; possible identity/award leak")


def judge_packet(packet, output, judge_id, family, instance, swap=False, selected=None):
    """Export exactly one isolated comparison; the full graph is coordinator-only."""
    root, data = _packet(packet)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Refuse to overwrite a judge workspace")
    if _within(output, root) or _within(root, output):
        raise ValueError("Judge workspace must be separate from the coordinator-only graph bundle")
    if selected is None or len(selected) != 1:
        raise ValueError("A judge workspace must contain exactly one selected pair")
    matches = [p for p in data["pairs"] if p["pair_id"] in selected]
    if len(matches) != 1:
        raise ValueError("Selected pair ID is not present in the coordinator bundle")
    pair = matches[0]
    ctx = read_json(root / data["contexts"][pair["problem"]]["path"])
    _check_context(ctx)
    output.mkdir(parents=True)
    for alias, pid in (("A", pair["left"]), ("B", pair["right"])):
        shutil.copyfile(root / data["papers"][pid]["path"], output / f"{alias}.txt")
    original = data["statement_attachments"].get(pair["problem"])
    if original:
        shutil.copyfile(root / original["path"], output / "problem-original.pdf")
    write_json(output / "context.json", ctx)
    left, right = ("B", "A") if swap else ("A", "B")
    presentation = pair["presentations"]["swapped" if swap else "normal"]
    blockers = [b for b in data["readiness"]["blockers"] if b["problem"] == pair["problem"]]
    readiness = {"ready_for_formal_eval": not blockers, "blockers": blockers}
    safe = {"schema": 1, "key_sha256": data["key_sha256"], "pair_id": pair["pair_id"],
            "presentation_id": presentation, "problem": pair["problem"],
            "left": left, "right": right, "readiness": readiness,
            "files": {f"{alias}.txt": sha256(output / f"{alias}.txt") for alias in ("A", "B")}}
    safe["files"]["context.json"] = sha256(output / "context.json")
    if original:
        safe["files"]["problem-original.pdf"] = sha256(output / "problem-original.pdf")
    write_json(output / "pair.json", safe)
    row = {"pair_id": pair["pair_id"], "presentation_id": presentation, "left": left, "right": right,
           "preferred": None, "confidence": None,
           "reasons": [{"left_location": None, "right_location": None, "reason": None} for _ in range(3)],
           "mechanical_findings": []}
    write_json(output / "judgments-template.json", {"schema": 1, "key_sha256": data["key_sha256"],
               "judge": {"id": judge_id, "family": family, "instance": instance}, "judgments": [row]})
    statuses = "\n".join(f"- {kind}: {meta['completeness']}; limitations: " +
        ("; ".join(meta["limitations"]) or "none declared") for kind, meta in ctx["resource_metadata"].items())
    request = (f"# Anonymous comparison · {pair['problem']}\n\n{QUESTION}\n\n"
               f"Formal evaluation context ready: {str(readiness['ready_for_formal_eval']).lower()}. "
               "Partial context requires the coordinator's user-approved scope decision.\n\n"
               f"Resource completeness and limits:\n{statuses}\n\n"
               f"Read context.json. LEFT: {left}.txt; RIGHT: {right}.txt.\n"
               + ("Read problem-original.pdf to inspect original maps, figures and question labels missing from the extracted text. "
                  "This illustration supplement does not mark the historical rules or data attachments complete.\n" if original else "") +
               "Use page/L-number locations. Abstain if extraction prevents comparison. "
               "Use only this directory, with no previous-pair judgments or other pair directories.\n")
    (output / "request.md").write_text(request, encoding="utf-8")
    (output / "README.md").write_text("Complete this single comparison in a fresh context. A/B are local manuscript aliases only. "
        "Do not inspect sibling pairs or the coordinator bundle. Directory separation alone is not OS access isolation.\n", encoding="utf-8")
    return {"status": "prepared_not_reviewed", "pairs": 1, "output": str(output), "swapped": swap,
            "readiness": readiness}


def stratified_sample(pairs, count=16, seed=SEED):
    if len(pairs) < count:
        raise ValueError(f"Need {count} distinct pairs; only {len(pairs)} available; do not pad")
    groups = defaultdict(list)
    for p in pairs:
        groups[p["problem"]].append(p["pair_id"])
    if len(groups) > count:
        raise ValueError("Sample size cannot represent every problem")
    rng = random.Random(seed)
    names = sorted(groups)
    rng.shuffle(names)
    for g in groups.values():
        g.sort()
        rng.shuffle(g)
    result = []
    while len(result) < count:
        for name in names:
            if groups[name] and len(result) < count:
                result.append(groups[name].pop())
    return result


def export_packet(packet, output, judge="external", seed=SEED):
    if judge != "external":
        raise ValueError("export-packet supports --judge external")
    root, data = _packet(packet)
    selected = data["external_selection"]
    if seed != selected["seed"]:
        raise ValueError("External sample is frozen in the coordinator key; cannot change its seed")
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Refuse to overwrite an external packet")
    if _within(output, root) or _within(root, output):
        raise ValueError("External container must be separate from the coordinator-only graph bundle")
    output.mkdir(parents=True)
    for pid in selected["pair_ids"]:
        judge_packet(packet, output / pid, "external-fill-in", "external-fill-in", "external-" + pid,
                     selected={pid})
    (output / "README.md").write_text("Each opaque subdirectory is a separate, self-contained single-pair input. "
        "Use a fresh conversation for each pair. Do not give a judge the parent directory or sibling pairs. "
        "The selection record and complete comparison graph remain with the coordinator. "
        "Repeated text may still reveal that a manuscript appears in another pair if inputs are pooled; "
        "local aliases do not prevent content recognition.\n", encoding="utf-8")
    # This return value is coordinator evidence, never part of the judge files.
    return {"status": "prepared_not_reviewed", "pairs": 16, "output": str(output),
            "selection_seed": seed, "selection": selected["pair_ids"],
            "coordinator_receipt_only": True, "readiness": data["readiness"]}


def _judgments(paths, key=None):
    output = []
    for path in paths:
        data = read_json(path)
        judge = data.get("judge", {})
        if not re.fullmatch(r"[0-9a-f]{64}", data.get("key_sha256", "")):
            raise ValueError("Judgment requires a valid key SHA256 identity")
        if data.get("schema") != 1 or any(not isinstance(judge.get(k), str) or not judge[k].strip() for k in ("id", "family", "instance")):
            raise ValueError("Judgment requires schema:1 and explicit judge id/family/instance")
        if any(isinstance(value, str) and "fill-in" in value for value in judge.values()):
            raise ValueError("Complete actual judge identity before analysis")
        if key is not None and data.get("key_sha256") != sha256(key):
            raise ValueError("Judgment/key SHA256 mismatch")
        if not isinstance(data.get("judgments"), list):
            raise ValueError("judgments array required")
        seen = set()
        for j in data["judgments"]:
            if j.get("pair_id") in seen or not j.get("pair_id") or j.get("left") == j.get("right"):
                raise ValueError("Duplicate or invalid judgment pair")
            seen.add(j["pair_id"])
            c = j.get("confidence")
            if j.get("preferred") not in {"left", "right", "abstain"} or isinstance(c, bool) or not isinstance(c, (float, int)) or not .5 <= c <= 1:
                raise ValueError("preferred must be left/right/abstain and confidence in [0.5,1]")
            reasons = j.get("reasons")
            if not isinstance(reasons, list) or len(reasons) != 3 or any(not isinstance(r, dict) or any(not isinstance(r.get(k), str) or not r[k].strip() for k in ("left_location", "right_location", "reason")) for r in reasons):
                raise ValueError("Exactly three reasons, each with both manuscript locations, required")
            if not isinstance(j.get("mechanical_findings"), list):
                raise ValueError("mechanical_findings must be a separate array")
            if "fresh_instance" in j and (not isinstance(j["fresh_instance"], str) or not j["fresh_instance"].strip()):
                raise ValueError("fresh_instance must be a nonempty actual context identifier")
        output.append((data, path))
    return output


def _observations(key_path, results):
    key = read_json(key_path)
    if key.get("schema") != 1 or not isinstance(key.get("pairs"), dict) or not isinstance(key.get("papers"), dict):
        raise ValueError("Invalid private answer key")
    obs = []
    seen_runs = set()
    for data, path in _judgments(results, key_path):
        for j in data["judgments"]:
            if j["pair_id"] not in key["pairs"]:
                raise ValueError("Unknown pair in judgment")
            pair = key["pairs"][j["pair_id"]]
            judge = {**data["judge"], "instance": j.get("fresh_instance", data["judge"]["instance"])}
            run = tuple(judge[k] for k in ("id", "family", "instance"))
            if "aliases" in pair:
                normal = j.get("presentation_id") == pair["presentations"]["normal"]
                swapped = j.get("presentation_id") == pair["presentations"]["swapped"]
                expected = ("A", "B") if normal else ("B", "A") if swapped else None
                if expected is None or (j["left"], j["right"]) != expected:
                    raise ValueError("Judgment local aliases/presentation differ from the sealed pair")
                left, right = pair["aliases"][j["left"]], pair["aliases"][j["right"]]
            else:
                # Historical coordinator keys remain descriptive only; no new
                # completeness certification is inferred for their old records.
                left, right = j["left"], j["right"]
                if {left, right} != {pair["left"], pair["right"]}:
                    raise ValueError("Judgment paper identity differs from sealed pair")
            identity = (run, j["pair_id"], j["left"], j["right"])
            if identity in seen_runs:
                raise ValueError("Duplicate judge-instance/order observation across files")
            seen_runs.add(identity)
            winner = (left if j["preferred"] == "left" else right) if j["preferred"] != "abstain" else None
            is_test = (pair.get("kind") == "O_vs_MH"
                       and {key["papers"][p].get("award") for p in (left, right)} in ({"O", "M"}, {"O", "H"}))
            obs.append({**j, "left": left, "right": right, "problem": pair["problem"], "kind": pair.get("kind", "unlabelled"), "winner": winner,
                        "correct": int(winner is not None and key["papers"][winner]["award"] == "O") if is_test else None,
                        "judge": judge, "source": str(path)})
    return key, obs


def _coverage(key, obs):
    planned = key.get("planned_judgments_per_pair")
    family = key.get("planned_family")
    if planned != 2 or not isinstance(family, str):
        return {"complete": False, "status": "legacy_or_missing_preregistered_plan", "planned_judgments_per_pair": planned}
    instance_pairs = defaultdict(set)
    for o in obs:
        identity = (o["judge"]["family"].casefold(), o["judge"]["instance"])
        instance_pairs[identity].add(o["pair_id"])
    reused = {identity for identity, pairs in instance_pairs.items() if len(pairs) > 1}
    details, by_kind, by_judge = {}, defaultdict(lambda: Counter()), defaultdict(lambda: Counter())
    for pid, pair in key["pairs"].items():
        rows = [o for o in obs if o["pair_id"] == pid]
        candidates = [o for o in rows if o["judge"]["family"].casefold() == family.casefold()
                      and (o["judge"]["family"].casefold(), o["judge"]["instance"]) not in reused]
        distinct_ids = {o["judge"]["id"] for o in candidates}
        distinct_instances = {o["judge"]["instance"] for o in candidates}
        valid_two = any(a["judge"]["id"] != b["judge"]["id"] and a["judge"]["instance"] != b["judge"]["instance"]
                        and a["left"] == b["right"] for a, b in itertools.combinations(candidates, 2))
        effective = 2 if valid_two else int(bool(candidates))
        duplicate_id = {j: n for j, n in Counter(o["judge"]["id"] for o in candidates).items() if n > 1}
        duplicate_instance = {j: n for j, n in Counter(o["judge"]["instance"] for o in candidates).items() if n > 1}
        details[pid] = {"problem": pair["problem"], "kind": pair["kind"], "planned": planned,
            "observed": len(rows), "eligible_family_observations": len(candidates), "effective": effective,
            "missing": planned - effective, "distinct_judge_ids": sorted(distinct_ids),
            "distinct_fresh_instances": len(distinct_instances), "opposite_orders": valid_two,
            "repeated_judge_ids": duplicate_id, "repeated_instances": duplicate_instance}
        by_kind[pair["kind"]].update(pairs=1, planned=planned, observed=len(rows), effective=effective,
                                    missing=planned - effective, complete_pairs=int(effective == planned))
        for o in candidates:
            by_judge[o["judge"]["id"]].update({pair["kind"]: 1})
    missing = sum(d["missing"] for d in details.values())
    excess = sum(max(0, d["eligible_family_observations"] - planned) for d in details.values())
    repeated = sum(bool(d["repeated_judge_ids"] or d["repeated_instances"]) for d in details.values())
    complete = bool(details) and missing == 0 and excess == 0 and repeated == 0
    return {"complete": complete, "status": "complete" if complete else "incomplete_or_repeated",
        "planned_judgments_per_pair": planned, "planned_family": family,
        "planned_pairs": len(details), "planned_judgments": planned * len(details),
        "observed_judgments": len(obs), "effective_judgments": planned * len(details) - missing,
        "completion_fraction": (planned * len(details) - missing) / (planned * len(details)) if details else 0,
        "missing_judgments": missing, "excess_judgments": excess, "pairs_with_repeated_ids_or_instances": repeated,
        "missing_pair_ids": [pid for pid, d in details.items() if d["missing"]],
        "reused_fresh_instances_across_pairs": [{"family": f, "instance": i, "pairs": len(instance_pairs[f, i])} for f, i in sorted(reused)],
        "by_kind": dict(by_kind), "by_judge_id": dict(by_judge), "pairs": details,
        "independence_limit": "Declared identifiers and opposite order are checked; actual fresh execution needs separate provenance evidence."}


def _accuracy(obs):
    test = [o for o in obs if o["kind"] == "O_vs_MH"]
    n = len(test)
    decided = sum(o["winner"] is not None for o in test)
    correct = sum(o["correct"] for o in test)
    return {"n": n, "correct": correct, "abstentions": n - decided,
            "accuracy": correct / n if n else None,
            "decided_accuracy": correct / decided if decided else None,
            "decision_coverage": decided / n if n else None,
            "denominator": "all O-vs-M/H judgments; abstention is not a correct identification"}


def _graph(ids, obs, directed=False):
    edges = {pid: set() for pid in ids}
    for o in obs:
        if o["winner"] is None:
            continue
        loser = o["right"] if o["winner"] == o["left"] else o["left"]
        edges[o["winner"]].add(loser)
        if not directed:
            edges[loser].add(o["winner"])
    def reach(start):
        todo, found = [start], {start}
        while todo:
            for other in edges[todo.pop()]:
                if other not in found:
                    found.add(other)
                    todo.append(other)
        return found
    if directed:
        return bool(ids) and all(len(reach(pid)) == len(ids) for pid in ids)
    remaining, components = set(ids), []
    while remaining:
        component = reach(min(remaining))
        remaining -= component
        components.append(sorted(component))
    return components


def _bt_problem(ids, obs, ridge):
    decided = [o for o in obs if o["winner"] is not None]
    components = _graph(ids, decided)
    separated = bool(decided) and not _graph(ids, decided, directed=True)
    result = {"n": len(decided), "connected_components": len(components),
              "separated_or_disconnected": separated, "ridge": ridge,
              "method": "penalized_BT" if ridge > 0 else "BT_MLE",
              "centering": "mean zero within each problem; no cross-problem absolute ranking",
              "scores": {pid: None for pid in ids}}
    if not decided:
        return {**result, "status": "no_decided_observations", "converged": False}
    if ridge == 0 and separated:
        return {**result, "status": "no_finite_identifiable_MLE", "converged": False}
    positions = {pid: i for i, pid in enumerate(ids)}
    a = np.array([positions[o["left"]] for o in decided])
    b = np.array([positions[o["right"]] for o in decided])
    y = np.array([float(o["winner"] == o["left"]) for o in decided])
    def objective(x):
        delta = x[a] - x[b]
        residual = expit(delta) - y
        grad = ridge * x
        np.add.at(grad, a, residual)
        np.add.at(grad, b, -residual)
        value = np.logaddexp(0, delta).sum() - np.dot(y, delta) + .5 * ridge * np.dot(x, x)
        return float(value), grad
    fit = minimize(objective, np.zeros(len(ids)), jac=True, method="BFGS", options={"gtol": 1e-8, "maxiter": 2000})
    grad_norm = float(np.max(np.abs(objective(fit.x)[1])))
    converged = bool(fit.success or grad_norm < 1e-6)
    active = {pid for o in decided for pid in (o["left"], o["right"])}
    centered = fit.x - fit.x.mean()
    scores = {pid: float(centered[i]) if pid in active and converged else None for i, pid in enumerate(ids)}
    return {**result, "scores": scores, "status": "converged_penalized" if converged and ridge else "converged_MLE" if converged else "optimization_failed",
            "converged": converged, "optimizer_success": bool(fit.success), "optimizer_message": str(fit.message),
            "gradient_max_abs": grad_norm,
            "limitations": (["Ridge supplies finite scores under separation; these are not an unpenalized MLE."] if ridge else []) +
                            (["Disconnected comparison components: penalized scores between components depend on the penalty."] if len(components) > 1 else [])}


def _group_difference(key, bts, multiplicities):
    values = {"O": [], "MH": []}
    for problem, count in multiplicities.items():
        for pid, score in bts[problem]["scores"].items():
            if score is not None:
                group = "O" if key["papers"][pid]["award"] == "O" else "MH"
                values[group].extend([score] * count)
    return float(np.mean(values["O"]) - np.mean(values["MH"])) if all(values.values()) else None


def _ci(values, clusters):
    finite = [v for v in values if v is not None and math.isfinite(v)]
    if clusters < 2 or not finite:
        return {"interval": None, "status": "insufficient_clusters_or_data", "valid_replicates": len(finite)}
    return {"interval": [float(v) for v in np.quantile(finite, [.025, .975])],
            "status": "degenerate_point_interval" if len(set(finite)) == 1 else "small_cluster_exploratory" if clusters < 8 else "computed",
            "valid_replicates": len(finite)}


def _length_bias(key, obs):
    decided = [o for o in obs if o["winner"] is not None]
    x = [key["papers"][o["left"]]["word_count"] - key["papers"][o["right"]]["word_count"] for o in decided]
    y = [int(o["winner"] == o["left"]) for o in decided]
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return {"n": len(x), "pearson": None, "spearman": None, "status": "insufficient_or_constant_data"}
    return {"n": len(x), "pearson": float(np.corrcoef(x, y)[0, 1]), "spearman": float(spearmanr(x, y).statistic),
            "status": "descriptive", "variables": "left-minus-right word count vs preference for left",
            "limitations": "Repeated papers/judgments are dependent; correlation is descriptive, not a causal test or independent-sample p-value."}


def fit(key_path, results, seed=SEED, ridge=1.0):
    if not math.isfinite(ridge) or ridge < 0:
        raise ValueError("ridge must be finite and nonnegative")
    key, all_obs = _observations(key_path, results)
    coverage = _coverage(key, all_obs)
    planned_family = key.get("planned_family")
    obs = [o for o in all_obs if not planned_family or o["judge"]["family"].casefold() == planned_family.casefold()]
    problems = sorted({p["problem"] for p in key["papers"].values()})
    by_problem = {p: [o for o in obs if o["problem"] == p] for p in problems}
    bts = {p: _bt_problem(sorted(pid for pid, item in key["papers"].items() if item["problem"] == p), by_problem[p], ridge)
           for p in problems}
    rng = random.Random(seed)
    acc_samples, bt_samples = [], []
    informative = sum(bool(_accuracy(by_problem[p])["n"]) for p in problems)
    for _ in range(BOOTSTRAPS):
        counts = Counter(rng.choices(problems, k=len(problems))) if problems else Counter()
        sampled = [o for p, count in counts.items() for o in by_problem[p] * count]
        acc_samples.append(_accuracy(sampled)["accuracy"])
        bt_samples.append(_group_difference(key, bts, counts))
    stratified = {"problem": {}, "anchor_level": {}, "version": {}}
    for dimension in stratified:
        grouped = defaultdict(list)
        for o in obs:
            papers = [key["papers"][o[k]] for k in ("left", "right")]
            label = o["problem"] if dimension == "problem" else key["contexts"][o["problem"]]["anchor_level"] if dimension == "anchor_level" else "+".join(sorted({p["version"] for p in papers}))
            grouped[label].append(o)
        stratified[dimension] = {k: _accuracy(v) for k, v in sorted(grouped.items())}
    accuracy = _accuracy(obs)
    accuracy["cluster_bootstrap_95"] = _ci(acc_samples, informative)
    accuracy["population_scope"] = "complete preregistered planned-family observations" if coverage["complete"] else "observed subset only; missing judgments not imputed"
    difference = _group_difference(key, bts, Counter(problems))
    lower = accuracy["cluster_bootstrap_95"]["interval"]
    return {"schema": 1, "status": "analysed_complete_plan" if coverage["complete"] else "incomplete_observed_subset" if obs else "no_observations",
            "judgments": len(obs), "input_judgments": len(all_obs), "coverage": coverage,
            "context_readiness": key.get("readiness", {"ready_for_formal_eval": False, "reason": "legacy key has no context readiness record"}),
            "accuracy": accuracy, "BT": {"method": "penalized_BT" if ridge else "BT_MLE", "ridge": ridge,
             "problems": bts, "O_minus_MH_mean": difference, "cluster_bootstrap_95": _ci(bt_samples, sum(b["converged"] for b in bts.values()))},
            "bootstrap": {"unit": "problem", "replicates": BOOTSTRAPS, "seed": seed,
                          "BT_refit": "Within-problem fits are unchanged by resampling whole problem clusters; resample their score sets with multiplicity."},
            "stratified_accuracy": stratified, "length_preference": _length_bias(key, obs),
            "predeclared_checks": {"complete_preregistered_coverage": coverage["complete"],
                 "accuracy_at_least_0_70": accuracy["accuracy"] >= .70 if coverage["complete"] and accuracy["accuracy"] is not None else None,
                 "cluster_CI_lower_above_0_5": lower[0] > .5 if coverage["complete"] and lower else None,
                 "cross_family_kappa_above_0_4": "requires external agreement result; not tested here"},
            "limitations": ["Official awards are comparison labels, not proof of mathematical correctness.",
                            "No absolute award prediction or calibrated O probability is produced.",
                            "Bootstrap uncertainty is across sampled problems, not independent paper pairs.",
                            "Original submission identity and prior/pretraining exposure remain corpus limitations."]}


def agreement(first, second):
    inputs = _judgments([first, second])
    one, two = (v[0] for v in inputs)
    if one.get("key_sha256") != two.get("key_sha256"):
        raise ValueError("Agreement inputs refer to different key identities")
    maps = [{j["pair_id"]: j for j in d["judgments"]} for d in (one, two)]
    shared = sorted(set(maps[0]) & set(maps[1]))
    a, b, swap_a, swap_b = [], [], [], []
    same_instance_flags = []
    swap_subsets = {"same_instance": [], "cross_instance": []}
    def actual_judge(header, row):
        return (header["id"], header["family"].casefold(), row.get("fresh_instance", header["instance"]))
    for pid in shared:
        x, y = (m[pid] for m in maps)
        if {x["left"], x["right"]} != {y["left"], y["right"]}:
            raise ValueError("Same pair_id has different manuscript identities")
        ids = sorted((x["left"], x["right"]))
        def choice(j):
            return "abstain" if j["preferred"] == "abstain" else str(ids.index(j[j["preferred"]]))
        a.append(choice(x))
        b.append(choice(y))
        same_actual = actual_judge(one["judge"], x) == actual_judge(two["judge"], y)
        same_instance_flags.append(same_actual)
        if x["left"] == y["right"]:
            swap_a.append(a[-1])
            swap_b.append(b[-1])
            swap_subsets["same_instance" if same_actual else "cross_instance"].append(a[-1] == b[-1])
    same_family = one["judge"]["family"].casefold() == two["judge"]["family"].casefold()
    n = len(a)
    same_instance = bool(n) and all(same_instance_flags)
    mixed_instances = any(same_instance_flags) and not same_instance
    comparison = ("no_shared_observations" if not n else "different_family_agreement" if not same_family else
                  "same_judge_repeated" if same_instance else "same_family_mixed_instance_agreement" if mixed_instances else
                  "same_family_two_instance_agreement")
    swap_scope = ("mixed actual instances; inspect same-instance and cross-instance reversed-order subsets" if mixed_instances else
                  "same judge instance, reversed order" if same_instance else
                  "reversed order across instances; not isolated same-judge order stability")
    raw = sum(x == y for x, y in zip(a, b)) / n if n else None
    chance = sum(a.count(k) / n * b.count(k) / n for k in {"0", "1", "abstain"}) if n else None
    kappa = (raw - chance) / (1 - chance) if n and chance < 1 else None
    return {"schema": 1, "comparison": comparison,
            "n_shared": n, "unmatched_first": len(maps[0]) - n, "unmatched_second": len(maps[1]) - n,
            "instance_comparisons": {"same_instance": sum(same_instance_flags), "cross_instance": n - sum(same_instance_flags),
                                     "resolution": "judge id/family and row fresh_instance, falling back to enclosing instance"},
            "agreement": raw, "cohens_kappa": None if same_family else kappa,
            "kappa_status": "not_reported_as_external_independence_same_family" if same_family else "degenerate_or_no_samples" if kappa is None else "computed",
            "abstentions_first": a.count("abstain"), "abstentions_second": b.count("abstain"),
            "swap_stability": {"n": len(swap_a), "agreement": sum(x == y for x, y in zip(swap_a, swap_b)) / len(swap_a) if swap_a else None,
                "scope": swap_scope, "identity_based": True,
                "same_instance": {"n": len(swap_subsets["same_instance"]),
                                  "agreement": sum(swap_subsets["same_instance"]) / len(swap_subsets["same_instance"]) if swap_subsets["same_instance"] else None},
                "cross_instance": {"n": len(swap_subsets["cross_instance"]),
                                   "agreement": sum(swap_subsets["cross_instance"]) / len(swap_subsets["cross_instance"]) if swap_subsets["cross_instance"] else None}},
            "external_16_check": {"exactly_16_shared": n == 16,
                "kappa_above_0_4": kappa > .4 if not same_family and n == 16 and kappa is not None else None},
            "limitations": ["Different family names do not by themselves prove independent exposure or execution.",
                             "Agreement includes explicit abstentions; raw decision coverage must be inspected."]}


FEATURE_NAMES = ('word_count', 'page_count', 'figure_count', 'caption_max', 'embedded_image_objects')


def pdf_features(path, pages):
    """Separate caption-number and raster-object proxies; neither is a figure count.

    Missing caption evidence stays null (image-only captions are not recovered).
    Per-page image resources include reused artwork; vector figures may be zero.
    """
    captions = [int(m.group(1)) for page in pages for m in re.finditer(
        r'^\s*(?:Figure|Fig\.?)\s*(\d+)\s*[.:]', page['text'], re.I | re.M)]
    result = {'page_count': len(pages), 'figure_count': None,
              'caption_max': max(captions) if captions else None,
              'embedded_image_objects': None,
              'feature_provenance': {
                  'page_count': 'all extracted physical PDF pages, not contest counted pages',
                  'figure_count': 'manual semantic figure count unavailable; never inferred from proxies',
                  'caption_max': 'maximum integer in line-initial Figure/Fig numbered-caption candidates; references or extraction order may contaminate it; no OCR',
                  'embedded_image_objects': 'sum of pypdf per-page raster image resources, reused on different pages counted again; multiple draws of one resource on a page are not separate; excludes vector artwork'}}
    try:
        from pypdf import PdfReader
        result['embedded_image_objects'] = sum(len(page.images) for page in PdfReader(path).pages)
    except Exception as exc:
        result['feature_provenance']['embedded_image_objects'] += f'; unavailable: {type(exc).__name__}'
    return result


def baselines(key_path, results=(), features=None):
    """Describe fixed larger-is-preferred rules on the exact returned comparisons.

    Award accuracy uses only explicitly labelled O-vs-M/H observations. Unlabelled
    practice papers receive preferences and overlap, never an imputed award.
    Without results the sealed pairs are previewed, with no accuracy estimate.
    """
    key, observations = _observations(key_path, results)
    paper_features = {pid: {name: paper.get(name) for name in FEATURE_NAMES}
                      for pid, paper in key['papers'].items()}
    provenance = {pid: paper.get('feature_provenance', {}) for pid, paper in key['papers'].items()}
    overlay_sha = None
    if features is not None:
        overlay = read_json(features)
        if overlay.get('schema') != 1 or overlay.get('key_sha256') != sha256(key_path):
            raise ValueError('Feature overlay/key SHA256 mismatch or unsupported schema')
        if not isinstance(overlay.get('papers'), dict):
            raise ValueError('Feature overlay requires a papers mapping')
        for pid, item in overlay['papers'].items():
            if pid not in key['papers'] or not isinstance(item, dict) or not re.fullmatch(r'[0-9a-f]{64}', str(item.get('pdf_sha256', ''))) or item['pdf_sha256'] != key['papers'][pid].get('sha256'):
                raise ValueError('Feature overlay paper/PDF SHA256 mismatch')
            for name in FEATURE_NAMES:
                if name in item:
                    paper_features[pid][name] = item[name]
            provenance[pid] = {'sealed_key': provenance[pid], 'overlay': item.get('provenance', {}),
                               'pdf_sha256': item['pdf_sha256']}
        overlay_sha = sha256(features)
    for pid, fields in paper_features.items():
        for name, value in fields.items():
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f'{pid}/{name}: feature must be null or a nonnegative integer')
    comparisons = []
    entries = observations if results else [dict(p, pair_id=pid, winner=None, source=None,
                                              judge=None, preferred=None) for pid, p in key['pairs'].items()]
    for observation in entries:
        left, right = observation['left'], observation['right']
        awards = [key['papers'][p].get('award') for p in (left, right)]
        labelled_cross = set(awards) in ({'O', 'M'}, {'O', 'H'})
        judged = bool(results)
        winner = observation['winner']
        correct = (winner is not None and key['papers'][winner].get('award') == 'O') if judged and labelled_cross else None
        row = {'pair_id': observation['pair_id'], 'problem': observation['problem'],
               'left': left, 'right': right, 'judge': observation['judge'], 'source': observation['source'],
               'judge_winner': winner, 'judge_correct': correct,
               'judge_abstained': judged and winner is None, 'labelled_cross_award': labelled_cross, 'rules': {}}
        for name in FEATURE_NAMES:
            a, b = paper_features[left][name], paper_features[right][name]
            state = 'missing' if a is None or b is None else 'tie' if a == b else 'decided'
            chosen = (left if a > b else right) if state == 'decided' else None
            rule_correct = chosen is not None and key['papers'][chosen].get('award') == 'O' if judged and labelled_cross else None
            row['rules'][name] = {'left_value': a, 'right_value': b, 'winner': chosen, 'state': state, 'correct': rule_correct}
        comparisons.append(row)
    accuracy_rows = [r for r in comparisons if r['judge_correct'] is not None]
    n = len(accuracy_rows)
    judge = {'correct': sum(r['judge_correct'] for r in accuracy_rows),
             'wrong': sum(not r['judge_correct'] and not r['judge_abstained'] for r in accuracy_rows),
             'abstained': sum(r['judge_abstained'] for r in accuracy_rows)}
    judge['accuracy'] = judge['correct'] / n if n else None
    rules = {}
    for name in FEATURE_NAMES:
        counts = dict.fromkeys(('correct', 'wrong', 'tie', 'missing'), 0)
        cross = {j: dict(counts) for j in ('correct', 'wrong', 'abstain')}
        for row in accuracy_rows:
            item = row['rules'][name]
            state = item['state'] if item['state'] != 'decided' else 'correct' if item['correct'] else 'wrong'
            counts[state] += 1
            jstate = 'abstain' if row['judge_abstained'] else 'correct' if row['judge_correct'] else 'wrong'
            cross[jstate][state] += 1
        overlap = dict.fromkeys(('agreed', 'disagreed', 'judge_abstained', 'rule_tie', 'rule_missing'), 0)
        for row in comparisons if results else []:
            item = row['rules'][name]
            state = 'judge_abstained' if row['judge_abstained'] else 'rule_' + item['state'] if item['winner'] is None else 'agreed' if item['winner'] == row['judge_winner'] else 'disagreed'
            overlap[state] += 1
        rules[name] = {**counts, 'accuracy': counts['correct'] / n if n else None,
                       'cross_table': cross, 'preference_overlap': overlap,
                       'all_comparisons_states': dict(Counter(r['rules'][name]['state'] for r in comparisons))}
    return {'schema': 1, 'key_sha256': sha256(key_path), 'features_sha256': overlay_sha,
            'observations': len(observations), 'accuracy_denominator': n, 'judge': judge,
            'rules': rules, 'comparisons': comparisons, 'paper_features': paper_features,
            'feature_provenance': provenance,
            'policy': {'rule': 'prefer the larger measured value; no composite fitting',
                       'denominator': 'same returned explicitly labelled O-vs-M/H comparisons; ties, missing and judge abstentions remain in it with zero correct credit',
                       'unknown_awards': 'preferences/overlap only; no award imputation or accuracy',
                       'preview': 'without returned judgments report sealed-pair preferences only',
                       'proxies': 'manual figure_count, caption_max and embedded_image_objects are separate rules, not interchangeable counts'},
            'limitations': ['Descriptive paired observations; repeated instances/orderings are dependent.',
                            'No baseline margin or evaluator acceptance is inferred; preregister the margin and validate on new problems.',
                            'Overlay authenticates identities against sealed hashes; it does not independently certify feature measurements.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("make-pairs")
    for name in ("index", "contexts", "packet", "key", "workspace"):
        make.add_argument(f"--{name}", required=True, type=Path)
    make.add_argument("--seed", type=int, default=SEED)
    judge = commands.add_parser("judge-packet", help="prepare requests/templates only; does not run an LLM")
    judge.add_argument("--packet", required=True, type=Path)
    judge.add_argument("--output", required=True, type=Path)
    for name in ("judge-id", "family", "instance"):
        judge.add_argument(f"--{name}", required=True)
    judge.add_argument("--swap", action="store_true")
    judge.add_argument("--pair-id", required=True, help="exactly one opaque sealed pair ID")
    analyse = commands.add_parser("fit")
    analyse.add_argument("--key", required=True, type=Path)
    analyse.add_argument("--results", required=True, nargs="+", type=Path)
    analyse.add_argument("--output", required=True, type=Path)
    analyse.add_argument("--seed", type=int, default=SEED)
    analyse.add_argument("--ridge", type=float, default=1.0)
    base = commands.add_parser("baselines", help="fixed simple-rule comparisons; never calls a model")
    base.add_argument("--key", required=True, type=Path)
    base.add_argument("--results", nargs="*", default=[], type=Path)
    base.add_argument("--features", type=Path, help="optional key/PDF-hash-bound feature overlay")
    base.add_argument("--output", required=True, type=Path)
    agree = commands.add_parser("agreement")
    for name in ("first", "second", "output"):
        agree.add_argument(f"--{name}", required=True, type=Path)
    export = commands.add_parser("export-packet")
    export.add_argument("--packet", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--judge", required=True, choices=["external"])
    export.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    try:
        if args.command == "make-pairs":
            result = make_pairs(args.index, args.contexts, args.packet, args.key, args.workspace, args.seed)
        elif args.command == "judge-packet":
            result = judge_packet(args.packet, args.output, args.judge_id, args.family, args.instance, args.swap,
                                  {args.pair_id})
        elif args.command == "fit":
            result = fit(args.key, args.results, args.seed, args.ridge)
            if args.output.exists():
                raise ValueError("Refuse to overwrite an analysis result")
            write_json(args.output, result)
        elif args.command == "baselines":
            if args.output.exists():
                raise ValueError("Refuse to overwrite a baseline analysis")
            result = baselines(args.key, args.results, args.features)
            write_json(args.output, result)
        elif args.command == "agreement":
            result = agreement(args.first, args.second)
            if args.output.exists():
                raise ValueError("Refuse to overwrite an agreement result")
            write_json(args.output, result)
        else:
            result = export_packet(args.packet, args.output, args.judge, args.seed)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc), "review_run": False}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
