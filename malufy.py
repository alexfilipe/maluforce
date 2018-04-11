import pandas as pd
import numpy as np
import os
import re
import timeit
import copy
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import (
    SalesforceError,
    SalesforceMoreThanOneRecord,
    SalesforceExpiredSession,
    SalesforceRefusedRequest,
    SalesforceResourceNotFound,
    SalesforceGeneralError,
    SalesforceMalformedRequest,
    SalesforceAuthenticationFailed
)


def main():
    pd.DataFrame.to_unicode = to_unicode
    pd.DataFrame.to_list_of_dict = to_list_of_dict
    Salesforce.to_salesforce = to_salesforce
    Salesforce.list_of_dict_to_saleforce = list_of_dict_to_saleforce
    Salesforce.query_salesforce = query_salesforce
    Salesforce.simple_describe = simple_describe

# funcoes de gerenciamento de arquivos, respeitando os limites do Salesforce
def num_caracteres(lista):
    """
        Retorna o numero de caracteres de uma lista.
    """
    todos_c = ''
    for i in lista:
        todos_c += str(i)
    return len(todos_c)

def quebra_list_num_caracteres(lista, maximo=9000000):
    """
        Quebra uma lista em sublistas. Cada sublista contem, respeita o maximo de caracteres especificado
        [input]
        * lista
        * maximo - maximo numero de caracteres que cada sublista pode ter
        [output]
        * lista com as sublistas
    """
    maximo = min(maximo,10000000)

    num_carac_por_registro = []
    for registro in lista:
        num_carac_por_registro.extend([num_caracteres([registro])])
    num_carac_cumulativo = list(np.cumsum(num_carac_por_registro))

    x = num_carac_cumulativo.copy()
    quebra = []
    ultimo = 0
    for i in range(0, len(x)-1):
        if x[i+1] > maximo:
            # print(x[i+1], x[i],i)
            x[i+1:] = list(np.add(x[i+1:], [-x[i]] * len(x[i+1:])))
            x[:i+1] = [0] * len(x[:i+1])
            quebra.extend([lista[ultimo:i+1]])
            ultimo = i+1
            # print('x depois:',x)
    if ultimo <= len(x):
        quebra.extend([lista[ultimo:len(x)]])
    return quebra

def quebra_num_de_registros(lista,max_registros=10000):
    """
        Quebra uma lista em sublistas respeitando o numero maximo de registros
        [input]
        * lista
        * max_registros
        [output]
        * lista com as sublistas
    """
    max_registros = min(max_registros,10000)
    files = []
    for i in range(0,len(lista),max_registros):
        files.extend([lista[i:i+max_registros]])
    return files

def separa_arquivos(lista,max_registros=10000,max_carac=10000000):
    """
    Separa uma lista de dicionarios em sublistas respeitando os limites passados.
        [input]
        * lista - lista de registros a ser dividida em sublistas
        * max_registros - numero maximo de linhas por sublista
        * max_carac - numero maximo de caracteres por sublista
        [output]
        * lista com as sublistas 
    """
    if type(lista) != list:
        raise ValueError("{}: lista deve ser do tipo list".format('quebra_arquivos'))
    if len(lista) == 0:
        raise ValueError("{}: a lista de lista passada nao tem itens".format('quebra_arquivos'))
    if type(lista[0]) == list:
        raise ValueError("{}: Nao passe uma lista de listas!".format('quebra_arquivos'))
    
    sublistas_finais = []
    sublistas_registros =  quebra_num_de_registros(lista,max_registros=max_registros)
    
    for sublista in sublistas_registros:
        sublistas_finais.extend(quebra_list_num_caracteres(sublista,maximo=max_carac))
    return sublistas_finais

