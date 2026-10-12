"""Run a small numerical and MCP contract on the actual operating system.

Prepare the bundle's locked environment first. This script does not install
dependencies, change product code, or certify other hosts or mathematical tools.
It retains partial records on failure and reaps every process it starts.
"""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import platform
import queue
import signal
import subprocess
import sys
import threading
import time


LP = {"c": [3, 2], "A_ub": [[1, 1], [1, 0]], "b_ub": [4, 2], "maximize": True}
MODEL = '''import argparse
import json
from pathlib import Path
from modeling.optimize import solve_lp

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = solve_lp([3, 2], A_ub=[[1, 1], [1, 0]], b_ub=[4, 2], maximize=True)
if not result["success"]:
    raise ValueError("The small LP did not solve")
args.output.mkdir(exist_ok=True)
(args.output / "results.json").write_text(json.dumps({
    "objective": result["objective"], "x": result["x"], "solver": result,
    "scope": "Original continuous LP runtime contract only",
}, allow_nan=False), encoding="utf-8")
'''
VALIDATOR = '''import argparse
from fractions import Fraction
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--results", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = json.loads(args.results.read_text(encoding="utf-8"))
x, y = [Fraction(str(value)) for value in result["x"]]
value = Fraction(str(result["objective"]))
checks = [
    {"name": "exact primal feasibility", "passed": x >= 0 and y >= 0 and x + y <= 4 and x <= 2,
     "independent": True, "evidence": f"x={x}, y={y}; x+y={x+y}<=4, x<=2"},
    {"name": "independent exact global upper bound", "passed": 3*x + 2*y == value == 10,
     "independent": True,
     "evidence": "For every feasible continuous point, 3x+2y=2(x+y)+x<=2*4+2=10; (2,2) attains10. No solver/model imported."},
]
args.output.write_text(json.dumps(checks, allow_nan=False), encoding="utf-8")
raise SystemExit(0 if all(check["passed"] for check in checks) else 1)
'''


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def process_options():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def kill_and_reap(process):
    """Kill the process group/tree on timeout; always wait for the direct child."""
    if process.poll() is None:
        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=5, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
    return process.wait(timeout=5)


