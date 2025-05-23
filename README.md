# AutomatedSleepEMAs

Documentation for 2025 IEEE NER submission "Automated Sleep-Deviation Triggered Ecological Momentary Assessments for Contextualizing Free-Living Neural and Behavioral Data in OCD DBS".
This provides an example of how to implement a sleep-deviation triggered EMA using Oura Ring and Qualtrics APIs.

### Contents
AutomatedSleepEMAs/
├─ sleep_ema_demo.py          # single-file demo pipeline
├─ example_oura_sleep.json    # anonymised sample data
├─ config.json        # template for real tokens / IDs

sleep_ema_demo.py does the following:
	1.	Pull Oura Ring sleep data
	•	If a real Oura token is present → downloads the last 8 nights.
	•	Otherwise → loads example_oura_sleep.json.
	2.	Apply the rule
Trigger = (|last–baseline| > 25 %).
	3.	Send (or print) a Qualtrics survey invite
• Email + SMS are posted if valid Qualtrics credentials are supplied.
• If any credential equals "xxx" or you pass --dry, it only prints the payload.

Only requirement is 'pip install requests'.

Use '--dry' argument if you are not defining your own Oura and Qualtrics ID's in 'config.json'.
'python sleep_ema_demo.py --dry'

Edit 'config.json' with Oura Ring tokens and Qualtrics IDs to trigger EMAs. Make sure