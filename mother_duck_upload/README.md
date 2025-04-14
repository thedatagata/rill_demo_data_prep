# MotherDuck Uploader Script

## Overview

This Python script uploads a specific table from a local DuckDB database file to your MotherDuck cloud account. It's designed to be run after the `filter_data_swamp_pipeline.py` script (or any process that generates a DuckDB file you want to upload).

The script interactively prompts the user for necessary information like file paths, database names, table names, and authentication tokens.

## Prerequisites

* **Python:** Version 3.x installed.
* **DuckDB Python Package:** You need the `duckdb` library installed in your Python environment. If you haven't installed it yet, open your terminal or command prompt and run:
    ```bash
    pip install duckdb --upgrade
    ```
* **MotherDuck Account:** You need an active MotherDuck account.
* **MotherDuck Service Token:** You need a service token from MotherDuck to allow the script to authenticate and upload data. You can generate one in your MotherDuck account settings.

## Setup

1.  **Save the Script:** Save the Python code provided as a file (e.g., `upload_to_motherduck.py`).
2.  **Locate Your DuckDB File:**
    * The previous pipeline step (`filter_data_swamp_pipeline.py`) creates a DuckDB file, typically named `data_swamp.duckdb` inside the `data_swamp_models` directory.
    * Make sure you know the **full path** to this file. You can either:
        * Run this upload script from the **same root directory** as the `data_swamp_models` folder, and provide the relative path (`data_swamp_models/data_swamp.duckdb`) when prompted.
        * Move the `data_swamp.duckdb` file elsewhere and provide its new full path when prompted.
        * Provide the full absolute path to the file in its original location when prompted.
3.  **Set Up MotherDuck Token (Recommended):**
    * For better security, it's recommended to set your MotherDuck Service Token as an environment variable named `MD_TOKEN`.
        * **Linux/macOS:** `export MD_TOKEN='your_token_here'`
        * **Windows (Command Prompt):** `set MD_TOKEN=your_token_here`
        * **Windows (PowerShell):** `$env:MD_TOKEN='your_token_here'`
    * If the script doesn't find the `MD_TOKEN` environment variable, it will prompt you to paste the token directly (input will be hidden).

## How to Run

1.  **Open Terminal:** Open a terminal or command prompt.
2.  **Navigate:** Go to the directory where you saved `upload_to_motherduck.py`.
3.  **Execute:** Run the script using Python:
    ```bash
    python upload_to_motherduck.py
    ```
4.  **Answer Prompts:** The script will ask for the following information:
    * **Full path to your local DuckDB file:** (e.g., `data_swamp_models/data_swamp.duckdb` or `/path/to/your/data_swamp.duckdb`).
    * **Your MotherDuck database name:** The name of the target database in MotherDuck (e.g., `my_analytics_db`).
    * **Schema name in the local file:** The schema containing the table you want to upload. The previous script loads data into the `source_data` schema, so you'll likely enter `source_data` (the script defaults to `main`, so be sure to change it if needed).
    * **Table name from the local file:** The specific table you want to upload (e.g., `src_sessions_fct` or `src_events_fct`).
    *