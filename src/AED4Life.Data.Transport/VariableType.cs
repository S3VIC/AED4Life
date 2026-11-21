using System.Text.Json.Serialization;

namespace AED4Life.Trananslation;

[JsonConverter(typeof(JsonStringEnumConverter<VariableType>))]
public enum VariableType {
	INTEGER,
	DOUBLE,
	STRING,
	BOOLEAN
}