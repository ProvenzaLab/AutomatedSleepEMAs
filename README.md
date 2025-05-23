# AutomatedSleepEMAs

Documentation for 2025 IEEE NER submission  
“Automated Sleep-Deviation Triggered Ecological Momentary Assessments for Contextualizing Free-Living Neural and Behavioral Data in OCD DBS.”

This repo is a minimal example of a **sleep-deviation-triggered EMA** that uses the **Oura Ring** and **Qualtrics** APIs.

⸻

### Basic Logic

	1.	Pull Oura Ring sleep data

	•	If a real Oura token is present → downloads the last 8 nights.

	•	Otherwise → loads example_oura_sleep.json.

	2.	Apply the rule: Trigger = | last night sleep – average of previous seven days | > 25 %.

	3.	Send (or print) a Qualtrics survey invite

	•	Email and SMS are posted if valid Qualtrics credentials are supplied.

	•	If any credential equals xxx or you pass --dry, it only prints the payload.

⸻

### Requirements

pip install requests


⸻

### Usage

Dry-run mode (no real tokens needed):

python sleep_ema_demo.py --dry

Use the --dry argument if you have not populated your own Oura and Qualtrics IDs in config.json.

To trigger real EMAs, edit config.json with your Oura Ring token and Qualtrics IDs, then run the script without --dry:

python sleep_ema_demo.py

⸻

### Contents

```text
AutomatedSleepEMAs/
├─ sleep_ema_demo.py          # single-file demo pipeline
├─ example_oura_sleep.json    # anonymised sample data
└─ config_example.json        # template for real tokens / IDs
