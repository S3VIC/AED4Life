namespace AED4Life.DataModel.DTOs;

public sealed record AEDOwnerResponse(
	Int64 RegonNumber, Boolean IsPublic, String Name,
	String CityName, String PostalCode, String StreetName);
