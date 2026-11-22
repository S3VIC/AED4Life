using System.Text.Json.Serialization;

namespace AED4Life.DataModel.DTOs;

public sealed record NearestAEDResponse(
	Int64 Id,
	Double Latitude,
	Double Longitude,
	[property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] String? OwnerName,
	[property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] String? CityName,
	[property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] String? StreetName,
	[property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] String? PostalCode,
	[property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Int32? BuildingNumber);
