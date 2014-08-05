# ROAR2DOAR

An application for connecting [ROAR](http://roar.eprints.org) to the new [OARR](https://github.com/CottageLabs/oarr)

## Installation

### Process

1. Create a virtual environment for this application
2. Install this application into the virtual environment ("pip install -e .")

## Running

To run this application, simply use

    python roar2doar/importer.py

This will import every record which has never been imported into OARR before, and will udpate any records in OARR which
have been updated in ROAR since the last time this script was run.

It will also copy all historical statistics on the first run, and will add new statistics in subsequent runs.

### Scheduling

Data in ROAR does not change that fast, so recommend to run this no more frequently than once per week.