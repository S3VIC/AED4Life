using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using AED4Life.DataModel.Entities;
using AED4Life.Requests;
using AED4Life.Trananslation;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;
using MySqlConnector;

namespace AED4Life.Endpoints;

public static class TranslationEndpoints {
	public static RouteGroupBuilder MapTranslationEndpoints(this IEndpointRouteBuilder endpoints) {
		RouteGroupBuilder group = endpoints.MapGroup("/api/translations").WithTags("Translations");
		group.MapPost("/profiles", CreateProfileAsync)
			.WithName("CreateTranslationProfile")
			.WithSummary("Create a translation profile")
			.WithDescription("Creates a named profile and its mapping units in one transaction, preserving array order. "
				+ "The trimmed name must contain 1-255 characters and be unique under the database's case-insensitive collation. "
				+ "Provide at least one transporter unit with nonblank fromColumn and toColumn values. "
				+ "Both fromType and toType are required: INTEGER, DOUBLE, STRING, or BOOLEAN (numeric values 0-3 are also accepted). "
				+ "This stores configuration only; it does not execute translations.")
			.ProducesProblem(StatusCodes.Status409Conflict);
		return group;
	}

	private static async Task<Results<Created<TranslationProfileResponse>, ValidationProblem, ProblemHttpResult>> CreateProfileAsync(
		CreateTranslationConfig request, AED4LifeDbContext database, CancellationToken cancellationToken) {
		String? name = request.Name?.Trim();
		TransporterUnit[]? units = request.Transporter?.TransporterUnits;
		Dictionary<String, String[]> errors = [];

		if (String.IsNullOrWhiteSpace(name) || name.Length > 255) {
			errors["name"] = ["A profile name between 1 and 255 characters is required."];
		}

		if (units is null || units.Length == 0) {
			errors["transporter.transporterUnits"] = ["At least one mapping unit is required."];
		} else {
			for (Int32 index = 0; index < units.Length; index++) {
				TransporterUnit? unit = units[index];
				String path = $"transporter.transporterUnits[{index}]";
				if (unit is null) {
					errors[path] = ["A mapping unit cannot be null."];
					continue;
				}
				if (String.IsNullOrWhiteSpace(unit.FromColumn)) {
					errors[$"{path}.fromColumn"] = ["A source column is required."];
				}
				if (String.IsNullOrWhiteSpace(unit.ToColumn)) {
					errors[$"{path}.toColumn"] = ["A destination column is required."];
				}
				if (!Enum.IsDefined(unit.FromType)) {
					errors[$"{path}.fromType"] = ["The source type must be INTEGER, DOUBLE, STRING, or BOOLEAN."];
				}
				if (!Enum.IsDefined(unit.ToType)) {
					errors[$"{path}.toType"] = ["The destination type must be INTEGER, DOUBLE, STRING, or BOOLEAN."];
				}
			}
		}

		if (errors.Count > 0 || name is null || units is null) {
			return TypedResults.ValidationProblem(errors);
		}

		TranslationProfile profile = new() {
			Name = name,
			Units = units.Select((unit, position) => new TranslationProfileUnit {
				Position = position,
				FromColumn = unit.FromColumn,
				FromType = unit.FromType,
				ToColumn = unit.ToColumn,
				ToType = unit.ToType
			}).ToList()
		};

		database.TranslationProfiles.Add(profile);
		try {
			await database.SaveChangesAsync(cancellationToken);
		} catch (DbUpdateException exception) when (exception.InnerException is MySqlException { Number: 1062 }) {
			return TypedResults.Problem(
				statusCode: StatusCodes.Status409Conflict,
				title: "A translation profile with this name already exists.");
		}

		return TypedResults.Created(uri: String.Empty, value: new TranslationProfileResponse(
			profile.Id, profile.Name, new Transporter { TransporterUnits = units }));
	}
}
