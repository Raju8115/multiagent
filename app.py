from flask import Flask, request, jsonify
from db_connector import db_conn
import ibm_db
import uuid, os

app = Flask(__name__)

@app.route("/")
def hello():
    return "Flask app is live!"

@app.route("/update-customer", methods=["POST"])
def update_customer():
    data = request.get_json()
    customer_id = data["customer_id"]
    new_email = data.get("new_email")
    new_phone = data.get("new_phone")
    print(new_email)
    conn = db_conn()
    try:
        fetch_stmt = ibm_db.prepare(conn, "SELECT MOBILE, EMAIL FROM customer_master WHERE customer_id = ?")
        ibm_db.bind_param(fetch_stmt, 1, customer_id)
        ibm_db.execute(fetch_stmt)
        row = ibm_db.fetch_tuple(fetch_stmt)
        if not row:
            return f"Customer {customer_id} not found", 404
        old_phone, old_email = row
        print(new_email, " ", old_email)
        updates = []
        if new_phone:
            stmt = ibm_db.prepare(conn, "UPDATE customer_master SET MOBILE = ? WHERE customer_id = ?")
            ibm_db.bind_param(stmt, 1, new_phone)
            ibm_db.bind_param(stmt, 2, customer_id)
            ibm_db.execute(stmt)
            updates.append(f"Phone updated from {old_phone} to {new_phone}")
        if new_email:
            stmt = ibm_db.prepare(conn, "UPDATE customer_master SET EMAIL = ? WHERE customer_id = ?")
            ibm_db.bind_param(stmt, 1, new_email)
            ibm_db.bind_param(stmt, 2, customer_id)
            ibm_db.execute(stmt)
            updates.append(f"Email updated from {old_email} to {new_email}")
        return jsonify({"result": ", ".join(updates)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        ibm_db.close(conn)


@app.route("/make-payment", methods=["POST"])
def make_payment():
    data = request.get_json()
    customer_id = data["customer_id"]
    destination_account_id = data["destination_account_id"]
    amount = data["amount"]

    conn = db_conn()
    try:
        ibm_db.autocommit(conn, ibm_db.SQL_AUTOCOMMIT_OFF)
        fetch_source = ibm_db.prepare(
            conn,
            "SELECT account_id FROM customer_account WHERE customer_id = ? AND account_type = 'Savings'"
        )
        ibm_db.bind_param(fetch_source, 1, customer_id)
        ibm_db.execute(fetch_source)
        source_row = ibm_db.fetch_tuple(fetch_source)
        if not source_row:
            ibm_db.rollback(conn)
            return "No savings account found.", 404
        source_account_id = source_row[0]

        fetch_dest = ibm_db.prepare(conn, "SELECT balance FROM customer_account WHERE account_id = ?")
        ibm_db.bind_param(fetch_dest, 1, destination_account_id)
        ibm_db.execute(fetch_dest)
        dest_row = ibm_db.fetch_tuple(fetch_dest)
        if not dest_row:
            ibm_db.rollback(conn)
            return "Destination account not found.", 404

        update_source = ibm_db.prepare(conn, "UPDATE customer_account SET balance = balance - ? WHERE account_id = ?")
        ibm_db.bind_param(update_source, 1, amount)
        ibm_db.bind_param(update_source, 2, source_account_id)
        ibm_db.execute(update_source)

        update_dest = ibm_db.prepare(conn, "UPDATE customer_account SET balance = balance + ? WHERE account_id = ?")
        ibm_db.bind_param(update_dest, 1, amount)
        ibm_db.bind_param(update_dest, 2, destination_account_id)
        ibm_db.execute(update_dest)

        txn_id = str(uuid.uuid4())
        insert_txn = ibm_db.prepare(
            conn,
            "INSERT INTO account_transactions (txn_id, account_id, txn_date, amount, destination_account_id, merchant, location) "
            "VALUES (?, ?, CURRENT TIMESTAMP, ?, ?, NULL, NULL)"
        )
        ibm_db.bind_param(insert_txn, 1, txn_id)
        ibm_db.bind_param(insert_txn, 2, source_account_id)
        ibm_db.bind_param(insert_txn, 3, amount)
        ibm_db.bind_param(insert_txn, 4, destination_account_id)
        ibm_db.execute(insert_txn)

        ibm_db.commit(conn)
        return jsonify({"message": "Payment successful", "txn_id": txn_id})
    except Exception as e:
        ibm_db.rollback(conn)
        return jsonify({"error": str(e)}), 500
    finally:
        ibm_db.autocommit(conn, ibm_db.SQL_AUTOCOMMIT_ON)
        ibm_db.close(conn)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port)
