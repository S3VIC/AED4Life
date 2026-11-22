using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using AED4Life.DataModel.Enums;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;

namespace AED4Life.Endpoints;

public static class AedEndpoints {
	private static readonly TimeZoneInfo AvailabilityTimeZone = TimeZoneInfo.FindSystemTimeZoneById("Europe/Warsaw");

	public static RouteGroupBuilder MapAedEndpoints(this IEndpointRouteBuilder endpoints) {
		RouteGroupBuilder group = endpoints.MapGroup("/api/aed").WithTags("AED");
		group.MapGet("/owners", GetOwnersAsync)
			.WithName("GetAEDOwners")
			.WithSummary("Get AED owners with address details")
			.WithDescription("Returns all owners joined with their city and street, ordered by REGON. "
				+ "Includes nullable city and street names without exposing location IDs; owners with unknown locations are included. "
				+ "Returns an empty array when no owners exist. No request body is required.");
		group.MapGet("/nearest", GetNearestAsync)
			.WithName("GetNearestAvailableAED")
			.WithSummary("Find the nearest available AED")
			.WithDescription("Provide latitude (-90 to 90) and longitude (-180 to 180) as required query parameters. "
				+ "Returns the nearest AED by great-circle distance, with its coordinates and known owner/address metadata. "
				+ "Unknown metadata fields are omitted. Private AEDs, devices with missing coordinates, and devices known to be closed are excluded. "
				+ "Open, Emergency, and unknown access are allowed. Unknown or partial hours are allowed; complete daily hours are evaluated "
				+ "in Europe/Warsaw, with an inclusive opening hour and exclusive closing hour, including overnight ranges. "
				+ "Distance ties select the lowest AED ID. Returns HTTP 404 when no candidate exists.")
			.ProducesProblem(StatusCodes.Status404NotFound);
		group.MapGet("/nearest({count})", GetNearestManyAsync)
			.WithName("GetNearestAvailableAEDs")
			.WithSummary("Find the requested number of nearest available AEDs")
			.WithDescription("Provide a positive integer count in the route, for example /api/aed/nearest(5), "
				+ "and required latitude (-90 to 90) and longitude (-180 to 180) query parameters. "
				+ "Returns up to count available AEDs ordered by great-circle distance, then AED ID for ties. "
				+ "Uses the same access and Europe/Warsaw opening-hour rules as /api/aed/nearest. "
				+ "Unknown owner/address metadata is omitted. Returns an empty array when no candidate exists.");
		return group;
	}

	private static async Task<Results<Ok<NearestAEDResponse>, ValidationProblem, ProblemHttpResult>> GetNearestAsync(
		Double latitude, Double longitude, AED4LifeDbContext database, CancellationToken cancellationToken) {
		Dictionary<String, String[]> errors = ValidateCoordinates(latitude, longitude);
		if (errors.Count > 0) {
			return TypedResults.ValidationProblem(errors);
		}

		NearestAEDResponse? nearest = await QueryNearest(database, latitude, longitude).FirstOrDefaultAsync(cancellationToken);
		if (nearest is null) {
			return TypedResults.Problem(statusCode: StatusCodes.Status404NotFound,
				title: "No available AED with known coordinates was found.");
		}
		return TypedResults.Ok(WithKnownMetadata(nearest));
	}

	private static async Task<Results<Ok<List<NearestAEDResponse>>, ValidationProblem>> GetNearestManyAsync(
		Int32 count, Double latitude, Double longitude, AED4LifeDbContext database, CancellationToken cancellationToken) {
		Dictionary<String, String[]> errors = ValidateCoordinates(latitude, longitude);
		if (count <= 0) {
			errors["count"] = ["Count must be a positive integer."];
		}
		if (errors.Count > 0) {
			return TypedResults.ValidationProblem(errors);
		}

		List<NearestAEDResponse> nearest = await QueryNearest(database, latitude, longitude).Take(count).ToListAsync(cancellationToken);
		return TypedResults.Ok(nearest.ConvertAll(WithKnownMetadata));
	}

