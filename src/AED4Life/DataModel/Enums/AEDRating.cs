using System.Text.Json.Serialization;

namespace AED4Life.DataModel.Enums;

[JsonConverter(typeof(JsonStringEnumConverter<AEDRating>))]
public enum AEDRating {
	MissingData = 0,
	Fine = 1
}