class Contract:
    def __init__(self, bundle, work, receipt):
        self.bundle = bundle.absolute()
        self.work = work.absolute()
        self.receipt = receipt.absolute()
        self.partial = self.receipt.with_suffix(".partial.json")
        self.cwd = self.work / "Unrelated working directory"
        self.workspace = self.work / "User model workspace 研究"
        self.environment = os.environ.copy()
        self.environment.pop("PYTHONPATH", None)
        self.started = time.monotonic()
        self.record = {
            "started_utc": timestamp(), "status": "running", "sys_platform": sys.platform,
            "platform": platform.platform(), "python": sys.version,
            "bundle": str(self.bundle), "work": str(self.work), "cwd": str(self.cwd),
            "source_sha256": {},
            "contract_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "dependency_installation_performed": False,
            "commands": [], "MCP": {"messages": []},
            "scope": "Actual recorded OS only; tiny LP/pipeline/stdio and three professional arithmetic checks, not all tools, sampling validity or desktop-host installation.",
        }
        self.save()

    def bind_source(self):
        files = ["pyproject.toml", "uv.lock", "scripts/pipeline.py", "scripts/mcp_server.py",
                 "scripts/bounded_execution.py", "modeling/optimize.py", "modeling/schema_contracts.py",
                 "modeling/data_analysis.py", "modeling/inference.py", "modeling/regression.py", "scripts/audit_data.py"]
        for name in files:
            self.record["source_sha256"][name] = hashlib.sha256((self.bundle / name).read_bytes()).hexdigest()
        self.save()

    def save(self):
        self.record["elapsed_s"] = time.monotonic() - self.started
        write_json(self.partial, self.record)

    def command(self, label, arguments, timeout=45):
        item = {"label": label, "argv": arguments, "cwd": str(self.cwd),
                "started_utc": timestamp(), "status": "running"}
        self.record["commands"].append(item)
        self.save()
        process = None
        try:
            process = subprocess.Popen(arguments, cwd=self.cwd, env=self.environment,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, **process_options())
            stdout, stderr = process.communicate(timeout=timeout)
            item.update(returncode=process.returncode, stdout=stdout, stderr=stderr)
            if process.returncode != 0:
                raise RuntimeError(f"{label} exited with {process.returncode}: {stderr[-2000:]}")
            item["status"] = "passed"
            return stdout
        except Exception as error:
            item.update(status="failed", error_type=type(error).__name__, error=str(error))
            if process is not None:
                kill_and_reap(process)
                stdout, stderr = process.communicate(timeout=5)
                item.update(returncode=process.returncode, stdout=stdout, stderr=stderr)
            raise
        finally:
            if process is not None and process.poll() is None:
                kill_and_reap(process)
            item["process_reaped"] = process is None or process.poll() is not None
            item["ended_utc"] = timestamp()
            self.save()

    def uv(self, option):
        return ["uv", "run", "--locked", "--no-sync", "--offline", option,
                str(self.bundle), "python"]

    def pipeline(self):
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
        problem = self.workspace / "Original small LP problem.md"
        problem.write_text("Maximize 3x+2y subject to x+y<=4, x<=2, x>=0, y>=0. "
                           "Find a continuous optimum with an independent exact upper bound. "
                           "This is an original tiny runtime contract, not a contest problem.\n",
                           encoding="utf-8")
        project = self.uv("--project") + [str(self.bundle / "scripts/pipeline.py")]
        directory = self.uv("--directory") + ["-m", "scripts.pipeline"]
        workspace = ["--workspace", str(self.workspace)]
        intake = json.loads(self.command("project_absolute_script_init", project + workspace + [
            "init", "--name", "lp-contract", "--problem", str(problem)]))
        case = Path(intake["case"])
        (case / "code/model.py").write_text(MODEL, encoding="utf-8")
        (case / "code/validate.py").write_text(VALIDATOR, encoding="utf-8")
        write_json(case / "planning/requirements.json", {"requirements": [{
            "id": "R1", "question": "What is the continuous LP optimum?", "unit": "objective units",
            "result_pointer": "/objective", "checks": ["exact primal feasibility", "independent exact global upper bound"],
        }]})
        self.command("directory_module_run", directory + workspace + [
            "run", "--case", str(case), "--timeout", "30"])
        status = json.loads(self.command("project_absolute_script_status", project + workspace + [
            "status", "--case", str(case)]))
        if not status["runs"][-1]["usable_automatic_evidence"]:
            raise ValueError("The actual pipeline run is stale or failed")
        evidence = json.loads(self.command("directory_module_evidence", directory + workspace + [
            "evidence", "--case", str(case)]))
        if evidence["status"] != "evidence-linked" or evidence["covered"] != 1 or evidence["paper_ready"]:
            raise ValueError("Pipeline evidence did not preserve its limited meaning")
        self.record.update(case=str(case), pipeline_status=status, pipeline_evidence=evidence)
        self.save()

    def mcp(self):
        with MCPClient(self) as client:
            initialized = client.request(1, "initialize", {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "actual-os-runtime-contract", "version": "1"},
            })
            client.notify("notifications/initialized")
            tools = client.request(2, "tools/list")["result"]["tools"]
            if "solve_lp" not in {tool["name"] for tool in tools}:
                raise ValueError("The actual MCP service does not provide solve_lp")
            first = client.request(3, "tools/call", {"name": "solve_lp", "arguments": LP})
            check_lp(first)
            bad = client.request(4, "tools/call", {"name": "solve_lp", "arguments": {"c": ["bad"]}})
            if bad["result"].get("isError") is not True:
                raise ValueError("Invalid LP input was not rejected")
            if client.request(5, "ping").get("result") != {}:
                raise ValueError("Ping did not recover after the invalid request")
            check_lp(client.request(6, "tools/call", {"name": "solve_lp", "arguments": LP}))
            def call(identity, name, arguments):
                reply = client.request(identity, "tools/call", {"name": name, "arguments": arguments})
                if reply["result"].get("isError"):
                    raise ValueError(f"Professional smoke {name} returned an error")
                return json.loads(reply["result"]["content"][0]["text"])
            adjusted = call(7, "adjust_pvalues", {
                "pvalues": [.01, .04, .03, .2], "hypothesis_ids": ["h1", "h2", "h3", "h4"],
                "method": "holm", "family_id": "runtime-four-tests"})
            expected = [Fraction(1, 25), Fraction(9, 100), Fraction(9, 100), Fraction(1, 5)]
            if (adjusted["family_size"] != 4 or len(adjusted["hypotheses"]) != 4 or
                    any(abs(row["adjusted_p_value"] - float(value)) > 1e-14
                        for row, value in zip(adjusted["hypotheses"], expected))):
                raise ValueError("Holm smoke disagrees with exact four-test arithmetic")
            joined = call(8, "audit_join", {"left": [{"id": 1}, {"id": 1}, {"id": 2}, {"id": 3}],
                                          "right": [{"id": 1}, {"id": 2}], "on": "id",
                                          "how": "left", "relationship": "many_to_one"})
            if joined["output_rows"] != 4 or joined["left"]["matched_input_rows"] != 3:
                raise ValueError("Join smoke disagrees with enumerated key counts")
            clustered = call(9, "ols_report", {
                "X": [[1]] * 12, "y": [value for value in range(1, 7) for _ in range(2)],
                "add_constant": False, "covariance": "cluster",
                "groups": [str(value) for value in range(1, 7) for _ in range(2)]})
            if (abs(clustered["coefficients"][0]["estimate"] - 3.5) > 1e-12 or
                    abs(clustered["covariance"]["matrix"][0][0] - float(Fraction(7, 12))) > 1e-12 or
                    clustered["covariance"]["df_inference"] != 5):
                raise ValueError("Cluster smoke disagrees with the six-group mean variance 7/12")
            self.record["MCP"].update(server_info=initialized["result"]["serverInfo"],
                                      tools=len(tools), LP_optimum=10,
                                      professional_arithmetic={"holm": True, "join": True, "cluster_mean_variance": "7/12"},
                                      invalid_then_ping_and_LP_recovery=True)
            self.save()


