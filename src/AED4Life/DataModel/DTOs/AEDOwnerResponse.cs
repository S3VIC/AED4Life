namespace AED4Life.DataModel.DTOs;

public sealed record AEDOwnerResponse(
	String? RegonNumber, Boolean? IsPublic, String? Name,
	String? CityName, String? StreetName);
