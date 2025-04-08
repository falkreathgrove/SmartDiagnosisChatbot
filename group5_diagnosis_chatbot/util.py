import os
from dotenv import load_dotenv

load_dotenv()

AWS_MYSQL_USER = os.getenv("AWS_MYSQL_USER_YE")
AWS_MYSQL_PASSWORD = os.getenv("AWS_MYSQL_PASSWORD_YE")
AWS_MYSQL_ENDPOINT = os.getenv("AWS_MYSQL_ENDPOINT_YE")

AWS_S3_REGION = os.getenv("AWS_S3_REGION_YE")
AWS_S3_ACCESS_KEY_ID = os.getenv("AWS_S3_ACCESS_KEY_ID_YE")
AWS_S3_SECRET_ACCESS_KEY = os.getenv("AWS_S3_SECRET_ACCESS_KEY_YE")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME_YE")
AWS_S3_KMS_KEY_ARN = os.getenv("AWS_S3_KMS_KEY_ARN_YE")

####################################

import pymysql


def connect_database(database_name):
    conn = pymysql.connect(
        host=AWS_MYSQL_ENDPOINT,
        user=AWS_MYSQL_USER,
        password=AWS_MYSQL_PASSWORD,
        db=database_name,
    )

    return conn


def create_database(database_name):
    conn = pymysql.connect(
        host=AWS_MYSQL_ENDPOINT,
        user=AWS_MYSQL_USER,
        password=AWS_MYSQL_PASSWORD,
    )

    query = f"CREATE DATABASE IF NOT EXISTS {database_name}"

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
        conn.commit()
        conn.close()
        print("Success create_database")
    except Exception as e:
        print("Error create_database", e)


def delete_database(database_name):
    conn = pymysql.connect(
        host=AWS_MYSQL_ENDPOINT,
        user=AWS_MYSQL_USER,
        password=AWS_MYSQL_PASSWORD,
    )

    query = f"DROP DATABASE IF EXISTS {database_name}"

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
        conn.commit()
        conn.close()
        print("Success delete_database")
    except Exception as e:
        print("Error delete_database", e)


def create_chat_history_table(conn):
    query = """
    CREATE TABLE IF NOT EXISTS chat (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50),
    patient_id VARCHAR(50),
    session_time VARCHAR(50),
    role VARCHAR(50),
    message TEXT,
    image_key VARCHAR(100)
    )
    """

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)

        conn.commit()
        print("Success create_chat_history_table")
    except Exception as e:
        print("Error create_chat_history_table", e)


def delete_chat_history_table(conn):
    query = "DROP TABLE IF EXISTS chat"

    try:
        with conn.cursor() as cursor:
            cursor.execute(query)

        conn.commit()
        print("Success delete_chat_history_table")
    except Exception as e:
        print("Error delete_chat_history_table", e)


def insert_data(conn, table_name, data):
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    values = list(data.values())

    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, values)

        conn.commit()
        print("Success insert_data")
    except Exception as e:
        print("Error insert_data", e)


def get_sessions_by_user_and_patient(conn, user_id, patient_id):
    query = f"SELECT DISTINCT session_time FROM chat WHERE user_id = %s AND patient_id = %s ORDER BY session_time"

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id, patient_id))
            session_times = [row[0] for row in cursor.fetchall()]

            print("Success get_sessions_by_user_and_patient")
            return session_times
    except Exception as e:
        print("Error get_sessions_by_user_and_patient", e)


def get_contents_by_user_and_patient_and_session(
    conn, user_id, patient_id, session_time
):
    query = f"SELECT role, message, image_key FROM chat WHERE user_id = %s AND patient_id = %s AND session_time = %s ORDER BY id"

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id, patient_id, session_time))
            res = cursor.fetchall()

            print("Success get_contents_by_user_and_patient_and_session")
            return [
                {"role": row[0], "message": row[1], "image_key": row[2]} for row in res
            ]
    except Exception as e:
        print("Error get_contents_by_user_and_patient_and_session", e)


def delete_contents_by_user_and_patient_and_session(
    conn, user_id, patient_id, session_time
):
    query = (
        f"DELETE FROM chat WHERE user_id = %s AND patient_id = %s AND session_time = %s"
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (user_id, patient_id, session_time))

        conn.commit()
        print("Success delete_contents_by_user_and_patient_and_session")
    except Exception as e:
        print("Error delete_contents_by_user_and_patient_and_session", e)


####################################

import boto3

s3 = boto3.client(
    service_name="s3",
    region_name=AWS_S3_REGION,
    aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY,
)


def upload_file(file, key):
    try:
        s3.upload_fileobj(
            Fileobj=file.file,
            Bucket=AWS_S3_BUCKET_NAME,
            Key=key,
            ExtraArgs={
                "ACL": "private",
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": AWS_S3_KMS_KEY_ARN,
            },
        )
        print("Success upload_file")
    except Exception as e:
        print("Error upload_file:", e)


def delete_file(key):
    try:
        s3.delete_object(Bucket=AWS_S3_BUCKET_NAME, Key=key)
        print("Success delete_file")
    except Exception as e:
        print("Error delete_file:", e)


def generate_presigned_url(key, expire):
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": AWS_S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expire,
        )
        print("Success generate_presigned_url")
        return url
    except Exception as e:
        print("Error generate_presigned_url", e)


####################################


def upload_content(data, file):
    if data["image_key"] == "None" and file != None:
        print("Error upload_content")
        return

    if data["image_key"] != "None" and file == None:
        print("Error upload_content")
        return

    conn = connect_database("diag_chatbot_db")

    if data["image_key"] != "None":
        upload_file(file, data["image_key"])

    insert_data(conn, "chat", data)

    conn.close()


def get_contents(user, patient, session):
    conn = connect_database("diag_chatbot_db")

    rows = get_contents_by_user_and_patient_and_session(conn, user, patient, session)

    for row in rows:
        if row["image_key"] != "None":
            row["image_key"] = generate_presigned_url(row["image_key"], 1200)

    conn.close()

    return rows


def delete_contents(user, patient, session):
    conn = connect_database("diag_chatbot_db")

    rows = get_contents_by_user_and_patient_and_session(conn, user, patient, session)

    for row in rows:
        if row["image_key"] != "None":
            delete_file(row["image_key"])

    delete_contents_by_user_and_patient_and_session(conn, user, patient, session)

    conn.close()
