# Description
This module contains an extension of simple-salesforce Salesforce class (https://github.com/simple-salesforce/) and utility functions that help you manage files and reports in large scales.

# Before Starting
This module's main data structre is a "list of dict" e.g. "lod": [{'a':1},{'a':2}], which is the accepted format by salesforce. 

# Setup
On parent directory:
```
git clone git@github.com:stone-payments/maluforce
pip install -e maluforce
```
After successfull installation, don't delete the folder.

# Usage
```
from maluforce import Maluforce
sf = Maluforce(username='', password='', security_token='', sandbox=False)
```
Refeer to https://github.com/simple-salesforce/ for more instructions.

# Report Utilities
```
from maluforce import adjust_report,lod_rename,to_lod
```

# Files Utilities
```
from maluforce import save_lod_files,read_lod_file,read_lod_files
```
