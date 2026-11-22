using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel.DTOs;

public sealed record AEDReportResponse(
	Int64 Id, Int64 UserId, Int64? AEDId, String PhotoUrl,
	String Description, Int32? AvailabilityStartHour, Int32? AvailabilityEndHour, Boolean? IsPubliclyAccessible, Int32? Rating,
	DateTime Created, DateTime LastUpdated, ReportStatus Status,
	Double? ReporterLatitude, Double? ReporterLongitude, Double? Latitude, Double? Longitude,
	String? CityName, String? StreetName, String? PostalCode, Int32? BuildingNumber);
