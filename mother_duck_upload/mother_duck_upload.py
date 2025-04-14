# -*- coding: utf-8 -*-
"""
MotherDuck Uploader Script

This script helps you upload a specific table from a local DuckDB database file
to your MotherDuck account.

It will ask you for:
1.  The path to your local DuckDB file (e.g., C:\\Users\\YourName\\data.db or /home/user/data.duckdb).
2.  Your MotherDuck database name (the one you see in app.motherduck.com).
3.  The schema name where your table is located in the local file (often 'main').
4.  The name of the table you want to upload from the local file.
5.  The name you want the table to have in MotherDuck (usually the same).
6.  Your MotherDuck Service Token (if not set as an environment variable).

**Prerequisites:**
* Python 3 installed on your computer.
* DuckDB installed for Python: Open a terminal or command prompt and run:
    pip install duckdb --upgrade

**How to Run:**
1.  Save this code as a Python file (e.g., upload_to_motherduck.py).
2.  Open a terminal or command prompt.
3.  Navigate to the directory where you saved the file.
4.  Run the script using: python upload_to_motherduck.py
5.  Answer the questions the script asks.
"""

import duckdb
import os
import sys
import getpass # Used to hide token input

# --- Function to get user input with defaults ---
def get_input(prompt_text, default_value=None):
    """Gets input from the user, providing a default value."""
    if default_value:
        prompt_with_default = f"{prompt_text} (Press Enter for default: '{default_value}'): "
    else:
        prompt_with_default = f"{prompt_text}: "

    value = input(prompt_with_default).strip()
    if not value and default_value:
        return default_value
    return value

# --- Configuration via User Prompts ---
print("-" * 60)
print("MotherDuck Table Uploader Configuration")
print("-" * 60)

# 1. Get Local DuckDB File Path
local_db_path_prompt = "Enter the FULL path to your local DuckDB file (e.g., data_swamp.duckdb)"
local_db_path = get_input(local_db_path_prompt)
if not local_db_path:
    print("\nError: Local database file path cannot be empty.")
    sys.exit(1)

# 2. Get MotherDuck Database Name
motherduck_db_name_prompt = "Enter your MotherDuck database name (e.g., rill_demo)"
motherduck_db_name = get_input(motherduck_db_name_prompt, "rill_demo") # Provide a common default

# 3. Get Source Schema Name
source_schema_prompt = "Enter the schema name containing your table in the local file"
source_schema_name = get_input(source_schema_prompt, "main") # DuckDB default schema is 'main'

# 4. Get Source Table Name
source_table_prompt = f"Enter the table name from schema '{source_schema_name}' to upload"
source_table_name = get_input(source_table_prompt)
if not source_table_name:
    print("\nError: Source table name cannot be empty.")
    sys.exit(1)

# 5. Get Destination Table Name
dest_table_prompt = f"Enter the desired table name in MotherDuck"
destination_table_name = get_input(dest_table_prompt, source_table_name) # Default to same name

# 6. Get MotherDuck Token (Check Environment Variable first)
print("\n--- MotherDuck Authentication ---")
motherduck_token = os.getenv('MD_TOKEN') # Check for env var named MD_TOKEN
if not motherduck_token:
    print("INFO: MotherDuck Token not found in environment variable 'MD_TOKEN'.")
    print("      You will be prompted to paste it.")
    print("\nWARNING: Pasting tokens directly is less secure than using environment variables.")
    print("         The token will not be saved in the script or displayed on screen.")
    try:
        # Use getpass to hide the token as the user types/pastes it
        motherduck_token = getpass.getpass("Please paste your MotherDuck Service Token now: ")
    except Exception as e:
        print(f"\nError reading token input: {e}")
        sys.exit(1)

if not motherduck_token:
    print("\nError: MotherDuck Token is required for authentication.")
    sys.exit(1)
else:
     print("Token received.")

# --- Set Up Connection Details ---
# Alias for the attached local database (used internally in SQL)
local_db_alias = 'local_source_db'

# Construct the connection string including the token
# Using f-string requires careful handling of {} if db name had them, but unlikely.
md_conn_str = f"md:{motherduck_db_name}?motherduck_token={motherduck_token}"
full_source_table_path = f'{local_db_alias}."{source_schema_name}"."{source_table_name}"'

# --- Main Upload Process ---
print("\n" + "-" * 60)
print("Starting Upload Process...")
print("-" * 60)

connection = None # Initialize connection variable outside try block

