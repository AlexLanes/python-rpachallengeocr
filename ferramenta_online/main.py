# std
import os as OS
import csv as Csv
# interno
from navegador import Navegador

def main() -> None:
    navegador = Navegador("https://rpachallengeocr.azurewebsites.net/")
    navegador.iniciar_desafio()

    invoices = navegador.obter_invoices()
    for invoice in invoices:
        navegador.baixar_imagem(invoice)
        navegador.iniciar_processamento(invoice)

    for invoice in invoices:
        navegador.capturar_informacoes(invoice)
        del invoice["contexto"]

    # Criar o .csv
    nomeCsv = "output.csv"
    with open( rf"./arquivos/{ nomeCsv }", "w", newline = "" ) as file:
        writer = Csv.DictWriter( file, list(invoices[0].keys()) )
        writer.writeheader()
        writer.writerows(invoices)
    
    navegador.finalizar_desafio(nomeCsv, 5)

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
Ambos os formatos precisam de uma interpretação única
Apenas o Aenean entra na condicação do DueDate
    - Sit Amet Corp.
    - Aenean LLC
"""
if __name__ == "__main__":
    # Limpa a pasta dos arquivos
    [ OS.remove(f"./arquivos/{ imagem }") for imagem in OS.listdir("./arquivos") ]
    
    main()
    exit(0)