namespace AED4Life.Translation;

public sealed class CsvImportException(String key, String message) : Exception(message) {
	public String Key { get; } = key;
}
