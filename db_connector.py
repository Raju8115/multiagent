import os
import ibm_db
from dotenv import load_dotenv

load_dotenv()  # if using .env locally

def db_conn():
    conn_str = (
        f"DATABASE={os.getenv('DB_NAME')};"
        f"HOSTNAME={os.getenv('DB_HOSTNAME')};"
        f"PORT={os.getenv('DB_PORT')};"
        f"PROTOCOL=TCPIP;"
        f"UID={os.getenv('DB_UID')};"
        f"PWD={os.getenv('DB_PWD')};"
        f"SECURITY={os.getenv('DB_SECURITY')};"
    )
    return ibm_db.connect(conn_str, "", "")