def salva_arquivos(arquivos,path,filename,start_index=0):
    """
        Salva as listas de dicionario em arquivos .txt
        [input]
        * arquivos - lista com as listas de dicionario a serem salvas
        * filename - nome dos arquivos
        * path - pasta de destino
        [output]
        * nomes no formato: filename_[\d].txt
    """
    if path[-1] != '/':
        raise ValueError("{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format('salva_arquivos'))

    for i in range(0,len(arquivos)):
        f = open("{}{}_{}.txt".format(path,filename,i+start_index),"w")
        f.write(str(arquivos[i]))
        f.close()

def carrega_arquivo(filename):
    x = open(filename,'r')
    load = x.read()
    x.close()
    load_file = eval(load)
    return load_file

def carrega_arquivos(path,filenames=None):
    """
        Carrega os arquivos (.txt) da pasta especificada. Os arquivos devem ter indices sequenciais
        [input]
        * path - pasta com os arquivos
        * filenames - lista de str com o nome(sem indice) dos arquivos
        [output]
        * dicionario com o {nome dos arquivos (sem indice) : lista dos arquivos}
        Exemplo:
        carrega_arquivos('Home/','account') carrega account_0.txt,account_1.txt...
    """
    if path[-1] != '/':
        raise ValueError("{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format('carrega_arquivos'))
    if filenames != None:
        if type(filenames) != list:
            raise ValueError("{}: filenames invalido!".format('carrega_arquivos'))
        elif len(filenames) == 0:
            raise ValueError("{}: filenames invalido!".format('carrega_arquivos'))

    arquivos_carregados = {}
    dir_filenames = []
    dir_files = []

    for root, dirs, files in os.walk(path):  
        for f in files:
            dir_files.extend([f])
    
    for f in dir_files:
        nome = re.split('_(\d)*.txt',f)
        dir_filenames.extend([nome[0]])

    if filenames == None:
        filenames = dir_filenames
    elif not (set(filenames) < set(dir_filenames)):
        raise ValueError("{}: os arquivos {} nao existem nessa pasta!".format('carrega_arquivos',str(set(filenames) - set(dir_filenames))))
    print("{}: arquivos sendo carregados: {}".format('carrega_arquivos',str(set(filenames))))
    print("{}: arquivos nao sendo carregados: {}".format('carrega_arquivos',str(set(dir_filenames) - set(filenames))))

    filenames = list(set(filenames)) # remove duplicatas
    for f in filenames:
        arquivos_carregados[f] = []

    for f in dir_files:
        for nome_alvo in filenames:
            if f[:len(nome_alvo)] == nome_alvo:
                load_file = carrega_arquivo(path+f)
                arquivos_carregados[nome_alvo].extend([load_file])
    return arquivos_carregados

# funcoes de validacao de dados
def validId(id):
    """
        [input]
        * id - str com o id a ser validado
        [output]
        * str - ['Pagar.me','Mundi','Stone','empty','invalid']
    """
    assert type(id) == str

    if bool(re.fullmatch('[a-f\d]{24}',id)):
        return 'Pagar.me'
    elif bool(re.fullmatch('[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',id)):
        return 'Mundi'
    elif bool(re.fullmatch('[\d]+', id)):
        return 'Stone'
    elif id == '':
        return 'empty'
    else:
        return 'invalid'

def corrigeCNPJ(cnpj,n):
    b = str(cnpj)
    while len(b) < n:
        b = '0' + b
    return b

# funcoes de formatacao de dados do Salesforce usando pandas
def adjust_report(report):
    """ 
        Ajusta a resposta retornada pelo sf (lista de dicionario) em um dataframe
    """
    s = []
    a = copy.deepcopy(report)
    for i in a:
        if 'errors' in i.keys():
            if not i['errors']:
                del i['errors']
                s.append(i)
            else:
                i["message"] = i["errors"][0]["message"]
                del i['errors']
                s.append(i)
        else:
            s.append(i)
    dataframe = pd.DataFrame(s)
    dataframe = dataframe.applymap(lambda x: x.encode('unicode_escape').decode('utf-8') if isinstance(x, str) else x)
    return dataframe

def renomeia_list_of_dict(lista,depara=None,drop = False):
    """
        [input]
        * lista - lista de dicionarios
        * depara - dicionario com o nome das novas chaves
        * drop - True para retornar apenas as colunas do depara, False para retornar todas
        [output]
        * lista de dicionarios
    """
    out = []
    df = pd.DataFrame(lista)
    lod = df.to_list_of_dict(depara,drop=drop)
    out.extend([lod])
    return out

# metodos para a classe pandas.DataFrame
def to_unicode(self):
    out = self.applymap(lambda x: x.encode('unicode_escape').decode('utf-8') if isinstance(x, str) else x)
    return out

def to_list_of_dict(self,depara=None,drop = False):
    """
        [input]
        * depara - dicionario com nome das novas colunas
        * drop - True para retornar apenas as colunas do depara, False para retornar todas.
        [output]
        * lista de dicionario
    """
    if depara == None:
        print("{}: depara esta vazio, nenhuma coluna foi renomeada!".format('to_list_of_dict'))
        out = self.to_dict(orient='records')
    else:
        assert type(depara) == dict, "Formato inválido"
        depara_nao_nas_colunas = set(depara.keys()) - set(self.columns)
        colunas_nao_no_depara = set(self.columns) - set(depara.keys())
        if len(depara_nao_nas_colunas) != 0:
            raise ValueError("As seguintes chaves do depara nao estao no DataFrame: {}".format(depara_nao_nas_colunas))
        if (len(colunas_nao_no_depara) > 0 ):
            if drop:
                print("As seguintes colunas serao dropadas: {}".format(colunas_nao_no_depara))
            else:
                raise ValueError("As seguintes colunas nao estao no depara: {}".format(colunas_nao_no_depara))

        df_new_columns = self.rename(index=str, columns=depara,copy = True)
        if drop:
            df_new_columns.drop(columns =  list(set(df_new_columns.columns) - set(depara.values())), inplace = True)
        out = df_new_columns.to_dict(orient='records')
    return out

# metodos para a classe simple_salesforce.Salesforce
def list_of_dict_to_saleforce(self,obj,method,data,step=5000):
    """
        [input]
        * obj -- objeto do salesforce
        * method - ['insert', 'delete','upsert','update','undelete']
        * data -- lista de dicionario com os dados
        * step -- tamanho dos batchs
        [output]
        * lista de diconarios
    """

    assert method in ['insert', 'delete','upsert','update','undelete'], """{} : Operacao de query invalida""".format('to_saleforce')
    assert (type(data) is list) and (True if len(data)==0 else type(data[0]) is dict), """{} : Dado nao suportado""".format('to_saleforce')
    assert type(step) in [type(None),int]
    
    step = min(10000,step)

    completeReport = []
    outlist = []
    for i in range(0,len(data),step):
        output = eval('self.bulk.{}.{}'.format(obj,method))(data[i:i+step])
        outlist.extend(output)
    for i in range(0,len(outlist)):
        completeReport.append({**outlist[i],**data[i]})
    return completeReport

def decodeSFresponse(resp):
    out = []
    for root in resp:
        contents = {}
        for k in list(set(root.keys()) - {'attributes'}):
            nome = k
            content = root[k]
            while type(content) is dict:
                chave = list(set(content.keys()) - {'attributes'}) # sempre tem 'attribute' e o que eu quero
    #             print('chave:', chave[0], chave)
    #             print('conteudo:', content[chave[0]])
                content = content[chave[0]]
                nome += '.' + chave[0]
            contents[nome] = content
    #         print('contents:',contents
    #     print('contents:',contents)
        out.append(contents)
    return out

def query_salesforce(self,obj,query,api='bulk'):
    """
        [input]
        * obj - nome do objeto do salesforce
        * query - query
        * api - ['bulk','rest']
        [output]
        * lista de dicionario
    """
    assert type(obj) is str, '{} : obj deve ser tipo str'.format('query_salesforce')
    assert type(query) is str, '{} : query deve ser tipo str'.format('query_salesforce')  
    assert api in ['bulk','rest'], '{} : api deve ser bulk ou rest'.format('query_salesforce')  

    out = []
    resp = []
    if api == 'bulk':
        try:
            resp = eval('self.bulk.'+obj).query(query)
        except (IndexError,SalesforceMalformedRequest) as e:
            print("{}: {} request invalida: {}".format('query_salesforce',api,e))
            print('Tentando com rest')
            api = 'rest'
        if len(resp) > 0:
            out = decodeSFresponse(resp)
    if api == 'rest':
        try:
            resp = self.query_all(query)
        except (IndexError,SalesforceMalformedRequest) as e:
            print("{}: {} request invalida: {}".format('query_salesforce',api,e))
            print('Tentando sem query_all(), a resposta pode conter no maximo 2000 registros!')
            try:
                resp = self.query(query)
            except (IndexError,SalesforceMalformedRequest) as e:
                print("{}: {} request invalida: {}".format('query_salesforce',api,e))
        if len(resp) > 0:
            out = decodeSFresponse(resp)
    return out

def to_salesforce(self,lista,method,obj,path,depara=None,drop=False,step=5000,sufixo='',prefixo='',start_index=0):
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
    
    if path[-1] != '/':
        raise ValueError("{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format('to_salesforce'))

    arquivos = []
    resultados = []
    resultados_df = []
    for item in lista:
        lod = renomeia_list_of_dict(item,depara,drop=drop)
        arquivos.extend(lod)

    count = start_index
    for arquivo in arquivos:
        if len(arquivo) > 0:
            filename = """{}_{}_report_{}_{}""".format(prefixo,method,obj,sufixo)
            
            start_time = timeit.default_timer()
            print("{} #{} de {} {} iniciado - {}:".format(method,count,len(arquivo),obj,filename))
            report = self.list_of_dict_to_saleforce(obj,method,arquivo,step)
            
            df_report = adjust_report(report)
            df_report["taskid"] = df_report["id"]
            df_report.drop(columns=["id"],inplace = True)

            tmp = df_report.to_dict(orient='records')
            salva_arquivos([tmp],path,filename,start_index=count)
            resultados.extend([tmp])
            resultados_df.extend([df_report])

            err = df_report[~df_report.success].shape[0]
            suc = df_report[df_report.success].shape[0]

            print("\terros:",err)
            print("\tsucessos:",suc)
            if err > 0:
                try:
                    df_report.to_excel("{}{}_{}.xlsx".format(path,filename,count))
                except:
                    pass
                print('\tmensagem: ', set(df_report.message))
            m, s = divmod(timeit.default_timer() - start_time, 60)
            print("\ttempo decorrido: {:1.0f}min {:2.0f}s".format(m,s))
            count += 1

    return resultados

def simple_describe(self,path,filename,nomes_objetos=None):
    """
        [input]
        * path - caminho para salvar o arquivo
        * filename - nome do arquivo a ser salvo
        * nomes_objetos - lista com o nome dos objetos> None para consultar todos
        [output]
    """
    if path[-1] != '/':
        raise ValueError("{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format('simple_describe'))
    
    quero = {'createable','custom','calculated','label','name','permissionable','queryable','retrieveable','searchable','triggerable','updateable','autoNumber','defaultedOnCreate','nillable','referenceTo','type'}
    simple_describe_objetos = pd.DataFrame()

    describe_sf = self.describe()
    objects = adjust_report(describe_sf['sobjects'])
    print("Max Batch Size: {}".format(describe_sf['maxBatchSize']))
    print("Encoding: {}".format(describe_sf['encoding']))

    if nomes_objetos == None:
        nomes_objetos = list(set(objects.name))

    for obj in nomes_objetos:
        describe_obj = eval("self.{}.describe()".format(obj))
        describe_campos_completo = pd.DataFrame(describe_obj['fields'])
        describe_campos_reduzido = describe_campos_completo[list(quero & set(describe_campos_completo.columns))].copy()
        describe_campos_reduzido['object'] = obj
        simple_describe_objetos = pd.concat([describe_campos_reduzido,simple_describe_objetos],axis=0)
    simple_describe_objetos.to_excel("{}{}.xlsx".format(path,filename),index=False)
    lod_simple_describe_objetos = simple_describe_objetos.to_dict(orient='records')
    return lod_simple_describe_objetos

# fazer funcionar com timestamp

# def select_all_from(self,obj,query,api='bulk'):
    
# falta fazer
# consulta org

# nova mudanca
if __name__ == "__main__":
    main()
