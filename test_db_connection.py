from db import get_connection


def test_read_only_connection_rejects_write():
    connection = get_connection(read_only=True)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute("CREATE TABLE test_readonly_guard (id INTEGER)")
            connection.commit()
            assert False, "Expected a read-only violation"
        except Exception as error:
            assert "read-only" in str(error).lower()
        finally:
            connection.rollback()
    finally:
        connection.close()


def test_read_write_connection_can_select():
    connection = get_connection(read_only=False)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
    finally:
        connection.close()
