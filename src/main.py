import subprocess

def run_script(script_name):
    """Function to run a Python script using subprocess."""
    print(f"Starting {script_name}")
    result = subprocess.run(['python', script_name], capture_output=True, text=True)
    print(f"Finished {script_name}")
    if result.stdout:
        print("Output:", result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

# List of your Python scraper scripts
scripts = [#'src/scrape_general_info/info_ajuda_regions.py',
           #'src/scrape_general_info/info_alcantara_regions.py',
           #'src/scrape_general_info/info_alvalade_regions.py',
           #'src/scrape_general_info/info_areeiro_regions.py',
           #'src/scrape_general_info/info_arroios_regions.py',
           #'src/scrape_general_info/info_avenidas_novas_regions.py',
           'src/scrape_general_info/info_beato_regions.py',
           'src/scrape_general_info/info_belem_regions.py',
           'src/scrape_general_info/info_benfica_regions.py',
           'src/scrape_general_info/info_campo_de_ourique_regions.py',
           'src/scrape_general_info/info_campolide_regions.py',
           'src/scrape_general_info/info_carnide_regions.py', 
           'src/scrape_general_info/info_estrela_regions.py',
           'src/scrape_general_info/info_lumiar_regions.py',
           'src/scrape_general_info/info_marvila_regions.py',
           'src/scrape_general_info/info_misericordia_regions.py',
           'src/scrape_general_info/info_olivais_regions.py'
           'src/scrape_general_info/info_parque_das_nacoes_regions.py',
           'src/scrape_general_info/info_penha_de_franca_regions.py',
           'src/scrape_general_info/info_santa_clara_regions.py',
           'src/scrape_general_info/info_santa_maria_maior_regions.py',
           'src/scrape_general_info/info_santo_antonio_regions.py',
           'src/scrape_general_info/info_sao_vicente_regions.py'
           ]

for script in scripts:
    run_script(script) 