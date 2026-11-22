using System.Security.Claims;
using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using AED4Life.DataModel.Entities;
using AED4Life.DataModel.Enums;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;

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
		group.MapGet("", GetAllAsync)
			.WithName("GetAllAEDs")
			.WithSummary("Get all AEDs")
			.WithDescription("Returns every AED ordered by ID with coordinates, owner and address details, access, availability hours, DataRating and LastUpdated. "
				+ "Unknown values are returned as null; devices without coordinates are included. Returns an empty array when no AEDs exist.");
		group.MapGet("/valid", GetAllValidAsync)
			.WithName("GetAllValidAEDs")
			.WithSummary("Get all AEDs with valid (complete) data")
			.WithDescription("Returns only AEDs whose DataRating is Fine, i.e. coordinates, a complete address, access and both availability hours are known. "
				+ "Same shape and ordering as GET /api/aed. Returns an empty array when none qualify.");
		group.MapGet("/statistics", GetStatisticsAsync)
			.WithName("GetAEDStatistics")
			.WithSummary("Get data verification statistics")
			.WithDescription("Returns total, valid (DataRating Fine), missingData (DataRating MissingData) and unknown (DataRating null) AED counts, "
				+ "and validPercentage = valid / total * 100 rounded to two decimals (0 when there are no AEDs).");
		group.MapPost("/validate", ValidateAsync)
			.WithName("ValidateAEDs")
			.WithSummary("Validate all AEDs against the data standard (maintainers and administrators)")
			.WithDescription("Requires a bearer token of a Maintainer or Administrator. Goes through every AED and checks the data standard: "
				+ "location (latitude and longitude), address (city, street, postal code and building number), name (the owner's name), access, and both availability hours. "
				+ "An AED missing any of them is marked DataRating MissingData, a complete one Fine; changed AEDs get a new LastUpdated. "
				+ "Optional dryRun=true only reports. The response gives the number checked, valid, missing, changed, a per-group count of what is missing, "
				+ "and up to 100 invalid AEDs (by ID) with their missing groups.")
			.RequireAuthorization()
			.ProducesProblem(StatusCodes.Status401Unauthorized)
			.ProducesProblem(StatusCodes.Status403Forbidden);
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

	private static async Task<Ok<List<AEDDetailsResponse>>> GetAllAsync(AED4LifeDbContext database, CancellationToken cancellationToken) =>
		TypedResults.Ok(await QueryDetails(database, false).ToListAsync(cancellationToken));

	private static async Task<Ok<List<AEDDetailsResponse>>> GetAllValidAsync(AED4LifeDbContext database, CancellationToken cancellationToken) =>
		TypedResults.Ok(await QueryDetails(database, true).ToListAsync(cancellationToken));

	private static async Task<Ok<AEDStatisticsResponse>> GetStatisticsAsync(AED4LifeDbContext database, CancellationToken cancellationToken) {
		Int32 total = await database.AEDs.CountAsync(cancellationToken);
		Int32 valid = await database.AEDs.CountAsync(aed => aed.DataRating == AEDRating.Fine, cancellationToken);
		Int32 missing = await database.AEDs.CountAsync(aed => aed.DataRating == AEDRating.MissingData, cancellationToken);
		Double percentage = total == 0 ? 0 : Math.Round(100.0 * valid / total, 2);
		return TypedResults.Ok(new AEDStatisticsResponse(total, valid, missing, total - valid - missing, percentage));
	}

	private static async Task<Results<Ok<AEDValidationResponse>, ProblemHttpResult>> ValidateAsync(
		Boolean? dryRun, ClaimsPrincipal principal, AED4LifeDbContext database, CancellationToken cancellationToken) {
		if (!AuthEndpoints.IsMaintainer(await AuthEndpoints.GetCallerAsync(principal, database, cancellationToken))) {
			return AuthEndpoints.Forbidden("Only maintainers and administrators can validate AEDs.");
		}
		Boolean preview = dryRun ?? false;

		var rows = await (
			from aed in database.AEDs.AsNoTracking()
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
			orderby aed.Id
			select new {
				aed.Id, aed.Latitude, aed.Longitude, aed.Access, aed.AvailabilityStartHour, aed.AvailabilityEndHour, aed.DataRating,
				OwnerName = owner == null ? null : owner.Name,
				CityName = city == null ? null : city.Name,
				StreetName = street == null ? null : street.Name,
				PostalCode = postalCode == null ? null : postalCode.Code,
				BuildingNumber = address == null ? null : address.BuildingNumber
			}).ToListAsync(cancellationToken);

		Dictionary<String, Int32> missing = AEDDataStandard.AllGaps.ToDictionary(gap => gap, _ => 0);
		List<AEDValidationIssue> issues = [];
		List<Int64> toFine = [], toMissing = [];
		Int32 valid = 0, invalid = 0;
		foreach (var row in rows) {
			List<String> gaps = AEDDataStandard.Gaps(row.Latitude, row.Longitude, row.CityName, row.StreetName, row.PostalCode,
				row.BuildingNumber, row.OwnerName, row.Access, row.AvailabilityStartHour, row.AvailabilityEndHour);
			AEDRating rating = gaps.Count == 0 ? AEDRating.Fine : AEDRating.MissingData;
			if (gaps.Count == 0) {
				valid++;
			} else {
				invalid++;
				foreach (String gap in gaps) {
					missing[gap]++;
				}
				if (issues.Count < 100) {
					issues.Add(new AEDValidationIssue(row.Id, [.. gaps]));
				}
			}
			if (row.DataRating != rating) {
				(rating == AEDRating.Fine ? toFine : toMissing).Add(row.Id);
			}
		}

		Int32 changed = toFine.Count + toMissing.Count;
		if (!preview && changed > 0) {
			DateTime now = DateTime.UtcNow;
			await using IDbContextTransaction transaction = await database.Database.BeginTransactionAsync(cancellationToken);
			foreach ((AEDRating rating, List<Int64> ids) in new[] { (AEDRating.Fine, toFine), (AEDRating.MissingData, toMissing) }) {
				foreach (Int64[] chunk in ids.Chunk(1000)) {
					await database.AEDs.Where(aed => chunk.Contains(aed.Id)).ExecuteUpdateAsync(setters => setters
						.SetProperty(aed => aed.DataRating, rating).SetProperty(aed => aed.LastUpdated, now), cancellationToken);
				}
			}
			await transaction.CommitAsync(cancellationToken);
		}
		return TypedResults.Ok(new AEDValidationResponse(preview, rows.Count, valid, invalid, changed, missing, issues));
	}

	private static IQueryable<AEDDetailsResponse> QueryDetails(AED4LifeDbContext database, Boolean validOnly) {
		IQueryable<AED> aeds = database.AEDs.AsNoTracking();
		if (validOnly) {
			aeds = aeds.Where(aed => aed.DataRating == AEDRating.Fine);
		}
		return
			from aed in aeds.OrderBy(aed => aed.Id)
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
			select new AEDDetailsResponse(aed.Id, aed.Latitude, aed.Longitude,
				owner == null ? null : owner.Name, city == null ? null : city.Name,
				street == null ? null : street.Name, postalCode == null ? null : postalCode.Code,
				address == null ? null : address.BuildingNumber,
				aed.Access, aed.AvailabilityStartHour, aed.AvailabilityEndHour, aed.DataRating, aed.LastUpdated);
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
		var available =
			from aed in database.AEDs.AsNoTracking()
			where aed.Access == null || aed.Access == AEDAccess.Open || aed.Access == AEDAccess.Emergency
			where aed.AvailabilityStartHour == null || aed.AvailabilityEndHour == null
				|| (aed.AvailabilityStartHour < aed.AvailabilityEndHour
					? aed.AvailabilityStartHour <= hour && hour < aed.AvailabilityEndHour
					: aed.AvailabilityStartHour <= hour || hour < aed.AvailabilityEndHour)
			select aed;
		return
			from aed in available.OrderByDistance(latitude, longitude)
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
