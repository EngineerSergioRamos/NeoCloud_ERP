import pyodbc
import psycopg2

def migrate_details():
    try:
        mssql = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=MiBaseDeDatos;Trusted_Connection=yes;')
        ms_cur = mssql.cursor()
        pg = psycopg2.connect(host="localhost", database="neocloud_erp", user="admin", password="password123")
        pg_cur = pg.cursor()

        # We join the Matrix Link with the Licitaciones Catalog
        # Note: We use 'Codigo' for the join as it's the standard Neodata key
        query = """
        SELECT 
            e.IdCodigoInsumo, 
            COALESCE(i.Descripcion, 'Insumo ' + CAST(e.IdCodigoInsumo AS VARCHAR)), 
            COALESCE(i.Unidad, 'pza'), 
            e.Volumen
        FROM PuExpinsXconcepto e
        LEFT JOIN LicLicitacionesInsumos i ON e.IdCodigoInsumo = i.Codigo
        WHERE e.IdCodigoMatriz = 860466
        """
        ms_cur.execute(query)
        rows = ms_cur.fetchall()

        pg_cur.execute("DELETE FROM matrix_items WHERE project_id = 48")

        for row in rows:
            pg_cur.execute(
                "INSERT INTO matrix_items (project_id, code, description, unit, quantity) VALUES (%s, %s, %s, %s, %s)",
                (48, str(row[0]), row[1], row[2], float(row[3]))
            )
        
        pg.commit()
        print(f"SUCCESS: Migrated {len(rows)} items. If descriptions are still missing, we will target 'PuInsumos' next.")
        
    except Exception as e:
        print(f"MIGRATION ERROR: {e}")

if __name__ == "__main__":
    migrate_details()