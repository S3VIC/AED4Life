using AED4Life.DataModel.Entities;

namespace AED4Life.DataModel;

internal static class AEDQueries {
	internal static IQueryable<AED> OrderByDistance(this IQueryable<AED> aeds, Double latitude, Double longitude,
		Double? maximumDistanceMeters = null) {
		const Double degreesToRadians = Math.PI / 180;
		const Double earthRadiusMeters = 6371000;
		Double originCosine = Math.Cos(latitude * degreesToRadians);
		var distances =
			from aed in aeds
			where aed.Latitude != null && aed.Longitude != null
			let latitudeSine = Math.Sin((aed.Latitude!.Value - latitude) * degreesToRadians / 2)
			let longitudeSine = Math.Sin((aed.Longitude!.Value - longitude) * degreesToRadians / 2)
			select new {
				AED = aed,
				Distance = latitudeSine * latitudeSine
					+ originCosine * Math.Cos(aed.Latitude!.Value * degreesToRadians) * longitudeSine * longitudeSine
			};
		if (maximumDistanceMeters is Double maximum) {
			Double maximumTerm = Math.Pow(Math.Sin(maximum / (2 * earthRadiusMeters)), 2);
			distances = distances.Where(candidate => candidate.Distance <= maximumTerm);
		}
		// The haversine term orders and bounds great-circle distances without inverse trigonometry.
		return distances.OrderBy(candidate => candidate.Distance).ThenBy(candidate => candidate.AED.Id)
			.Select(candidate => candidate.AED);
	}
}
