using System.Text.Json.Serialization;

namespace AED4Life.DataModel.Enums;

[JsonConverter(typeof(JsonStringEnumConverter<AEDAccess>))]
public enum AEDAccess {
	Open = 0,
	Emergency = 1,
	Private = 2
}
