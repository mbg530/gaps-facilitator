#!/bin/bash

DB="fourws.db"

echo "Listing all tables in $DB:"
sqlite3 "$DB" ".tables"
echo

# Get all table names
tables=$(sqlite3 "$DB" ".tables" | tr ' ' '\n')

for table in $tables; do
    echo "-------------------------------"
    echo "Table: $table"
    echo "-------------------------------"
    sqlite3 "$DB" <<EOF
.headers on
.mode column
SELECT * FROM $table;
EOF
    echo
done
