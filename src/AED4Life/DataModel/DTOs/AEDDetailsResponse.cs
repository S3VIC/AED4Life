using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel.DTOs;

public sealed record AEDDetailsResponse(
	Int64 Id, Double? Latitude, Double? Longitude,
	String? OwnerName, String? CityName, String? StreetName, String? PostalCode, Int32? BuildingNumber,
	AEDAccess? Access, Int32? AvailabilityStartHour, Int32? AvailabilityEndHour,
	AEDRating? DataRating, DateTime LastUpdated);
