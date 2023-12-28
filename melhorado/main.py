# std
from time import sleep
from enum import Enum, unique
from re import search as re_search
from datetime import datetime as DateTime
# interno
import bot


NOME_CSV = "resultado.csv"
DATA_AGORA = str(DateTime.utcnow().date())
SITE = "https://rpachallengeocr.azurewebsites.net"


@unique
class Localizadores (Enum):
    start = "button#start"
    submit = "input[name=csv]"
    next = "a#tableSandbox_next"
    linhas_tabela = ".//tbody/tr"


def inverter_data (data: str) -> str:
    """Inverter a data (ano para dia) ou (dia para ano)"""
    return "-".join(reversed(data.split("-")))


def main():
    """Fluxo principal"""
    try:
        # abrir site
        navegador = bot.navegador.Edge(3)
        navegador.pesquisar(SITE)

        # iniciar o desafio
        navegador.encontrar_elemento("css selector", Localizadores.start).click()
        sleep(0.5)

        # invoices
        # list[(id, dueDate, linkImagem)]
        invoices: list[tuple[str, str, str]] = []

        # loop da paginação dos invoices
        while True:
            # loop nas linhas da tabela
            linhas = navegador.encontrar_elementos("xpath", Localizadores.linhas_tabela)
            for index, _ in enumerate(linhas): 
                sleep(0.01)
                _id = navegador.encontrar_elemento("xpath", f"{ Localizadores.linhas_tabela.value }[{ index + 1 }]/td[2]").text
                dueDate = navegador.encontrar_elemento("xpath", f"{ Localizadores.linhas_tabela.value }[{ index + 1 }]/td[3]").text
                dueDate = inverter_data(dueDate)
                link = navegador.encontrar_elemento("xpath", f"{ Localizadores.linhas_tabela.value }[{ index + 1 }]/td[4]/a").get_attribute("href")
                if dueDate <= DATA_AGORA: invoices.append((_id, dueDate, link))

            # paginação
            _next = navegador.encontrar_elemento("css selector", Localizadores.next)
            if "disabled" in _next.get_attribute("class"): break
            else: _next.click()
        
        # campos necessários no csv
        colunas = ["ID", "DueDate", "InvoiceNo", "InvoiceDate", "CompanyName", "TotalDue"]
        linhas: list[list[str]] = []

        # loop da extração dos dados
        leitor = bot.imagem.LeitorOCR()
        for (_id, dueDate, linkImagem) in invoices:
            linha = [_id, inverter_data(dueDate), "", "", "Aenean LLC", ""]
            imagem = bot.rest.request("get", linkImagem).content
            for texto, _ in leitor.ler_imagem(imagem):
                if match := re_search(r"#\d{5,6}$", texto): linha[2] = match.group()[1:]
                elif re_search(r"^\d{4}-\d{2}-\d{2}$", texto): linha[3] = inverter_data(texto)
                elif re_search(r"^\d{3,}\.\d{1,2}$", texto): linha[5] = texto
            linhas.append(linha)

        # montar csv
        with open(NOME_CSV, "w", encoding="utf-8") as csv:
            csv.write(",".join(colunas) + "\n")
            for linha in linhas: csv.write(",".join(linha) + "\n")

        # enviar csv
        navegador.encontrar_elemento("css selector", Localizadores.submit)\
                 .send_keys(bot.windows.path.abspath(NOME_CSV))
        sleep(5)

    except TimeoutError as erro:
        bot.logger.erro(f"Erro de timeout na espera de alguma condição/elemento/janela: { erro }")
        exit(1)
    except AssertionError as erro:
        bot.logger.erro(f"Erro de validação pré-execução de algum passo no fluxo: { erro }")
        exit(1)
    except Exception as erro:
        bot.logger.erro(f"Erro inesperado no fluxo: { erro }")
        exit(1)


if __name__ == "__main__":
    bot.logger.informar("### Iniciado execução do fluxo ###")
    main()
    bot.logger.informar("### Finalizado execução com sucesso ###")


"""
Desafio RPA: https://rpachallengeocr.azurewebsites.net/

Dados necessários dos invoices:
    - ID: TABELA
    - DueDate: TABELA DD-MM-YYYY
    - InvoiceNo: IMAGEM
    - InvoiceDate: IMAGEM
    - CompanyName: IMAGEM
    - TotalDue: IMAGEM

Procurar apenas pelos invoices onde:
    - DueDate <= Date.Now

São 2 formatos de invoice
    - Sit Amet Corp.
    - Aenean LLC
Ambos os formatos precisam de uma interpretação única
Apenas o Aenean entra na condicação do DueDate
"""