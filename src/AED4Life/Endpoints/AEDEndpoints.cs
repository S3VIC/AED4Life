using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;

namespace AED4Life.Endpoints;

public static class AedEndpoints {
	public static RouteGroupBuilder MapAedEndpoints(this IEndpointRouteBuilder endpoints) {
		RouteGroupBuilder group = endpoints.MapGroup("/api/aed").WithTags("AED");
		group.MapGet("/owners", GetOwnersAsync)
			.WithName("GetAEDOwners")
			.WithSummary("Get AED owners with address details")
			.WithDescription("Returns all owners joined with their city and street, ordered by REGON. "
				+ "Includes the city name, postal code, and street name without exposing location IDs. "
				+ "Returns an empty array when no owners exist. No request body is required.");
		return group;
	}

	private static async Task<Ok<List<AEDOwnerResponse>>> GetOwnersAsync(
		AED4LifeDbContext database, CancellationToken cancellationToken) {
		List<AEDOwnerResponse> owners = await (
			from owner in database.AEDOwners
			join city in database.Cities on owner.CityId equals city.Id
			join street in database.Streets on owner.StreetId equals street.Id
			orderby owner.RegonNumber
			select new AEDOwnerResponse(
				owner.RegonNumber, owner.IsPublic, owner.Name,
				city.Name, city.PostalCode, street.Name)
		).ToListAsync(cancellationToken);

		return TypedResults.Ok(owners);
	}
}
