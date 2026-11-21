using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;

namespace AED4Life.Endpoints;

public static class AEDEndpoints {
	public static RouteGroupBuilder MapAEDEndpoints(this IEndpointRouteBuilder endpoints) {
		RouteGroupBuilder group = endpoints.MapGroup("/api/aed").WithTags("AED");
		group.MapGet("/owners", GetOwnersAsync).WithName("GetAEDOwners");
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
