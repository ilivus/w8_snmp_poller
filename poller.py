import yaml        # used to read the config.yml file
import subprocess  # used to run the snmpget command
import time        # used to measure runtime
import json        # used to write the result to a JSON file
import sys         # used for program exit codes
import logging     # used for log messages
import argparse    # used to read CLI arguments

# Reads the YAML config file and converts it to a Python dictionary
# Input: filename (path to config.yml)
# Output: config dictionary with defaults and targets
def load_config(filename):

    # open the config file
    with open(filename) as f:

        # convert YAML to Python dictionary
        config = yaml.safe_load(f)

    # return the config dictionary
    return config

# Checks that the config file contains the required fields
# If something important is missing the program stops
# Input: config dictionary
# Output: none (raises error if config is invalid)
def validate_config(config):

    # config must contain defaults
    if "defaults" not in config:
        raise ValueError("Missing defaults")

    # config must contain targets
    if "targets" not in config:
        raise ValueError("Missing targets")

    # targets must be a list with at least one entry
    if not isinstance(config["targets"], list) or len(config["targets"]) == 0:
        raise ValueError("targets must be a non-empty list")

    defaults = config["defaults"]

    # check that timeout exists
    if "timeout_s" not in defaults:
        raise ValueError("Missing defaults.timeout_s")

    # timeout must be numeric
    if not isinstance(defaults["timeout_s"], (int, float)):
        raise ValueError("timeout_s must be numeric")

    # check that target time budget exists
    if "target_budget_s" not in defaults:
        raise ValueError("Missing defaults.target_budget_s")

    # check that OIDs exist
    if "oids" not in defaults:
        raise ValueError("Missing defaults.oids")

    # retries should be numeric if present
    if "retries" in defaults and not isinstance(defaults["retries"], int):
        raise ValueError("retries must be an integer")

    # validate each target entry
    for target in config["targets"]:

        # every target must have a name
        if "name" not in target:
            raise ValueError("Target missing name")

        # every target must have an IP address
        if "ip" not in target:
            raise ValueError("Target missing ip")

        # every target must have a community string
        if "community" not in target:
            raise ValueError("Target missing community")

# Runs the snmpget command to retrieve SNMP data from a device
# Input: ip address, community string, oid, timeout
# Output: SNMP response text, error text, or "timeout"
def get_snmp(ip, community, oid, timeout_s, retries):

    # attempt the SNMP request and retry on timeout
    for attempt in range(retries + 1):

        try:

            # run the snmpget command
            result = subprocess.run(
                ["snmpget", "-v2c", "-c", community, ip, oid],
                capture_output=True,
                text=True,
                timeout=timeout_s
            )

            # if successful return the SNMP output
            if result.returncode == 0:
                return result.stdout.strip()

            # otherwise return the error message
            return result.stderr.strip()

        # if the device does not respond in time
        except subprocess.TimeoutExpired:

            if attempt < retries:

                # warning messages show timeout and retry number
                logging.warning("Timeout on %s %s, retry %d/%d", ip, oid, attempt + 1, retries + 1)

            else:

                # if all retries fail return timeout
                logging.error("Final timeout on %s %s after %ss", ip, oid, timeout_s)
                return "timeout"

# Main function that runs the whole poller
# It loads the config, polls all targets, and saves the result
def main():

    # define CLI arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)

    # extra argument so the user can choose which log level to show
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["INFO", "WARNING", "ERROR"]
    )

    args = parser.parse_args()

    # configure logging after reading CLI arguments
    # asctime adds date and time to each log line
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s"
    )

    # load and validate configuration
    try:
        config = load_config(args.config)
        validate_config(config)

    except Exception as e:

        logging.error("Config error: %s", e)
        sys.exit(2)

    # read default values from config
    timeout_s = config["defaults"]["timeout_s"]
    budget_s = config["defaults"]["target_budget_s"]
    retries = config["defaults"].get("retries", 1)

    results = []

    # short info log for normal program start
    logging.info("Starting poller, %d targets", len(config["targets"]))

    # start time for total runtime
    run_start = time.time()

    # loop through all targets in the config
    for target in config["targets"]:

        logging.info("Polling %s (%s)", target["name"], target["ip"])

        start = time.time()

        # structure where results for this target are stored
        target_result = {
            "name": target["name"],
            "ip": target["ip"],
            "results": {}
        }

        ok_count = 0
        fail_count = 0

        # use target OIDs if defined, otherwise use default OIDs
        oids = target.get("oids", config["defaults"]["oids"])

        # loop through each OID
        for oid in oids:

            # stop if time budget for this target is exceeded
            if time.time() - start > budget_s:

                # warning log for budget problems
                logging.warning("Time budget exceeded for %s (%s) after %ss", target["name"], target["ip"], budget_s)
                break

            # run SNMP query
            output = get_snmp(
                target["ip"],
                target["community"],
                oid,
                timeout_s,
                retries
            )

            # store result
            target_result["results"][oid] = output

            # count successful and failed OIDs
            # keep the check simple: timeout or clear error text means failure
            if output == "timeout" or "ERROR" in output.upper() or "TIMEOUT" in output.upper():

                fail_count += 1
                logging.error("Failed %s (%s) %s: %s", target["name"], target["ip"], oid, output)

            else:

                ok_count += 1

        # determine the status for the target
        if fail_count == 0:
            status = "ok"
        elif ok_count == 0:
            status = "failed"
        else:
            status = "partial"

        target_result["status"] = status
        target_result["ok_count"] = ok_count
        target_result["fail_count"] = fail_count

        # runtime for this target
        target_result["runtime"] = time.time() - start

        results.append(target_result)

    # build final JSON output
    output = {
        "run": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": args.config,
            "duration": time.time() - run_start
        },
        "targets": results
    }

    # write results to JSON file
    # if --out - is used, print JSON to stdout instead of writing a file
    if args.out == "-":
        json.dump(output, sys.stdout, indent=2)
        print()
    else:
        with open(args.out, "w") as f:
            json.dump(output, f, indent=2)

    # only show this when results are written to a file
    if args.out != "-":
        logging.info("Saved results to %s", args.out)

    # determine exit code based on results
    all_ok = True
    any_success = False

    for t in results:

        if t["status"] != "ok":
            all_ok = False

        if t["status"] != "failed":
            any_success = True

    if all_ok:
        sys.exit(0)
    elif any_success:
        sys.exit(1)
    else:
        sys.exit(2)

# start the program
if __name__ == "__main__":
    main()
