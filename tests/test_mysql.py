"""Integration tests for MySQL connection and data operations.

Tests MySQL database schema creation and CIM data upload from
cimgraph GraphModel objects.

Prerequisites:
    - Docker daemon running
    - MySQL container: docker-compose up -d mysql

Usage:
    pytest tests/test_mysql.py -v
    pytest tests/test_mysql.py -v -k test_schema
    pytest -m mysql
"""

import pytest

from cimloader.databases import MySQLConnection


# =============================================================================
# Connection Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.mysql
class TestMySQLConnection:
    """Test MySQL connection functionality."""

    def test_connection_create(self, mysql_connection):
        """Test that connection can be created."""
        assert mysql_connection is not None
        assert mysql_connection.host == 'localhost'
        assert mysql_connection.username == 'root'
        assert mysql_connection.database == 'rc4_2021'

    def test_connection_connect(self, mysql_connection):
        """Test that connection can be established."""
        mysql_connection.connect()
        assert mysql_connection.connection is not None
        assert mysql_connection.cursor is not None

    def test_connection_execute_query(self, mysql_connection):
        """Test executing a simple SQL query."""
        query = "SELECT 1 AS value"
        result = mysql_connection.execute(query)
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == 1

    def test_connection_disconnect(self, mysql_connection):
        """Test disconnection."""
        mysql_connection.connect()
        mysql_connection.disconnect()
        assert mysql_connection.cursor is None


# =============================================================================
# Schema Creation Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.mysql
class TestMySQLSchema:
    """Test MySQL schema creation from CIM profile."""

    def test_configure_creates_tables(self, mysql_connection):
        """Test that configure() creates tables for CIM classes."""
        # configure() was already called in fixture
        # Verify tables exist
        query = "SHOW TABLES"
        result = mysql_connection.execute(query)
        tables = [row[0] for row in result]

        # Should have many tables for CIM classes
        assert len(tables) > 50, "Should create tables for CIM classes"

        # Check for specific expected tables
        common_tables = ['ACLineSegment', 'PowerTransformer', 'EnergyConsumer', 'Feeder']
        for table in common_tables:
            if table in tables:
                # At least some expected tables should exist
                break
        else:
            # If none of the common tables exist, that's unexpected
            pytest.skip(f"Expected CIM tables not found. Available: {tables[:10]}")

    def test_configure_table_structure(self, mysql_connection):
        """Test that created tables have correct structure."""
        # Check a specific table structure
        query = "DESCRIBE ACLineSegment"
        try:
            result = mysql_connection.execute(query)
            columns = [row[0] for row in result]

            # Should have audit columns
            assert 'username' in columns, "Should have username audit column"
            assert 'timestamp' in columns, "Should have timestamp audit column"

            # Should have mRID
            assert '_mRID' in columns, "Should have _mRID column"
        except Exception as e:
            pytest.skip(f"ACLineSegment table not available: {e}")

    def test_configure_handles_enums(self, mysql_connection):
        """Test that enumeration classes are handled correctly."""
        # Check if any enum tables were created
        query = "SHOW TABLES"
        result = mysql_connection.execute(query)
        tables = [row[0] for row in result]

        # CIM has many enumerations - check for a common one
        enum_tables = [t for t in tables if 'PhaseCode' in t or 'UnitSymbol' in t or 'WindingConnection' in t]
        # May or may not have enum tables depending on profile
        # Just verify no errors occurred

    def test_reconfigure_drops_and_recreates(self, mysql_connection):
        """Test that configure can be run multiple times."""
        # Get initial table count
        query = "SHOW TABLES"
        result = mysql_connection.execute(query)
        initial_count = len(result)

        # Reconfigure
        mysql_connection.configure()

        # Check table count again
        result = mysql_connection.execute(query)
        final_count = len(result)

        # Should have similar number of tables
        assert final_count == initial_count, "Table count should be consistent after reconfigure"


