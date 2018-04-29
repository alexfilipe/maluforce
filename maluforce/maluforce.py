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
from maluforce.utils.fileutils import (num_char, split_lod, split_lod_by_char, split_lod_by_item, save_lod_files, read_lod_file, read_lod_files)


class Maluforce(Salesforce):
    
    # metodos para a classe simple_salesforce.Salesforce
    def lod_to_saleforce(self, obj, method, data, step=5000):
        """
            [input]
            * obj -- objeto do salesforce
            * method - ['insert', 'delete','upsert','update','undelete']
            * data -- lista de dicionario com os dados
            * step -- tamanho dos batchs
            [output]
            * lista de diconarios
        """

        assert method in [
            "insert", "delete", "upsert", "update", "undelete"
        ], """{} : Operacao de query invalida""".format(
            "to_saleforce"
        )
        assert (
            (type(data) is list) and (True if len(data) == 0 else type(data[0]) is dict)
        ), """{} : Dado nao suportado""".format(
            "to_saleforce"
        )
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
            * obj - nome do objeto do salesforce
            * query - query
            * api - ['bulk','rest']
            [output]
            * lista de dicionario
        """
        assert type(obj) is str, "{} : obj deve ser tipo str".format("query_salesforce")
        assert type(query) is str, "{} : query deve ser tipo str".format("query_salesforce")
        assert api in ["bulk", "rest"], "{} : api deve ser bulk ou rest".format(
            "query_salesforce"
        )

        out = []
        resp = []
        if api == "bulk":
            try:
                resp = eval("self.bulk." + obj).query(query)
            except (IndexError, SalesforceMalformedRequest) as e:
                print("{}: {} request invalida: {}".format("query_salesforce", api, e))
                print("Tentando com rest")
                api = "rest"
            if len(resp) > 0:
                out = decodeSFresponse(resp)
        if api == "rest":
            try:
                resp = self.query_all(query)
            except (IndexError, SalesforceMalformedRequest) as e:
                print("{}: {} request invalida: {}".format("query_salesforce", api, e))
                print(
                    "Tentando sem query_all(), a resposta pode conter no maximo 2000 registros!"
                )
                try:
                    resp = self.query(query)
                except (IndexError, SalesforceMalformedRequest) as e:
                    print("{}: {} request invalida: {}".format("query_salesforce", api, e))
            if len(resp) > 0:
                out = decodeSFresponse(resp)
        return out


    def to_salesforce(
        self,
        lista,
        method,
        obj,
        path,
        depara=None,
        drop=False,
        step=5000,
        sufixo="",
        prefixo="",
        start_index=0,
    ):
        """
            Envia uma lista de list_of_dict para o Salesforce, e salva o resultado em arquivos.
            [input]
            * lista - lista com lista de dicionarios a serem enviadas
            * method - ['insert', 'delete','upsert','update','undelete']
            * obj - objeto do salesforce
            * depara - dicionario pare renomear as colunas a serem enviadas
            * path - caminho da pasta para salvar os arquivos
            * drop - True para retornar apenas as colunas do depara, False para retornar todas
            * step - tamanho dos batchs
            * sufixo - a ser adicinado ao nome do arquivo
            * prefixo - a ser adicinado ao nome do arquivo
            * start_index - a ser adicinado ao nome do arquivo
            [output]
            * lista com lista de dicionarios que foram enviados + report
            * lista com dataframes que foram enviados + report
        """

        if path[-1] != "/":
            raise ValueError(
                "{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format(
                    "to_salesforce"
                )
            )

        arquivos = []
        resultados = []
        resultados_df = []
        for item in lista:
            lod = lod_rename(item, depara, drop=drop)
            arquivos.extend(lod)

        count = start_index
        for arquivo in arquivos:
            if len(arquivo) > 0:
                filename = """{}_{}_report_{}_{}""".format(prefixo, method, obj, sufixo)

                start_time = timeit.default_timer()
                print(
                    "{} #{} de {} {} iniciado - {}:".format(
                        method, count, len(arquivo), obj, filename
                    )
                )
                report = self.list_of_dict_to_saleforce(obj, method, arquivo, step)

                df_report = adjust_report(report)
                df_report["taskid"] = df_report["id"]
                df_report.drop(columns=["id"], inplace=True)

                tmp = df_report.to_dict(orient="records")
                save_lod_files([tmp], path, filename, start_index=count)
                resultados.extend([tmp])
                resultados_df.extend([df_report])

                err = df_report[~df_report.success].shape[0]
                suc = df_report[df_report.success].shape[0]

                print("\terros:", err)
                print("\tsucessos:", suc)
                if err > 0:
                    try:
                        df_report.to_excel("{}{}_{}.xlsx".format(path, filename, count))
                    except:
                        pass
                    print("\tmensagem: ", set(df_report.message))
                m, s = divmod(timeit.default_timer() - start_time, 60)
                print("\ttempo decorrido: {:1.0f}min {:2.0f}s".format(m, s))
                count += 1
        return resultados


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