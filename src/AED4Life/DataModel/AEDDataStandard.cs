using AED4Life.DataModel.Entities;
using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel;

/// <summary>
/// The AED4Life data standard. An AED record is <see cref="AEDRating.Fine"/> when nothing the application needs
/// to guide a rescuer is missing: GPS coordinates, a complete address (city, street, postal code, building number),
/// the access category and both opening hours. Otherwise it is <see cref="AEDRating.MissingData"/>.
/// The owner is optional and does not affect the rating.
/// </summary>
public static class AEDDataStandard {
	public static AEDRating Evaluate(AED aed, Boolean addressComplete) =>
		aed.Latitude is not null && aed.Longitude is not null
		&& addressComplete
		&& aed.Access is not null
		&& aed.AvailabilityStartHour is not null && aed.AvailabilityEndHour is not null
			? AEDRating.Fine
			: AEDRating.MissingData;
}
