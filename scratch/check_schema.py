import psycopg
c = psycopg.connect('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
cur = c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables ({len(tables)}): {tables}")
for t in tables:
    n = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    cols = [r[0] for r in c.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name=%s ORDER BY ordinal_position", (t,)).fetchall()]
    print(f"  {t}: {n} rows, {len(cols)} cols")
    print(f"    {cols}")
c.close()
