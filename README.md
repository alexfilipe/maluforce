# Description
This module contains an extension of simple-salesforce Salesforce class (https://github.com/simple-salesforce/) and utility functions that help you manage files and reports in large scales.

# Before Starting
This module's main data structre is a "list of dict" e.g. "lod": [{'a':1},{'a':2}], which is the accepted format by salesforce. 

# Setup
For edit mode installation, n parent directory:
```
git clone git@github.com:stone-payments/maluforce
pip3 install -e maluforce
```
For global installation:
```
pip3 install git+https://github.com/stone-payments/maluforce.git
```
For ubuntu: 
```
python3 -m pip install git+ssh://git@github.com/stone-payments/maluforce.git --user
```
For a project:
- clone the git repo
- delete .git and .gitgnore files
- install with `pipenv install -e maluforce`
# Usage
```
from maluforce import Maluforce
sf = Maluforce(username='', password='', security_token='', sandbox=False)
```
Refeer to https://github.com/simple-salesforce/ for more instructions.

You can also run
```
from maluforce import *
```
# Report Utilities
```
from maluforce import adjust_report,lod_rename,to_lod
```

# Files Utilities
```
from maluforce import save_lod_files,read_lod_file,read_lod_files
```
