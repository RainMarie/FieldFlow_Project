import sqlite3
import pandas as pd
import re

def parse_foreign_key(col_name, notes):
    """
    Parses the 'Notes / Foreign Keys' column to extract foreign key relationships.
    Looks for the pattern: "References table_name(column_name)"
    """
    if pd.isna(notes):
        return None
        
    match = re.search(r'References\s+([a-zA-Z0-9_]+)\(([a-zA-Z0-9_]+)\)', str(notes))
    if match:
        target_table = match.group(1)
        target_column = match.group(2)
        return f"FOREIGN KEY ({col_name}) REFERENCES {target_table}({target_column})"
    return None

def build_schema_from_excel(excel_path="TBC_Database_Schema.xlsx", db_file="tbc_local.db"):
    """
    Reads the Data Dictionary from the Excel file and builds the SQLite database schema.
    """
    # Step 1: Read the Excel file
    try:
        print(f"Reading schema from {excel_path}...")
        df = pd.read_excel(excel_path, sheet_name="Data Dictionary")
    except Exception as e:
        print(f"Failed to read Excel file: {e}")
        return

    # Step 2: Connect to the SQLite Database
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Enable foreign key support in SQLite
        cursor.execute("PRAGMA foreign_keys = ON;")
        print(f"Connected to local database: {db_file}")

        # Group data by table name to process one table at a time
        grouped_tables = df.groupby('Table Name', sort=False)

        # Step 3: Iterate through each table group to build the CREATE TABLE statement
        for table_name, group in grouped_tables:
            column_clauses = []
            foreign_key_clauses = []
            
            for index, row in group.iterrows():
                col_name = str(row['Column Name']).strip()
                data_type = str(row['Data Type']).strip().upper()
                key_type = str(row['Key Type']) if pd.notna(row['Key Type']) else ""
                nullable = str(row['Nullable']).strip().lower()
                default_val = row['Default Value']
                notes = row['Notes / Foreign Keys']

                # Build the basic column definition
                col_sql = f"{col_name} {data_type}"

                # Handle Primary and Unique keys
                if "primary key" in key_type.lower():
                    # SQLite prefers INTEGER for auto-increment primary keys
                    if data_type == 'INTEGER':
                         col_sql += " PRIMARY KEY AUTOINCREMENT"
                    else:
                         col_sql += " PRIMARY KEY"
                elif "unique" in key_type.lower():
                    col_sql += " UNIQUE"

                # Handle Nullability
                if nullable == "no":
                    col_sql += " NOT NULL"

                # Handle Default Values
                if pd.notna(default_val):
                    # Format strings with quotes, leave numbers as they are
                    if isinstance(default_val, str):
                        col_sql += f" DEFAULT '{default_val.strip()}'"
                    else:
                         col_sql += f" DEFAULT {default_val}"

                column_clauses.append(col_sql)

                # Check for Foreign Keys in the Notes column
                fk_clause = parse_foreign_key(col_name, notes)
                if fk_clause:
                    foreign_key_clauses.append(fk_clause)

            # Step 4: Combine all clauses to form the final CREATE TABLE statement
            all_clauses = column_clauses + foreign_key_clauses
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    "
            create_table_sql += ",\n    ".join(all_clauses)
            create_table_sql += "\n);"

            # print(f"\nExecuting SQL for {table_name}:\n{create_table_sql}") # Uncomment to debug SQL strings
            
            # Step 5: Execute the generated statement
            try:
                cursor.execute(create_table_sql)
                print(f"Created table: {table_name}")
            except sqlite3.Error as e:
                 print(f"Error creating table {table_name}: {e}")
                 print(f"Failed SQL: {create_table_sql}")

        # Commit all changes to the database
        conn.commit()
        print("\nDatabase schema deployment complete!")

    except sqlite3.Error as error:
        print(f"Database connection error occurred: {error}")
        
    finally:
        # Step 6: Safely close the database connection
        if conn:
            conn.close()

if __name__ == "__main__":
    build_schema_from_excel()