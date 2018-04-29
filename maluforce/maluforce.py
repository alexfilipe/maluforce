import pandas as pd
import numpy as np
import os
import re
import timeit
import copy
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import (SalesforceMalformedRequest)

from maluforce.utils.validators import (path_formatter)
from maluforce.utils.reportutils import (adjust_report, lod_rename, to_lod, decodeSFObject, decodeSFresponse)
from maluforce.utils.fileutils import ( 
    num_char, split_lod, split_lod_by_char, split_lod_by_item, save_lod_files, read_lod_file, read_lod_files,SF_BULK_MAX_CHAR,SF_BULK_MAX_ITEM
)


class Maluforce(Salesforce):
    
    def lod_to_saleforce(self, obj, method, data, step=5000):
        """
            [input]
            * obj - str, Salesforce sObject
            * method - str, ('insert'|'delete'|'upsert'|'update'|'undelete')
            * data - lod
            * step - 
            [output]
            * lod
        """
        assert method in [
            "insert", "delete", "upsert", "update", "undelete"
        ], """invalid method"""
        assert (
            (type(data) is list) and (True if len(data) == 0 else type(data[0]) is dict)
        ), """wrong data format"""
        assert type(step) in [type(None), int]
        step = min(10000, step)
        completeReport = []
        outlist = []
        for i in range(0, len(data), step):
            output = eval("self.bulk.{}.{}".format(obj, method))(data[i:i + step])
            outlist.extend(output)
        for i in range(0, len(outlist)):
            completeReport.append({**outlist[i], **data[i]})
        return completeReport


    def query_salesforce(self, obj, query, api="bulk"):
        """
            [input]
            * obj - (str), sObject name
            * query - query
            * api - ['bulk','rest']
            [output]
            * lod
        """
        assert type(obj) is str, "{} : obj must be a str".format("query_salesforce")
        assert type(query) is str, "{} : query must be a str".format("query_salesforce")
        assert api in ["bulk", "rest"], "{} : api options are: bulk, rest".format(
            "query_salesforce"
        )
        out = []
        resp = []
        if api == "bulk":
            try:
                resp = eval("self.bulk." + obj).query(query)
            except (IndexError, SalesforceMalformedRequest) as e:
                print("{}: {} invalid request: {}".format("query_salesforce", api, e))
                print("Trying with rest api...")
                api = "rest"
            if len(resp) > 0:
                out = decodeSFresponse(resp)
        if api == "rest":
            try:
                resp = self.query_all(query)
            except (IndexError, SalesforceMalformedRequest) as e:
                print("{}: {} invalid request: {}".format("query_salesforce", api, e))
                print(
                    "Trying limiting the response to 2000 registers..."
                )
                try:
                    resp = self.query(query)
                except (IndexError, SalesforceMalformedRequest) as e:
                    print("{}: {} invalid request: {}".format("query_salesforce", api, e))
            if len(resp) > 0:
                out = decodeSFresponse(resp)
        return out


    def to_salesforce(
        self,
        lod_list,
        method,
        obj,
        path=None,
        key_map=None,
        drop=False,
        step=5000,
        suf="",
        pref="",
        start_index=0,
    ):
        """
            Sends all lods parsed to Salesforce. They must be of the same sObject and respect Salesforce's bulk api limits.
            [input]
            * lod_list - (list) of lods to be sent
            * method - ('insert'|'delete'|'upsert'|'update'|'undelete')
            * obj - (str), sObject
            * key_map - (dict), used to rename current keys to Salesforce's field api names.
            * path - (str), path to save report files
            * drop - (bool), True to drop keys that are not in key_map
            * step - (int), batch size
            * suf - (str), added to the end of the file name
            * pref - (str), added to the start of the file name
            * start_index - (int), index of the first file to be saved.
            [output]
            * (list), list of lods report
        """
        path = path_formatter(path)
        files = []
        lod_report_final = []
        for lod in lod_list:
            files.extend(lod_rename(lod, key_map, drop=drop))
        count = start_index
        for lod in files:
            if len(lod) > 0:
                filename = """{}_{}_report_{}_{}""".format(pref, method, obj, suf)
                start_time = timeit.default_timer()
                print(
                    "{} #{} of {} {} started at {}, saved on {}:".format(
                        method, count, len(lod), obj, timeit.time.strftime("%H:%M:%S", timeit.time.localtime()), filename
                    )
                )
                # sends to salesforce
                report = self.lod_to_saleforce(obj, method, lod, step)
                # format response
                df_report = adjust_report(report)
                df_report = df_report.assign(taskid=df_report["id"])
                df_report.drop(columns=["id"], inplace=True)
                # reports
                lod_report = df_report.to_dict(orient="records")
                save_lod_files([lod_report], path, filename, start_index=count)
                lod_report_final.append(lod_report)
                err = df_report[~df_report.success].shape[0]
                suc = df_report[df_report.success].shape[0]
                print("\terrors:", err)
                print("\tsuccess:", suc)
                if err > 0:
                    try:
                        df_report.to_excel("{}{}_{}.xlsx".format(path, filename, count))
                    except:
                        pass
                    print("\tmessages: ", set(df_report.message))
                m, s = divmod(timeit.default_timer() - start_time, 60)
                print("\texecution time: {:1.0f}min {:2.0f}s".format(m, s))
                count += 1
            else:
                print("One of the lods passed had length zero. Skipped...")
        return lod_report_final

    def simple_describe(self, path, filename, nomes_objetos=None):
        """
            [input]
            * path - caminho para salvar o arquivo
            * filename - nome do arquivo a ser salvo
            * nomes_objetos - lista com o nome dos objetos> None para consultar todos
            [output]
        """
        if path[-1] != "/":
            raise ValueError(
                "{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format(
                    "simple_describe"
                )
            )

        quero = {
            "createable",
            "custom",
            "calculated",
            "label",
            "name",
            "permissionable",
            "queryable",
            "retrieveable",
            "searchable",
            "triggerable",
            "updateable",
            "autoNumber",
            "defaultedOnCreate",
            "nillable",
            "referenceTo",
            "type",
        }
        simple_describe_objetos = pd.DataFrame()

        describe_sf = self.describe()
        objects = adjust_report(describe_sf["sobjects"])
        print("Max Batch Size: {}".format(describe_sf["maxBatchSize"]))
        print("Encoding: {}".format(describe_sf["encoding"]))

        if nomes_objetos == None:
            nomes_objetos = list(set(objects.name))

        for obj in nomes_objetos:
            describe_obj = eval("self.{}.describe()".format(obj))
            describe_campos_completo = pd.DataFrame(describe_obj["fields"])
            describe_campos_reduzido = describe_campos_completo[
                list(quero & set(describe_campos_completo.columns))
            ].copy()
            describe_campos_reduzido["object"] = obj
            simple_describe_objetos = pd.concat(
                [describe_campos_reduzido, simple_describe_objetos], axis=0
            )
        simple_describe_objetos.to_excel("{}{}.xlsx".format(path, filename), index=False)
        lod_simple_describe_objetos = simple_describe_objetos.to_dict(orient="records")
        return lod_simple_describe_objetos


# fazer funcionar com timestamp

# def select_all_from(self,obj,query,api='bulk'):

# falta fazer
# consulta org