	private static Dictionary<String, String[]> ValidateCoordinates(Double latitude, Double longitude) {
		Dictionary<String, String[]> errors = [];
		if (!Double.IsFinite(latitude) || latitude is < -90 or > 90) {
			errors["latitude"] = ["Latitude must be a finite number between -90 and 90."];
		}
		if (!Double.IsFinite(longitude) || longitude is < -180 or > 180) {
			errors["longitude"] = ["Longitude must be a finite number between -180 and 180."];
		}
		return errors;
	}

	private static IQueryable<NearestAEDResponse> QueryNearest(AED4LifeDbContext database, Double latitude, Double longitude) {
		Int32 hour = TimeZoneInfo.ConvertTime(DateTimeOffset.UtcNow, AvailabilityTimeZone).Hour;
		const Double degreesToRadians = Math.PI / 180;
		Double originCosine = Math.Cos(latitude * degreesToRadians);
		return
			from aed in database.AEDs.AsNoTracking()
			where aed.Latitude != null && aed.Longitude != null
			where aed.Access == null || aed.Access == AEDAccess.Open || aed.Access == AEDAccess.Emergency
			where aed.AvailabilityStartHour == null || aed.AvailabilityEndHour == null
				|| (aed.AvailabilityStartHour < aed.AvailabilityEndHour
					? aed.AvailabilityStartHour <= hour && hour < aed.AvailabilityEndHour
					: aed.AvailabilityStartHour <= hour || hour < aed.AvailabilityEndHour)
			let latitudeSine = Math.Sin((aed.Latitude!.Value - latitude) * degreesToRadians / 2)
			let longitudeSine = Math.Sin((aed.Longitude!.Value - longitude) * degreesToRadians / 2)
			// The haversine term orders great-circle distances without an inverse trigonometric calculation.
			let distance = latitudeSine * latitudeSine
				+ originCosine * Math.Cos(aed.Latitude!.Value * degreesToRadians) * longitudeSine * longitudeSine
			join owner in database.AEDOwners on aed.OwnerId equals owner.Id into owners
			from owner in owners.DefaultIfEmpty()
			join address in database.Addresses on aed.AddressId equals address.Id into addresses
			from address in addresses.DefaultIfEmpty()
			join city in database.Cities on address.CityId equals city.Id into cities
			from city in cities.DefaultIfEmpty()
			join street in database.Streets on address.StreetId equals street.Id into streets
			from street in streets.DefaultIfEmpty()
			join postalCode in database.PostalCodes on address.PostalCodeId equals postalCode.Id into postalCodes
			from postalCode in postalCodes.DefaultIfEmpty()
			orderby distance, aed.Id
			select new NearestAEDResponse(aed.Id, aed.Latitude!.Value, aed.Longitude!.Value,
				owner == null ? null : owner.Name, city == null ? null : city.Name,
				street == null ? null : street.Name, postalCode == null ? null : postalCode.Code,
				address == null ? null : address.BuildingNumber);
	}

	private static NearestAEDResponse WithKnownMetadata(NearestAEDResponse nearest) => nearest with {
		OwnerName = KnownText(nearest.OwnerName),
		CityName = KnownText(nearest.CityName),
		StreetName = KnownText(nearest.StreetName),
		PostalCode = KnownText(nearest.PostalCode)
	};

	private static String? KnownText(String? value) => String.IsNullOrWhiteSpace(value) ? null : value;

	private static async Task<Ok<List<AEDOwnerResponse>>> GetOwnersAsync(
		AED4LifeDbContext database, CancellationToken cancellationToken) {
		List<AEDOwnerResponse> owners = await (
			from owner in database.AEDOwners
			join city in database.Cities on owner.CityId equals city.Id into cities
			from city in cities.DefaultIfEmpty()
			join street in database.Streets on owner.StreetId equals street.Id into streets
			from street in streets.DefaultIfEmpty()
			orderby owner.RegonNumber
			select new AEDOwnerResponse(
				owner.RegonNumber, owner.IsPublic, owner.Name,
				city == null ? null : city.Name, street == null ? null : street.Name)
		).ToListAsync(cancellationToken);

		return TypedResults.Ok(owners);
	}
}