try:
    # 1. Connect to MotherDuck
    print(f"1. Connecting to MotherDuck database: '{motherduck_db_name}'...")
    # `connect` handles authentication using the token in the string
    connection = duckdb.connect(database=md_conn_str, read_only=False)
    print("   Successfully connected to MotherDuck.")

    # 2. Attach the local database file
    # Use READ_ONLY as we only need to read from the local file
    attach_sql = f"ATTACH '{local_db_path}' AS {local_db_alias} (READ_ONLY);"
    print(f"2. Attaching local database: '{local_db_path}'...")
    connection.execute(attach_sql)
    print(f"   Local database attached successfully as '{local_db_alias}'.")

    # 3. Prepare the copy command
    # Use CREATE OR REPLACE: WARNING - THIS WILL DELETE AND REPLACE THE TABLE IF IT EXISTS IN MOTHERDUCK!
    # Alternatives (more complex): Check existence first, or use CREATE TABLE IF NOT EXISTS ...
    copy_sql = f"""
    CREATE OR REPLACE TABLE "{destination_table_name}" AS
    SELECT * FROM {full_source_table_path};
    """
    print(f"3. Preparing to copy data from '{source_schema_name}.{source_table_name}' (local)")
    print(f"   to '{destination_table_name}' (in MotherDuck '{motherduck_db_name}').")
    print("   WARNING: This will OVERWRITE the destination table if it exists!")

    # --- Confirmation Step ---
    confirm = input("   Do you want to proceed with the upload? (yes/no): ").lower().strip()
    if confirm != 'yes':
        print("\nUpload cancelled by user.")
        # Still need to detach before exiting
        print("Detaching local database...")
        connection.execute(f"DETACH {local_db_alias};")
        connection.close()
        print("Exiting.")
        sys.exit(0)
    # --- End Confirmation Step ---

    # 4. Execute the copy command
    print(f"4. Executing data copy...")
    connection.execute(copy_sql)
    print("   Copy command executed.")

    # 5. Verify copy (optional check)
    print(f"5. Verifying table '{destination_table_name}' in MotherDuck...")
    row_count_result = connection.execute(f'SELECT COUNT(*) FROM "{destination_table_name}";').fetchone()
    if row_count_result:
        row_count = row_count_result[0]
        print(f"   Successfully created/replaced '{destination_table_name}' with {row_count} rows in MotherDuck.")
    else:
        print(f"   Could not verify row count for '{destination_table_name}', but copy command finished.")


# --- Error Handling ---
except duckdb.IOException as e:
     print(f"\n!!! ERROR: Could not access the local file !!!")
     print(f"    File path used: '{local_db_path}'")
     print(f"    Error details: {e}")
     print(f"    -> Please check if the file path is correct and the file exists.")
except duckdb.CatalogException as e:
     print(f"\n!!! ERROR: Could not find table or schema !!!")
     print(f"    Error details: {e}")
     print(f"    -> Check if schema '{source_schema_name}' and table '{source_table_name}' exist in your local file.")
     print(f"    -> Also check if MotherDuck database '{motherduck_db_name}' exists.")
except duckdb.AuthenticationException as e: # Catching specific auth error
     print(f"\n!!! ERROR: Authentication Failed !!!")
     print(f"    Error details: {e}")
     print(f"    -> Check if your MotherDuck database name ('{motherduck_db_name}') is correct.")
     print(f"    -> Check if your MotherDuck Token is correct and has not expired.")
except duckdb.Error as e: # Catch other DuckDB-related errors (connection, SQL syntax etc.)
    print(f"\n!!! DUCKDB ERROR !!!")
    print(f"    Details: {e}")
    # Check if it might be an authentication error missed by the specific exception
    if "Authentication failed" in str(e) or "token" in str(e).lower():
         print(f"    -> This looks like an AUTHENTICATION error.")
         print(f"    -> Check your MotherDuck database name ('{motherduck_db_name}') and Token validity.")
    elif "attach" in str(e).lower() and local_db_path in str(e):
         print(f"    -> Error likely occurred while attaching '{local_db_path}'. Check path/file.")
    else:
         print(f"    -> An unexpected database error occurred. Check connection details and table/schema names.")
except Exception as e: # Catch any other unexpected Python errors
    print(f"\n!!! UNEXPECTED SCRIPT ERROR !!!")
    print(f"    Details: {e}")
    print(f"    -> Please report this error if it persists.")

# --- Cleanup ---
finally:
    if connection:
        try:
            # Always try to detach if connection was made, even if copy failed
            print("\n6. Detaching local database (cleanup)...")
            # Check if alias exists before detaching to avoid errors if attach failed
            attached_dbs = connection.execute("SELECT database_name FROM duckdb_databases() WHERE internal = false;").fetchall()
            if any(db[0] == local_db_alias for db in attached_dbs):
                 connection.execute(f"DETACH {local_db_alias};")
                 print("   Local database detached.")
            else:
                 print(f"   Local database '{local_db_alias}' was not attached or already detached.")

            connection.close()
            print("   Connection to MotherDuck closed.")
        except duckdb.Error as cleanup_error:
             print(f"   Error during cleanup (detach/close): {cleanup_error}")
             print("   You may need to manually check connections if issues persist.")

print("\n" + "-" * 60)
print("Script finished.")
print("-" * 60)