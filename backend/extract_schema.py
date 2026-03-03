import pyodbc

# CONFIGURATION
# Using the details from your ATTACH script
server = r'localhost\SQLEXPRESS'
database = 'MiBaseDeDatos'

connection_string = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"Trusted_Connection=yes;"
)

def discover_neodata_schema():
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        print(f"--- Connected to {database} ---")
        
        # 1. List all tables
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables = cursor.fetchall()
        
        print(f"\nFound {len(tables)} tables. Look for: 'Insumo', 'Matriz', 'Concepto'.")
        
        # 2. Focus on the most important Neodata tables
        for table in tables:
            table_name = table[0]
            if any(key in table_name.lower() for key in ['insumo', 'matriz', 'concepto', 'presupuesto']):
                print(f"\n[TABLE] {table_name}")
                cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table_name}'")
                for col in cursor.fetchall():
                    print(f"  - {col[0]} ({col[1]})")
                    
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    discover_neodata_schema()