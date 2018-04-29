import pandas as pd
import numpy as np
import os
import re
import timeit
import copy

# funcoes de gerenciamento de arquivos, respeitando os limites do Salesforce
def num_caracteres(lista):
    """
        Retorna o numero de caracteres de uma lista.
    """
    todos_c = ""
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
    maximo = min(maximo, 10000000)
    num_carac_por_registro = []
    for registro in lista:
        num_carac_por_registro.append(num_caracteres([registro]))
    num_carac_cumulativo = list(np.cumsum(num_carac_por_registro))
    x = num_carac_cumulativo.copy()
    quebra = []
    ultimo = 0
    for i in range(0, len(x) - 1):
        if x[i + 1] > maximo:
            # print(x[i+1], x[i],i)
            x[i + 1:] = list(np.add(x[i + 1:], [-x[i]] * len(x[i + 1:])))
            x[:i + 1] = [0] * len(x[:i + 1])
            quebra.append(lista[ultimo:i + 1])
            ultimo = i + 1
            # print('x depois:',x)
    if ultimo <= len(x):
        quebra.append(lista[ultimo:len(x)])
    return quebra


def quebra_num_de_registros(lista, max_registros=10000):
    """
        Quebra uma lista em sublistas respeitando o numero maximo de registros
        [input]
        * lista
        * max_registros
        [output]
        * lista com as sublistas
    """
    max_registros = min(max_registros, 10000)
    files = []
    for i in range(0, len(lista), max_registros):
        files.append(lista[i:i + max_registros])
    return files


def separa_arquivos(lista, max_registros=10000, max_carac=10000000):
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
        raise ValueError("{}: lista deve ser do tipo list".format("quebra_arquivos"))
    if len(lista) == 0:
        raise ValueError(
            "{}: a lista de lista passada nao tem itens".format("quebra_arquivos")
        )
    if type(lista[0]) == list:
        raise ValueError("{}: Nao passe uma lista de listas!".format("quebra_arquivos"))

    sublistas_finais = []
    sublistas_registros = quebra_num_de_registros(lista, max_registros=max_registros)

    for sublista in sublistas_registros:
        sublistas_finais.extend(quebra_list_num_caracteres(sublista, maximo=max_carac))
    return sublistas_finais


def salva_arquivos(arquivos, filename, path=None, start_index=0):
    """
        Salva as listas de dicionario em arquivos .txt
        [input]
        * arquivos - lista com as listas de dicionario a serem salvas
        * filename - nome dos arquivos
        * path - pasta de destino
        [output]
        * nomes no formato: filename_[\d].txt
    """
    if path is not None:
        if path[-1] != "/":
            raise ValueError(
                "{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format(
                    "salva_arquivos"
                )
            )
    else:
        path = ''
    for i in range(0, len(arquivos)):
        with open("{}{}_{}.txt".format(path, filename, i + start_index), "w") as f:
            f.write(str(arquivos[i]))


def carrega_arquivo(filename):
    with open(filename, "r")  as target:
        load = target.read()
    load_file = eval(load)
    return load_file


def carrega_arquivos(path=None, filenames=None):
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
    if path is not None:
        if path[-1] != "/":
            raise ValueError(
                "{}: O path passado nao direciona para uma pasta. Coloque '/' no final!".format(
                    "carrega_arquivos"
                )
            )
    else:
        path = ''
    if filenames != None:
        if type(filenames) != list:
            raise ValueError("{}: filenames invalido!".format("carrega_arquivos"))
        elif len(filenames) == 0:
            raise ValueError("{}: filenames invalido!".format("carrega_arquivos"))
    arquivos_carregados = {}
    dir_filenames = []
    dir_files = []
    for files in os.walk(path):
        for f in files[2]:
            dir_files.append(f)
    for f in dir_files:
        nome = re.split("_(\d)*.txt", f)
        dir_filenames.append(nome[0])

    if filenames == None:
        filenames = dir_filenames
    elif not (set(filenames) < set(dir_filenames)):
        raise ValueError(
            "{}: os arquivos {} nao existem nessa pasta!".format(
                "carrega_arquivos", str(set(filenames) - set(dir_filenames))
            )
        )
    print(
        "{}: arquivos sendo carregados: {}".format(
            "carrega_arquivos", str(set(filenames))
        )
    )
    filenames = list(set(filenames))  # remove duplicatas
    for f in filenames:
        arquivos_carregados[f] = []
    for f in dir_files:
        for nome_alvo in filenames:
            if f[:len(nome_alvo)] == nome_alvo:
                load_file = carrega_arquivo(path + f)
                arquivos_carregados[nome_alvo].append(load_file)
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

    if bool(re.fullmatch("[a-f\d]{24}", id)):
        return "Pagar.me"
    elif bool(
        re.fullmatch(
            "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            id,
        )
    ):
        return "Mundi"
    elif bool(re.fullmatch("[\d]+", id)):
        return "Stone"
    elif id == "":
        return "empty"
    else:
        return "invalid"


def corrigeCNPJ(cnpj, n):
    b = str(cnpj)
    while len(b) < n:
        b = "0" + b
    return b


# funcoes de formatacao de dados do Salesforce usando pandas
def adjust_report(report):
    """ 
        Ajusta a resposta retornada pelo sf (lista de dicionario) em um dataframe
    """
    s = []
    a = copy.deepcopy(report)
    for i in a:
        if "errors" in i.keys():
            if not i["errors"]:
                del i["errors"]
                s.append(i)
            else:
                i["message"] = i["errors"][0]["message"]
                del i["errors"]
                s.append(i)
        else:
            s.append(i)
    dataframe = pd.DataFrame(s)
    dataframe = dataframe.applymap(
        lambda x: x.encode("unicode_escape").decode("utf-8")
        if isinstance(x, str)
        else x
    )
    return dataframe


def renomeia_list_of_dict(lista, depara=None, drop=False):
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
    lod = to_lod(df,depara, drop=drop)
    out.append(lod)
    return out

def to_lod(df, depara=None, drop=False):
    """
        [input]
        * depara - dicionario com nome das novas colunas
        * drop - True para retornar apenas as colunas do depara, False para retornar todas.
        [output]
        * lista de dicionario
    """
    df_copy = copy.deepcopy(df)
    if depara == None:
        print(
            "{}: depara esta vazio, nenhuma coluna foi renomeada!".format(
                "to_lod"
            )
        )
        out = df_copy.to_dict(orient="records")
    else:
        assert type(depara) == dict, "Formato inválido"
        depara_nao_nas_colunas = set(depara.keys()) - set(df_copy.columns)
        colunas_nao_no_depara = set(df_copy.columns) - set(depara.keys())
        if len(depara_nao_nas_colunas) != 0:
            raise ValueError(
                "As seguintes chaves do depara nao estao no DataFrame: {}".format(
                    depara_nao_nas_colunas
                )
            )
        if len(colunas_nao_no_depara) > 0:
            if drop:
                print(
                    "As seguintes colunas serao dropadas: {}".format(
                        colunas_nao_no_depara
                    )
                )
            else:
                raise ValueError(
                    "As seguintes colunas nao estao no depara: {}".format(
                        colunas_nao_no_depara
                    )
                )

        df_new_columns = df_copy.rename(index=str, columns=depara, copy=True)
        if drop:
            df_new_columns.drop(
                columns=list(set(df_new_columns.columns) - set(depara.values())),
                inplace=True,
            )
        out = df_new_columns.to_dict(orient="records")
    return out


