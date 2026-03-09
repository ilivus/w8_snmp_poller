# SNMP Poller - Ops-grade Python Poller

## About the application

This project is a small SNMP polling tool written in Python.

The program reads a YAML configuration file (`config.yml`) that defines network devices and SNMP OIDs to query. It polls the devices using the Net-SNMP `snmpget` command.

The results are saved as JSON output and the program logs important events such as start, retries, and errors.

Main features:

* YAML based configuration
* logging with INFO, WARNING, and ERROR
* timeout handling and retry on timeout
* time budget per target
* JSON output with results
* exit codes for success or failure

The tool is designed to behave predictably and can be run multiple times safely.

---

## Files

The project contains the following files:

**poller.py**  
Main application that performs the SNMP polling.  
It loads the configuration, runs SNMP queries, and writes the results to a JSON file.

**config.yml**  
Configuration file that defines default settings, SNMP targets, and OIDs to query.

**test_config.py**  
Unit test that verifies the configuration validation function.

**README.md**  
Documentation describing the application and how to run it.

---

## Methods

The program contains a few main functions.

**load_config(filename)**  
Reads the YAML configuration file and converts it to a Python dictionary.

Input: path to the configuration file  
Output: configuration dictionary

---

**validate_config(config)**  
Checks that the configuration file contains the required fields.

It verifies that the config file has `defaults`, `targets`, and that each target has `name`, `ip`, and `community`.

Input: configuration dictionary  
Output: none (raises an error if the config is invalid)

---

**get_snmp(ip, community, oid, timeout_s, retries)**  
Runs the SNMP command `snmpget` to get data from a network device.

If the request times out, the function will retry according to the retry value.

Input:

* device IP address
* SNMP community
* OID to query
* timeout value
* retry count

Output:

* SNMP response
* error message
* `timeout` if the request fails

---

**main()**  
Controls the whole program.

It loads the configuration, validates it, polls all targets and writes the results to the JSON output file.

Input: CLI arguments (`--config`, `--out`, `--log-level`)  
Output: JSON result file and program exit code

### Method dependencies

Program flow:

```text
main()
 ├── load_config()
 ├── validate_config()
 └── get_snmp()
```

`main()` coordinates the program and calls the other functions.

---

## Installation

The program was tested on Linux in a VirtualBox environment.

Install required packages:

```bash
sudo apt-get update
sudo apt-get install -y snmp python3 python3-venv
```

Create a virtual environment and install the Python dependency:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pyyaml
```

---

## Running

Run the program using:

```bash
python3 poller.py --config config.yml --out out.json --log-level INFO
```

Write JSON output to stdout instead of a file:

```bash
python3 poller.py --config config.yml --out - --log-level INFO
```

Show only warnings and errors:

```bash
python3 poller.py --config config.yml --out out.json --log-level WARNING
```

Show only errors:

```bash
python3 poller.py --config config.yml --out out.json --log-level ERROR
```

Arguments:

`--config`  
Path to the YAML configuration file.

`--out`  
Name of the JSON file where the results will be saved.  
Use `-` to write the JSON output to stdout.

`--log-level`  
Controls which log messages are shown in the terminal.

* `INFO` shows INFO, WARNING, and ERROR
* `WARNING` shows WARNING and ERROR
* `ERROR` shows only ERROR

The program polls the devices defined in `config.yml` and saves the results to the selected output destination.

### Exit codes

`0` – all targets successful  
`1` – partial success, at least one target returned data but some OIDs failed  
`2` – total failure or configuration error