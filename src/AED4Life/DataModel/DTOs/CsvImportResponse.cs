namespace AED4Life.DataModel.DTOs;

public sealed record CsvImportResponse(
	String ProfileName, Int32 RowsProcessed, IReadOnlyDictionary<String, CsvImportTableResult> Tables);

public sealed record CsvImportTableResult(Int32 Inserted, Int32 Updated);