def check_lp(reply):
    if reply["result"].get("isError"):
        raise ValueError("The valid MCP LP returned an error")
    result = json.loads(reply["result"]["content"][0]["text"])
    x, y = [Fraction(str(value)) for value in result["x"]]
    value = Fraction(str(result["objective"]))
    if not (x >= 0 and y >= 0 and x + y <= 4 and x <= 2 and 3*x + 2*y == value == 10):
        raise ValueError("The MCP LP did not attain the independent exact global bound of 10")


class MCPClient:
    def __init__(self, contract):
        self.contract = contract
        self.queue = queue.Queue()
        self.stderr = bytearray()
        self.stderr_truncated = False
        self.process = None
        self.threads = []

    def __enter__(self):
        arguments = self.contract.uv("--directory") + ["-m", "scripts.mcp_server"]
        self.contract.record["MCP"].update(argv=arguments, cwd=str(self.contract.cwd))
        self.contract.save()
        self.process = subprocess.Popen(arguments, cwd=self.contract.cwd, env=self.contract.environment,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        **process_options())
        try:
            self.threads = [threading.Thread(target=self.read_stdout, daemon=True),
                            threading.Thread(target=self.read_stderr, daemon=True)]
            for thread in self.threads:
                thread.start()
        except Exception:
            kill_and_reap(self.process)
            self.contract.record["MCP"].update(server_exit_code=self.process.returncode, server_reaped=True)
            self.contract.save()
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                stream.close()
            raise
        return self

    def read_stdout(self):
        try:
            while line := self.process.stdout.readline(1024 * 1024 + 1):
                if len(line) > 1024 * 1024:
                    raise ValueError("MCP reply exceeds the contract's 1 MiB limit")
                self.queue.put(line)
            self.queue.put(EOFError("MCP server closed stdout"))
        except Exception as error:
            self.queue.put(error)

    def read_stderr(self):
        while chunk := self.process.stderr.read(4096):
            remaining = max(0, 65536 - len(self.stderr))
            self.stderr.extend(chunk[:remaining])
            self.stderr_truncated |= len(chunk) > remaining

    def send(self, message):
        self.process.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def notify(self, method):
        self.send({"jsonrpc": "2.0", "method": method})

    def request(self, identifier, method, params=None):
        message = {"jsonrpc": "2.0", "id": identifier, "method": method}
        if params is not None:
            message["params"] = params
        item = {"request": message, "status": "pending", "started_utc": timestamp()}
        self.contract.record["MCP"]["messages"].append(item)
        self.contract.save()
        self.send(message)
        try:
            response = self.queue.get(timeout=30)
        except queue.Empty as error:
            raise TimeoutError(f"MCP {method} exceeded 30 seconds") from error
        if isinstance(response, Exception):
            raise response
        reply = json.loads(response.decode("utf-8"))
        item.update(response=reply, ended_utc=timestamp(), status="received")
        self.contract.save()
        if reply.get("id") != identifier or "error" in reply:
            raise ValueError(f"Unexpected MCP reply to {method}: {reply}")
        return reply

    def __exit__(self, error_type, error, traceback):
        try:
            if error is None:
                self.process.stdin.close()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    kill_and_reap(self.process)
            else:
                kill_and_reap(self.process)
        finally:
            if self.process.poll() is None:
                kill_and_reap(self.process)
            for thread in self.threads:
                thread.join(timeout=1)
            self.contract.record["MCP"].update(server_exit_code=self.process.returncode,
                server_reaped=self.process.poll() is not None,
                server_stderr=self.stderr.decode("utf-8", errors="replace"),
                stderr_truncated=self.stderr_truncated)
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
            self.contract.save()
        if error is None and self.process.returncode != 0:
            raise RuntimeError(f"MCP server exited with {self.process.returncode}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True, help="Fresh directory receiving actual case evidence")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    contract = Contract(args.bundle, args.work, args.receipt)
    try:
        contract.bind_source()
        contract.pipeline()
        contract.mcp()
        contract.record.update(status="passed", completed_utc=timestamp())
    except Exception as error:
        contract.record.update(status="failed", completed_utc=timestamp(),
                               error_type=type(error).__name__, error=str(error))
        raise
    finally:
        contract.save()
        write_json(contract.receipt, contract.record)
    print(json.dumps({"status": contract.record["status"], "platform": contract.record["platform"],
                      "MCP_tools": contract.record["MCP"]["tools"], "LP_optimum": 10,
                      "elapsed_s": contract.record["elapsed_s"]}))


if __name__ == "__main__":
    main()