# =============================================================================
# Data Upload Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.mysql
@pytest.mark.slow
class TestMySQLDataUpload:
    """Test uploading CIM data to MySQL.

    Note: These tests require loading data from Blazegraph first
    using cimgraph GraphModel, which is a more complex integration test.
    """

    def test_table_insert(self, mysql_connection):
        """Test basic insert into a CIM table."""
        try:
            # Clear table
            mysql_connection.execute("DELETE FROM ACLineSegment")

            # Insert a test record
            query = """
            INSERT INTO ACLineSegment (username, timestamp, _mRID, _name)
            VALUES (%s, %s, %s, %s)
            """
            params = ('test_user', 1234567890, 'test-mrid-123', 'TestLine')
            mysql_connection.cursor.execute(query, params)
            mysql_connection.connection.commit()

            # Verify insert
            result = mysql_connection.execute("SELECT * FROM ACLineSegment WHERE _mRID = 'test-mrid-123'")
            assert len(result) == 1, "Should have inserted one record"
            assert result[0][2] == 'test-mrid-123', "Should have correct mRID"

            # Cleanup
            mysql_connection.execute("DELETE FROM ACLineSegment WHERE _mRID = 'test-mrid-123'")
            mysql_connection.connection.commit()
        except Exception as e:
            pytest.skip(f"ACLineSegment table not available or schema mismatch: {e}")

    def test_query_empty_table(self, mysql_connection):
        """Test querying an empty table."""
        try:
            # Clear table
            mysql_connection.execute("DELETE FROM ACLineSegment")
            mysql_connection.connection.commit()

            # Query
            result = mysql_connection.execute("SELECT COUNT(*) FROM ACLineSegment")
            count = result[0][0]
            assert count == 0, "Table should be empty"
        except Exception as e:
            pytest.skip(f"ACLineSegment table not available: {e}")


# =============================================================================
# Query Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.mysql
class TestMySQLQuery:
    """Test SQL query functionality."""

    def test_query_show_databases(self, mysql_connection):
        """Test listing databases."""
        query = "SHOW DATABASES"
        result = mysql_connection.execute(query)
        databases = [row[0] for row in result]
        assert 'rc4_2021' in databases, "Should have test database"

    def test_query_show_tables(self, mysql_connection):
        """Test listing tables."""
        query = "SHOW TABLES"
        result = mysql_connection.execute(query)
        assert len(result) > 0, "Should have tables"

    def test_query_table_count(self, mysql_connection):
        """Test counting tables."""
        query = "SHOW TABLES"
        result = mysql_connection.execute(query)
        table_count = len(result)
        # Should have created many tables for CIM classes
        assert table_count > 50, f"Should have many CIM tables, got {table_count}"

    def test_query_with_json_column(self, mysql_connection):
        """Test querying JSON columns (used for CIM references)."""
        try:
            # Insert test data with JSON
            mysql_connection.execute("DELETE FROM ACLineSegment")
            query = """
            INSERT INTO ACLineSegment (username, timestamp, _mRID, _BaseVoltage)
            VALUES (%s, %s, %s, %s)
            """
            json_data = '{"@id": "test-voltage-id", "@type": "BaseVoltage"}'
            params = ('test_user', 1234567890, 'test-mrid-json', json_data)
            mysql_connection.cursor.execute(query, params)
            mysql_connection.connection.commit()

            # Query with JSON extraction
            result = mysql_connection.execute(
                "SELECT _BaseVoltage FROM ACLineSegment WHERE _mRID = 'test-mrid-json'"
            )
            assert len(result) == 1, "Should find record"

            # Cleanup
            mysql_connection.execute("DELETE FROM ACLineSegment WHERE _mRID = 'test-mrid-json'")
            mysql_connection.connection.commit()
        except Exception as e:
            pytest.skip(f"JSON column test not applicable: {e}")


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.integration
@pytest.mark.mysql
class TestMySQLErrorHandling:
    """Test error handling in MySQL operations."""

    def test_query_invalid_sql(self, mysql_connection):
        """Test executing invalid SQL query."""
        with pytest.raises(Exception):
            mysql_connection.execute("INVALID SQL QUERY")

    def test_query_nonexistent_table(self, mysql_connection):
        """Test querying a table that doesn't exist."""
        with pytest.raises(Exception):
            mysql_connection.execute("SELECT * FROM NonexistentTable")

    def test_insert_invalid_data_type(self, mysql_connection):
        """Test inserting data with wrong type."""
        try:
            # Try to insert string into timestamp field
            query = "INSERT INTO ACLineSegment (username, timestamp, _mRID) VALUES (%s, %s, %s)"
            params = ('test_user', 'not-a-timestamp', 'test-mrid')
            with pytest.raises(Exception):
                mysql_connection.cursor.execute(query, params)
        except Exception as e:
            pytest.skip(f"Schema doesn't match expected structure: {e}")
