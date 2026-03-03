import pyodbc
import psycopg2

# 1. Connect to your LOCAL Neodata (Source)
try:
    mssql_conn = pyodbc.connect(
        r'DRIVER={ODBC Driver 17 for SQL Server};'
        r'SERVER=localhost\SQLEXPRESS;'
        r'DATABASE=MiBaseDeDatos;'
        r'Trusted_Connection=yes;'
    )
    ms_cursor = mssql_conn.cursor()
    print("Connected to Neodata SQL Server.")
except Exception as e:
    print(f"Failed to connect to Neodata: {e}")

# 2. Connect to your DOCKER Postgres (Target)
try:
    pg_conn = psycopg2.connect(
        host="localhost", 
        database="neocloud_erp", 
        user="admin", 
        password="password123"
    )
    pg_cursor = pg_conn.cursor()
    print("Connected to Docker Postgres.")
except Exception as e:
    print(f"Failed to connect to Docker: {e}")

def run_migration():
    # Fetch the Top 10 projects from Neodata
    ms_cursor.execute("SELECT IdPresupuesto, Presupuesto, Nombre FROM PuPresupuestos")
    rows = ms_cursor.fetchall()
    
    for row in rows:
        # INSERT INTO the 'projects' table we just created
        pg_cursor.execute(
            "INSERT INTO projects (id, name, description) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (row.IdPresupuesto, row.Presupuesto, row.Nombre)
        )
    
    pg_conn.commit()
    print(f"Migration Complete: {len(rows)} projects moved to Cloud.")

if __name__ == "__main__":
    run_migration()