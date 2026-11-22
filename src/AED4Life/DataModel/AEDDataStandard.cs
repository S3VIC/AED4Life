using AED4Life.DataModel.Entities;
using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel;

/// <summary>
/// The AED4Life data standard. An AED record is <see cref="AEDRating.Fine"/> when nothing the application needs
/// to guide a rescuer is missing, otherwise <see cref="AEDRating.MissingData"/>. Required:
/// <list type="bullet">
/// <item><c>location</c>: latitude and longitude;</item>
/// <item><c>address</c>: city, street, postal code (all nonblank) and building number;</item>
/// <item><c>name</c>: a nonblank owner name (the AED itself has no name);</item>
/// <item><c>access</c>: the access category;</item>
/// <item><c>hours</c>: both availability hours.</item>
/// </list>
/// </summary>
public static class AEDDataStandard {
	public const String Location = "location";
	public const String Address = "address";
	public const String Name = "name";
	public const String Access = "access";
	public const String Hours = "hours";

	public static readonly IReadOnlyList<String> AllGaps = [Location, Address, Name, Access, Hours];

	/// <summary>Returns the names of the required data groups that are missing (empty when the record is complete).</summary>
	public static List<String> Gaps(Double? latitude, Double? longitude, String? cityName, String? streetName,
		String? postalCode, Int32? buildingNumber, String? ownerName, AEDAccess? access,
		Int32? availabilityStartHour, Int32? availabilityEndHour) {
		List<String> gaps = [];
		if (latitude is null || longitude is null) {
			gaps.Add(Location);
		}
		if (String.IsNullOrWhiteSpace(cityName) || String.IsNullOrWhiteSpace(streetName)
			|| String.IsNullOrWhiteSpace(postalCode) || buildingNumber is null) {
			gaps.Add(Address);
		}
		if (String.IsNullOrWhiteSpace(ownerName)) {
			gaps.Add(Name);
		}
		if (access is null) {
			gaps.Add(Access);
		}
		if (availabilityStartHour is null || availabilityEndHour is null) {
			gaps.Add(Hours);
		}
		return gaps;
	}

	public static AEDRating Evaluate(AED aed, String? cityName, String? streetName, String? postalCode,
		Int32? buildingNumber, String? ownerName) =>
		Gaps(aed.Latitude, aed.Longitude, cityName, streetName, postalCode, buildingNumber, ownerName, aed.Access,
			aed.AvailabilityStartHour, aed.AvailabilityEndHour).Count == 0
			? AEDRating.Fine
			: AEDRating.MissingData;
}
