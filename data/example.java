public static String getValueForColumn(ResultSet rs, String columnNameToCheck, Database database){
    ResultSetMetaData metadata = rs.getMetaData();
    int numberOfColumns = metadata.getColumnCount();
    String correctedColumnName = database.correctObjectName(columnNameToCheck, Column.class);
    for (int i = 1; i < (numberOfColumns + 1); i++) {
        String columnName = metadata.getColumnLabel(i);
        if (correctedColumnName.equalsIgnoreCase(columnName)) {
            return rs.getString(columnName);
        }
    }
    return null;
}

