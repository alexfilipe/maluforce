## run
%run -i malufy.py

## login
sf = Salesforce(username='', password='', security_token='', sandbox=False)

# Introduction
This module's main data structres are pandas.DataFrame and "list of dict" ie "lod": [{'a':1},{'a':2}]. lod is the accepted format by salesforce. 

# File (Batch) Management
Breaks your lod into smaller lods respecting salesforce´s bulk-api limittations, so that your batch is accepted. 

## Main functions:

```
separa_arquivos()
salva_arquivos()
carrega_arquivos()

``` 
# Pandas.DataFrame custom methods

```
import pandas as pd
df = pd.DataFrame()

df.to_list_of_dict()

```

# simple-salesforce custom methods

```
lod = sf.query_salesforce('account',"select id, recordtype.name, owner.email from account where recordtype.name = 'Default'")

```
Use this for easy file management:
```
lod_res = sf.to_salesforce([lod_req_one,lod_req_two],'update','account','~/Documents/')
``` 
Use this to avoid writing files:
```
lod_res = sf.list_of_dict_to_saleforce('account','insert',lod_req)
```
And this to format salesforce's lod responses into dataframes:
```
 df = adjust_report(lod_res)
```

# Utils

Get a description of salesforce objects:
```
sf.simple_describe()
```

Data validation utils
```
validId()
corrigeCNPJ()
```
